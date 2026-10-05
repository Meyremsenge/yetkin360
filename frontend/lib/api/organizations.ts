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

/** AC-1/AC-2/AC-4: her zaman 202 {"status":"queued"} — hesap var/yok sızıntısı yok. */
export async function inviteOrgMember(
  organizationId: string,
  email: string,
  role: OrgMemberRole
): Promise<{ status: string }> {
  const response = await apiFetch<{ status: string }>(`/organizations/${organizationId}/members`, {
    method: "POST",
    body: { email, role },
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
