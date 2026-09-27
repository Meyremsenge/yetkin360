/**
 * PLAN 2.11/2.12: Engagement (Çalışma) listesi/detay/durum geçişi API katmanı.
 *
 * GET /engagements (liste) ve GET /engagements/{id} (detay) artık gerçek backend uçları.
 * Mock store kaldırıldı — bkz. obss_project/artifacts/calismalar-gercek-backend-baglama/atdd.md.
 *
 * BACKEND GAP (kalan): GET /me principal.kind/role döndürmüyor (backend/app/api/me.py)
 * → availableTransitions() rol bazlı değil, SADECE durum bazlı hesaplanıyor.
 * Gerçek yetkilendirme sunucuda POST /transitions çağrısında uygulanır (403/422/409 arayüzde ele alınır).
 *
 * availableTransitions() ve isReasonRequired() kalır: backend rol bilgisi /me'ye eklenene kadar gerekli.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type EngagementStatus =
  | "DRAFT"
  | "PENDING_APPROVAL"
  | "ACTIVE"
  | "REJECTED"
  | "CANCELLED"
  | "PENDING_EVALUATION";

export type EngagementKind = "INTERNSHIP" | "CAPSTONE" | "SHORT_PROJECT" | "PART_TIME";

export interface EngagementSummary {
  id: string;
  title: string;
  kind: EngagementKind;
  status: EngagementStatus;
  organization_name: string;
  version: number;
  updated_at: string;
}

export interface EngagementTask {
  id: string;
  title: string;
  status: string;
}

export interface EngagementDeliverable {
  id: string;
  title: string;
  submitted_at: string;
}

export interface EngagementDetail extends EngagementSummary {
  talent_id: string;
  organization_id: string;
  institution_id: string | null;
  reason: string | null;
  created_at: string;
  tasks: EngagementTask[];
  deliverables: EngagementDeliverable[];
}

export interface TransitionPayload {
  to_status: EngagementStatus;
  version: number;
  reason?: string;
}

// ============================================================================
// Durum makinesi — backend/app/services/engagement.py:257-292 ile birebir eşleşir.
// Rol bilgisi /me'den gelmediği için SADECE durum bazlı aday geçişler hesaplanıyor;
// gerçek yetki sunucuda uygulanır (bkz. dosya başındaki BACKEND GAP notu).
// ============================================================================
const NEXT_STATUSES: Record<EngagementStatus, EngagementStatus[]> = {
  DRAFT: ["PENDING_APPROVAL"],
  PENDING_APPROVAL: ["ACTIVE", "REJECTED"],
  ACTIVE: ["CANCELLED", "PENDING_EVALUATION"],
  REJECTED: [],
  CANCELLED: [],
  PENDING_EVALUATION: [],
};

const REASON_REQUIRED = new Set<EngagementStatus>(["REJECTED", "CANCELLED"]);

export function availableTransitions(status: EngagementStatus): EngagementStatus[] {
  return NEXT_STATUSES[status] ?? [];
}

export function isReasonRequired(toStatus: EngagementStatus): boolean {
  return REASON_REQUIRED.has(toStatus);
}


// ============================================================================
// Public API
// ============================================================================

export async function listEngagements(): Promise<{ items: EngagementSummary[] }> {
  const response = await apiFetch<{ items: EngagementSummary[] }>("/engagements");
  return response ?? { items: [] };
}

export async function getEngagement(id: string): Promise<EngagementDetail> {
  const response = await apiFetch<EngagementDetail>(`/engagements/${id}`);
  if (!response) {
    throw new ApiError({
      status: 404,
      code: "NOT_FOUND",
      message: "Engagement bulunamadı.",
      requestId: null,
    });
  }
  return response;
}

export async function transitionEngagement(
  id: string,
  payload: TransitionPayload
): Promise<EngagementDetail> {
  const response = await apiFetch<EngagementDetail>(`/engagements/${id}/transitions`, {
    method: "POST",
    body: payload,
  });
  if (!response) {
    throw new ApiError({
      status: 502,
      code: "UNKNOWN_ERROR",
      message: "Beklenmeyen yanıt.",
      requestId: null,
    });
  }
  return response;
}
