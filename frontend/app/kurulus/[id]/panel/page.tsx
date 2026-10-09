"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getOrganization,
  inviteOrgMember,
  verifyDomain,
  type OrgMemberRole,
} from "@/lib/api/organizations";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

const FIELD_CLASS =
  "block w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";
const LABEL_CLASS = "mb-1 block text-sm font-medium text-foreground";
const PRIMARY_BUTTON_CLASS =
  "bg-success text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 disabled:opacity-60";
const TRUST_BADGE_VARIANT: Record<string, "default" | "success" | "warning"> = {
  T0: "default",
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};

/**
 * YET-202/ENT-01: Organizasyon paneli — alan adı doğrulama (DNS TXT) + üye davet.
 *
 * Alan adı doğrulama UX'i (dokümante bir referans yok, burada tasarlandı):
 * "Doğrulamayı Kontrol Et" tıklanınca backend bir TXT token üretir/yeniden kullanır
 * ve DNS'i sorgular. "pending" bir HATA DEĞİLDİR — kayıt henüz DNS'te yok demektir;
 * TXT değeri ekrana basılır, kullanıcı DNS sağlayıcısına ekler, tekrar dener.
 * verification_level T1'den çıkınca (T2+) buton kalkar, doğrulanmış rozeti kalır.
 */
export default function KurulusPanelPage() {
  const params = useParams<{ id: string }>();
  const organizationId = params.id;
  const queryClient = useQueryClient();
  const ORG_QUERY_KEY = ["organization", organizationId] as const;

  const [dnsTxtRecord, setDnsTxtRecord] = useState<string | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<"verified" | "pending" | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<OrgMemberRole>("MEMBER");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);

  const { data: org, isLoading, isError, error, refetch } = useQuery({
    queryKey: ORG_QUERY_KEY,
    queryFn: () => getOrganization(organizationId),
  });

  const verifyMutation = useMutation({
    mutationFn: () => verifyDomain(organizationId),
    onSuccess: (result) => {
      setVerifyError(null);
      setDnsTxtRecord(result.dns_txt_record);
      setVerifyStatus(result.status);
      if (result.status === "verified") {
        queryClient.invalidateQueries({ queryKey: ORG_QUERY_KEY });
      }
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.code === "FREE_EMAIL_DOMAIN") {
          setVerifyError(messages.kurulusPanel.freeEmailDomainError);
          return;
        }
        if (error.code === "TOO_MANY_REQUESTS") {
          setVerifyError(messages.kurulusPanel.rateLimitedError);
          return;
        }
        if (error.code === "DOMAIN_ALREADY_VERIFIED") {
          setVerifyError(messages.kurulusPanel.domainAlreadyVerifiedError);
          return;
        }
      }
      setVerifyError(messages.errors.generic);
    },
  });

  const inviteMutation = useMutation({
    mutationFn: () => inviteOrgMember(organizationId, inviteEmail.trim(), inviteRole),
    onSuccess: () => {
      setInviteError(null);
      setInviteMessage(messages.kurulusPanel.inviteSuccessMessage);
      setInviteEmail("");
    },
    onError: () => {
      setInviteMessage(null);
      setInviteError(messages.kurulusPanel.inviteErrorMessage);
    },
  });

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInviteMessage(null);
    setInviteError(null);
    inviteMutation.mutate();
  };

  const trustLabels = messages.kurulusPanel.trustLevel as Record<string, string>;

  return (
    <AppShell>
      <div className="max-w-[960px] px-4 py-8 md:px-6 lg:px-10">
        <p className="text-xs text-muted-foreground">{messages.kurulusPanel.title}</p>

        {isLoading && (
          <div role="status" className="mt-2 space-y-4">
            <span className="sr-only">{messages.shell.loading}</span>
            <div aria-hidden="true" className="h-10 w-2/3 animate-pulse rounded-md bg-muted" />
            <div aria-hidden="true" className="h-40 animate-pulse rounded-lg bg-muted" />
            <div aria-hidden="true" className="h-32 animate-pulse rounded-lg bg-muted" />
          </div>
        )}

        {isError && error && (
          <div className="mt-4">
            <ErrorBanner
              message={
                error instanceof SessionExpiredError
                  ? messages.session.expired
                  : error instanceof ApiError
                    ? error.message
                    : error instanceof NetworkError
                      ? error.message
                      : messages.errors.generic
              }
              requestId={error instanceof ApiError ? error.requestId : undefined}
              onRetry={() => refetch()}
            />
          </div>
        )}

        {!isLoading && !isError && org && (
          <>
            <header className="mt-1">
              <h1 className="font-serif text-[32px] font-semibold leading-10 text-foreground">
                {org.name}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
                <Badge variant={TRUST_BADGE_VARIANT[org.verification_level] ?? "default"}>
                  {trustLabels[org.verification_level] ?? org.verification_level}
                </Badge>
                {org.legal_id && (
                  <span className="font-mono text-[13px] text-muted-foreground">
                    {messages.kurulusPanel.legalIdLabel}: {org.legal_id}
                  </span>
                )}
              </div>
            </header>

            {/* Alan adı doğrulama */}
            <section className="mt-8 rounded-lg border border-border bg-card p-4 md:p-6">
              <h2 className="mb-3 font-serif text-xl font-medium leading-7 text-foreground">
                {messages.kurulusPanel.domainSectionTitle}
              </h2>

              {!org.domain ? (
                <Alert variant="info" className="text-sm">
                  {messages.kurulusPanel.noDomainMessage}
                </Alert>
              ) : org.verification_level !== "T1" ? (
                <div className="flex flex-wrap items-center gap-3 text-sm text-foreground">
                  <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success text-background">
                    <svg
                      viewBox="0 0 24 24"
                      className="h-3 w-3"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={3}
                      aria-hidden="true"
                    >
                      <path d="M5 12l5 5L20 7" />
                    </svg>
                  </span>
                  <span>{messages.kurulusPanel.verifiedMessage}</span>
                  <Badge variant="success">{messages.kurulusPanel.domainVerifiedBadge}</Badge>
                  <span className="w-full font-mono text-[13px] text-muted-foreground">
                    {org.domain}
                  </span>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-foreground">
                    {messages.kurulusPanel.domainLabel}: <strong>{org.domain}</strong>
                  </p>

                  {dnsTxtRecord && (
                    <div className="mt-3">
                      <p className="mb-2 text-xs text-muted-foreground">
                        {messages.kurulusPanel.txtRecordHint}
                      </p>
                      <code
                        aria-label={messages.kurulusPanel.txtRecordLabel}
                        className="block select-all break-all rounded-md border border-border bg-muted px-3 py-2 font-mono text-sm text-foreground"
                      >
                        {dnsTxtRecord}
                      </code>
                    </div>
                  )}

                  {verifyStatus === "pending" && (
                    <Alert variant="warning" className="mt-3 text-sm">
                      {messages.kurulusPanel.pendingMessage}
                    </Alert>
                  )}
                  {verifyStatus === "verified" && (
                    <Alert variant="success" className="mt-3 text-sm">
                      {messages.kurulusPanel.verifiedMessage}
                    </Alert>
                  )}
                  {verifyError && (
                    <Alert variant="error" className="mt-3 text-sm">
                      {verifyError}
                    </Alert>
                  )}

                  {verifyStatus !== "verified" && (
                    <div className="mt-4">
                      <Button
                        onClick={() => verifyMutation.mutate()}
                        disabled={verifyMutation.isPending}
                        className={PRIMARY_BUTTON_CLASS}
                      >
                        {verifyMutation.isPending
                          ? messages.kurulusPanel.verifyingButton
                          : dnsTxtRecord
                            ? messages.kurulusPanel.retryVerifyButton
                            : messages.kurulusPanel.verifyButton}
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* Üye davet */}
            <section className="mt-6 rounded-lg border border-border bg-card p-4 md:p-6">
              <h2 className="mb-3 font-serif text-xl font-medium leading-7 text-foreground">
                {messages.kurulusPanel.inviteMemberTitle}
              </h2>

              <form onSubmit={handleInviteSubmit}>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="min-w-[200px] flex-1">
                    <label htmlFor="org-invite-email" className={LABEL_CLASS}>
                      {messages.kurulusPanel.inviteEmailLabel}
                    </label>
                    <input
                      id="org-invite-email"
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                      className={FIELD_CLASS}
                    />
                  </div>

                  <div className="w-full sm:w-40">
                    <label htmlFor="org-invite-role" className={LABEL_CLASS}>
                      {messages.kurulusPanel.inviteRoleLabel}
                    </label>
                    <select
                      id="org-invite-role"
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value as OrgMemberRole)}
                      className={FIELD_CLASS}
                    >
                      <option value="MEMBER">{messages.kurulusPanel.memberRole.MEMBER}</option>
                      <option value="ADMIN">{messages.kurulusPanel.memberRole.ADMIN}</option>
                    </select>
                  </div>

                  <Button
                    type="submit"
                    variant="secondary"
                    disabled={inviteMutation.isPending}
                    className="border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                  >
                    {inviteMutation.isPending
                      ? messages.kurulusPanel.invitingButton
                      : messages.kurulusPanel.inviteButton}
                  </Button>
                </div>

                {inviteError && (
                  <Alert variant="error" className="mt-3 text-sm">
                    {inviteError}
                  </Alert>
                )}
                {inviteMessage && (
                  <Alert variant="success" className="mt-3 text-sm">
                    {inviteMessage}
                  </Alert>
                )}
              </form>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
