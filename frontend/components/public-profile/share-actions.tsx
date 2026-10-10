"use client";

import { useEffect, useId, useState } from "react";
import { publicFocusRing } from "@/components/public-top-bar";
import messages from "@/messages/tr.json";
import { cn } from "@/lib/utils";
import { QrCode } from "./qr-code";

const t = messages.publicProfile;

const actionClass = cn(
  "inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors",
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

function QrIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <rect x="4" y="4" width="6" height="6" rx="1" />
      <rect x="14" y="4" width="6" height="6" rx="1" />
      <rect x="4" y="14" width="6" height="6" rx="1" />
      <path d="M14 14h2v2h-2zM18 18h2v2h-2zM14 18h2M18 14h2" strokeLinecap="round" />
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

/** Copy link · QR · print. Screen only — hidden in the printed copy. */
export function ShareActions({ url, name }: { url: string; name: string }) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const [qrOpen, setQrOpen] = useState(false);
  const qrPanelId = useId();

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
      <div className="flex flex-wrap items-center gap-2">
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
          onClick={() => setQrOpen((open) => !open)}
          aria-expanded={qrOpen}
          aria-controls={qrPanelId}
          className={cn(actionClass, "border-border bg-muted text-foreground hover:bg-sand")}
        >
          <QrIcon />
          {t.showQr}
        </button>
        <button
          type="button"
          onClick={() => window.print()}
          className={cn(actionClass, "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground")}
        >
          <PrintIcon />
          {t.print}
        </button>
      </div>
      <p aria-live="polite" className="mt-2 min-h-[1.25rem] text-[13px] text-destructive">
        {copyState === "failed" ? t.copyFailed : ""}
      </p>
      {qrOpen ? (
        <div
          id={qrPanelId}
          className="y360-step-in mt-1 flex max-w-sm items-center gap-4 rounded-lg border border-border bg-card p-4"
        >
          <QrCode value={url} label={t.qrLabel.replace("{name}", name)} className="h-28 w-28 shrink-0 rounded" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">{t.qrTitle}</p>
            <p className="mt-1 text-[13px] text-muted-foreground">{t.qrHint}</p>
            <button
              type="button"
              onClick={() => setQrOpen(false)}
              className={cn("mt-3 text-[13px] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline", publicFocusRing)}
            >
              {t.close}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
