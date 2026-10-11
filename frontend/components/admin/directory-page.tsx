"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyCard, FIELD_CLASS, Field, FilterBar, LoadError, LoadingBlock, SM, TABLE } from "@/components/admin/admin-ui";
import { PageBody, PageHeader } from "@/components/page-layout";
import { PanelIcon, actionClass } from "@/components/panel-kit";
import { cn } from "@/lib/utils";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { PAGE_SIZE, setSuspended, type DirectoryKind, type ListParams, type Page } from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

/** Texts every directory screen needs; each screen passes its own tr.json namespace. */
export interface DirectoryMessages {
  title: string;
  intro: string;
  searchLabel: string;
  searchPlaceholder: string;
  searchButton: string;
  filterStatus: string;
  filterAll: string;
  empty: string;
  emptyFiltered: string;
  loadError: string;
  prev: string;
  next: string;
  pageInfo: string;
  actions: string;
  suspend: string;
  reactivate: string;
  confirmSuspendTitle: string;
  confirmSuspendBody: string;
  confirmReactivateTitle: string;
  confirmReactivateBody: string;
  confirm: string;
  cancel: string;
  suspended: string;
  reactivated: string;
  notFound: string;
  statusLabels: Record<string, string>;
}

export interface Column<T> {
  header: string;
  cell: (item: T) => ReactNode;
}

interface DirectoryItem {
  id: string;
  status: string;
}

interface DirectoryPageProps<T extends DirectoryItem> {
  kind: DirectoryKind;
  m: DirectoryMessages;
  fetchPage: (params: ListParams) => Promise<Page<T> | undefined>;
  columns: Column<T>[];
  rowLabel: (item: T) => string;
  statusOptions: string[];
  /** Statuses that offer no suspend/reactivate button (e.g. DELETED users). */
  inactionableStatuses?: string[];
  extraFilters?: ReactNode;
  extraParams?: Partial<ListParams>;
  extraActions?: (item: T, onChanged: (msg: string) => void, onError: (err: unknown) => void) => ReactNode;
  conflictMessage?: (err: ApiError) => string | null;
}

export const NONE = "—";

export function formatDate(value: string | null | undefined): string {
  if (!value) return NONE;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? NONE : d.toLocaleDateString("tr-TR");
}

export function DirectoryPage<T extends DirectoryItem>({
  kind,
  m,
  fetchPage,
  columns,
  rowLabel,
  statusOptions,
  inactionableStatuses = [],
  extraFilters,
  extraParams,
  extraActions,
  conflictMessage,
}: DirectoryPageProps<T>) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [pending, setPending] = useState<T | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const params: ListParams = { q, status: status || undefined, limit: PAGE_SIZE, offset, ...extraParams };
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["admin", kind, params],
    queryFn: () => fetchPage(params),
  });

  const describeError = (err: unknown): string => {
    if (err instanceof ApiError) {
      if (err.status === 404) return m.notFound;
      if (err.status === 409) return conflictMessage?.(err) ?? messages.errors.generic;
      return messages.errors.generic;
    }
    if (err instanceof NetworkError) return err.kind === "timeout" ? messages.errors.timeout : messages.errors.network;
    return messages.errors.generic;
  };

  const onChanged = (msg: string) => {
    setActionError(null);
    setNotice(msg);
    queryClient.invalidateQueries({ queryKey: ["admin", kind] });
  };
  const onError = (err: unknown) => {
    setNotice(null);
    setActionError(describeError(err));
    // A timed-out write may have completed on the server: refresh instead of retrying blindly.
    queryClient.invalidateQueries({ queryKey: ["admin", kind] });
  };

  const { mutate, isPending } = useMutation({
    mutationFn: (vars: { id: string; suspend: boolean }) => setSuspended<T>(kind, vars.id, vars.suspend),
    onSuccess: (_res, vars) => {
      setPending(null);
      onChanged(vars.suspend ? m.suspended : m.reactivated);
    },
    onError: (err) => {
      setPending(null);
      onError(err);
    },
  });

  const submitSearch = (e: FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setQ(draft.trim());
  };

  const items = data?.items ?? [];
  const filtered = Boolean(q || status || extraParams?.verification_level);
  const pendingSuspend = pending ? pending.status !== "SUSPENDED" : true;
  const statusLabel = (s: string) => m.statusLabels[s] ?? s;

  return (
    <AppShell>
      <main>
        <PageHeader eyebrow={messages.shell.groupAdmin} title={m.title} description={m.intro} />
        <PageBody className="space-y-5">
          <FilterBar onSubmit={submitSearch} role="search">
            <Field label={m.searchLabel} htmlFor={`${kind}-q`} className="min-w-[240px] flex-1 sm:max-w-sm">
              <input
                id={`${kind}-q`}
                type="search"
                value={draft}
                maxLength={200}
                placeholder={m.searchPlaceholder}
                onChange={(e) => setDraft(e.target.value)}
                className={FIELD_CLASS}
              />
            </Field>
            {statusOptions.length > 0 && (
              <Field label={m.filterStatus} htmlFor={`${kind}-status`}>
                <select
                  id={`${kind}-status`}
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setOffset(0);
                  }}
                  className={FIELD_CLASS}
                >
                  <option value="">{m.filterAll}</option>
                  {statusOptions.map((s) => (
                    <option key={s} value={s}>
                      {statusLabel(s)}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            {extraFilters}
            <button type="submit" className={actionClass.primary}>
              <PanelIcon name="search" className="h-4 w-4" />
              {m.searchButton}
            </button>
          </FilterBar>

          <div aria-live="polite">
            {notice && (
              <div role="status" className="rounded-md border border-success/30 bg-success/10 p-3 text-sm text-success">
                {notice}
              </div>
            )}
          </div>
          <div aria-live="assertive">
            {actionError && (
              <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {actionError}
              </div>
            )}
          </div>

          {isLoading ? (
            <LoadingBlock label={messages.shell.loading} />
          ) : isError ? (
            <LoadError
              message={error instanceof NetworkError || error instanceof ApiError ? describeError(error) : m.loadError}
              onRetry={() => refetch()}
              retryLabel={messages.errors.retry}
            />
          ) : items.length === 0 ? (
            <EmptyCard icon="search" title={filtered || offset > 0 ? m.emptyFiltered : m.empty} />
          ) : (
            <div className={TABLE.frame}>
              <table className={TABLE.table}>
                <thead>
                  <tr className={TABLE.headRow}>
                    {columns.map((c) => (
                      <th key={c.header} scope="col" className={TABLE.th}>
                        {c.header}
                      </th>
                    ))}
                    <th scope="col" className={TABLE.th}>
                      {m.actions}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className={TABLE.row}>
                      {columns.map((c) => (
                        <td key={c.header} className={TABLE.td}>
                          {c.cell(item)}
                        </td>
                      ))}
                      <td className={TABLE.td}>
                        <div className="flex flex-wrap items-center gap-2">
                          {!inactionableStatuses.includes(item.status) && (
                            <button
                              type="button"
                              onClick={() => setPending(item)}
                              disabled={isPending}
                              aria-label={`${item.status === "SUSPENDED" ? m.reactivate : m.suspend}: ${rowLabel(item)}`}
                              className={cn(
                                item.status === "SUSPENDED" ? actionClass.outline : actionClass.dangerOutline,
                                SM
                              )}
                            >
                              {item.status === "SUSPENDED" ? m.reactivate : m.suspend}
                            </button>
                          )}
                          {extraActions?.(item, onChanged, onError)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!isLoading && !isError && (items.length > 0 || offset > 0) && (
            <nav className="flex items-center justify-between gap-3" aria-label={m.pageInfo}>
              <button
                type="button"
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0 || isFetching}
                className={cn(actionClass.neutral, SM)}
              >
                {m.prev}
              </button>
              <span className="text-sm text-muted-foreground">
                {m.pageInfo} {Math.floor(offset / PAGE_SIZE) + 1}
              </span>
              <button
                type="button"
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={!data?.has_more || isFetching}
                className={cn(actionClass.neutral, SM)}
              >
                {m.next}
              </button>
            </nav>
          )}

          <ConfirmDialog
            open={pending !== null}
            title={pendingSuspend ? m.confirmSuspendTitle : m.confirmReactivateTitle}
            body={`${pending ? rowLabel(pending) : ""} — ${pendingSuspend ? m.confirmSuspendBody : m.confirmReactivateBody}`}
            confirmLabel={m.confirm}
            cancelLabel={m.cancel}
            busy={isPending}
            onCancel={() => setPending(null)}
            onConfirm={() => pending && mutate({ id: pending.id, suspend: pendingSuspend })}
          />
        </PageBody>
      </main>
    </AppShell>
  );
}
