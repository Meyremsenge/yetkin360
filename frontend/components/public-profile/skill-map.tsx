import { SealMark } from "@/components/brand/brand-mark";
import type { PublicSkill } from "@/lib/api/public";
import messages from "@/messages/tr.json";
import { cn } from "@/lib/utils";

const t = messages.publicProfile;
const CATEGORY_ORDER = ["LANGUAGE", "FRAMEWORK", "TOOL", "DOMAIN", "SOFT"];
const STRENGTH_DOTS: Record<string, number> = { WEAK: 1, MODERATE: 2, STRONG: 3 };

function StrengthDots({ strength, attested }: { strength: string; attested: boolean }) {
  const filled = STRENGTH_DOTS[strength] ?? 0;
  return (
    <span className="inline-flex items-center gap-[3px]" aria-hidden="true">
      {[1, 2, 3].map((n) => (
        <span
          key={n}
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            n <= filled ? (attested ? "bg-success" : "bg-muted-foreground") : "bg-border"
          )}
        />
      ))}
    </span>
  );
}

function SkillChip({ skill }: { skill: PublicSkill }) {
  const strengthLabel = (t.strength as Record<string, string>)[skill.strength] ?? skill.strength;
  const where = t.inExperiences.replace("{n}", String(skill.experience_count));
  return (
    <li
      title={`${strengthLabel} · ${where}`}
      className={cn(
        "inline-flex h-8 items-center gap-2 rounded-md border px-2.5 text-sm",
        skill.attested
          ? "border-success/30 bg-success/[0.06] font-medium text-foreground"
          : "border-dashed border-border bg-card text-muted-foreground"
      )}
    >
      {skill.attested ? <SealMark className="h-4 w-4 shrink-0" /> : null}
      <span>{skill.name_tr}</span>
      <StrengthDots strength={skill.strength} attested={skill.attested} />
      <span className="sr-only">
        {" — "}
        {skill.attested ? t.attestedLegend : t.evidencedLegend}, {strengthLabel}, {where}
      </span>
    </li>
  );
}

/** Proven skills grouped by category; sealed (attested) and evidence-only chips never look alike. */
export function SkillMap({ skills }: { skills: PublicSkill[] }) {
  const categories = (t.categories as Record<string, string>);
  const groups = CATEGORY_ORDER.map((category) => ({
    category,
    items: skills.filter((s) => s.category === category),
  })).filter((g) => g.items.length > 0);
  const others = skills.filter((s) => !CATEGORY_ORDER.includes(s.category));
  if (others.length) groups.push({ category: "OTHER", items: others });
  const hasEvidenceOnly = skills.some((s) => !s.attested);

  return (
    <div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-muted-foreground" aria-hidden="true">
        <li className="inline-flex items-center gap-1.5">
          <SealMark className="h-3.5 w-3.5" />
          {t.attestedLegend}
        </li>
        {hasEvidenceOnly ? (
          <li className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm border border-dashed border-muted-foreground" />
            {t.evidencedLegend}
          </li>
        ) : null}
      </ul>
      <dl className="mt-5 divide-y divide-border rounded-lg border border-border bg-card">
        {groups.map((group) => (
          <div key={group.category} className="grid gap-3 px-4 py-4 sm:grid-cols-[176px_1fr] sm:items-start md:px-5">
            <dt className="pt-1.5 text-[13px] font-medium text-muted-foreground">
              {categories[group.category] ?? group.category}
            </dt>
            <dd>
              <ul className="flex flex-wrap gap-2">
                {group.items.map((skill) => (
                  <SkillChip key={skill.name_tr} skill={skill} />
                ))}
              </ul>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
