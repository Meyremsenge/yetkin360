"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { Button } from "@/components/ui/button";
import {
  approveLinkRequest,
  getCoordinatorDashboard,
  listPendingLinkRequests,
  rejectLinkRequest,
} from "@/lib/api/institutions";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export default function KurumPanelPage() {
  const params = useParams<{ id: string }>();
  const institutionId = params.id;
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

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
                <ul className="space-y-2">
                  {data.pending_evaluation.map((item) => (
                    <li
                      key={item.id}
                      className="bg-white p-4 rounded-md border border-slate-200 text-sm"
                    >
                      <div className="font-medium text-slate-900">{item.title}</div>
                      {item.ended_on && (
                        <div className="text-xs text-slate-600 mt-1">
                          {new Date(item.ended_on).toLocaleString("tr-TR")}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
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
