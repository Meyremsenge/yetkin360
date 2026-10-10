import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import messages from "@/messages/tr.json";
import { VerifiedSeal } from "@/components/ui/verified-seal";
import { BrandLockup, SealMark } from "@/components/brand/brand-mark";
import { ParticleSeal } from "@/components/brand/particle-seal";
import { ChainDemo } from "@/components/landing/chain-demo";
import { LoginDialogLink } from "@/components/landing/login-dialog";

const { home } = messages;

const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success";

const primaryCta = `inline-flex h-12 items-center justify-center gap-2 rounded-md bg-success px-6 text-base font-medium text-background shadow-[0_10px_24px_-12px_rgba(38,84,69,0.7)] transition-[background-color,transform] hover:bg-success/90 active:translate-y-px motion-reduce:transition-none ${focusRing}`;
const outlineCta = `inline-flex h-12 items-center justify-center rounded-md border border-success/40 bg-card px-6 text-base font-medium text-success transition-colors hover:border-success hover:bg-success/10 motion-reduce:transition-none ${focusRing}`;

const personas = [
  { ...home.personas.organization, icon: "organization" as const },
  { ...home.personas.student, icon: "student" as const },
  { ...home.personas.institution, icon: "institution" as const },
];

const PERSONA_ICONS: Record<(typeof personas)[number]["icon"], ReactNode> = {
  student: <path d="M2.5 9.5 12 5l9.5 4.5L12 14zM6.5 11.5V16c1.5 1.6 3.4 2.4 5.5 2.4s4-.8 5.5-2.4v-4.5M21.5 9.5v5" />,
  organization: <path d="M4 21V5.5A1.5 1.5 0 0 1 5.5 4h7A1.5 1.5 0 0 1 14 5.5V21M14 10h4.5a1.5 1.5 0 0 1 1.5 1.5V21M2.5 21h19M7.5 8h3M7.5 12h3M7.5 16h3" />,
  institution: <path d="M3 21h18M4.5 18h15M6 18v-7M10 18v-7M14 18v-7M18 18v-7M3 9.5 12 4l9 5.5z" />,
};

function rise(delayMs: number): CSSProperties {
  return { animationDelay: `${delayMs}ms` };
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={2.25} aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Home() {
  return (
    <div className="y360-landing overflow-x-clip">
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-4 py-5 md:px-8">
        <Link href="/" className={`rounded-md ${focusRing}`}>
          <BrandLockup name={home.title} />
        </Link>
        <nav className="flex items-center gap-2 text-sm md:gap-3">
          <a
            href="#zincir"
            className={`hidden rounded-md px-3 py-2 text-muted-foreground transition-colors hover:text-foreground md:inline-block ${focusRing}`}
          >
            {home.nav.how}
          </a>
          <a
            href="#kimler"
            className={`hidden rounded-md px-3 py-2 text-muted-foreground transition-colors hover:text-foreground md:inline-block ${focusRing}`}
          >
            {home.nav.audience}
          </a>
          <span aria-hidden="true" className="mx-1 hidden h-5 w-px bg-border md:block" />
          <LoginDialogLink
            className={`rounded-md px-3 py-2 font-medium text-foreground transition-colors hover:text-success ${focusRing}`}
          >
            {home.loginLink}
          </LoginDialogLink>
          <Link
            href="/kayit"
            className={`inline-flex h-9 items-center rounded-md border border-success/40 bg-card px-4 font-medium text-success transition-colors hover:border-success hover:bg-success hover:text-background motion-reduce:transition-none ${focusRing}`}
          >
            {home.registerLink}
          </Link>
        </nav>
      </header>

      <main>
        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-6 px-4 pb-16 pt-6 md:px-8 lg:min-h-[calc(100vh-84px)] lg:grid-cols-[11fr_9fr] lg:gap-8 lg:pb-20">
          <div>
            <p
              className="y360-rise inline-flex items-center gap-2.5 rounded-full border border-border bg-card px-3.5 py-1.5 text-[13px] text-muted-foreground"
              style={rise(0)}
            >
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-success" />
              {home.eyebrow}
            </p>

            <h1
              className="y360-rise mt-7 font-serif text-[44px] font-semibold leading-[1.04] tracking-tight md:text-6xl lg:text-[68px]"
              style={rise(90)}
            >
              {home.heroTitleLead}{" "}
              <span className="relative inline-block whitespace-nowrap text-success">
                {home.heroTitleAccent}
                <svg
                  aria-hidden="true"
                  viewBox="0 0 300 14"
                  preserveAspectRatio="none"
                  className="y360-underline absolute -bottom-2 left-0 h-3.5 w-full md:-bottom-3"
                >
                  <path
                    d="M3 10 C 70 3, 160 2, 297 7"
                    fill="none"
                    stroke="#B98330"
                    strokeWidth="4.5"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
            </h1>

            <p className="y360-rise mt-8 max-w-xl text-lg leading-8 text-muted-foreground md:text-xl md:leading-8" style={rise(180)}>
              {home.heroDescription}
            </p>

            <div className="y360-rise mt-9 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4" style={rise(270)}>
              <Link href="/kayit" className={primaryCta}>
                {home.registerLink}
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
              <a href="#zincir" className={outlineCta}>
                {home.secondaryCta}
              </a>
            </div>

            <ul className="y360-rise mt-9 flex flex-wrap gap-x-6 gap-y-2.5 text-sm text-foreground" style={rise(360)}>
              {home.heroPoints.map((point) => (
                <li key={point} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success/10 text-success">
                    <CheckIcon className="h-3 w-3" />
                  </span>
                  {point}
                </li>
              ))}
            </ul>

            <p className="y360-rise mt-8 font-mono text-[13px] text-muted-foreground" style={rise(450)}>
              {home.tagline}
            </p>
          </div>

          {/* Scene: scattered claims gather into one seal. */}
          <div className="mx-auto w-full max-w-[560px]">
            <div className="relative">
              <div
                aria-hidden="true"
                className="y360-dot-grid absolute inset-[6%] rounded-full [mask-image:radial-gradient(circle,black_45%,transparent_72%)]"
              />
              <ParticleSeal className="aspect-square w-full" particles={5200} />
              <div
                className="y360-fade pointer-events-none absolute bottom-[1%] left-1/2 flex -translate-x-1/2 items-center gap-2.5 whitespace-nowrap rounded-full border border-border bg-card/95 py-1.5 pl-1.5 pr-4 text-[13px] shadow-[0_10px_30px_-18px_rgba(34,31,27,0.5)]"
                style={rise(2600)}
              >
                <VerifiedSeal size="sm" />
                <span className="font-medium text-foreground">{home.sceneBadge}</span>
              </div>
            </div>
            <p className="mt-4 text-center text-sm text-muted-foreground">{home.sceneCaption}</p>
            <p className="mt-1 hidden text-center font-mono text-xs text-muted-foreground/80 lg:block">
              {home.sceneHint}
            </p>
          </div>
        </section>

        {/* ── Chain ────────────────────────────────────────────────────── */}
        <section id="zincir" className="scroll-mt-6 border-y border-border bg-sand/60">
          <div className="mx-auto max-w-6xl px-4 py-20 md:px-8 md:py-24">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-[0.14em] text-success">{home.chainEyebrow}</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold md:text-[40px] md:leading-tight">{home.chainTitle}</h2>
              <p className="mt-4 text-lg leading-8 text-muted-foreground">{home.chainLead}</p>
            </div>
            <ChainDemo />
          </div>
        </section>

        {/* ── Claim vs verified ────────────────────────────────────────── */}
        <section className="mx-auto max-w-6xl px-4 py-20 md:px-8 md:py-24">
          <h2 className="max-w-2xl font-serif text-3xl font-semibold md:text-[40px] md:leading-tight">
            {home.comparisonTitle}
          </h2>

          <div className="relative mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 md:gap-10">
            <article className="rounded-xl border border-dashed border-muted-foreground/30 bg-background p-6 md:p-8">
              <p className="font-mono text-xs text-muted-foreground">{home.comparison.claimLabel}</p>
              <p className="mt-5 font-serif text-xl leading-snug text-muted-foreground md:text-2xl">
                {home.comparison.cvLine}
              </p>
              <p className="mt-6 flex items-center gap-2.5 text-sm text-muted-foreground">
                <span className="flex h-6 w-6 items-center justify-center rounded-full border border-muted-foreground/30 font-mono text-xs">
                  ?
                </span>
                {home.comparison.whoSays}
              </p>
              <p className="mt-6 border-t border-dashed border-muted-foreground/25 pt-5 text-[15px] text-muted-foreground">
                {home.comparisonClaim}
              </p>
            </article>

            <span
              aria-hidden="true"
              className="absolute left-1/2 top-1/2 hidden h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-card text-success shadow-sm md:flex"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>

            <article className="relative rounded-xl border border-success/30 bg-card p-6 shadow-[0_30px_70px_-45px_rgba(38,84,69,0.6)] md:p-8">
              <p className="font-mono text-xs text-success">{home.comparison.verifiedLabel}</p>
              <div className="mt-5 flex items-start justify-between gap-4">
                <div>
                  <p className="font-serif text-xl font-semibold leading-snug md:text-2xl">{home.comparison.recordSkill}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{home.comparison.recordContext}</p>
                </div>
                <SealMark className="h-14 w-14 shrink-0 -rotate-6" />
              </div>
              <ul className="mt-6 flex flex-wrap gap-2">
                {home.comparison.recordMeta.map((meta) => (
                  <li
                    key={meta}
                    className="inline-flex items-center gap-1.5 rounded-full border border-success/25 bg-success/10 px-3 py-1 text-[13px] text-success"
                  >
                    <CheckIcon className="h-3.5 w-3.5" />
                    {meta}
                  </li>
                ))}
              </ul>
              <p className="mt-6 border-t border-border pt-5 text-[15px] text-foreground">{home.comparisonVerified}</p>
            </article>
          </div>
        </section>

        {/* ── Personas ─────────────────────────────────────────────────── */}
        <section id="kimler" className="scroll-mt-6 border-t border-border">
          <div className="mx-auto max-w-6xl px-4 py-20 md:px-8 md:py-24">
            <h2 className="font-serif text-3xl font-semibold md:text-[40px] md:leading-tight">{home.personasTitle}</h2>
            <p className="mt-3 text-lg text-muted-foreground">{home.personasLead}</p>

            <div className="mt-12 grid gap-5 md:grid-cols-3 md:gap-6">
              {personas.map((persona) => (
                <article
                  key={persona.title}
                  className="group rounded-xl border border-border bg-card p-6 transition-[border-color,transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-success/40 hover:shadow-[0_24px_50px_-36px_rgba(38,84,69,0.6)] motion-reduce:transition-none motion-reduce:hover:translate-y-0 md:p-7"
                >
                  <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-sand text-success transition-colors group-hover:bg-success group-hover:text-background motion-reduce:transition-none">
                    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      {PERSONA_ICONS[persona.icon]}
                    </svg>
                  </span>
                  <h3 className="mt-5 font-serif text-2xl font-semibold">{persona.title}</h3>
                  <p className="mt-2 text-[15px] leading-6 text-muted-foreground">{persona.description}</p>
                  <ul className="mt-5 space-y-2.5 border-t border-border pt-5">
                    {persona.points.map((point) => (
                      <li key={point} className="flex items-start gap-2.5 text-sm text-foreground">
                        <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        {point}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── Closing call to action ───────────────────────────────────── */}
        <section className="mx-auto max-w-6xl px-4 pb-20 md:px-8 md:pb-24">
          <div className="relative overflow-hidden rounded-2xl bg-success px-6 py-12 text-background md:px-14 md:py-16">
            <SealMark className="pointer-events-none absolute -bottom-24 -right-16 h-80 w-80 rotate-12 text-background/[0.08] md:-bottom-28 md:right-6 md:h-96 md:w-96" />
            <div className="relative max-w-2xl">
              <h2 className="font-serif text-3xl font-semibold leading-tight md:text-[44px] md:leading-[1.1]">
                {home.closing.title}
              </h2>
              <p className="mt-5 text-lg leading-8 text-background/85">{home.closing.text}</p>
              <div className="mt-9 flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
                <Link
                  href="/kayit"
                  className="inline-flex h-12 items-center justify-center rounded-md bg-background px-7 text-base font-medium text-success transition-colors hover:bg-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-background motion-reduce:transition-none"
                >
                  {home.registerLink}
                </Link>
                <p className="text-[15px] text-background/85">
                  {home.closing.loginPrompt}{" "}
                  <LoginDialogLink className="rounded-sm font-medium text-background underline decoration-background/40 underline-offset-4 hover:decoration-background focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-background">
                    {home.loginLink}
                  </LoginDialogLink>
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-8">
          <div className="flex items-center gap-3">
            <SealMark className="h-5 w-5" />
            <p>{home.footerNote}</p>
          </div>
          <nav className="flex gap-5">
            <a href="#zincir" className={`rounded-sm hover:text-foreground ${focusRing}`}>
              {home.nav.how}
            </a>
            <a href="#kimler" className={`rounded-sm hover:text-foreground ${focusRing}`}>
              {home.nav.audience}
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
