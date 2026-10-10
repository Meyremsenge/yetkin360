import type { Complaint } from "@/lib/api/complaints";
import messages from "@/messages/tr.json";

const TONE: Record<string, string> = {
  IN_PROGRESS: "border-warning/30 bg-warning/10 text-warning",
  DISMISSED: "border-border bg-muted text-foreground",
  RESOLVED: "border-success/30 bg-success/10 text-success",
  UPHELD: "border-destructive/30 bg-destructive/10 text-destructive",
};

/**
 * Student view shows only status_label (AC-19): open complaints are always
 * "İşlem devam etmekte", whatever the internal state. The internal status is
 * shown only to the respondent (viewer_role RESPONDENT), who needs it to act.
 */
export function ComplaintStatusBadge({ complaint }: { complaint: Complaint }) {
  const labels = messages.complaints.statusLabel as Record<string, string>;
  const internal = messages.adminComplaints.statusLabel as Record<string, string>;
  const isRespondent = complaint.viewer_role === "RESPONDENT";
  const text =
    isRespondent && complaint.status && internal[complaint.status]
      ? internal[complaint.status]
      : (labels[complaint.status_label] ?? labels.IN_PROGRESS);
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONE[complaint.status_label] ?? TONE.IN_PROGRESS}`}
    >
      {text}
    </span>
  );
}
