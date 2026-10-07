"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "@/lib/session/use-session";
import { listMyLinkRequests } from "@/lib/api/institutions";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";

const STATUS_BADGE_CLASS: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-700",
  APPROVED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
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
  const institutions = (session?.data?.institutions as Array<{ id: string; name: string }> | undefined) ?? [];

  const REQUESTS_QUERY_KEY = ["my-institution-link-requests"] as const;
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: REQUESTS_QUERY_KEY,
    queryFn: listMyLinkRequests,
  });
  const requests = data?.items ?? [];

  return (
    <section className="mt-8">
      <h2 className="text-lg font-bold mb-3">{messages.profil.institutionLinkSection}</h2>

      {institutions.length === 0 ? (
        <div className="bg-slate-50 rounded-md border border-slate-200 p-4 text-sm">
          <div className="text-slate-700 mb-1">{messages.profil.notLinkedMessage}</div>
          <div className="text-slate-500">{messages.profil.notLinkedHint}</div>
        </div>
      ) : (
        <ul className="space-y-1 mb-4">
          {institutions.map((inst) => (
            <li key={inst.id} className="text-sm text-slate-900 font-medium">
              {inst.name}
            </li>
          ))}
        </ul>
      )}

      <h3 className="text-sm font-semibold text-slate-700 mt-4 mb-2">
        {messages.profil.linkRequestHistoryTitle}
      </h3>

      {isLoading ? (
        <p className="text-slate-600 text-sm">{messages.shell.loading}</p>
      ) : isError ? (
        <div className="text-sm text-red-600">
          {messages.profil.linkRequestsLoadError}
          <Button onClick={() => refetch()} className="ml-3 px-3 py-1 text-xs">
            {messages.profil.retryButton}
          </Button>
        </div>
      ) : requests.length === 0 ? (
        <p className="text-sm text-slate-600 bg-slate-50 rounded-md border border-slate-200 p-4">
          {messages.profil.emptyLinkRequestsMessage}
        </p>
      ) : (
        <ul className="space-y-2">
          {requests.map((req) => (
            <li
              key={req.id}
              className="flex items-center justify-between bg-white p-3 rounded-md border border-slate-200 text-sm"
            >
              <div>
                <div className="font-medium text-slate-900">{req.institution_name}</div>
                <div className="text-xs text-slate-500">{formatDate(req.requested_at)}</div>
              </div>
              <span
                className={`text-xs font-medium px-2 py-1 rounded-full ${
                  STATUS_BADGE_CLASS[req.status] ?? "bg-slate-100 text-slate-700"
                }`}
              >
                {getStatusBadgeLabel(req.status)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
