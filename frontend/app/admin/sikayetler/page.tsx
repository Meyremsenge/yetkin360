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

/** "" = open queue (server default); the rest are the terminal outcomes. */
const TABS: { status: string; label: string }[] = [
  { status: "", label: t.tabs.open },
  { status: "UPHELD", label: t.tabs.UPHELD },
  { status: "RESOLVED", label: t.tabs.RESOLVED },
  { status: "DISMISSED", label: t.tabs.DISMISSED },
];

/** C8: admin şikayet kuyruğu (limit/offset + has_more ile Önceki/Sonraki). */
export default function AdminSikayetlerPage() {
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "complaints", status, offset],
    queryFn: () => adminListComplaints(status ? { limit: PAGE_SIZE, offset, status } : { limit: PAGE_SIZE, offset }),
  });
  const activeTab = TABS.find((tab) => tab.status === status) ?? TABS[0];

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const statusLabels = t.statusLabel as Record<string, string>;
  const subjectLabels = t.subjectType as Record<string, string>;

  return (
    <AppShell>
      <main>
        <PageHeader eyebrow={messages.shell.groupAdmin} title={t.title} description={t.description} />
        <PageBody className="space-y-6">
          <div role="tablist" aria-label={t.tabs.label} className="flex flex-wrap gap-2">
            {TABS.map((tab) => {
              const selected = tab.status === status;
              return (
                <button
                  key={tab.status || "open"}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  onClick={() => {
                    setStatus(tab.status);
                    setOffset(0);
                  }}
                  className={cn(
                    "h-9 rounded-full border px-4 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
                    selected
                      ? "border-success/30 bg-success/[0.08] font-medium text-success"
                      : "border-border bg-card text-muted-foreground hover:text-foreground"
                  )}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div aria-live="polite" role="tabpanel" aria-label={activeTab.label}>
            {isLoading ? (
              <LoadingBlock label={t.loading} />
            ) : isError ? (
              <LoadError message={t.loadError} />
            ) : !data || data.items.length === 0 ? (
              status ? (
                <EmptyCard icon="inbox" title={t.tabs.empty.replace("{tab}", activeTab.label)} />
              ) : (
                <EmptyCard icon="inbox" title={t.empty.title} hint={t.empty.body} />
              )
            ) : (
              <PanelSection icon="inbox" title={activeTab.label} count={data.items.length} flush>
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
