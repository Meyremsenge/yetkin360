"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminPagination } from "@/components/admin-pagination";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import {
  EmptyState,
  PanelIcon,
  PanelSection,
  StatTile,
  StatusPill,
  TimeAgo,
  actionClass,
  type IconName,
} from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import * as adminApi from "@/lib/api/admin";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const f = messages.adminFraudQueue;

const CONFIDENCE_TONE: Record<string, "default" | "warning" | "error"> = {
  LOW: "default",
  MEDIUM: "warning",
  HIGH: "error",
};

const CONFIDENCE_BAR: Record<string, string> = {
  LOW: "bg-border",
  MEDIUM: "bg-warning",
  HIGH: "bg-destructive",
};

const CONFIDENCE_ORDER: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

const SUBJECT_ICON: Record<string, IconName> = {
  ATTESTATION: "check",
  ORGANIZATION: "building",
  INSTITUTION: "landmark",
};

// fraud_flags.model değeri: backend'deki fraud_signals.RULES_MODEL ile aynı.
const RULES_MODEL = "rules-v1";

const signalLabels: Record<string, string> = f.signalLabel;

const SM = "h-8 px-3 text-[13px]";

/**
 * PLAN 3.54 / 3.56: tanıklık, kuruluş ve kurum onayları için üretilen
 * işaretleri admin'in inceleyip CONFIRMED/DISMISSED ile karara bağladığı ekran.
 * İşaretleri sabit kurallar ve AI üretir; hiçbiri bir hesabı etkilemez — bu
 * ekran yalnız bir öneri listesi, karar admin'de.
 */
export default function SahtekarlikIsaretleriPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const limit = adminApi.ADMIN_PAGE_SIZE;
  const QUEUE_KEY = ["admin", "fraud-queue", { limit, offset }] as const;

  const { data: queue, isLoading, isError, error, refetch } = useQuery({
    queryKey: QUEUE_KEY,
    queryFn: () => adminApi.getFraudQueue({ limit, offset }),
  });

  const resolve = useMutation({
    mutationFn: (vars: { flagId: string; outcome: "CONFIRMED" | "DISMISSED" }) =>
      adminApi.resolveFraudFlag(vars.flagId, vars.outcome),
    onSuccess: (resolved) => {
      if (!resolved) return;
      queryClient.setQueryData(QUEUE_KEY, (prev: adminApi.FraudQueueResponse | undefined) => {
        if (!prev) return prev;
        return { ...prev, items: prev.items.filter((item) => item.id !== resolved.id) };
      });
    },
  });

  const items = [...(queue?.items ?? [])].sort(
    (a, b) => (CONFIDENCE_ORDER[a.confidence] ?? 9) - (CONFIDENCE_ORDER[b.confidence] ?? 9)
  );

  return (
    <AppShell>
      <main>
        <PageHeader eyebrow={messages.shell.groupAdmin} title={f.title} description={f.description} />

        <PageBody className="space-y-6">
          {isLoading ? (
            <div role="status">
              <span className="sr-only">{messages.shell.loading}</span>
              <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
            </div>
          ) : isError ? (
            <Alert variant="error" className="text-sm">
              {error instanceof ApiError && error.status === 404
                ? f.notFound
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
          ) : items.length === 0 ? (
            <section className="rounded-xl border border-border bg-card p-5">
              <EmptyState icon="flag" title={f.empty} hint={f.emptyHint} />
            </section>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3 sm:gap-4">
                <StatTile label={f.summary.pending} value={items.length} tone="ochre" icon="flag" />
                <StatTile
                  label={f.summary.high}
                  value={items.filter((item) => item.confidence === "HIGH").length}
                  tone="brick"
                  icon="shield"
                />
                <StatTile
                  label={f.summary.rule}
                  value={items.filter((item) => item.model === RULES_MODEL).length}
                  tone="ink"
                  icon="clipboard"
                />
              </div>

              {resolve.isError ? (
                <Alert variant="error" className="text-sm">
                  {resolve.error instanceof ApiError && resolve.error.status === 409
                    ? f.notPending
                    : messages.errors.generic}
                </Alert>
              ) : null}

              <PanelSection icon="flag" title={f.listTitle} hint={f.listHint} flush>
                <ul className="divide-y divide-border">
                  {items.map((flag) => (
                    <li key={flag.id} className="relative flex flex-col gap-4 px-5 py-4 pl-6 md:flex-row md:items-start">
                      <span
                        aria-hidden="true"
                        className={cn("absolute inset-y-0 left-0 w-[3px]", CONFIDENCE_BAR[flag.confidence] ?? "bg-border")}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                          <PanelIcon
                            name={SUBJECT_ICON[flag.subject_type] ?? "flag"}
                            className="h-4 w-4 shrink-0 text-muted-foreground"
                          />
                          <span className="min-w-0 truncate">
                            {f.subjectTypeLabel[flag.subject_type as keyof typeof f.subjectTypeLabel] ??
                              flag.subject_type}
                            : {flag.subject_label ?? `#${flag.subject_id.slice(0, 8)}`}
                          </span>
                        </p>
                        <p className="mt-1.5 max-w-[640px] text-[15px] leading-6 text-foreground">{flag.reason}</p>
                        <div className="mt-2.5 flex flex-wrap items-center gap-2">
                          <StatusPill tone={CONFIDENCE_TONE[flag.confidence] ?? "default"}>
                            {f.confidenceLabel[flag.confidence as keyof typeof f.confidenceLabel] ?? flag.confidence}
                          </StatusPill>
                          {flag.signal ? (
                            <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground">
                              {signalLabels[flag.signal] ?? flag.signal}
                            </span>
                          ) : null}
                          <span className="text-xs text-muted-foreground">
                            {flag.model === RULES_MODEL ? f.sourceLabel.rule : f.sourceLabel.ai}
                          </span>
                          <span className="font-mono text-xs text-muted-foreground">{flag.model}</span>
                          <TimeAgo iso={flag.created_at} />
                        </div>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <button
                          onClick={() => resolve.mutate({ flagId: flag.id, outcome: "DISMISSED" })}
                          disabled={resolve.isPending}
                          aria-label={`${f.form.dismiss} ${flag.id}`}
                          className={cn(actionClass.neutral, SM)}
                        >
                          {f.form.dismiss}
                        </button>
                        <button
                          onClick={() => resolve.mutate({ flagId: flag.id, outcome: "CONFIRMED" })}
                          disabled={resolve.isPending}
                          aria-label={`${f.form.confirm} ${flag.id}`}
                          className={cn(actionClass.dangerOutline, SM)}
                        >
                          {f.form.confirm}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
                <AdminPagination
                  offset={offset}
                  limit={limit}
                  hasMore={queue?.has_more ?? false}
                  disabled={resolve.isPending}
                  onChange={setOffset}
                />
              </PanelSection>
            </>
          )}
        </PageBody>
      </main>
    </AppShell>
  );
}
