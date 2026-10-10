import Link from "next/link";
import { SealMark } from "@/components/brand/brand-mark";
import { Badge } from "@/components/ui/badge";
import { publicFocusRing } from "@/components/public-top-bar";
import type { PublicVerifiedExperience } from "@/lib/api/public";
import messages from "@/messages/tr.json";
import { cn } from "@/lib/utils";
import { formatDuration, formatMonthYear, formatPeriod } from "./format";

const t = messages.publicProfile;
const trustLabels = messages.publicVerification.trustLevels as Record<string, string>;
const claimTypeLabels = messages.calismalar.claimType as Record<string, string>;
const TRUST_VARIANT: Record<string, "default" | "warning" | "success"> = {
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};

/**
 * One verified experience as a certificate card. The seal "stamps" once on
 * mount (y360-stamp, off under reduced motion); hover lifts the card slightly.
 */
export function ExperienceCard({ experience, index }: { experience: PublicVerifiedExperience; index: number }) {
  const period = formatPeriod(experience.started_on_snapshot, experience.ended_on_snapshot);
  const duration = formatDuration(experience.started_on_snapshot, experience.ended_on_snapshot);
  const trust = experience.organization_trust_level;
  const claimLabel = claimTypeLabels[experience.claim_type];
  const attested = experience.skills ?? [];
  const evidenced = experience.evidenced_skills ?? [];
  const attestors = Array.from(new Set(attested.map((s) => s.attestor_organization).filter(Boolean)));

  return (
    <li className="relative grid gap-3 md:grid-cols-[132px_1fr] md:gap-6 print:break-inside-avoid">
      <div className="flex items-baseline gap-2 font-mono text-xs tabular-nums text-muted-foreground md:block md:pt-6 md:text-right">
        {experience.started_on_snapshot ? (
          <span className="block text-foreground">{formatMonthYear(experience.started_on_snapshot)}</span>
        ) : null}
        {duration ? <span className="block md:mt-1">{duration}</span> : null}
      </div>

      <article
        className={cn(
          "group relative rounded-lg border border-border bg-card p-5 transition-[transform,border-color] duration-200 ease-out md:p-6",
          "hover:-translate-y-0.5 hover:border-foreground/25 motion-reduce:transition-none motion-reduce:hover:translate-y-0",
          "print:border-foreground/30"
        )}
      >
        <div aria-hidden="true" className="pointer-events-none absolute inset-[5px] rounded-md border border-border/60" />
        <span
          className="y360-stamp absolute right-4 top-4 h-11 w-11 md:right-5 md:top-5 md:h-12 md:w-12"
          style={{ animationDelay: `${200 + index * 140}ms` }}
        >
          <SealMark label={t.sealLabel} className="h-full w-full" />
        </span>
        <div className="relative pr-14">
          <h3 className="font-serif text-xl font-semibold leading-snug text-foreground">{experience.role_snapshot}</h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-foreground">
            <span>{experience.organization_name_snapshot}</span>
            {trust && trustLabels[trust] ? <Badge variant={TRUST_VARIANT[trust] ?? "default"}>{trustLabels[trust]}</Badge> : null}
          </p>
          <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted-foreground">
            {period ? <span className="font-mono text-xs tabular-nums">{period}</span> : null}
            {claimLabel ? (
              <>
                <span aria-hidden="true">·</span>
                <span>{claimLabel}</span>
              </>
            ) : null}
            {experience.institution_name_snapshot ? (
              <>
                <span aria-hidden="true">·</span>
                <span>{experience.institution_name_snapshot}</span>
              </>
            ) : null}
          </p>
          {trust === "T1" ? <p className="mt-2 text-[13px] text-warning">{t.unverifiedOrganization}</p> : null}
        </div>

        {attested.length > 0 || evidenced.length > 0 ? (
          <div className="relative mt-4 space-y-3 border-t border-border pt-4">
            {attested.length > 0 ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground">{t.attestedSkillsLabel}</p>
                <ul className="mt-1.5 flex flex-wrap gap-2">
                  {attested.map((skill) => (
                    <li
                      key={skill.name_tr}
                      className="inline-flex h-7 items-center gap-1.5 rounded-md border border-success/30 bg-success/[0.06] px-2 text-[13px] font-medium text-foreground"
                    >
                      <SealMark className="h-3.5 w-3.5" />
                      {skill.name_tr}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {evidenced.length > 0 ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground">{t.evidencedSkillsLabel}</p>
                <ul className="mt-1.5 flex flex-wrap gap-2">
                  {evidenced.map((skill) => (
                    <li
                      key={skill.name_tr}
                      className="inline-flex h-7 items-center rounded-md border border-dashed border-border px-2 text-[13px] text-muted-foreground"
                    >
                      {skill.name_tr}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {attestors.length > 0 || experience.public_token ? (
          <div className="relative mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-dashed border-border pt-3">
            <p className="text-[13px] text-muted-foreground">
              {attestors.length > 0 ? t.attestedBy.replace("{org}", attestors.join(", ")) : null}
            </p>
            {experience.public_token ? (
              <Link
                href={`/v/${encodeURIComponent(experience.public_token)}`}
                className={cn(
                  "inline-flex items-center gap-1 text-sm font-medium text-success underline-offset-4 hover:underline print:hidden",
                  publicFocusRing
                )}
              >
                {t.viewVerification}
                <span aria-hidden="true">↗</span>
              </Link>
            ) : null}
          </div>
        ) : null}
      </article>
    </li>
  );
}
