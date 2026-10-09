"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listEngagements } from "@/lib/api/engagements";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

type FilterKey = keyof typeof messages.calismalar.filterTabs;

const FILTER_KEYS: FilterKey[] = ["all", "ongoing", "evaluation", "verified", "closed"];

const FILTER_STATUSES: Record<Exclude<FilterKey, "all">, string[]> = {
  ongoing: ["DRAFT", "PENDING_APPROVAL", "ACTIVE"],
  evaluation: ["PENDING_EVALUATION", "EVALUATED"],
  verified: ["VERIFIED", "RESOLVED"],
  closed: ["REJECTED", "CANCELLED", "DISPUTED"],
};

type BadgeVariant = "default" | "success" | "error" | "warning";

const STATUS_BADGE_VARIANT: Record<string, BadgeVariant> = {
  DRAFT: "default",
  PENDING_APPROVAL: "warning",
  ACTIVE: "default",
  PENDING_EVALUATION: "warning",
  EVALUATED: "default",
  VERIFIED: "success",
  RESOLVED: "success",
  REJECTED: "error",
  CANCELLED: "error",
  DISPUTED: "error",
};

const DOT_CLASS: Record<BadgeVariant, string> = {
  default: "bg-foreground",
  success: "bg-success",
  error: "bg-destructive",
  warning: "bg-warning",
};

// Completed chain steps per status; `broken` marks the step where the chain stopped (1-based).
const CHAIN_PROGRESS: Record<string, { done: number; broken?: number }> = {
  DRAFT: { done: 0 },
  PENDING_APPROVAL: { done: 0 },
  ACTIVE: { done: 1 },
  PENDING_EVALUATION: { done: 2 },
  EVALUATED: { done: 2 },
  VERIFIED: { done: 4 },
  RESOLVED: { done: 4 },
  REJECTED: { done: 0, broken: 1 },
  CANCELLED: { done: 1, broken: 2 },
  DISPUTED: { done: 3, broken: 4 },
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
      <div className="max-w-[1120px] px-4 py-8 md:px-6 lg:px-10">
        <header>
          <h1 className="font-serif text-[32px] font-semibold leading-10 text-foreground">
            {messages.calismalar.listTitle}
          </h1>
          {!isLoading && !isError ? (
            <p className="mt-2 text-sm text-muted-foreground">
              {formatTemplate(messages.calismalar.listCount, { count: items.length })}
            </p>
          ) : null}
        </header>

        {isLoading ? (
          <div className="mt-8">
            <SkeletonCards />
          </div>
        ) : isError ? (
          <Alert variant="error" className="mt-8 flex items-center justify-between gap-4">
            <span>{messages.calismalar.loadError}</span>
            <Button variant="secondary" size="sm" onClick={() => void refetch()}>
              {messages.calismalar.retry}
            </Button>
          </Alert>
        ) : items.length === 0 ? (
          <section className="mt-8 rounded-lg border border-border bg-card p-6">
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
            <div
              role="tablist"
              aria-label={messages.calismalar.filterTabsLabel}
              className="mt-8 flex overflow-x-auto border-b border-border"
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
                      "-mb-px flex h-10 shrink-0 items-center gap-1.5 border-b-2 px-4 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success",
                      selected
                        ? "border-success text-foreground"
                        : "border-transparent text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {messages.calismalar.filterTabs[key]}
                    <span className="font-mono text-xs text-muted-foreground tabular-nums">
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
                          className="flex h-full flex-col gap-4 rounded-lg border border-border bg-card p-5 hover:border-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                        >
                          <div className="flex items-start justify-end">
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
                          </div>
                          <div className="flex items-center justify-between gap-2">
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
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
