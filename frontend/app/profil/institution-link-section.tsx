"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "@/lib/session/use-session";
import { listMyLinkRequests } from "@/lib/api/institutions";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProfileSection, SkeletonRows, EmptyNote, focusRingClass } from "./profile-ui";

const STATUS_BADGE_VARIANT: Record<string, "warning" | "success" | "error"> = {
  PENDING: "warning",
  APPROVED: "success",
  REJECTED: "error",
};

function getStatusBadgeLabel(status: string): string {
  const map: Record<string, string> = {
    PENDING: messages.profil.linkRequestPendingBadge,
    APPROVED: messages.profil.linkRequestApprovedBadge,
    REJECTED: messages.profil.linkRequestRejectedBadge,
  };
  return map[status] ?? status;
}

function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("tr-TR", { year: "numeric", month: "long", day: "numeric" }).format(
    new Date(isoDate)
  );
}

/**
 * YET-197/IS-10: Talent's institution link status + own request history.
 * No "request new link" form here (bilinçli — kurum arama/seçim UI'ı yok, talent
 * kurumun paylaştığı /kurum/{id}/baglan linkiyle talep gönderir).
 */
export default function InstitutionLinkSection() {
  const session = useSession();
  // `/me.institutions` lists institutions this user STAFFS (coordinator/admin
  // membership, via principal.institution_ids) — a student is never a member
  // of their own institution that way, so that field is always empty for
  // them even when linked. The student's own link lives on their talent
  // profile (`talent_profile.institution_id`); use that instead.
  const isLinked = Boolean(session?.data?.talent_profile?.institution_id);

  const REQUESTS_QUERY_KEY = ["my-institution-link-requests"] as const;
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: REQUESTS_QUERY_KEY,
    queryFn: listMyLinkRequests,
  });
  const requests = data?.items ?? [];
  const linkedInstitutionName = requests.find((req) => req.status === "APPROVED")?.institution_name;

  return (
    <ProfileSection
      title={messages.profil.institutionLinkSection}
      description={messages.profil.institutionDescription}
    >
      {!isLinked ? (
        <EmptyNote title={messages.profil.notLinkedMessage} hint={messages.profil.notLinkedHint} />
      ) : (
        <p className="text-[15px] font-medium text-foreground">
          {linkedInstitutionName ?? messages.profil.linkedFallbackMessage}
        </p>
      )}

      <h3 className="mb-3 mt-6 font-serif text-lg font-medium text-foreground">
        {messages.profil.linkRequestHistoryTitle}
      </h3>

      {isLoading ? (
        <SkeletonRows rows={2} />
      ) : isError ? (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          {messages.profil.linkRequestsLoadError}
          <Button onClick={() => refetch()} variant="secondary" size="sm" className={focusRingClass}>
            {messages.profil.retryButton}
          </Button>
        </div>
      ) : requests.length === 0 ? (
        <EmptyNote title={messages.profil.emptyLinkRequestsMessage} />
      ) : (
        <ul className="divide-y divide-border rounded-md border border-border">
          {requests.map((req) => (
            <li key={req.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
              <div>
                <div className="text-[15px] font-medium text-foreground">{req.institution_name}</div>
                <div className="font-mono text-xs text-muted-foreground">{formatDate(req.requested_at)}</div>
              </div>
              <Badge variant={STATUS_BADGE_VARIANT[req.status] ?? "default"}>
                {getStatusBadgeLabel(req.status)}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </ProfileSection>
  );
}
