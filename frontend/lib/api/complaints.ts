/**
 * Complaint (şikayet) API layer — student, respondent and admin sides.
 *
 * Contract: backend/app/schemas/complaint.py + app/api/complaints.py,
 * app/api/admin_complaints.py. Backend views differ per viewer (owner, respondent,
 * admin); this module normalises them into one UI-facing `Complaint` shape so the
 * pages stay viewer-agnostic. Every field beyond the identifiers is optional.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";
import { uploadFileToStorage } from "./evidence";

export type ComplaintSubjectType = "ENGAGEMENT" | "CERTIFICATE_CHECK";

/** What a student may see: no internal intermediate state (AC-19). */
export type ComplaintStatusLabel = "IN_PROGRESS" | "DISMISSED" | "RESOLVED" | "UPHELD";

export type ComplaintStatus =
  | "OPEN"
  | "UNDER_REVIEW"
  | "EXPLANATION_REQUESTED"
  | "EXPLANATION_SUBMITTED"
  | "ESCALATED"
  | "DISMISSED"
  | "RESOLVED"
  | "UPHELD";

export type ComplaintAction =
  | "START_REVIEW"
  | "DISMISS"
  | "REQUEST_EXPLANATION"
  | "ACCEPT_EXPLANATION"
  | "REJECT_EXPLANATION"
  | "RESOLVE"
  | "UPHOLD";

export interface ComplaintAttachment {
  id: string;
  /** Backend stores no file name; only set for a file just uploaded in this session. */
  filename?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
}

export interface ComplaintEvent {
  id?: string | null;
  action?: string | null;
  from_status?: string | null;
  to_status?: string | null;
  note?: string | null;
  created_at?: string | null;
}

export interface Complaint {
  id: string;
  status?: ComplaintStatus | null;
  status_label: ComplaintStatusLabel;
  subject_type: ComplaintSubjectType;
  subject_id: string;
  /** Admin view: name of the institution/organization the complaint is about. */
  subject_label?: string | null;
  description?: string | null;
  created_at?: string | null;
  closed_at?: string | null;
  /** Admin's closing reason (owner and admin views). */
  result_reason?: string | null;
  /** The admin's request to the respondent (respondent and admin views). */
  admin_note?: string | null;
  explanation_text?: string | null;
  viewer_role?: "OWNER" | "RESPONDENT" | null;
  attachments?: ComplaintAttachment[] | null;
}

export interface AdminComplaint extends Complaint {
  subject_still_pending?: boolean | null;
  /** Optimistic-lock token; sent back with a transition (AC-20). */
  version?: number | null;
  events?: ComplaintEvent[] | null;
}

export interface AdminComplaintPage {
  items: AdminComplaint[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface CreateComplaintInput {
  subject_type: ComplaintSubjectType;
  subject_id: string;
  description: string;
}

export interface TransitionInput {
  action: ComplaintAction;
  reason?: string;
  note?: string;
  version?: number;
}

// --- backend wire shapes -------------------------------------------------------

interface AttachmentWire {
  id: string;
  mime_type?: string | null;
  size_bytes?: number | null;
}

interface EventWire {
  id?: string | null;
  event_type?: string | null;
  from_status?: string | null;
  to_status?: string | null;
  note?: string | null;
  created_at?: string | null;
}

/** Union of the owner, respondent, created and admin wire views. */
interface ComplaintWire {
  id: string;
  viewer_role?: "OWNER" | "RESPONDENT" | null;
  subject_type: ComplaintSubjectType;
  subject_id: string;
  status?: ComplaintStatus | null;
  status_label?: ComplaintStatusLabel | null;
  description?: string | null;
  resolution_reason?: string | null;
  request_note?: string | null;
  explanation_text?: string | null;
  subject_pending?: boolean | null;
  target_name?: string | null;
  version?: number | null;
  created_at?: string | null;
  closed_at?: string | null;
  attachments?: AttachmentWire[] | null;
  events?: EventWire[] | null;
}

const TERMINAL: ReadonlySet<string> = new Set(["DISMISSED", "RESOLVED", "UPHELD"]);

function labelFor(wire: ComplaintWire): ComplaintStatusLabel {
  if (wire.status_label) return wire.status_label;
  return wire.status && TERMINAL.has(wire.status) ? (wire.status as ComplaintStatusLabel) : "IN_PROGRESS";
}

function normalize(wire: ComplaintWire): AdminComplaint {
  return {
    id: wire.id,
    status: wire.status ?? null,
    status_label: labelFor(wire),
    subject_type: wire.subject_type,
    subject_id: wire.subject_id,
    subject_label: wire.target_name ?? null,
    description: wire.description ?? null,
    created_at: wire.created_at ?? null,
    closed_at: wire.closed_at ?? null,
    result_reason: wire.resolution_reason ?? null,
    admin_note: wire.request_note ?? null,
    explanation_text: wire.explanation_text ?? null,
    viewer_role: wire.viewer_role ?? null,
    subject_still_pending: wire.subject_pending ?? null,
    version: wire.version ?? null,
    attachments: wire.attachments
      ? wire.attachments.map((a) => ({ id: a.id, mime_type: a.mime_type ?? null, size_bytes: a.size_bytes ?? null }))
      : null,
    events: wire.events
      ? wire.events.map((e) => ({
          id: e.id ?? null,
          action: e.event_type ?? null,
          from_status: e.from_status ?? null,
          to_status: e.to_status ?? null,
          note: e.note ?? null,
          created_at: e.created_at ?? null,
        }))
      : null,
  };
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

function seg(id: string): string {
  return encodeURIComponent(id);
}

const PAGE_SIZE = 200;
const MAX_PAGES = 20;

/** Follows `has_more` so a long list is never silently truncated. */
async function fetchAllPages(path: string): Promise<ComplaintWire[]> {
  const all: ComplaintWire[] = [];
  let offset = 0;
  for (let page = 0; page < MAX_PAGES; page += 1) {
    const response = await apiFetch<{ items?: ComplaintWire[] | null; has_more?: boolean }>(
      `${path}?limit=${PAGE_SIZE}&offset=${offset}`,
    );
    all.push(...(response?.items ?? []));
    if (response?.has_more !== true) break;
    offset += PAGE_SIZE;
  }
  return all;
}

// --- student / respondent ---------------------------------------------------

export async function createComplaint(input: CreateComplaintInput): Promise<Complaint> {
  // Only these three fields are ever sent; org/respondent/status are server-derived (AC-S11).
  const response = await apiFetch<ComplaintWire>("/complaints", {
    method: "POST",
    body: {
      subject_type: input.subject_type,
      subject_id: input.subject_id,
      description: input.description,
    },
  });
  if (!response) throw unexpectedResponse();
  return normalize(response);
}

/** Own complaints plus the ones that concern the viewer as respondent, newest first. */
export async function listComplaints(): Promise<Complaint[]> {
  const [owned, assigned] = await Promise.all([fetchAllPages("/complaints"), fetchAllPages("/complaints/assigned")]);
  return [...owned, ...assigned]
    .map(normalize)
    .sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
}

export async function getComplaint(id: string): Promise<Complaint> {
  const response = await apiFetch<ComplaintWire>(`/complaints/${seg(id)}`);
  if (!response) throw unexpectedResponse();
  return normalize(response);
}

export async function submitExplanation(id: string, text: string): Promise<Complaint> {
  const response = await apiFetch<ComplaintWire>(`/complaints/${seg(id)}/explanation`, {
    method: "POST",
    body: { text },
  });
  if (!response) throw unexpectedResponse();
  return normalize(response);
}

interface UploadSlotWire {
  upload_url: string;
  upload_fields: Record<string, string>;
  object_key: string;
  expires_in: number;
}

/**
 * Same three-step presigned flow as evidence: upload-url → storage POST → record.
 * The backend verifies the content (magic bytes) when the record is created.
 */
export async function uploadAttachment(complaintId: string, file: File): Promise<ComplaintAttachment> {
  const slot = await apiFetch<UploadSlotWire>(`/complaints/${seg(complaintId)}/attachments/upload-url`, {
    method: "POST",
    body: { filename: file.name, content_type: file.type, size_bytes: file.size },
  });
  if (!slot) throw unexpectedResponse();

  await uploadFileToStorage(slot.upload_url, slot.upload_fields, file);

  const record = await apiFetch<AttachmentWire>(`/complaints/${seg(complaintId)}/attachments`, {
    method: "POST",
    body: { storage_key: slot.object_key, mime_type: file.type, size_bytes: file.size },
  });
  if (!record) throw unexpectedResponse();
  return { id: record.id, filename: file.name, mime_type: file.type, size_bytes: file.size };
}

/** Resolves a short-lived signed download URL; the endpoint answers JSON, not the file. */
export async function getAttachmentDownloadUrl(
  complaintId: string,
  attachmentId: string,
  options: { admin?: boolean } = {},
): Promise<string> {
  const base = options.admin ? "/admin/complaints" : "/complaints";
  const response = await apiFetch<{ download_url?: string | null }>(
    `${base}/${seg(complaintId)}/attachments/${seg(attachmentId)}`,
  );
  if (!response?.download_url) throw unexpectedResponse();
  return response.download_url;
}

// --- admin ------------------------------------------------------------------

export async function adminListComplaints(params: { limit?: number; offset?: number } = {}): Promise<AdminComplaintPage> {
  const limit = params.limit ?? 50;
  const offset = params.offset ?? 0;
  const response = await apiFetch<{
    items?: ComplaintWire[] | null;
    limit?: number;
    offset?: number;
    has_more?: boolean;
  }>(`/admin/complaints?limit=${limit}&offset=${offset}`);
  return {
    items: (response?.items ?? []).map(normalize),
    limit: response?.limit ?? limit,
    offset: response?.offset ?? offset,
    has_more: response?.has_more === true,
  };
}

export async function adminGetComplaint(id: string): Promise<AdminComplaint> {
  const response = await apiFetch<ComplaintWire>(`/admin/complaints/${seg(id)}`);
  if (!response) throw unexpectedResponse();
  return normalize(response);
}

export async function adminTransition(id: string, input: TransitionInput): Promise<AdminComplaint> {
  const response = await apiFetch<ComplaintWire>(`/admin/complaints/${seg(id)}/transitions`, {
    method: "POST",
    body: input,
  });
  if (!response) throw unexpectedResponse();
  return normalize(response);
}
