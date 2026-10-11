"use client";

import type { FormHTMLAttributes, ReactNode } from "react";
import { Alert } from "@/components/ui/alert";
import { EmptyState, type IconName } from "@/components/panel-kit";
import type { StatusTone } from "@/lib/ui/engagement-chain";
import { cn } from "@/lib/utils";

/**
 * Admin screen building blocks on top of panel-kit, so every admin page uses
 * the same fields, filter bar, tables and loading/error/empty states.
 */

export const FIELD_CLASS =
  "block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25 disabled:bg-muted";

export const LABEL_CLASS = "mb-1.5 block text-sm font-medium text-foreground";

/** Compact size for buttons inside list rows and table cells. */
export const SM = "h-8 px-3 text-xs";

/** Search/filter form drawn as a card above a list. */
export function FilterBar({ className, children, ...props }: FormHTMLAttributes<HTMLFormElement>) {
  return (
    <form
      {...props}
      className={cn("flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-4", className)}
    >
      {children}
    </form>
  );
}

export function LoadingBlock({ label, className }: { label: string; className?: string }) {
  return (
    <div role="status">
      <span className="sr-only">{label}</span>
      <div
        aria-hidden="true"
        className={cn("h-64 animate-pulse rounded-xl bg-muted motion-reduce:animate-none", className)}
      />
    </div>
  );
}

export function LoadError({
  message,
  onRetry,
  retryLabel,
}: {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <Alert variant="error" className="text-sm">
      <p>{message}</p>
      {onRetry && retryLabel ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive"
        >
          {retryLabel}
        </button>
      ) : null}
    </Alert>
  );
}

/** Empty state inside a card, matching the queue screens. */
export function EmptyCard({ icon, title, hint }: { icon: IconName; title: string; hint?: string }) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <EmptyState icon={icon} title={title} hint={hint} />
    </section>
  );
}

/** Table styles: card frame, muted header row, divided body. */
export const TABLE = {
  frame: "overflow-x-auto rounded-xl border border-border bg-card",
  table: "w-full border-collapse text-left text-sm",
  headRow: "border-b border-border bg-muted/50",
  th: "whitespace-nowrap px-4 py-3 text-xs font-medium uppercase tracking-wide text-muted-foreground",
  row: "border-b border-border last:border-b-0 align-middle transition-colors hover:bg-muted/30",
  td: "px-4 py-3 text-foreground",
};

/** Account/entity status → pill tone (ACTIVE green, PENDING ochre, SUSPENDED red). */
export function statusTone(status: string): StatusTone {
  switch (status) {
    case "ACTIVE":
    case "RESOLVED":
      return "success";
    case "PENDING":
    case "OPEN":
    case "UNDER_REVIEW":
    case "EXPLANATION_REQUESTED":
    case "EXPLANATION_SUBMITTED":
    case "ESCALATED":
      return "warning";
    case "SUSPENDED":
    case "UPHELD":
    case "CONFIRMED":
      return "error";
    default:
      return "default";
  }
}

export function Field({ label, htmlFor, children, className }: { label: string; htmlFor: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("min-w-[180px]", className)}>
      <label htmlFor={htmlFor} className={LABEL_CLASS}>
        {label}
      </label>
      {children}
    </div>
  );
}
