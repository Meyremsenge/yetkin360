"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  getOrganizationShowcase,
  type OrganizationShowcase,
  type OrganizationShowcaseExperience,
} from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PublicTopBar, publicFocusRing } from "@/components/public-top-bar";
import { SealMark } from "@/components/brand/brand-mark";
import { formatPeriod, initials } from "@/components/public-profile/format";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.orgShowcase;
const v = messages.publicVerification;
const trustLabels = v.trustLevels as Record<string, string>;
const TRUST_VARIANT: Record<string, "default" | "warning" | "success"> = {
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};
// Matches SHOWCASE_LIMIT in backend/app/services/organization_showcase.py.
const SHOWCASE_LIMIT = 50;

const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";

function ShowcaseSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label={t.loadingLabel}>
      <div className="space-y-3">
        <div className={`h-3 w-36 ${pulse}`} />
        <div className={`h-10 w-72 ${pulse}`} />
        <div className={`h-4 w-48 ${pulse}`} />
      </div>
      <div className={`mt-10 h-20 w-full ${pulse}`} />
      <div className="mt-10 grid gap-5 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`h-40 w-full ${pulse}`} />
        ))}
      </div>
    </div>
  );
}

function NotFoundState() {
  return (
    <div className="rounded-lg border border-border bg-card p-6 md:p-12">
      <div aria-hidden="true" className="mb-6 h-24 w-24 rounded-full border border-dashed border-muted-foreground" />
      <h1 className="font-serif text-2xl font-medium">{t.notFound}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t.notFoundDescription}</p>
      <Link
        href="/"
        className={`mt-6 inline-flex h-10 items-center rounded-md bg-muted px-4 text-sm font-medium text-foreground hover:bg-muted/80 ${publicFocusRing}`}
      >
        {v.backHome}
      </Link>
    </div>
  );
}

function Hero({ showcase }: { showcase: OrganizationShowcase }) {
  const level = showcase.verification_level;
  return (
    <header className="y360-rise flex items-start gap-5">
      <span
        aria-hidden="true"
        className="hidden h-16 w-16 shrink-0 items-center justify-center rounded-md border border-border bg-sand font-serif text-xl font-semibold text-foreground sm:flex"
      >
        {initials(showcase.name)}
      </span>
      <div className="min-w-0">
        <p className="inline-flex items-center gap-2 font-mono text-xs text-success">
          <SealMark className="h-4 w-4" />
          {t.eyebrow}
        </p>
        <h1 className="mt-3 font-serif text-[32px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[44px]">
          {showcase.name}
        </h1>
        <p className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-[15px] text-foreground">
          <span className="text-xs font-medium text-muted-foreground">{t.trustLabel}</span>
          {trustLabels[level] ? <Badge variant={TRUST_VARIANT[level] ?? "default"}>{trustLabels[level]}</Badge> : null}
          {showcase.domain ? (
            <span className="inline-flex items-center gap-2">
              <span className="font-mono text-[13px]">{showcase.domain}</span>
              <Badge variant="success">{t.domainVerified}</Badge>
            </span>
          ) : null}
        </p>
      </div>
    </header>
  );
}

function StatStrip({ stats }: { stats: OrganizationShowcase["stats"] }) {
  const items = [
    { label: t.statVerified, value: stats.verified_public_count },
    { label: t.statInstitutions, value: stats.institution_count },
  ];
  return (
    <dl
      aria-label={t.statsLabel}
      className="mt-10 grid grid-cols-2 divide-x divide-border rounded-lg border border-border bg-card"
    >
      {items.map((item) => (
        <div key={item.label} className="px-5 py-4">
          <dt className="text-xs text-muted-foreground">{item.label}</dt>
          <dd className="mt-1 font-serif text-3xl font-semibold tabular-nums text-foreground">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function RecordCard({ record }: { record: OrganizationShowcaseExperience }) {
  const period = formatPeriod(record.started_on, record.ended_on);
  return (
    <li>
      <article className="relative flex h-full flex-col rounded-lg border border-border bg-card p-5 transition-colors duration-150 hover:border-foreground/25">
        <SealMark className="absolute right-4 top-4 h-9 w-9" />
        <div className="pr-12">
          <h3 className="font-serif text-lg font-semibold leading-snug text-foreground">{record.role_snapshot}</h3>
          <p className="mt-1 text-[15px]">
            <Link
              href={`/p/${encodeURIComponent(record.talent_public_slug)}`}
              aria-label={t.personLinkOf.replace("{name}", record.talent_display_name)}
              className={cn("font-medium text-foreground underline-offset-4 hover:underline", publicFocusRing)}
            >
              {record.talent_display_name}
            </Link>
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted-foreground">
            {period ? <span className="font-mono text-xs tabular-nums">{period}</span> : null}
            {record.institution_name ? (
              <>
                {period ? <span aria-hidden="true">·</span> : null}
                <span>{record.institution_name}</span>
              </>
            ) : null}
          </p>
        </div>

        {record.skills.length > 0 ? (
          <div className="mt-4 border-t border-border pt-3">
            <p className="text-xs font-medium text-muted-foreground">{t.skillsLabel}</p>
            <ul className="mt-1.5 flex flex-wrap gap-2">
              {record.skills.map((skill) => (
                <li
                  key={skill}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border border-success/30 bg-success/[0.06] px-2 text-[13px] font-medium text-foreground"
                >
                  <SealMark className="h-3.5 w-3.5" />
                  {skill}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {record.public_token ? (
          <div className="mt-auto flex justify-end pt-4">
            <Link
              href={`/v/${encodeURIComponent(record.public_token)}`}
              aria-label={t.verifyRecordOf.replace("{role}", record.role_snapshot)}
              className={cn(
                "inline-flex items-center gap-1 text-sm font-medium text-success underline-offset-4 hover:underline",
                publicFocusRing
              )}
            >
              {t.verifyRecord}
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        ) : null}
      </article>
    </li>
  );
}

function EmptyNote({ title, body }: { title: string; body: string }) {
  return (
    <div className="mt-6 flex items-start gap-4 rounded-lg border border-dashed border-border bg-card p-6">
      <SealMark className="h-10 w-10 shrink-0 text-muted-foreground/40" />
      <div>
        <p className="text-base font-semibold">{title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{body}</p>
      </div>
    </div>
  );
}

function ShowcaseView({ showcase }: { showcase: OrganizationShowcase }) {
  const records = showcase.experiences;
  return (
    <>
      <Hero showcase={showcase} />
      {showcase.showcase_enabled ? (
        <>
          <StatStrip stats={showcase.stats} />
          <section className="mt-14" aria-labelledby="records-title">
            <div className="max-w-[640px]">
              <h2 id="records-title" className="font-serif text-2xl font-semibold text-foreground">
                {t.recordsTitle}
              </h2>
              <p className="mt-2 text-[15px] text-muted-foreground">{t.recordsLead}</p>
            </div>
            {records.length === 0 ? (
              <EmptyNote title={t.emptyTitle} body={t.emptyBody} />
            ) : (
              <>
                <ul className="mt-6 grid gap-5 md:grid-cols-2">
                  {records.map((record, index) => (
                    <RecordCard key={record.public_token ?? `${record.talent_public_slug}-${index}`} record={record} />
                  ))}
                </ul>
                {showcase.stats.verified_public_count > SHOWCASE_LIMIT ? (
                  <p className="mt-4 text-xs text-muted-foreground">{t.recordsLimitNote}</p>
                ) : null}
              </>
            )}
          </section>
        </>
      ) : (
        <EmptyNote title={t.closedTitle} body={t.closedBody} />
      )}
      <p className="mt-14 border-t border-border pt-6 text-xs text-muted-foreground">{t.consentNote}</p>
    </>
  );
}

export default function OrganizationShowcasePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["organizationShowcase", id],
    queryFn: () => getOrganizationShowcase(id),
    retry: false,
  });

  return (
    <div className="min-h-screen bg-background">
      <PublicTopBar label={t.topBarLabel} />
      <main className="mx-auto max-w-[1100px] px-4 pb-20 pt-8 md:px-8 md:pt-14">
        {isLoading ? (
          <ShowcaseSkeleton />
        ) : isError ? (
          error instanceof ApiError && (error.status === 404 || error.status === 422) ? (
            <NotFoundState />
          ) : (
            <Alert variant="error">
              <p>{error instanceof NetworkError ? error.message : messages.errors.generic}</p>
              <div className="mt-3">
                <Button variant="secondary" size="sm" onClick={() => refetch()}>
                  {v.retry}
                </Button>
              </div>
            </Alert>
          )
        ) : data ? (
          <ShowcaseView showcase={data} />
        ) : null}
      </main>
    </div>
  );
}
