"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PublicCertificate } from "@/lib/api/public";
import { publicFocusRing } from "@/components/public-top-bar";
import messages from "@/messages/tr.json";
import { cn } from "@/lib/utils";
import { formatMonthYear } from "./format";

const t = messages.publicProfile;
const kindLabels = t.certificateKind as Record<string, string>;
const providerLabels = messages.certificateProviders as Record<string, string>;

function CertificateCard({ cert }: { cert: PublicCertificate }) {
  const confirmed = cert.badge === "COORDINATOR_CONFIRMED";
  const source = confirmed
    ? cert.provider && cert.provider !== "UNKNOWN"
      ? providerLabels[cert.provider] ?? null
      : null
    : cert.issuer;

  return (
    <li
      className={cn(
        "flex w-[272px] shrink-0 snap-start flex-col rounded-lg p-5 sm:w-[288px] print:w-auto print:break-inside-avoid",
        confirmed
          ? "border border-success/40 bg-card shadow-[inset_0_0_0_4px_hsl(var(--success)/0.06)]"
          : "border border-dashed border-border bg-sand/40"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">{kindLabels[cert.kind]}</span>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
            confirmed ? "border-success/40 bg-success/10 text-success" : "border-dashed border-border bg-card text-muted-foreground"
          )}
        >
          {confirmed ? (
            <svg aria-hidden="true" viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M3.5 8.5l3 3 6-7" />
            </svg>
          ) : null}
          {confirmed ? t.confirmedBadge : t.selfDeclared}
        </span>
      </div>

      <h4 className="mt-3 font-serif text-[17px] font-semibold leading-snug text-foreground [overflow-wrap:anywhere]">{cert.title}</h4>
      {source ? <p className="mt-1 text-sm text-foreground">{source}</p> : null}

      <dl className="mt-3 space-y-1 text-[13px] text-muted-foreground">
        {cert.issued_on ? (
          <div className="font-mono tabular-nums">
            <dt className="sr-only">{messages.profil.portfolioIssuedOnLabel}</dt>
            <dd>{formatMonthYear(cert.issued_on)}</dd>
          </div>
        ) : null}
        {cert.credential_id ? (
          <div className="flex gap-1.5">
            <dt>{t.credentialLabel}:</dt>
            <dd className="font-mono text-foreground [overflow-wrap:anywhere]">{cert.credential_id}</dd>
          </div>
        ) : null}
      </dl>

      <div className="mt-auto pt-4">
        {confirmed && cert.verify_url ? (
          <a
            href={cert.verify_url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn("text-sm font-medium text-success underline-offset-4 hover:underline", publicFocusRing)}
          >
            {t.officialVerify} ↗
          </a>
        ) : null}
        {!confirmed && cert.link_url && cert.link_host ? (
          <p className="text-[13px]">
            <a
              href={cert.link_url}
              target="_blank"
              rel="nofollow ugc noopener noreferrer"
              className={cn("font-mono text-foreground underline-offset-4 hover:underline", publicFocusRing)}
            >
              {cert.link_host} ↗
            </a>
            <span className="ml-2 text-muted-foreground">{t.unverifiedLinkNote}</span>
          </p>
        ) : null}
      </div>
    </li>
  );
}

function ArrowButton({ direction, disabled, onClick }: { direction: "prev" | "next"; disabled: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={direction === "prev" ? t.scrollPrev : t.scrollNext}
      className={cn(
        "hidden h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-foreground transition-colors hover:border-success hover:text-success disabled:pointer-events-none disabled:opacity-35 md:inline-flex print:hidden",
        publicFocusRing
      )}
    >
      <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <path d={direction === "prev" ? "M10 3.5L5.5 8l4.5 4.5" : "M6 3.5L10.5 8 6 12.5"} />
      </svg>
    </button>
  );
}

/**
 * One horizontally scrolling group (scroll-snap). Swipe on touch, arrow keys once the
 * list is focused, arrow buttons on desktop. Prints as a wrapped grid.
 */
function CertificateRow({ title, note, certificates }: { title: string; note?: string; certificates: PublicCertificate[] }) {
  const listRef = useRef<HTMLUListElement>(null);
  const [edges, setEdges] = useState({ atStart: true, atEnd: true });

  const measure = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    setEdges({ atStart: el.scrollLeft <= 4, atEnd: el.scrollLeft + el.clientWidth >= el.scrollWidth - 4 });
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure, certificates.length]);

  const scroll = (direction: 1 | -1) => {
    const el = listRef.current;
    if (!el) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el.scrollBy?.({ left: direction * Math.max(el.clientWidth * 0.8, 280), behavior: reduce ? "auto" : "smooth" });
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLUListElement>) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      scroll(1);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      scroll(-1);
    }
  };

  const scrollable = !(edges.atStart && edges.atEnd);

  return (
    <div className="mt-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h3 className="text-[15px] font-semibold text-foreground">
            {title} <span className="font-mono text-xs font-normal text-muted-foreground">({certificates.length})</span>
          </h3>
          {note ? <p className="mt-0.5 text-[13px] text-muted-foreground">{note}</p> : null}
        </div>
        {scrollable ? (
          <div className="flex shrink-0 gap-2">
            <ArrowButton direction="prev" disabled={edges.atStart} onClick={() => scroll(-1)} />
            <ArrowButton direction="next" disabled={edges.atEnd} onClick={() => scroll(1)} />
          </div>
        ) : null}
      </div>
      <ul
        ref={listRef}
        tabIndex={0}
        aria-label={t.certificatesRegionLabel.replace("{group}", title)}
        onScroll={measure}
        onKeyDown={onKeyDown}
        className={cn(
          "-mx-1 mt-3 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth px-1 pb-3 motion-reduce:scroll-auto",
          "[scrollbar-width:thin] print:grid print:grid-cols-2 print:overflow-visible",
          publicFocusRing
        )}
      >
        {certificates.map((cert, i) => (
          <CertificateCard key={`${cert.title}-${i}`} cert={cert} />
        ))}
      </ul>
    </div>
  );
}

/** Public "Sertifikalar": coordinator-confirmed first, self-declared in a separate, seal-free row. */
export function CertificateStrip({ certificates }: { certificates: PublicCertificate[] }) {
  const confirmed = certificates.filter((c) => c.badge === "COORDINATOR_CONFIRMED");
  const declared = certificates.filter((c) => c.badge !== "COORDINATOR_CONFIRMED");

  return (
    <>
      {confirmed.length > 0 ? <CertificateRow title={t.certificatesConfirmedTitle} certificates={confirmed} /> : null}
      {declared.length > 0 ? (
        <CertificateRow title={t.certificatesSelfTitle} note={t.certificatesSelfNote} certificates={declared} />
      ) : null}
    </>
  );
}
