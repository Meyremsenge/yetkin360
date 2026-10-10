"use client";

import { useCallback, useEffect, useState } from "react";
import {
  validateFile,
  requestUploadUrl,
  uploadFileToStorage,
  recordEvidence,
  listEvidenceForDeliverable,
  requestCertificateCheck,
  listCertificateChecksForEngagement,
  type EvidenceRecord,
  type ScanStatus,
  type CertificateCheck,
} from "@/lib/api/evidence";
import { ApiError } from "@/lib/api/errors";
import { Label } from "@/components/ui/label";
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

export function EvidenceUploadForm({
  deliverableId,
  engagementId,
}: {
  deliverableId: string;
  engagementId: string;
}) {
  const [items, setItems] = useState<EvidenceRecord[]>([]);
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isCertificate, setIsCertificate] = useState(false);
  const [checksByEvidenceId, setChecksByEvidenceId] = useState<Record<string, CertificateCheck>>({});
  const [requestingCheckFor, setRequestingCheckFor] = useState<string | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setItems(await listEvidenceForDeliverable(deliverableId));
  }, [deliverableId]);

  const refreshChecks = useCallback(async () => {
    const checks = await listCertificateChecksForEngagement(engagementId);
    setChecksByEvidenceId(Object.fromEntries(checks.map((c) => [c.evidence_id, c])));
  }, [engagementId]);

  const hasPending = items.some((item) => item.scan_status === "PENDING");
  const hasPendingCheck = Object.values(checksByEvidenceId).some((c) => c.status === "PENDING");

  useEffect(() => {
    (async () => {
      try {
        await refresh();
        await refreshChecks();
      } catch {
        setError(messages.errors.generic);
      }
    })();
  }, [refresh, refreshChecks]);

  useEffect(() => {
    if (!hasPending) return;
    const interval = setInterval(() => {
      refresh().catch(() => {});
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [hasPending, refresh]);

  useEffect(() => {
    if (!hasPendingCheck) return;
    const interval = setInterval(() => {
      refreshChecks().catch(() => {});
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [hasPendingCheck, refreshChecks]);

  const handleRequestCheck = async (evidenceId: string) => {
    setCheckError(null);
    setRequestingCheckFor(evidenceId);
    try {
      const check = await requestCertificateCheck(evidenceId);
      setChecksByEvidenceId((prev) => ({ ...prev, [evidenceId]: check }));
    } catch (err) {
      if (err instanceof ApiError && err.code === "ALREADY_REQUESTED") {
        setCheckError(messages.calismalar.certificateCheckAlreadyRequested);
      } else if (err instanceof ApiError && err.code === "EVIDENCE_NOT_CLEAN") {
        setCheckError(messages.calismalar.certificateCheckNotClean);
      } else {
        setCheckError(messages.errors.generic);
      }
    } finally {
      setRequestingCheckFor(null);
    }
  };

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
        kind: isCertificate ? "CERTIFICATE" : validation.kind,
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
          {items.map((item) => {
            const check = checksByEvidenceId[item.id];
            return (
              <li key={item.id} className="text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">
                    {item.mime_type} · {(item.size_bytes / 1024).toFixed(0)} KB
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full font-medium ${SCAN_STATUS_CLASS[item.scan_status]}`}
                  >
                    {messages.calismalar.evidenceScanStatus[item.scan_status]}
                  </span>
                </div>

                {item.kind === "CERTIFICATE" && item.scan_status === "CLEAN" && (
                  <div className="mt-1 pl-2 border-l border-slate-200">
                    {!check ? (
                      <button
                        type="button"
                        onClick={() => handleRequestCheck(item.id)}
                        disabled={requestingCheckFor === item.id}
                        className="text-xs text-blue-700 hover:underline disabled:text-slate-400"
                      >
                        {requestingCheckFor === item.id
                          ? messages.calismalar.certificateCheckRequestingButton
                          : messages.calismalar.certificateCheckRequestButton}
                      </button>
                    ) : (
                      <div className="space-y-0.5 text-slate-600">
                        <p className="font-medium text-slate-700">
                          {messages.calismalar.certificateCheckStatus[check.status]}
                        </p>
                        {check.status === "DONE" && (
                          <>
                            {check.provider && (
                              <p>
                                {messages.calismalar.certificateCheckProviderLabel}: {check.provider}
                              </p>
                            )}
                            {check.credential_id && (
                              <p>
                                {messages.calismalar.certificateCheckCredentialLabel}: {check.credential_id}
                              </p>
                            )}
                            {check.extracted_name && (
                              <p>
                                {messages.calismalar.certificateCheckNameLabel}: {check.extracted_name}{" "}
                                {check.name_match !== null && (
                                  <span className={check.name_match ? "text-green-700" : "text-red-700"}>
                                    (
                                    {check.name_match
                                      ? messages.calismalar.certificateCheckNameMatchYes
                                      : messages.calismalar.certificateCheckNameMatchNo}
                                    )
                                  </span>
                                )}
                              </p>
                            )}
                            {check.page_name && (
                              <p>
                                {messages.calismalar.certificateCheckPageNameLabel}: {check.page_name}{" "}
                                {check.page_match !== null && (
                                  <span className={check.page_match ? "text-green-700" : "text-red-700"}>
                                    (
                                    {check.page_match
                                      ? messages.calismalar.certificateCheckPageMatchYes
                                      : messages.calismalar.certificateCheckPageMatchNo}
                                    )
                                  </span>
                                )}
                              </p>
                            )}
                            {check.verify_url && (
                              <p>
                                <a
                                  href={check.verify_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-blue-700 hover:underline"
                                >
                                  {messages.calismalar.certificateCheckVerifyLinkLabel}
                                </a>
                              </p>
                            )}
                            <p className="italic">
                              {check.decision === "PENDING"
                                ? messages.calismalar.certificateCheckDecisionPending
                                : check.decision === "CONFIRMED"
                                  ? messages.calismalar.certificateCheckDecisionConfirmed
                                  : messages.calismalar.certificateCheckDecisionRejected}
                            </p>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {checkError && (
        <div role="alert" aria-live="polite" className="mb-2 text-xs text-red-600">
          {checkError}
        </div>
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

      <div className="mt-1 flex items-center gap-1.5">
        <input
          id={`evidence-is-certificate-${deliverableId}`}
          type="checkbox"
          checked={isCertificate}
          onChange={(e) => setIsCertificate(e.target.checked)}
          disabled={step !== "idle"}
          className="h-3 w-3"
        />
        <Label htmlFor={`evidence-is-certificate-${deliverableId}`} className="text-xs font-normal">
          {messages.calismalar.certificateCheckboxLabel}
        </Label>
      </div>
      {isCertificate && (
        <p className="mt-0.5 text-xs text-slate-500">{messages.calismalar.certificateCheckConsentHint}</p>
      )}

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
