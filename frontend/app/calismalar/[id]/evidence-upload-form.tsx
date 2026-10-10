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
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

/**
 * PLAN 2.12/YET-98/YET-99: 3 adımlı kanıt yükleme akışı (upload-url → depolama → kayıt)
 * + ilerleme göstergesi + hata durumları (dosya reddi, tarama bekleniyor).
 *
 * Gerçek backend akışı (bkz. lib/api/evidence.ts). Tarama backend'de worker tarafından
 * asenkron yapılır (PENDING → CLEAN/FAILED); bekleyen kayıt varken liste periyodik yeniden okunur.
 */

const POLL_INTERVAL_MS = 3000;

const SCAN_STATUS_CLASS: Record<ScanStatus, string> = {
  PENDING: "bg-warning/10 text-warning",
  CLEAN: "bg-success/10 text-success",
  INFECTED: "bg-destructive/10 text-destructive",
  FAILED: "bg-destructive/10 text-destructive",
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

  const hasPending = items.some((item) => item.scan_status === "PENDING");

  useEffect(() => {
    (async () => {
      try {
        await refresh();
      } catch {
        setError(messages.errors.generic);
      }
    })();
  }, [refresh]);

  useEffect(() => {
    if (!hasPending) return;
    const interval = setInterval(() => {
      refresh().catch(() => {});
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [hasPending, refresh]);

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
    <div className="mt-3">
      {items.length > 0 && (
        <ul className="mb-3 space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2 text-xs"
            >
              <span className="flex items-center gap-2.5 text-foreground">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-sand font-mono text-[10px] font-medium uppercase text-foreground">
                  {(item.mime_type.split("/")[1] ?? "").slice(0, 4)}
                </span>
                <span className="font-mono text-muted-foreground">{(item.size_bytes / 1024).toFixed(0)} KB</span>
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

      <label
        htmlFor={`evidence-file-${deliverableId}`}
        className={cn(
          "flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-muted-foreground/30 bg-card px-4 py-3 text-sm transition-colors hover:border-success hover:bg-success/[0.04] focus-within:border-success",
          step !== "idle" && "pointer-events-none opacity-60"
        )}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success" aria-hidden="true">
          <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
          </svg>
        </span>
        <span className="text-foreground">{messages.calismalar.evidenceUploadLabel}</span>
      </label>
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
        className="sr-only"
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
