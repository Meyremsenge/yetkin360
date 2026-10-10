"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listCertificateChecksForEngagement,
  resolveCertificateCheck,
  type CertificateCheck,
} from "@/lib/api/evidence";
import { ApiError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

/**
 * PLAN 3.55: koordinatörün/supervisor'un nihai CONFIRMED/REJECTED kararını
 * verdiği bölüm. AI hiçbir zaman bu kararı vermez — yalnız provider/kimlik
 * no/isim/doğrulama linkini çıkarıp buraya önerir. Butonları herkes görür
 * (final-analiz: frontend'de gizlemek yetkilendirme değildir) — yetkisiz bir
 * tıklama sunucudan 404 alır.
 */
export function CertificateChecksSection({
  engagementId,
  canComplain = false,
}: {
  engagementId: string;
  /** UX only: show the student's "Şikayet et" entry on pending checks. */
  canComplain?: boolean;
}) {
  const queryClient = useQueryClient();
  const QUERY_KEY = ["certificate-checks", engagementId] as const;
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const { data: checks } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => listCertificateChecksForEngagement(engagementId),
  });

  if (!checks || checks.length === 0) return null;

  const handleResolve = async (checkId: string, decision: "CONFIRMED" | "REJECTED") => {
    setResolveError(null);
    setResolvingId(checkId);
    try {
      await resolveCertificateCheck(checkId, decision);
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setResolveError(messages.calismalar.certificateCheckAlreadyResolved);
      } else {
        setResolveError(messages.errors.generic);
      }
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <section className="mt-8">
      <h2 className="text-lg font-bold mb-3">{messages.calismalar.certificateChecksSectionTitle}</h2>

      {resolveError && (
        <div role="alert" className="mb-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {resolveError}
        </div>
      )}

      <ul className="space-y-2">
        {checks.map((check: CertificateCheck) => (
          <li key={check.id} className="bg-white p-3 rounded-md border border-slate-200 text-sm">
            <p className="font-medium">{messages.calismalar.certificateCheckStatus[check.status]}</p>
            {check.status === "DONE" && (
              <div className="mt-1 space-y-0.5 text-slate-600">
                {check.provider && (
                  <p>
                    {messages.calismalar.certificateCheckProviderLabel}:{" "}
                {(messages.certificateProviders as Record<string, string>)[check.provider] ?? check.provider}
                  </p>
                )}
                {check.credential_id && (
                  <p>
                    {messages.calismalar.certificateCheckCredentialLabel}: {check.credential_id}
                  </p>
                )}
                {check.extracted_name && (
                  <p>
                    {messages.calismalar.certificateCheckNameLabel}: {check.extracted_name}{" "}
                    {check.name_match !== null && (
                      <span className={check.name_match ? "text-green-700" : "text-red-700"}>
                        (
                        {check.name_match
                          ? messages.calismalar.certificateCheckNameMatchYes
                          : messages.calismalar.certificateCheckNameMatchNo}
                        )
                      </span>
                    )}
                  </p>
                )}
                {check.extracted_course_name && (
                  <p>
                    {messages.calismalar.certificateCheckCourseLabel}: {check.extracted_course_name}
                  </p>
                )}
                {check.page_name && (
                  <p>
                    {messages.calismalar.certificateCheckPageNameLabel}: {check.page_name}{" "}
                    {check.page_match !== null && (
                      <span className={check.page_match ? "text-green-700" : "text-red-700"}>
                        (
                        {check.page_match
                          ? messages.calismalar.certificateCheckPageMatchYes
                          : messages.calismalar.certificateCheckPageMatchNo}
                        )
                      </span>
                    )}
                  </p>
                )}
                {check.page_course_name && (
                  <p>
                    {messages.calismalar.certificateCheckPageCourseLabel}: {check.page_course_name}{" "}
                    {check.course_match !== null && (
                      <span className={check.course_match ? "text-green-700" : "text-red-700"}>
                        (
                        {check.course_match
                          ? messages.calismalar.certificateCheckCourseMatchYes
                          : messages.calismalar.certificateCheckCourseMatchNo}
                        )
                      </span>
                    )}
                  </p>
                )}
                {check.verify_url && (
                  <p>
                    <a
                      href={check.verify_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-700 hover:underline"
                    >
                      {messages.calismalar.certificateCheckVerifyLinkLabel}
                    </a>
                  </p>
                )}
                {!check.page_name && !check.page_course_name && (
                  <p className="mt-2 rounded-md border border-amber-300 bg-amber-50 p-2 text-amber-900">
                    {check.verify_url
                      ? messages.calismalar.certificateCheckManualVerifyNotice
                      : messages.calismalar.certificateCheckNoVerifyLinkNotice}
                  </p>
                )}
              </div>
            )}

            {check.decision === "PENDING" && canComplain && (
              <Link
                href={`/sikayetlerim/yeni?subject_type=CERTIFICATE_CHECK&subject_id=${encodeURIComponent(check.id)}`}
                className="mt-2 inline-block text-xs font-medium text-success underline underline-offset-4"
              >
                {messages.complaints.reportAction}
              </Link>
            )}

            {check.decision === "PENDING" ? (
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => handleResolve(check.id, "CONFIRMED")}
                  disabled={resolvingId === check.id}
                  className="px-3 py-1 bg-slate-900 text-white text-xs rounded-md hover:bg-slate-700 disabled:bg-slate-300"
                >
                  {messages.calismalar.certificateCheckConfirmButton}
                </button>
                <button
                  type="button"
                  onClick={() => handleResolve(check.id, "REJECTED")}
                  disabled={resolvingId === check.id}
                  className="px-3 py-1 border border-slate-300 text-slate-700 text-xs rounded-md hover:bg-slate-100 disabled:bg-slate-100"
                >
                  {messages.calismalar.certificateCheckRejectButton}
                </button>
              </div>
            ) : (
              <p className="mt-2 italic text-xs text-slate-500">
                {check.decision === "CONFIRMED"
                  ? messages.calismalar.certificateCheckDecisionConfirmed
                  : messages.calismalar.certificateCheckDecisionRejected}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
