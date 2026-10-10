"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PanelIcon, SideCard, StatusPill, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { SealMark } from "@/components/brand/brand-mark";
import { verifyDomain, type OrganizationResponse } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.kurulusPanel;

/**
 * Domain verification (DNS TXT). "pending" is not an error — the record is not
 * in DNS yet. Once verified (T2+) the card shrinks to a small badge.
 * Only admins see the verify button (the endpoint is admin-only).
 */
export function DomainCard({ org, canManage }: { org: OrganizationResponse; canManage: boolean }) {
  const queryClient = useQueryClient();
  const [dnsTxtRecord, setDnsTxtRecord] = useState<string | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<"verified" | "pending" | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const verifyMutation = useMutation({
    mutationFn: () => verifyDomain(org.id),
    onSuccess: (result) => {
      setVerifyError(null);
      setDnsTxtRecord(result.dns_txt_record);
      setVerifyStatus(result.status);
      if (result.status === "verified") {
        queryClient.invalidateQueries({ queryKey: ["organization", org.id] });
      }
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.code === "FREE_EMAIL_DOMAIN") return setVerifyError(t.freeEmailDomainError);
        if (error.code === "TOO_MANY_REQUESTS") return setVerifyError(t.rateLimitedError);
        if (error.code === "DOMAIN_ALREADY_VERIFIED") return setVerifyError(t.domainAlreadyVerifiedError);
      }
      setVerifyError(messages.errors.generic);
    },
  });

  if (org.domain && org.verification_level !== "T1") {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-success/25 bg-success/[0.06] px-4 py-3">
        <SealMark className="h-8 w-8 shrink-0" />
        <div className="min-w-0 text-sm">
          <StatusPill tone="success">{t.domainVerifiedBadge}</StatusPill>
          <p className="mt-1 truncate font-mono text-[13px] text-muted-foreground">{org.domain}</p>
        </div>
      </div>
    );
  }

  return (
    <SideCard title={t.domainSectionTitle} hint={t.domainHint}>
      {!org.domain ? (
        <Alert variant="info" className="text-sm">
          {t.noDomainMessage}
        </Alert>
      ) : (
        <div className="text-sm">
          <p className="flex items-center gap-2 text-foreground">
            <PanelIcon name="globe" className="h-4 w-4 text-muted-foreground" />
            {t.domainLabel}: <strong className="font-mono text-[13px] font-medium">{org.domain}</strong>
          </p>

          {dnsTxtRecord ? (
            <div className="mt-3">
              <p className="mb-2 text-xs text-muted-foreground">{t.txtRecordHint}</p>
              <code
                aria-label={t.txtRecordLabel}
                className="block select-all break-all rounded-md border border-border bg-muted px-3 py-2 font-mono text-[13px] text-foreground"
              >
                {dnsTxtRecord}
              </code>
            </div>
          ) : null}

          <div aria-live="polite">
            {verifyStatus === "pending" ? (
              <Alert variant="warning" className="mt-3 text-sm">
                {t.pendingMessage}
              </Alert>
            ) : null}
            {verifyStatus === "verified" ? (
              <Alert variant="success" className="mt-3 text-sm">
                {t.verifiedMessage}
              </Alert>
            ) : null}
            {verifyError ? (
              <Alert variant="error" className="mt-3 text-sm">
                {verifyError}
              </Alert>
            ) : null}
          </div>

          {canManage && verifyStatus !== "verified" ? (
            <button
              type="button"
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending}
              className={cn(actionClass.primary, "mt-4 w-full")}
            >
              {verifyMutation.isPending ? t.verifyingButton : dnsTxtRecord ? t.retryVerifyButton : t.verifyButton}
            </button>
          ) : null}
        </div>
      )}
    </SideCard>
  );
}
