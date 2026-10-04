"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPublicVerification } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export default function PublicVerificationPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const { data: verification, isLoading, isError, error } = useQuery({
    queryKey: ["publicVerification", token],
    queryFn: () => getPublicVerification(token),
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="p-6 max-w-2xl mx-auto">
        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error instanceof ApiError && error.status === 404
              ? messages.publicVerification.notFound
              : error instanceof NetworkError
                ? error.message
                : messages.errors.generic}
          </div>
        ) : verification ? (
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-bold mb-2">{verification.title}</h1>
              <p className="text-lg text-slate-600">{verification.talent_name}</p>
            </div>

            <div className="grid grid-cols-1 gap-4 bg-white p-4 rounded-md border border-slate-200">
              <div>
                <dt className="text-xs font-medium text-slate-500">{messages.publicVerification.organizationLabel}</dt>
                <dd className="text-lg">{verification.organization_name}</dd>
                <dd className="text-sm text-slate-500">
                  {messages.publicVerification.trustLevelLabel}: {verification.organization_trust_level}
                </dd>
                {verification.organization_trust_level === "T1" && (
                  <p
                    role="note"
                    className="mt-2 rounded-md border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900"
                  >
                    {messages.publicVerification.unverifiedOrganizationNotice}
                  </p>
                )}
                {verification.organization_domain && (
                  <dd className="text-sm text-slate-500">
                    {messages.publicVerification.domainLabel}: {verification.organization_domain}
                  </dd>
                )}
              </div>
              {verification.institution_name && (
                <div>
                  <dt className="text-xs font-medium text-slate-500">{messages.publicVerification.institutionLabel}</dt>
                  <dd className="text-lg">{verification.institution_name}</dd>
                  {verification.institution_trust_level && (
                    <dd className="text-sm text-slate-500">
                      {messages.publicVerification.trustLevelLabel}: {verification.institution_trust_level}
                    </dd>
                  )}
                </div>
              )}
              {(verification.started_on || verification.ended_on) && (
                <div>
                  <dt className="text-xs font-medium text-slate-500">{messages.publicVerification.periodLabel}</dt>
                  <dd className="text-sm">
                    {verification.started_on ?? "-"} – {verification.ended_on ?? "-"}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-xs font-medium text-slate-500">{messages.publicVerification.verifiedAtLabel}</dt>
                <dd className="text-sm">{new Date(verification.verified_at).toLocaleDateString("tr-TR")}</dd>
              </div>
            </div>

            {verification.attested_skills.length > 0 && (
              <div className="bg-white p-4 rounded-md border border-slate-200">
                <h2 className="font-semibold mb-3">{messages.publicVerification.attestedSkillsTitle}</h2>
                <ul className="space-y-2">
                  {verification.attested_skills.map((skill, idx) => (
                    <li key={idx} className="text-sm">
                      <span className="font-medium">{skill.name_tr}</span>
                      {skill.attestor_organization && (
                        <span className="text-slate-500 ml-2">({skill.attestor_organization})</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
