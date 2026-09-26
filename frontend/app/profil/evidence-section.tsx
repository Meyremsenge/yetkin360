"use client";

import { useQuery } from "@tanstack/react-query";
import { getMySignals, getMyVerifiedExperiences } from "@/lib/api/client";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";

interface Signal {
  source_type: string;
  strength: string;
  occurred_at: string;
  attested_by: string | null;
  superseded: boolean;
}

interface SignalGroup {
  skill: { id: string; name_tr: string; name_en: string; slug: string; category: string };
  signals: Signal[];
}

interface VerifiedExperience {
  id: string;
  organization_name_snapshot: string;
  role_snapshot: string;
  started_on_snapshot: string | null;
  ended_on_snapshot: string | null;
  institution_name_snapshot: string | null;
  claim_type: string;
  visibility: string;
  public_token: string | null;
  created_at: string;
}

function getSourceTypeLabel(sourceType: string): string {
  const sourceTypeMap: Record<string, string> = {
    SELF_CLAIM: messages.profil.sourceTypeSelfClaim,
    DELIVERABLE: messages.profil.sourceTypeDeliverable,
    TASK: messages.profil.sourceTypeTask,
    EVALUATION: messages.profil.sourceTypeEvaluation,
    ATTESTATION: messages.profil.sourceTypeAttestation,
    EXTERNAL: messages.profil.sourceTypeExternal,
  };
  return sourceTypeMap[sourceType] || sourceType;
}

function getStrengthLabel(strength: string): string {
  const strengthMap: Record<string, string> = {
    NONE: messages.profil.strengthNone,
    WEAK: messages.profil.strengthWeak,
    MODERATE: messages.profil.strengthModerate,
    STRONG: messages.profil.strengthStrong,
  };
  return strengthMap[strength] || strength;
}

function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat("tr-TR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

export default function EvidenceSection() {
  // AC-1/AC-12: Independent useQuery for signals
  const SIGNALS_QUERY_KEY = ["talent-signals"] as const;
  const {
    data: signalsData,
    isLoading: signalsLoading,
    isError: signalsError,
    refetch: refetchSignals,
  } = useQuery({
    queryKey: SIGNALS_QUERY_KEY,
    queryFn: getMySignals,
  });

  // AC-12: Independent useQuery for verified experiences
  const VERIFIED_EXP_QUERY_KEY = ["talent-verified-experiences"] as const;
  const {
    data: verifiedExpData,
    isLoading: verifiedExpLoading,
    isError: verifiedExpError,
  } = useQuery({
    queryKey: VERIFIED_EXP_QUERY_KEY,
    queryFn: getMyVerifiedExperiences,
  });

  const signalGroups = (signalsData?.items as SignalGroup[]) ?? [];
  const verifiedExperiences = (verifiedExpData?.items as VerifiedExperience[]) ?? [];

  // AC-3: Retry handler for signals error
  const handleRetry = () => {
    refetchSignals();
  };

  return (
    <div className="rounded-md bg-slate-50 p-6 border border-slate-200 mt-8">
      <h2 className="text-xl font-bold mb-6">{messages.profil.evidenceSection}</h2>

      {/* ===== Signals Section ===== */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold mb-4">{messages.profil.signalsSectionTitle}</h3>

        {signalsLoading && <p className="text-slate-600">{messages.shell.loading}</p>}

        {signalsError && (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-600 mb-4">
            <div className="font-medium mb-3">{messages.profil.signalsLoadError}</div>
            <Button onClick={handleRetry} className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 text-sm">
              {messages.profil.retryButton}
            </Button>
          </div>
        )}

        {!signalsLoading && !signalsError && signalGroups.length === 0 && (
          <p className="text-slate-600">{messages.profil.emptySignalsMessage}</p>
        )}

        {!signalsLoading && !signalsError && signalGroups.length > 0 && (
          <div className="space-y-6">
            {signalGroups.map((group) => {
              // AC-1: Sort signals by occurred_at descending (newest first)
              const sortedSignals = [...group.signals].sort((a, b) => {
                const dateA = new Date(a.occurred_at).getTime();
                const dateB = new Date(b.occurred_at).getTime();
                return dateB - dateA;
              });

              return (
                <div key={group.skill.id} className="border-l-4 border-slate-300 pl-4">
                  {/* AC-1: Skill name grouped */}
                  <h4 className="font-semibold text-slate-900 mb-3">{group.skill.name_tr}</h4>

                  <div className="space-y-3">
                    {sortedSignals.map((signal, idx) => (
                      <div
                        key={idx}
                        className={`bg-white p-3 rounded border border-slate-200 ${
                          signal.superseded ? "opacity-60" : ""
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            {/* AC-1: source_type, strength, date */}
                            <div className="text-sm text-slate-700 mb-1">
                              {getSourceTypeLabel(signal.source_type)} • {getStrengthLabel(signal.strength)}
                            </div>
                            <div className="text-xs text-slate-500 mb-1">{formatDate(signal.occurred_at)}</div>

                            {/* AC-5: attested_by or "Kendi beyanı" */}
                            <div className="text-sm font-medium text-slate-900">
                              {signal.attested_by || messages.profil.selfClaimLabel}
                            </div>
                          </div>

                          {/* AC-4: superseded badge */}
                          {signal.superseded && (
                            <div className="ml-2 bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">
                              {messages.profil.supersededBadge}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ===== Verified Experiences Section ===== */}
      <div>
        <h3 className="text-lg font-semibold mb-4">{messages.profil.verifiedExperiencesSectionTitle}</h3>

        {verifiedExpLoading && <p className="text-slate-600">{messages.shell.loading}</p>}

        {verifiedExpError && (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-600">
            {messages.errors.generic}
          </div>
        )}

        {!verifiedExpLoading && !verifiedExpError && verifiedExperiences.length === 0 && (
          <p className="text-slate-600">{messages.profil.emptyVerifiedExperiencesMessage}</p>
        )}

        {!verifiedExpLoading && !verifiedExpError && verifiedExperiences.length > 0 && (
          <div className="space-y-4">
            {verifiedExperiences.map((exp) => (
              <div key={exp.id} className="bg-white p-4 rounded border border-slate-200">
                <div className="font-semibold text-slate-900 mb-1">{exp.organization_name_snapshot}</div>
                <div className="text-sm text-slate-700 mb-2">{exp.role_snapshot}</div>
                <div className="text-xs text-slate-500">
                  {exp.started_on_snapshot ? formatDate(exp.started_on_snapshot) : messages.profil.unknownStartLabel} – {exp.ended_on_snapshot ? formatDate(exp.ended_on_snapshot) : messages.profil.ongoingLabel}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
