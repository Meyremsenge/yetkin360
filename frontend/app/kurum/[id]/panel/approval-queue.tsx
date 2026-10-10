"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ActionLink,
  EmptyState,
  PanelSection,
  StatusPill,
  actionClass,
  formatDate,
  formatTemplate,
} from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { transitionEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import type { PendingItem } from "@/lib/api/institutions";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.kurumPanel;
const c = messages.calismalar;

const SM = "h-8 px-3 text-[13px]";

type RowStatus = "PENDING_APPROVAL" | "PENDING_EVALUATION" | "EVALUATED";

/** Student and organization behind an engagement, e.g. "Ayşe Yılmaz · Yelkovan Yazılım". */
function rowMeta(item: PendingItem): string {
  return formatTemplate(t.rowMeta, {
    talent: item.talent_full_name,
    organization: item.organization_name,
  });
}

/**
 * One engagement in an institution queue: title, who and where, a date line and
 * its status. Clicking opens the engagement; `trailing` holds inline actions.
 */
export function EngagementRow({
  item,
  date,
  status,
  leading,
  trailing,
  selected,
}: {
  item: PendingItem;
  date: string | null;
  status: RowStatus;
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
  selected?: boolean;
}) {
  return (
    <li
      className={cn(
        "flex flex-wrap items-center gap-3 px-5 py-3.5 transition-colors",
        selected ? "bg-success/[0.06]" : "hover:bg-background",
      )}
    >
      {leading}
      <Link
        href={`/calismalar/${item.id}`}
        className="group flex min-w-0 flex-1 items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
      >
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-foreground group-hover:underline group-hover:underline-offset-4">
            {item.title}
          </span>
          <span className="mt-0.5 block truncate text-[13px] text-foreground/80">
            {rowMeta(item)}
          </span>
          {date ? (
            <span className="mt-0.5 block font-mono text-xs text-muted-foreground">
              {date}
            </span>
          ) : null}
        </span>
        <StatusPill
          tone={status === "EVALUATED" ? "success" : "warning"}
          className="hidden sm:inline-flex"
        >
          {c.status[status]}
        </StatusPill>
        {trailing ? null : (
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4 shrink-0 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.75}
            aria-hidden="true"
          >
            <path
              d="M9 6l6 6-6 6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </Link>
      {trailing}
    </li>
  );
}

function Notice({
  error,
  message,
}: {
  error: string | null;
  message: string | null;
}) {
  if (error) {
    return (
      <Alert variant="error" className="m-5 mb-0 text-sm">
        {error}
      </Alert>
    );
  }
  if (message) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="m-5 mb-0 rounded-md border border-success/30 bg-success/10 px-4 py-3 text-sm text-success"
      >
        {message}
      </div>
    );
  }
  return null;
}

/**
 * Engagements waiting for the institution's start approval. A coordinator
 * approves (→ ACTIVE) or rejects with a required reason (→ REJECTED) inline;
 * an admin sees the same list read-only with a note on who approves. UX only:
 * the server re-checks every transition.
 */
export function ApprovalSection({
  institutionId,
  items,
  canApprove,
}: {
  institutionId: string;
  items: PendingItem[];
  canApprove: boolean;
}) {
  const queryClient = useQueryClient();
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: ["institution-dashboard", institutionId],
    });

  const mutation = useMutation({
    mutationFn: (input: {
      item: PendingItem;
      to: "ACTIVE" | "REJECTED";
      reason?: string;
    }) =>
      transitionEngagement(input.item.id, {
        to_status: input.to,
        version: input.item.version,
        ...(input.reason ? { reason: input.reason } : {}),
      }),
    onSuccess: (_data, input) => {
      setError(null);
      setMessage(input.to === "ACTIVE" ? t.approvedMessage : t.rejectedMessage);
      setRejectingId(null);
      setReason("");
      void refresh();
    },
    onError: (err) => {
      setMessage(null);
      if (err instanceof ApiError && err.status === 409) {
        setError(t.conflictMessage);
        setRejectingId(null);
        void refresh();
        return;
      }
      setError(t.transitionError);
    },
  });

  const startReject = (id: string) => {
    setRejectingId(id);
    setReason("");
    setReasonError(null);
    setMessage(null);
    setError(null);
  };

  const submitReject = (item: PendingItem) => {
    const trimmed = reason.trim();
    if (!trimmed) {
      setReasonError(t.rejectReasonRequired);
      return;
    }
    setReasonError(null);
    mutation.mutate({ item, to: "REJECTED", reason: trimmed });
  };

  return (
    <PanelSection
      id="onay-bekleyen"
      icon="clock"
      title={t.pendingApprovalTitle}
      hint={canApprove ? t.pendingApprovalHint : t.adminApprovalNote}
      count={items.length}
      flush={items.length > 0}
      actions={
        <ActionLink href="/calismalar" variant="neutral" className={SM}>
          {t.seeAll}
        </ActionLink>
      }
    >
      {items.length === 0 ? (
        <EmptyState
          icon="inbox"
          title={t.emptyPendingApprovalMessage}
          hint={t.emptyPendingApprovalHint}
        />
      ) : (
        <>
          <Notice error={error} message={message} />
          <ul className="divide-y divide-border">
            {items.map((item) => (
              <ApprovalRow
                key={item.id}
                item={item}
                canApprove={canApprove}
                rejecting={rejectingId === item.id}
                busy={mutation.isPending}
                reason={reason}
                reasonError={reasonError}
                onReason={setReason}
                onApprove={() => {
                  setMessage(null);
                  setError(null);
                  mutation.mutate({ item, to: "ACTIVE" });
                }}
                onStartReject={() => startReject(item.id)}
                onCancelReject={() => setRejectingId(null)}
                onSubmitReject={() => submitReject(item)}
              />
            ))}
          </ul>
        </>
      )}
    </PanelSection>
  );
}

function ApprovalRow({
  item,
  canApprove,
  rejecting,
  busy,
  reason,
  reasonError,
  onReason,
  onApprove,
  onStartReject,
  onCancelReject,
  onSubmitReject,
}: {
  item: PendingItem;
  canApprove: boolean;
  rejecting: boolean;
  busy: boolean;
  reason: string;
  reasonError: string | null;
  onReason: (value: string) => void;
  onApprove: () => void;
  onStartReject: () => void;
  onCancelReject: () => void;
  onSubmitReject: () => void;
}) {
  const date = item.started_on
    ? formatTemplate(t.startedOn, { date: formatDate(item.started_on) })
    : null;
  const reasonId = `reject-reason-${item.id}`;

  return (
    <>
      <EngagementRow
        item={item}
        date={date}
        status="PENDING_APPROVAL"
        trailing={
          canApprove && !rejecting ? (
            <span className="flex gap-2">
              <button
                type="button"
                onClick={onApprove}
                disabled={busy}
                aria-label={formatTemplate(t.approveOf, { title: item.title })}
                className={cn(actionClass.primary, SM)}
              >
                {t.approveButton}
              </button>
              <button
                type="button"
                onClick={onStartReject}
                disabled={busy}
                aria-label={formatTemplate(t.rejectOf, { title: item.title })}
                className={cn(actionClass.dangerOutline, SM)}
              >
                {t.rejectButton}
              </button>
            </span>
          ) : undefined
        }
      />
      {canApprove && rejecting ? (
        <li className="bg-destructive/[0.03] px-5 py-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onSubmitReject();
            }}
            className="space-y-2"
            noValidate
          >
            <Label htmlFor={reasonId} className="text-xs">
              {t.rejectReasonLabel}
            </Label>
            <textarea
              id={reasonId}
              rows={2}
              value={reason}
              onChange={(e) => onReason(e.target.value)}
              aria-invalid={reasonError ? true : undefined}
              aria-describedby={`${reasonId}-hint`}
              className="block w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25"
            />
            <p
              id={`${reasonId}-hint`}
              className="text-xs text-muted-foreground"
            >
              {t.rejectReasonHint}
            </p>
            {reasonError ? (
              <p role="alert" className="text-sm text-destructive">
                {reasonError}
              </p>
            ) : null}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={busy}
                className={cn(actionClass.dangerOutline, SM)}
              >
                {t.rejectSubmit}
              </button>
              <button
                type="button"
                onClick={onCancelReject}
                disabled={busy}
                className={cn(actionClass.neutral, SM)}
              >
                {t.rejectCancel}
              </button>
            </div>
          </form>
        </li>
      ) : null}
    </>
  );
}

/**
 * Engagements the organization has evaluated (EVALUATED): the institution's
 * seal makes the record double-signed. The seal itself is given on the
 * engagement page; a coordinator gets a direct "Mühürle" link.
 */
export function AttestationSection({
  items,
  canSeal,
}: {
  items: PendingItem[];
  canSeal: boolean;
}) {
  return (
    <PanelSection
      id="muhur-bekleyen"
      icon="shield"
      title={t.pendingAttestationTitle}
      hint={t.pendingAttestationHint}
      count={items.length}
      flush={items.length > 0}
    >
      {items.length === 0 ? (
        <EmptyState
          icon="shield"
          title={t.emptyPendingAttestationMessage}
          hint={t.emptyPendingAttestationHint}
        />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <EngagementRow
              key={item.id}
              item={item}
              status="EVALUATED"
              date={
                item.ended_on
                  ? formatTemplate(t.endedOn, {
                      date: formatDate(item.ended_on),
                    })
                  : null
              }
              trailing={
                canSeal ? (
                  <Link
                    href={`/calismalar/${item.id}#taniklik`}
                    aria-label={formatTemplate(t.sealButtonOf, {
                      title: item.title,
                    })}
                    className={cn(actionClass.primary, SM)}
                  >
                    {t.sealButton}
                  </Link>
                ) : undefined
              }
            />
          ))}
        </ul>
      )}
    </PanelSection>
  );
}
