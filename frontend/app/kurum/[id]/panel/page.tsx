"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { PageBody, PageHeader } from "@/components/page-layout";
import {
  CopyButton,
  EmptyState,
  Initials,
  PanelGrid,
  PanelIcon,
  PanelSection,
  PanelSkeleton,
  SideCard,
  StatTile,
  StatusPill,
  TimeAgo,
  actionClass,
  formatDate,
  formatTemplate,
} from "@/components/panel-kit";
import { SealMark } from "@/components/brand/brand-mark";
import { Alert } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  approveLinkRequest,
  createReminders,
  getCoordinatorDashboard,
  inviteMember,
  listInstitutionStudents,
  listPendingLinkRequests,
  rejectLinkRequest,
  reportCsvUrl,
  type InstitutionMemberRole,
  type InstitutionStudentItem,
  type PendingItem,
  type PendingLinkRequestItem,
} from "@/lib/api/institutions";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import { useSession } from "@/lib/session/use-session";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { ApprovalSection, AttestationSection, EngagementRow } from "./approval-queue";
import { PartnersSection } from "./partners-section";

const t = messages.kurumPanel;

const REMINDER_TEMPLATE = "evaluation_pending";

const SM = "h-8 px-3 text-[13px]";

function errorMessage(error: unknown): string {
  if (error instanceof SessionExpiredError) return messages.session.expired;
  if (error instanceof ApiError || error instanceof NetworkError) return error.message;
  return messages.errors.generic;
}

type InstitutionRole = "ADMIN" | "COORDINATOR" | "SUPERVISOR";

/** The caller's entry for this institution in /me (name; role once the server sends it). */
function institutionFrom(
  items: unknown[] | undefined,
  id: string
): { name?: string; role: InstitutionRole | null } {
  const match = (items ?? []).find(
    (item): item is { id: string; name?: unknown; role?: unknown } =>
      typeof item === "object" && item !== null && (item as { id?: unknown }).id === id
  );
  const role = match?.role;
  return {
    name: typeof match?.name === "string" ? match.name : undefined,
    role: role === "ADMIN" || role === "COORDINATOR" || role === "SUPERVISOR" ? role : null,
  };
}

export default function KurumPanelPage() {
  const params = useParams<{ id: string }>();
  const institutionId = params.id;
  const session = useSession();

  // AC-6/AC-S1: Cache key must include institutionId for tenant isolation
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["institution-dashboard", institutionId],
    queryFn: () => getCoordinatorDashboard(institutionId),
  });

  // YET-197/IS-10: pending institution link requests (coordinator view)
  const linkRequestsQuery = useQuery({
    queryKey: ["institution-link-requests", institutionId],
    queryFn: () => listPendingLinkRequests(institutionId),
  });

  const studentsQuery = useQuery({
    queryKey: ["institution-students", institutionId],
    queryFn: () => listInstitutionStudents(institutionId),
  });

  // The dashboard has no name; the session lists the caller's institutions and roles.
  // UX only: the server decides every action (a hidden button grants nothing).
  const { name: institutionName, role } = institutionFrom(session.data?.institutions, institutionId);
  const isAdmin = role === "ADMIN";
  // An unknown role (older /me) keeps the previous panel: actions shown, server decides.
  const canInvite = role === null || isAdmin;
  const canApprove = !isAdmin && role !== "SUPERVISOR";
  const joinLink = () => `${window.location.origin}/kurum/${institutionId}/baglan`;

  const students = studentsQuery.data?.items ?? [];
  const verifiedTotal = students.reduce((sum, student) => sum + student.verified_count, 0);

  return (
    <AppShell>
      <PageHeader
        eyebrow={t.title}
        title={institutionName ?? t.title}
        description={
          role ? (
            <span className="flex flex-wrap items-center gap-2">
              <StatusPill tone={isAdmin ? "success" : "default"}>{t.roleLabel[role]}</StatusPill>
              <span>{t.roleDescription[role]}</span>
            </span>
          ) : (
            t.pageDescription
          )
        }
        actions={
          <>
            <CopyButton value={joinLink} label={t.joinLinkButton} />
            <a href={reportCsvUrl(institutionId)} download className={actionClass.outline}>
              <PanelIcon name="clipboard" className="h-4 w-4" />
              {t.reportCsvButton}
            </a>
          </>
        }
      />

      <PageBody>
        {/* AC-1/AC-4/AC-5: Loading state */}
        {isLoading ? <PanelSkeleton tiles={4} /> : null}

        {/* AC-3/AC-4/AC-5: Error state */}
        {isError && error ? (
          <ErrorBanner
            message={errorMessage(error)}
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => refetch()}
          />
        ) : null}

        {/* AC-1/AC-2: Success state */}
        {!isLoading && !isError && data ? (
          <PanelGrid
            main={
              <>
                <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
                  <StatTile
                    label={t.pendingApprovalLabel}
                    value={data.summary.pending_approval}
                    tone="ochre"
                    icon="clock"
                    href="#onay-bekleyen"
                  />
                  <StatTile
                    label={t.pendingEvaluationLabel}
                    value={data.summary.pending_evaluation}
                    tone="ochre"
                    icon="clipboard"
                    href="#degerlendirme-bekleyen"
                  />
                  <StatTile
                    label={t.pendingAttestationLabel}
                    value={data.summary.pending_attestation ?? 0}
                    tone="ink"
                    icon="shield"
                    href="#muhur-bekleyen"
                  />
                  <StatTile label={t.summary.verifiedExperiences} value={verifiedTotal} tone="pine" icon="check" />
                </div>

                <LinkRequestsSection institutionId={institutionId} query={linkRequestsQuery} />

                <ApprovalSection
                  institutionId={institutionId}
                  items={data.pending_approval}
                  canApprove={canApprove}
                />

                <EvaluationSection institutionId={institutionId} items={data.pending_evaluation} />

                <AttestationSection items={data.pending_attestation ?? []} canSeal={canApprove} />

                <PartnersSection institutionId={institutionId} />

                <StudentsSection query={studentsQuery} students={students} />
              </>
            }
            aside={<MembersCard institutionId={institutionId} members={data.members} canInvite={canInvite} />}
          />
        ) : null}
      </PageBody>
    </AppShell>
  );
}

function LinkRequestsSection({
  institutionId,
  query,
}: {
  institutionId: string;
  query: { isLoading: boolean; isError: boolean; isSuccess: boolean; data?: { items: PendingLinkRequestItem[] } };
}) {
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["institution-link-requests", institutionId] });
    // An approved link adds a student; keep the dashboard and student list fresh too.
    queryClient.invalidateQueries({ queryKey: ["institution-dashboard", institutionId] });
    queryClient.invalidateQueries({ queryKey: ["institution-students", institutionId] });
  };

  const onDone = (message: string) => () => {
    setActionError(null);
    setActionMessage(message);
    invalidate();
  };
  const onFail = () => {
    setActionMessage(null);
    setActionError(t.linkRequestActionError);
  };

  const approveMutation = useMutation({
    mutationFn: (requestId: string) => approveLinkRequest(institutionId, requestId),
    onSuccess: onDone(t.linkRequestApprovedMessage),
    onError: onFail,
  });
  const rejectMutation = useMutation({
    mutationFn: (requestId: string) => rejectLinkRequest(institutionId, requestId),
    onSuccess: onDone(t.linkRequestRejectedMessage),
    onError: onFail,
  });
  const isActionPending = approveMutation.isPending || rejectMutation.isPending;
  const items = query.data?.items ?? [];

  return (
    <PanelSection
      icon="userPlus"
      title={t.linkRequestsTitle}
      hint={t.linkRequestsHint}
      count={query.isSuccess ? items.length : undefined}
      flush={items.length > 0}
    >
      {actionError ? (
        <Alert variant="error" className={cn("text-sm", items.length > 0 ? "m-5 mb-0" : "mb-4")}>
          {actionError}
        </Alert>
      ) : null}
      {actionMessage ? (
        <div
          role="status"
          aria-live="polite"
          className={cn(
            "rounded-md border border-success/30 bg-success/10 px-4 py-3 text-sm text-success",
            items.length > 0 ? "m-5 mb-0" : "mb-4"
          )}
        >
          {actionMessage}
        </div>
      ) : null}

      {query.isLoading ? (
        <div aria-hidden="true" className="h-14 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
      ) : query.isError ? (
        <p className="text-sm text-destructive">{t.linkRequestActionError}</p>
      ) : items.length === 0 ? (
        <EmptyState icon="inbox" title={t.emptyLinkRequestsMessage} hint={t.emptyLinkRequestsHint} />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li key={item.id} className="y360-step-in flex flex-wrap items-center gap-3 bg-warning/[0.04] px-5 py-3.5">
              <Initials name={item.talent_full_name} />
              <span className="min-w-0 flex-1">
                <span className="block font-medium text-foreground">{item.talent_full_name}</span>
                <span className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                  {t.requestedAt} · <TimeAgo iso={item.requested_at} />
                </span>
              </span>
              <span className="flex gap-2">
                <button
                  type="button"
                  onClick={() => approveMutation.mutate(item.id)}
                  disabled={isActionPending}
                  className={cn(actionClass.primary, SM)}
                >
                  {t.approveButton}
                </button>
                <button
                  type="button"
                  onClick={() => rejectMutation.mutate(item.id)}
                  disabled={isActionPending}
                  className={cn(actionClass.dangerOutline, SM)}
                >
                  {t.rejectButton}
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </PanelSection>
  );
}

function EvaluationSection({ institutionId, items }: { institutionId: string; items: PendingItem[] }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [reminderError, setReminderError] = useState<string | null>(null);
  const [reminderMessage, setReminderMessage] = useState<string | null>(null);

  const reminderMutation = useMutation({
    mutationFn: () => createReminders(institutionId, selected, REMINDER_TEMPLATE),
    onSuccess: () => {
      setReminderError(null);
      setReminderMessage(t.reminderSuccessMessage);
      setSelected([]);
    },
    onError: () => {
      setReminderMessage(null);
      setReminderError(t.reminderErrorMessage);
    },
  });

  const handleSendReminders = () => {
    setReminderMessage(null);
    if (selected.length === 0) {
      setReminderError(t.reminderNoneSelectedMessage);
      return;
    }
    setReminderError(null);
    reminderMutation.mutate();
  };

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((existing) => existing !== id) : [...prev, id]));
  const allSelected = selected.length > 0 && selected.length === items.length;

  return (
    <PanelSection
      id="degerlendirme-bekleyen"
      icon="clipboard"
      title={t.pendingEvaluationTitle}
      hint={t.pendingEvaluationHint}
      flush={items.length > 0}
      actions={
        items.length > 0 ? (
          <button
            type="button"
            onClick={handleSendReminders}
            disabled={reminderMutation.isPending}
            className={cn(actionClass.outline, "w-full sm:w-auto")}
          >
            <PanelIcon name="bell" className="h-4 w-4" />
            {reminderMutation.isPending ? t.reminderSendingButton : t.reminderSendButton}
          </button>
        ) : undefined
      }
    >
      {items.length === 0 ? (
        <EmptyState icon="clipboard" title={t.emptyPendingEvaluationMessage} hint={t.emptyPendingEvaluationHint} />
      ) : (
        <>
          <div className="flex items-center justify-between gap-3 border-b border-border bg-muted/50 px-5 py-2.5">
            <label className="flex cursor-pointer items-center gap-3 text-[13px] font-medium text-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 accent-success"
                checked={allSelected}
                onChange={(e) => setSelected(e.target.checked ? items.map((item) => item.id) : [])}
              />
              {t.reminderSelectAllLabel}
            </label>
            {selected.length > 0 ? (
              <span className="font-mono text-xs text-success">
                {formatTemplate(t.selectedCount, { n: selected.length })}
              </span>
            ) : null}
          </div>

          {reminderError ? (
            <Alert variant="error" className="m-5 mb-0 text-sm">
              {reminderError}
            </Alert>
          ) : null}
          {reminderMessage ? (
            <div
              role="status"
              aria-live="polite"
              className="m-5 mb-0 rounded-md border border-success/30 bg-success/10 px-4 py-3 text-sm text-success"
            >
              {reminderMessage}
            </div>
          ) : null}

          <ul className="divide-y divide-border">
            {items.map((item) => {
              const isSelected = selected.includes(item.id);
              return (
                <EngagementRow
                    key={item.id}
                    item={item}
                    selected={isSelected}
                    status="PENDING_EVALUATION"
                    date={item.ended_on ? formatTemplate(t.endedOn, { date: formatDate(item.ended_on) }) : null}
                    leading={
                      <input
                        type="checkbox"
                        className="h-4 w-4 shrink-0 accent-success"
                        checked={isSelected}
                        onChange={() => toggle(item.id)}
                        aria-label={item.title}
                      />
                    }
                  />
              );
            })}
          </ul>
        </>
      )}
    </PanelSection>
  );
}

function StudentsSection({
  query,
  students,
}: {
  query: { isLoading: boolean; isError: boolean; refetch: () => unknown };
  students: InstitutionStudentItem[];
}) {
  return (
    <PanelSection
      id="ogrenciler"
      icon="users"
      title={t.studentsTitle}
      hint={t.studentsHint}
      count={query.isLoading || query.isError ? undefined : students.length}
      flush={students.length > 0}
    >
      {query.isLoading ? (
        <div aria-hidden="true" className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
      ) : query.isError ? (
        <div className="flex items-center justify-between gap-4 text-sm text-destructive">
          <span>{t.studentsError}</span>
          <button type="button" onClick={() => void query.refetch()} className={cn(actionClass.neutral, SM)}>
            {messages.errors.retry}
          </button>
        </div>
      ) : students.length === 0 ? (
        <EmptyState icon="users" title={t.studentsEmptyTitle} hint={t.studentsEmptyHint} />
      ) : (
        <ul className="divide-y divide-border">
          {students.map((student) => {
            const meta = [
              student.department,
              student.study_year ? formatTemplate(t.studyYear, { n: student.study_year }) : null,
            ].filter(Boolean);
            return (
              <li key={student.talent_profile_id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                <Initials name={student.full_name} />
                <span className="min-w-[60%] flex-1 sm:min-w-0">
                  <span className="flex items-center gap-2">
                    <span className="truncate font-medium text-foreground">{student.full_name}</span>
                    {student.verified_count > 0 ? <SealMark className="h-4 w-4 shrink-0" /> : null}
                  </span>
                  {meta.length > 0 ? (
                    <span className="mt-0.5 block truncate text-xs text-muted-foreground">{meta.join(" · ")}</span>
                  ) : null}
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  {student.total_count === 0 ? (
                    <span className="text-xs text-muted-foreground">{t.noEngagements}</span>
                  ) : (
                    <>
                      <StatusPill tone={student.verified_count > 0 ? "success" : "default"}>
                        {formatTemplate(t.verifiedCount, { n: student.verified_count })}
                      </StatusPill>
                      {student.in_progress_count > 0 ? (
                        <StatusPill tone="warning">
                          {formatTemplate(t.inProgressCount, { n: student.in_progress_count })}
                        </StatusPill>
                      ) : null}
                    </>
                  )}
                  {student.public_slug ? (
                    <a
                      href={`/p/${student.public_slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(actionClass.outline, SM)}
                    >
                      {t.viewProfile}
                      <span className="sr-only"> {t.newTab}</span>
                      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                        <path d="M7 17 17 7M8 7h9v9" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </a>
                  ) : null}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </PanelSection>
  );
}

function MembersCard({
  institutionId,
  members,
  canInvite,
}: {
  institutionId: string;
  members: { user_id: string; email: string; role: string }[];
  canInvite: boolean;
}) {
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<InstitutionMemberRole>("COORDINATOR");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);

  const inviteMutation = useMutation({
    mutationFn: () => inviteMember(institutionId, inviteEmail.trim(), inviteRole),
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
    <SideCard title={t.membersTitle} hint={t.membersHint}>
      {members.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border px-3 py-2.5 text-sm text-muted-foreground">
          {t.emptyMembersMessage}
        </p>
      ) : (
        <ul className="space-y-2">
          {members.map((member) => (
            <li key={member.user_id} className="flex items-center justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-mono text-[13px] text-foreground" title={member.email}>
                {member.email}
              </span>
              <StatusPill tone={member.role === "ADMIN" ? "success" : "default"}>
                {(t.roleLabel as Record<string, string>)[member.role] ?? member.role}
              </StatusPill>
            </li>
          ))}
        </ul>
      )}

      {canInvite ? (
        <form onSubmit={handleInviteSubmit} className="mt-5 space-y-3 rounded-lg border border-border bg-sand/50 p-4">
          <p className="text-sm font-semibold text-foreground">{t.inviteMemberTitle}</p>
          <div>
            <Label htmlFor="invite-email" className="text-xs">
              {t.inviteEmailLabel}
            </Label>
            <Input
              id="invite-email"
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="invite-role" className="text-xs">
              {t.inviteRoleLabel}
            </Label>
            <select
              id="invite-role"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as InstitutionMemberRole)}
              className="block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25"
            >
              <option value="COORDINATOR">{t.memberRole.COORDINATOR}</option>
              <option value="ADMIN">{t.memberRole.ADMIN}</option>
            </select>
          </div>
          <button type="submit" disabled={inviteMutation.isPending} className={cn(actionClass.neutral, "w-full bg-card")}>
            <PanelIcon name="userPlus" className="h-4 w-4" />
            {inviteMutation.isPending ? t.invitingButton : t.inviteButton}
          </button>

          {inviteError ? (
            <Alert variant="error" className="text-sm">
              {inviteError}
            </Alert>
          ) : null}
          {inviteMessage ? (
            <div
              role="status"
              aria-live="polite"
              className="rounded-md border border-success/30 bg-success/10 px-3 py-2.5 text-sm text-success"
            >
              {inviteMessage}
            </div>
          ) : null}
        </form>
      ) : null}
    </SideCard>
  );
}
