"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  transitionEngagement,
  availableTransitions,
  isReasonRequired,
  type EngagementDetail,
  type EngagementStatus,
} from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MAX_NOTIFY_EMAILS, parseNotifyEmails } from "@/lib/ui/notify-emails";
import messages from "@/messages/tr.json";

// Sending for approval asks who should receive the request before it goes out.
const APPROVAL_REQUEST: EngagementStatus = "PENDING_APPROVAL";
const NOTICE_MS = 2000;
// The recipient notice explains what happens to the address; give it time to be read.
const RECIPIENT_NOTICE_MS = 8000;

/**
 * PLAN 2.11/YET-97: Durum geçiş aksiyonları — POST /transitions bağlantısı + hata gösterimi.
 *
 * candidates SADECE durum bazlı hesaplanır (bkz. lib/api/engagements.ts başındaki
 * BACKEND GAP notu — /me principal.kind döndürmüyor). Sunucu 403 dönerse (yetkisiz
 * kullanıcı) bunu burada gösteriyoruz; bu, rol filtrelemesinin eksikliğini telafi eden
 * kasıtlı bir davranış, hata değil.
 */
export function TransitionActions({
  engagement,
  onSuccess,
}: {
  engagement: EngagementDetail;
  onSuccess: () => void;
}) {
  const [pendingTarget, setPendingTarget] = useState<EngagementStatus | null>(null);
  const [reason, setReason] = useState("");
  const [notifyInput, setNotifyInput] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: ({ toStatus, notifyEmails = [] }: { toStatus: EngagementStatus; notifyEmails?: string[] }) =>
      transitionEngagement(engagement.id, {
        to_status: toStatus,
        version: engagement.version,
        reason: reason.trim() || undefined,
        ...(notifyEmails.length > 0 ? { notify_emails: notifyEmails } : {}),
      }),
    onSuccess: (_data, { notifyEmails = [] }) => {
      const addressed = notifyEmails.length > 0;
      setPendingTarget(null);
      setReason("");
      setNotifyInput("");
      setFormError(null);
      setSuccessMessage(
        addressed ? messages.calismalar.notifyEmailsSentMessage : messages.calismalar.transitionSuccessMessage,
      );
      onSuccess();
      setTimeout(() => setSuccessMessage(null), addressed ? RECIPIENT_NOTICE_MS : NOTICE_MS);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        // AC-S4 (backend): version tampering / stale state → 409, güncel durumu getir.
        if (error.status === 409) {
          setFormError(messages.calismalar.transitionConflictError);
          onSuccess();
          return;
        }
        // Sunucu yetkilendirmeyi reddetti (rol UX'te filtrelenmedi — bkz. dosya başı notu).
        if (error.status === 403) {
          setFormError(messages.calismalar.transitionForbiddenError);
          return;
        }
        if (error.code === "PRECONDITION_FAILED") {
          setFormError(messages.calismalar.reasonRequiredError);
          return;
        }
        if (error.code === "ILLEGAL_TRANSITION") {
          setFormError(messages.calismalar.transitionIllegalError);
          onSuccess();
          return;
        }
      }
      setFormError(messages.errors.generic);
    },
  });

  const candidates = availableTransitions(engagement.status, engagement.institution_id);

  // AC-S4 (backend) sonrası refetch, engagement.status'u ör. terminal bir duruma
  // güncelleyebilir (candidates boşalır) — ANCAK az önce set edilen formError/
  // successMessage'ı hâlâ göstermemiz gerekir. Bu yüzden erken "return null" SADECE
  // gösterilecek hiçbir şey yokken yapılır; aksi halde mesaj bir render sonra silinip
  // kullanıcı okuyamadan kaybolur (bkz. manuel test — Faz F).
  if (candidates.length === 0 && !pendingTarget && !formError && !successMessage) {
    return null;
  }

  const handleActionClick = (toStatus: EngagementStatus) => {
    setFormError(null);
    setSuccessMessage(null);
    if (isReasonRequired(toStatus) || toStatus === APPROVAL_REQUEST) {
      setPendingTarget(toStatus);
    } else {
      mutation.mutate({ toStatus });
    }
  };

  const handleApprovalRequestSubmit = () => {
    const parsed = parseNotifyEmails(notifyInput);
    if (!parsed.ok) {
      setFormError(
        parsed.error === "required"
          ? messages.calismalar.notifyEmailsRequiredError
          : parsed.error === "tooMany"
            ? messages.calismalar.notifyEmailsTooManyError.replace("{max}", String(MAX_NOTIFY_EMAILS))
            : messages.calismalar.notifyEmailsInvalidError.replace("{email}", parsed.email),
      );
      return;
    }
    setFormError(null);
    mutation.mutate({ toStatus: APPROVAL_REQUEST, notifyEmails: parsed.emails });
  };

  const handleCancel = () => {
    setPendingTarget(null);
    setFormError(null);
  };

  const handleReasonSubmit = (toStatus: EngagementStatus) => {
    if (!reason.trim()) {
      setFormError(messages.calismalar.reasonRequiredError);
      return;
    }
    mutation.mutate({ toStatus });
  };

  return (
    <div className="mt-4 border-t border-border pt-4">
      {/* The approval-request form carries its own submit button. */}
      {candidates.length > 0 && pendingTarget !== APPROVAL_REQUEST && (
        <div className="flex flex-wrap gap-2">
          {candidates.map((toStatus) => (
            <Button
              key={toStatus}
              onClick={() => handleActionClick(toStatus)}
              disabled={mutation.isPending}
              className={
                toStatus === "REJECTED" || toStatus === "CANCELLED"
                  ? "border border-destructive/30 bg-transparent text-destructive hover:bg-destructive/10"
                  : ""
              }
            >
              {messages.calismalar.transitionAction[toStatus]}
            </Button>
          ))}
        </div>
      )}

      {/* pendingTarget artık geçersiz bir hedefse (ör. başka sekmenin geçişi sonucu
          durum değişti) gerekçe formunu göstermiyoruz — sadece hata mesajı görünür. */}
      {pendingTarget === APPROVAL_REQUEST && candidates.includes(APPROVAL_REQUEST) && (
        <form
          className="mt-4 max-w-xl"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            handleApprovalRequestSubmit();
          }}
        >
          <Label htmlFor="transition-notify-emails">{messages.calismalar.notifyEmailsLabel}</Label>
          <Input
            id="transition-notify-emails"
            type="text"
            inputMode="email"
            autoComplete="off"
            required
            aria-required="true"
            value={notifyInput}
            onChange={(e) => setNotifyInput(e.target.value)}
            placeholder={messages.calismalar.notifyEmailsPlaceholder}
            aria-describedby="transition-notify-emails-hint"
          />
          <p id="transition-notify-emails-hint" className="mt-1 text-sm text-muted-foreground">
            {messages.calismalar.notifyEmailsHint.replace("{max}", String(MAX_NOTIFY_EMAILS))}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending
                ? messages.calismalar.transitionSubmittingButton
                : messages.calismalar.transitionAction[APPROVAL_REQUEST]}
            </Button>
            <Button type="button" variant="secondary" onClick={handleCancel} disabled={mutation.isPending}>
              {messages.calismalar.transitionCancelButton}
            </Button>
          </div>
        </form>
      )}

      {pendingTarget && pendingTarget !== APPROVAL_REQUEST && candidates.includes(pendingTarget) && (
        <div className="mt-4 max-w-md">
          <Label htmlFor="transition-reason">{messages.calismalar.reasonLabel}</Label>
          <Input id="transition-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button
            onClick={() => handleReasonSubmit(pendingTarget)}
            disabled={mutation.isPending}
            className="mt-2"
          >
            {mutation.isPending
              ? messages.calismalar.transitionSubmittingButton
              : messages.calismalar.transitionSubmitButton}
          </Button>
        </div>
      )}

      {formError && (
        <div
          role="alert"
          aria-live="polite"
          className="mt-4 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
        >
          {formError}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          aria-live="polite"
          className="mt-4 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-600"
        >
          {successMessage}
        </div>
      )}
    </div>
  );
}
