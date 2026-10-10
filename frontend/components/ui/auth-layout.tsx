import Link from "next/link";
import messages from "@/messages/tr.json";
import { BrandLockup } from "@/components/brand/brand-mark";
import { ParticleSeal } from "@/components/brand/particle-seal";

const { home, authLayout } = messages;

const CHAIN_STEPS = [
  { label: home.chain.claim, completed: false },
  { label: home.chain.evidence, completed: false },
  { label: home.chain.attestation, completed: false },
  { label: home.chain.verified, completed: true },
];

interface AuthLayoutProps {
  brandSentence: string;
  links?: { href: string; label: string }[];
  children: React.ReactNode;
}

export function AuthLayout({ brandSentence, links, children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[2fr_3fr] lg:grid-cols-[5fr_6fr]">
      <div className="relative flex flex-col gap-6 overflow-hidden border-b border-border bg-sand p-6 md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r md:p-10 lg:p-12">
        <BrandLockup name={home.title} />

        <div className="relative mx-auto hidden w-full max-w-[340px] flex-1 items-center md:flex lg:max-w-[400px]">
          <div
            aria-hidden="true"
            className="y360-dot-grid absolute inset-[4%] rounded-full [mask-image:radial-gradient(circle,black_40%,transparent_70%)]"
          />
          <ParticleSeal className="aspect-square w-full" particles={3200} />
        </div>

        <div>
          <p className="font-serif text-2xl font-semibold leading-snug md:text-[28px] md:leading-tight">
            {brandSentence}
          </p>
          <p className="mt-3 hidden text-sm text-muted-foreground md:block">{authLayout.panelCaption}</p>
        </div>

        {/* Compact chain: one line of chips joined by arrows; last step sealed. */}
        <div className="hidden border-t border-foreground/10 pt-5 md:block">
          <ol aria-label={home.chainTitle} className="flex flex-wrap items-center gap-x-1.5 gap-y-2">
            {CHAIN_STEPS.map((step, index) => (
              <li key={step.label} className="flex items-center gap-1.5">
                {index > 0 ? (
                  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-muted-foreground/60" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                    <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : null}
                <span
                  className={
                    step.completed
                      ? "inline-flex items-center gap-1.5 rounded-full bg-success px-3 py-1 text-[13px] font-medium text-background"
                      : "inline-flex items-center rounded-full border border-foreground/15 bg-card/70 px-3 py-1 text-[13px] text-foreground"
                  }
                >
                  {step.completed ? (
                    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                      <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : null}
                  <span className="whitespace-nowrap">{step.label}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>

        {links && links.length > 0 && (
          <nav aria-label="Auth bağlantıları" className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-sm font-medium text-foreground underline decoration-foreground/30 underline-offset-4 transition-colors hover:text-success hover:decoration-success focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        )}
      </div>
      <div className="flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
