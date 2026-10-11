"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AdminPagination } from "@/components/admin-pagination";
import { EmptyCard, FIELD_CLASS, Field, FilterBar, LoadError, LoadingBlock, TABLE } from "@/components/admin/admin-ui";
import { PageBody, PageHeader } from "@/components/page-layout";
import { actionClass } from "@/components/panel-kit";
import { cn } from "@/lib/utils";
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

  return (
    <AppShell>
      <main>
        <PageHeader
          eyebrow={messages.shell.groupAdmin}
          title={messages.adminAudit.title}
          description={messages.adminAudit.description}
        />
        <PageBody className="space-y-5">
          <FilterBar onSubmit={applyFilters} className="grid gap-4 sm:grid-cols-3">
            <Field label={messages.adminAudit.filters.action} htmlFor="audit-action">
              <input
                id="audit-action"
                className={FIELD_CLASS}
                maxLength={100}
                placeholder={messages.adminAudit.filters.actionPlaceholder}
                value={draft.action}
                onChange={(e) => setDraft({ ...draft, action: e.target.value })}
              />
            </Field>
            <Field label={messages.adminAudit.filters.subjectType} htmlFor="audit-subject-type">
              <input
                id="audit-subject-type"
                className={FIELD_CLASS}
                maxLength={50}
                placeholder={messages.adminAudit.filters.subjectTypePlaceholder}
                value={draft.subject_type}
                onChange={(e) => setDraft({ ...draft, subject_type: e.target.value })}
              />
            </Field>
            <Field label={messages.adminAudit.filters.actorUserId} htmlFor="audit-actor">
              <input
                id="audit-actor"
                className={FIELD_CLASS}
                placeholder={messages.adminAudit.filters.actorPlaceholder}
                value={draft.actor_user_id}
                aria-invalid={actorError}
                onChange={(e) => setDraft({ ...draft, actor_user_id: e.target.value })}
              />
            </Field>
            <div className="flex gap-2 sm:col-span-3">
              <button type="submit" className={actionClass.primary}>
                {messages.adminAudit.filters.apply}
              </button>
              <button type="button" onClick={clearFilters} className={actionClass.neutral}>
                {messages.adminAudit.filters.clear}
              </button>
            </div>
            {actorError && (
              <p role="alert" className="text-sm text-destructive sm:col-span-3">
                {messages.adminAudit.filters.invalidActor}
              </p>
            )}
          </FilterBar>

          {isLoading ? (
            <LoadingBlock label={messages.adminAudit.loading} />
          ) : isError ? (
            <LoadError
              message={
                error instanceof ApiError && error.status === 404
                  ? messages.adminAudit.notFound
                  : error instanceof NetworkError && error.kind === "timeout"
                    ? messages.errors.timeout
                    : messages.errors.generic
              }
              onRetry={() => refetch()}
              retryLabel={messages.adminAudit.retry}
            />
          ) : items.length === 0 ? (
            <EmptyCard icon="clipboard" title={messages.adminAudit.empty} />
          ) : (
            <div className={TABLE.frame}>
              <table className={TABLE.table}>
                <thead>
                  <tr className={TABLE.headRow}>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.time}</th>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.action}</th>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.subject}</th>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.actor}</th>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.result}</th>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.ip}</th>
                    <th scope="col" className={TABLE.th}>{messages.adminAudit.columns.details}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((event) => (
                    <tr key={event.id} className={cn(TABLE.row, "align-top")}>
                      <td className={cn(TABLE.td, "whitespace-nowrap text-muted-foreground")}>
                        {formatDate(event.created_at)}
                      </td>
                      <td className={TABLE.td}>
                        <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-xs">{event.action}</span>
                      </td>
                      <td className={TABLE.td}>
                        {event.subject_type}{" "}
                        <span className="font-mono text-xs text-muted-foreground">{shortId(event.subject_id)}</span>
                      </td>
                      <td className={cn(TABLE.td, "font-mono text-xs")}>
                        {event.actor_user_id ? shortId(event.actor_user_id) : messages.adminAudit.systemActor}
                      </td>
                      <td className={TABLE.td}>{event.result}</td>
                      <td className={cn(TABLE.td, "font-mono text-xs text-muted-foreground")}>
                        {event.actor_ip ?? messages.adminAudit.none}
                      </td>
                      <td className={cn(TABLE.td, "max-w-[320px] text-xs text-muted-foreground")}>
                        {formatMetadata(event.metadata)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <AdminPagination
                offset={offset}
                limit={PAGE_SIZE}
                hasMore={data?.has_more === true}
                disabled={isFetching}
                onChange={setOffset}
              />
            </div>
          )}
        </PageBody>
      </main>
    </AppShell>
  );
}
