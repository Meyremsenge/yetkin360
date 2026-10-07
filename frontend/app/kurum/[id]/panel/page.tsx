"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  approveLinkRequest,
  createReminders,
  getCoordinatorDashboard,
  inviteMember,
  listPendingLinkRequests,
  rejectLinkRequest,
  type InstitutionMemberRole,
} from "@/lib/api/institutions";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

const REMINDER_TEMPLATE = "evaluation_pending";

export default function KurumPanelPage() {
  const params = useParams<{ id: string }>();
  const institutionId = params.id;
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // YET-202/ENT-01: üye davet formu
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<InstitutionMemberRole>("COORDINATOR");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);

  // YET-202/ENT-01: toplu hatırlatma seçimi
  const [selectedEngagementIds, setSelectedEngagementIds] = useState<string[]>([]);
  const [reminderError, setReminderError] = useState<string | null>(null);
  const [reminderMessage, setReminderMessage] = useState<string | null>(null);

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

  const invalidateLinkRequests = () => {
    queryClient.invalidateQueries({ queryKey: ["institution-link-requests", institutionId] });
    // Approval can affect dashboard membership-adjacent state; keep it fresh too.
    queryClient.invalidateQueries({ queryKey: ["institution-dashboard", institutionId] });
  };

  const approveMutation = useMutation({
    mutationFn: (requestId: string) => approveLinkRequest(institutionId, requestId),
    onSuccess: () => {
      setActionError(null);
      setActionMessage(messages.kurumPanel.linkRequestApprovedMessage);
      invalidateLinkRequests();
    },
    onError: () => {
      setActionMessage(null);
      setActionError(messages.kurumPanel.linkRequestActionError);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: string) => rejectLinkRequest(institutionId, requestId),
    onSuccess: () => {
      setActionError(null);
      setActionMessage(messages.kurumPanel.linkRequestRejectedMessage);
      invalidateLinkRequests();
    },
    onError: () => {
      setActionMessage(null);
      setActionError(messages.kurumPanel.linkRequestActionError);
    },
  });

  const isActionPending = approveMutation.isPending || rejectMutation.isPending;

  const inviteMutation = useMutation({
    mutationFn: () => inviteMember(institutionId, inviteEmail.trim(), inviteRole),
    onSuccess: () => {
      setInviteError(null);
      setInviteMessage(messages.kurumPanel.inviteSuccessMessage);
      setInviteEmail("");
    },
    onError: () => {
      setInviteMessage(null);
      setInviteError(messages.kurumPanel.inviteErrorMessage);
    },
  });

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInviteMessage(null);
    setInviteError(null);
    inviteMutation.mutate();
  };

  const toggleEngagementSelected = (id: string) => {
    setSelectedEngagementIds((prev) =>
      prev.includes(id) ? prev.filter((existing) => existing !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = (allIds: string[], checked: boolean) => {
    setSelectedEngagementIds(checked ? allIds : []);
  };

  const reminderMutation = useMutation({
    mutationFn: () => createReminders(institutionId, selectedEngagementIds, REMINDER_TEMPLATE),
    onSuccess: () => {
      setReminderError(null);
      setReminderMessage(messages.kurumPanel.reminderSuccessMessage);
      setSelectedEngagementIds([]);
    },
    onError: () => {
      setReminderMessage(null);
      setReminderError(messages.kurumPanel.reminderErrorMessage);
    },
  });

  const handleSendReminders = () => {
    setReminderMessage(null);
    if (selectedEngagementIds.length === 0) {
      setReminderError(messages.kurumPanel.reminderNoneSelectedMessage);
      return;
    }
    setReminderError(null);
    reminderMutation.mutate();
  };

  return (
    <AppShell>
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.kurumPanel.title}</h1>

        {/* AC-1/AC-4/AC-5: Loading state */}
        {isLoading && <p className="text-slate-600">{messages.shell.loading}</p>}

        {/* AC-3/AC-4/AC-5: Error state */}
        {isError && error && (
          <ErrorBanner
            message={
              error instanceof SessionExpiredError
                ? messages.session.expired
                : error instanceof ApiError
                  ? error.message
                  : error instanceof NetworkError
                    ? error.message
                    : messages.errors.generic
            }
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => refetch()}
          />
        )}

        {/* AC-1/AC-2: Success state */}
        {!isLoading && !isError && data && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-4 mb-8">
              {/* Pending approval card */}
              <div className="bg-slate-50 rounded-md border border-slate-200 p-4">
                <div className="text-sm text-slate-600 font-medium mb-2">
                  {messages.kurumPanel.pendingApprovalLabel}
                </div>
                <div className="text-3xl font-bold text-slate-900">
                  {data.summary.pending_approval}
                </div>
              </div>

              {/* Pending evaluation card */}
              <div className="bg-slate-50 rounded-md border border-slate-200 p-4">
                <div className="text-sm text-slate-600 font-medium mb-2">
                  {messages.kurumPanel.pendingEvaluationLabel}
                </div>
                <div className="text-3xl font-bold text-slate-900">
                  {data.summary.pending_evaluation}
                </div>
              </div>
            </div>

            {/* Pending approval list */}
            <section className="mb-8">
              <h2 className="text-lg font-bold mb-3">
                {messages.kurumPanel.pendingApprovalTitle}
              </h2>
              {data.pending_approval.length === 0 ? (
                <p className="text-sm text-slate-600 bg-slate-50 rounded-md border border-slate-200 p-4">
                  {messages.kurumPanel.emptyPendingApprovalMessage}
                </p>
              ) : (
                <ul className="space-y-2">
                  {data.pending_approval.map((item) => (
                    <li
                      key={item.id}
                      className="bg-white p-4 rounded-md border border-slate-200 text-sm"
                    >
                      <div className="font-medium text-slate-900">{item.title}</div>
                      {item.started_on && (
                        <div className="text-xs text-slate-600 mt-1">
                          {new Date(item.started_on).toLocaleString("tr-TR")}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Pending evaluation list */}
            <section>
              <h2 className="text-lg font-bold mb-3">
                {messages.kurumPanel.pendingEvaluationTitle}
              </h2>
              {data.pending_evaluation.length === 0 ? (
                <p className="text-sm text-slate-600 bg-slate-50 rounded-md border border-slate-200 p-4">
                  {messages.kurumPanel.emptyPendingEvaluationMessage}
                </p>
              ) : (
                <>
                  <label className="flex items-center gap-2 text-sm text-slate-700 mb-2">
                    <input
                      type="checkbox"
                      checked={
                        selectedEngagementIds.length > 0 &&
                        selectedEngagementIds.length === data.pending_evaluation.length
                      }
                      onChange={(e) =>
                        toggleSelectAll(data.pending_evaluation.map((item) => item.id), e.target.checked)
                      }
                    />
                    {messages.kurumPanel.reminderSelectAllLabel}
                  </label>
                  <ul className="space-y-2">
                    {data.pending_evaluation.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-start gap-3 bg-white p-4 rounded-md border border-slate-200 text-sm"
                      >
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={selectedEngagementIds.includes(item.id)}
                          onChange={() => toggleEngagementSelected(item.id)}
                          aria-label={item.title}
                        />
                        <div>
                          <div className="font-medium text-slate-900">{item.title}</div>
                          {item.ended_on && (
                            <div className="text-xs text-slate-600 mt-1">
                              {new Date(item.ended_on).toLocaleString("tr-TR")}
                            </div>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>

                  <div className="mt-3">
                    <Button onClick={handleSendReminders} disabled={reminderMutation.isPending}>
                      {reminderMutation.isPending
                        ? messages.kurumPanel.reminderSendingButton
                        : messages.kurumPanel.reminderSendButton}
                    </Button>
                  </div>

                  {reminderError && (
                    <div
                      role="alert"
                      aria-live="polite"
                      className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
                    >
                      {reminderError}
                    </div>
                  )}
                  {reminderMessage && (
                    <div
                      role="status"
                      aria-live="polite"
                      className="mt-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-700"
                    >
                      {reminderMessage}
                    </div>
                  )}
                </>
              )}
            </section>

            {/* YET-202/ENT-01: Üyeler listesi + davet formu */}
            <section className="mt-8">
              <h2 className="text-lg font-bold mb-3">{messages.kurumPanel.membersTitle}</h2>

              {data.members.length === 0 ? (
                <p className="text-sm text-slate-600 bg-slate-50 rounded-md border border-slate-200 p-4 mb-4">
                  {messages.kurumPanel.emptyMembersMessage}
                </p>
              ) : (
                <ul className="space-y-2 mb-4">
                  {data.members.map((member) => (
                    <li
                      key={member.user_id}
                      className="flex items-center justify-between bg-white p-4 rounded-md border border-slate-200 text-sm"
                    >
                      <span className="text-slate-900">{member.email}</span>
                      <span className="text-xs text-slate-600">
                        {messages.kurumPanel.memberRole[member.role as "ADMIN" | "COORDINATOR"] ?? member.role}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <form
                onSubmit={handleInviteSubmit}
                className="bg-slate-50 p-4 rounded-md border border-slate-200"
              >
                <h3 className="text-sm font-bold mb-3">{messages.kurumPanel.inviteMemberTitle}</h3>

                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <Label htmlFor="invite-email">{messages.kurumPanel.inviteEmailLabel}</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="invite-role">{messages.kurumPanel.inviteRoleLabel}</Label>
                    <select
                      id="invite-role"
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value as InstitutionMemberRole)}
                      className="block px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                    >
                      <option value="COORDINATOR">{messages.kurumPanel.memberRole.COORDINATOR}</option>
                      <option value="ADMIN">{messages.kurumPanel.memberRole.ADMIN}</option>
                    </select>
                  </div>

                  <Button type="submit" disabled={inviteMutation.isPending}>
                    {inviteMutation.isPending
                      ? messages.kurumPanel.invitingButton
                      : messages.kurumPanel.inviteButton}
                  </Button>
                </div>

                {inviteError && (
                  <div
                    role="alert"
                    aria-live="polite"
                    className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
                  >
                    {inviteError}
                  </div>
                )}
                {inviteMessage && (
                  <div
                    role="status"
                    aria-live="polite"
                    className="mt-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-700"
                  >
                    {inviteMessage}
                  </div>
                )}
              </form>
            </section>

            {/* YET-197/IS-10: Pending institution link requests */}
            <section className="mt-8">
              <h2 className="text-lg font-bold mb-3">{messages.kurumPanel.linkRequestsTitle}</h2>

              {actionError && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="mb-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
                >
                  {actionError}
                </div>
              )}
              {actionMessage && (
                <div
                  role="status"
                  aria-live="polite"
                  className="mb-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-600"
                >
                  {actionMessage}
                </div>
              )}

              {linkRequestsQuery.isLoading ? (
                <p className="text-slate-600">{messages.shell.loading}</p>
              ) : linkRequestsQuery.isError ? (
                <p className="text-sm text-red-600">{messages.kurumPanel.linkRequestActionError}</p>
              ) : linkRequestsQuery.data && linkRequestsQuery.data.items.length === 0 ? (
                <p className="text-sm text-slate-600 bg-slate-50 rounded-md border border-slate-200 p-4">
                  {messages.kurumPanel.emptyLinkRequestsMessage}
                </p>
              ) : (
                <ul className="space-y-2">
                  {linkRequestsQuery.data?.items.map((item) => (
                    <li
                      key={item.id}
                      className="flex items-center justify-between bg-white p-4 rounded-md border border-slate-200 text-sm"
                    >
                      <div className="font-medium text-slate-900">{item.talent_full_name}</div>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => approveMutation.mutate(item.id)}
                          disabled={isActionPending}
                        >
                          {messages.kurumPanel.approveButton}
                        </Button>
                        <Button
                          onClick={() => rejectMutation.mutate(item.id)}
                          disabled={isActionPending}
                          className="bg-red-600 hover:bg-red-700"
                        >
                          {messages.kurumPanel.rejectButton}
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
