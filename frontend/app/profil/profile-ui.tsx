import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

// Local presentation helpers for the profile screen. Kept next to the screen
// (not in components/ui) so parallel screen work does not collide.

export const fieldClass =
  "block w-full h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground/70 hover:border-muted-foreground/40 focus-visible:outline-none focus-visible:border-success focus-visible:ring-2 focus-visible:ring-success/25 disabled:bg-muted disabled:text-muted-foreground";

export const labelClass = "block text-xs font-medium text-foreground mb-1.5";

export const primaryButtonClass =
  "bg-success text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 disabled:opacity-60";

export const focusRingClass =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";

export function ProfileSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card className="mt-6 p-4 sm:p-6">
      <h2 className="font-serif text-xl font-medium text-foreground">{title}</h2>
      {description ? (
        <p className="mt-1 mb-4 text-sm text-muted-foreground">{description}</p>
      ) : (
        <div className="mb-4" />
      )}
      {children}
    </Card>
  );
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div aria-busy="true" className="space-y-2 animate-pulse">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-12 rounded-md bg-muted" />
      ))}
    </div>
  );
}

export function EmptyNote({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-md border border-dashed border-border p-4">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      {hint ? <p className="mt-1 text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
