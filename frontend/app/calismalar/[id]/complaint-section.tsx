"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  COMPLAINT_CATEGORIES,
  COMPLAINT_DESCRIPTION_MAX,
  COMPLAINT_DESCRIPTION_MIN,
  createComplaint,
  listEngagementComplaints,
  type Complaint,
  type ComplaintCategory,
  type ComplaintStatus,
} from "@/lib/api/complaints";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { listEvidenceForDeliverable } from "@/lib/api/evidence";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.calismalar.complaint;

const STATUS_CLASS: Record<ComplaintStatus, string> = {
  OPEN: "border-warning/30 bg-warning/10 text-warning",
  UPHELD: "border-success/30 bg-success/10 text-success",
  DISMISSED: "border-border bg-muted text-foreground",
};

const FIELD_CLASS =
  "mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "COMPLAINT_ALREADY_OPEN") return t.alreadyOpenError;
    if (error.code === "INVALID_EVIDENCE") return t.invalidEvidenceError;
    if (error.code === "PRECONDITION_FAILED" || error.status === 403) return t.notAllowedError;
  }
  return messages.errors.generic;
}

function ComplaintCard({ complaint }: { complaint: Complaint }) {
  return (
    <li className="rounded-lg border border-border bg-background p-4" data-testid="complaint-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{t.category[complaint.category]}</span>
        <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-medium", STATUS_CLASS[complaint.status])}>
          {t.status[complaint.status]}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-line text-sm text-muted-foreground">{complaint.description}</p>
      <p className="mt-2 font-mono text-xs text-muted-foreground">
        {complaint.decided_at
          ? t.decidedOn.replace("{date}", formatDate(complaint.decided_at))
          : t.submittedOn.replace("{date}", formatDate(complaint.created_at))}
      </p>
      {complaint.decision_note ? (
        <p className="mt-2 rounded-md bg-muted/60 px-3 py-2 text-sm text-foreground">
          <span className="font-medium">{t.decisionNoteLabel}:</span> {complaint.decision_note}
        </p>
      ) : null}
    </li>
  );
}

/**
 * The student's complaint about their own engagement: the organization is not
 * approving, or a personal problem. Shown to the engagement's talent only — the
 * server enforces the same rule.
 */
export function ComplaintSection({ engagement }: { engagement: EngagementDetail }) {
  const queryClient = useQueryClient();
  const queryKey = ["engagement-complaints", engagement.id] as const;
  const [formOpen, setFormOpen] = useState(false);
  const [category, setCategory] = useState<ComplaintCategory>("TASK_APPROVAL");
  const [description, setDescription] = useState("");
  const [evidenceId, setEvidenceId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const complaints = useQuery({ queryKey, queryFn: () => listEngagementComplaints(engagement.id) });

  // Scanned files the student uploaded to this engagement's deliverables.
  const evidence = useQuery({
    queryKey: ["engagement-complaint-evidence", engagement.id, engagement.deliverables.map((d) => d.id)],
    enabled: formOpen && engagement.deliverables.length > 0,
    queryFn: async () => {
      const perDeliverable = await Promise.all(
        engagement.deliverables.map(async (deliverable) =>
          (await listEvidenceForDeliverable(deliverable.id))
            .filter((record) => record.scan_status === "CLEAN")
            .map((record) => ({ id: record.id, deliverable: deliverable.title, createdAt: record.created_at })),
        ),
      );
      return perDeliverable.flat();
    },
  });

  const mutation = useMutation({
    mutationFn: () =>
      createComplaint(engagement.id, {
        category,
        description: description.trim(),
        ...(evidenceId ? { evidence_id: evidenceId } : {}),
      }),
    onSuccess: () => {
      setFormOpen(false);
      setDescription("");
      setEvidenceId("");
      setFormError(null);
      setSent(true);
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: unknown) => setFormError(errorMessage(error)),
  });

  const items = complaints.data ?? [];
  const open = items.find((complaint) => complaint.status === "OPEN");
  const decided = items.filter((complaint) => complaint.status !== "OPEN");
  const attachable = evidence.data ?? [];

  const handleSubmit = () => {
    if (description.trim().length < COMPLAINT_DESCRIPTION_MIN) {
      setFormError(t.descriptionTooShortError.replace("{min}", String(COMPLAINT_DESCRIPTION_MIN)));
      return;
    }
    setFormError(null);
    mutation.mutate();
  };

  return (
    <section className="rounded-xl border border-border bg-card p-5" aria-labelledby="complaint-title">
      <h2 id="complaint-title" className="font-serif text-lg font-semibold text-foreground">
        {t.title}
      </h2>
      <p className="mt-0.5 text-[13px] text-muted-foreground">{t.hint}</p>

      {complaints.isError ? (
        <p role="alert" className="mt-4 text-sm text-destructive">
          {t.loadError}
        </p>
      ) : null}

      {sent ? (
        <p role="status" className="mt-4 rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          {t.successMessage}
        </p>
      ) : null}

      {open ? (
        <div className="mt-4 rounded-lg border border-warning/30 bg-warning/10 p-4" data-testid="complaint-open">
          <p className="text-sm font-semibold text-warning">{t.openStatusTitle}</p>
          <p className="mt-1 text-sm text-foreground">{t.openStatusText}</p>
          <p className="mt-2 text-sm text-foreground">{t.category[open.category]}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {t.submittedOn.replace("{date}", formatDate(open.created_at))}
          </p>
        </div>
      ) : formOpen ? (
        <form
          className="mt-4 space-y-4"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            handleSubmit();
          }}
        >
          <div>
            <Label htmlFor="complaint-category">{t.categoryLabel}</Label>
            <select
              id="complaint-category"
              className={FIELD_CLASS}
              value={category}
              onChange={(event) => setCategory(event.target.value as ComplaintCategory)}
            >
              {COMPLAINT_CATEGORIES.map((key) => (
                <option key={key} value={key}>
                  {t.category[key]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="complaint-description">{t.descriptionLabel}</Label>
            <textarea
              id="complaint-description"
              className={cn(FIELD_CLASS, "min-h-[120px]")}
              required
              aria-required="true"
              maxLength={COMPLAINT_DESCRIPTION_MAX}
              aria-describedby="complaint-description-hint"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
            <p id="complaint-description-hint" className="mt-1 text-xs text-muted-foreground">
              {t.descriptionHint.replace("{min}", String(COMPLAINT_DESCRIPTION_MIN))}
            </p>
          </div>

          <div>
            <Label htmlFor="complaint-evidence">{t.evidenceLabel}</Label>
            <select
              id="complaint-evidence"
              className={FIELD_CLASS}
              value={evidenceId}
              disabled={attachable.length === 0}
              aria-describedby="complaint-evidence-hint"
              onChange={(event) => setEvidenceId(event.target.value)}
            >
              <option value="">{t.evidenceNone}</option>
              {attachable.map((record) => (
                <option key={record.id} value={record.id}>
                  {t.evidenceOption
                    .replace("{deliverable}", record.deliverable)
                    .replace("{date}", formatDate(record.createdAt))}
                </option>
              ))}
            </select>
            <p id="complaint-evidence-hint" className="mt-1 text-xs text-muted-foreground">
              {attachable.length === 0 ? t.evidenceEmptyHint : t.evidenceNotice}
            </p>
          </div>

          <p className="text-xs text-muted-foreground">{t.processNote}</p>

          {formError ? (
            <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {formError}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? t.submittingButton : t.submitButton}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={mutation.isPending}
              onClick={() => {
                setFormOpen(false);
                setFormError(null);
              }}
            >
              {t.cancelButton}
            </Button>
          </div>
        </form>
      ) : (
        <Button
          type="button"
          variant="secondary"
          className="mt-4"
          onClick={() => {
            setSent(false);
            setFormOpen(true);
          }}
        >
          {t.openButton}
        </Button>
      )}

      {decided.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-sm font-semibold text-foreground">{t.historyTitle}</h3>
          <ul className="mt-2 space-y-3">
            {decided.map((complaint) => (
              <ComplaintCard key={complaint.id} complaint={complaint} />
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
