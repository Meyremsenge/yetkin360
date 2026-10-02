/**
 * PLAN 2.11/2.12: Engagement (Çalışma) listesi/detay/durum geçişi API katmanı.
 *
 * BACKEND GAP — bkz. obss_project/artifacts/yet-73-96-97-engagement-frontend-mock/ENTEGRASYON_NOTU.md:
 *  - GET /engagements (liste) backend'de YOK (backend/app/api/engagements.py sadece POST uçları içeriyor).
 *  - GET /engagements/{id} (detay) YOK.
 *  - GET /me principal.kind/role döndürmüyor (backend/app/api/me.py) → availableTransitions()
 *    rol bazlı değil, SADECE durum bazlı hesaplanıyor. Gerçek yetkilendirme sunucuda
 *    POST /transitions çağrısında uygulanır (403/422/409 arayüzde ele alınır — bkz. YET-97).
 *
 * GERÇEK OLAN: POST /engagements/{id}/transitions ZATEN VAR (backend/app/api/engagements.py:236).
 * transitionEngagement() bu yüzden gerçek bir engagement ID'si için doğrudan bu uca gider;
 * mock listedeki ID'ler için ise mock store üzerinde AYNI durum makinesi kurallarını simüle eder
 * (backend/app/services/engagement.py:257-292 ile birebir eşleşir).
 *
 * MOCK STORE = localStorage (anahtar: STORAGE_KEY). Bilinçli tercih: gerçek backend tek bir DB
 * üzerinden TÜM sekmelere/istemcilere aynı durumu gösterir; bir `let` modül değişkeni ise her
 * tarayıcı sekmesinde AYRI bir JS belleği olduğu için sekmeler arasında paylaşılmaz (manuel test
 * sırasında gözlendi — iki sekmede aynı engagement'a çelişen geçişler ikisi de "başarılı" görünür).
 * localStorage aynı origin'deki tüm sekmelerce paylaşıldığı için versiyon çatışması (409) gerçekçi
 * şekilde test edilebiliyor. Sayfa sert yenilense (F5) DAHİ veri kalıcı — sıfırlamak için tarayıcı
 * konsolunda `localStorage.removeItem("yetkin360_mock_engagements_v2")` çalıştırıp sayfayı yenile.
 *
 * SİLME NOKTASI: backend GET /engagements + GET /engagements/{id} eklendiğinde:
 *   1. USE_MOCK_LIST ve USE_MOCK_DETAIL'i false yap.
 *   2. "MOCK STORE" bölümünü (STORAGE_KEY, seedEngagements, loadStore, saveStore, findMock, toSummary)
 *      ve transitionEngagement() içindeki mock dallanmasını sil.
 *   3. availableTransitions()/isReasonRequired() KALIR (backend rol bilgisi /me'ye eklenene kadar
 *      bunlar hâlâ gerekli — ayrı bir backend gap'i).
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
// PENDING_EVALUATION sonrası (EVALUATED/VERIFIED/DISPUTED/RESOLVED) bilinçli
// olarak hepsi boş dizi: docs/STATE_MACHINE.md §4 T7-T10.
//  - T7 (→EVALUATED): sistem tarafından otomatik tetiklenir (değerlendirme
//    gönderimi, bkz. lib/api/evaluation.ts) — bu genel /transitions ucundan
//    GEÇMEZ, dolayısıyla burada aday olarak sunulamaz.
//  - T8 (EVALUATED→VERIFIED): ayrı bir uçtan yapılır (POST .../attestations,
//    bkz. backend/app/api/engagements.py T8 yorumu) — bu da /transitions
//    değil, dolayısıyla burada aday değil.
//  - T9/T10 (DISPUTED/RESOLVED): STATE_MACHINE.md §7'de "vakit kalırsa" —
//    backend'de hiç gerçeklenmemiş (ne /transitions'ta ne ayrı bir uçta).
const NEXT_STATUSES: Record<EngagementStatus, EngagementStatus[]> = {
  DRAFT: ["PENDING_APPROVAL"],
  PENDING_APPROVAL: ["ACTIVE", "REJECTED"],
  ACTIVE: ["CANCELLED", "PENDING_EVALUATION"],
  REJECTED: [],
  CANCELLED: [],
  PENDING_EVALUATION: [],
  EVALUATED: [],
  VERIFIED: [],
  DISPUTED: [],
  RESOLVED: [],
};

const REASON_REQUIRED = new Set<EngagementStatus>(["REJECTED", "CANCELLED"]);

export function availableTransitions(status: EngagementStatus): EngagementStatus[] {
  return NEXT_STATUSES[status] ?? [];
}

export function isReasonRequired(toStatus: EngagementStatus): boolean {
  return REASON_REQUIRED.has(toStatus);
}

// ============================================================================
// MOCK STORE (localStorage) — backend GET /engagements + GET /engagements/{id}
// eklenince silinecek. Bkz. dosya başındaki not: localStorage seçildi çünkü
// aynı origin'deki tüm sekmeler tarafından paylaşılıyor (gerçek DB gibi).
// ============================================================================
const USE_MOCK_LIST = true; // TODO(backend): GET /engagements eklenince false yap, mock'u sil
const USE_MOCK_DETAIL = true; // TODO(backend): GET /engagements/{id} eklenince false yap, mock'u sil

// NOT: seedEngagements() değiştiğinde (yeni/silinen mock kayıt) bu versiyonu artır.
// loadStore() anahtar VARSA yeniden tohumlamıyor — versiyon artışı olmadan
// tarayıcıda kalıcı eski veri sessizce yeni seed'i maskeler (bkz. mock-eng-5 eklenirken
// yaşanan "Çalışma bulunamadı" sorunu — manuel localStorage temizliği gerekti).
const STORAGE_KEY = "yetkin360_mock_engagements_v2";

function seedEngagements(): EngagementDetail[] {
  return [
    {
      id: "mock-eng-1",
      title: "Frontend Staj Programı",
      kind: "INTERNSHIP",
      status: "DRAFT",
      organization_name: "Acme Yazılım A.Ş.",
      talent_id: "mock-talent-1",
      organization_id: "mock-org-1",
      institution_id: "mock-inst-1",
      reason: null,
      version: 1,
      created_at: "2026-09-10T09:00:00Z",
      updated_at: "2026-09-10T09:00:00Z",
      tasks: [],
      deliverables: [],
    },
    {
      id: "mock-eng-2",
      title: "Bitirme Projesi — Öneri Sistemi",
      kind: "CAPSTONE",
      status: "PENDING_APPROVAL",
      organization_name: "Veri Bilimi A.Ş.",
      talent_id: "mock-talent-1",
      organization_id: "mock-org-2",
      institution_id: "mock-inst-1",
      reason: null,
      version: 1,
      created_at: "2026-09-12T09:00:00Z",
      updated_at: "2026-09-12T09:00:00Z",
      tasks: [],
      deliverables: [],
    },
    {
      id: "mock-eng-3",
      title: "Yaz Kısa Projesi — API Entegrasyonu",
      kind: "SHORT_PROJECT",
      status: "ACTIVE",
      organization_name: "Bulut Sistemleri Ltd.",
      talent_id: "mock-talent-1",
      organization_id: "mock-org-3",
      institution_id: null,
      reason: null,
      version: 2,
      created_at: "2026-09-01T09:00:00Z",
      updated_at: "2026-09-18T14:30:00Z",
      tasks: [
        { id: "mock-task-1", title: "API şeması çıkarımı", status: "DONE" },
        { id: "mock-task-2", title: "Entegrasyon testleri", status: "IN_PROGRESS" },
      ],
      deliverables: [
        { id: "mock-del-1", title: "API entegrasyon raporu", submitted_at: "2026-09-17T10:00:00Z" },
      ],
    },
    {
      id: "mock-eng-4",
      title: "Yarı Zamanlı Backend Görevi",
      kind: "PART_TIME",
      status: "REJECTED",
      organization_name: "Fintek A.Ş.",
      talent_id: "mock-talent-1",
      organization_id: "mock-org-4",
      institution_id: "mock-inst-1",
      reason: "Kontenjan dolduğu için reddedildi.",
      version: 2,
      created_at: "2026-08-28T09:00:00Z",
      updated_at: "2026-09-05T09:00:00Z",
      tasks: [],
      deliverables: [],
    },
    {
      id: "mock-eng-5",
      title: "Kısa Süreli Tasarım Danışmanlığı",
      kind: "SHORT_PROJECT",
      status: "PENDING_EVALUATION",
      organization_name: "Tasarım Atölyesi Ltd.",
      talent_id: "mock-talent-1",
      organization_id: "mock-org-5",
      institution_id: "mock-inst-1",
      reason: null,
      version: 3,
      created_at: "2026-08-20T09:00:00Z",
      updated_at: "2026-09-20T11:00:00Z",
      tasks: [{ id: "mock-task-3", title: "Arayüz tasarım gözden geçirmesi", status: "DONE" }],
      deliverables: [
        { id: "mock-del-2", title: "Tasarım sistemi dokümanı", submitted_at: "2026-09-19T16:00:00Z" },
      ],
    },
  ];
}

function hasLocalStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function loadStore(): EngagementDetail[] {
  if (!hasLocalStorage()) {
    return seedEngagements();
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const seeded = seedEngagements();
      saveStore(seeded);
      return seeded;
    }
    return JSON.parse(raw) as EngagementDetail[];
  } catch {
    return seedEngagements();
  }
}

function saveStore(items: EngagementDetail[]): void {
  if (!hasLocalStorage()) {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // localStorage dolu/erişilemez olabilir (gizli sekme vb.) — mock için kritik değil.
  }
}

function findInStore(store: EngagementDetail[], id: string): EngagementDetail | undefined {
  return store.find((e) => e.id === id);
}

function toSummary(e: EngagementDetail): EngagementSummary {
  const { id, title, kind, status, organization_name, version, updated_at } = e;
  return { id, title, kind, status, organization_name, version, updated_at };
}

// ============================================================================
// Public API
// ============================================================================

export async function listEngagements(): Promise<{ items: EngagementSummary[] }> {
  if (USE_MOCK_LIST) {
    return { items: loadStore().map(toSummary) };
  }
  const response = await apiFetch<{ items: EngagementSummary[] }>("/engagements");
  return response ?? { items: [] };
}

export async function getEngagement(id: string): Promise<EngagementDetail> {
  if (USE_MOCK_DETAIL) {
    const found = findInStore(loadStore(), id);
    if (!found) {
      throw new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: "Engagement bulunamadı.",
        requestId: null,
      });
    }
    return found;
  }
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
  const store = USE_MOCK_DETAIL ? loadStore() : undefined;
  const mock = store ? findInStore(store, id) : undefined;

  if (!mock || !store) {
    // Gerçek engagement — gerçek uca git (bu uç zaten backend'de mevcut).
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

  // --- Mock durum makinesi simülasyonu (backend/app/services/engagement.py ile birebir) ---
  if (mock.version !== payload.version) {
    throw new ApiError({
      status: 409,
      code: "CONFLICT",
      message: "Kayıt başka tarafından değiştirilmiş. Lütfen yeniden yükleyin.",
      requestId: null,
    });
  }

  const allowed = availableTransitions(mock.status);
  if (!allowed.includes(payload.to_status)) {
    throw new ApiError({
      status: 422,
      code: "ILLEGAL_TRANSITION",
      message: `Bu durumdan '${payload.to_status}' durumuna geçiş yapılamaz.`,
      requestId: null,
    });
  }

  if (isReasonRequired(payload.to_status) && (!payload.reason || !payload.reason.trim())) {
    throw new ApiError({
      status: 422,
      code: "PRECONDITION_FAILED",
      message: "Bu geçiş için gerekçe zorunludur.",
      requestId: null,
    });
  }

  mock.status = payload.to_status;
  mock.version += 1;
  mock.reason = payload.reason ?? mock.reason;
  mock.updated_at = new Date().toISOString();

  saveStore(store);

  return mock;
}
