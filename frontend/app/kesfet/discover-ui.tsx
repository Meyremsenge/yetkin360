import Link from "next/link";
import type { ReactNode } from "react";
import { SealMark } from "@/components/brand/brand-mark";
import { UpheldComplaintBadge } from "@/components/upheld-complaint-badge";
import type { DiscoverOrganization, DiscoverTalent } from "@/lib/api/discover";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.kesfet;

export const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 focus-visible:ring-offset-card";

// Sealed skills shown on a card before collapsing into "+N more".
const VISIBLE_SKILLS = 6;

// Inline lucide paths (no icon dependency, brief §1.5).
const ICONS = {
  search: (
    <>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </>
  ),
  landmark: (
    <>
      <path d="M3 22h18" />
      <path d="M6 18v-7M10 18v-7M14 18v-7M18 18v-7" />
      <path d="M12 2 20 7H4z" />
    </>
  ),
  cap: (
    <>
      <path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z" />
      <path d="M22 10v6" />
      <path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5" />
    </>
  ),
  pin: (
    <>
      <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0" />
      <circle cx="12" cy="10" r="3" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
      <path d="M2 12h20" />
    </>
  ),
  arrow: (
    <>
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </>
  ),
  x: (
    <>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </>
  ),
  filter: (
    <>
      <path d="M3 6h18" />
      <path d="M7 12h10" />
      <path d="M10 18h4" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="5" />
      <path d="M20 21a8 8 0 0 0-16 0" />
    </>
  ),
  building: (
    <>
      <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" />
      <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
      <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2" />
      <path d="M10 6h4M10 10h4M10 14h4M10 18h4" />
    </>
  ),
  equal: (
    <>
      <path d="M5 9h14" />
      <path d="M5 15h14" />
    </>
  ),
  link: (
    <>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </>
  ),
  compass: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z" />
    </>
  ),
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("h-4 w-4 shrink-0", className)}
    >
      {ICONS[name]}
    </svg>
  );
}

export function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toLocaleUpperCase("tr");
}

/** Small check used inside sealed-skill chips. */
function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Mono strip on top of every record card: what kind of record, and its address. */
function RecordStrip({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-dashed border-border px-5 py-2.5 font-mono text-[11px] text-muted-foreground">
      <span className="uppercase tracking-[0.14em]">{label}</span>
      <span aria-hidden="true" className="h-px flex-1 bg-border" />
      <span className="truncate">{value}</span>
    </div>
  );
}

const cardFrame =
  "group relative flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card transition-colors duration-150 hover:border-muted-foreground/50 focus-within:border-success/60";

export type Facet = "department" | "city";

// Filter buttons sit above the card's stretched profile link (z-10).
const facetButton = cn(
  "relative z-10 rounded-sm underline decoration-transparent underline-offset-2 transition-colors duration-150 hover:text-foreground hover:decoration-current",
  FOCUS_RING
);

/**
 * A student as a registry card: who they are, where they study, and only the
 * skills an organization has attested to. The card body is one link to the
 * public profile (stretched link); skill chips, department and city are
 * separate buttons that narrow the directory to that value.
 */
export function TalentCard({
  talent,
  selectedSkills = [],
  onSkillClick,
  onFacetClick,
}: {
  talent: DiscoverTalent;
  selectedSkills?: string[];
  onSkillClick?: (skill: string) => void;
  onFacetClick?: (facet: Facet, value: string) => void;
}) {
  const metaParts: { key: string; value: string; facet?: Facet }[] = [
    ...(talent.institution_name ? [{ key: "institution", value: talent.institution_name }] : []),
    ...(talent.department ? [{ key: "department", value: talent.department, facet: "department" as const }] : []),
    ...(talent.city ? [{ key: "city", value: talent.city, facet: "city" as const }] : []),
  ];
  const metaIcon: IconName = talent.institution_name ? "landmark" : talent.department ? "cap" : "pin";
  const sealed = talent.verified_experience_count > 0;
  const shown = talent.sealed_skills.slice(0, VISIBLE_SKILLS);
  const hidden = talent.sealed_skills.length - shown.length;

  return (
    <article className={cardFrame}>
      <RecordStrip label={t.registryLabel} value={`/p/${talent.public_slug}`} />

      {sealed ? (
        <SealMark
          label={t.sealedStamp}
          className="y360-stamp pointer-events-none absolute right-4 top-11 h-12 w-12 -rotate-[8deg] text-success/85"
        />
      ) : null}

      <div className="flex flex-1 flex-col px-5 pb-5 pt-5">
        <div className={cn("flex items-start gap-4", sealed && "pr-14")}>
          <span
            aria-hidden="true"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-border bg-sand font-serif text-lg font-semibold text-foreground ring-1 ring-border ring-offset-[3px] ring-offset-card"
          >
            {initials(talent.full_name)}
          </span>
          <div className="min-w-0 pt-0.5">
            <h2 className="font-serif text-xl font-semibold leading-7 text-foreground decoration-success/60 underline-offset-4 group-hover:underline">
              {talent.full_name}
            </h2>
            {talent.headline ? <p className="mt-0.5 text-sm leading-5 text-foreground/90">{talent.headline}</p> : null}
            {metaParts.length > 0 ? (
              <div className="mt-1.5 flex items-start gap-1.5 text-xs leading-4 text-muted-foreground">
                <Icon name={metaIcon} className="mt-px h-3.5 w-3.5" />
                <p>
                  {metaParts.map((part, index) => (
                    <span key={part.key}>
                      {index > 0 ? " · " : null}
                      {part.facet && onFacetClick ? (
                        <button
                          type="button"
                          onClick={() => onFacetClick(part.facet as Facet, part.value)}
                          aria-label={(part.facet === "city" ? t.filterByCity : t.filterByDepartment).replace(
                            "{value}",
                            part.value
                          )}
                          className={facetButton}
                        >
                          {part.value}
                        </button>
                      ) : (
                        part.value
                      )}
                    </span>
                  ))}
                </p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-5">
          <p className="mb-2 text-xs font-medium text-muted-foreground">{t.sealedSkillsLabel}</p>
          {shown.length > 0 ? (
            <>
              <ul aria-label={t.sealedSkillsLabel} className="flex flex-wrap gap-1.5">
                {shown.map((skill) => {
                  const active = selectedSkills.includes(skill);
                  const chip = cn(
                    "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
                    active
                      ? "border-success bg-success text-background"
                      : "border-success/20 bg-success/[0.08] text-success"
                  );
                  return (
                    <li key={skill} className="flex">
                      {onSkillClick ? (
                        <button
                          type="button"
                          onClick={() => onSkillClick(skill)}
                          aria-pressed={active}
                          aria-label={(active ? t.unfilterBySkill : t.filterBySkill).replace("{skill}", skill)}
                          className={cn(
                            chip,
                            "relative z-10 transition-colors duration-150",
                            !active && "hover:border-success/50 hover:bg-success/[0.14]",
                            FOCUS_RING
                          )}
                        >
                          <CheckIcon />
                          {skill}
                        </button>
                      ) : (
                        <span className={chip}>
                          <CheckIcon />
                          {skill}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
              {hidden > 0 ? (
                <p className="mt-2 text-xs text-muted-foreground">{t.moreSkills.replace("{count}", String(hidden))}</p>
              ) : null}
            </>
          ) : (
            <p className="rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              {t.noSealedSkills}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border bg-background/70 px-5 py-3">
        <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
          <SealMark className={cn("h-4 w-4", sealed ? "text-success" : "text-muted-foreground/40")} />
          <span className="tabular-nums">
            {t.verifiedExperienceCount.replace("{count}", String(talent.verified_experience_count))}
          </span>
        </span>
        <Link
          href={`/p/${encodeURIComponent(talent.public_slug)}`}
          aria-label={t.viewProfileOf.replace("{name}", talent.full_name)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-sm text-sm font-medium text-success after:absolute after:inset-0 after:content-['']",
            FOCUS_RING
          )}
        >
          {t.viewProfile}
          <Icon name="arrow" className="h-3.5 w-3.5 transition-transform duration-150 motion-safe:group-hover:translate-x-0.5" />
        </Link>
      </div>
    </article>
  );
}

const TRUST_STEPS = ["T1", "T2", "T3", "T4"] as const;
const TRUST_TONE: Record<string, string> = {
  T1: "bg-warning",
  T2: "bg-foreground/70",
  T3: "bg-success",
  T4: "bg-success",
};

/** Four-step trust gauge: how far the organization's identity has been verified. */
function TrustGauge({ level }: { level: string }) {
  const reached = TRUST_STEPS.indexOf(level as (typeof TRUST_STEPS)[number]) + 1;
  const tone = TRUST_TONE[level] ?? "bg-muted-foreground";
  return (
    <span aria-hidden="true" className="flex items-center gap-1">
      {TRUST_STEPS.map((step, index) => (
        <span key={step} className={cn("h-1.5 w-5 rounded-full", index < reached ? tone : "bg-muted")} />
      ))}
    </span>
  );
}

/**
 * An organization as a short record: name, verified domain (T2+ only, the API
 * nulls it otherwise), and its trust level as a gauge plus words.
 */
export function OrganizationCard({
  organization,
  canStartEngagement,
}: {
  organization: DiscoverOrganization;
  canStartEngagement: boolean;
}) {
  const levels = messages.kurulusSec.verificationLevel as Record<string, string>;
  const levelLabel = levels[organization.verification_level] ?? organization.verification_level;

  return (
    <article className={cardFrame}>
      <RecordStrip label={t.organizationRecordLabel} value={organization.verification_level} />

      <div className="flex flex-1 flex-col px-5 py-5">
        <div className="flex items-start gap-4">
          <span
            aria-hidden="true"
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md border border-border bg-sand font-serif text-lg font-semibold text-foreground"
          >
            {initials(organization.name)}
          </span>
          <div className="min-w-0 pt-0.5">
            <h2 className="font-serif text-xl font-semibold leading-7 text-foreground">{organization.name}</h2>
            {organization.domain ? (
              <p className="mt-1 inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                <Icon name="globe" className="h-3.5 w-3.5" />
                <span>{organization.domain}</span>
              </p>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">{t.domainHidden}</p>
            )}
          </div>
        </div>

        <UpheldComplaintBadge count={organization.upheld_complaint_count} />

        <div className="mt-auto pt-5">
          <p className="mb-2 text-xs font-medium text-muted-foreground">{t.trustLabel}</p>
          <p className="inline-flex items-center gap-2.5 text-xs text-foreground">
            <TrustGauge level={organization.verification_level} />
            <span>{levelLabel}</span>
          </p>
        </div>
      </div>

      {canStartEngagement && (
        <div className="flex items-center justify-end border-t border-border bg-background/70 px-5 py-3">
          <Link
            href={`/calismalar/olustur?organization_id=${encodeURIComponent(organization.id)}`}
            aria-label={t.startEngagementWith.replace("{name}", organization.name)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-sm text-sm font-medium text-success after:absolute after:inset-0 after:content-['']",
              FOCUS_RING
            )}
          >
            {t.startEngagement}
            <Icon name="arrow" className="h-3.5 w-3.5 transition-transform duration-150 motion-safe:group-hover:translate-x-0.5" />
          </Link>
        </div>
      )}
    </article>
  );
}

const pulse = "animate-pulse rounded bg-muted motion-reduce:animate-none";

/** Card-shaped skeleton so the grid does not jump when results arrive. */
export function CardSkeleton({ variant }: { variant: "talent" | "organization" }) {
  return (
    <div aria-hidden="true" className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card">
      <div className="border-b border-dashed border-border px-5 py-3">
        <div className={cn("h-2.5 w-28", pulse)} />
      </div>
      <div className="flex gap-4 px-5 py-5">
        <div className={cn("h-14 w-14 shrink-0 rounded-full", pulse, variant === "organization" && "rounded-md")} />
        <div className="flex-1 space-y-2 pt-1">
          <div className={cn("h-4 w-2/3", pulse)} />
          <div className={cn("h-3 w-1/2", pulse)} />
          {variant === "talent" ? <div className={cn("h-3 w-3/4", pulse)} /> : null}
        </div>
      </div>
      {variant === "talent" ? (
        <div className="flex gap-1.5 px-5 pb-5">
          <div className={cn("h-5 w-16 rounded-full", pulse)} />
          <div className={cn("h-5 w-20 rounded-full", pulse)} />
          <div className={cn("h-5 w-12 rounded-full", pulse)} />
        </div>
      ) : null}
      <div className="mt-auto border-t border-border px-5 py-3.5">
        <div className={cn("h-3 w-32", pulse)} />
      </div>
    </div>
  );
}

/** Left-aligned empty state (brief §2.11): icon, title, what to do, action. */
export function EmptyState({
  icon,
  title,
  body,
  children,
}: {
  icon: IconName;
  title: string;
  body: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card px-6 py-8">
      <Icon name={icon} className="h-8 w-8 text-muted-foreground" />
      <p className="mt-4 text-base font-semibold text-foreground">{title}</p>
      <p className="mt-1 max-w-[520px] text-sm text-muted-foreground">{body}</p>
      {children ? <div className="mt-4 flex flex-wrap items-center gap-3">{children}</div> : null}
    </div>
  );
}
