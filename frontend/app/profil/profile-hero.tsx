"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMySignals, getMyVerifiedExperiences } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { focusRingClass } from "./profile-ui";

const t = messages.profil.hero;

type Visibility = keyof typeof t.visibility;

interface HeroSignal {
  source_type: string;
  strength: string;
  superseded: boolean;
}

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const last = words.length > 1 ? words[words.length - 1].charAt(0) : "";
  return `${words[0].charAt(0)}${last}`.toLocaleUpperCase("tr-TR");
}

function Stat({ label, value, accent }: { label: string; value: number | null; accent?: boolean }) {
  return (
    <div className="px-5 py-4">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd
        className={cn(
          "mt-1 font-serif text-2xl font-semibold tabular-nums",
          accent ? "text-success" : "text-foreground"
        )}
      >
        {value ?? "–"}
      </dd>
    </div>
  );
}

/**
 * Identity card on top of /profil: who you are, who can see you, your share
 * link, and real counts from the same queries the evidence section uses.
 */
export default function ProfileHero({ profile }: { profile: Record<string, unknown> }) {
  const [copied, setCopied] = useState(false);

  // Same query keys as EvidenceSection, so the data is fetched once.
  const signals = useQuery({ queryKey: ["talent-signals"], queryFn: getMySignals });
  const experiences = useQuery({
    queryKey: ["talent-verified-experiences"],
    queryFn: getMyVerifiedExperiences,
  });

  const name = typeof profile.full_name === "string" ? profile.full_name : "";
  const headline = typeof profile.headline === "string" ? profile.headline : "";
  const visibility = (typeof profile.visibility === "string" ? profile.visibility : "INSTITUTION") as Visibility;
  const slug = typeof profile.public_slug === "string" && profile.public_slug ? profile.public_slug : null;
  const meta = [
    typeof profile.department === "string" ? profile.department : null,
    typeof profile.study_year === "number" ? t.studyYear.replace("{n}", String(profile.study_year)) : null,
    typeof profile.city === "string" ? profile.city : null,
  ].filter(Boolean);

  const groups = (signals.data?.items as { signals: HeroSignal[] }[] | undefined) ?? null;
  const backedSkills = groups
    ? groups.filter((g) =>
        g.signals.some((s) => !s.superseded && s.source_type !== "SELF_CLAIM" && s.strength !== "NONE")
      ).length
    : null;
  const signalCount = groups ? groups.reduce((sum, g) => sum + g.signals.length, 0) : null;
  const verifiedCount = experiences.data ? experiences.data.items.length : null;

  const isPublic = visibility === "PUBLIC" && slug;
  const publicPath = slug ? `/p/${encodeURIComponent(slug)}` : "";
  const publicUrl = typeof window !== "undefined" ? `${window.location.origin}${publicPath}` : publicPath;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(publicUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked; the link stays visible for manual copy.
    }
  };

  return (
    <section className="mt-6 overflow-hidden rounded-xl border border-border bg-card">
      <div className="relative flex flex-col gap-6 p-5 sm:p-7 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-5">
          <span
            aria-hidden="true"
            className="flex h-[72px] w-[72px] shrink-0 items-center justify-center rounded-full bg-success font-serif text-2xl font-semibold text-background ring-4 ring-success/10"
          >
            {initials(name)}
          </span>
          <div className="min-w-0">
            <p className="font-serif text-[26px] font-semibold leading-tight text-foreground">{name}</p>
            {headline ? <p className="mt-1 text-[15px] text-foreground">{headline}</p> : null}
            {meta.length > 0 ? (
              <p className="mt-1 text-sm text-muted-foreground">{meta.join(" · ")}</p>
            ) : null}
            <p
              className={cn(
                "mt-3 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
                visibility === "PUBLIC"
                  ? "border-success/30 bg-success/10 text-success"
                  : "border-border bg-muted text-muted-foreground"
              )}
            >
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
              {t.visibility[visibility] ?? t.visibility.INSTITUTION}
            </p>
          </div>
        </div>

        {isPublic ? (
          <div className="w-full rounded-lg border border-border bg-background p-4 lg:max-w-[380px]">
            <p className="text-xs font-medium text-muted-foreground">{t.publicLinkTitle}</p>
            <p className="mt-1.5 truncate font-mono text-[13px] text-foreground" title={publicUrl}>
              {publicUrl}
            </p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={copy}
                className={cn(
                  "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-muted",
                  focusRingClass
                )}
              >
                {copied ? t.copied : t.copy}
              </button>
              <a
                href={publicPath}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  "inline-flex h-8 items-center gap-1.5 rounded-md bg-success px-3 text-[13px] font-medium text-background transition-colors hover:bg-success/90",
                  focusRingClass
                )}
              >
                {t.view}
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path d="M7 7h10v10M7 17 17 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
            </div>
          </div>
        ) : (
          <div className="w-full rounded-lg border border-dashed border-border p-4 lg:max-w-[380px]">
            <p className="text-sm font-medium text-foreground">{t.notPublicTitle}</p>
            <p className="mt-1 text-[13px] text-muted-foreground">{t.notPublicHint}</p>
          </div>
        )}
      </div>

      <dl className="grid grid-cols-3 divide-x divide-border border-t border-border bg-background/60">
        <Stat label={t.stats.verified} value={verifiedCount} accent />
        <Stat label={t.stats.backedSkills} value={backedSkills} />
        <Stat label={t.stats.signals} value={signalCount} />
      </dl>
    </section>
  );
}
