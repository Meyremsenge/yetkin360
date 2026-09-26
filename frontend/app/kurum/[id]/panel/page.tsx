"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { getCoordinatorDashboard } from "@/lib/api/institutions";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export default function KurumPanelPage() {
  const params = useParams<{ id: string }>();
  const institutionId = params.id;

  // AC-6/AC-S1: Cache key must include institutionId for tenant isolation
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["institution-dashboard", institutionId],
    queryFn: () => getCoordinatorDashboard(institutionId),
  });

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
          </>
        )}
      </div>
    </AppShell>
  );
}
