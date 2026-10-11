"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  listApprovalRecipients,
  transitionEngagement,
  type ApprovalRecipient,
  type EngagementDetail,
  type EngagementStatus,
} from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";
import { ApproverIdentity, approverName } from "../yeni-calisma-parts";

// Sending for approval asks which coordinator of the school should receive it.
const APPROVAL_REQUEST: EngagementStatus = "PENDING_APPROVAL";
const NOTICE_MS = 2000;
// The recipient notice says where the request went; give it time to be read.
const RECIPIENT_NOTICE_MS = 6000;
const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";
const choiceCard =
  "flex cursor-pointer items-center gap-3 rounded-lg border border-border bg-card p-3 transition-colors hover:border-muted-foreground/50 has-[:checked]:border-success has-[:checked]:bg-success/[0.06] has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-success";

/**
 * PLAN 2.11/YET-97: Durum geçiş aksiyonları — POST /transitions bağlantısı + hata gösterimi.
 *
 * SPRINT A: adaylar sunucunun `viewer.allowed_transitions` listesidir — yalnız bu
 * kullanıcının yapabileceği geçişler. Liste boşsa bileşen hiç görünmez. 403 yine ele
 * alınır (ör. sayfa açıkken üyelik değiştiyse); yetki kararı her çağrıda sunucudadır.
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
  // "" = every coordinator of the school (the server's default).
  const [recipientId, setRecipientId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const recipientsQuery = useQuery({
    queryKey: ["approval-recipients", engagement.id],
    queryFn: () => listApprovalRecipients(engagement.id),
    enabled: pendingTarget === APPROVAL_REQUEST,
    retry: false,
  });
  const recipients = recipientsQuery.data ?? [];

  const mutation = useMutation({
    mutationFn: ({ toStatus, recipient }: { toStatus: EngagementStatus; recipient?: ApprovalRecipient | null }) =>
      transitionEngagement(engagement.id, {
        to_status: toStatus,
        version: engagement.version,
        reason: reason.trim() || undefined,
        ...(recipient ? { notify_user_ids: [recipient.user_id] } : {}),
      }),
    onSuccess: (_data, { toStatus, recipient }) => {
      const approvalRequest = toStatus === APPROVAL_REQUEST;
      setPendingTarget(null);
      setReason("");
      setRecipientId("");
      setFormError(null);
      setSuccessMessage(
        !approvalRequest
          ? messages.calismalar.transitionSuccessMessage
          : recipient
            ? messages.calismalar.approvalSentTo.replace("{name}", approverName(recipient))
            : messages.calismalar.approvalSentAll,
      );
      onSuccess();
      setTimeout(() => setSuccessMessage(null), approvalRequest ? RECIPIENT_NOTICE_MS : NOTICE_MS);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        // AC-S4 (backend): version tampering / stale state → 409, güncel durumu getir.
        if (error.status === 409) {
          setFormError(messages.calismalar.transitionConflictError);
          onSuccess();
          return;
        }
        // Sunucu yetkilendirmeyi reddetti (ör. sayfa açıkken rol değişti).
        if (error.status === 403) {
          setFormError(messages.calismalar.transitionForbiddenError);
          return;
        }
        if (error.code === "PRECONDITION_FAILED") {
          // The only precondition of a request for approval is a school on the engagement.
          setFormError(
            pendingTarget === APPROVAL_REQUEST
              ? messages.calismalar.approvalNoInstitutionError
              : messages.calismalar.reasonRequiredError,
          );
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

  const candidates = engagement.viewer.allowed_transitions;

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
    if (engagement.viewer.reason_required.includes(toStatus) || toStatus === APPROVAL_REQUEST) {
      setPendingTarget(toStatus);
    } else {
      mutation.mutate({ toStatus });
    }
  };

  const handleApprovalRequestSubmit = () => {
    setFormError(null);
    const recipient = recipients.find((candidate) => candidate.user_id === recipientId) ?? null;
    mutation.mutate({ toStatus: APPROVAL_REQUEST, recipient });
  };

  const handleCancel = () => {
    setPendingTarget(null);
    setRecipientId("");
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
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            handleApprovalRequestSubmit();
          }}
        >
          <fieldset aria-describedby="approval-recipients-hint">
            <legend className="text-sm font-medium text-foreground">
              {messages.calismalar.approvalRecipientsLabel}
            </legend>
            <p id="approval-recipients-hint" className="mt-1 text-[13px] leading-5 text-muted-foreground">
              {messages.calismalar.approvalRecipientsHint}
            </p>
            {recipientsQuery.isLoading ? (
              <div
                role="status"
                aria-busy="true"
                aria-label={messages.calismalar.approvalRecipientsLoading}
                className="mt-3 space-y-2"
              >
                {[0, 1].map((n) => (
                  <div key={n} aria-hidden="true" className={`h-14 w-full ${pulse}`} />
                ))}
              </div>
            ) : recipients.length === 0 ? (
              // No list (none registered, or it could not be fetched): the server notifies them all.
              <p className="mt-3 rounded-md bg-muted px-3 py-2 text-sm text-foreground">
                {messages.calismalar.approvalRecipientsNone}
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                <label className={choiceCard}>
                  <input
                    type="radio"
                    name="approval-recipient"
                    value=""
                    checked={recipientId === ""}
                    onChange={() => setRecipientId("")}
                    className="h-4 w-4 shrink-0 accent-success"
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-foreground">
                      {messages.calismalar.approvalRecipientsAll}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {messages.calismalar.approvalRecipientsAllHint}
                    </span>
                  </span>
                </label>
                {recipients.map((recipient) => (
                  <label key={recipient.user_id} className={choiceCard}>
                    <input
                      type="radio"
                      name="approval-recipient"
                      value={recipient.user_id}
                      checked={recipientId === recipient.user_id}
                      onChange={() => setRecipientId(recipient.user_id)}
                      className="h-4 w-4 shrink-0 accent-success"
                    />
                    <ApproverIdentity approver={recipient} />
                  </label>
                ))}
              </div>
            )}
          </fieldset>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="submit" disabled={mutation.isPending || recipientsQuery.isLoading}>
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
          className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {formError}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          aria-live="polite"
          className="mt-4 rounded-md border border-success/30 bg-success/10 p-3 text-sm text-success"
        >
          {successMessage}
        </div>
      )}
    </div>
  );
}
