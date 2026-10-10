"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPublicProfile } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { VerifiedSeal } from "@/components/ui/verified-seal";
import { PublicTopBar, publicFocusRing } from "@/components/public-top-bar";
import { SealMark } from "@/components/brand/brand-mark";
import messages from "@/messages/tr.json";

const t = messages.publicProfile;
const claimTypeLabels = messages.calismalar.claimType as Record<string, string>;

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function formatPeriod(start: string | null, end: string | null): string | null {
  if (!start && !end) return null;
  return `${start ? formatDate(start) : "-"} – ${end ? formatDate(end) : "-"}`;
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toLocaleUpperCase("tr-TR"))
    .join("");
}

const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";

function ProfileSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label={t.loadingLabel}>
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="h-16 w-16 animate-pulse rounded-full bg-muted motion-reduce:animate-none" />
        <div className="space-y-2">
          <div className={`h-8 w-56 ${pulse}`} />
          <div className={`h-4 w-32 ${pulse}`} />
        </div>
      </div>
      <div className="mt-8 border-t border-border pt-8">
        <div className={`h-6 w-52 ${pulse}`} />
        <div className="mt-6 space-y-8 border-l border-border pl-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="space-y-2">
              <div className={`h-5 w-64 ${pulse}`} />
              <div className={`h-4 w-40 ${pulse}`} />
              <div className={`h-3 w-48 ${pulse}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function NotFoundState() {
  const v = messages.publicVerification;
  return (
    <div className="rounded-lg border border-border bg-card p-6 md:p-12">
      <div
        aria-hidden="true"
        className="mb-6 h-24 w-24 rounded-full border border-dashed border-muted-foreground"
      />
      <h1 className="font-serif text-2xl font-medium">{t.notFound}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{v.notFoundDescription}</p>
      <Link
        href="/"
        className={`mt-6 inline-flex h-10 items-center rounded-md bg-muted px-4 text-sm font-medium text-foreground hover:bg-muted/80 ${publicFocusRing}`}
      >
        {v.backHome}
      </Link>
    </div>
  );
}

export default function PublicProfilePage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  const { data: profile, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["publicProfile", slug],
    queryFn: () => getPublicProfile(slug),
  });

  return (
    <div className="min-h-screen bg-background">
      <PublicTopBar label={t.topBarLabel} />

      <main className="mx-auto max-w-[800px] px-4 pb-16 pt-6 md:pt-10">
        {isLoading ? (
          <ProfileSkeleton />
        ) : isError ? (
          error instanceof ApiError && error.status === 404 ? (
            <NotFoundState />
          ) : (
            <Alert variant="error">
              <p>{error instanceof NetworkError ? error.message : messages.errors.generic}</p>
              <div className="mt-3">
                <Button variant="secondary" size="sm" onClick={() => refetch()}>
                  {messages.publicVerification.retry}
                </Button>
              </div>
            </Alert>
          )
        ) : profile ? (
          <>
            <header className="relative overflow-hidden rounded-2xl border border-border bg-sand/70 p-6 md:p-8">
              <SealMark className="pointer-events-none absolute -right-10 -top-10 h-52 w-52 rotate-12 text-success/[0.07]" />
              <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center">
                <span
                  aria-hidden="true"
                  className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-success font-serif text-2xl font-semibold text-background ring-4 ring-background"
                >
                  {initials(profile.display_name)}
                </span>
                <div className="min-w-0">
                  <p className="font-mono text-xs text-success">{t.eyebrow}</p>
                  <h1 className="mt-1 font-serif text-[34px] font-semibold leading-tight md:text-[40px]">
                    {profile.display_name}
                  </h1>
                  <p className="mt-3 inline-flex items-center gap-2 rounded-full border border-success/25 bg-card px-3 py-1 text-sm tabular-nums text-success">
                    <SealMark className="h-4 w-4" />
                    {t.experienceCount.replace("{n}", String(profile.verified_experiences.length))}
                  </p>
                </div>
              </div>
            </header>

            <section className="mt-10">
              <h2 className="font-serif text-2xl font-semibold">{t.timelineTitle}</h2>

              {profile.verified_experiences.length === 0 ? (
                <div className="mt-6 flex items-center gap-5 rounded-xl border border-dashed border-border p-6">
                  <SealMark className="h-12 w-12 shrink-0 text-muted-foreground/30" />
                  <div>
                    <p className="text-base font-semibold first-letter:uppercase">{t.empty}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{t.emptyHint}</p>
                  </div>
                </div>
              ) : (
                <ol className="relative mt-6 space-y-4 before:absolute before:bottom-6 before:left-[19px] before:top-6 before:w-px before:bg-border">
                  {profile.verified_experiences.map((exp) => {
                    const period = formatPeriod(exp.started_on_snapshot, exp.ended_on_snapshot);
                    const claimLabel = claimTypeLabels[exp.claim_type];
                    return (
                      <li key={exp.id} className="relative flex gap-4">
                        <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-success/25 bg-background">
                          <VerifiedSeal size="sm" label={t.sealLabel} />
                        </span>
                        <div className="min-w-0 flex-1 rounded-xl border border-border bg-card p-5 transition-colors hover:border-success/40">
                          <h3 className="font-serif text-xl font-semibold">{exp.role_snapshot}</h3>
                          <p className="mt-1 text-[15px] text-foreground">{exp.organization_name_snapshot}</p>
                          {(period || claimLabel) && (
                            <p className="mt-3 flex flex-wrap items-center gap-2 text-[13px] tabular-nums text-muted-foreground">
                              {period ? <span className="font-mono text-xs">{period}</span> : null}
                              {claimLabel ? (
                                <span className="rounded-full border border-border bg-background px-2 py-0.5">
                                  {claimLabel}
                                </span>
                              ) : null}
                            </p>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ol>
              )}
            </section>

            <aside className="mt-12 flex flex-col gap-4 rounded-xl border border-border bg-card p-5 sm:flex-row sm:items-center sm:justify-between md:p-6">
              <div className="flex items-start gap-3">
                <SealMark className="mt-0.5 h-6 w-6 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">{t.trustTitle}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{t.trustNote}</p>
                </div>
              </div>
              <Link
                href="/"
                className={`inline-flex h-9 shrink-0 items-center justify-center rounded-md border border-border px-4 text-sm font-medium text-foreground transition-colors hover:border-success hover:text-success ${publicFocusRing}`}
              >
                {messages.publicVerification.whatIs}
              </Link>
            </aside>
          </>
        ) : null}
      </main>
    </div>
  );
}
