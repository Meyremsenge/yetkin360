"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AdminPagination } from "@/components/admin-pagination";
import * as auditApi from "@/lib/api/admin-audit";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PAGE_SIZE = auditApi.AUDIT_PAGE_SIZE;

interface Filters {
  action: string;
  subject_type: string;
  actor_user_id: string;
}

const EMPTY_FILTERS: Filters = { action: "", subject_type: "", actor_user_id: "" };

function formatDate(value: string | null | undefined): string {
  if (!value) return messages.adminAudit.none;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? messages.adminAudit.none : date.toLocaleString("tr-TR");
}

function shortId(value: string | null | undefined): string {
  return value ? `#${value.slice(0, 8)}` : messages.adminAudit.none;
}

function formatMetadata(metadata: auditApi.AuditEvent["metadata"]): string {
  const entries = Object.entries(metadata ?? {});
  if (entries.length === 0) return messages.adminAudit.none;
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(", ");
}

/**
 * A1: append-only audit log viewer (platform admin). Read-only; the server
 * returns an id-only actor and an allow-listed metadata subset.
 */
export default function DenetimKayitlariPage() {
  const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [actorError, setActorError] = useState(false);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["admin", "audit-events", applied, offset],
    queryFn: () =>
      auditApi.getAuditEvents({
        action: applied.action.trim() || undefined,
        subject_type: applied.subject_type.trim() || undefined,
        actor_user_id: applied.actor_user_id.trim() || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  });

  const items = data?.items ?? [];

  function applyFilters(event: React.FormEvent) {
    event.preventDefault();
    const actor = draft.actor_user_id.trim();
    if (actor !== "" && !UUID_RE.test(actor)) {
      setActorError(true);
      return;
    }
    setActorError(false);
    setOffset(0);
    setApplied(draft);
  }

  function clearFilters() {
    setActorError(false);
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    setOffset(0);
  }

  const inputClass =
    "w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900";

  return (
    <AppShell>
      <main className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">{messages.adminAudit.title}</h1>
        <p className="text-sm text-slate-600 mb-6">{messages.adminAudit.description}</p>

        <form onSubmit={applyFilters} className="mb-6 grid gap-4 sm:grid-cols-3 items-end">
          <div>
            <label htmlFor="audit-action" className="block text-sm font-medium mb-1">
              {messages.adminAudit.filters.action}
            </label>
            <input
              id="audit-action"
              className={inputClass}
              maxLength={100}
              placeholder={messages.adminAudit.filters.actionPlaceholder}
              value={draft.action}
              onChange={(e) => setDraft({ ...draft, action: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="audit-subject-type" className="block text-sm font-medium mb-1">
              {messages.adminAudit.filters.subjectType}
            </label>
            <input
              id="audit-subject-type"
              className={inputClass}
              maxLength={50}
              placeholder={messages.adminAudit.filters.subjectTypePlaceholder}
              value={draft.subject_type}
              onChange={(e) => setDraft({ ...draft, subject_type: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="audit-actor" className="block text-sm font-medium mb-1">
              {messages.adminAudit.filters.actorUserId}
            </label>
            <input
              id="audit-actor"
              className={inputClass}
              placeholder={messages.adminAudit.filters.actorPlaceholder}
              value={draft.actor_user_id}
              aria-invalid={actorError}
              onChange={(e) => setDraft({ ...draft, actor_user_id: e.target.value })}
            />
          </div>
          <div className="sm:col-span-3 flex gap-2">
            <button
              type="submit"
              className="px-3 py-1.5 bg-slate-900 text-white text-sm rounded-md hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
            >
              {messages.adminAudit.filters.apply}
            </button>
            <button
              type="button"
              onClick={clearFilters}
              className="px-3 py-1.5 border border-slate-300 text-sm rounded-md hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
            >
              {messages.adminAudit.filters.clear}
            </button>
          </div>
          {actorError && (
            <p role="alert" className="sm:col-span-3 text-sm text-red-700">
              {messages.adminAudit.filters.invalidActor}
            </p>
          )}
        </form>

        {isLoading ? (
          <p role="status" className="text-slate-600">
            {messages.adminAudit.loading}
          </p>
        ) : isError ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            <p>
              {error instanceof ApiError && error.status === 404
                ? messages.adminAudit.notFound
                : error instanceof NetworkError && error.kind === "timeout"
                  ? messages.errors.timeout
                  : messages.errors.generic}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-2 px-3 py-1 border border-red-300 rounded-md hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            >
              {messages.adminAudit.retry}
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.adminAudit.empty}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-600">
                    <th scope="col" className="py-2 pr-4">{messages.adminAudit.columns.time}</th>
                    <th scope="col" className="py-2 pr-4">{messages.adminAudit.columns.action}</th>
                    <th scope="col" className="py-2 pr-4">{messages.adminAudit.columns.subject}</th>
                    <th scope="col" className="py-2 pr-4">{messages.adminAudit.columns.actor}</th>
                    <th scope="col" className="py-2 pr-4">{messages.adminAudit.columns.result}</th>
                    <th scope="col" className="py-2 pr-4">{messages.adminAudit.columns.ip}</th>
                    <th scope="col" className="py-2">{messages.adminAudit.columns.details}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((event) => (
                    <tr key={event.id} className="border-b border-slate-100 align-top">
                      <td className="py-2 pr-4 whitespace-nowrap">{formatDate(event.created_at)}</td>
                      <td className="py-2 pr-4 font-mono text-xs">{event.action}</td>
                      <td className="py-2 pr-4">
                        {event.subject_type} {shortId(event.subject_id)}
                      </td>
                      <td className="py-2 pr-4">
                        {event.actor_user_id ? shortId(event.actor_user_id) : messages.adminAudit.systemActor}
                      </td>
                      <td className="py-2 pr-4">{event.result}</td>
                      <td className="py-2 pr-4">{event.actor_ip ?? messages.adminAudit.none}</td>
                      <td className="py-2 text-xs text-slate-600">{formatMetadata(event.metadata)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
