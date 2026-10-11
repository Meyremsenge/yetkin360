"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { EmptyCard, LoadError, LoadingBlock, SM, statusTone } from "@/components/admin/admin-ui";
import { PageBody, PageHeader } from "@/components/page-layout";
import { PanelSection, StatusPill, actionClass } from "@/components/panel-kit";
import { cn } from "@/lib/utils";
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
      <main>
        <PageHeader eyebrow={messages.shell.groupAdmin} title={t.title} description={t.description} />
        <PageBody className="space-y-6">
          <div aria-live="polite">
            {isLoading ? (
              <LoadingBlock label={t.loading} />
            ) : isError ? (
              <LoadError message={t.loadError} />
            ) : !data || data.items.length === 0 ? (
              <EmptyCard icon="inbox" title={t.empty.title} hint={t.empty.body} />
            ) : (
              <PanelSection icon="inbox" title={t.title} count={data.items.length} flush>
                <ul className="divide-y divide-border">
                  {data.items.map((c) => {
                    const created = formatDate(c.created_at);
                    const statusText = (c.status && statusLabels[c.status]) || statusLabels.OPEN;
                    return (
                      <li key={c.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
                        <div className="min-w-0 flex-1">
                          <p className="text-[15px] font-medium text-foreground">
                            {subjectLabels[c.subject_type] ?? c.subject_type}
                            {c.subject_label ? `: ${c.subject_label}` : ""}
                          </p>
                          <div className="mt-1.5 flex flex-wrap items-center gap-2">
                            <StatusPill tone={statusTone(c.status ?? "OPEN")}>{statusText}</StatusPill>
                            {c.subject_still_pending === false && (
                              <span className="rounded-full border border-warning/30 bg-warning/10 px-2.5 py-0.5 text-xs text-warning">
                                {t.stalePending}
                              </span>
                            )}
                            {created ? <span className="text-xs text-muted-foreground">{created}</span> : null}
                          </div>
                        </div>
                        <Link
                          href={`/admin/sikayetler/${encodeURIComponent(c.id)}`}
                          className={cn(actionClass.outline, SM, "shrink-0")}
                        >
                          {t.detail.view}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </PanelSection>
            )}
          </div>

          {data && (offset > 0 || data.has_more) && (
            <nav
              aria-label={t.pagination.page.replace("{page}", String(page))}
              className="flex items-center justify-between gap-3"
            >
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className={cn(actionClass.neutral, SM)}
              >
                {t.pagination.previous}
              </button>
              <span className="text-sm text-muted-foreground">{t.pagination.page.replace("{page}", String(page))}</span>
              <button
                type="button"
                disabled={!data.has_more}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className={cn(actionClass.neutral, SM)}
              >
                {t.pagination.next}
              </button>
            </nav>
          )}
        </PageBody>
      </main>
    </AppShell>
  );
}
