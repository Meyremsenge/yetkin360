"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { revokeAttestation } from "@/lib/api/attestations";
import type { EngagementAttestation } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";

/**
 * YET-202/ENT-01: Bir tanıklığı geri çeker — sadece attestor kendi verdiği
 * tanıklığı geri çekebilir (backend 403 döner, burada rol kontrolü yapılmaz).
 * Zaten geri çekilmiş bir tanıklık için buton yerine rozet+gerekçe gösterilir
 * (append-only felsefeyle uyumlu: geri çekilmiş kayıt asla "yok" gibi görünmez,
 * bkz. database.md — attestations UPDATE/DELETE yasak, tek istisna revoked_at/revoke_reason).
 */
export function AttestationRevoke({
  attestation,
  onSuccess,
}: {
  attestation: EngagementAttestation;
  onSuccess: () => void;
}) {
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => revokeAttestation(attestation.id, reason.trim()),
    onSuccess: () => {
      setFormError(null);
      setSuccessMessage(messages.calismalar.revokeAttestationSuccessMessage);
      onSuccess();
      setTimeout(() => setSuccessMessage(null), 2000);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setFormError(messages.calismalar.revokeAttestationForbiddenError);
          return;
        }
        if (error.code === "ALREADY_REVOKED") {
          setFormError(messages.calismalar.revokeAttestationAlreadyRevokedError);
          onSuccess(); // güncel veriyi getir — artık revoked_at dolu görünecek
          return;
        }
        if (error.code === "VALIDATION_ERROR") {
          setFormError(messages.calismalar.revokeAttestationReasonRequiredError);
          return;
        }
      }
      setFormError(messages.errors.generic);
    },
  });

  // transition-actions.tsx'teki desenle aynı: durum artık uygun değilse (revoked_at
  // dolmuş) AMA henüz okunmamış bir mesaj varsa erken dönme.
  if (attestation.revoked_at && !formError && !successMessage) {
    return (
      <div className="text-xs text-slate-600 mt-1">
        {messages.calismalar.attestationRevokedLabel}
        {attestation.revoke_reason ? `: ${attestation.revoke_reason}` : ""}
      </div>
    );
  }

  if (successMessage) {
    return (
      <div role="status" aria-live="polite" className="mt-2 rounded-md bg-green-50 border border-green-200 p-2 text-xs text-green-700">
        {successMessage}
      </div>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    mutation.mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex flex-wrap items-end gap-2">
      <div className="flex-1 min-w-[160px]">
        <Label htmlFor={`revoke-reason-${attestation.id}`}>{messages.calismalar.revokeReasonLabel}</Label>
        <Input
          id={`revoke-reason-${attestation.id}`}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          required
        />
      </div>
      <Button type="submit" disabled={mutation.isPending} className="bg-red-600 hover:bg-red-700">
        {mutation.isPending ? messages.calismalar.revokingAttestationButton : messages.calismalar.revokeAttestationButton}
      </Button>

      {formError && (
        <div role="alert" aria-live="polite" className="w-full mt-1 rounded-md bg-red-50 border border-red-200 p-2 text-xs text-red-600">
          {formError}
        </div>
      )}
    </form>
  );
}
