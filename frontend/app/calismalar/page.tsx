"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listEngagements } from "@/lib/api/engagements";
import { cn } from "@/lib/utils";
import { CHAIN_PROGRESS, STATUS_TONE, type StatusTone } from "@/lib/ui/engagement-chain";
import messages from "@/messages/tr.json";

type FilterKey = keyof typeof messages.calismalar.filterTabs;

const FILTER_KEYS: FilterKey[] = ["all", "ongoing", "evaluation", "verified", "closed"];

const FILTER_STATUSES: Record<Exclude<FilterKey, "all">, string[]> = {
  ongoing: ["DRAFT", "PENDING_APPROVAL", "ACTIVE"],
  evaluation: ["PENDING_EVALUATION", "EVALUATED"],
  verified: ["VERIFIED", "RESOLVED"],
  closed: ["REJECTED", "CANCELLED", "DISPUTED"],
};

type BadgeVariant = StatusTone;

const STATUS_BADGE_VARIANT = STATUS_TONE;

const DOT_CLASS: Record<BadgeVariant, string> = {
  default: "bg-foreground",
  success: "bg-success",
  error: "bg-destructive",
  warning: "bg-warning",
};

function formatTemplate(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replace(`{${key}}`, String(value)),
    template,
  );
}

function relativeTime(iso: string, now: number = Date.now()): string {
  const rel = messages.calismalar.relative;
  const seconds = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return rel.now;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return formatTemplate(rel.minutes, { n: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return formatTemplate(rel.hours, { n: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return formatTemplate(rel.days, { n: days });
  if (days < 30) return formatTemplate(rel.weeks, { n: Math.floor(days / 7) });
  if (days < 365) return formatTemplate(rel.months, { n: Math.floor(days / 30) });
  return formatTemplate(rel.years, { n: Math.floor(days / 365) });
}

function fullDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function MiniChain({ status }: { status: string }) {
  const { done, broken } = CHAIN_PROGRESS[status] ?? { done: 0 };
  const label = broken
    ? formatTemplate(messages.calismalar.chainBrokenLabel, { step: broken })
    : formatTemplate(messages.calismalar.chainLabel, { done });

  return (
    <span role="img" aria-label={label} className="flex items-center">
      {[1, 2, 3, 4].map((step) => {
        const isDone = step <= done;
        const isBroken = step === broken;
        return (
          <span key={step} className="flex items-center" aria-hidden="true">
            {step > 1 ? (
              <span className={cn("h-px w-3", step <= done ? "bg-success" : "bg-border")} />
            ) : null}
            <span
              className={cn(
                "h-2 w-2 rounded-full border",
                isDone && "border-success bg-success",
                isBroken && "border-destructive bg-destructive/10",
                !isDone && !isBroken && "border-border bg-card",
              )}
            />
          </span>
        );
      })}
    </span>
  );
}

function SealMark() {
  return (
    <span
      data-testid="calismalar-verified-mark"
      className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success text-background"
    >
      <svg
        viewBox="0 0 24 24"
        className="h-3 w-3"
        fill="none"
        stroke="currentColor"
        strokeWidth={3}
        aria-hidden="true"
      >
        <path d="M5 12l5 5L20 7" />
      </svg>
    </span>
  );
}

type Tone = "ink" | "ochre" | "pine";

const TONE_TILE: Record<Tone, string> = {
  ink: "bg-muted text-foreground",
  ochre: "bg-warning/10 text-warning",
  pine: "bg-success/10 text-success",
};

const SUMMARY: {
  key: keyof typeof messages.calismalar.summary;
  filterKey: FilterKey;
  tone: Tone;
  icon: string;
}[] = [
  {
    key: "total",
    filterKey: "all",
    tone: "ink",
    icon: "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z",
  },
  { key: "ongoing", filterKey: "ongoing", tone: "ochre", icon: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z" },
  { key: "verified", filterKey: "verified", tone: "pine", icon: "M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4 12 14l-3-3" },
];

// "Next step" chip colour follows the status badge.
const NEXT_TONE: Record<BadgeVariant, string> = {
  default: "bg-muted text-foreground",
  warning: "bg-warning/10 text-warning",
  success: "bg-success/10 text-success",
  error: "bg-destructive/10 text-destructive",
};

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

// One quiet line icon per engagement kind (lucide shapes, inline).
function KindIcon({ kind }: { kind: string }) {
  const paths: Record<string, string> = {
    INTERNSHIP: "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z",
    CAPSTONE: "M22 10 12 5 2 10l10 5 10-5zM6 12v5c3 2 9 2 12 0v-5",
    SHORT_PROJECT: "M13 2 3 14h9l-1 8 10-12h-9l1-8z",
    PART_TIME: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-[18px] w-[18px]"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[kind] ?? paths.INTERNSHIP} />
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

export default function CalismalarPage() {
  const [filter, setFilter] = useState<FilterKey>("all");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["engagements"],
    queryFn: listEngagements,
  });

  const items = data?.items ?? [];

  function countFor(key: FilterKey): number {
    return key === "all"
      ? items.length
      : items.filter((item) => FILTER_STATUSES[key].includes(item.status)).length;
  }

  const visibleItems =
    filter === "all"
      ? items
      : items.filter((item) => FILTER_STATUSES[filter].includes(item.status));

  return (
    <AppShell>
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

      <PageBody>
        {isLoading ? (
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
        ) : items.length === 0 ? (
          <section className="rounded-xl border border-border bg-card p-6">
            <BriefcaseIcon />
            <p className="mt-4 text-base font-semibold text-foreground">
              {messages.calismalar.emptyMessage}
            </p>
            <p className="mt-1 max-w-[640px] text-sm text-muted-foreground">
              {messages.calismalar.emptyHint}
            </p>
          </section>
        ) : (
          <>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {SUMMARY.map(({ key, filterKey, tone, icon }) => (
                <div key={key} className="flex items-center gap-4 rounded-xl border border-border bg-card px-5 py-4">
                  <span className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-lg", TONE_TILE[tone])}>
                    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d={icon} />
                    </svg>
                  </span>
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
                    const variant = STATUS_BADGE_VARIANT[item.status] ?? "default";
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
                              <span
                                aria-hidden="true"
                                className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASS[variant])}
                              />
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
                                NEXT_TONE[variant]
                              )}
                            >
                              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                                <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                              {messages.calismalar.nextStep[item.status as keyof typeof messages.calismalar.nextStep]}
                            </p>
                          </div>
                          <div className="flex items-center justify-between gap-2 border-t border-border pt-4">
                            <MiniChain status={item.status} />
                            <time
                              dateTime={item.updated_at}
                              title={fullDate(item.updated_at)}
                              className="font-mono text-xs text-muted-foreground"
                            >
                              {relativeTime(item.updated_at)}
                            </time>
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
        )}
      </PageBody>
    </AppShell>
  );
}
