"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  getComplaintEvidenceUrl,
  getComplaintQueue,
  resolveComplaint,
  type AdminComplaint,
  type ComplaintOutcome,
  type ComplaintStatus,
} from "@/lib/api/complaints";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.adminComplaints;
const c = messages.calismalar;

const TABS: ComplaintStatus[] = ["OPEN", "UPHELD", "DISMISSED"];
const NOTE_MAX = 1000;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

function evidenceErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return t.evidenceError.notFound;
    if (error.status === 409) return t.evidenceError.notReady;
  }
  return t.evidenceError.generic;
}

/** The organization's "deliberate non-verification" mark: how many complaints were upheld against it. */
function Stamp({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span
      data-testid="complaint-stamp"
      title={t.stampLabel.replace("{count}", String(count))}
      className="inline-flex items-center gap-1.5 rounded-full border border-destructive/30 bg-destructive/10 px-2.5 py-0.5 text-xs font-semibold text-destructive"
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-destructive" />
      {t.stamp.replace("{count}", String(count))}
    </span>
  );
}

function ComplaintItem({
  complaint,
  busy,
  onDecide,
}: {
  complaint: AdminComplaint;
  busy: boolean;
  onDecide: (outcome: ComplaintOutcome, note: string) => void;
}) {
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<ComplaintOutcome | null>(null);
  // The link is short-lived and every request is audited: fetch it only on click.
  // The tab is opened in the click itself (a window opened after the request
  // returns is blocked as a pop-up) and pointed at the file once the link arrives.
  const evidence = useMutation({
    mutationFn: async (tab: Window | null) => {
      try {
        const url = await getComplaintEvidenceUrl(complaint.id);
        if (tab) tab.location.href = url;
        else window.location.assign(url);
      } catch (error) {
        tab?.close();
        throw error;
      }
    },
  });

  const openEvidence = () => {
    const tab = window.open("", "_blank");
    // User content is served from another origin: it must not reach back into this page.
    if (tab) tab.opener = null;
    evidence.mutate(tab);
  };
  const noteId = `complaint-note-${complaint.id}`;
  const label = (action: string) =>
    t.actionLabel
      .replace("{student}", complaint.talent_name)
      .replace("{engagement}", complaint.engagement_title)
      .replace("{action}", action);

  return (
    <li className="rounded-xl border border-border bg-card p-5" data-testid="admin-complaint">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            {(c.complaint.category as Record<string, string>)[complaint.category]}
          </p>
          <p className="mt-0.5 font-mono text-xs text-muted-foreground">
            {complaint.decided_at
              ? t.decidedOn.replace("{date}", formatDate(complaint.decided_at))
              : t.openedOn.replace("{date}", formatDate(complaint.created_at))}
          </p>
        </div>
        {complaint.has_evidence ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs text-foreground">
              {t.hasEvidence}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={evidence.isPending}
              aria-label={t.openEvidenceLabel
                .replace("{student}", complaint.talent_name)
                .replace("{engagement}", complaint.engagement_title)}
              onClick={openEvidence}
            >
              {evidence.isPending ? t.openingEvidence : t.openEvidence}
            </Button>
          </div>
        ) : null}
      </div>

      {evidence.isError ? (
        <p role="alert" className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {evidenceErrorMessage(evidence.error)}
        </p>
      ) : null}

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">{t.studentLabel}</dt>
          <dd className="font-medium text-foreground">{complaint.talent_name}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t.organizationLabel}</dt>
          <dd className="flex flex-wrap items-center gap-2 font-medium text-foreground">
            {complaint.organization_name}
            <Stamp count={complaint.organization_upheld_count} />
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">{t.engagementLabel}</dt>
          <dd className="font-medium text-foreground">
            {complaint.engagement_title}
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {(c.status as Record<string, string>)[complaint.engagement_status] ?? complaint.engagement_status}
            </span>
          </dd>
        </div>
      </dl>

      <p className="mt-4 whitespace-pre-line rounded-lg bg-muted/60 px-4 py-3 text-sm text-foreground">
        {complaint.description}
      </p>

      {complaint.status !== "OPEN" ? (
        complaint.decision_note ? (
          <p className="mt-3 text-sm text-foreground">
            <span className="font-medium">{t.decisionNoteLabel}:</span> {complaint.decision_note}
          </p>
        ) : null
      ) : (
        <div className="mt-4">
          <Label htmlFor={noteId}>{t.noteLabel}</Label>
          <textarea
            id={noteId}
            maxLength={NOTE_MAX}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="mt-1 min-h-[72px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
          />

          {pending ? (
            <div role="alertdialog" aria-label={t.confirmButton} className="mt-3 rounded-lg border border-warning/30 bg-warning/10 p-3">
              <p className="text-sm text-foreground">{t.confirm[pending]}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button type="button" disabled={busy} onClick={() => onDecide(pending, note.trim())}>
                  {t.confirmButton}
                </Button>
                <Button type="button" variant="secondary" disabled={busy} onClick={() => setPending(null)}>
                  {t.cancelButton}
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                type="button"
                aria-label={label(t.uphold)}
                disabled={busy}
                onClick={() => setPending("UPHELD")}
                className="bg-destructive text-background hover:bg-destructive/90"
              >
                {t.uphold}
              </Button>
              <Button
                type="button"
                variant="secondary"
                aria-label={label(t.dismiss)}
                disabled={busy}
                onClick={() => setPending("DISMISSED")}
              >
                {t.dismiss}
              </Button>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

/**
 * Student complaints: the organization is notified when one is opened, the
 * admin upholds it (counts against the organization) or dismisses it here.
 */
export default function SikayetlerPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ComplaintStatus>("OPEN");

  const queue = useQuery({
    queryKey: ["admin", "complaints", status],
    queryFn: () => getComplaintQueue(status),
  });

  const resolve = useMutation({
    mutationFn: (vars: { id: string; outcome: ComplaintOutcome; note: string }) =>
      resolveComplaint(vars.id, vars.outcome, vars.note || undefined),
    // Every tab changes: the decided one moves, and the organization's count with it.
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["admin", "complaints"] }),
  });

  const items = queue.data ?? [];

  return (
    <AppShell>
      <PageHeader eyebrow={messages.shell.groupAdmin} title={t.title} description={t.description} />
      <PageBody>
        <div
          role="tablist"
          aria-label={t.tabsLabel}
          className="inline-flex gap-1 rounded-lg border border-border bg-muted/60 p-1"
        >
          {TABS.map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={status === key}
              onClick={() => setStatus(key)}
              className={cn(
                "h-9 rounded-md px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
                status === key
                  ? "bg-card text-foreground shadow-[0_1px_3px_rgba(34,31,27,0.12)]"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t.tabs[key]}
            </button>
          ))}
        </div>

        <div role="tabpanel" className="mt-6">
          {resolve.isError ? (
            <p role="alert" className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {resolve.error instanceof ApiError && resolve.error.status === 409 ? t.notOpen : messages.errors.generic}
            </p>
          ) : null}

          {queue.isLoading ? (
            <p role="status" className="text-sm text-muted-foreground">
              {messages.shell.loading}
            </p>
          ) : queue.isError ? (
            <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {queue.error instanceof ApiError && queue.error.status === 404
                ? t.notFound
                : queue.error instanceof NetworkError && queue.error.kind === "timeout"
                  ? messages.errors.timeout
                  : messages.errors.generic}
            </p>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-muted-foreground/30 p-6">
              <p className="text-sm font-medium text-foreground">{t.empty[status].title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t.empty[status].hint}</p>
            </div>
          ) : (
            <ul className="space-y-4">
              {items.map((complaint) => (
                <ComplaintItem
                  key={complaint.id}
                  complaint={complaint}
                  busy={resolve.isPending}
                  onDecide={(outcome, note) => resolve.mutate({ id: complaint.id, outcome, note })}
                />
              ))}
            </ul>
          )}
        </div>
      </PageBody>
    </AppShell>
  );
}
