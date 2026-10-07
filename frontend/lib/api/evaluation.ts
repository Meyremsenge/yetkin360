/**
 * YET-203/ENT-02 (PLAN 2.13, YET-75/100/101): Kurum tarafı değerlendirme formu API katmanı.
 * Sözleşme: docs/API.md §2.8 — POST /engagements/{id}/evaluation (artık gerçek uç).
 *
 * Durum/yetki kontrolü (PENDING_EVALUATION mı, doğru rol mü, zaten gönderilmiş mi)
 * istemcide ÖN KONTROL olarak TEKRARLANMIYOR — hepsi sunucuda yapılıyor (404/403/409),
 * codebase'teki genel ilke: gerçek yetki her zaman sunucuda.
 *
 * KAPSAM DIŞI (bilinçli, değişmedi): `items[].skill_id` için bir yetkinlik seçici UI'ı
 * eklenmedi — ticket metni sadece "items[], rating" diyor, skill ilişkilendirme
 * ayrı bir iterasyon.
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";
import type { EvaluationFormData } from "@/lib/evaluation/schemas";

export type EvaluationDirection = "ORG_TO_TALENT" | "TALENT_TO_ORG";

export interface EvaluationItemRecord {
  id: string;
  criterion: string;
  skill_id: string | null;
  rating: string;
  comment: string | null;
}

export interface EvaluationRecord {
  id: string;
  engagement_id: string;
  direction: EvaluationDirection;
  items: EvaluationItemRecord[];
  submitted_at: string;
  // private_note KASITLI OLARAK burada yok — D9 (docs/DOMAIN.md): backend hiçbir
  // okuma ucunda döndürmüyor, bu isteğin yanıtında da yok.
}

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

export async function submitEvaluation(
  engagementId: string,
  direction: EvaluationDirection,
  form: EvaluationFormData
): Promise<EvaluationRecord> {
  const response = await apiFetch<EvaluationRecord>(`/engagements/${engagementId}/evaluation`, {
    method: "POST",
    body: {
      direction,
      items: form.items,
      private_note: form.private_note,
    },
  });
  if (!response) throw unexpectedResponse();
  return response;
}
