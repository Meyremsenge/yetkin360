"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPublicProfile, type PublicProfile } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PublicTopBar, publicFocusRing } from "@/components/public-top-bar";
import { SealMark } from "@/components/brand/brand-mark";
import { ParticleSeal } from "@/components/brand/particle-seal";
import { ChainLegend } from "@/components/page-layout";
import { ExperienceCard } from "@/components/public-profile/experience-card";
import { QrCode } from "@/components/public-profile/qr-code";
import { ShareActions } from "@/components/public-profile/share-actions";
import { SkillMap } from "@/components/public-profile/skill-map";
import messages from "@/messages/tr.json";

const t = messages.publicProfile;
const VERIFIED_LEVELS = new Set(["T2", "T3", "T4"]);

const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";

function ProfileSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label={t.loadingLabel}>
      <div className="space-y-3">
        <div className={`h-3 w-44 ${pulse}`} />
        <div className={`h-10 w-72 ${pulse}`} />
        <div className={`h-4 w-80 ${pulse}`} />
        <div className={`h-4 w-56 ${pulse}`} />
      </div>
      <div className={`mt-10 h-24 w-full ${pulse}`} />
      <div className="mt-10 space-y-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className={`h-36 w-full ${pulse}`} />
        ))}
      </div>
    </div>
  );
}

function NotFoundState() {
  const v = messages.publicVerification;
  return (
    <div className="rounded-lg border border-border bg-card p-6 md:p-12">
      <div aria-hidden="true" className="mb-6 h-24 w-24 rounded-full border border-dashed border-muted-foreground" />
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

function SectionHeading({ eyebrow, title, lead }: { eyebrow?: string; title: string; lead?: string }) {
  return (
    <div className="max-w-[640px]">
      {eyebrow ? <p className="font-mono text-xs text-muted-foreground">{eyebrow}</p> : null}
      <h2 className="mt-1 font-serif text-2xl font-semibold text-foreground">{title}</h2>
      {lead ? <p className="mt-2 text-[15px] text-muted-foreground">{lead}</p> : null}
    </div>
  );
}

/** Usable share URL: the live origin in the browser, the path as a fallback. */
const noopSubscribe = () => () => {};

function useProfileUrl(slug: string): string {
  const origin = useSyncExternalStore(noopSubscribe, () => window.location.origin, () => "");
  return `${origin}/p/${encodeURIComponent(slug)}`;
}

function Hero({ profile, url }: { profile: PublicProfile; url: string }) {
  const meta = [
    profile.department,
    profile.study_year ? t.studyYear.replace("{n}", String(profile.study_year)) : null,
    profile.city,
  ].filter(Boolean) as string[];
  const institutionTrust = profile.institution_trust_level;

  return (
    <header className="y360-rise relative grid gap-6 md:grid-cols-[1fr_176px] md:items-center">
      <div className="min-w-0">
        <p className="inline-flex items-center gap-2 font-mono text-xs text-success">
          <SealMark className="h-4 w-4" />
          {t.eyebrow}
        </p>
        <h1 className="mt-3 font-serif text-[36px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[48px]">
          {profile.display_name}
        </h1>
        {profile.headline ? (
          <p className="mt-3 max-w-[560px] text-lg text-muted-foreground">{profile.headline}</p>
        ) : null}
        {meta.length > 0 ? (
          <p className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-foreground">
            {meta.map((item, i) => (
              <span key={item} className="inline-flex items-center gap-2">
                {i > 0 ? <span aria-hidden="true" className="text-muted-foreground">·</span> : null}
                {item}
              </span>
            ))}
          </p>
        ) : null}
        {profile.institution_name ? (
          <p className="mt-2 flex flex-wrap items-center gap-2 text-[15px] text-foreground">
            <span>{profile.institution_name}</span>
            {institutionTrust && VERIFIED_LEVELS.has(institutionTrust) ? (
              <Badge variant="success">{t.institutionVerified}</Badge>
            ) : null}
          </p>
        ) : null}
        <div className="mt-6">
          <ShareActions url={url} name={profile.display_name} />
        </div>
      </div>
      <div className="hidden md:block print:hidden">
        <ParticleSeal className="h-44 w-44" particles={1400} />
      </div>
    </header>
  );
}

function TrustStrip({ profile }: { profile: PublicProfile }) {
  const stats = [
    { value: profile.verified_experiences.length, label: t.statExperiences },
    { value: profile.skills?.length ?? 0, label: t.statSkills },
    { value: profile.attesting_organization_count ?? 0, label: t.statOrganizations },
  ];
  return (
    <dl
      aria-label={t.statsLabel}
      className="grid grid-cols-3 divide-x divide-border rounded-lg border border-border bg-card"
    >
      {stats.map((stat) => (
        <div key={stat.label} className="px-3 py-4 text-center md:px-6 md:py-5 md:text-left">
          <dd className="font-serif text-[28px] font-semibold leading-none tabular-nums text-foreground md:text-[32px]">
            {stat.value}
          </dd>
          <dt className="mt-2 text-xs text-muted-foreground md:text-[13px]">{stat.label}</dt>
        </div>
      ))}
    </dl>
  );
}

function EmptyExperiences() {
  return (
    <div className="mt-6 flex items-start gap-4 rounded-lg border border-dashed border-border bg-card p-6">
      <SealMark className="h-10 w-10 shrink-0 text-muted-foreground/40" />
      <div>
        <p className="text-base font-semibold first-letter:uppercase">{t.empty}</p>
        <p className="mt-1 text-sm text-muted-foreground">{t.emptyHint}</p>
      </div>
    </div>
  );
}

function ProfileView({ profile, slug }: { profile: PublicProfile; slug: string }) {
  const url = useProfileUrl(slug);
  const experiences = profile.verified_experiences;
  const skills = profile.skills ?? [];

  return (
    <>
      <Hero profile={profile} url={url} />

      {experiences.length > 0 ? (
        <div className="mt-10">
          <TrustStrip profile={profile} />
        </div>
      ) : null}

      {skills.length > 0 ? (
        <section className="mt-14 print:mt-8 print:break-inside-avoid" aria-labelledby="skill-map-title">
          <div id="skill-map-title">
            <SectionHeading title={t.skillMapTitle} lead={t.skillMapLead} />
          </div>
          <div className="mt-5">
            <SkillMap skills={skills} />
          </div>
        </section>
      ) : null}

      <section className="mt-14 print:mt-8" aria-labelledby="timeline-title">
        <div id="timeline-title">
          <SectionHeading title={t.timelineTitle} lead={experiences.length > 0 ? t.timelineLead : undefined} />
        </div>
        {experiences.length === 0 ? (
          <EmptyExperiences />
        ) : (
          <ol className="mt-6 space-y-5">
            {experiences.map((exp, index) => (
              <ExperienceCard key={exp.id} experience={exp} index={index} />
            ))}
          </ol>
        )}
      </section>

      <section className="mt-14 print:hidden" aria-labelledby="how-title">
        <div id="how-title">
          <SectionHeading title={t.howTitle} lead={t.howLead} />
        </div>
        <div className="mt-5">
          <ChainLegend current={4} />
        </div>
      </section>

      <footer className="mt-14 flex flex-col gap-4 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{t.profileUrlLabel}</p>
          <p className="mt-1 break-all font-mono text-[13px] text-foreground">{url}</p>
        </div>
        <Link
          href="/"
          className={`inline-flex h-9 shrink-0 items-center justify-center rounded-md border border-border px-4 text-sm font-medium text-foreground transition-colors hover:border-success hover:text-success print:hidden ${publicFocusRing}`}
        >
          {messages.publicVerification.whatIs}
        </Link>
        <div className="hidden items-center gap-4 print:flex">
          <QrCode value={url} label={t.qrLabel.replace("{name}", profile.display_name)} className="h-24 w-24" />
          <p className="max-w-[260px] text-xs text-muted-foreground">{t.printNote}</p>
        </div>
      </footer>
    </>
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
    <div className="min-h-screen bg-background print:bg-white">
      <div className="print:hidden">
        <PublicTopBar label={t.topBarLabel} />
      </div>

      <main className="mx-auto max-w-[880px] px-4 pb-20 pt-8 md:px-8 md:pt-14 print:max-w-none print:px-0 print:pt-0">
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
          <ProfileView profile={profile} slug={slug} />
        ) : null}
      </main>
    </div>
  );
}
