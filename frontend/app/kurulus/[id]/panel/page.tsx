"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { PageBody, PageHeader } from "@/components/page-layout";
import {
  ActionLink,
  CopyButton,
  EmptyState,
  NextStepHint,
  PanelGrid,
  PanelIcon,
  PanelSection,
  PanelSkeleton,
  SideCard,
  StatTile,
  StatusPill,
  TimeAgo,
  actionClass,
} from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { SealMark } from "@/components/brand/brand-mark";
import {
  getOrganization,
  inviteOrgMember,
  verifyDomain,
  type OrgMemberRole,
  type OrganizationResponse,
} from "@/lib/api/organizations";
import { listEngagements, type EngagementSummary } from "@/lib/api/engagements";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import { STATUS_TONE, type StatusTone } from "@/lib/ui/engagement-chain";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.kurulusPanel;
const c = messages.calismalar;

const FIELD_CLASS =
  "block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground transition-colors hover:border-muted-foreground/40 focus-visible:border-success focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/25";
const LABEL_CLASS = "mb-1.5 block text-xs font-medium text-foreground";

const TRUST_TONE: Record<string, StatusTone> = {
  T0: "default",
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};

// Rows the organization has to act on come first, closed ones last.
const STATUS_ORDER: Record<string, number> = {
  PENDING_EVALUATION: 0,
  EVALUATED: 1,
  PENDING_APPROVAL: 2,
  ACTIVE: 3,
  DRAFT: 4,
  DISPUTED: 5,
  VERIFIED: 6,
  RESOLVED: 7,
  REJECTED: 8,
  CANCELLED: 9,
};

// Finished rows: the status badge already says it all, no "next step" chip.
const CLOSED = new Set(["VERIFIED", "RESOLVED", "REJECTED", "CANCELLED"]);

function sortForOrganization(items: EngagementSummary[]): EngagementSummary[] {
  return [...items].sort(
    (a, b) =>
      (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99) ||
      b.updated_at.localeCompare(a.updated_at)
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof SessionExpiredError) return messages.session.expired;
  if (error instanceof ApiError || error instanceof NetworkError) return error.message;
  return messages.errors.generic;
}

/**
 * YET-202/ENT-01: Organizasyon paneli — çalışma özeti + alan adı doğrulama (DNS TXT) + üye davet.
 *
 * Alan adı doğrulama UX'i: "Doğrulamayı Kontrol Et" tıklanınca backend bir TXT token
 * üretir/yeniden kullanır ve DNS'i sorgular. "pending" bir HATA DEĞİLDİR — kayıt henüz
 * DNS'te yok demektir; TXT değeri ekrana basılır, kullanıcı DNS sağlayıcısına ekler,
 * tekrar dener. verification_level T1'den çıkınca (T2+) buton kalkar, doğrulanmış rozeti kalır.
 */
export default function KurulusPanelPage() {
  const params = useParams<{ id: string }>();
  const organizationId = params.id;

  const { data: org, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["organization", organizationId] as const,
    queryFn: () => getOrganization(organizationId),
  });

  // The link students open to start an engagement with this organization.
  const startLink = () => `${window.location.origin}/calismalar/olustur?organization_id=${organizationId}`;

  const trustLabels = t.trustLevel as Record<string, string>;

  return (
    <AppShell>
      <PageHeader
        eyebrow={t.title}
        title={org?.name ?? t.title}
        description={
          org ? (
            <span className="flex flex-col gap-2">
              <span>{t.pageDescription}</span>
              <span className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <StatusPill tone={TRUST_TONE[org.verification_level] ?? "default"}>
                  {trustLabels[org.verification_level] ?? org.verification_level}
                </StatusPill>
                {org.legal_id ? (
                  <span className="font-mono text-[13px] text-muted-foreground">
                    {t.legalIdLabel}: {org.legal_id}
                  </span>
                ) : null}
              </span>
            </span>
          ) : undefined
        }
        actions={org ? <CopyButton value={startLink} label={t.startLinkButton} /> : undefined}
      />

      <PageBody>
        {isLoading ? <PanelSkeleton /> : null}

        {isError && error ? (
          <ErrorBanner
            message={errorMessage(error)}
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => refetch()}
          />
        ) : null}

        {!isLoading && !isError && org ? (
          <PanelGrid
            main={<EngagementsOverview organizationId={organizationId} startLink={startLink} />}
            aside={
              <>
                <DomainCard org={org} />
                <InviteCard organizationId={organizationId} />
              </>
            }
          />
        ) : null}
      </PageBody>
    </AppShell>
  );
}

function EngagementsOverview({ organizationId, startLink }: { organizationId: string; startLink: () => string }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["engagements"],
    queryFn: listEngagements,
  });

  if (isLoading) return <PanelSkeleton />;

  if (isError) {
    return (
      <Alert variant="error" className="flex items-center justify-between gap-4 text-sm">
        <span>{t.engagementsError}</span>
        <button type="button" onClick={() => void refetch()} className={actionClass.neutral}>
          {messages.errors.retry}
        </button>
      </Alert>
    );
  }

  // A member of several organizations gets all of them from /engagements.
  const items = sortForOrganization((data?.items ?? []).filter((item) => item.organization_id === organizationId));
  const awaiting = items.filter((item) => item.status === "PENDING_EVALUATION").length;
  const verified = items.filter((item) => item.status === "VERIFIED" || item.status === "RESOLVED").length;

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatTile label={t.summary.total} value={items.length} tone="ink" icon="briefcase" />
        <StatTile
          label={t.summary.awaiting}
          value={awaiting}
          tone="ochre"
          icon="clipboard"
          href="#kurulus-calismalar"
        />
        <StatTile label={t.summary.verified} value={verified} tone="pine" icon="check" />
      </div>

      <PanelSection
        id="kurulus-calismalar"
        icon="briefcase"
        title={t.engagementsTitle}
        hint={t.engagementsHint}
        count={items.length}
        flush={items.length > 0}
      >
        {items.length === 0 ? (
          <EmptyState
            icon="link"
            title={t.engagementsEmptyTitle}
            hint={t.engagementsEmptyHint}
            action={<CopyButton value={startLink} label={t.startLinkButton} variant="neutral" />}
          />
        ) : (
          <ul className="divide-y divide-border">
            {items.map((item) => {
              const tone = STATUS_TONE[item.status] ?? "default";
              const needsEvaluation = item.status === "PENDING_EVALUATION";
              return (
                <li
                  key={item.id}
                  className={cn(
                    "y360-step-in flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-background sm:flex-row sm:items-center",
                    needsEvaluation && "bg-warning/[0.04]"
                  )}
                >
                  <Link
                    href={`/calismalar/${item.id}`}
                    className="group min-w-0 flex-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-foreground group-hover:underline group-hover:underline-offset-4">
                        {item.title}
                      </span>
                      <StatusPill tone={tone}>{c.status[item.status]}</StatusPill>
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-muted-foreground">
                      <span>{c.kind[item.kind]}</span>
                      <TimeAgo iso={item.updated_at} />
                    </span>
                  </Link>
                  <div className="flex shrink-0 flex-wrap items-center gap-2 empty:hidden">
                    {CLOSED.has(item.status) ? null : (
                      <NextStepHint tone={tone}>
                        {(t.orgNextStep as Record<string, string>)[item.status] ?? c.status[item.status]}
                      </NextStepHint>
                    )}
                    {needsEvaluation ? (
                      <ActionLink href={`/calismalar/${item.id}/degerlendirme`} variant="outline" className="h-8 px-3">
                        {t.evaluateAction}
                      </ActionLink>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </PanelSection>
    </>
  );
}

function DomainCard({ org }: { org: OrganizationResponse }) {
  const queryClient = useQueryClient();
  const [dnsTxtRecord, setDnsTxtRecord] = useState<string | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<"verified" | "pending" | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const verifyMutation = useMutation({
    mutationFn: () => verifyDomain(org.id),
    onSuccess: (result) => {
      setVerifyError(null);
      setDnsTxtRecord(result.dns_txt_record);
      setVerifyStatus(result.status);
      if (result.status === "verified") {
        queryClient.invalidateQueries({ queryKey: ["organization", org.id] });
      }
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.code === "FREE_EMAIL_DOMAIN") return setVerifyError(t.freeEmailDomainError);
        if (error.code === "TOO_MANY_REQUESTS") return setVerifyError(t.rateLimitedError);
        if (error.code === "DOMAIN_ALREADY_VERIFIED") return setVerifyError(t.domainAlreadyVerifiedError);
      }
      setVerifyError(messages.errors.generic);
    },
  });

  return (
    <SideCard title={t.domainSectionTitle} hint={t.domainHint}>
      {!org.domain ? (
        <Alert variant="info" className="text-sm">
          {t.noDomainMessage}
        </Alert>
      ) : org.verification_level !== "T1" ? (
        <div className="flex items-start gap-3 rounded-lg border border-success/25 bg-success/[0.06] p-3">
          <SealMark className="h-9 w-9 shrink-0" />
          <div className="min-w-0 text-sm">
            <p className="font-medium text-success">{t.verifiedMessage}</p>
            <p className="mt-0.5 truncate font-mono text-[13px] text-muted-foreground">{org.domain}</p>
            <StatusPill tone="success" className="mt-2">
              {t.domainVerifiedBadge}
            </StatusPill>
          </div>
        </div>
      ) : (
        <div className="text-sm">
          <p className="flex items-center gap-2 text-foreground">
            <PanelIcon name="globe" className="h-4 w-4 text-muted-foreground" />
            {t.domainLabel}: <strong className="font-mono text-[13px] font-medium">{org.domain}</strong>
          </p>

          {dnsTxtRecord ? (
            <div className="mt-3">
              <p className="mb-2 text-xs text-muted-foreground">{t.txtRecordHint}</p>
              <code
                aria-label={t.txtRecordLabel}
                className="block select-all break-all rounded-md border border-border bg-muted px-3 py-2 font-mono text-[13px] text-foreground"
              >
                {dnsTxtRecord}
              </code>
            </div>
          ) : null}

          {verifyStatus === "pending" ? (
            <Alert variant="warning" className="mt-3 text-sm">
              {t.pendingMessage}
            </Alert>
          ) : null}
          {verifyStatus === "verified" ? (
            <Alert variant="success" className="mt-3 text-sm">
              {t.verifiedMessage}
            </Alert>
          ) : null}
          {verifyError ? (
            <Alert variant="error" className="mt-3 text-sm">
              {verifyError}
            </Alert>
          ) : null}

          {verifyStatus !== "verified" ? (
            <button
              type="button"
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending}
              className={cn(actionClass.primary, "mt-4 w-full")}
            >
              {verifyMutation.isPending
                ? t.verifyingButton
                : dnsTxtRecord
                  ? t.retryVerifyButton
                  : t.verifyButton}
            </button>
          ) : null}
        </div>
      )}
    </SideCard>
  );
}

function InviteCard({ organizationId }: { organizationId: string }) {
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<OrgMemberRole>("MEMBER");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);

  const inviteMutation = useMutation({
    mutationFn: () => inviteOrgMember(organizationId, inviteEmail.trim(), inviteRole),
    onSuccess: () => {
      setInviteError(null);
      setInviteMessage(t.inviteSuccessMessage);
      setInviteEmail("");
    },
    onError: () => {
      setInviteMessage(null);
      setInviteError(t.inviteErrorMessage);
    },
  });

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInviteMessage(null);
    setInviteError(null);
    inviteMutation.mutate();
  };

  return (
    <SideCard title={t.inviteMemberTitle} hint={t.inviteHint}>
      <form onSubmit={handleInviteSubmit} className="space-y-3">
        <div>
          <label htmlFor="org-invite-email" className={LABEL_CLASS}>
            {t.inviteEmailLabel}
          </label>
          <input
            id="org-invite-email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            required
            className={FIELD_CLASS}
          />
        </div>
        <div>
          <label htmlFor="org-invite-role" className={LABEL_CLASS}>
            {t.inviteRoleLabel}
          </label>
          <select
            id="org-invite-role"
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as OrgMemberRole)}
            className={FIELD_CLASS}
          >
            <option value="MEMBER">{t.memberRole.MEMBER}</option>
            <option value="ADMIN">{t.memberRole.ADMIN}</option>
          </select>
        </div>
        <button type="submit" disabled={inviteMutation.isPending} className={cn(actionClass.neutral, "w-full")}>
          <PanelIcon name="userPlus" className="h-4 w-4" />
          {inviteMutation.isPending ? t.invitingButton : t.inviteButton}
        </button>

        {inviteError ? (
          <Alert variant="error" className="text-sm">
            {inviteError}
          </Alert>
        ) : null}
        {inviteMessage ? (
          <Alert variant="success" className="text-sm">
            {inviteMessage}
          </Alert>
        ) : null}
      </form>
    </SideCard>
  );
}
