"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { listComplaints } from "@/lib/api/complaints";
import { ComplaintStatusBadge } from "./status-badge";
import { formatDate } from "@/lib/complaints/format";
import messages from "@/messages/tr.json";

const t = messages.complaints;

/** C8: öğrencinin ve hakkında şikayet açılan yetkilinin şikayet listesi. */
export default function SikayetlerimPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["complaints"],
    queryFn: () => listComplaints(),
  });

  return (
    <AppShell>
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-2 text-2xl font-bold">{t.title}</h1>
        <p className="mb-6 text-sm text-muted-foreground">{t.description}</p>

        <div aria-live="polite">
          {isLoading ? (
            <p className="text-muted-foreground">{t.loading}</p>
          ) : isError ? (
            <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {t.loadError}
            </div>
          ) : !data || data.length === 0 ? (
            <div className="rounded-md border border-border bg-muted p-6">
              <p className="font-semibold">{t.empty.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t.empty.body}</p>
              <Link href="/calismalar" className="mt-3 inline-block text-sm font-medium text-success underline underline-offset-4">
                {messages.shell.engagementsLink}
              </Link>
            </div>
          ) : (
            <ul className="space-y-3">
              {data.map((complaint) => {
                const created = formatDate(complaint.created_at);
                return (
                  <li key={complaint.id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium">
                          {t.subjectType[complaint.subject_type] ?? complaint.subject_type}
                          {complaint.subject_label ? `: ${complaint.subject_label}` : ""}
                        </p>
                        {created ? <p className="text-xs text-muted-foreground">{created}</p> : null}
                      </div>
                      <div className="flex items-center gap-3">
                        <ComplaintStatusBadge complaint={complaint} />
                        <Link
                          href={`/sikayetlerim/${encodeURIComponent(complaint.id)}`}
                          className="text-sm font-medium text-success underline underline-offset-4"
                        >
                          {t.detail.viewDetail}
                        </Link>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </main>
    </AppShell>
  );
}
