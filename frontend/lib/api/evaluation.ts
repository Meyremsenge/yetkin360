/**
 * PLAN 2.13 (YET-75/100/101): Kurum tarafı değerlendirme formu API katmanı.
 * Sözleşme: docs/API.md §2.8 — POST /engagements/{id}/evaluation.
 *
 * BACKEND DURUMU: bu uç backend'de HİÇ YOK (PLAN 2.7 "Değerlendirme formu şeması"
 * henüz yazılmadı — PLAN.md'de 2.9 notu: "EVALUATION kaynağı hâlâ açık, 2.7'ye bağımlı").
 * Her koşulda mock (localStorage) — backend PLAN 2.7'yi tamamlayınca gerçek
 * apiFetch çağrısına çevrilecek (aşağıda tek fonksiyon: submitEvaluation).
 *
 * KAPSAM DIŞI (bilinçli): `items[].skill_id` için bir yetkinlik seçici UI'ı
 * eklenmedi — ticket metni sadece "items[], rating" diyor, skill ilişkilendirme
 * ayrı bir iterasyon. Mock'ta her item'ın skill_id'si null gönderiliyor.
 *
 * KAPSAM DIŞI (bilinçli): docs/STATE_MACHINE.md T7 (PENDING_EVALUATION → EVALUATED,
 * otomatik) tetikleyicisi dokümanda AÇIK SORU olarak işaretli (tek yön mü, karşılıklı
 * mı gerekiyor). Bu yüzden mock, evaluation kaydedildiğinde engagement.status'u
 * DEĞİŞTİRMİYOR — bu karar backend'de netleşmeden frontend'in taklit etmesi yanlış
 * bir varsayım üretir.
 */

import { ApiError } from "./errors";
import { getEngagement } from "./engagements";
import type { EvaluationFormData } from "@/lib/evaluation/schemas";

export type EvaluationDirection = "ORG_TO_TALENT" | "TALENT_TO_ORG";

export interface EvaluationRecord {
  id: string;
  engagement_id: string;
  direction: EvaluationDirection;
  submitted_at: string;
  // private_note KASITLI OLARAK burada yok — D9 (docs/DOMAIN.md): hiçbir okuma
  // ucunda dönmez, kendi gönderdiğin isteğin yanıtında da tutarlılık için.
}

const EVALUATION_STORAGE_KEY = "yetkin360_mock_evaluations_v1";

function hasLocalStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

interface StoredEvaluation extends EvaluationRecord {
  private_note?: string;
}

function loadStore(): StoredEvaluation[] {
  if (!hasLocalStorage()) return [];
  try {
    const raw = window.localStorage.getItem(EVALUATION_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredEvaluation[]) : [];
  } catch {
    return [];
  }
}

function saveStore(items: StoredEvaluation[]): void {
  if (!hasLocalStorage()) return;
  try {
    window.localStorage.setItem(EVALUATION_STORAGE_KEY, JSON.stringify(items));
  } catch {
    // localStorage dolu/erişilemez olabilir — mock için kritik değil.
  }
}

/**
 * Bu engagement + direction için zaten gönderilmiş bir değerlendirme var mı?
 * (backend UNIQUE (engagement_id, evaluator_user_id, direction) kısıtının
 * mock karşılığı — evaluator_user_id burada tek mock kullanıcıya sabit).
 */
export async function hasSubmittedEvaluation(
  engagementId: string,
  direction: EvaluationDirection
): Promise<boolean> {
  return loadStore().some((e) => e.engagement_id === engagementId && e.direction === direction);
}

export async function submitEvaluation(
  engagementId: string,
  direction: EvaluationDirection,
  form: EvaluationFormData
): Promise<EvaluationRecord> {
  // AC (docs/API.md §2.8): 422 INVALID_STATUS — sadece PENDING_EVALUATION durumunda gönderilebilir.
  const engagement = await getEngagement(engagementId);
  if (engagement.status !== "PENDING_EVALUATION") {
    throw new ApiError({
      status: 422,
      code: "INVALID_STATUS",
      message: "Bu çalışma şu anda değerlendirme aşamasında değil.",
      requestId: null,
    });
  }

  // AC: 409 ALREADY_SUBMITTED — append-only, aynı yön için ikinci kez gönderilemez.
  if (await hasSubmittedEvaluation(engagementId, direction)) {
    throw new ApiError({
      status: 409,
      code: "ALREADY_SUBMITTED",
      message: "Bu çalışma için değerlendirme zaten gönderilmiş.",
      requestId: null,
    });
  }

  const record: StoredEvaluation = {
    id: `mock-evaluation-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    engagement_id: engagementId,
    direction,
    submitted_at: new Date().toISOString(),
    private_note: form.private_note,
  };

  const store = loadStore();
  store.push(record);
  saveStore(store);

  const { id, engagement_id, submitted_at } = record;
  return { id, engagement_id, direction, submitted_at };
}
