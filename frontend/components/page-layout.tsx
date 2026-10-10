import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

/** Shared content width for app screens: centred, grows to 1200px. */
export const PAGE_CONTAINER = "mx-auto w-full max-w-[1200px] px-4 md:px-6 lg:px-10";

/**
 * White header strip on top of every app screen: what this page is (eyebrow,
 * title, one-line description), its main action, and optional extra content
 * such as the chain legend. Gives the paper background a bright top band.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  back,
  children,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  back?: { href: string; label: string };
  children?: ReactNode;
}) {
  return (
    <header className="relative overflow-hidden border-b border-border bg-card">
      <div
        aria-hidden="true"
        className="y360-dot-grid pointer-events-none absolute inset-y-0 right-0 w-1/2 [mask-image:linear-gradient(to_left,black,transparent)]"
      />
      <div className={cn(PAGE_CONTAINER, "relative py-7 lg:py-9")}>
        {back ? (
          <Link
            href={back.href}
            className="mb-4 inline-flex items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
              <path d="M19 12H5M11 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {back.label}
          </Link>
        ) : null}
        <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-5">
          <div className="min-w-0 max-w-3xl">
            {eyebrow ? (
              <p className="mb-2 font-mono text-xs uppercase tracking-[0.12em] text-success">{eyebrow}</p>
            ) : null}
            <h1 className="font-serif text-[32px] font-semibold leading-tight text-foreground md:text-[36px]">
              {title}
            </h1>
            {description ? (
              <div className="mt-2 text-[15px] leading-6 text-muted-foreground">{description}</div>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap items-center gap-3">{actions}</div> : null}
        </div>
        {children ? <div className="mt-6">{children}</div> : null}
      </div>
    </header>
  );
}

export function PageBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn(PAGE_CONTAINER, "py-8", className)}>{children}</div>;
}

const LEGEND = [
  { label: messages.home.chain.claim, hint: messages.home.demo.steps.claim.actor },
  { label: messages.home.chain.evidence, hint: messages.home.demo.steps.evidence.actor },
  { label: messages.home.chain.attestation, hint: messages.home.demo.steps.attestation.actor },
  { label: messages.home.chain.verified, hint: messages.home.demo.steps.verified.actor },
];

/**
 * The four chain steps as a compact strip, so the model behind every card is
 * readable at a glance. `current` (1-4) highlights progress on detail pages.
 */
export function ChainLegend({ current, broken }: { current?: number; broken?: number }) {
  return (
    <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label={messages.home.chainTitle}>
      {LEGEND.map((step, index) => {
        const n = index + 1;
        const done = current !== undefined && n <= current;
        const isBroken = broken === n;
        const isLast = n === LEGEND.length;
        return (
          <li
            key={step.label}
            className={cn(
              "flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
              isBroken
                ? "border-destructive/30 bg-destructive/[0.06]"
                : done
                  ? isLast
                    ? "border-success/40 bg-success/[0.1]"
                    : "border-success/25 bg-success/[0.05]"
                  : "border-border bg-background"
            )}
          >
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-xs",
                isBroken
                  ? "bg-destructive text-background"
                  : done || (current === undefined && isLast)
                    ? "bg-success text-background"
                    : "border border-border bg-card text-muted-foreground"
              )}
            >
              {done && !isBroken ? (
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                  <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                n
              )}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium text-foreground">{step.label}</span>
              <span className="block truncate text-xs text-muted-foreground">{step.hint}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
