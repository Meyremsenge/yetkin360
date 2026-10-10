/**
 * YET-202/ENT-01: Organizasyon oluşturma + panel (üye davet, alan adı doğrulama) API katmanı.
 * Sözleşme: backend/app/api/organizations.py.
 *
 * NOT: create/verify-domain uçları bazı hata dallarında ApiError yerine düz
 * string `detail` ile HTTPException fırlatıyor (institutions/members ile aynı
 * desende değil) — global http_exception_handler SCREAMING_SNAKE string'leri
 * doğrudan `code` olarak kullanıyor, değilse status'e göre jenerik koda düşüyor.
 * Pratik sonuç: create'te 422 (boş ad VEYA geçersiz domain) ayırt edilemez,
 * ikisi de code=VALIDATION_ERROR olarak gelir — backend'de böyle, frontend
 * bunu "düzeltmeye" çalışmaz.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type OrgMemberRole = "ADMIN" | "MEMBER";

export interface CreateOrganizationInput {
  name: string;
  domain?: string;
  legal_id?: string;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  domain: string | null;
  legal_id: string | null;
  verification_level: string;
  status: string;
  /** SPRINT D2: backend her zaman döndürür; eski test fikstürleri bozulmasın diye opsiyonel. */
  showcase_public?: boolean;
}

export interface DomainVerifyResult {
  dns_txt_record: string;
  status: "verified" | "pending";
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

export async function createOrganization(input: CreateOrganizationInput): Promise<OrganizationResponse> {
  // Router prefix "/organizations" + route "/" → gerçek yol "/organizations/".
  // Taraflı yol (sondaki / olmadan) 307 redirect alır — doğrudan gerçek yolu
  // çağırmak, fetch'in redirect'te method/body/header'ları koruma davranışına
  // (spec'e göre doğru ama gereksiz bir ekstra round-trip) güvenmekten daha sağlam.
  const response = await apiFetch<OrganizationResponse>("/organizations/", {
    method: "POST",
    body: input,
  });
  if (!response) throw unexpectedResponse();
  return response;
}

export async function getOrganization(organizationId: string): Promise<OrganizationResponse> {
  const response = await apiFetch<OrganizationResponse>(`/organizations/${organizationId}`);
  if (!response) throw unexpectedResponse();
  return response;
}

/**
 * AC-1/AC-2/AC-4: her zaman 202 {"status":"queued"} — hesap var/yok sızıntısı yok.
 * SPRINT D2: isteğe bağlı birim (en fazla 60 karakter, boş → birimsiz).
 */
export async function inviteOrgMember(
  organizationId: string,
  email: string,
  role: OrgMemberRole,
  unit?: string | null
): Promise<{ status: string }> {
  const body = unit === undefined ? { email, role } : { email, role, unit };
  const response = await apiFetch<{ status: string }>(`/organizations/${organizationId}/members`, {
    method: "POST",
    body,
  });
  if (!response) throw unexpectedResponse();
  return response;
}

/**
 * AC-6/AC-7/AC-8: DNS TXT kontrolü. "pending" bir hata değildir — kayıt henüz
 * bulunamadı demektir, dns_txt_record her durumda (verified/pending) döner.
 */
export async function verifyDomain(organizationId: string): Promise<DomainVerifyResult> {
  const response = await apiFetch<DomainVerifyResult>(`/organizations/${organizationId}/verify-domain`, {
    method: "POST",
  });
  if (!response) throw unexpectedResponse();
  return response;
}

/**
 * PLAN 3.53: öğrencinin "Yeni Çalışma" başlatırken serbestçe arayıp
 * seçebileceği kuruluş dizini. Sözleşme: backend GET /organizations
 * (scoped_organization_directory — üyelikten bağımsız, tenant-scoping'in
 * kasıtlı istisnası, legal_id/status döndürmez).
 */
export interface OrganizationDirectoryEntry {
  id: string;
  name: string;
  domain: string | null;
  verification_level: string;
}

export async function listOrganizationDirectory(q?: string): Promise<OrganizationDirectoryEntry[]> {
  // Router prefix "/organizations" + route "/" → gerçek yol "/organizations/"
  // (createOrganization'daki aynı 307-redirect notu geçerli).
  const query = q?.trim() ? `?q=${encodeURIComponent(q.trim())}` : "";
  const response = await apiFetch<{ items: OrganizationDirectoryEntry[] }>(`/organizations/${query}`);
  if (!response) throw unexpectedResponse();
  return response.items;
}

/**
 * SPRINT D2: ekip listesi. Kuruluşun her üyesi görür; `email` yalnız çağıran
 * ADMIN ise dolu, değilse null. `open_assigned_count` = kişinin onaylayıcı
 * olduğu açık (ACTIVE / PENDING_EVALUATION / EVALUATED) çalışma sayısı.
 */
export interface OrgMember {
  user_id: string;
  display_name: string;
  role: OrgMemberRole;
  unit: string | null;
  open_assigned_count: number;
  email: string | null;
}

export async function listOrgMembers(organizationId: string): Promise<OrgMember[]> {
  const response = await apiFetch<OrgMember[]>(`/organizations/${organizationId}/members`);
  if (!response) throw unexpectedResponse();
  return response;
}

/** SPRINT D2: yalnız ADMIN. null (veya boş metin) birimi temizler; 61+ karakter → 422 INVALID_UNIT. */
export async function updateMemberUnit(
  organizationId: string,
  userId: string,
  unit: string | null
): Promise<OrgMember> {
  const response = await apiFetch<OrgMember>(`/organizations/${organizationId}/members/${userId}`, {
    method: "PATCH",
    body: { unit },
  });
  if (!response) throw unexpectedResponse();
  return response;
}

/**
 * SPRINT D2: öğrencinin çalışmayı onaya gönderirken seçebileceği onaylayıcılar.
 * E-posta ve rol bilinçli olarak yok. Keşfet ile ortak hız sınırı → 429 RATE_LIMITED.
 */
export interface Approver {
  user_id: string;
  display_name: string;
  unit: string | null;
}

export async function listApprovers(organizationId: string): Promise<Approver[]> {
  const response = await apiFetch<Approver[]>(`/organizations/${organizationId}/approvers`);
  if (!response) throw unexpectedResponse();
  return response;
}

/** SPRINT D2: yalnız ADMIN. En az bir alan gerekir (alan adı veya vitrin anahtarı). */
export interface OrganizationUpdateInput {
  domain?: string;
  showcase_public?: boolean;
}

export async function updateOrganization(
  organizationId: string,
  input: OrganizationUpdateInput
): Promise<OrganizationResponse> {
  const response = await apiFetch<OrganizationResponse>(`/organizations/${organizationId}`, {
    method: "PATCH",
    body: input,
  });
  if (!response) throw unexpectedResponse();
  return response;
}
