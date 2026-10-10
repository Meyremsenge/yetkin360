"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listEngagements, type EngagementSummary } from "@/lib/api/engagements";
import { useSession } from "@/lib/session/use-session";
import { cn } from "@/lib/utils";
import { STATUS_TONE } from "@/lib/ui/engagement-chain";
import type { ReviewerScope } from "@/lib/ui/engagement-review";
import messages from "@/messages/tr.json";
import {
  ArrowIcon,
  CHIP_TONE,
  DOT_CLASS,
  KindIcon,
  MiniChain,
  SealMark,
  TILE_ICON,
  TileIcon,
  TimeAgo,
  type TileTone,
} from "./list-parts";
import { ReviewView } from "./review-view";

type FilterKey = keyof typeof messages.calismalar.filterTabs;

const FILTER_KEYS: FilterKey[] = ["all", "ongoing", "evaluation", "verified", "closed"];

const FILTER_STATUSES: Record<Exclude<FilterKey, "all">, string[]> = {
  ongoing: ["DRAFT", "PENDING_APPROVAL", "ACTIVE"],
  evaluation: ["PENDING_EVALUATION", "EVALUATED"],
  verified: ["VERIFIED", "RESOLVED"],
  closed: ["REJECTED", "CANCELLED", "DISPUTED"],
};

const SUMMARY: {
  key: keyof typeof messages.calismalar.summary;
  filterKey: FilterKey;
  tone: TileTone;
  icon: string;
}[] = [
  { key: "total", filterKey: "all", tone: "ink", icon: TILE_ICON.briefcase },
  { key: "ongoing", filterKey: "ongoing", tone: "ochre", icon: TILE_ICON.clock },
  { key: "verified", filterKey: "verified", tone: "pine", icon: TILE_ICON.check },
];

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function SkeletonCards() {
  return (
    <div role="status" className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <span className="sr-only">{messages.calismalar.loadingLabel}</span>
      {[0, 1, 2, 3].map((n) => (
        <div
          key={n}
          aria-hidden="true"
          className="space-y-4 rounded-lg border border-border bg-card p-5"
        >
          <div className="flex justify-between">
            <div className="h-3 w-16 animate-pulse rounded-md bg-muted" />
            <div className="h-5 w-20 animate-pulse rounded-full bg-muted" />
          </div>
          <div className="h-6 w-3/4 animate-pulse rounded-md bg-muted" />
          <div className="h-4 w-1/2 animate-pulse rounded-md bg-muted" />
          <div className="h-3 w-24 animate-pulse rounded-md bg-muted" />
        </div>
      ))}
    </div>
  );
}

function BriefcaseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-8 w-8 text-muted-foreground"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 13h18" />
    </svg>
  );
}

function idsOf(refs: unknown[] | undefined): string[] {
  return (refs ?? [])
    .map((ref) => (typeof ref === "object" && ref !== null ? (ref as { id?: unknown }).id : undefined))
    .filter((id): id is string => typeof id === "string");
}

type ViewKey = "own" | "review";

const VIEW_KEYS: ViewKey[] = ["own", "review"];

const VIEW_LABEL: Record<ViewKey, string> = {
  own: messages.calismalar.review.viewOwn,
  review: messages.calismalar.review.viewReview,
};

/** The student's own engagements: counts, status tabs and one card per engagement. */
function StudentView({ items }: { items: EngagementSummary[] }) {
  const [filter, setFilter] = useState<FilterKey>("all");

  function countFor(key: FilterKey): number {
    return key === "all"
      ? items.length
      : items.filter((item) => FILTER_STATUSES[key].includes(item.status)).length;
  }

  if (items.length === 0) {
    return (
      <section className="rounded-xl border border-border bg-card p-6">
        <BriefcaseIcon />
        <p className="mt-4 text-base font-semibold text-foreground">{messages.calismalar.emptyMessage}</p>
        <p className="mt-1 max-w-[640px] text-sm text-muted-foreground">{messages.calismalar.emptyHint}</p>
      </section>
    );
  }

  const visibleItems =
    filter === "all" ? items : items.filter((item) => FILTER_STATUSES[filter].includes(item.status));

  return (
    <>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {SUMMARY.map(({ key, filterKey, tone, icon }) => (
          <div key={key} className="flex items-center gap-4 rounded-xl border border-border bg-card px-5 py-4">
            <TileIcon path={icon} tone={tone} />
            <div>
              <dt className="text-xs text-muted-foreground">{messages.calismalar.summary[key]}</dt>
              <dd className="font-serif text-[28px] font-semibold leading-tight tabular-nums text-foreground">
                {countFor(filterKey)}
              </dd>
            </div>
          </div>
        ))}
      </dl>

      <div
        role="tablist"
        aria-label={messages.calismalar.filterTabsLabel}
        className="mt-8 flex gap-1 overflow-x-auto overflow-y-hidden rounded-lg border border-border bg-muted/60 p-1 [scrollbar-width:none] sm:inline-flex [&::-webkit-scrollbar]:hidden"
      >
        {FILTER_KEYS.map((key) => {
          const selected = filter === key;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => setFilter(key)}
              className={cn(
                "flex h-9 shrink-0 items-center gap-2 rounded-md px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
                selected
                  ? "bg-card text-foreground shadow-[0_1px_3px_rgba(34,31,27,0.12)]"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {messages.calismalar.filterTabs[key]}
              <span
                className={cn(
                  "min-w-[20px] rounded-full px-1.5 text-center font-mono text-[11px] tabular-nums",
                  selected ? "bg-success/10 text-success" : "bg-background/70 text-muted-foreground"
                )}
              >
                {countFor(key)}
              </span>
            </button>
          );
        })}
      </div>

      <div role="tabpanel" className="mt-6">
        {visibleItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">{messages.calismalar.filterEmpty}</p>
        ) : (
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visibleItems.map((item) => {
              const variant = STATUS_TONE[item.status] ?? "default";
              const isVerified = item.status === "VERIFIED" || item.status === "RESOLVED";
              return (
                <li key={item.id}>
                  <Link
                    href={`/calismalar/${item.id}`}
                    className={cn(
                      "group relative flex h-full flex-col gap-4 overflow-hidden rounded-xl border bg-card p-5 transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-28px_rgba(34,31,27,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success motion-reduce:transition-none motion-reduce:hover:translate-y-0",
                      isVerified ? "border-success/30 hover:border-success/60" : "border-border hover:border-muted-foreground/40"
                    )}
                  >
                    {isVerified ? (
                      <span aria-hidden="true" className="absolute inset-x-0 top-0 h-1 bg-success" />
                    ) : null}
                    <div className="flex items-start justify-between gap-3">
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-sand text-foreground">
                        <KindIcon kind={item.kind} />
                      </span>
                      <Badge variant={variant} className="gap-1.5">
                        <span aria-hidden="true" className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASS[variant])} />
                        {messages.calismalar.status[item.status]}
                      </Badge>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start gap-2">
                        <h2 className="line-clamp-2 font-serif text-xl font-medium leading-7 text-foreground">
                          {item.title}
                        </h2>
                        {isVerified ? <SealMark /> : null}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {messages.calismalar.kind[item.kind]} · {item.organization_name}
                      </p>
                      <p
                        className={cn(
                          "mt-4 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] font-medium",
                          CHIP_TONE[variant]
                        )}
                      >
                        <ArrowIcon />
                        {messages.calismalar.nextStep[item.status as keyof typeof messages.calismalar.nextStep]}
                      </p>
                    </div>
                    <div className="flex items-center justify-between gap-2 border-t border-border pt-4">
                      <MiniChain status={item.status} />
                      <TimeAgo iso={item.updated_at} />
                    </div>
                  </Link>
                </li>
              );
            })}
            {filter === "all" ? (
              <li>
                <Link
                  href="/calismalar/kurulus-sec"
                  className="group flex h-full min-h-[180px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-muted-foreground/30 p-5 text-center transition-colors hover:border-success hover:bg-success/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-sand text-success transition-colors group-hover:bg-success group-hover:text-background">
                    <PlusIcon />
                  </span>
                  <span className="font-serif text-lg font-semibold text-foreground">
                    {messages.calismalar.newCardTitle}
                  </span>
                  <span className="max-w-[260px] text-sm text-muted-foreground">
                    {messages.calismalar.newCardHint}
                  </span>
                </Link>
              </li>
            ) : null}
          </ul>
        )}
      </div>
    </>
  );
}

export default function CalismalarPage() {
  const session = useSession();
  const [view, setView] = useState<ViewKey>("own");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["engagements"],
    queryFn: listEngagements,
  });

  const me = session.data;
  const scope = useMemo<ReviewerScope>(
    () => ({
      organizationIds: new Set(idsOf(me?.organizations)),
      institutionIds: new Set(idsOf(me?.institutions)),
    }),
    [me],
  );

  // Organization members and institution coordinators review student
  // engagements; a student sees their own. Someone who is both can switch.
  const isReviewer = scope.organizationIds.size + scope.institutionIds.size > 0;
  const talentId = me?.talent_profile?.id;
  const canSwitch = isReviewer && Boolean(me?.talent_profile);
  const mode: ViewKey = !isReviewer ? "own" : canSwitch ? view : "review";

  const items = data?.items ?? [];
  const ownItems = canSwitch ? items.filter((item) => item.talent_id === talentId) : items;

  return (
    <AppShell>
      {mode === "review" ? (
        <PageHeader
          eyebrow={messages.shell.groupWork}
          title={messages.calismalar.review.title}
          description={messages.calismalar.review.description}
        />
      ) : (
        <PageHeader
          eyebrow={messages.shell.groupWork}
          title={messages.calismalar.listTitle}
          description={messages.calismalar.pageDescription}
          actions={
            <Link
              href="/calismalar/kurulus-sec"
              className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-md bg-success px-5 text-sm font-medium text-background shadow-[0_8px_20px_-12px_rgba(38,84,69,0.8)] transition-colors hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
            >
              <PlusIcon />
              {messages.calismalar.newEngagementButton}
            </Link>
          }
        />
      )}

      <PageBody>
        {canSwitch ? (
          <div
            role="group"
            aria-label={messages.calismalar.review.viewSwitchLabel}
            className="mb-6 inline-flex gap-1 rounded-lg border border-border bg-muted/60 p-1"
          >
            {VIEW_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                aria-pressed={mode === key}
                onClick={() => setView(key)}
                className={cn(
                  "h-9 rounded-md px-3.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
                  mode === key
                    ? "bg-card text-foreground shadow-[0_1px_3px_rgba(34,31,27,0.12)]"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {VIEW_LABEL[key]}
              </button>
            ))}
          </div>
        ) : null}

        {isLoading || session.isPending ? (
          <div>
            <SkeletonCards />
          </div>
        ) : isError ? (
          <Alert variant="error" className="flex items-center justify-between gap-4">
            <span>{messages.calismalar.loadError}</span>
            <Button variant="secondary" size="sm" onClick={() => void refetch()}>
              {messages.calismalar.retry}
            </Button>
          </Alert>
        ) : mode === "review" ? (
          <ReviewView items={items} scope={scope} />
        ) : (
          <StudentView items={ownItems} />
        )}
      </PageBody>
    </AppShell>
  );
}
