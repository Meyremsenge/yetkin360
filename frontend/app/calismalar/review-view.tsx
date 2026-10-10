"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { EngagementSummary } from "@/lib/api/engagements";
import { STATUS_TONE } from "@/lib/ui/engagement-chain";
import {
  approvedGroup,
  reviewHref,
  splitForReview,
  type ApprovedGroup,
  type ReviewerScope,
} from "@/lib/ui/engagement-review";
import { cn } from "@/lib/utils";
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
  formatTemplate,
  type TileTone,
} from "./list-parts";

const t = messages.calismalar.review;

type FilterKey = "all" | ApprovedGroup;

const FILTER_KEYS: FilterKey[] = ["all", "ongoing", "verified", "closed"];

function studentName(item: EngagementSummary): string {
  return item.talent_name.trim() || t.unnamedStudent;
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts;
  return letters.map((part) => part.charAt(0).toLocaleUpperCase("tr-TR")).join("");
}

function Initials({ name }: { name: string }) {
  return (
    <span
      aria-hidden="true"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sand font-serif text-sm font-semibold text-foreground"
    >
      {initialsOf(name)}
    </span>
  );
}

function matchesQuery(item: EngagementSummary, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase("tr-TR");
  if (!needle) return true;
  return `${item.talent_name} ${item.title}`.toLocaleLowerCase("tr-TR").includes(needle);
}

/**
 * /calismalar for organization members and institution coordinators: what is
 * waiting on them first, then the student engagements they approved.
 */
export function ReviewView({ items, scope }: { items: EngagementSummary[]; scope: ReviewerScope }) {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [query, setQuery] = useState("");

  const { awaiting, approved } = useMemo(() => splitForReview(items, scope), [items, scope]);

  if (awaiting.length === 0 && approved.length === 0) {
    return (
      <section className="rounded-xl border border-border bg-card p-6">
        <p className="text-base font-semibold text-foreground">{t.emptyTitle}</p>
        <p className="mt-1 max-w-[640px] text-sm text-muted-foreground">{t.emptyHint}</p>
      </section>
    );
  }

  function countFor(key: FilterKey): number {
    return key === "all" ? approved.length : approved.filter((item) => approvedGroup(item) === key).length;
  }

  const visibleApproved = approved.filter(
    (item) => (filter === "all" || approvedGroup(item) === filter) && matchesQuery(item, query),
  );

  const tiles: { key: keyof typeof t.summary; tone: TileTone; icon: string; count: number; href: string }[] = [
    { key: "awaiting", tone: "ochre", icon: TILE_ICON.inbox, count: awaiting.length, href: "#islem-bekleyenler" },
    { key: "approved", tone: "ink", icon: TILE_ICON.briefcase, count: approved.length, href: "#onayladiklariniz" },
    { key: "verified", tone: "pine", icon: TILE_ICON.check, count: countFor("verified"), href: "#onayladiklariniz" },
  ];

  return (
    <>
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {tiles.map(({ key, tone, icon, count, href }) => (
          <li key={key}>
            <a
              href={href}
              className="flex items-center gap-4 rounded-xl border border-border bg-card px-5 py-4 transition-colors hover:border-muted-foreground/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
            >
              <TileIcon path={icon} tone={tone} />
              <span className="flex flex-col">
                <span className="text-xs text-muted-foreground">{t.summary[key]}</span>
                <span
                  data-testid={`review-count-${key}`}
                  className="font-serif text-[28px] font-semibold leading-tight tabular-nums text-foreground"
                >
                  {count}
                </span>
              </span>
            </a>
          </li>
        ))}
      </ul>

      <section
        id="islem-bekleyenler"
        aria-labelledby="islem-bekleyenler-baslik"
        className="mt-8 scroll-mt-24 rounded-xl border border-border bg-card"
      >
        <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border px-5 py-4">
          <h2 id="islem-bekleyenler-baslik" className="font-serif text-lg font-semibold text-foreground">
            {t.awaitingTitle}
            <span className="ml-2 rounded-full bg-warning/10 px-2 py-0.5 font-mono text-xs tabular-nums text-warning">
              {awaiting.length}
            </span>
          </h2>
          {awaiting.length > 0 ? <p className="text-xs text-muted-foreground">{t.awaitingHint}</p> : null}
        </header>

        {awaiting.length === 0 ? (
          <div className="px-5 py-6">
            <p className="text-sm font-medium text-foreground">{t.awaitingEmptyTitle}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t.awaitingEmptyHint}</p>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {awaiting.map(({ item, action }) => {
              const name = studentName(item);
              return (
                <li
                  key={item.id}
                  data-testid="review-awaiting-row"
                  className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:gap-4"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <Initials name={name} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">{name}</p>
                      <p className="truncate text-sm text-muted-foreground">
                        {item.title} · {messages.calismalar.kind[item.kind]} · {item.organization_name}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 md:shrink-0">
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-warning/10 px-2 py-1 text-[13px] font-medium text-warning">
                      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-warning" />
                      {t.action[action]}
                    </span>
                    <TimeAgo iso={item.updated_at} />
                    <Link
                      href={reviewHref(item, action)}
                      aria-label={formatTemplate(t.actionButtonLabel, {
                        student: name,
                        title: item.title,
                        action: t.actionButton[action],
                      })}
                      className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md bg-success px-3.5 text-sm font-medium text-background transition-colors hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
                    >
                      {t.actionButton[action]}
                      <ArrowIcon />
                    </Link>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section id="onayladiklariniz" aria-labelledby="onayladiklariniz-baslik" className="mt-10 scroll-mt-24">
        <h2 id="onayladiklariniz-baslik" className="font-serif text-lg font-semibold text-foreground">
          {t.approvedTitle}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{t.approvedHint}</p>

        {approved.length === 0 ? (
          <div className="mt-4 rounded-xl border border-dashed border-muted-foreground/30 p-6">
            <p className="text-sm font-medium text-foreground">{t.approvedEmptyTitle}</p>
            <p className="mt-1 max-w-[640px] text-sm text-muted-foreground">{t.approvedEmptyHint}</p>
          </div>
        ) : (
          <>
            <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div
                role="tablist"
                aria-label={t.filterTabsLabel}
                className="flex gap-1 overflow-x-auto overflow-y-hidden rounded-lg border border-border bg-muted/60 p-1 [scrollbar-width:none] sm:inline-flex [&::-webkit-scrollbar]:hidden"
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
                      {t.filterTabs[key]}
                      <span
                        className={cn(
                          "min-w-[20px] rounded-full px-1.5 text-center font-mono text-[11px] tabular-nums",
                          selected ? "bg-success/10 text-success" : "bg-background/70 text-muted-foreground",
                        )}
                      >
                        {countFor(key)}
                      </span>
                    </button>
                  );
                })}
              </div>
              <div className="w-full lg:w-72">
                <Label htmlFor="review-search" className="sr-only">
                  {t.searchLabel}
                </Label>
                <Input
                  id="review-search"
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={t.searchPlaceholder}
                />
              </div>
            </div>

            <div role="tabpanel" className="mt-6">
              {visibleApproved.length === 0 ? (
                <p role="status" className="text-sm text-muted-foreground">
                  {query.trim() ? t.searchEmpty : messages.calismalar.filterEmpty}
                </p>
              ) : (
                <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {visibleApproved.map((item) => {
                    const tone = STATUS_TONE[item.status] ?? "default";
                    const isVerified = approvedGroup(item) === "verified";
                    const name = studentName(item);
                    const stage = t.stage[item.status as keyof typeof t.stage];
                    return (
                      <li key={item.id}>
                        <Link
                          href={`/calismalar/${item.id}`}
                          data-testid="review-approved-card"
                          className={cn(
                            "group relative flex h-full flex-col gap-4 overflow-hidden rounded-xl border bg-card p-5 transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-28px_rgba(34,31,27,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success motion-reduce:transition-none motion-reduce:hover:translate-y-0",
                            isVerified
                              ? "border-success/30 hover:border-success/60"
                              : "border-border hover:border-muted-foreground/40",
                          )}
                        >
                          {isVerified ? (
                            <span aria-hidden="true" className="absolute inset-x-0 top-0 h-1 bg-success" />
                          ) : null}
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex min-w-0 items-center gap-3">
                              <Initials name={name} />
                              <p className="truncate text-sm font-semibold text-foreground">{name}</p>
                            </div>
                            <Badge variant={tone} className="shrink-0 gap-1.5">
                              <span aria-hidden="true" className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASS[tone])} />
                              {messages.calismalar.status[item.status]}
                            </Badge>
                          </div>
                          <div className="flex-1">
                            <div className="flex items-start gap-2">
                              <h3 className="line-clamp-2 font-serif text-xl font-medium leading-7 text-foreground">
                                {item.title}
                              </h3>
                              {isVerified ? <SealMark /> : null}
                            </div>
                            <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                              <KindIcon kind={item.kind} />
                              {messages.calismalar.kind[item.kind]} · {item.organization_name}
                            </p>
                            {stage ? (
                              <p
                                className={cn(
                                  "mt-4 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] font-medium",
                                  CHIP_TONE[tone],
                                )}
                              >
                                <ArrowIcon />
                                {stage}
                              </p>
                            ) : null}
                          </div>
                          <div className="flex items-center justify-between gap-2 border-t border-border pt-4">
                            <MiniChain status={item.status} />
                            <TimeAgo iso={item.updated_at} />
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
      </section>
    </>
  );
}
