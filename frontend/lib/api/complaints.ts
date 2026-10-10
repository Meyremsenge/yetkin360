/**
 * Öğrenci şikayetleri API katmanı.
 *
 * Öğrenci: POST/GET /engagements/{id}/complaints (yalnız çalışmanın sahibi).
 * Admin:   GET /admin/complaints, POST /admin/complaints/{id}/resolve.
 *
 * Kuruluşun "kasıtlı doğrulamama" sayacı ayrı bir alan değil: haklı bulunan
 * (UPHELD) şikayetlerinin sayısıdır (organization_upheld_count).
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type ComplaintCategory = "TASK_APPROVAL" | "CERTIFICATE_APPROVAL" | "PERSONAL";
export type ComplaintStatus = "OPEN" | "UPHELD" | "DISMISSED";
export type ComplaintOutcome = Exclude<ComplaintStatus, "OPEN">;

export const COMPLAINT_CATEGORIES: ComplaintCategory[] = ["TASK_APPROVAL", "CERTIFICATE_APPROVAL", "PERSONAL"];
export const COMPLAINT_DESCRIPTION_MIN = 20;
export const COMPLAINT_DESCRIPTION_MAX = 2000;

export interface Complaint {
  id: string;
  engagement_id: string;
  category: ComplaintCategory;
  description: string;
  evidence_id: string | null;
  status: ComplaintStatus;
  decision_note: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface ComplaintInput {
  category: ComplaintCategory;
  description: string;
  /** Çalışmaya yüklenmiş, taraması tamamlanmış bir kanıt (isteğe bağlı). */
  evidence_id?: string;
}

export interface AdminComplaint {
  id: string;
  engagement_id: string;
  engagement_title: string;
  engagement_status: string;
  talent_name: string;
  organization_id: string;
  organization_name: string;
  /** Kuruluşun haklı bulunan şikayet sayısı ("kasıtlı doğrulamama" sayacı). */
  organization_upheld_count: number;
  category: ComplaintCategory;
  description: string;
  has_evidence: boolean;
  status: ComplaintStatus;
  decision_note: string | null;
  decided_at: string | null;
  created_at: string;
}

function unexpected(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

export async function listEngagementComplaints(engagementId: string): Promise<Complaint[]> {
  const response = await apiFetch<{ items: Complaint[] }>(`/engagements/${engagementId}/complaints`);
  return response?.items ?? [];
}

export async function createComplaint(engagementId: string, input: ComplaintInput): Promise<Complaint> {
  const response = await apiFetch<Complaint>(`/engagements/${engagementId}/complaints`, {
    method: "POST",
    body: input,
  });
  if (!response) throw unexpected();
  return response;
}

export async function getComplaintQueue(status: ComplaintStatus): Promise<AdminComplaint[]> {
  const response = await apiFetch<{ items: AdminComplaint[] }>(`/admin/complaints?status=${status}`);
  return response?.items ?? [];
}

export async function resolveComplaint(
  complaintId: string,
  outcome: ComplaintOutcome,
  note?: string
): Promise<AdminComplaint> {
  const response = await apiFetch<AdminComplaint>(`/admin/complaints/${complaintId}/resolve`, {
    method: "POST",
    body: note ? { outcome, note } : { outcome },
  });
  if (!response) throw unexpected();
  return response;
}

/**
 * Şikayete eklenen belge için kısa ömürlü indirme bağlantısı (yalnız admin).
 * Admin'in öğrencinin özel bir kanıtını okuyabildiği tek yol; her çağrı sunucuda kayda geçer.
 */
export async function getComplaintEvidenceUrl(complaintId: string): Promise<string> {
  const response = await apiFetch<{ download_url: string; expires_in: number }>(
    `/admin/complaints/${complaintId}/evidence-url`
  );
  if (!response) throw unexpected();
  return response.download_url;
}
