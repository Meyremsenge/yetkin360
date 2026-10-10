/**
 * PLAN 2.12 (YET-74/98/99) + YET-195: Kanıt (evidence) yükleme API katmanı — gerçek backend akışı:
 *   1) POST /evidence/upload-url  → imzalı yükleme URL'si + alanları (presigned POST, PUT değil)
 *   2) Dosyanın doğrudan depolamaya (MinIO) yüklenmesi (multipart/form-data)
 *   3) POST /evidence             → kanıt kaydı (scan_status=PENDING)
 *   4) GET  /evidence             → talent'ın kendi kanıtları; tarama sonucu (scan_status) buradan okunur
 *
 * Tarama backend'de outbox worker'ında (magic-byte + boyut + içerik tipi) asenkron yapılır;
 * PENDING → CLEAN/FAILED geçişi için liste periyodik yeniden okunur (bkz. evidence-upload-form.tsx).
 */

import { apiFetch } from "./client";
import { ApiError } from "./errors";

export type EvidenceKind = "DOCUMENT" | "IMAGE" | "CERTIFICATE";
export type ScanStatus = "PENDING" | "CLEAN" | "INFECTED" | "FAILED";

export interface EvidenceRecord {
  id: string;
  deliverable_id: string | null;
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

function unexpectedResponse(): ApiError {
  return new ApiError({ status: 502, code: "UNKNOWN_ERROR", message: "Beklenmeyen yanıt.", requestId: null });
}

// ============================================================================
// Adım 1: POST /evidence/upload-url
// ============================================================================
export async function requestUploadUrl(file: File): Promise<UploadUrlResponse> {
  const response = await apiFetch<UploadUrlResponse>("/evidence/upload-url", {
    method: "POST",
    body: { filename: file.name, content_type: file.type, size_bytes: file.size },
  });
  if (!response) throw unexpectedResponse();
  return response;
}

// ============================================================================
// Adım 2: Depolamaya (MinIO) fiili yükleme — presigned POST (PUT değil)
// ============================================================================
export async function uploadFileToStorage(
  uploadUrl: string,
  uploadFields: Record<string, string>,
  file: File
): Promise<void> {
  const formData = new FormData();
  Object.entries(uploadFields).forEach(([key, value]) => formData.append(key, value));
  // S3 presigned POST: "file" alanı en son eklenmeli.
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
// Adım 3/4: POST /evidence (kayıt) ve GET /evidence (liste)
// ============================================================================

// Backend EvidenceResponse (backend/app/schemas/evidence.py) — alan adı storage_key.
interface EvidenceApiResponse {
  id: string;
  kind: EvidenceKind;
  provenance: "SELF_UPLOADED";
  storage_key: string;
  mime_type: string;
  size_bytes: number;
  scan_status: ScanStatus;
  deliverable_id: string | null;
  created_at: string;
}

function toRecord(item: EvidenceApiResponse): EvidenceRecord {
  return {
    id: item.id,
    deliverable_id: item.deliverable_id,
    kind: item.kind,
    provenance: item.provenance,
    object_key: item.storage_key,
    mime_type: item.mime_type,
    size_bytes: item.size_bytes,
    scan_status: item.scan_status,
    created_at: item.created_at,
  };
}

export interface RecordEvidenceInput {
  /** Omitted for evidence outside an engagement (profile showcase files). */
  deliverable_id?: string;
  object_key: string;
  kind: EvidenceKind;
  mime_type: string;
  size_bytes: number;
}

export async function recordEvidence(input: RecordEvidenceInput): Promise<EvidenceRecord> {
  const response = await apiFetch<EvidenceApiResponse>("/evidence", {
    method: "POST",
    body: {
      storage_key: input.object_key,
      kind: input.kind,
      mime_type: input.mime_type,
      size_bytes: input.size_bytes,
      deliverable_id: input.deliverable_id,
    },
  });
  if (!response) throw unexpectedResponse();
  return toRecord(response);
}

export async function listEvidenceForDeliverable(deliverableId: string): Promise<EvidenceRecord[]> {
  const response = await apiFetch<EvidenceApiResponse[]>(
    `/evidence?deliverable_id=${encodeURIComponent(deliverableId)}`
  );
  if (!response) throw unexpectedResponse();
  return response.map(toRecord);
}

// ============================================================================
// PLAN 3.55: sertifika kontrolü (öğrencinin açık rızasıyla, AI karar vermez)
// ============================================================================

export type CertificateCheckStatus = "PENDING" | "DONE" | "FAILED";
export type CertificateCheckDecision = "PENDING" | "CONFIRMED" | "REJECTED";

export interface CertificateCheck {
  id: string;
  evidence_id: string;
  status: CertificateCheckStatus;
  provider: "UDEMY" | "COURSERA" | "UNKNOWN" | null;
  credential_id: string | null;
  verify_url: string | null;
  qr_raw_data: string | null;
  extracted_name: string | null;
  name_match: boolean | null;
  page_name: string | null;
  page_match: boolean | null;
  decision: CertificateCheckDecision;
  decided_by_user_id: string | null;
  decided_at: string | null;
  created_at: string;
}

/** Öğrencinin açık rızasıyla tetiklenir — upload anında otomatik değil (KVKK). */
export async function requestCertificateCheck(evidenceId: string): Promise<CertificateCheck> {
  const response = await apiFetch<CertificateCheck>(`/evidence/${evidenceId}/request-certificate-check`, {
    method: "POST",
  });
  if (!response) throw unexpectedResponse();
  return response;
}

export async function listCertificateChecksForEngagement(engagementId: string): Promise<CertificateCheck[]> {
  const response = await apiFetch<{ items: CertificateCheck[] }>(
    `/engagements/${engagementId}/certificate-checks`
  );
  if (!response) throw unexpectedResponse();
  return response.items;
}

/** Koordinatör/supervisor kararı — AI bu kararı asla vermez. */
export async function resolveCertificateCheck(
  checkId: string,
  decision: "CONFIRMED" | "REJECTED"
): Promise<CertificateCheck> {
  const response = await apiFetch<CertificateCheck>(`/certificate-checks/${checkId}/resolve`, {
    method: "POST",
    body: { decision },
  });
  if (!response) throw unexpectedResponse();
  return response;
}
