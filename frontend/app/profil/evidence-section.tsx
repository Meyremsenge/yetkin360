"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getMySignals, getMyVerifiedExperiences, setMyVerifiedExperienceVisibility } from "@/lib/api/client";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { VerifiedSeal } from "@/components/ui/verified-seal";
import { ProfileSection, SkeletonRows, EmptyNote, focusRingClass } from "./profile-ui";

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

const STRENGTH_LEVEL: Record<string, number> = { NONE: 0, WEAK: 1, MODERATE: 2, STRONG: 3 };

/** Owner switch: PUBLIC shows the record on /p/[slug] and makes its /v link resolve. */
function ExperienceVisibilityToggle({ experience }: { experience: VerifiedExperience }) {
  const queryClient = useQueryClient();
  const [failed, setFailed] = useState(false);
  const isPublic = experience.visibility === "PUBLIC";
  const mutation = useMutation({
    mutationFn: (next: "PUBLIC" | "PRIVATE") => setMyVerifiedExperienceVisibility(experience.id, next),
    onMutate: () => setFailed(false),
    onError: () => setFailed(true),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["talent-verified-experiences"] }),
  });
  const labelId = `exp-visibility-${experience.id}`;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          role="switch"
          aria-checked={isPublic}
          aria-labelledby={labelId}
          disabled={mutation.isPending}
          onClick={() => mutation.mutate(isPublic ? "PRIVATE" : "PUBLIC")}
          className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors disabled:opacity-50 ${
            isPublic ? "border-success bg-success" : "border-border bg-muted"
          } ${focusRingClass}`}
        >
          <span
            aria-hidden="true"
            className={`inline-block h-3.5 w-3.5 rounded-full bg-card shadow-sm transition-transform motion-reduce:transition-none ${
              isPublic ? "translate-x-[18px]" : "translate-x-[2px]"
            }`}
          />
        </button>
        <span id={labelId} className="text-sm text-foreground" title={messages.profil.experiencePublicHint}>
          {messages.profil.experiencePublicLabel}
        </span>
      </div>
      {isPublic && experience.public_token ? (
        <Link
          href={`/v/${encodeURIComponent(experience.public_token)}`}
          className={`text-sm text-success underline-offset-4 hover:underline ${focusRingClass}`}
        >
          {messages.profil.experienceVerificationLink} ↗
        </Link>
      ) : null}
      <p aria-live="polite" className="basis-full text-[13px] text-destructive empty:hidden">
        {failed ? messages.profil.experienceVisibilityError : ""}
      </p>
    </div>
  );
}

// Signals produced inside an engagement: with no named attester they come from
// the engagement record, not from the student's own claim.
const ENGAGEMENT_SOURCES = new Set(["TASK", "DELIVERABLE", "EVALUATION", "ATTESTATION"]);

function signalOrigin(signal: Signal): string {
  if (signal.attested_by) return signal.attested_by;
  return ENGAGEMENT_SOURCES.has(signal.source_type)
    ? messages.profil.engagementSourceLabel
    : messages.profil.selfClaimLabel;
}

function StrengthBars({ strength }: { strength: string }) {
  const filled = STRENGTH_LEVEL[strength] ?? 0;
  return (
    <span aria-hidden="true" className="inline-flex items-end gap-0.5">
      {[1, 2, 3].map((n) => (
        <span
          key={n}
          className={`w-1 rounded-sm ${n <= filled ? "bg-foreground" : "bg-border"}`}
          style={{ height: 4 + n * 3 }}
        />
      ))}
    </span>
  );
}

function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat("tr-TR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

// Long breakdowns stay scannable: a few skills open the list, the rest behind a toggle.
const VISIBLE_SKILL_GROUPS = 6;

/**
 * One skill as a single summary row (seal, name, evidence count, strongest
 * level); the dated signal list opens on demand.
 */
function SignalGroupCard({ group }: { group: SignalGroup }) {
  // AC-1: Sort signals by occurred_at descending (newest first)
  const sortedSignals = [...group.signals].sort(
    (a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()
  );
  const active = group.signals.filter((s) => !s.superseded);
  // Sealed only when a real (non self-claim, non superseded) signal backs the skill
  const hasEvidence = active.some(
    (s) => s.source_type !== "SELF_CLAIM" && (STRENGTH_LEVEL[s.strength] ?? 0) > 0
  );
  const strongest = active.reduce<string>(
    (best, s) => ((STRENGTH_LEVEL[s.strength] ?? 0) > (STRENGTH_LEVEL[best] ?? 0) ? s.strength : best),
    "NONE"
  );

  return (
    <li>
      <details
        className={`group rounded-md border ${hasEvidence ? "border-success/40 bg-success/5" : "border-border"}`}
      >
        <summary
          className={`flex cursor-pointer list-none items-center gap-3 rounded-md px-4 py-3 [&::-webkit-details-marker]:hidden ${focusRingClass}`}
        >
          {hasEvidence && <VerifiedSeal size="sm" label={messages.profil.evidenceBackedLabel} />}
          {/* AC-1: Skill name grouped */}
          <h4
            className={`min-w-0 flex-1 truncate text-[15px] font-medium ${
              hasEvidence ? "text-success" : "text-muted-foreground"
            }`}
          >
            {group.skill.name_tr}
          </h4>
          <span
            role="img"
            aria-label={messages.profil.strongestLevel.replace("{level}", getStrengthLabel(strongest))}
            className="inline-flex"
          >
            <StrengthBars strength={strongest} />
          </span>
          <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
            {messages.profil.signalCount.replace("{count}", String(group.signals.length))}
          </span>
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180 motion-reduce:transition-none"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </summary>

        <ul className="mx-4 divide-y divide-border border-t border-border pb-1">
          {sortedSignals.map((signal, idx) => (
            <li
              key={idx}
              className={`flex items-start justify-between gap-3 py-2.5 ${signal.superseded ? "opacity-60" : ""}`}
            >
              <div className="min-w-0 flex-1">
                {/* AC-1: source_type, strength, date */}
                <div className="flex flex-wrap items-center gap-x-2 text-sm text-foreground">
                  <span className="font-medium">{getSourceTypeLabel(signal.source_type)}</span>
                  <StrengthBars strength={signal.strength} />
                  <span className="text-muted-foreground">{getStrengthLabel(signal.strength)}</span>
                </div>
                {/* AC-5: attested_by, else engagement record or "Kendi beyanı" */}
                <div className="mt-0.5 text-[13px] text-muted-foreground">{signalOrigin(signal)}</div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className="font-mono text-xs text-muted-foreground">{formatDate(signal.occurred_at)}</span>
                {/* AC-4: superseded badge */}
                {signal.superseded && <Badge variant="warning">{messages.profil.supersededBadge}</Badge>}
              </div>
            </li>
          ))}
        </ul>
      </details>
    </li>
  );
}

/**
 * `part` lets /profil put signals and verified experiences on separate tabs;
 * without it both render in one card.
 */
export default function EvidenceSection({ part = "all" }: { part?: "all" | "signals" | "experiences" }) {
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

  const [showAllSkills, setShowAllSkills] = useState(false);
  const signalGroups = (signalsData?.items as SignalGroup[]) ?? [];
  const verifiedExperiences = (verifiedExpData?.items as VerifiedExperience[]) ?? [];

  // AC-3: Retry handler for signals error
  const handleRetry = () => {
    refetchSignals();
  };

  const signalsBlock = (
    <>
      {/* ===== Signals Section ===== */}
      <div className={part === "all" ? "mb-8" : undefined}>
        {part === "all" && (
          <h3 className="mb-3 font-serif text-lg font-medium text-foreground">
            {messages.profil.signalsSectionTitle}
          </h3>
        )}

        {signalsLoading && <SkeletonRows />}

        {signalsError && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            <div className="font-medium">{messages.profil.signalsLoadError}</div>
            <Button onClick={handleRetry} variant="secondary" size="sm" className={focusRingClass}>
              {messages.profil.retryButton}
            </Button>
          </div>
        )}

        {!signalsLoading && !signalsError && signalGroups.length === 0 && (
          <EmptyNote title={messages.profil.emptySignalsMessage} hint={messages.profil.emptySignalsHint} />
        )}

        {!signalsLoading && !signalsError && signalGroups.length > 0 && (
          <>
            <ul className="space-y-2">
              {(showAllSkills ? signalGroups : signalGroups.slice(0, VISIBLE_SKILL_GROUPS)).map((group) => (
                <SignalGroupCard key={group.skill.id} group={group} />
              ))}
            </ul>
            {signalGroups.length > VISIBLE_SKILL_GROUPS && (
              <button
                type="button"
                aria-expanded={showAllSkills}
                onClick={() => setShowAllSkills((value) => !value)}
                className={`mt-3 text-sm font-medium text-success underline-offset-4 hover:underline ${focusRingClass}`}
              >
                {showAllSkills
                  ? messages.profil.showFewerSkills
                  : messages.profil.showAllSkills.replace("{count}", String(signalGroups.length))}
              </button>
            )}
          </>
        )}
      </div>

    </>
  );

  const experiencesBlock = (
    <>
      {/* ===== Verified Experiences Section ===== */}
      <div>
        {part === "all" && (
          <h3 className="mb-3 font-serif text-lg font-medium text-foreground">
            {messages.profil.verifiedExperiencesSectionTitle}
          </h3>
        )}

        {verifiedExpLoading && <SkeletonRows rows={2} />}

        {verifiedExpError && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            {messages.errors.generic}
          </div>
        )}

        {!verifiedExpLoading && !verifiedExpError && verifiedExperiences.length === 0 && (
          <EmptyNote title={messages.profil.emptyVerifiedExperiencesMessage} />
        )}

        {!verifiedExpLoading && !verifiedExpError && verifiedExperiences.length > 0 && (
          <ul className={part === "experiences" ? "grid gap-3 md:grid-cols-2" : "space-y-3"}>
            {verifiedExperiences.map((exp) => (
              <li
                key={exp.id}
                className="flex items-start gap-3 rounded-md border border-success/40 bg-success/5 p-4"
              >
                <VerifiedSeal size="sm" label={messages.profil.verifiedLabel} />
                <div className="min-w-0">
                  <div className="font-medium text-foreground">{exp.organization_name_snapshot}</div>
                  <div className="text-sm text-foreground">{exp.role_snapshot}</div>
                  <div className="mt-1 font-mono text-xs text-muted-foreground">
                    {exp.started_on_snapshot ? formatDate(exp.started_on_snapshot) : messages.profil.unknownStartLabel} – {exp.ended_on_snapshot ? formatDate(exp.ended_on_snapshot) : messages.profil.ongoingLabel}
                  </div>
                  <ExperienceVisibilityToggle experience={exp} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );

  if (part === "signals") {
    return (
      <ProfileSection title={messages.profil.evidenceSection} description={messages.profil.signalsTabDescription}>
        {signalsBlock}
      </ProfileSection>
    );
  }
  if (part === "experiences") {
    return (
      <ProfileSection
        title={messages.profil.verifiedExperiencesSectionTitle}
        description={messages.profil.verifiedExperiencesDescription}
      >
        {experiencesBlock}
      </ProfileSection>
    );
  }
  return (
    <ProfileSection title={messages.profil.evidenceSection} description={messages.profil.evidenceDescription}>
      {signalsBlock}
      {experiencesBlock}
    </ProfileSection>
  );
}
