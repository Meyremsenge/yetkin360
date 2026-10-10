"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { PageBody, PageHeader } from "@/components/page-layout";
import { CopyButton, PanelGrid, PanelSkeleton, StatTile, StatusPill, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { getOrganization, listOrgMembers } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";
import type { StatusTone } from "@/lib/ui/engagement-chain";
import { useSession } from "@/lib/session/use-session";
import messages from "@/messages/tr.json";
import { CandidateVerifyCard } from "./candidate-verify-card";
import { DomainCard } from "./domain-card";
import { Inbox } from "./inbox";
import { InviteCard } from "./invite-card";
import { fill, listOrganizationEngagements, orgRoleOf, summarize } from "./panel-data";
import { PartnersSection } from "./partners-section";
import { ShowcaseCard } from "./showcase-card";
import { TeamCard } from "./team-card";
import { errorMessage } from "./ui";

const t = messages.kurulusPanel;

const TRUST_TONE: Record<string, StatusTone> = {
  T0: "default",
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};

/**
 * SPRINT F: the organization's desk — who is waiting, who in the team handles
 * what, which universities we work with, candidate check, showcase.
 * MEMBER sees no management controls (invite, unit edit, showcase switch,
 * domain verify); the server enforces the same.
 */
export default function KurulusPanelPage() {
  const params = useParams<{ id: string }>();
  const organizationId = params.id;
  const session = useSession();
  const me = session.data;
  const userId = me?.user.id;
  const isAdmin = orgRoleOf(me?.organizations, organizationId) === "ADMIN";

  const { data: org, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["organization", organizationId] as const,
    queryFn: () => getOrganization(organizationId),
  });

  const members = useQuery({
    queryKey: ["organization-members", organizationId] as const,
    queryFn: () => listOrgMembers(organizationId),
    enabled: Boolean(org),
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
            main={
              <Desk
                organizationId={organizationId}
                isAdmin={isAdmin}
                userId={userId}
                members={members.data ?? []}
                startLink={startLink}
              />
            }
            aside={
              <>
                <CandidateVerifyCard />
                <ShowcaseCard org={org} canManage={isAdmin} />
                <TeamCard
                  organizationId={organizationId}
                  members={members.data ?? []}
                  isLoading={members.isLoading}
                  isError={members.isError}
                  onRetry={() => void members.refetch()}
                  canManage={isAdmin}
                  currentUserId={userId}
                />
                {isAdmin ? <InviteCard organizationId={organizationId} /> : null}
                <DomainCard org={org} canManage={isAdmin} />
              </>
            }
          />
        ) : null}
      </PageBody>
    </AppShell>
  );
}

function Desk({
  organizationId,
  isAdmin,
  userId,
  members,
  startLink,
}: {
  organizationId: string;
  isAdmin: boolean;
  userId: string | undefined;
  members: Parameters<typeof Inbox>[0]["members"];
  startLink: () => string;
}) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["organization-engagements", organizationId] as const,
    queryFn: () => listOrganizationEngagements(organizationId),
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

  const items = data ?? [];
  const summary = summarize(items, userId);

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatTile
          label={`${t.desk.awaitingAll} · ${fill(t.desk.awaitingMine, { count: summary.awaitingMine })}`}
          value={summary.awaitingAll}
          tone="ochre"
          icon="clipboard"
          href="#kurulus-calismalar"
        />
        <StatTile label={t.desk.ongoing} value={summary.ongoing} tone="ink" icon="briefcase" />
        <StatTile label={t.desk.sealed} value={summary.sealed} tone="pine" icon="check" />
        <StatTile
          label={t.desk.universities}
          value={summary.universities}
          tone="ink"
          icon="landmark"
          href="#kurulus-is-birlikleri"
        />
      </div>

      <Inbox
        organizationId={organizationId}
        items={items}
        members={members}
        isAdmin={isAdmin}
        userId={userId}
        startLink={startLink}
        onChanged={() => void refetch()}
      />

      <PartnersSection items={items} />
    </>
  );
}
