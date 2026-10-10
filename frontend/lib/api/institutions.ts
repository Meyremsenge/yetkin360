/**
 * PLAN 3.9 — Koordinator dashboard API client.
 * AC-1/AC-2/AC-3/AC-6/AC-7: GET /institutions/{id}/dashboard
 * Returns DashboardResponse or throws ApiError/NetworkError
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export interface InstitutionResponse {
  id: string;
  name: string;
  domain: string | null;
  verification_level: string;
  status: string;
}

/**
 * YET-202/ENT-01: Yeni kurum oluşturur, çağıran otomatik ADMIN olur.
 * `domain` şema'da kabul edilse de backend'de GUV-09 ile hep `None`a sabitlenir
 * (domain-squatting riski — bkz. backend/app/api/institutions.py) — bu yüzden
 * burada domain parametresi bile yok, forma da eklenmeyecek.
 * Router prefix+"/" → gerçek yol "/institutions/" (organizations.ts'teki
 * aynı 307-redirect nedeniyle sondaki / ile doğrudan çağrılır).
 */
export async function createInstitution(name: string): Promise<InstitutionResponse> {
  const response = await apiFetch<InstitutionResponse>("/institutions/", {
    method: "POST",
    body: { name },
  });
  if (!response) {
    throw new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
  }
  return response;
}

export interface PendingItem {
  id: string;
  talent_id: string;
  organization_id: string;
  title: string;
  started_on?: string | null;
  ended_on?: string | null;
}

export interface DashboardMemberItem {
  user_id: string;
  email: string;
  role: string;
  joined_at: string;
}

export interface DashboardResponse {
  institution_id: string;
  summary: {
    pending_approval: number;
    pending_evaluation: number;
  };
  pending_approval: PendingItem[];
  pending_evaluation: PendingItem[];
  members: DashboardMemberItem[];
}

/**
 * Fetch coordinator dashboard for given institution.
 * AC-1: Happy path — returns summary + two lists
 * AC-2: Empty lists — returns summary with 0 counts
 * AC-3/AC-4: 404/401 — throws ApiError
 * AC-5: Network/500 — throws NetworkError/ApiError
 * AC-6: Caller must use institution_id in queryKey for cache isolation
 */
export async function getCoordinatorDashboard(
  institutionId: string
): Promise<DashboardResponse | undefined> {
  return apiFetch<DashboardResponse>(`/institutions/${institutionId}/dashboard`);
}

/**
 * YET-197/IS-10: Student requests to link their talent profile to an institution.
 * Institution shares its id via a link (e.g. /kurum/{id}/baglan) — no search/picker UI.
 * Throws ApiError 409 if a PENDING request already exists, 404 if institution not found.
 */
export async function requestInstitutionLink(institutionId: string): Promise<void> {
  await apiFetch(`/institutions/${institutionId}/link-requests`, { method: "POST" });
}

/** YET-197/IS-10: Coordinator/Admin approves a PENDING link request for their institution. */
export async function approveLinkRequest(institutionId: string, requestId: string): Promise<void> {
  await apiFetch(`/institutions/${institutionId}/link-requests/${requestId}/approve`, { method: "POST" });
}

/** YET-197/IS-10: Coordinator/Admin rejects a PENDING link request for their institution. */
export async function rejectLinkRequest(institutionId: string, requestId: string): Promise<void> {
  await apiFetch(`/institutions/${institutionId}/link-requests/${requestId}/reject`, { method: "POST" });
}

export interface PendingLinkRequestItem {
  id: string;
  talent_profile_id: string;
  talent_full_name: string;
  status: string;
  requested_at: string;
}

/** YET-197/IS-10: Coordinator/Admin lists PENDING link requests for their institution. */
export async function listPendingLinkRequests(
  institutionId: string
): Promise<{ items: PendingLinkRequestItem[] } | undefined> {
  return apiFetch<{ items: PendingLinkRequestItem[] }>(`/institutions/${institutionId}/link-requests`);
}

export interface MyLinkRequestItem {
  id: string;
  institution_id: string;
  institution_name: string;
  status: string;
  requested_at: string;
  decided_at: string | null;
}

/** YET-197/IS-10: Authenticated talent lists their own link request history (all statuses). */
export async function listMyLinkRequests(): Promise<{ items: MyLinkRequestItem[] } | undefined> {
  return apiFetch<{ items: MyLinkRequestItem[] }>("/talents/me/institution-link-requests");
}

export type InstitutionMemberRole = "ADMIN" | "COORDINATOR";

/**
 * YET-202/ENT-01: Institution ADMIN invites a new member by email.
 * Always 202 {"status":"queued"} on success — new member, already-member, and
 * unknown-email all look the same on the wire (no account-existence leak).
 * Throws ApiError 404 if caller is not an ADMIN of this institution, 422 INVALID_ROLE.
 */
export async function inviteMember(
  institutionId: string,
  email: string,
  role: InstitutionMemberRole
): Promise<{ status: string } | undefined> {
  return apiFetch<{ status: string }>(`/institutions/${institutionId}/members`, {
    method: "POST",
    body: { email, role },
  });
}

/**
 * YET-202/ENT-01: Coordinator/Admin sends reminders for the given engagement ids.
 * Backend applies no status filter — the caller decides which ids to send.
 * 202 {"queued_count": number}. 422 on empty engagement_ids/template.
 */
export async function createReminders(
  institutionId: string,
  engagementIds: string[],
  template: string
): Promise<{ queued_count: number } | undefined> {
  return apiFetch<{ queued_count: number }>(`/institutions/${institutionId}/reminders`, {
    method: "POST",
    body: { engagement_ids: engagementIds, template },
  });
}

export interface InstitutionStudentItem {
  talent_profile_id: string;
  full_name: string;
  department: string | null;
  study_year: number | null;
  /** Only set when the student's profile is PUBLIC. */
  public_slug: string | null;
  verified_count: number;
  in_progress_count: number;
  total_count: number;
}

/**
 * Students linked to the institution (approved link, profile not PRIVATE) with their
 * engagement counts for this institution. Coordinator/Admin only; others get 404.
 */
export async function listInstitutionStudents(
  institutionId: string
): Promise<{ items: InstitutionStudentItem[] } | undefined> {
  return apiFetch<{ items: InstitutionStudentItem[] }>(`/institutions/${institutionId}/students`);
}
