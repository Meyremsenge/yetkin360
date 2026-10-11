import Link from "next/link";
import messages from "@/messages/tr.json";

/** Anchor of the demo account list rendered by the login form. */
export const DEMO_ACCOUNTS_ANCHOR = "demo-hesaplar";

/**
 * Points a visitor (typically a jury member) from the login dialog or the
 * register page to the seeded demo accounts, so they do not explore an empty
 * freshly registered account.
 */
export function DemoAccountsLink({ className = "" }: { className?: string }) {
  const demo = messages.giris.demo;
  return (
    <Link
      href={`/giris#${DEMO_ACCOUNTS_ANCHOR}`}
      className={`group flex items-center justify-between gap-3 rounded-md border border-success/30 bg-success/5 px-4 py-3 transition-colors hover:border-success/60 hover:bg-success/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success motion-reduce:transition-none ${className}`}
    >
      <span>
        <span className="block text-sm font-semibold text-success">{demo.cta}</span>
        <span className="mt-0.5 block text-[13px] text-muted-foreground">{demo.ctaHint}</span>
      </span>
      <svg
        viewBox="0 0 24 24"
        className="h-5 w-5 shrink-0 text-success transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        aria-hidden="true"
      >
        <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </Link>
  );
}
