"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listSkills } from "@/lib/api/client";
import {
  DISCOVER_MAX_SKILL_FILTERS,
  DISCOVER_MIN_QUERY_LENGTH,
  listDiscoverOrganizations,
  listDiscoverTalents,
  type DiscoverOrganization,
  type DiscoverTalent,
} from "@/lib/api/discover";
import { ApiError } from "@/lib/api/errors";
import { useSession } from "@/lib/session/use-session";
import messages from "@/messages/tr.json";

const t = messages.kesfet;

const pulse = "animate-pulse rounded-lg bg-muted motion-reduce:animate-none";
const focusRing = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";
const fieldClass = `block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground ${focusRing}`;
const SEARCH_DEBOUNCE_MS = 300;
// Cards step in one after another; later pages should not wait behind a long queue.
const STEP_MS = 40;
const MAX_STEPS = 8;

type Tab = "talents" | "organizations";

interface SkillChip {
  id: string;
  name: string;
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/** Search term as the API will use it: shorter than the minimum means "not searching". */
function effectiveQuery(raw: string): string {
  const term = raw.trim();
  return term.length >= DISCOVER_MIN_QUERY_LENGTH ? term : "";
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toLocaleUpperCase("tr");
}

function stepStyle(index: number) {
  return { animationDelay: `${Math.min(index, MAX_STEPS) * STEP_MS}ms` };
}

export default function KesfetPage() {
  const [tab, setTab] = useState<Tab>("talents");
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [city, setCity] = useState("");
  const [skills, setSkills] = useState<SkillChip[]>([]);

  const q = effectiveQuery(useDebounced(search, SEARCH_DEBOUNCE_MS));
  const debouncedDepartment = useDebounced(department, SEARCH_DEBOUNCE_MS).trim();
  const debouncedCity = useDebounced(city, SEARCH_DEBOUNCE_MS).trim();

  const hasTalentFilters = Boolean(q || debouncedDepartment || debouncedCity || skills.length);
  const clearFilters = () => {
    setSearch("");
    setDepartment("");
    setCity("");
    setSkills([]);
  };

  return (
    <AppShell>
      <div className="max-w-[1120px] px-4 py-8 md:px-6 lg:px-10">
        <h1 className="font-serif text-[32px] font-semibold leading-10 text-foreground">{t.title}</h1>
        <p className="mt-2 max-w-[640px] text-sm text-muted-foreground">{t.description}</p>

        <div className="mt-6">
          <label htmlFor="discover-search" className="sr-only">
            {tab === "talents" ? t.talentSearchLabel : t.organizationSearchLabel}
          </label>
          <input
            id="discover-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={tab === "talents" ? t.talentSearchPlaceholder : t.organizationSearchPlaceholder}
            maxLength={64}
            className={fieldClass}
          />
        </div>

        <div role="tablist" aria-label={t.tabsLabel} className="mt-6 flex gap-1 border-b border-border">
          {(["talents", "organizations"] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              id={`discover-tab-${key}`}
              aria-selected={tab === key}
              aria-controls={`discover-panel-${key}`}
              onClick={() => setTab(key)}
              className={`-mb-px rounded-t-md border-b-2 px-4 py-2 text-sm font-medium ${focusRing} ${
                tab === key
                  ? "border-success text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {key === "talents" ? t.tabTalents : t.tabOrganizations}
            </button>
          ))}
        </div>

        {tab === "talents" ? (
          <div role="tabpanel" id="discover-panel-talents" aria-labelledby="discover-tab-talents" className="mt-6">
            <TalentFilters
              department={department}
              city={city}
              skills={skills}
              onDepartmentChange={setDepartment}
              onCityChange={setCity}
              onSkillsChange={setSkills}
              hasFilters={hasTalentFilters}
              onClear={clearFilters}
            />
            <TalentResults
              q={q}
              department={debouncedDepartment}
              city={debouncedCity}
              skillIds={skills.map((skill) => skill.id)}
              hasFilters={hasTalentFilters}
              onClear={clearFilters}
            />
          </div>
        ) : (
          <div
            role="tabpanel"
            id="discover-panel-organizations"
            aria-labelledby="discover-tab-organizations"
            className="mt-6"
          >
            <OrganizationResults q={q} onClear={() => setSearch("")} />
          </div>
        )}
      </div>
    </AppShell>
  );
}

function TalentFilters({
  department,
  city,
  skills,
  onDepartmentChange,
  onCityChange,
  onSkillsChange,
  hasFilters,
  onClear,
}: {
  department: string;
  city: string;
  skills: SkillChip[];
  onDepartmentChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onSkillsChange: (skills: SkillChip[]) => void;
  hasFilters: boolean;
  onClear: () => void;
}) {
  const chips = [
    ...skills.map((skill) => ({
      key: `skill-${skill.id}`,
      label: skill.name,
      remove: () => onSkillsChange(skills.filter((other) => other.id !== skill.id)),
    })),
    ...(department.trim()
      ? [{ key: "department", label: `${t.departmentLabel}: ${department.trim()}`, remove: () => onDepartmentChange("") }]
      : []),
    ...(city.trim() ? [{ key: "city", label: `${t.cityLabel}: ${city.trim()}`, remove: () => onCityChange("") }] : []),
  ];

  return (
    <section aria-label={t.filtersLabel} className="mb-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <SkillFilter selected={skills} onChange={onSkillsChange} />
        <div>
          <label htmlFor="discover-department" className="mb-1 block text-xs font-medium text-muted-foreground">
            {t.departmentLabel}
          </label>
          <input
            id="discover-department"
            value={department}
            onChange={(e) => onDepartmentChange(e.target.value)}
            placeholder={t.departmentPlaceholder}
            maxLength={100}
            className={fieldClass}
          />
        </div>
        <div>
          <label htmlFor="discover-city" className="mb-1 block text-xs font-medium text-muted-foreground">
            {t.cityLabel}
          </label>
          <input
            id="discover-city"
            value={city}
            onChange={(e) => onCityChange(e.target.value)}
            placeholder={t.cityPlaceholder}
            maxLength={100}
            className={fieldClass}
          />
        </div>
      </div>

      {chips.length > 0 && (
        <ul aria-label={t.activeFiltersLabel} className="mt-3 flex flex-wrap items-center gap-2">
          {chips.map((chip) => (
            <li key={chip.key}>
              <button
                type="button"
                onClick={chip.remove}
                aria-label={t.removeFilter.replace("{filter}", chip.label)}
                className={`inline-flex items-center gap-1 rounded-full border border-border bg-card px-3 py-1 text-xs text-foreground hover:border-muted-foreground/50 ${focusRing}`}
              >
                {chip.label}
                <span aria-hidden="true">×</span>
              </button>
            </li>
          ))}
          {hasFilters && (
            <li>
              <button
                type="button"
                onClick={onClear}
                className={`rounded-sm text-xs text-muted-foreground underline hover:text-foreground ${focusRing}`}
              >
                {t.clearFilters}
              </button>
            </li>
          )}
        </ul>
      )}
    </section>
  );
}

function SkillFilter({ selected, onChange }: { selected: SkillChip[]; onChange: (skills: SkillChip[]) => void }) {
  const [term, setTerm] = useState("");
  const debouncedTerm = useDebounced(term, SEARCH_DEBOUNCE_MS).trim();
  const full = selected.length >= DISCOVER_MAX_SKILL_FILTERS;

  const { data } = useQuery({
    queryKey: ["discover-skill-options", debouncedTerm],
    queryFn: () => listSkills(debouncedTerm),
    enabled: debouncedTerm.length > 0 && !full,
  });
  const options = ((data?.items ?? []) as { id: string; name_tr: string }[]).filter(
    (option) => !selected.some((skill) => skill.id === option.id)
  );

  return (
    <div>
      <label htmlFor="discover-skill" className="mb-1 block text-xs font-medium text-muted-foreground">
        {t.skillLabel}
      </label>
      <input
        id="discover-skill"
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        placeholder={full ? t.skillLimitReached : t.skillPlaceholder}
        disabled={full}
        aria-describedby="discover-skill-hint"
        className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-60`}
      />
      <p id="discover-skill-hint" className="mt-1 text-xs text-muted-foreground">
        {t.skillHint}
      </p>
      {debouncedTerm && !full && options.length > 0 && (
        <ul aria-label={t.skillOptionsLabel} className="mt-2 flex flex-wrap gap-2">
          {options.slice(0, 8).map((option) => (
            <li key={option.id}>
              <button
                type="button"
                onClick={() => {
                  onChange([...selected, { id: option.id, name: option.name_tr }]);
                  setTerm("");
                }}
                className={`rounded-full border border-border bg-muted px-3 py-1 text-xs text-foreground hover:border-muted-foreground/50 ${focusRing}`}
              >
                + {option.name_tr}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TalentResults({
  q,
  department,
  city,
  skillIds,
  hasFilters,
  onClear,
}: {
  q: string;
  department: string;
  city: string;
  skillIds: string[];
  hasFilters: boolean;
  onClear: () => void;
}) {
  const query = useInfiniteQuery({
    queryKey: ["discover-talents", q, department, city, skillIds],
    queryFn: ({ pageParam }) => listDiscoverTalents({ q, department, city, skillIds, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    retry: false,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <ResultList
      query={query}
      isEmpty={items.length === 0}
      loadingLabel={t.talentsLoading}
      errorMessage={t.talentsError}
      emptyTitle={hasFilters ? t.talentsEmptyFilteredTitle : t.talentsEmptyTitle}
      emptyBody={hasFilters ? t.talentsEmptyFilteredBody : t.talentsEmptyBody}
      onClear={hasFilters ? onClear : undefined}
    >
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((talent, index) => (
          <li key={talent.public_slug} className="y360-step-in" style={stepStyle(index)}>
            <TalentCard talent={talent} />
          </li>
        ))}
      </ul>
    </ResultList>
  );
}

function TalentCard({ talent }: { talent: DiscoverTalent }) {
  const meta = [talent.institution_name, talent.department, talent.city].filter(Boolean).join(" · ");
  return (
    <article className="flex h-full flex-col rounded-lg border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-sand font-serif text-sm font-semibold text-foreground"
        >
          {initials(talent.full_name)}
        </span>
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-foreground">{talent.full_name}</h2>
          {talent.headline ? <p className="text-sm text-foreground">{talent.headline}</p> : null}
          {meta ? <p className="mt-0.5 text-xs text-muted-foreground">{meta}</p> : null}
        </div>
      </div>

      {talent.sealed_skills.length > 0 ? (
        <ul aria-label={t.sealedSkillsLabel} className="mt-4 flex flex-wrap gap-1.5">
          {talent.sealed_skills.map((skill) => (
            <li key={skill}>
              <Badge variant="success" className="gap-1">
                <SealIcon />
                {skill}
              </Badge>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-xs text-muted-foreground">{t.noSealedSkills}</p>
      )}

      <div className="mt-auto flex items-center justify-between gap-3 pt-4">
        <span className="text-xs text-muted-foreground">
          {t.verifiedExperienceCount.replace("{count}", String(talent.verified_experience_count))}
        </span>
        <Link
          href={`/p/${encodeURIComponent(talent.public_slug)}`}
          aria-label={t.viewProfileOf.replace("{name}", talent.full_name)}
          className={`rounded-sm text-sm font-medium text-success underline-offset-4 hover:underline ${focusRing}`}
        >
          {t.viewProfile}
        </Link>
      </div>
    </article>
  );
}

function SealIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function OrganizationResults({ q, onClear }: { q: string; onClear: () => void }) {
  const session = useSession();
  const canStartEngagement = Boolean(session.data?.talent_profile);

  const query = useInfiniteQuery({
    queryKey: ["discover-organizations", q],
    queryFn: ({ pageParam }) => listDiscoverOrganizations({ q, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    retry: false,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <ResultList
      query={query}
      isEmpty={items.length === 0}
      loadingLabel={t.organizationsLoading}
      errorMessage={t.organizationsError}
      emptyTitle={q ? t.organizationsEmptyFilteredTitle : t.organizationsEmptyTitle}
      emptyBody={q ? t.organizationsEmptyFilteredBody : t.organizationsEmptyBody}
      onClear={q ? onClear : undefined}
    >
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((organization, index) => (
          <li key={organization.id} className="y360-step-in" style={stepStyle(index)}>
            <OrganizationCard organization={organization} canStartEngagement={canStartEngagement} />
          </li>
        ))}
      </ul>
    </ResultList>
  );
}

function OrganizationCard({
  organization,
  canStartEngagement,
}: {
  organization: DiscoverOrganization;
  canStartEngagement: boolean;
}) {
  const levels = messages.kurulusSec.verificationLevel;
  return (
    <article className="flex h-full flex-col rounded-lg border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-sand font-serif text-sm font-semibold text-foreground"
        >
          {initials(organization.name)}
        </span>
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-foreground">{organization.name}</h2>
          {organization.domain ? <p className="text-xs text-muted-foreground">{organization.domain}</p> : null}
        </div>
      </div>
      <div className="mt-auto flex items-center justify-between gap-3 pt-4">
        <span className="text-xs text-muted-foreground">
          {levels[organization.verification_level as keyof typeof levels] ?? organization.verification_level}
        </span>
        {canStartEngagement && (
          <Link
            href={`/calismalar/olustur?organization_id=${encodeURIComponent(organization.id)}`}
            aria-label={t.startEngagementWith.replace("{name}", organization.name)}
            className={`rounded-sm text-sm font-medium text-success underline-offset-4 hover:underline ${focusRing}`}
          >
            {t.startEngagement}
          </Link>
        )}
      </div>
    </article>
  );
}

/** Loading / error / rate-limit / empty / "load more" frame shared by both tabs. */
function ResultList({
  query,
  isEmpty,
  loadingLabel,
  errorMessage,
  emptyTitle,
  emptyBody,
  onClear,
  children,
}: {
  query: {
    isLoading: boolean;
    isError: boolean;
    error: unknown;
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    refetch: () => unknown;
    fetchNextPage: () => unknown;
  };
  isEmpty: boolean;
  loadingLabel: string;
  errorMessage: string;
  emptyTitle: string;
  emptyBody: string;
  onClear?: () => void;
  children: React.ReactNode;
}) {
  if (query.isLoading) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label={loadingLabel}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        {[0, 1, 2, 3, 4, 5].map((n) => (
          <div key={n} aria-hidden="true" className={`h-40 w-full ${pulse}`} />
        ))}
      </div>
    );
  }

  if (query.isError) {
    const rateLimited = query.error instanceof ApiError && query.error.status === 429;
    return (
      <Alert variant="error" className="flex items-center justify-between gap-4">
        <span>{rateLimited ? t.rateLimited : errorMessage}</span>
        <Button variant="secondary" size="sm" onClick={() => void query.refetch()}>
          {t.retry}
        </Button>
      </Alert>
    );
  }

  if (isEmpty) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card px-6 py-10 text-center">
        <p className="font-medium text-foreground">{emptyTitle}</p>
        <p className="mx-auto mt-1 max-w-[440px] text-sm text-muted-foreground">{emptyBody}</p>
        {onClear && (
          <Button variant="secondary" size="sm" className="mt-4" onClick={onClear}>
            {t.clearFilters}
          </Button>
        )}
      </div>
    );
  }

  return (
    <>
      {children}
      {query.hasNextPage && (
        <div className="mt-6 flex justify-center">
          <Button
            variant="secondary"
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? t.loadingMore : t.loadMore}
          </Button>
        </div>
      )}
    </>
  );
}
