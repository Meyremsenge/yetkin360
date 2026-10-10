"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import * as adminApi from "@/lib/api/admin";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

const CONFIDENCE_BADGE: Record<string, string> = {
  LOW: "bg-slate-100 text-slate-700",
  MEDIUM: "bg-amber-100 text-amber-800",
  HIGH: "bg-red-100 text-red-800",
};

/**
 * PLAN 3.54: AI'nin ürettiği fraud flag'leri (attestation.statement üzerinden)
 * admin'in inceleyip CONFIRMED/DISMISSED ile karara bağladığı ekran.
 * AI hiçbir hesabı etkilemez — bu ekran yalnız bir öneri listesi, karar admin'de.
 */
export default function SahtekarlikIsaretleriPage() {
  const queryClient = useQueryClient();
  const QUEUE_KEY = ["admin", "fraud-queue"] as const;

  const { data: queue, isLoading, isError, error } = useQuery({
    queryKey: QUEUE_KEY,
    queryFn: () => adminApi.getFraudQueue(),
  });

  const resolve = useMutation({
    mutationFn: (vars: { flagId: string; outcome: "CONFIRMED" | "DISMISSED" }) =>
      adminApi.resolveFraudFlag(vars.flagId, vars.outcome),
    onSuccess: (resolved) => {
      if (!resolved) return;
      queryClient.setQueryData(QUEUE_KEY, (prev: adminApi.FraudQueueResponse | undefined) => {
        if (!prev) return prev;
        return { items: prev.items.filter((f) => f.id !== resolved.id) };
      });
    },
  });

  return (
    <AppShell>
      <main className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">{messages.adminFraudQueue.title}</h1>
        <p className="text-sm text-slate-600 mb-6">{messages.adminFraudQueue.description}</p>

        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error instanceof ApiError && error.status === 404
              ? messages.adminFraudQueue.notFound
              : error instanceof NetworkError && error.kind === "timeout"
                ? messages.errors.timeout
                : messages.errors.generic}
          </div>
        ) : !queue || queue.items.length === 0 ? (
          <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.adminFraudQueue.empty}
          </div>
        ) : (
          <>
            {resolve.isError && (
              <div role="alert" className="mb-4 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
                {resolve.error instanceof ApiError && resolve.error.status === 409
                  ? messages.adminFraudQueue.notPending
                  : messages.errors.generic}
              </div>
            )}

            <ul className="space-y-4">
              {queue.items.map((flag) => (
                <li key={flag.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CONFIDENCE_BADGE[flag.confidence]}`}>
                          {messages.adminFraudQueue.confidenceLabel[flag.confidence]}
                        </span>
                        <span className="text-xs text-slate-500">{flag.model}</span>
                        <span className="text-xs text-slate-400">
                          {new Date(flag.created_at).toLocaleString("tr-TR")}
                        </span>
                      </div>
                      <p className="text-sm text-slate-800">{flag.reason}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {messages.adminFraudQueue.headers.subject}: {flag.subject_type} #{flag.subject_id.slice(0, 8)}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        onClick={() => resolve.mutate({ flagId: flag.id, outcome: "CONFIRMED" })}
                        disabled={resolve.isPending}
                        aria-label={`${messages.adminFraudQueue.form.confirm} ${flag.id}`}
                        className="px-3 py-1 bg-red-700 text-white text-xs rounded-md hover:bg-red-800 disabled:bg-slate-300 disabled:cursor-not-allowed"
                      >
                        {messages.adminFraudQueue.form.confirm}
                      </button>
                      <button
                        onClick={() => resolve.mutate({ flagId: flag.id, outcome: "DISMISSED" })}
                        disabled={resolve.isPending}
                        aria-label={`${messages.adminFraudQueue.form.dismiss} ${flag.id}`}
                        className="px-3 py-1 border border-slate-300 text-slate-700 text-xs rounded-md hover:bg-slate-100 disabled:bg-slate-100 disabled:cursor-not-allowed"
                      >
                        {messages.adminFraudQueue.form.dismiss}
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </main>
    </AppShell>
  );
}
