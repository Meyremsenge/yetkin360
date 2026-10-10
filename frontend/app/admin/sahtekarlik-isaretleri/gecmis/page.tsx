"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AdminPagination } from "@/components/admin-pagination";
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
      <main className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">{messages.adminFraudHistory.title}</h1>
        <p className="text-sm text-slate-600 mb-4">{messages.adminFraudHistory.description}</p>
        <p className="mb-6 text-sm">
          <Link
            href="/admin/sahtekarlik-isaretleri"
            className="underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
          >
            {messages.adminFraudHistory.backToQueue}
          </Link>
        </p>

        <div className="mb-6 max-w-xs">
          <label htmlFor="history-status" className="block text-sm font-medium mb-1">
            {messages.adminFraudHistory.filterLabel}
          </label>
          <select
            id="history-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as StatusFilter);
              setOffset(0);
            }}
            className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
          >
            <option value="">{messages.adminFraudHistory.filterAll}</option>
            <option value="CONFIRMED">{messages.adminFraudHistory.status.CONFIRMED}</option>
            <option value="DISMISSED">{messages.adminFraudHistory.status.DISMISSED}</option>
          </select>
        </div>

        {isLoading ? (
          <p role="status" className="text-slate-600">
            {messages.adminFraudHistory.loading}
          </p>
        ) : isError ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            <p>
              {error instanceof ApiError && error.status === 404
                ? messages.adminFraudHistory.notFound
                : error instanceof NetworkError && error.kind === "timeout"
                  ? messages.errors.timeout
                  : messages.errors.generic}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-2 px-3 py-1 border border-red-300 rounded-md hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            >
              {messages.adminFraudHistory.retry}
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.adminFraudHistory.empty}
          </div>
        ) : (
          <>
            <ul className="space-y-4">
              {items.map((flag) => (
                <li key={flag.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        flag.status === "CONFIRMED"
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {statusLabels[flag.status] ?? flag.status}
                    </span>
                    {flag.signal && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                        {signalLabels[flag.signal] ?? flag.signal}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">{flag.model}</span>
                  </div>
                  <p className="text-sm text-slate-800">{flag.reason}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {subjectTypeLabels[flag.subject_type] ?? flag.subject_type}:{" "}
                    {flag.subject_label ?? `#${flag.subject_id.slice(0, 8)}`}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
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
          </>
        )}
      </main>
    </AppShell>
  );
}
