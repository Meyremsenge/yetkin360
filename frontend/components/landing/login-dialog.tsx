"use client";

import { useEffect, useId, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import messages from "@/messages/tr.json";
import LoginForm from "@/app/giris/form";
import { SealMark } from "@/components/brand/brand-mark";
import { DemoAccountsLink } from "@/components/ui/demo-accounts-link";
import { demoAccountsEnabled } from "@/lib/demo-accounts";

const { loginDialog, home, authLayout } = messages;

/**
 * A link to /giris that, on a plain left click, opens the login form in a
 * modal over the current page instead of navigating. Modifier clicks
 * (new tab), middle clicks and no-JS visits still reach the full /giris page.
 */
export function LoginDialogLink({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!open || !dialog) return;
    if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
    const root = document.documentElement;
    const previousOverflow = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = previousOverflow;
    };
  }, [open]);

  const onTriggerClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    setOpen(true);
  };

  const close = () => dialogRef.current?.close();

  const dialog = (
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
      <div className="relative w-[440px] max-w-full overflow-hidden rounded-xl border border-border bg-card shadow-[0_32px_80px_-32px_rgba(34,31,27,0.45)]">
        <div className="y360-dot-grid flex items-center gap-4 border-b border-border bg-sand/60 px-8 py-6">
          <SealMark className="h-11 w-11 shrink-0" />
          <div>
            <h2 id={titleId} className="font-serif text-2xl font-semibold leading-tight">
              {loginDialog.title}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">{loginDialog.subtitle}</p>
          </div>
        </div>

        <div className="px-8 pb-8 pt-7">
          <LoginForm />

          {demoAccountsEnabled() && <DemoAccountsLink className="mt-5" />}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5 text-sm">
            <p className="text-muted-foreground">
              {loginDialog.noAccount}{" "}
              <Link
                href="/kayit"
                className="font-medium text-success underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success"
              >
                {home.registerLink}
              </Link>
            </p>
            <Link
              href="/sifre-unuttum"
              className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success"
            >
              {authLayout.forgotPasswordLink}
            </Link>
          </div>
        </div>

        {/* Last in DOM so the first focus lands on the e-mail field. */}
        <button
          type="button"
          onClick={close}
          aria-label={loginDialog.close}
          className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-success motion-reduce:transition-none"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </dialog>
  );

  return (
    <>
      <a href="/giris" className={className} onClick={onTriggerClick}>
        {children}
      </a>
      {open ? createPortal(dialog, document.body) : null}
    </>
  );
}
