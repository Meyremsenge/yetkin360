"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { SealMark } from "@/components/brand/brand-mark";
import { PAGE_CONTAINER } from "@/components/page-layout";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { listSkills } from "@/lib/api/client";
import {
  DISCOVER_MAX_SKILL_FILTERS,
  DISCOVER_MIN_QUERY_LENGTH,
  listDiscoverOrganizations,
  listDiscoverTalents,
} from "@/lib/api/discover";
import { ApiError } from "@/lib/api/errors";
import { useSession } from "@/lib/session/use-session";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import {
  CardSkeleton,
  EmptyState,
  FOCUS_RING,
  Icon,
  OrganizationCard,
  TalentCard,
  type Facet,
  type IconName,
} from "./discover-ui";

const t = messages.kesfet;

const fieldClass = cn(
  "block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground transition-colors duration-150 placeholder:text-muted-foreground/70 hover:border-muted-foreground/40 focus:border-success",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/25"
);
const outlineButton = cn(
  "inline-flex h-10 items-center justify-center gap-2 rounded-md border border-success px-4 text-sm font-medium text-success transition-colors duration-150 hover:bg-success/10 active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
  FOCUS_RING
);
const SEARCH_DEBOUNCE_MS = 300;
// Cards step in one after another; later pages should not wait behind a long queue.
const STEP_MS = 40;
const MAX_STEPS = 8;
const TABS = ["talents", "organizations"] as const;

// Shareable search: filters live in the address bar under Turkish keys.
const URL_KEYS = { q: "ara", tab: "sekme", skill: "yetkinlik", department: "bolum", city: "sehir" } as const;
const ORGANIZATIONS_TAB_VALUE = "kuruluslar";

type Tab = (typeof TABS)[number];

interface SkillChip {
  id: string;
  name: string;
}

type SkillOption = { id: string; name_tr: string };

/**
 * Debounced copy of `value`. Changing `syncKey` adopts the current value at
 * once — used when filters are restored from the URL, so the first request
 * already carries them.
 */
function useDebounced<T>(value: T, delayMs: number, syncKey = 0): T {
  const [state, setState] = useState({ value, syncKey });
  // Render-phase adjustment (React "storing information from previous renders"):
  // a new syncKey takes the value in this same render, not one effect later.
  if (state.syncKey !== syncKey) setState({ value, syncKey });
  useEffect(() => {
    const timer = setTimeout(
      () => setState((current) => (Object.is(current.value, value) ? current : { ...current, value })),
      delayMs
    );
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return state.syncKey !== syncKey ? value : state.value;
}

/** Search term as the API will use it: shorter than the minimum means "not searching". */
function effectiveQuery(raw: string): string {
  const term = raw.trim();
  return term.length >= DISCOVER_MIN_QUERY_LENGTH ? term : "";
}

function stepStyle(index: number) {
  return { animationDelay: `${Math.min(index, MAX_STEPS) * STEP_MS}ms` };
}

function sameName(a: string, b: string): boolean {
  return a.toLocaleLowerCase("tr") === b.toLocaleLowerCase("tr");
}

/** Skill names come back from the directory without ids; resolve one by exact name. */
async function findSkillByName(name: string): Promise<SkillChip | null> {
  const result = await listSkills(name);
  const match = ((result?.items ?? []) as SkillOption[]).find((option) => sameName(option.name_tr, name));
  return match ? { id: match.id, name: match.name_tr } : null;
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function KesfetPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("talents");
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [city, setCity] = useState("");
  const [skills, setSkills] = useState<SkillChip[]>([]);
  // URL → state happens once after mount; queries wait for it (`ready`).
  const [ready, setReady] = useState(false);
  const [syncKey, setSyncKey] = useState(0);
  const resultsRef = useRef<HTMLDivElement>(null);

  const q = effectiveQuery(useDebounced(search, SEARCH_DEBOUNCE_MS, syncKey));
  const debouncedDepartment = useDebounced(department, SEARCH_DEBOUNCE_MS, syncKey).trim();
  const debouncedCity = useDebounced(city, SEARCH_DEBOUNCE_MS, syncKey).trim();

  // Restore filters from the address bar (a shared or reloaded search).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const skillNames = params.getAll(URL_KEYS.skill).slice(0, DISCOVER_MAX_SKILL_FILTERS);
    let cancelled = false;
    const apply = (resolved: SkillChip[]) => {
      if (cancelled) return;
      setSearch(params.get(URL_KEYS.q) ?? "");
      setDepartment(params.get(URL_KEYS.department) ?? "");
      setCity(params.get(URL_KEYS.city) ?? "");
      setTab(params.get(URL_KEYS.tab) === ORGANIZATIONS_TAB_VALUE ? "organizations" : "talents");
      setSkills(resolved);
      setSyncKey((key) => key + 1);
      setReady(true);
    };
    if (skillNames.length === 0) {
      apply([]);
    } else {
      Promise.all(skillNames.map((name) => findSkillByName(name).catch(() => null))).then((found) =>
        apply(found.filter((skill): skill is SkillChip => skill !== null))
      );
    }
    return () => {
      cancelled = true;
    };
  }, []);

  // State → address bar. replaceState: filtering should not flood browser history.
  useEffect(() => {
    if (!ready) return;
    const params = new URLSearchParams();
    if (q) params.set(URL_KEYS.q, q);
    if (tab === "organizations") params.set(URL_KEYS.tab, ORGANIZATIONS_TAB_VALUE);
    for (const skill of skills) params.append(URL_KEYS.skill, skill.name);
    if (debouncedDepartment) params.set(URL_KEYS.department, debouncedDepartment);
    if (debouncedCity) params.set(URL_KEYS.city, debouncedCity);
    const query = params.toString();
    const next = `${window.location.pathname}${query ? `?${query}` : ""}`;
    if (next !== `${window.location.pathname}${window.location.search}`) {
      window.history.replaceState(window.history.state, "", next);
    }
  }, [ready, q, tab, skills, debouncedDepartment, debouncedCity]);

  const hasTalentFilters = Boolean(q || debouncedDepartment || debouncedCity || skills.length);
  const clearFilters = () => {
    setSearch("");
    setDepartment("");
    setCity("");
    setSkills([]);
  };

  // A filter picked on a card replaces the grid: bring its top back into view.
  const revealResults = () => {
    const el = resultsRef.current;
    if (el && el.getBoundingClientRect().top < 0) {
      el.scrollIntoView?.({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
    }
  };

  const toggleSkillByName = async (name: string) => {
    const existing = skills.find((skill) => sameName(skill.name, name));
    if (existing) {
      setSkills((current) => current.filter((skill) => skill.id !== existing.id));
      revealResults();
      return;
    }
    if (skills.length >= DISCOVER_MAX_SKILL_FILTERS) return;
    const found = await queryClient
      .fetchQuery({ queryKey: ["discover-skill-by-name", name.toLocaleLowerCase("tr")], queryFn: () => findSkillByName(name) })
      .catch(() => null);
    if (!found) return;
    setSkills((current) =>
      current.some((skill) => skill.id === found.id) || current.length >= DISCOVER_MAX_SKILL_FILTERS
        ? current
        : [...current, found]
    );
    revealResults();
  };

  const applyFacet = (facet: Facet, value: string) => {
    if (facet === "department") setDepartment(value);
    else setCity(value);
    revealResults();
  };

  const chips = [
    ...skills.map((skill) => ({
      key: `skill-${skill.id}`,
      label: skill.name,
      remove: () => setSkills((current) => current.filter((other) => other.id !== skill.id)),
    })),
    ...(department.trim()
      ? [{ key: "department", label: `${t.departmentLabel}: ${department.trim()}`, remove: () => setDepartment("") }]
      : []),
    ...(city.trim() ? [{ key: "city", label: `${t.cityLabel}: ${city.trim()}`, remove: () => setCity("") }] : []),
  ];

  return (
    <AppShell>
      <DiscoverHeader tab={tab} onTabChange={setTab} search={search} onSearchChange={setSearch} />

      <div className={cn(PAGE_CONTAINER, "py-8")}>
        {tab === "talents" ? (
          <div
            role="tabpanel"
            id="discover-panel-talents"
            aria-labelledby="discover-tab-talents"
            className="grid gap-6 lg:grid-cols-[264px_minmax(0,1fr)] lg:gap-10"
          >
            <FilterPanel
              department={department}
              city={city}
              skills={skills}
              onDepartmentChange={setDepartment}
              onCityChange={setCity}
              onSkillsChange={setSkills}
              activeCount={chips.length}
              hasFilters={hasTalentFilters}
              onClear={clearFilters}
            />
            <div ref={resultsRef} className="min-w-0 scroll-mt-24">
              <TalentResults
                ready={ready}
                q={q}
                department={debouncedDepartment}
                city={debouncedCity}
                skills={skills}
                hasFilters={hasTalentFilters}
                onClear={clearFilters}
                onSkillClick={(name) => void toggleSkillByName(name)}
                onFacetClick={applyFacet}
                chips={<ActiveFilters chips={chips} hasFilters={hasTalentFilters} onClear={clearFilters} />}
              />
            </div>
          </div>
        ) : (
          <div role="tabpanel" id="discover-panel-organizations" aria-labelledby="discover-tab-organizations">
            <OrganizationResults ready={ready} q={q} onClear={() => setSearch("")} />
          </div>
        )}
      </div>
    </AppShell>
  );
}

/* ── Header: one compact band — title, search, the directory's rules, tabs ── */

const PRINCIPLES: { icon: "globe" | "seal" | "equal"; title: string; body: string }[] = [
  { icon: "globe", title: t.principlePublicTitle, body: t.principlePublicBody },
  { icon: "seal", title: t.principleSealTitle, body: t.principleSealBody },
  { icon: "equal", title: t.principleOrderTitle, body: t.principleOrderBody },
];

function DiscoverHeader({
  tab,
  onTabChange,
  search,
  onSearchChange,
}: {
  tab: Tab;
  onTabChange: (tab: Tab) => void;
  search: string;
  onSearchChange: (value: string) => void;
}) {
  const searchRef = useRef<HTMLInputElement>(null);
  const tabRefs = useRef<Record<Tab, HTMLButtonElement | null>>({ talents: null, organizations: null });
  const tooShort = search.trim().length > 0 && search.trim().length < DISCOVER_MIN_QUERY_LENGTH;

  // "/" jumps to the search box, as in most directories; ignored while typing elsewhere.
  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      event.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = TABS.indexOf(tab);
    let next: Tab | null = null;
    if (event.key === "ArrowRight") next = TABS[(index + 1) % TABS.length];
    if (event.key === "ArrowLeft") next = TABS[(index - 1 + TABS.length) % TABS.length];
    if (event.key === "Home") next = TABS[0];
    if (event.key === "End") next = TABS[TABS.length - 1];
    if (!next) return;
    event.preventDefault();
    onTabChange(next);
    tabRefs.current[next]?.focus();
  };

  return (
    <header className="relative overflow-hidden border-b border-border bg-card">
      <div
        aria-hidden="true"
        className="y360-dot-grid pointer-events-none absolute inset-y-0 right-0 w-1/2 [mask-image:linear-gradient(to_left,black,transparent)]"
      />
      <div className={cn(PAGE_CONTAINER, "relative pt-6 lg:pt-7")}>
        <div className="flex flex-col gap-x-10 gap-y-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <p className="mb-1.5 font-mono text-xs uppercase tracking-[0.12em] text-success">{t.eyebrow}</p>
            <h1 className="font-serif text-[26px] font-semibold leading-tight tracking-tight text-foreground md:text-[30px]">
              {t.heroTitle}
            </h1>
          </div>

          <div className="w-full lg:max-w-[520px]">
            <label htmlFor="discover-search" className="sr-only">
              {tab === "talents" ? t.talentSearchLabel : t.organizationSearchLabel}
            </label>
            <div className="relative">
              <Icon
                name="search"
                className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-muted-foreground"
              />
              <input
                ref={searchRef}
                id="discover-search"
                type="search"
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder={tab === "talents" ? t.talentSearchPlaceholder : t.organizationSearchPlaceholder}
                maxLength={64}
                autoComplete="off"
                aria-describedby={tooShort ? "discover-search-hint" : undefined}
                className={cn(
                  "block h-11 w-full rounded-lg border border-border bg-background pl-11 pr-4 text-[15px] text-foreground transition-colors duration-150 placeholder:text-muted-foreground/70 hover:border-muted-foreground/40 focus:border-success focus:bg-card sm:pr-12",
                  "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-success/20"
                )}
              />
              <kbd
                aria-hidden="true"
                title={t.searchShortcut}
                className="pointer-events-none absolute right-3 top-1/2 hidden h-6 min-w-6 -translate-y-1/2 items-center justify-center rounded border border-border bg-card px-1.5 font-mono text-xs text-muted-foreground sm:flex"
              >
                /
              </kbd>
            </div>
            <p id="discover-search-hint" aria-live="polite" className="text-xs text-warning [&:not(:empty)]:mt-1.5">
              {tooShort ? t.searchTooShort : ""}
            </p>
          </div>
        </div>

        <ul
          aria-label={t.principlesLabel}
          className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground"
        >
          {PRINCIPLES.map((item) => (
            <li key={item.title} title={item.body} className="inline-flex items-center gap-1.5">
              {item.icon === "seal" ? (
                <SealMark className="h-3.5 w-3.5" />
              ) : (
                <Icon name={item.icon} className="h-3.5 w-3.5 text-success" />
              )}
              <span>{item.title}</span>
              <span className="sr-only">— {item.body}</span>
            </li>
          ))}
        </ul>

        <div className="mt-3 flex items-end justify-between gap-4">
          <div role="tablist" aria-label={t.tabsLabel} className="-mx-1 flex gap-1 overflow-x-auto px-1">
            {TABS.map((key) => {
              const selected = tab === key;
              const icon: IconName = key === "talents" ? "user" : "building";
              return (
                <button
                  key={key}
                  ref={(el) => {
                    tabRefs.current[key] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`discover-tab-${key}`}
                  aria-selected={selected}
                  aria-controls={`discover-panel-${key}`}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => onTabChange(key)}
                  onKeyDown={onTabKeyDown}
                  className={cn(
                    "relative inline-flex h-11 shrink-0 items-center gap-2 rounded-t-md px-4 text-sm font-medium transition-colors duration-150",
                    "after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:transition-colors after:duration-200",
                    selected
                      ? "text-foreground after:bg-success"
                      : "text-muted-foreground after:bg-transparent hover:text-foreground hover:after:bg-border",
                    FOCUS_RING
                  )}
                >
                  <Icon name={icon} className={selected ? "text-success" : undefined} />
                  {key === "talents" ? t.tabTalents : t.tabOrganizations}
                </button>
              );
            })}
          </div>
          <ShareSearchButton />
        </div>
      </div>
    </header>
  );
}

/** Copies the current address (filters included) so a search can be handed on. */
function ShareSearchButton() {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 1800);
    return () => clearTimeout(timer);
  }, [state]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setState("copied");
    } catch {
      setState("failed");
    }
  };

  return (
    <div className="mb-1.5 flex shrink-0 items-center gap-2">
      <span aria-live="polite" className={cn("text-xs", state === "failed" ? "text-destructive" : "text-success")}>
        {state === "copied" ? t.shareCopied : state === "failed" ? t.shareFailed : ""}
      </span>
      <button
        type="button"
        onClick={() => void copy()}
        className={cn(
          "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors duration-150 hover:bg-muted",
          FOCUS_RING
        )}
      >
        {state === "copied" ? (
          <svg viewBox="0 0 24 24" aria-hidden="true" className="h-3.5 w-3.5 text-success" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <Icon name="link" className="h-3.5 w-3.5" />
        )}
        <span className="sr-only sm:not-sr-only">{t.shareSearch}</span>
      </button>
    </div>
  );
}

/* ── Talent filters: sticky panel on desktop, collapsible on mobile ── */

function FilterPanel({
  department,
  city,
  skills,
  onDepartmentChange,
  onCityChange,
  onSkillsChange,
  activeCount,
  hasFilters,
  onClear,
}: {
  department: string;
  city: string;
  skills: SkillChip[];
  onDepartmentChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onSkillsChange: (skills: SkillChip[]) => void;
  activeCount: number;
  hasFilters: boolean;
  onClear: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="lg:sticky lg:top-24 lg:self-start">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="discover-filters"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex h-11 w-full items-center justify-between rounded-lg border border-border bg-card px-4 text-sm font-medium text-foreground lg:hidden",
          FOCUS_RING
        )}
      >
        <span className="inline-flex items-center gap-2">
          <Icon name="filter" />
          {t.filtersToggle}
          {activeCount > 0 ? (
            <span className="rounded-full bg-success/10 px-2 py-0.5 text-xs text-success">
              {t.filtersActiveCount.replace("{count}", String(activeCount))}
            </span>
          ) : null}
        </span>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-4 w-4 text-muted-foreground transition-transform duration-150", open && "rotate-180")}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      <section
        id="discover-filters"
        aria-label={t.filtersLabel}
        className={cn("mt-3 rounded-lg border border-border bg-card p-5 lg:mt-0 lg:block", open ? "block" : "hidden")}
      >
        <div className="mb-5 flex items-baseline justify-between gap-3">
          <h2 className="font-serif text-lg font-semibold text-foreground">{t.filtersTitle}</h2>
          {hasFilters && (
            <button
              type="button"
              onClick={onClear}
              className={cn("rounded-sm text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline", FOCUS_RING)}
            >
              {t.clearFilters}
            </button>
          )}
        </div>

        <div className="space-y-5">
          <SkillFilter selected={skills} onChange={onSkillsChange} />
          <FieldWithIcon
            id="discover-department"
            icon="cap"
            label={t.departmentLabel}
            value={department}
            placeholder={t.departmentPlaceholder}
            onChange={onDepartmentChange}
          />
          <FieldWithIcon
            id="discover-city"
            icon="pin"
            label={t.cityLabel}
            value={city}
            placeholder={t.cityPlaceholder}
            onChange={onCityChange}
          />
        </div>

        <p className="mt-5 flex gap-2 border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
          <SealMark className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {t.filtersNote}
        </p>
      </section>
    </div>
  );
}

function FieldWithIcon({
  id,
  icon,
  label,
  value,
  placeholder,
  onChange,
}: {
  id: string;
  icon: IconName;
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <Icon
          name={icon}
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        />
        <input
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          maxLength={100}
          autoComplete="off"
          className={cn(fieldClass, "pl-9")}
        />
      </div>
    </div>
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
  const options = ((data?.items ?? []) as SkillOption[])
    .filter((option) => !selected.some((skill) => skill.id === option.id))
    .slice(0, 8);
  const showOptions = Boolean(term.trim() && debouncedTerm && !full && options.length > 0);

  const pick = (option: SkillOption) => {
    onChange([...selected, { id: option.id, name: option.name_tr }]);
    setTerm("");
  };

  return (
    <div>
      <label htmlFor="discover-skill" className="mb-1.5 block text-xs font-medium text-foreground">
        {t.skillLabel}
      </label>
      <div className="relative">
        <SealMark className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
        <input
          id="discover-skill"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setTerm("");
            if (e.key === "Enter" && showOptions) {
              e.preventDefault();
              pick(options[0]);
            }
          }}
          placeholder={full ? t.skillLimitReached : t.skillPlaceholder}
          disabled={full}
          autoComplete="off"
          aria-describedby="discover-skill-hint"
          className={cn(fieldClass, "pl-9 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70")}
        />
        {showOptions && (
          <ul
            aria-label={t.skillOptionsLabel}
            className="y360-step-in absolute inset-x-0 top-full z-20 mt-1 max-h-64 overflow-auto rounded-lg border border-border bg-card p-1 shadow-[0_8px_24px_-12px_rgba(34,31,27,0.25)]"
          >
            {options.map((option) => (
              <li key={option.id}>
                <button
                  type="button"
                  onClick={() => pick(option)}
                  className={cn(
                    "flex h-9 w-full items-center gap-2 rounded-md px-3 text-left text-sm text-foreground hover:bg-muted",
                    FOCUS_RING
                  )}
                >
                  <span className="font-mono text-success">+</span> {option.name_tr}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p id="discover-skill-hint" className="mt-1.5 text-xs text-muted-foreground">
        {t.skillHint}
      </p>
    </div>
  );
}

function ActiveFilters({
  chips,
  hasFilters,
  onClear,
}: {
  chips: { key: string; label: string; remove: () => void }[];
  hasFilters: boolean;
  onClear: () => void;
}) {
  if (chips.length === 0) return null;
  return (
    <ul aria-label={t.activeFiltersLabel} className="mb-5 flex flex-wrap items-center gap-2">
      {chips.map((chip) => (
        <li key={chip.key} className="y360-step-in">
          <button
            type="button"
            onClick={chip.remove}
            aria-label={t.removeFilter.replace("{filter}", chip.label)}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-full border border-foreground/15 bg-card pl-3 pr-2 text-xs font-medium text-foreground transition-colors duration-150 hover:border-destructive/40 hover:text-destructive",
              FOCUS_RING
            )}
          >
            {chip.label}
            <Icon name="x" className="h-3.5 w-3.5" />
          </button>
        </li>
      ))}
      {hasFilters && (
        <li>
          <button
            type="button"
            onClick={onClear}
            className={cn("rounded-sm px-1 text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground", FOCUS_RING)}
          >
            {t.clearFilters}
          </button>
        </li>
      )}
    </ul>
  );
}

/* ── Results ── */

/** "{n} profil" / "{n}+ profil" while more pages remain (no total from the API). */
function resultCount(template: string, loaded: number, more: boolean): string {
  return template.replace("{count}", more ? t.resultCountMore.replace("{count}", String(loaded)) : String(loaded));
}

function ResultsHeading({ title, count, sort }: { title: string; count: string | null; sort: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border pb-3">
      <p className="flex items-baseline gap-3" aria-live="polite">
        <span className="font-serif text-xl font-semibold text-foreground">{title}</span>
        {count !== null ? (
          <span className="font-mono text-xs tabular-nums text-muted-foreground">{count}</span>
        ) : null}
      </p>
      <p className="font-mono text-[11px] text-muted-foreground">{sort}</p>
    </div>
  );
}

function TalentResults({
  ready,
  q,
  department,
  city,
  skills,
  hasFilters,
  onClear,
  onSkillClick,
  onFacetClick,
  chips,
}: {
  ready: boolean;
  q: string;
  department: string;
  city: string;
  skills: SkillChip[];
  hasFilters: boolean;
  onClear: () => void;
  onSkillClick: (name: string) => void;
  onFacetClick: (facet: Facet, value: string) => void;
  chips: ReactNode;
}) {
  const session = useSession();
  const isStudent = Boolean(session.data?.talent_profile);
  const skillIds = skills.map((skill) => skill.id);
  const query = useInfiniteQuery({
    queryKey: ["discover-talents", q, department, city, skillIds],
    queryFn: ({ pageParam }) => listDiscoverTalents({ q, department, city, skillIds, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    retry: false,
    enabled: ready,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const selectedNames = skills.map((skill) => skill.name);

  return (
    <>
      <ResultsHeading
        title={t.tabTalents}
        count={query.isSuccess ? resultCount(t.talentResultCount, items.length, query.hasNextPage) : null}
        sort={t.talentSort}
      />
      {chips}
      <ResultList
        query={query}
        ready={ready}
        isEmpty={items.length === 0}
        variant="talent"
        loadingLabel={t.talentsLoading}
        errorMessage={t.talentsError}
        empty={
          <EmptyState
            icon={hasFilters ? "search" : "compass"}
            title={hasFilters ? t.talentsEmptyFilteredTitle : t.talentsEmptyTitle}
            body={hasFilters ? t.talentsEmptyFilteredBody : t.talentsEmptyBody}
          >
            {hasFilters ? (
              <Button variant="secondary" size="sm" onClick={onClear}>
                {t.clearFilters}
              </Button>
            ) : isStudent ? (
              <>
                <span className="text-sm text-muted-foreground">{t.emptyStudentHint}</span>
                <Link href="/profil" className={cn(outlineButton, "h-8 px-3")}>
                  {t.emptyStudentAction}
                </Link>
              </>
            ) : null}
          </EmptyState>
        }
      >
        {!hasFilters ? <p className="-mt-1 mb-4 text-xs text-muted-foreground">{t.cardFilterHint}</p> : null}
        <ul className="grid gap-5 sm:grid-cols-2">
          {items.map((talent, index) => (
            <li key={talent.public_slug} className="y360-step-in" style={stepStyle(index)}>
              <TalentCard
                talent={talent}
                selectedSkills={selectedNames}
                onSkillClick={onSkillClick}
                onFacetClick={onFacetClick}
              />
            </li>
          ))}
        </ul>
      </ResultList>
    </>
  );
}

function OrganizationResults({ ready, q, onClear }: { ready: boolean; q: string; onClear: () => void }) {
  const session = useSession();
  const canStartEngagement = Boolean(session.data?.talent_profile);

  const query = useInfiniteQuery({
    queryKey: ["discover-organizations", q],
    queryFn: ({ pageParam }) => listDiscoverOrganizations({ q, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    retry: false,
    enabled: ready,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <>
      <ResultsHeading
        title={t.tabOrganizations}
        count={query.isSuccess ? resultCount(t.organizationResultCount, items.length, query.hasNextPage) : null}
        sort={t.organizationSort}
      />
      <ResultList
        query={query}
        ready={ready}
        isEmpty={items.length === 0}
        variant="organization"
        loadingLabel={t.organizationsLoading}
        errorMessage={t.organizationsError}
        empty={
          <EmptyState
            icon={q ? "search" : "building"}
            title={q ? t.organizationsEmptyFilteredTitle : t.organizationsEmptyTitle}
            body={q ? t.organizationsEmptyFilteredBody : t.organizationsEmptyBody}
          >
            {q ? (
              <Button variant="secondary" size="sm" onClick={onClear}>
                {t.clearFilters}
              </Button>
            ) : null}
          </EmptyState>
        }
      >
        <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((organization, index) => (
            <li key={organization.id} className="y360-step-in" style={stepStyle(index)}>
              <OrganizationCard organization={organization} canStartEngagement={canStartEngagement} />
            </li>
          ))}
        </ul>
      </ResultList>
    </>
  );
}

/** Loading / error / rate-limit / empty / "load more" frame shared by both tabs. */
function ResultList({
  query,
  ready,
  isEmpty,
  variant,
  loadingLabel,
  errorMessage,
  empty,
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
  ready: boolean;
  isEmpty: boolean;
  variant: "talent" | "organization";
  loadingLabel: string;
  errorMessage: string;
  empty: ReactNode;
  children: ReactNode;
}) {
  if (!ready || query.isLoading) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label={loadingLabel}
        className={cn("grid gap-5 sm:grid-cols-2", variant === "organization" && "lg:grid-cols-3")}
      >
        {[0, 1, 2, 3].concat(variant === "organization" ? [4, 5] : []).map((n) => (
          <CardSkeleton key={n} variant={variant} />
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

  if (isEmpty) return <>{empty}</>;

  return (
    <>
      {children}
      {query.hasNextPage && (
        <div className="mt-8 flex justify-center">
          <button
            type="button"
            className={outlineButton}
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? t.loadingMore : t.loadMore}
          </button>
        </div>
      )}
    </>
  );
}
