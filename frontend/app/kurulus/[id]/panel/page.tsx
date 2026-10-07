"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ErrorBanner } from "@/components/error-banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getOrganization,
  inviteOrgMember,
  verifyDomain,
  type OrgMemberRole,
} from "@/lib/api/organizations";
import { ApiError, NetworkError, SessionExpiredError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

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

  return (
    <AppShell>
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.kurulusPanel.title}</h1>

        {isLoading && <p className="text-slate-600">{messages.shell.loading}</p>}

        {isError && error && (
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
        )}

        {!isLoading && !isError && org && (
          <>
            <div className="bg-slate-50 rounded-md border border-slate-200 p-4 mb-8">
              <div className="text-lg font-bold text-slate-900">{org.name}</div>
              {org.legal_id && (
                <div className="text-sm text-slate-600 mt-1">
                  {messages.kurulusPanel.legalIdLabel}: {org.legal_id}
                </div>
              )}
            </div>

            {/* Alan adı doğrulama */}
            <section className="mb-8">
              <h2 className="text-lg font-bold mb-3">{messages.kurulusPanel.domainSectionTitle}</h2>

              {!org.domain ? (
                <p className="text-sm text-slate-600 bg-slate-50 rounded-md border border-slate-200 p-4">
                  {messages.kurulusPanel.noDomainMessage}
                </p>
              ) : org.verification_level !== "T1" ? (
                <div className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-700">
                  {messages.kurulusPanel.domainVerifiedBadge}: <strong>{org.domain}</strong>
                </div>
              ) : (
                <div className="bg-white rounded-md border border-slate-200 p-4">
                  <p className="text-sm text-slate-700 mb-3">
                    {messages.kurulusPanel.domainLabel}: <strong>{org.domain}</strong>
                  </p>

                  {dnsTxtRecord && (
                    <div className="mb-3 rounded-md bg-slate-50 border border-slate-200 p-3">
                      <p className="text-xs text-slate-600 mb-1">{messages.kurulusPanel.txtRecordHint}</p>
                      <code className="block text-sm font-mono bg-white border border-slate-300 rounded px-2 py-1 break-all">
                        {dnsTxtRecord}
                      </code>
                    </div>
                  )}

                  {verifyStatus === "pending" && (
                    <div role="status" aria-live="polite" className="mb-3 rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
                      {messages.kurulusPanel.pendingMessage}
                    </div>
                  )}
                  {verifyStatus === "verified" && (
                    <div role="status" aria-live="polite" className="mb-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-700">
                      {messages.kurulusPanel.verifiedMessage}
                    </div>
                  )}
                  {verifyError && (
                    <div role="alert" aria-live="polite" className="mb-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
                      {verifyError}
                    </div>
                  )}

                  {verifyStatus !== "verified" && (
                    <Button onClick={() => verifyMutation.mutate()} disabled={verifyMutation.isPending}>
                      {verifyMutation.isPending
                        ? messages.kurulusPanel.verifyingButton
                        : dnsTxtRecord
                          ? messages.kurulusPanel.retryVerifyButton
                          : messages.kurulusPanel.verifyButton}
                    </Button>
                  )}
                </div>
              )}
            </section>

            {/* Üye davet */}
            <section>
              <h2 className="text-lg font-bold mb-3">{messages.kurulusPanel.inviteMemberTitle}</h2>

              <form onSubmit={handleInviteSubmit} className="bg-slate-50 p-4 rounded-md border border-slate-200">
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <Label htmlFor="org-invite-email">{messages.kurulusPanel.inviteEmailLabel}</Label>
                    <Input
                      id="org-invite-email"
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="org-invite-role">{messages.kurulusPanel.inviteRoleLabel}</Label>
                    <select
                      id="org-invite-role"
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value as OrgMemberRole)}
                      className="block px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                    >
                      <option value="MEMBER">{messages.kurulusPanel.memberRole.MEMBER}</option>
                      <option value="ADMIN">{messages.kurulusPanel.memberRole.ADMIN}</option>
                    </select>
                  </div>

                  <Button type="submit" disabled={inviteMutation.isPending}>
                    {inviteMutation.isPending
                      ? messages.kurulusPanel.invitingButton
                      : messages.kurulusPanel.inviteButton}
                  </Button>
                </div>

                {inviteError && (
                  <div role="alert" aria-live="polite" className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
                    {inviteError}
                  </div>
                )}
                {inviteMessage && (
                  <div role="status" aria-live="polite" className="mt-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-700">
                    {inviteMessage}
                  </div>
                )}
              </form>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
