"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { useSession } from "@/lib/session/use-session";
import { ChainLegend, PageBody, PageHeader } from "@/components/page-layout";
import { SealMark } from "@/components/brand/brand-mark";
import { getEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { CHAIN_PROGRESS, STATUS_TONE, type StatusTone } from "@/lib/ui/engagement-chain";
import { cn } from "@/lib/utils";
import { TransitionActions } from "./transition-actions";
import { EvidenceUploadForm } from "./evidence-upload-form";
import { DeliverableForm } from "./deliverable-form";
import { AttestationForm } from "./attestation-form";
import { TaskForm } from "./task-form";
import { AttestationRevoke } from "./attestation-revoke";
import messages from "@/messages/tr.json";

const c = messages.calismalar;

const TONE_BADGE: Record<StatusTone, string> = {
  default: "border-border bg-muted text-foreground",
  warning: "border-warning/30 bg-warning/10 text-warning",
  success: "border-success/30 bg-success/10 text-success",
  error: "border-destructive/30 bg-destructive/10 text-destructive",
};

const TASK_BADGE: Record<string, string> = {
  PLANNED: "bg-muted text-muted-foreground",
  IN_PROGRESS: "bg-warning/10 text-warning",
  DONE: "bg-success/10 text-success",
};

// Lucide-style line icons for the section headers.
const ICONS = {
  tasks: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
  deliverables: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M12 18v-6M9 15l3-3 3 3",
  attestations: "M12 15a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM8.2 13.9 7 23l5-3 5 3-1.2-9.1",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

function DetailSection({
  icon,
  title,
  hint,
  count,
  children,
}: {
  icon: keyof typeof ICONS;
  title: string;
  hint: string;
  count: number;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card">
      <header className="flex items-center gap-3 border-b border-border px-5 py-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success">
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d={ICONS[icon]} />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="flex items-center gap-2 font-serif text-lg font-semibold text-foreground">
            {title}
            <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] font-normal tabular-nums text-muted-foreground">
              {count}
            </span>
          </h2>
          <p className="text-[13px] text-muted-foreground">{hint}</p>
        </div>
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

function EmptyLine({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-dashed border-border px-4 py-3 text-sm text-muted-foreground">{children}</p>
  );
}

export default function CalismaDetayPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const currentUserId = useSession().data?.user.id;
  const ENGAGEMENT_QUERY_KEY = ["engagement", id] as const;
  const refresh = () => queryClient.invalidateQueries({ queryKey: ENGAGEMENT_QUERY_KEY });

  const { data: engagement, isLoading, isError, error } = useQuery({
    queryKey: ENGAGEMENT_QUERY_KEY,
    queryFn: () => getEngagement(id),
  });

  const back = { href: "/calismalar", label: c.detailBackLink };

  if (isLoading || isError || !engagement) {
    return (
      <AppShell>
        <PageBody>
          <Link href={back.href} className="text-sm text-muted-foreground hover:text-foreground hover:underline">
            ← {back.label}
          </Link>
          {isLoading ? (
            <p className="mt-4 text-muted-foreground">{messages.shell.loading}</p>
          ) : isError ? (
            <div
              role="alert"
              className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
            >
              {error instanceof ApiError && error.status === 404 ? c.detailNotFound : c.detailLoadError}
            </div>
          ) : null}
        </PageBody>
      </AppShell>
    );
  }

  const tone = STATUS_TONE[engagement.status] ?? "default";
  const progress = CHAIN_PROGRESS[engagement.status] ?? { done: 0 };
  const isVerified = engagement.status === "VERIFIED" || engagement.status === "RESOLVED";

  return (
    <AppShell>
      <PageHeader
        back={back}
        eyebrow={c.kind[engagement.kind]}
        title={engagement.title}
        description={
          <span className="inline-flex flex-wrap items-center gap-x-2">
            <span className="font-medium text-foreground">{engagement.organization_name}</span>
            <span aria-hidden="true">·</span>
            <span>
              {c.updatedAtLabel}: {formatDate(engagement.updated_at)}
            </span>
          </span>
        }
        actions={
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-medium",
              TONE_BADGE[tone]
            )}
          >
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-current" />
            {c.status[engagement.status]}
          </span>
        }
      >
        <ChainLegend current={progress.done} broken={progress.broken} />
      </PageHeader>

      <PageBody>
        {isVerified ? (
          <div className="mb-6 flex flex-col gap-4 overflow-hidden rounded-xl border border-success/30 bg-success/[0.07] p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <SealMark className="y360-stamp h-16 w-16 shrink-0" />
              <div>
                <p className="font-serif text-xl font-semibold text-success">{c.detail.verifiedTitle}</p>
                <p className="mt-0.5 text-sm text-foreground">{c.detail.verifiedText}</p>
              </div>
            </div>
            <Link
              href="/profil"
              className="inline-flex h-10 shrink-0 items-center justify-center rounded-md bg-success px-4 text-sm font-medium text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
            >
              {c.detail.verifiedLink}
            </Link>
          </div>
        ) : null}

        {engagement.reason && (
          <div className="mb-6 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
            {c.reasonLabel}: {engagement.reason}
          </div>
        )}

        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-6">
            <DetailSection icon="tasks" title={c.tasksTitle} hint={c.detail.tasksHint} count={engagement.tasks.length}>
              <TaskForm engagement={engagement} onSuccess={refresh} />
              {engagement.tasks.length === 0 ? (
                <EmptyLine>{c.emptyTasksMessage}</EmptyLine>
              ) : (
                <ul className="divide-y divide-border rounded-lg border border-border">
                  {engagement.tasks.map((task) => (
                    <li key={task.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                      <span className="text-foreground">{task.title}</span>
                      <span
                        className={cn(
                          "shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium",
                          TASK_BADGE[task.status] ?? TASK_BADGE.PLANNED
                        )}
                      >
                        {(c.taskStatus as Record<string, string>)[task.status] ?? task.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </DetailSection>

            <DetailSection
              icon="deliverables"
              title={c.deliverablesTitle}
              hint={c.detail.deliverablesHint}
              count={engagement.deliverables.length}
            >
              <DeliverableForm engagement={engagement} onSuccess={refresh} />
              {engagement.deliverables.length === 0 ? (
                <EmptyLine>{c.emptyDeliverablesMessage}</EmptyLine>
              ) : (
                <ul className="space-y-3">
                  {engagement.deliverables.map((deliverable) => (
                    <li key={deliverable.id} className="rounded-lg border border-border bg-background p-4">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <span className="font-medium text-foreground">{deliverable.title}</span>
                        {deliverable.submitted_at ? (
                          <span className="font-mono text-xs text-muted-foreground">
                            {c.detail.submittedOn.replace("{date}", formatDate(deliverable.submitted_at))}
                          </span>
                        ) : null}
                      </div>
                      <EvidenceUploadForm deliverableId={deliverable.id} />
                    </li>
                  ))}
                </ul>
              )}
            </DetailSection>

            <DetailSection
              icon="attestations"
              title={c.attestationsTitle}
              hint={c.detail.attestationsHint}
              count={engagement.attestations.length}
            >
              {engagement.attestations.length === 0 ? (
                <EmptyLine>{c.emptyAttestationsMessage}</EmptyLine>
              ) : (
                <ul className="space-y-3">
                  {engagement.attestations.map((attestation) => (
                    <li
                      key={attestation.id}
                      className={cn(
                        "rounded-lg border p-4",
                        attestation.revoked_at ? "border-border bg-muted/40" : "border-success/25 bg-success/[0.04]"
                      )}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="flex items-center gap-2.5">
                          <SealMark
                            className={cn("h-6 w-6", attestation.revoked_at && "text-muted-foreground/50")}
                          />
                          <span className="font-medium text-foreground">
                            {(c.claimType as Record<string, string>)[attestation.claim_type] ?? attestation.claim_type}
                          </span>
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">
                          {formatDate(attestation.created_at)}
                        </span>
                      </div>
                      {/* Only the attestor may revoke (server enforces it too); a revoked
                          attestation's reason stays visible to everyone. */}
                      {attestation.revoked_at || attestation.attestor_user_id === currentUserId ? (
                        <AttestationRevoke attestation={attestation} onSuccess={refresh} />
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </DetailSection>
          </div>

          <aside className="space-y-4 lg:sticky lg:top-6">
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="font-serif text-lg font-semibold text-foreground">{c.detail.statusCardTitle}</p>
              <dl className="mt-4 text-sm">
                <div className="rounded-lg bg-muted/60 px-3 py-2.5">
                  <dt className="text-xs text-muted-foreground">{c.detail.nextStepLabel}</dt>
                  <dd className="mt-0.5 font-medium text-foreground">
                    {(c.nextStep as Record<string, string>)[engagement.status]}
                  </dd>
                </div>
              </dl>

              <TransitionActions engagement={engagement} onSuccess={refresh} />

              {engagement.status === "PENDING_EVALUATION" && (
                <Link
                  href={`/calismalar/${engagement.id}/degerlendirme`}
                  className="mt-4 flex h-10 w-full items-center justify-center rounded-md bg-success px-4 text-sm font-medium text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
                >
                  {c.evaluationFormLink}
                </Link>
              )}

              <AttestationForm engagement={engagement} onSuccess={refresh} />
            </div>
          </aside>
        </div>
      </PageBody>
    </AppShell>
  );
}
