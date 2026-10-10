import { z } from "zod";
import type { ComplaintAction, ComplaintStatus } from "@/lib/api/complaints";

export const MAX_ATTACHMENTS = 5;
export const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;
export const ALLOWED_ATTACHMENT_TYPES = ["application/pdf", "image/jpeg", "image/png"] as const;
export const DESCRIPTION_MIN = 10;
export const DESCRIPTION_MAX = 2000;

export const complaintFormSchema = z.object({
  description: z.string().trim().min(DESCRIPTION_MIN, "descriptionMin").max(DESCRIPTION_MAX, "descriptionMax"),
});
export type ComplaintFormValues = z.infer<typeof complaintFormSchema>;

export const explanationSchema = z.object({
  text: z.string().trim().min(DESCRIPTION_MIN, "minError").max(DESCRIPTION_MAX, "descriptionMax"),
});
export type ExplanationFormValues = z.infer<typeof explanationSchema>;

/** UX-only pre-check; the server validates magic bytes and size (AC-S12). */
export function validateAttachment(file: File): "fileType" | "fileSize" | null {
  if (!(ALLOWED_ATTACHMENT_TYPES as readonly string[]).includes(file.type)) return "fileType";
  if (file.size > MAX_ATTACHMENT_BYTES) return "fileSize";
  return null;
}

const REASON_REQUIRED: ReadonlySet<ComplaintAction> = new Set([
  "DISMISS",
  "REJECT_EXPLANATION",
  "RESOLVE",
  "UPHOLD",
  "REQUEST_EXPLANATION",
]);

/** Text is the admin `reason` for most actions and the `note` for REQUEST_EXPLANATION. */
export function actionRequiresReason(action: ComplaintAction): boolean {
  return REASON_REQUIRED.has(action);
}

export function transitionSchema(action: ComplaintAction) {
  const text = actionRequiresReason(action)
    ? z.string().trim().min(1, "required").max(DESCRIPTION_MAX, "descriptionMax")
    : z.string().trim().max(DESCRIPTION_MAX, "descriptionMax");
  return z.object({ text });
}

// UX hint only: which actions to offer per status. The server is authoritative.
const ALLOWED: Partial<Record<ComplaintStatus, ComplaintAction[]>> = {
  OPEN: ["START_REVIEW", "DISMISS", "REQUEST_EXPLANATION"],
  UNDER_REVIEW: ["DISMISS", "REQUEST_EXPLANATION"],
  // REJECT_EXPLANATION only passes once the respondent's deadline is over (else 409).
  EXPLANATION_REQUESTED: ["REJECT_EXPLANATION", "RESOLVE"],
  EXPLANATION_SUBMITTED: ["ACCEPT_EXPLANATION", "REJECT_EXPLANATION"],
  ESCALATED: ["RESOLVE", "UPHOLD"],
};

export function allowedActions(status: ComplaintStatus | null | undefined): ComplaintAction[] {
  return status ? [...(ALLOWED[status] ?? [])] : [];
}

const TERMINAL = new Set(["DISMISSED", "RESOLVED", "UPHELD"]);
export function isTerminalStatus(status: string | null | undefined): boolean {
  return !!status && TERMINAL.has(status);
}

export function isUpheldBadgeVisible(count: number | null | undefined): count is number {
  return typeof count === "number" && Number.isFinite(count) && count > 0;
}
