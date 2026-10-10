"use client";

import { useEffect, useState } from "react";
import { publicFocusRing } from "@/components/public-top-bar";
import messages from "@/messages/tr.json";
import { cn } from "@/lib/utils";

const t = messages.publicProfile;

const actionClass = cn(
  "inline-flex h-9 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-md border px-3 text-sm font-medium transition-colors",
  publicFocusRing
);

function LinkIcon({ copied }: { copied: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      {copied ? (
        <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <>
          <path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1" strokeLinecap="round" />
          <path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}

function PrintIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <path d="M7 9V4h10v5M7 17H5a1 1 0 0 1-1-1v-5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v5a1 1 0 0 1-1 1h-2" strokeLinejoin="round" />
      <rect x="7" y="14" width="10" height="6" rx="1" />
    </svg>
  );
}

/** Copy link · print. Screen only — hidden in the printed copy. */
export function ShareActions({ url }: { url: string }) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (copyState !== "copied") return;
    const id = setTimeout(() => setCopyState("idle"), 1500);
    return () => clearTimeout(id);
  }, [copyState]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  };

  return (
    <div className="print:hidden">
      <div className="flex flex-col gap-2 min-[400px]:flex-row lg:flex-col">
        <button
          type="button"
          onClick={copy}
          className={cn(actionClass, "border-success text-success hover:bg-success/10")}
        >
          <LinkIcon copied={copyState === "copied"} />
          {copyState === "copied" ? t.copied : t.copyLink}
        </button>
        <button
          type="button"
          onClick={() => window.print()}
          className={cn(actionClass, "border-border bg-muted text-foreground hover:bg-sand")}
        >
          <PrintIcon />
          {t.print}
        </button>
      </div>
      <p aria-live="polite" className="mt-2 text-[13px] text-destructive empty:hidden">
        {copyState === "failed" ? t.copyFailed : ""}
      </p>
    </div>
  );
}
