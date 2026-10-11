"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AdminPagination } from "@/components/admin-pagination";
import { EmptyCard, FIELD_CLASS, Field, FilterBar, LoadError, LoadingBlock } from "@/components/admin/admin-ui";
import { PageBody, PageHeader } from "@/components/page-layout";
import { PanelSection, StatusPill } from "@/components/panel-kit";
import * as auditApi from "@/lib/api/admin-audit";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

const PAGE_SIZE = auditApi.AUDIT_PAGE_SIZE;
const signalLabels: Record<string, string> = messages.adminFraudQueue.signalLabel;
const subjectTypeLabels: Record<string, string> = messages.adminFraudQueue.subjectTypeLabel;
const statusLabels: Record<string, string> = messages.adminFraudHistory.status;

type StatusFilter = "" | "CONFIRMED" | "DISMISSED";

function formatDate(value: string | null | undefined): string {
  if (!value) return messages.adminFraudHistory.notReviewed;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? messages.adminFraudHistory.notReviewed
    : date.toLocaleString("tr-TR");
}

/** F2: reviewed (CONFIRMED / DISMISSED) fraud flags, read-only. */
export default function SahtekarlikGecmisiPage() {
  const [status, setStatus] = useState<StatusFilter>("");
  const [offset, setOffset] = useState(0);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["admin", "fraud-history", status, offset],
    queryFn: () =>
      auditApi.getFraudHistory({ status: status || undefined, limit: PAGE_SIZE, offset }),
  });

  const items = data?.items ?? [];

  return (
    <AppShell>
      <main>
        <PageHeader
          eyebrow={messages.shell.groupAdmin}
          title={messages.adminFraudHistory.title}
          description={messages.adminFraudHistory.description}
          back={{ href: "/admin/sahtekarlik-isaretleri", label: messages.adminFraudHistory.backToQueue }}
        />
        <PageBody className="space-y-5">
          <FilterBar onSubmit={(e) => e.preventDefault()}>
            <Field label={messages.adminFraudHistory.filterLabel} htmlFor="history-status" className="w-full sm:w-64">
              <select
                id="history-status"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value as StatusFilter);
                  setOffset(0);
                }}
                className={FIELD_CLASS}
              >
                <option value="">{messages.adminFraudHistory.filterAll}</option>
                <option value="CONFIRMED">{messages.adminFraudHistory.status.CONFIRMED}</option>
                <option value="DISMISSED">{messages.adminFraudHistory.status.DISMISSED}</option>
              </select>
            </Field>
          </FilterBar>

          {isLoading ? (
            <LoadingBlock label={messages.adminFraudHistory.loading} />
          ) : isError ? (
            <LoadError
              message={
                error instanceof ApiError && error.status === 404
                  ? messages.adminFraudHistory.notFound
                  : error instanceof NetworkError && error.kind === "timeout"
                    ? messages.errors.timeout
                    : messages.errors.generic
              }
              onRetry={() => refetch()}
              retryLabel={messages.adminFraudHistory.retry}
            />
          ) : items.length === 0 ? (
            <EmptyCard icon="clock" title={messages.adminFraudHistory.empty} />
          ) : (
            <PanelSection icon="clock" title={messages.adminFraudHistory.title} count={items.length} flush>
              <ul className="divide-y divide-border">
                {items.map((flag) => (
                  <li key={flag.id} className="px-5 py-4">
                    <p className="text-sm font-medium text-foreground">
                      {subjectTypeLabels[flag.subject_type] ?? flag.subject_type}:{" "}
                      {flag.subject_label ?? `#${flag.subject_id.slice(0, 8)}`}
                    </p>
                    <p className="mt-1.5 max-w-[640px] text-[15px] leading-6 text-foreground">{flag.reason}</p>
                    <div className="mt-2.5 flex flex-wrap items-center gap-2">
                      <StatusPill tone={flag.status === "CONFIRMED" ? "error" : "default"}>
                        {statusLabels[flag.status] ?? flag.status}
                      </StatusPill>
                      {flag.signal && (
                        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground">
                          {signalLabels[flag.signal] ?? flag.signal}
                        </span>
                      )}
                      <span className="font-mono text-xs text-muted-foreground">{flag.model}</span>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {messages.adminFraudHistory.reviewedAt}: {formatDate(flag.reviewed_at)} ·{" "}
                      {messages.adminFraudHistory.reviewedBy}:{" "}
                      {flag.reviewed_by_user_id
                        ? `#${flag.reviewed_by_user_id.slice(0, 8)}`
                        : messages.adminFraudHistory.notReviewed}
                    </p>
                  </li>
                ))}
              </ul>
              <AdminPagination
                offset={offset}
                limit={PAGE_SIZE}
                hasMore={data?.has_more === true}
                disabled={isFetching}
                onChange={setOffset}
              />
            </PanelSection>
          )}
        </PageBody>
      </main>
    </AppShell>
  );
}
