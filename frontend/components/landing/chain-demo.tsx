"use client";

import { useEffect, useRef, useState } from "react";
import messages from "@/messages/tr.json";
import { cn } from "@/lib/utils";
import { SealMark } from "@/components/brand/brand-mark";
import { useReducedMotion } from "@/components/brand/use-reduced-motion";

const { home } = messages;
const { demo } = home;

const STEPS = [
  { key: "claim", label: home.chain.claim, ...demo.steps.claim },
  { key: "evidence", label: home.chain.evidence, ...demo.steps.evidence },
  { key: "attestation", label: home.chain.attestation, ...demo.steps.attestation },
  { key: "verified", label: home.chain.verified, ...demo.steps.verified },
] as const;

const STEP_MS = 2000;
const HOLD_LAST_MS = 3600;

const STATUS_CLASS = [
  "border-border bg-muted text-muted-foreground",
  "border-warning/30 bg-warning/10 text-warning",
  "border-warning/30 bg-warning/10 text-warning",
  "border-success/30 bg-success/10 text-success",
] as const;

const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success";

function Placeholder({ text }: { text: string }) {
  return (
    <div className="flex min-h-[142px] items-center justify-center rounded-lg border border-dashed border-border px-4 text-sm text-muted-foreground/80">
      {text}
    </div>
  );
}

/**
 * "How the chain works" showcase: one sample record fills up step by step
 * (claim → evidence → attestation → stamped seal). Auto-advances only while
 * visible, never under reduced motion, and pauses on hover/focus or via the
 * explicit pause button (WCAG 2.2.2).
 */
export function ChainDemo() {
  const rootRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  // Until the visitor picks a step: first step, or the finished record when
  // motion is reduced (no autoplay to reveal it).
  const [picked, setPicked] = useState<number | null>(null);
  const active = picked ?? (reduced ? STEPS.length - 1 : 0);
  const setActive = (index: number) => setPicked(index);
  const [visible, setVisible] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(([entry]) => setVisible(!!entry?.isIntersecting), {
      threshold: 0.35,
    });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  const autoplay = visible && !hovering && !paused && !reduced;
  const delay = active === STEPS.length - 1 ? HOLD_LAST_MS : STEP_MS;

  useEffect(() => {
    if (!autoplay) return;
    const timer = window.setTimeout(() => setPicked((active + 1) % STEPS.length), delay);
    return () => window.clearTimeout(timer);
  }, [autoplay, active, delay]);

  return (
    <div
      ref={rootRef}
      className="grid grid-cols-1 gap-10 lg:grid-cols-[5fr_7fr] lg:gap-16"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onFocus={() => setHovering(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setHovering(false);
      }}
    >
      {/* Stepper */}
      <div>
        <ol aria-label={demo.stepsLabel} className="relative">
          {STEPS.map((step, index) => {
            const done = index < active;
            const current = index === active;
            const last = index === STEPS.length - 1;
            return (
              <li key={step.key} className="relative pb-2 last:pb-0">
                {!last ? (
                  <span
                    aria-hidden="true"
                    className="absolute left-[19px] top-11 h-[calc(100%-36px)] w-px bg-border"
                  >
                    <span
                      className={cn(
                        "absolute inset-x-0 top-0 bg-success transition-[height] duration-500 ease-in-out motion-reduce:transition-none",
                        done ? "h-full" : "h-0"
                      )}
                    />
                  </span>
                ) : null}
                <button
                  type="button"
                  onClick={() => setActive(index)}
                  aria-current={current ? "step" : undefined}
                  className={cn(
                    "group flex w-full items-start gap-4 rounded-lg p-2 text-left transition-colors motion-reduce:transition-none",
                    current ? "bg-card shadow-[0_8px_24px_-16px_rgba(34,31,27,0.35)]" : "hover:bg-card/60",
                    focusRing
                  )}
                >
                  <span
                    className={cn(
                      "flex h-10 w-10 shrink-0 items-center justify-center rounded-full border font-mono text-sm transition-colors duration-300 motion-reduce:transition-none",
                      done && "border-success bg-success text-background",
                      current && !last && "border-success bg-background text-success ring-4 ring-success/15",
                      current && last && "border-success bg-success text-background ring-4 ring-success/20",
                      !done && !current && "border-border bg-background text-muted-foreground"
                    )}
                  >
                    {done || (current && last) ? (
                      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.25} aria-hidden="true">
                        <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </span>
                  <span className="min-w-0 flex-1 pt-1">
                    <span className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                      <span
                        className={cn(
                          "font-serif text-xl font-semibold transition-colors motion-reduce:transition-none",
                          current || done ? "text-foreground" : "text-muted-foreground",
                          last && current && "text-success"
                        )}
                      >
                        {step.label}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">{step.actor}</span>
                    </span>
                    <span
                      className={cn(
                        "mt-1 block text-[15px] leading-6 text-muted-foreground transition-opacity motion-reduce:transition-none",
                        current ? "opacity-100" : "opacity-70"
                      )}
                    >
                      {step.text}
                    </span>
                    {current && autoplay ? (
                      <span aria-hidden="true" className="mt-3 block h-0.5 overflow-hidden rounded-full bg-border">
                        <span
                          key={active}
                          className="y360-progress block h-full bg-success"
                          style={{ animationDuration: `${delay}ms` }}
                        />
                      </span>
                    ) : null}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>

        {!reduced ? (
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            aria-pressed={paused}
            className={cn(
              "mt-5 inline-flex items-center gap-2 rounded-md px-2 py-1 font-mono text-xs text-muted-foreground transition-colors hover:text-foreground motion-reduce:transition-none",
              focusRing
            )}
          >
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="currentColor" aria-hidden="true">
              {paused ? <path d="M8 5.5v13l10-6.5z" /> : <path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" />}
            </svg>
            {paused ? demo.play : demo.pause}
          </button>
        ) : null}
      </div>

      {/* Sample record — first on small screens so autoplay stays in view. */}
      <div className="relative order-first lg:order-none">
        <div
          className="relative overflow-hidden rounded-xl border border-border bg-card shadow-[0_30px_70px_-40px_rgba(34,31,27,0.45)]"
        >
          <div className="flex items-center justify-between gap-4 border-b border-border px-6 py-4 md:px-8">
            <span className="font-mono text-xs text-muted-foreground">{demo.sample}</span>
            <span
              key={active}
              className={cn(
                "y360-step-in inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
                STATUS_CLASS[active]
              )}
            >
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
              {demo.status[STEPS[active].key]}
            </span>
          </div>

          <div className="space-y-6 px-6 py-6 md:px-8 md:py-7">
            <div>
              {/* Right padding leaves room for the stamped seal. */}
              <div className="pr-24 md:pr-28">
                <h3 className="font-serif text-2xl font-semibold leading-tight md:text-[28px]">{demo.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{demo.org}</p>
              </div>
              <ul className="mt-4 flex flex-wrap gap-2">
                {demo.skills.map((skill) => (
                  <li
                    key={skill}
                    className={cn(
                      "rounded-full border px-3 py-1 text-[13px] transition-colors duration-500 motion-reduce:transition-none",
                      active === STEPS.length - 1
                        ? "border-success/30 bg-success/10 text-success"
                        : "border-border bg-background text-foreground"
                    )}
                  >
                    {skill}
                  </li>
                ))}
              </ul>
              <p className="mt-5 border-l-2 border-border pl-4 text-[15px] italic leading-6 text-muted-foreground">
                {demo.claimText}
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="min-h-[170px]">
                <p className="mb-2 text-xs font-medium text-muted-foreground">{demo.evidenceTitle}</p>
                {active >= 1 ? (
                  <ul className="y360-step-in space-y-2">
                    {demo.evidenceItems.map((item, i) => (
                      <li
                        key={item}
                        className="flex items-center gap-3 rounded-lg border border-border bg-background px-3 py-2.5 text-sm"
                      >
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-sand text-foreground">
                          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden="true">
                            {i === 0 ? (
                              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h4" strokeLinecap="round" strokeLinejoin="round" />
                            ) : (
                              <path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1" strokeLinecap="round" strokeLinejoin="round" />
                            )}
                          </svg>
                        </span>
                        <span className="truncate font-mono text-[13px]">{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Placeholder text={demo.pendingEvidence} />
                )}
              </div>

              <div className="min-h-[170px]">
                <p className="mb-2 text-xs font-medium text-muted-foreground">{demo.attestationTitle}</p>
                {active >= 2 ? (
                  <figure className="y360-step-in rounded-lg border border-border bg-background px-4 py-3">
                    <blockquote className="font-serif text-[15px] leading-6">“{demo.quote}”</blockquote>
                    <figcaption className="mt-2 text-xs text-muted-foreground">{demo.quoteBy}</figcaption>
                  </figure>
                ) : (
                  <Placeholder text={demo.pendingAttestation} />
                )}
              </div>
            </div>
          </div>

          <div
            className={cn(
              "flex items-center justify-between gap-4 border-t px-6 py-4 transition-colors duration-500 md:px-8 motion-reduce:transition-none",
              active === STEPS.length - 1 ? "border-success/20 bg-success/[0.07]" : "border-border bg-background"
            )}
          >
            <span
              className={cn(
                "font-mono text-xs",
                active === STEPS.length - 1 ? "text-success" : "text-muted-foreground/80"
              )}
            >
              {active === STEPS.length - 1 ? demo.registry : demo.pendingSeal}
            </span>
            {active === STEPS.length - 1 ? (
              <span className="font-mono text-xs text-success">{demo.verifiedOn}</span>
            ) : null}
          </div>
        </div>

        {active === STEPS.length - 1 ? (
          <div
            key="stamp"
            className="y360-stamp pointer-events-none absolute right-4 top-[64px] rounded-full bg-card/85 p-1 md:right-8 md:top-[76px]"
          >
            <SealMark label={demo.sealLabel} className="h-20 w-20 drop-shadow-[0_6px_12px_rgba(38,84,69,0.25)] md:h-24 md:w-24" />
          </div>
        ) : null}
      </div>
    </div>
  );
}
