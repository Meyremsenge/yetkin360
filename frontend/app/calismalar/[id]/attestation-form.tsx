"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createAttestation, type ClaimType } from "@/lib/api/attestations";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { SkillPicker } from "@/components/skill-picker";
import messages from "@/messages/tr.json";

const CLAIM_TYPES: ClaimType[] = ["PARTICIPATION", "CONTRIBUTION", "COMPETENCE", "CONDUCT"];

function claimTypeLabel(claimType: string): string {
  return (messages.calismalar.claimType as Record<string, string>)[claimType] ?? claimType;
}

function downgradeReasonLabel(reason: string): string {
  return (messages.calismalar.downgradeReason as Record<string, string>)[reason] ?? reason;
}

/**
 * YET-202/ENT-01: Engagement EVALUATED durumundayken tanıklık (attestation) verir —
 * STATE_MACHINE.md T8 (EVALUATED → VERIFIED), zincirin kilit taşı.
 *
 * Sadece COORDINATOR (institution_id varsa) / ORG_ADMIN (yoksa) çağırabilir — backend
 * 403/404 döner, burada rol kontrolü yapılmaz (transition-actions.tsx'teki felsefeyle aynı).
 *
 * downgrade_reasons dolu bir 201 yanıtı HATA DEĞİLDİR (COMPETENCE istenip PARTICIPATION
 * kaydedilmiş olabilir) — başarı mesajı olarak gösterilir.
 */
export function AttestationForm({
  engagement,
  onSuccess,
}: {
  engagement: EngagementDetail;
  onSuccess: () => void;
}) {
  const [claimType, setClaimType] = useState<ClaimType>("COMPETENCE");
  const [skillId, setSkillId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      createAttestation(engagement.id, {
        claim_type: claimType,
        version: engagement.version,
        skill_id: skillId ?? undefined,
      }),
    onSuccess: (data) => {
      setSkillId(null);
      setFormError(null);
      if (data.downgrade_reasons.length > 0) {
        const reasons = data.downgrade_reasons.map(downgradeReasonLabel).join(", ");
        setSuccessMessage(
          `${messages.calismalar.attestationDowngradedMessagePrefix} "${claimTypeLabel(data.requested_claim_type)}" ${messages.calismalar.attestationDowngradedMessageInfix} "${claimTypeLabel(data.claim_type)}" ${messages.calismalar.attestationDowngradedMessageSuffix} (${reasons})`
        );
      } else {
        setSuccessMessage(messages.calismalar.attestationVerifiedMessage);
      }
      onSuccess(); // engagement.status artık VERIFIED — güncel veriyi getir
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setFormError(messages.calismalar.transitionForbiddenError);
          return;
        }
        if (error.code === "INVALID_STATE_TRANSITION") {
          setFormError(messages.calismalar.attestationNotEvaluatedError);
          onSuccess();
          return;
        }
        if (error.code === "CONFLICT") {
          setFormError(messages.calismalar.transitionConflictError);
          onSuccess(); // sürüm eski — güncel veriyi getir
          return;
        }
        if (error.code === "SELF_ATTESTATION_FORBIDDEN") {
          setFormError(messages.calismalar.attestationSelfForbiddenError);
          return;
        }
        if (error.code === "ATTESTATION_ALREADY_EXISTS") {
          setFormError(messages.calismalar.attestationAlreadyExistsError);
          onSuccess();
          return;
        }
      }
      setFormError(messages.errors.generic);
    },
  });

  // transition-actions.tsx'teki desenle aynı: mesaj gösterilmeden status değişip
  // bileşen kaybolmasın.
  if (engagement.status !== "EVALUATED" && !formError && !successMessage) {
    return null;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMessage(null);
    mutation.mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 border-t border-border pt-4">
      <h3 className="text-sm font-bold mb-3">{messages.calismalar.attestationTitle}</h3>

      <div className="mb-3 max-w-xs">
        <Label htmlFor="attestation-claim-type">{messages.calismalar.attestationClaimTypeLabel}</Label>
        <select
          id="attestation-claim-type"
          value={claimType}
          onChange={(e) => setClaimType(e.target.value as ClaimType)}
          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
        >
          {CLAIM_TYPES.map((ct) => (
            <option key={ct} value={ct}>
              {claimTypeLabel(ct)}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-3 max-w-xs">
        <SkillPicker value={skillId} onChange={setSkillId} label={messages.calismalar.attestationSkillLabel} />
      </div>

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? messages.calismalar.submittingAttestationButton : messages.calismalar.submitAttestationButton}
      </Button>

      {formError && (
        <div role="alert" aria-live="polite" className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
          {formError}
        </div>
      )}

      {successMessage && (
        <div role="status" aria-live="polite" className="mt-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-600">
          {successMessage}
        </div>
      )}
    </form>
  );
}
