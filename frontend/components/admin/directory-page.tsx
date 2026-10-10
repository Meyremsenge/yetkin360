"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
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
      <main className="mx-auto max-w-6xl p-6">
        <h1 className="mb-2 text-2xl font-bold">{m.title}</h1>
        <p className="mb-6 text-sm text-slate-600">{m.intro}</p>

        <form onSubmit={submitSearch} className="mb-4 flex flex-wrap items-end gap-3" role="search">
          <div className="flex flex-col">
            <label htmlFor={`${kind}-q`} className="text-sm font-medium text-slate-700">
              {m.searchLabel}
            </label>
            <input
              id={`${kind}-q`}
              type="search"
              value={draft}
              maxLength={200}
              placeholder={m.searchPlaceholder}
              onChange={(e) => setDraft(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          {statusOptions.length > 0 && (
          <div className="flex flex-col">
            <label htmlFor={`${kind}-status`} className="text-sm font-medium text-slate-700">
              {m.filterStatus}
            </label>
            <select
              id={`${kind}-status`}
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            >
              <option value="">{m.filterAll}</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
          </div>
          )}
          {extraFilters}
          <button
            type="submit"
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-slate-900"
          >
            {m.searchButton}
          </button>
        </form>

        <div aria-live="polite">
          {notice && (
            <div role="status" className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              {notice}
            </div>
          )}
        </div>
        <div aria-live="assertive">
          {actionError && (
            <div role="alert" className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {actionError}
            </div>
          )}
        </div>

        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <p>{error instanceof NetworkError || error instanceof ApiError ? describeError(error) : m.loadError}</p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-2 rounded-md border border-red-300 px-3 py-1 text-sm hover:bg-red-100"
            >
              {messages.errors.retry}
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            {filtered || offset > 0 ? m.emptyFiltered : m.empty}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  {columns.map((c) => (
                    <th key={c.header} scope="col" className="p-3 text-left font-medium text-slate-700">
                      {c.header}
                    </th>
                  ))}
                  <th scope="col" className="p-3 text-left font-medium text-slate-700">
                    {m.actions}
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-slate-200">
                    {columns.map((c) => (
                      <td key={c.header} className="p-3 text-slate-700">
                        {c.cell(item)}
                      </td>
                    ))}
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        {!inactionableStatuses.includes(item.status) && (
                          <button
                            type="button"
                            onClick={() => setPending(item)}
                            disabled={isPending}
                            aria-label={`${item.status === "SUSPENDED" ? m.reactivate : m.suspend}: ${rowLabel(item)}`}
                            className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
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
          <nav className="mt-4 flex items-center gap-3" aria-label={m.pageInfo}>
            <button
              type="button"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0 || isFetching}
              className="rounded-md border border-slate-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
            >
              {m.prev}
            </button>
            <span className="text-sm text-slate-600">
              {m.pageInfo} {Math.floor(offset / PAGE_SIZE) + 1}
            </span>
            <button
              type="button"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={!data?.has_more || isFetching}
              className="rounded-md border border-slate-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
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
      </main>
    </AppShell>
  );
}
