"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPublicProfile } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

export default function PublicProfilePage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  const { data: profile, isLoading, isError, error } = useQuery({
    queryKey: ["publicProfile", slug],
    queryFn: () => getPublicProfile(slug),
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="p-6 max-w-2xl mx-auto">
        {isLoading ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error instanceof ApiError && error.status === 404
              ? messages.publicProfile.notFound
              : error instanceof NetworkError
                ? error.message
                : messages.errors.generic}
          </div>
        ) : profile ? (
          <>
            <h1 className="text-3xl font-bold mb-6">{profile.display_name}</h1>

            {profile.verified_experiences.length === 0 ? (
              <p className="text-slate-600">{messages.publicProfile.empty}</p>
            ) : (
              <div className="space-y-4">
                {profile.verified_experiences.map((exp) => (
                  <div key={exp.id} className="bg-white p-4 rounded-md border border-slate-200">
                    <div className="mb-2">
                      <h2 className="font-semibold text-lg">{exp.role_snapshot}</h2>
                      <p className="text-sm text-slate-600">{exp.organization_name_snapshot}</p>
                    </div>
                    <div className="text-xs text-slate-500 space-y-1">
                      {(exp.started_on_snapshot || exp.ended_on_snapshot) && (
                        <p>
                          {exp.started_on_snapshot ?? "-"} – {exp.ended_on_snapshot ?? "-"}
                        </p>
                      )}
                      <p>{exp.claim_type}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
