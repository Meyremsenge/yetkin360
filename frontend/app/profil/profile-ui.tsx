"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
  action,
  children,
}: {
  title: string;
  description?: string;
  /** Primary action, top-right of the card (e.g. "+ Yeni kayıt"). */
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="mt-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="font-serif text-xl font-medium text-foreground">{title}</h2>
        {action}
      </div>
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

/**
 * Header button ("+ …") that opens a form in a centred modal, so the add
 * action stays at the top however long a list grows. The content stays
 * mounted: a draft survives closing; `children(close)` can close it on success.
 */
export function ProfileFormDialog({
  triggerLabel,
  title,
  description,
  closeLabel,
  children,
}: {
  triggerLabel: string;
  title: string;
  description?: string;
  closeLabel: string;
  children: (close: () => void, titleId: string) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  // `open` drives the native dialog; jsdom has no showModal/close, the open
  // attribute is enough there.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (!open) {
      if (typeof dialog.close === "function") {
        if (dialog.open) dialog.close();
      } else {
        dialog.removeAttribute("open");
      }
      return;
    }
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    const root = document.documentElement;
    const previousOverflow = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = previousOverflow;
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <>
      <Button
        type="button"
        size="sm"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
        className={cn("inline-flex items-center gap-1.5", primaryButtonClass)}
      >
        <span aria-hidden="true" className="text-base leading-none">+</span>
        {triggerLabel}
      </Button>
      <dialog
        ref={dialogRef}
        className="y360-dialog"
        aria-labelledby={titleId}
        onClose={() => setOpen(false)}
        onClick={(event) => {
          // A click on the dialog element itself is a click on the backdrop.
          if (event.target === event.currentTarget) close();
        }}
      >
        <div className="flex max-h-[min(88dvh,860px)] w-[560px] max-w-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-[0_32px_80px_-32px_rgba(34,31,27,0.45)]">
          <div className="flex items-start justify-between gap-3 border-b border-border px-6 py-5">
            <div>
              <h2 id={titleId} className="font-serif text-xl font-medium text-foreground">
                {title}
              </h2>
              {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
            </div>
            <button
              type="button"
              aria-label={closeLabel}
              onClick={close}
              className={cn(
                "-mr-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground",
                focusRingClass
              )}
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" className="h-4 w-4">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5">{children(close, titleId)}</div>
        </div>
      </dialog>
    </>
  );
}
