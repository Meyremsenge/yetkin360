"use client";

import Link from "next/link";
import { Suspense, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { useSession } from "@/lib/session/use-session";
import {
  createEngagement,
  listOwnApprovalRecipients,
  transitionEngagement,
  type CreateEngagementResponse,
  type EngagementKind,
} from "@/lib/api/engagements";
import { listApprovers } from "@/lib/api/organizations";
import { getOrganizationShowcase } from "@/lib/api/public";
import { ApiError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { ApproverIdentity, NewEngagementSteps } from "../yeni-calisma-parts";

const KIND_OPTIONS: EngagementKind[] = ["INTERNSHIP", "CAPSTONE", "SHORT_PROJECT", "PART_TIME"];
// Mirrors SCHOOL_BOUND_KINDS (backend): the student's school always approves these.
const SCHOOL_BOUND_KINDS = new Set<EngagementKind>(["INTERNSHIP", "CAPSTONE"]);

const o = messages.calismaOlustur;
const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";
const legendClass = "mb-2 block text-[13px] font-medium text-foreground";
const fieldClass =
  "block h-11 w-full rounded-md border border-border bg-card px-3 text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25";
// A native radio drives each choice card: arrow keys, focus and form semantics come for free.
const choiceCard =
  "flex h-full cursor-pointer items-start gap-3 rounded-lg border border-border bg-card p-3.5 transition-colors hover:border-muted-foreground/50 has-[:checked]:border-success has-[:checked]:bg-success/[0.06] has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-success";
const radioClass = "mt-0.5 h-4 w-4 shrink-0 accent-success";

function PageFrame({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <AppShell>
      <PageHeader
        back={{ href: "/calismalar/kurulus-sec", label: o.backToPicker }}
        eyebrow={messages.kurulusSec.eyebrow}
        title={o.title}
        description={o.description}
      >
        <NewEngagementSteps current={2} />
      </PageHeader>
      <PageBody>
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="min-w-0 max-w-[640px]">{children}</div>
          {aside}
        </div>
      </PageBody>
    </AppShell>
  );
}

function InfoState({ message }: { message: string }) {
  return (
    <div>
      <Alert variant="info" className="text-sm">
        {message}
      </Alert>
      <Link
        href="/calismalar/kurulus-sec"
        className="mt-4 inline-flex items-center gap-1.5 rounded-sm text-sm font-medium text-success hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
      >
        {o.missingLinkPickerLink}
      </Link>
    </div>
  );
}

/** Which organization this draft goes to, and what happens after "Taslağı oluştur". */
function Summary({ organizationId, viaSchool }: { organizationId: string; viaSchool: boolean }) {
  // Public card (no membership needed): also reached from a link the organization shared.
  const organization = useQuery({
    queryKey: ["organization-showcase", organizationId],
    queryFn: () => getOrganizationShowcase(organizationId),
    retry: false,
  });
  const level = organization.data?.verification_level ?? "";

  return (
    <aside className="space-y-4 lg:sticky lg:top-6">
      <section className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[13px] font-medium text-muted-foreground">{o.orgSummaryLabel}</h2>
          <Link
            href="/calismalar/kurulus-sec"
            className="rounded-sm text-[13px] font-medium text-success hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
          >
            {o.changeOrg}
          </Link>
        </div>
        {organization.isLoading ? (
          <div role="status" aria-busy="true" aria-label={o.orgLoadingLabel} className="mt-3 space-y-2">
            <div className={`h-5 w-3/4 ${pulse}`} />
            <div className={`h-4 w-1/2 ${pulse}`} />
          </div>
        ) : organization.data ? (
          <div className="mt-3">
            <p className="font-serif text-lg font-semibold leading-6 text-foreground">{organization.data.name}</p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              {organization.data.domain ? <span className="font-mono">{organization.data.domain} · </span> : null}
              {messages.kurulusSec.verificationLevel[level as keyof typeof messages.kurulusSec.verificationLevel] ?? level}
            </p>
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-border bg-sand/60 p-5">
        <h2 className="font-serif text-base font-semibold text-foreground">{o.nextTitle}</h2>
        <ol className="mt-3 space-y-2.5">
          {(viaSchool ? o.nextStepsSchool : o.nextStepsDirect).map((step, index) => (
            <li key={step} className="flex gap-2.5 text-[13px] leading-5 text-foreground">
              <span aria-hidden="true" className="font-mono text-muted-foreground">
                {index + 1}.
              </span>
              {step}
            </li>
          ))}
        </ol>
      </section>
    </aside>
  );
}

/**
 * YET-202/ENT-01: Engagement oluşturma — adım 2/2. Kuruluş ya seçiciden
 * (/calismalar/kurulus-sec) ya da kuruluşun paylaştığı bağlantıdan gelir.
 *
 * talent_id ve institution_id kullanıcıdan ASLA elle istenmez — oturumdan
 * otomatik doldurulur. institution_id verilirse backend onu talent'ın kendi
 * institution_id'siyle eşleştirmek ZORUNDA (INSTITUTION_MISMATCH, 400) —
 * elle girilebilir bir alan olsa bu hatayı anlamsız yere tetikler.
 *
 * SPRINT D1: kuruluşun onaylayıcı listesi (GET /organizations/{id}/approvers) varsa
 * "Kime gönderilsin?" seçimi gösterilir (ad · birim · maskeli e-posta); varsayılan
 * genel (kuruluş yöneticisi = null). Liste boşsa ya da alınamazsa alan hiç
 * gösterilmez. Kullanıcının kendisi listeden çıkarılır (sunucu da kendini
 * onaylayıcı seçmeyi 404 ile reddeder).
 *
 * Suspense sarmalı: useSearchParams() App Router'da CSR-bailout için bir
 * Suspense sınırı gerektirir, yoksa `next build` prerender'da hata verir
 * (bkz. e-posta-dogrula/page.tsx'teki aynı desen).
 */
function CalismaOlusturContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const organizationId = searchParams.get("organization_id");
  const session = useSession();

  const [kind, setKind] = useState<EngagementKind>("INTERNSHIP");
  const [title, setTitle] = useState("");
  const [supervisorUserId, setSupervisorUserId] = useState("");
  // Short projects and part-time work skip the school unless the student asks for it.
  const [schoolOptIn, setSchoolOptIn] = useState(false);
  // "" = every coordinator of the school (the server's default).
  const [coordinatorId, setCoordinatorId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  // Created, but the follow-up send failed: never create a second one on retry.
  const [orphanDraft, setOrphanDraft] = useState<CreateEngagementResponse | null>(null);

  const talentId = session.data?.talent_profile?.id;
  const institutionId = session.data?.talent_profile?.institution_id;
  const currentUserId = session.data?.user.id;

  const approversQuery = useQuery({
    queryKey: ["organization-approvers", organizationId],
    queryFn: () => listApprovers(organizationId as string),
    enabled: Boolean(organizationId && talentId),
    retry: false,
  });
  const approvers = (approversQuery.data ?? []).filter((approver) => approver.user_id !== currentUserId);

  const hasSchool = Boolean(institutionId);
  const schoolBound = SCHOOL_BOUND_KINDS.has(kind);
  const viaSchool = hasSchool && (schoolBound || schoolOptIn);

  const coordinatorsQuery = useQuery({
    queryKey: ["own-approval-recipients"],
    queryFn: listOwnApprovalRecipients,
    enabled: Boolean(talentId && hasSchool),
    retry: false,
  });
  const coordinators = coordinatorsQuery.data ?? [];

  const mutation = useMutation({
    mutationFn: async ({ draftOnly }: { draftOnly: boolean }) => {
      if (!organizationId || !talentId) {
        throw new Error("missing_precondition");
      }
      const engagement = await createEngagement({
        talent_id: talentId,
        organization_id: organizationId,
        kind,
        title: title.trim(),
        institution_id: viaSchool ? (institutionId ?? undefined) : undefined,
        supervisor_user_id: supervisorUserId || undefined,
      });
      if (draftOnly) return engagement;
      try {
        await transitionEngagement(engagement.id, {
          to_status: viaSchool ? "PENDING_APPROVAL" : "ACTIVE",
          version: engagement.version,
          ...(viaSchool && coordinatorId ? { notify_user_ids: [coordinatorId] } : {}),
        });
      } catch {
        setOrphanDraft(engagement);
        throw new Error("send_failed");
      }
      return engagement;
    },
    onSuccess: (engagement) => {
      router.push(`/calismalar/${engagement.id}`);
    },
    onError: (error: unknown) => {
      if (error instanceof Error && error.message === "send_failed") {
        setFormError(o.sendFailedAfterCreate);
        return;
      }
      if (error instanceof ApiError && error.code === "ORGANIZATION_NOT_FOUND") {
        setFormError(o.invalidLinkError);
        return;
      }
      // The server answers an approver who is no longer available with the same
      // generic 404; with an approver chosen, that is the likely cause.
      if (error instanceof ApiError && error.status === 404 && supervisorUserId) {
        setFormError(o.supervisorUnavailableError);
        void approversQuery.refetch();
        return;
      }
      setFormError(messages.errors.generic);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    mutation.mutate({ draftOnly: false });
  };

  const handleSaveDraft = (e: React.MouseEvent<HTMLButtonElement>) => {
    // Same validation as the main submit: the title is required.
    const form = e.currentTarget.form;
    if (form && !form.reportValidity()) return;
    setFormError(null);
    mutation.mutate({ draftOnly: true });
  };

  if (!organizationId) {
    return (
      <PageFrame>
        <InfoState message={o.missingLinkMessage} />
      </PageFrame>
    );
  }

  if (session.isPending) {
    return (
      <PageFrame>
        <div role="status" aria-busy="true" aria-label={o.loadingLabel} className="space-y-4">
          <div className={`h-5 w-24 ${pulse}`} />
          <div className="grid grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((n) => (
              <div key={n} className={`h-[72px] ${pulse}`} />
            ))}
          </div>
          <div className={`h-11 w-full ${pulse}`} />
        </div>
      </PageFrame>
    );
  }

  if (!talentId) {
    return (
      <PageFrame>
        <InfoState message={o.notATalentMessage} />
      </PageFrame>
    );
  }

  return (
    <PageFrame aside={<Summary organizationId={organizationId} viaSchool={viaSchool} />}>
      <form onSubmit={handleSubmit} className="space-y-8">
        <fieldset>
          <legend className={legendClass}>{o.kindLabel}</legend>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {KIND_OPTIONS.map((option) => (
              <label key={option} className={choiceCard}>
                <input
                  type="radio"
                  name="engagement-kind"
                  value={option}
                  checked={kind === option}
                  onChange={() => setKind(option)}
                  className={radioClass}
                />
                <span>
                  <span className="block text-[15px] font-medium text-foreground">
                    {messages.calismalar.kind[option]}
                  </span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">{o.kindHint[option]}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <label htmlFor="engagement-title" className={legendClass}>
            {o.titleLabel}
          </label>
          <input
            id="engagement-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={o.titlePlaceholder}
            aria-describedby="engagement-title-hint"
            required
            className={fieldClass}
          />
          <p id="engagement-title-hint" className="mt-1.5 text-[13px] text-muted-foreground">
            {o.titleHint}
          </p>
        </div>

        {approvers.length > 0 && (
          <fieldset aria-describedby="engagement-supervisor-hint">
            <legend className={legendClass}>{o.supervisorLabel}</legend>
            <p id="engagement-supervisor-hint" className="-mt-1 mb-3 text-[13px] text-muted-foreground">
              {o.supervisorHint}
            </p>
            <div className="space-y-2">
              <label className={choiceCard}>
                <input
                  type="radio"
                  name="engagement-supervisor"
                  value=""
                  checked={supervisorUserId === ""}
                  onChange={() => setSupervisorUserId("")}
                  className={cn(radioClass, "mt-2.5")}
                />
                <span className="flex min-w-0 items-center gap-3">
                  <span
                    aria-hidden="true"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-dashed border-muted-foreground/40 text-muted-foreground"
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7}>
                      <path d="M4 21V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16M15 9h4a1 1 0 0 1 1 1v11M8 8h3M8 12h3M8 16h3M3 21h18" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-foreground">{o.supervisorDefault}</span>
                    <span className="block text-xs text-muted-foreground">{o.supervisorDefaultHint}</span>
                  </span>
                </span>
              </label>
              {approvers.map((approver) => (
                <label key={approver.user_id} className={choiceCard}>
                  <input
                    type="radio"
                    name="engagement-supervisor"
                    value={approver.user_id}
                    checked={supervisorUserId === approver.user_id}
                    onChange={() => setSupervisorUserId(approver.user_id)}
                    className={cn(radioClass, "mt-2.5")}
                  />
                  <ApproverIdentity approver={approver} />
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {hasSchool && !schoolBound ? (
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={schoolOptIn}
              onChange={(e) => setSchoolOptIn(e.target.checked)}
              aria-describedby="engagement-school-opt-in-hint"
              className="mt-0.5 h-4 w-4 shrink-0 accent-success"
            />
            <span>
              <span className="block text-sm font-medium text-foreground">{o.schoolOptIn}</span>
              <span id="engagement-school-opt-in-hint" className="block text-[13px] text-muted-foreground">
                {o.schoolOptInHint}
              </span>
            </span>
          </label>
        ) : null}

        {viaSchool ? (
          <fieldset aria-describedby="engagement-school-hint">
            <legend className={legendClass}>{o.schoolLegend}</legend>
            <p id="engagement-school-hint" className="-mt-1 mb-3 text-[13px] text-muted-foreground">
              {o.schoolHint}
            </p>
            {coordinatorsQuery.isLoading ? (
              <div className="space-y-2" aria-hidden="true">
                {[0, 1].map((n) => (
                  <div key={n} className={`h-14 w-full ${pulse}`} />
                ))}
              </div>
            ) : coordinators.length === 0 ? (
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-foreground">{o.schoolNone}</p>
            ) : (
              <div className="space-y-2">
                <label className={choiceCard}>
                  <input
                    type="radio"
                    name="engagement-coordinator"
                    value=""
                    checked={coordinatorId === ""}
                    onChange={() => setCoordinatorId("")}
                    className={radioClass}
                  />
                  <span>
                    <span className="block text-sm font-medium text-foreground">{o.schoolAll}</span>
                    <span className="block text-xs text-muted-foreground">{o.schoolAllHint}</span>
                  </span>
                </label>
                {coordinators.map((coordinator) => (
                  <label key={coordinator.user_id} className={choiceCard}>
                    <input
                      type="radio"
                      name="engagement-coordinator"
                      value={coordinator.user_id}
                      checked={coordinatorId === coordinator.user_id}
                      onChange={() => setCoordinatorId(coordinator.user_id)}
                      className={cn(radioClass, "mt-2.5")}
                    />
                    <ApproverIdentity approver={coordinator} />
                  </label>
                ))}
              </div>
            )}
          </fieldset>
        ) : hasSchool ? null : (
          // With a school, the opt-in hint above already says the same.
          <p className="rounded-md border border-border bg-card px-3 py-2.5 text-[13px] text-muted-foreground">
            {o.noSchoolNote}
          </p>
        )}

        {formError && (
          <Alert variant="error" role="alert" aria-live="polite" className="p-3 text-sm">
            {formError}
            {orphanDraft ? (
              <Link
                href={`/calismalar/${orphanDraft.id}`}
                className="ml-2 font-medium underline underline-offset-4"
              >
                {o.openDraft}
              </Link>
            ) : null}
          </Alert>
        )}

        <div className="flex flex-wrap items-center gap-3 border-t border-border pt-6">
          <Button
            type="submit"
            disabled={mutation.isPending || Boolean(orphanDraft)}
            className="h-11 px-6 text-background disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
          >
            {mutation.isPending
              ? o.submittingButton
              : viaSchool
                ? o.submitAndSendButton
                : o.submitAndStartButton}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={handleSaveDraft}
            disabled={mutation.isPending || Boolean(orphanDraft)}
            className="h-11 text-muted-foreground hover:text-foreground"
          >
            {o.submitButton}
          </Button>
        </div>
      </form>
    </PageFrame>
  );
}

export default function CalismaOlusturPage() {
  return (
    <Suspense fallback={null}>
      <CalismaOlusturContent />
    </Suspense>
  );
}
