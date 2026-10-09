import type { ReactNode } from "react";
import Link from "next/link";

// Shared frame for 404 / error pages: slim top bar + 560px left-aligned column.
export function StatusPageFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-sand">
        <div className="mx-auto flex h-14 max-w-6xl items-center px-4 sm:px-8">
          <Link
            href="/"
            className="font-serif text-lg font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
          >
            Yetkin360
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[560px] px-4 pb-16 pt-16 sm:pt-24">{children}</main>
    </div>
  );
}

export const primaryLinkClass =
  "inline-flex h-10 items-center rounded-md bg-success px-4 text-sm font-medium text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2";

export const outlineLinkClass =
  "inline-flex h-10 items-center rounded-md border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2";
