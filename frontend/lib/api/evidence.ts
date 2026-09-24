/**
 * PLAN 2.12 (YET-74/98/99): Kanıt (evidence) yükleme API katmanı — 3 adımlı akış:
 *   1) POST /evidence/upload-url  → imzalı yükleme URL'si + alanları
 *   2) Dosyanın doğrudan depolamaya (MinIO) yüklenmesi
 *   3) POST /evidence             → kanıt kaydının oluşturulması
 *
 * BACKEND DURUMU (bkz. obss_project/artifacts/yet-74-98-99-evidence-upload-mock/ENTEGRASYON_NOTU.md):
 *  - Adım 1 (POST /evidence/upload-url) backend'de GERÇEKTEN VAR (backend/app/api/evidence.py:31,
 *    PLAN 2.5/YET-82-83). Bu oturumda backend+MinIO çalışmadığı için MOCK'landı — kullanıcı onayıyla.
 *    Gerçek backend+MinIO ayaktayken USE_MOCK_UPLOAD_URL'i false yapmak yeterli.
 *  - Adım 2 (depolamaya fiili yükleme) de aynı sebeple MOCK'landı (USE_MOCK_STORAGE_UPLOAD).
 *    ÖNEMLİ: Backend presigned POST üretiyor (upload_url + upload_fields, multipart/form-data),
 *    PUT DEĞİL — Jira ticket metni "upload-url → PUT → POST /evidence" diyor ama gerçek backend
 *    şekli PUT değil. Gerçek entegrasyonda uploadFileToStorage() bir FormData POST yapmalı (aşağıda
 *    zaten öyle yazılı — sadece USE_MOCK_STORAGE_UPLOAD'ı false yapmak yeterli).
 *  - Adım 3 (POST /evidence, kanıt kaydı) backend'de HİÇ YOK (Evidence modeli/tablosu PLAN 2.6'da
 *    henüz oluşturulmadı). Bu adım HER KOŞULDA mock — backend PLAN 2.6/2.7'yi tamamlayınca
 *    gerçek çağrıyla değiştirilmeli (aşağıdaki recordEvidence() içindeki mock kaldırılacak).
 *  - Tarama sonucu (scan_status) burada deterministik bir zamanlayıcı ile simüle ediliyor
 *    (scheduleMockScanResolution, ~4s sonra PENDING → CLEAN). Gerçek sistemde bu bir arka
 *    plan worker + outbox ile asenkron gerçekleşir (bkz. .claude/rules/security.md —
 *    "Tarama bitmeden indirilemez"). INFECTED/FAILED render'ı otomatik testte sabit mock
 *    veriyle doğrulanıyor — burada rastgele üretilmiyor (manuel testte kafa karıştırıyordu).
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type EvidenceKind = "DOCUMENT" | "IMAGE";
export type ScanStatus = "PENDING" | "CLEAN" | "INFECTED" | "FAILED";

export interface EvidenceRecord {
  id: string;
  deliverable_id: string;
  kind: EvidenceKind;
  provenance: "SELF_UPLOADED";
  object_key: string;
  mime_type: string;
  size_bytes: number;
  scan_status: ScanStatus;
  created_at: string;
}

export interface UploadUrlResponse {
  upload_url: string;
  upload_fields: Record<string, string>;
  object_key: string;
  expires_in: number;
}

export type FileValidationResult =
  | { ok: true; kind: EvidenceKind }
  | { ok: false; code: string; message: string };

// Backend allowlist ile birebir (backend/app/services/storage.py: ALLOWED_CONTENT_TYPES).
// İki dosyada da elle tutuluyor — biri değişirse diğeri manuel güncellenmeli (paylaşılan paket yok).
const ALLOWED_CONTENT_TYPES: Record<string, EvidenceKind> = {
  "application/pdf": "DOCUMENT",
  "image/jpeg": "IMAGE",
  "image/png": "IMAGE",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCUMENT",
};

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // backend/app/core/config.py: evidence_max_size_bytes (10MB)

export function validateFile(file: File): FileValidationResult {
  const kind = ALLOWED_CONTENT_TYPES[file.type];
  if (!kind) {
    return {
      ok: false,
      code: "UNSUPPORTED_CONTENT_TYPE",
      message: "Desteklenmeyen dosya türü. İzin verilen türler: PDF, JPEG, PNG, DOCX.",
    };
  }
  if (file.size > MAX_SIZE_BYTES) {
    return {
      ok: false,
      code: "FILE_TOO_LARGE",
      message: `Dosya çok büyük. Maksimum izin verilen boyut: ${MAX_SIZE_BYTES / (1024 * 1024)}MB.`,
    };
  }
  return { ok: true, kind };
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

// ============================================================================
// Adım 1: POST /evidence/upload-url
// ============================================================================
const USE_MOCK_UPLOAD_URL = true; // TODO(backend+MinIO ayaktayken): false yap

export async function requestUploadUrl(file: File): Promise<UploadUrlResponse> {
  if (USE_MOCK_UPLOAD_URL) {
    await delay(300);
    const objectKey = `evidence/mock-talent-1/${randomId()}`;
    return {
      upload_url: "https://mock-minio.local/yetkin360-evidence",
      upload_fields: { key: objectKey, policy: "mock-policy", "x-amz-signature": "mock-signature" },
      object_key: objectKey,
      expires_in: 900,
    };
  }

  const response = await apiFetch<UploadUrlResponse>("/evidence/upload-url", {
    method: "POST",
    body: { filename: file.name, content_type: file.type, size_bytes: file.size },
  });
  if (!response) {
    throw new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
  }
  return response;
}

// ============================================================================
// Adım 2: Depolamaya (MinIO) fiili yükleme — presigned POST (PUT değil, bkz. dosya başı notu)
// ============================================================================
const USE_MOCK_STORAGE_UPLOAD = true; // TODO(backend+MinIO ayaktayken): false yap

export async function uploadFileToStorage(
  uploadUrl: string,
  uploadFields: Record<string, string>,
  file: File
): Promise<void> {
  if (USE_MOCK_STORAGE_UPLOAD) {
    await delay(600);
    return;
  }

  const formData = new FormData();
  Object.entries(uploadFields).forEach(([key, value]) => formData.append(key, value));
  formData.append("file", file);

  const response = await fetch(uploadUrl, { method: "POST", body: formData });
  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      code: "STORAGE_UPLOAD_FAILED",
      message: "Dosya depolamaya yüklenemedi.",
      requestId: null,
    });
  }
}

// ============================================================================
// Adım 3: POST /evidence — backend'de YOK, her koşulda mock (localStorage).
// ============================================================================
const EVIDENCE_STORAGE_KEY = "yetkin360_mock_evidence_v1";

function hasLocalStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function loadEvidenceStore(): EvidenceRecord[] {
  if (!hasLocalStorage()) return [];
  try {
    const raw = window.localStorage.getItem(EVIDENCE_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as EvidenceRecord[]) : [];
  } catch {
    return [];
  }
}

function saveEvidenceStore(items: EvidenceRecord[]): void {
  if (!hasLocalStorage()) return;
  try {
    window.localStorage.setItem(EVIDENCE_STORAGE_KEY, JSON.stringify(items));
  } catch {
    // localStorage dolu/erişilemez olabilir — mock için kritik değil.
  }
}

/**
 * Gerçek sistemde tarama bir arka plan worker'ı ile asenkron sonuçlanır.
 * Burada sadece manuel testte "tarama bekleniyor" durumunun (PENDING → sonuç) geçişinin
 * gözlenebilmesi için kısa bir gecikmeyle CLEAN sonucu simüle ediyoruz.
 *
 * Bilinçli olarak DETERMİNİSTİK: rastgele CLEAN/INFECTED denenmişti ama dosya içeriğiyle
 * hiçbir ilgisi olmayan bir "zar atma" olduğu için manuel testte kafa karıştırdı (kullanıcı
 * geri bildirimi). INFECTED rozetinin doğru render olduğu ayrıca sabit mock veriyle
 * otomatik testte doğrulanıyor (bkz. evidence-upload-form.test.tsx).
 */
function scheduleMockScanResolution(evidenceId: string): void {
  if (!hasLocalStorage()) return;
  setTimeout(() => {
    const store = loadEvidenceStore();
    const record = store.find((e) => e.id === evidenceId);
    if (!record || record.scan_status !== "PENDING") return;
    record.scan_status = "CLEAN";
    saveEvidenceStore(store);
  }, 4000);
}

export interface RecordEvidenceInput {
  deliverable_id: string;
  object_key: string;
  kind: EvidenceKind;
  mime_type: string;
  size_bytes: number;
}

export async function recordEvidence(input: RecordEvidenceInput): Promise<EvidenceRecord> {
  await delay(300);

  const record: EvidenceRecord = {
    id: `mock-evidence-${randomId()}`,
    deliverable_id: input.deliverable_id,
    kind: input.kind,
    provenance: "SELF_UPLOADED",
    object_key: input.object_key,
    mime_type: input.mime_type,
    size_bytes: input.size_bytes,
    scan_status: "PENDING",
    created_at: new Date().toISOString(),
  };

  const store = loadEvidenceStore();
  store.push(record);
  saveEvidenceStore(store);

  scheduleMockScanResolution(record.id);

  return record;
}

export async function listEvidenceForDeliverable(deliverableId: string): Promise<EvidenceRecord[]> {
  return loadEvidenceStore().filter((e) => e.deliverable_id === deliverableId);
}
