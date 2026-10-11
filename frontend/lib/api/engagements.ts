/**
 * PLAN 2.11/2.12: Engagement (Çalışma) listesi/detay/durum geçişi API katmanı.
 *
 * SPRINT A: Hangi düğmenin gösterileceğine sunucu karar verir — GET /engagements/{id}
 * yanıtındaki `viewer` bloğu, yazma uçlarının kabul edeceğini birebir söyler
 * (backend tests/authorization/test_engagement_viewer_capabilities.py). Durum bazlı
 * tahmin kaldırıldı; yetki kararı yine her çağrıda sunucuda verilir.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type EngagementStatus =
  | "DRAFT"
  | "PENDING_APPROVAL"
  | "ACTIVE"
  | "REJECTED"
  | "CANCELLED"
  | "PENDING_EVALUATION"
  | "EVALUATED"
  | "VERIFIED"
  | "DISPUTED"
  | "RESOLVED";

export type EngagementKind = "INTERNSHIP" | "CAPSTONE" | "SHORT_PROJECT" | "PART_TIME";

export interface EngagementSummary {
  id: string;
  title: string;
  kind: EngagementKind;
  status: EngagementStatus;
  organization_id: string;
  institution_id: string | null;
  organization_name: string;
  version: number;
  updated_at: string;
  /** Çalışmanın sahibi öğrenci; kuruluş/kurum listesi öğrenciye göre gösterilir. */
  talent_id: string;
  talent_name: string;
  /** SPRINT D1 (sunucu her zaman gönderir; eski yanıtlarla uyum için isteğe bağlı). */
  institution_name?: string | null;
  /** SPRINT D1: kuruluşta onaya atanan kişi (yoksa genel: kuruluş yöneticisi). */
  supervisor_user_id?: string | null;
}

export interface EngagementTask {
  id: string;
  title: string;
  status: string;
  /** false: öğrencinin eklediği, kuruluş/kurum henüz onaylamadığı görev. */
  verified: boolean;
}

export interface EngagementDeliverable {
  id: string;
  title: string;
  submitted_at: string;
}

export interface EngagementAttestation {
  id: string;
  claim_type: string;
  requested_claim_type: string;
  attestor_user_id: string;
  created_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
}

export type ViewerRelation =
  | "SUBJECT"
  | "ORG_ADMIN"
  | "ORG_MEMBER"
  | "COORDINATOR"
  | "INSTITUTION_ADMIN"
  | "OBSERVER";

/** SPRINT A: what the signed-in viewer may do on this engagement (server-computed). */
export interface EngagementViewer {
  relation: ViewerRelation;
  /** Targets POST /transitions will accept; EVALUATED→VERIFIED is never here (see can_attest). */
  allowed_transitions: EngagementStatus[];
  /** Subset of allowed_transitions that needs a reason. */
  reason_required: EngagementStatus[];
  can_add_task: boolean;
  can_add_deliverable: boolean;
  /** Organization-side (ORG_TO_TALENT) evaluation form. */
  can_evaluate: boolean;
  can_attest: boolean;
  /** Informational: the seal is still allowed but will be recorded as participation. */
  attest_blocker: "ORG_NOT_VERIFIED" | null;
}

/** SPRINT D1: the engagement's approver — name and unit only, never the e-mail. */
export interface EngagementSupervisor {
  user_id: string;
  display_name: string;
  unit: string | null;
}

// The detail response identifies the student by id only.
export interface EngagementDetail
  extends Omit<EngagementSummary, "talent_name" | "institution_name" | "supervisor_user_id"> {
  talent_id: string;
  organization_id: string;
  institution_id: string | null;
  reason: string | null;
  created_at: string;
  tasks: EngagementTask[];
  deliverables: EngagementDeliverable[];
  attestations: EngagementAttestation[];
  viewer: EngagementViewer;
  supervisor: EngagementSupervisor | null;
}

export interface TransitionPayload {
  to_status: EngagementStatus;
  version: number;
  reason?: string;
  /** DRAFT → PENDING_APPROVAL, isteğe bağlı: onay isteğinin iletileceği kurum koordinatörleri. */
  notify_emails?: string[];
  /** DRAFT → PENDING_APPROVAL, isteğe bağlı: listApprovalRecipients'ten seçilen koordinatörler. Yoksa hepsine gider. */
  notify_user_ids?: string[];
}

/** Çalışmanın okulundaki koordinatörler; e-posta yalnız maskeli gelir. */
export interface ApprovalRecipient {
  user_id: string;
  display_name: string;
  email_hint: string;
}

// ============================================================================
// Public API
// ============================================================================

export interface ListEngagementsOptions {
  /** "me": only engagements I was assigned to approve (SPRINT D1). */
  assigned?: "me";
  /** Only this organization's engagements; never widens what I may see. */
  organizationId?: string;
  limit?: number;
}

// Also handed to React Query directly as a queryFn, which passes its own context
// object: only the known option keys are read, so that context is ignored.
export async function listEngagements(
  options: ListEngagementsOptions | object = {}
): Promise<{ items: EngagementSummary[] }> {
  const { assigned, organizationId, limit } = options as ListEngagementsOptions;
  const params = new URLSearchParams();
  if (assigned === "me") params.set("assigned", assigned);
  if (typeof organizationId === "string" && organizationId) params.set("organization_id", organizationId);
  if (typeof limit === "number") params.set("limit", String(limit));
  const query = params.toString();
  const response = await apiFetch<{ items: EngagementSummary[] }>(`/engagements${query ? `?${query}` : ""}`);
  return response ?? { items: [] };
}

export interface CreateEngagementInput {
  talent_id: string;
  organization_id: string;
  kind: EngagementKind;
  title: string;
  institution_id?: string;
  /** SPRINT D1: optional approver from GET /organizations/{id}/approvers. */
  supervisor_user_id?: string;
}

/**
 * POST /engagements ve /transitions AYNI dar şemayı döner (PostEngagementResponse) —
 * organization_name/tasks/deliverables/attestations YOK (bunlar sadece GET detay'da
 * var). EngagementDetail'ı burada dönüş tipi olarak kullanmak yanlış olurdu — sadece
 * id'ye ihtiyacımız var (oluşturduktan sonra detay sayfasına yönlendirmek için),
 * o da kendi GET'ini yapıp tam veriyi çeker.
 */
export interface CreateEngagementResponse {
  id: string;
  talent_id: string;
  organization_id: string;
  institution_id: string | null;
  kind: EngagementKind;
  title: string;
  status: EngagementStatus;
  version: number;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * YET-202/ENT-01: TALENT kendi engagement'ını oluşturur (link-tabanlı akış —
 * organization_id paylaşılan linkten gelir, talent_id/institution_id oturumdan
 * otomatik doldurulur, bkz. calismalar/olustur/page.tsx). institution_id
 * verilirse talent.institution_id'yle eşleşmek ZORUNDA (backend kontrolü) —
 * bu yüzden burada hep oturumdaki değer gönderilir, elle girilmez.
 */
export async function createEngagement(input: CreateEngagementInput): Promise<CreateEngagementResponse> {
  const response = await apiFetch<CreateEngagementResponse>("/engagements", {
    method: "POST",
    body: input,
  });
  if (!response) {
    throw new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
  }
  return response;
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

/**
 * DRAFT çalışmayı onaya gönderebilen kişi için okulun koordinatörleri.
 * Kapsam dışı / taslak değil / okulsuz → 404.
 */
export async function listApprovalRecipients(id: string): Promise<ApprovalRecipient[]> {
  const response = await apiFetch<ApprovalRecipient[]>(`/engagements/${id}/approval-recipients`);
  if (!response) {
    throw new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
  }
  return response;
}

/** "Yeni çalışma" formu için: kullanıcının kendi okulunun koordinatörleri. Okulu yoksa 404. */
export async function listOwnApprovalRecipients(): Promise<ApprovalRecipient[]> {
  const response = await apiFetch<ApprovalRecipient[]>("/engagements/approval-recipients");
  if (!response) {
    throw new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
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
