"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { adminListComplaints } from "@/lib/api/complaints";
import { formatDate } from "@/lib/complaints/format";
import messages from "@/messages/tr.json";

const t = messages.adminComplaints;
const PAGE_SIZE = 50;

/** C8: admin şikayet kuyruğu (limit/offset + has_more ile Önceki/Sonraki). */
export default function AdminSikayetlerPage() {
  const [offset, setOffset] = useState(0);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "complaints", offset],
    queryFn: () => adminListComplaints({ limit: PAGE_SIZE, offset }),
  });

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const statusLabels = t.statusLabel as Record<string, string>;
  const subjectLabels = t.subjectType as Record<string, string>;

  return (
    <AppShell>
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="mb-2 text-2xl font-bold">{t.title}</h1>
        <p className="mb-6 text-sm text-muted-foreground">{t.description}</p>

        <div aria-live="polite">
          {isLoading ? (
            <p className="text-muted-foreground">{t.loading}</p>
          ) : isError ? (
            <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {t.loadError}
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="rounded-md border border-border bg-muted p-6">
              <p className="font-semibold">{t.empty.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t.empty.body}</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {data.items.map((c) => {
                const created = formatDate(c.created_at);
                const statusText = (c.status && statusLabels[c.status]) || statusLabels.OPEN;
                return (
                  <li key={c.id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium">
                          {subjectLabels[c.subject_type] ?? c.subject_type}
                          {c.subject_label ? `: ${c.subject_label}` : ""}
                        </p>
                        {created ? <p className="text-xs text-muted-foreground">{created}</p> : null}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {c.subject_still_pending === false && (
                          <span className="rounded-full border border-warning/30 bg-warning/10 px-2 py-0.5 text-xs text-warning">
                            {t.stalePending}
                          </span>
                        )}
                        <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium">
                          {statusText}
                        </span>
                        <Link
                          href={`/admin/sikayetler/${encodeURIComponent(c.id)}`}
                          className="text-sm font-medium text-success underline underline-offset-4"
                        >
                          {t.detail.view}
                        </Link>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {data && (offset > 0 || data.has_more) && (
          <nav aria-label={t.pagination.page.replace("{page}", String(page))} className="mt-6 flex items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              {t.pagination.previous}
            </Button>
            <span className="text-sm text-muted-foreground">{t.pagination.page.replace("{page}", String(page))}</span>
            <Button type="button" variant="secondary" disabled={!data.has_more} onClick={() => setOffset(offset + PAGE_SIZE)}>
              {t.pagination.next}
            </Button>
          </nav>
        )}
      </main>
    </AppShell>
  );
}
