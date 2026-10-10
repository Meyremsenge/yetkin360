"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { StatusTone } from "@/lib/ui/engagement-chain";
import messages from "@/messages/tr.json";

/**
 * Building blocks shared by the organization, institution and admin panels so
 * they speak the same visual language as the student screens (calismalar,
 * profil): toned stat tiles, icon-headed section cards, status pills with a
 * dot, guiding empty states and a sticky side card.
 */

// Lucide-style line icons (inline paths; no icon dependency).
const ICON_PATHS = {
  building: "M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18zM6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4",
  landmark: "M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7M12 2l8 5H4z",
  briefcase: "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z",
  users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  userPlus: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM19 8v6M22 11h-6",
  clock: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  check: "M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4 12 14l-3-3",
  shield: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1zM9 12l2 2 4-4",
  globe: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2a15 15 0 0 1 4 10 15 15 0 0 1-4 10 15 15 0 0 1-4-10 15 15 0 0 1 4-10z",
  mail: "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM22 6l-10 7L2 6",
  link: "M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1",
  bell: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0",
  inbox: "M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",
  tags: "M12.59 2.59A2 2 0 0 0 11.17 2H4a2 2 0 0 0-2 2v7.17a2 2 0 0 0 .59 1.41l8.7 8.7a2.43 2.43 0 0 0 3.42 0l6.58-6.58a2.43 2.43 0 0 0 0-3.42zM7.5 7.5h.01",
  flag: "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7",
  clipboard: "M9 2h6a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zM16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M9 12h6M9 16h4",
  lock: "M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2zM7 11V7a5 5 0 0 1 10 0v4",
  arrowRight: "M5 12h14M13 6l6 6-6 6",
  plus: "M12 5v14M5 12h14",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
} as const;

export type IconName = keyof typeof ICON_PATHS;

export function PanelIcon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn("h-[18px] w-[18px]", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

export type Tone = "ink" | "ochre" | "pine" | "brick";

const TONE_TILE: Record<Tone, string> = {
  ink: "bg-muted text-foreground",
  ochre: "bg-warning/10 text-warning",
  pine: "bg-success/10 text-success",
  brick: "bg-destructive/10 text-destructive",
};

const TONE_VALUE: Record<Tone, string> = {
  ink: "text-foreground",
  ochre: "text-warning",
  pine: "text-success",
  brick: "text-destructive",
};

/**
 * Count tile with a toned icon. With `href` (an in-page anchor) the whole
 * tile jumps to the section it summarises.
 */
export function StatTile({
  label,
  value,
  tone,
  icon,
  href,
}: {
  label: string;
  value: number;
  tone: Tone;
  icon: IconName;
  href?: string;
}) {
  // A pending count of zero is good news: drop the warning colour.
  const valueTone = value === 0 && (tone === "ochre" || tone === "brick") ? "ink" : tone;
  const body = (
    <>
      <span className={cn("hidden h-11 w-11 shrink-0 items-center justify-center rounded-lg min-[400px]:flex", TONE_TILE[tone])}>
        <PanelIcon name={icon} className="h-5 w-5" />
      </span>
      <span className="min-w-0">
        <span className="block text-xs text-muted-foreground">{label}</span>
        <span
          className={cn(
            "block font-serif text-[28px] font-semibold leading-tight tabular-nums",
            TONE_VALUE[valueTone]
          )}
        >
          {value}
        </span>
      </span>
    </>
  );
  const base = "flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-4 sm:gap-4 sm:px-5";
  if (href) {
    return (
      <a
        href={href}
        className={cn(
          base,
          "transition-colors hover:border-muted-foreground/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        )}
      >
        {body}
      </a>
    );
  }
  return <div className={base}>{body}</div>;
}

/** Card with an icon header (title, count, one-line hint) — same as the engagement detail sections. */
export function PanelSection({
  id,
  icon,
  title,
  hint,
  count,
  actions,
  children,
  flush,
}: {
  id?: string;
  icon: IconName;
  title: string;
  hint?: string;
  count?: number;
  actions?: ReactNode;
  children: ReactNode;
  /** Render children edge to edge (tables/lists draw their own padding). */
  flush?: boolean;
}) {
  return (
    <section id={id} className="scroll-mt-24 rounded-xl border border-border bg-card">
      <header className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success">
          <PanelIcon name={icon} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="flex items-center gap-2 font-serif text-lg font-semibold text-foreground">
            {title}
            {count !== undefined ? (
              <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] font-normal tabular-nums text-muted-foreground">
                {count}
              </span>
            ) : null}
          </h2>
          {hint ? <p className="text-[13px] text-muted-foreground">{hint}</p> : null}
        </div>
        {actions ? <div className="flex w-full flex-wrap gap-2 sm:w-auto">{actions}</div> : null}
      </header>
      <div className={flush ? undefined : "p-5"}>{children}</div>
    </section>
  );
}

/** Empty state that tells the reader what to do next (frontend rule: never just "nothing here"). */
export function EmptyState({
  icon,
  title,
  hint,
  action,
  className,
}: {
  icon: IconName;
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start gap-4 rounded-lg border border-dashed border-border px-4 py-4", className)}>
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sand text-muted-foreground">
        <PanelIcon name={icon} />
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        {hint ? <p className="mt-0.5 max-w-[560px] text-sm text-muted-foreground">{hint}</p> : null}
        {action ? <div className="mt-3">{action}</div> : null}
      </div>
    </div>
  );
}

const PILL_CLASS: Record<StatusTone, string> = {
  default: "bg-muted text-foreground",
  warning: "bg-warning/10 text-warning",
  success: "bg-success/10 text-success",
  error: "bg-destructive/10 text-destructive",
};

const PILL_DOT: Record<StatusTone, string> = {
  default: "bg-foreground",
  warning: "bg-warning",
  success: "bg-success",
  error: "bg-destructive",
};

/** Status badge with a leading dot in the status colour. */
export function StatusPill({ tone, children, className }: { tone: StatusTone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium",
        PILL_CLASS[tone],
        className
      )}
    >
      <span aria-hidden="true" className={cn("h-1.5 w-1.5 rounded-full", PILL_DOT[tone])} />
      {children}
    </span>
  );
}

/** "Next step" hint chip, coloured like the status it follows. */
export function NextStepHint({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] font-medium", PILL_CLASS[tone])}>
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path d={ICON_PATHS.arrowRight} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {children}
    </span>
  );
}

/** Right-hand action column; sticks under the top bar on wide screens. */
export function SideCard({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="font-serif text-lg font-semibold text-foreground">{title}</p>
      {hint ? <p className="mt-1 text-[13px] text-muted-foreground">{hint}</p> : null}
      <div className="mt-4">{children}</div>
    </div>
  );
}

/** Main column + sticky 340px aside, stacked on narrow screens. */
export function PanelGrid({ main, aside }: { main: ReactNode; aside: ReactNode }) {
  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-6">{main}</div>
      <aside className="space-y-4 lg:sticky lg:top-24">{aside}</aside>
    </div>
  );
}

/** Pulse blocks in the shape of a panel (header tiles + two cards). */
export function PanelSkeleton({ tiles = 3 }: { tiles?: number }) {
  return (
    <div role="status" className="space-y-6">
      <span className="sr-only">{messages.shell.loading}</span>
      <div aria-hidden="true" className={cn("grid gap-4", tiles === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3")}>
        {Array.from({ length: tiles }, (_, n) => (
          <div key={n} className="h-[78px] animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
        ))}
      </div>
      <div aria-hidden="true" className="h-56 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
      <div aria-hidden="true" className="h-40 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
    </div>
  );
}

const ACTION_BASE =
  "inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-md px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50";

/** Button looks used across the panels (brief §2.1). */
export const actionClass = {
  primary: cn(ACTION_BASE, "bg-success text-background hover:bg-success/90"),
  outline: cn(ACTION_BASE, "border border-success text-success hover:bg-success/10"),
  neutral: cn(ACTION_BASE, "border border-border bg-muted text-foreground hover:bg-sand"),
  dangerOutline: cn(ACTION_BASE, "border border-destructive/40 text-destructive hover:bg-destructive/10"),
};

/** In-panel link styled as a button. */
export function ActionLink({
  href,
  variant = "outline",
  icon,
  children,
  className,
}: {
  href: string;
  variant?: keyof typeof actionClass;
  icon?: IconName;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link href={href} className={cn(actionClass[variant], className)}>
      {icon ? <PanelIcon name={icon} className="h-4 w-4" /> : null}
      {children}
    </Link>
  );
}

/**
 * Copies `value` (a function is evaluated on click, e.g. to read window.location);
 * the label flips to a check for 1.5s, failures are announced.
 */
export function CopyButton({
  value,
  label,
  variant = "outline",
  className,
}: {
  value: string | (() => string);
  label: string;
  variant?: keyof typeof actionClass;
  className?: string;
}) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (state !== "copied") return;
    const timer = setTimeout(() => setState("idle"), 1500);
    return () => clearTimeout(timer);
  }, [state]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(typeof value === "function" ? value() : value);
      setState("copied");
    } catch {
      setState("failed");
    }
  };

  return (
    <span className="inline-flex flex-col">
      <button type="button" onClick={copy} className={cn(actionClass[variant], className)}>
        {state === "copied" ? (
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <PanelIcon name="link" className="h-4 w-4" />
        )}
        {state === "copied" ? messages.panel.copied : label}
      </button>
      <span aria-live="polite" className="mt-1 text-[13px] text-destructive empty:hidden">
        {state === "failed" ? messages.panel.copyFailed : ""}
      </span>
    </span>
  );
}

export function formatTemplate(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, String(value)), template);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

export function relativeTime(iso: string, now: number = Date.now()): string {
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

/** Relative time with the full date on hover (brief §1.2). */
export function TimeAgo({ iso }: { iso: string }) {
  return (
    <time dateTime={iso} title={formatDate(iso)} className="font-mono text-xs text-muted-foreground">
      {relativeTime(iso)}
    </time>
  );
}

/** Initials avatar on sand (brief §2.14). */
export function Initials({ name, className }: { name: string; className?: string }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR"))
    .join("");
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-sand font-serif text-sm font-medium text-foreground",
        className
      )}
    >
      {initials || "?"}
    </span>
  );
}

/** Numbered "what happens next" steps for onboarding forms. */
export function StepsCard({ title, steps }: { title: string; steps: { title: string; hint: string }[] }) {
  return (
    <div className="rounded-xl border border-border bg-sand/50 p-5">
      <p className="font-serif text-lg font-semibold text-foreground">{title}</p>
      <ol className="mt-4 space-y-4">
        {steps.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-card font-mono text-xs text-foreground">
              {index + 1}
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium text-foreground">{step.title}</span>
              <span className="block text-[13px] text-muted-foreground">{step.hint}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Form card on the left, steps card on the right (stacked on narrow screens). */
export function FormLayout({ form, aside }: { form: ReactNode; aside: ReactNode }) {
  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,560px)_minmax(0,360px)] lg:gap-10">
      <div className="rounded-xl border border-border bg-card p-5 md:p-6">{form}</div>
      <aside>{aside}</aside>
    </div>
  );
}
