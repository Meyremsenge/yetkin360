/**
 * Kuruluş kayıt belgesi (Ticaret Sicili Gazetesi / faaliyet belgesi) kontrolü.
 *
 * DURUM: TAMAMEN MOCK — backend'de bu iş için bir uç YOK ve docs/API.md'de
 * sözleşmesi de yazılı değil. Kayıt sayfasındaki adım göstermeliktir:
 *   - Belge hiçbir yere gönderilmez ve saklanmaz; karekod/metin gerçekten OKUNMAZ.
 *   - Sonuç dosyanın içeriğine değil, yalnız formdaki beyana bağlıdır (deterministik,
 *     rastgelelik yok): kuruluş adı dolu ve MERSİS 16 haneliyse MATCH, değilse
 *     UNVERIFIED + manuel inceleme.
 *   - Sonuç hiçbir yetkiyi/doğrulama seviyesini etkilemez; kuruluş T1 olarak açılır,
 *     T3 kararı admin kuyruğundadır (docs/DOMAIN.md).
 * Ekran bu yüzden sonucun yanında "örnek sonuç" notunu gösterir.
 *
 * Gerçek uç yazıldığında: sözleşme docs/API.md'ye eklenir, aşağıdaki else dalı
 * gerçek çağrıyla doldurulur ve USE_MOCK_DOCUMENT_CHECK false yapılır.
 * Ayrıntı: obss_project/artifacts/kurulus-kayit-dogrulama/ENTEGRASYON_NOTU.md
 */

import { isValidMersis } from "@/lib/auth/schemas";

export const USE_MOCK_DOCUMENT_CHECK = true;

export const DOCUMENT_MAX_BYTES = 5 * 1024 * 1024;
export const DOCUMENT_ALLOWED_TYPES = ["application/pdf", "image/png", "image/jpeg"] as const;

export type DocumentCheckStatus = "MATCH" | "UNVERIFIED";

export interface OrganizationDocumentCheckResult {
  status: DocumentCheckStatus;
  qr_found: boolean;
  manual_review: boolean;
}

export interface OrganizationClaim {
  entity_name: string;
  legal_id: string;
}

export type DocumentRejection = "INVALID_TYPE" | "TOO_LARGE";

/** Gerçek, istemci taraflı ön kontrol: tür ve boyut. */
export function rejectDocument(file: File): DocumentRejection | null {
  if (!(DOCUMENT_ALLOWED_TYPES as readonly string[]).includes(file.type)) return "INVALID_TYPE";
  if (file.size > DOCUMENT_MAX_BYTES) return "TOO_LARGE";
  return null;
}

export async function checkOrganizationDocument(
  file: File,
  claim: OrganizationClaim
): Promise<OrganizationDocumentCheckResult> {
  if (USE_MOCK_DOCUMENT_CHECK) {
    const claimComplete = claim.entity_name.trim().length > 0 && isValidMersis(claim.legal_id.trim());
    return claimComplete
      ? { status: "MATCH", qr_found: true, manual_review: false }
      : { status: "UNVERIFIED", qr_found: false, manual_review: true };
  }

  // Backend ucu ve sözleşmesi henüz yok — uydurma bir yola istek atmak yerine açıkça hata ver.
  throw new Error(`Document check endpoint is not available yet (file: ${file.type}).`);
}
