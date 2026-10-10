"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminPagination } from "@/components/admin-pagination";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import {
  EmptyState,
  StatusPill,
  actionClass,
  formatDate,
  formatTemplate,
} from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { UpheldComplaintBadge } from "@/components/upheld-complaint-badge";
import * as adminApi from "@/lib/api/admin";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const q = messages.adminVerificationQueue;
const TRUST_LABELS = messages.kurulusPanel.trustLevel as Record<string, string>;
const LEVELS = ["T0", "T1", "T2", "T3"] as const;
const LEVEL_TONE: Record<string, "default" | "warning" | "success"> = {
  T0: "default",
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};
const SM = "h-8 px-3 text-[13px]";

export default function DogrulamaKuyruguPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const limit = adminApi.ADMIN_PAGE_SIZE;
  const QUEUE_KEY = ["admin", "verification-queue", { limit, offset }] as const;

  const [selectedLevels, setSelectedLevels] = useState<Record<string, string>>({});
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: queue, isLoading, isError, error, refetch } = useQuery({
    queryKey: QUEUE_KEY,
    queryFn: () => adminApi.getVerificationQueue({ limit, offset }),
  });

  const { mutate: updateLevel, isPending: isUpdating } = useMutation({
    mutationFn: (vars: { orgId: string; level: string }) =>
      adminApi.updateVerificationLevel(vars.orgId, vars.level),
    onSuccess: (updated: adminApi.Organization | undefined) => {
      if (!updated) return;
      setMutationError(null);
      setSuccessMessage(q.updated);
      // Brif §19: işlenen satır kaybolur — onaylanmış kuruluş artık kuyruğun
      // eligibility kriterini (T2 + legal_id dolu) karşılamayabilir, ayrıca
      // sunucu yanıtı (updated) legal_id/domain döndürmüyor; satırı o eksik
      // veriyle yerinde güncellemek yerine reject ile tutarlı şekilde kaldırıyoruz.
      queryClient.setQueryData(QUEUE_KEY, (prev: adminApi.VerificationQueueResponse | undefined) => {
        if (!prev) return prev;
        return { ...prev, items: prev.items.filter((org) => org.id !== updated.id) };
      });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setMutationError(err.status === 404 ? q.notFound : messages.errors.generic);
      } else if (err instanceof NetworkError) {
        setMutationError(err.kind === "timeout" ? messages.errors.timeout : messages.errors.network);
      }
    },
  });

  const { mutate: reject, isPending: isRejecting } = useMutation({
    mutationFn: (orgId: string) => adminApi.rejectVerification(orgId),
    onSuccess: (rejected: adminApi.Organization | undefined) => {
      if (!rejected) return;
      setMutationError(null);
      setSuccessMessage(q.rejected);
      queryClient.setQueryData(QUEUE_KEY, (prev: adminApi.VerificationQueueResponse | undefined) => {
        if (!prev) return prev;
        return { ...prev, items: prev.items.filter((org) => org.id !== rejected.id) };
      });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setMutationError(
          err.status === 404 ? q.notFound : err.status === 409 ? q.notPending : messages.errors.generic
        );
      } else if (err instanceof NetworkError) {
        setMutationError(err.kind === "timeout" ? messages.errors.timeout : messages.errors.network);
      }
    },
  });

  const handleLevelChange = (orgId: string, newLevel: string) => {
    setSelectedLevels((prev) => ({ ...prev, [orgId]: newLevel }));
    setMutationError(null);
  };

  const handleSubmit = (orgId: string) => {
    const level = selectedLevels[orgId];
    if (!level) return;
    updateLevel({ orgId, level });
  };

  const count = queue?.items.length ?? 0;

  return (
    <AppShell>
      <main>
        <PageHeader
          eyebrow={messages.shell.groupAdmin}
          title={q.title}
          description={
            <span className="flex flex-col items-start gap-2">
              <span>{q.description}</span>
              {queue ? (
                <StatusPill tone={count > 0 ? "warning" : "default"}>
                  {formatTemplate(q.pendingCount, { n: count })}
                </StatusPill>
              ) : null}
            </span>
          }
        />

        <PageBody>
          <div className="space-y-6">
            {
              isLoading ? (
                <div role="status">
                  <span className="sr-only">{messages.shell.loading}</span>
                  <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
                </div>
              ) : isError ? (
                <Alert variant="error" className="text-sm">
                  {error instanceof ApiError && error.status === 404
                    ? q.notFound
                    : error instanceof NetworkError && error.kind === "timeout"
                      ? messages.errors.timeout
                      : messages.errors.generic}
                  <button
                    type="button"
                    onClick={() => refetch()}
                    className="ml-3 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
                  >
                    {messages.errors.retry}
                  </button>
                </Alert>
              ) : !queue || queue.items.length === 0 ? (
                <section className="rounded-xl border border-border bg-card p-5">
                  <EmptyState icon="shield" title={q.empty} hint={q.emptyHint} />
                </section>
              ) : (
                <>
                  {successMessage ? (
                    <div
                      role="status"
                      // Stock green scale is mapped to pine in tailwind.config.ts.
                      className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700"
                    >
                      {successMessage}
                    </div>
                  ) : null}

                  {mutationError ? (
                    <Alert variant="error" className="text-sm">
                      {mutationError}
                    </Alert>
                  ) : null}

                  <div className="overflow-x-auto rounded-xl border border-border bg-card">
                    <table className="w-full min-w-[760px] border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/70 text-left text-xs text-muted-foreground">
                          <th className="px-4 py-3 font-medium">{q.headers.name}</th>
                          <th className="px-4 py-3 font-medium">{q.headers.legalId}</th>
                          <th className="px-4 py-3 font-medium">{q.headers.domain}</th>
                          <th className="px-4 py-3 font-medium">{q.headers.verificationLevel}</th>
                          <th className="px-4 py-3 font-medium">{q.headers.createdAt}</th>
                          <th className="px-4 py-3 text-right font-medium">{q.actionsHeader}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {queue.items.map((org) => {
                          const level = selectedLevels[org.id] || org.verification_level;
                          return (
                            <tr key={org.id} className="border-b border-border last:border-0 hover:bg-background">
                              <td className="px-4 py-3.5 font-medium text-foreground">
                                <span className="flex flex-wrap items-center gap-2">
                                  <span>{org.name}</span>
                                  <UpheldComplaintBadge count={org.upheld_complaint_count} />
                                </span>
                              </td>
                              <td className="px-4 py-3.5 whitespace-nowrap font-mono text-[13px] text-muted-foreground">
                                {org.legal_id || "-"}
                              </td>
                              <td className="px-4 py-3.5 whitespace-nowrap font-mono text-[13px] text-muted-foreground">
                                {org.domain || "-"}
                              </td>
                              <td className="px-4 py-3.5">
                                <div className="flex flex-col items-start gap-1.5">
                                  <select
                                    value={level}
                                    onChange={(e) => handleLevelChange(org.id, e.target.value)}
                                    disabled={isUpdating}
                                    aria-label={formatTemplate(q.levelSelectAria, { name: org.name })}
                                    className="h-8 rounded-md border border-border bg-card px-2 font-mono text-[13px] text-foreground focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25"
                                  >
                                    {LEVELS.map((value) => (
                                      <option key={value} value={value}>
                                        {value}
                                      </option>
                                    ))}
                                  </select>
                                  <StatusPill tone={LEVEL_TONE[level] ?? "default"}>
                                    {TRUST_LABELS[level] ?? level}
                                  </StatusPill>
                                </div>
                              </td>
                              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs text-muted-foreground">
                                {org.verified_at ? formatDate(org.verified_at) : "-"}
                              </td>
                              <td className="px-4 py-3.5">
                                <div className="flex justify-end gap-2">
                                  <button
                                    onClick={() => handleSubmit(org.id)}
                                    disabled={
                                      isUpdating || isRejecting || selectedLevels[org.id] === org.verification_level
                                    }
                                    aria-label={`Onayla ${org.name}`}
                                    className={cn(actionClass.primary, SM)}
                                  >
                                    {q.form.confirm}
                                  </button>
                                  <button
                                    onClick={() => reject(org.id)}
                                    disabled={isUpdating || isRejecting}
                                    aria-label={`Reddet ${org.name}`}
                                    className={cn(actionClass.dangerOutline, SM)}
                                  >
                                    {q.form.reject}
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <AdminPagination
                    offset={offset}
                    limit={limit}
                    hasMore={queue.has_more}
                    disabled={isUpdating || isRejecting}
                    onChange={setOffset}
                  />
                </>
              )
            }
            <section className="rounded-xl border border-border bg-card p-5">
              <p className="font-serif text-lg font-semibold text-foreground">{q.levelsTitle}</p>
              <p className="mt-1 text-[13px] text-muted-foreground">{q.levelsHint}</p>
              <dl className="mt-4 flex flex-wrap gap-x-5 gap-y-2.5">
                {Object.entries(TRUST_LABELS).map(([value, label]) => (
                  <div key={value} className="flex items-center gap-2">
                    <dt className="font-mono text-[13px] text-muted-foreground">{value}</dt>
                    <dd>
                      <StatusPill tone={LEVEL_TONE[value] ?? "default"}>{label}</StatusPill>
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>
        </PageBody>
      </main>
    </AppShell>
  );
}
