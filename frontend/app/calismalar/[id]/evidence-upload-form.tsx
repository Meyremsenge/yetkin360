"use client";

import { useCallback, useEffect, useState } from "react";
import {
  validateFile,
  requestUploadUrl,
  uploadFileToStorage,
  recordEvidence,
  listEvidenceForDeliverable,
  type EvidenceRecord,
  type ScanStatus,
} from "@/lib/api/evidence";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";

/**
 * PLAN 2.12/YET-98/YET-99: 3 adımlı kanıt yükleme akışı (upload-url → depolama → kayıt)
 * + ilerleme göstergesi + hata durumları (dosya reddi, tarama bekleniyor).
 *
 * Adımların tamamı mock (bkz. lib/api/evidence.ts dosya başı notu) — bu oturumda
 * backend+MinIO çalışmıyor. scan_status, kısa bir gecikmeyle otomatik PENDING →
 * CLEAN/INFECTED'e döndüğü için bileşen periyodik olarak yeniden okuyor.
 */

const SCAN_STATUS_CLASS: Record<ScanStatus, string> = {
  PENDING: "bg-amber-100 text-amber-700",
  CLEAN: "bg-green-100 text-green-700",
  INFECTED: "bg-red-100 text-red-700",
  FAILED: "bg-red-100 text-red-700",
};

type Step = "idle" | "requesting_url" | "uploading" | "recording";

const STEP_MESSAGE_KEY: Record<
  Exclude<Step, "idle">,
  "evidenceStepUploadUrl" | "evidenceStepUploading" | "evidenceStepRecording"
> = {
  requesting_url: "evidenceStepUploadUrl",
  uploading: "evidenceStepUploading",
  recording: "evidenceStepRecording",
};

export function EvidenceUploadForm({ deliverableId }: { deliverableId: string }) {
  const [items, setItems] = useState<EvidenceRecord[]>([]);
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setItems(await listEvidenceForDeliverable(deliverableId));
  }, [deliverableId]);

  useEffect(() => {
    refresh();
    // Mock tarama sonucu arka planda kendiliğinden değişiyor (bkz. lib/api/evidence.ts:
    // scheduleMockScanResolution) — bileşenin bunu göstermesi için periyodik yeniden okuma.
    const interval = setInterval(refresh, 1000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setError(null);

    // Dosya reddi (YET-99): sunucuya gitmeden önce client-side kontrol.
    const validation = validateFile(file);
    if (!validation.ok) {
      setError(validation.message);
      return;
    }

    try {
      setStep("requesting_url");
      const uploadUrlResponse = await requestUploadUrl(file);

      setStep("uploading");
      await uploadFileToStorage(uploadUrlResponse.upload_url, uploadUrlResponse.upload_fields, file);

      setStep("recording");
      await recordEvidence({
        deliverable_id: deliverableId,
        object_key: uploadUrlResponse.object_key,
        kind: validation.kind,
        mime_type: file.type,
        size_bytes: file.size,
      });

      await refresh();
    } catch {
      setError(messages.errors.generic);
    } finally {
      setStep("idle");
    }
  };

  return (
    <div className="mt-2 pl-3 border-l-2 border-slate-200">
      {items.length > 0 && (
        <ul className="space-y-1 mb-2">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between text-xs">
              <span className="text-slate-600">
                {item.mime_type} · {(item.size_bytes / 1024).toFixed(0)} KB
              </span>
              <span
                className={`px-2 py-0.5 rounded-full font-medium ${SCAN_STATUS_CLASS[item.scan_status]}`}
              >
                {messages.calismalar.evidenceScanStatus[item.scan_status]}
              </span>
            </li>
          ))}
        </ul>
      )}

      <Label htmlFor={`evidence-file-${deliverableId}`} className="text-xs">
        {messages.calismalar.evidenceUploadLabel}
      </Label>
      {/* `accept` UX kolaylığı için var: işletim sistemi dosya seçicisi uyumsuz dosyaları
          soluklaştırıp seçilemez yapar. Bu bir güvenlik sınırı DEĞİL — gerçek kontrol
          validateFile()'da MIME türüne bakıyor; `accept` bypass edilse (ör. sürükle-bırak,
          "Tüm dosyalar" seçeneği) yine validateFile() reddeder. */}
      <input
        id={`evidence-file-${deliverableId}`}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.docx"
        disabled={step !== "idle"}
        onChange={handleFileChange}
        className="block text-xs"
      />

      {step !== "idle" && (
        <p className="text-xs text-slate-500 mt-1">{messages.calismalar[STEP_MESSAGE_KEY[step]]}</p>
      )}

      {error && (
        <div role="alert" aria-live="polite" className="mt-1 text-xs text-red-600">
          {error}
        </div>
      )}
    </div>
  );
}
