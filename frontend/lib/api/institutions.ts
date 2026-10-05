/**
 * PLAN 3.9 — Koordinator dashboard API client.
 * AC-1/AC-2/AC-3/AC-6/AC-7: GET /institutions/{id}/dashboard
 * Returns DashboardResponse or throws ApiError/NetworkError
 */

import { apiFetch } from "./client";

export interface PendingItem {
  id: string;
  talent_id: string;
  organization_id: string;
  title: string;
  started_on?: string | null;
  ended_on?: string | null;
}

export interface DashboardResponse {
  institution_id: string;
  summary: {
    pending_approval: number;
    pending_evaluation: number;
  };
  pending_approval: PendingItem[];
  pending_evaluation: PendingItem[];
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
