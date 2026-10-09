"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPublicVerification } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChainProgress } from "@/components/ui/chain-progress";
import { VerifiedSeal } from "@/components/ui/verified-seal";
import messages from "@/messages/tr.json";

const t = messages.publicVerification;

const trustLevelVariant: Record<string, "default" | "warning" | "success"> = {
  T0: "default",
  T1: "warning",
  T2: "default",
  T3: "success",
  T4: "success",
};

const focusRing =
  "rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";

function formatDate(value: string, dateOnly = false): string {
  return new Date(value).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    ...(dateOnly ? { timeZone: "UTC" } : {}),
  });
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TrustLevelBadge({ level }: { level: string }) {
  const label = (t.trustLevels as Record<string, string>)[level];
  return (
    <>
      <span className="sr-only">
        {t.trustLevelLabel}: {level}
      </span>
      {label ? (
        <Badge variant={trustLevelVariant[level] ?? "default"}>{label}</Badge>
      ) : null}
    </>
  );
}

function CertificateFrame({ children }: { children: React.ReactNode }) {
  return (
    <article className="relative rounded-lg border border-border bg-card p-6 md:p-12">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-[6px] rounded-md border border-border"
      />
      <div className="relative">{children}</div>
    </article>
  );
}

function CertificateSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label={t.loadingLabel}>
      <CertificateFrame>
        <div className="mb-6 flex justify-center md:absolute md:right-2 md:top-[-8px] md:mb-0">
          <div className="h-24 w-24 animate-pulse rounded-full bg-muted motion-reduce:animate-none" />
        </div>
        <div className="h-3 w-48 animate-pulse rounded-md bg-muted motion-reduce:animate-none" />
        <div className="mt-6 h-8 w-64 animate-pulse rounded-md bg-muted motion-reduce:animate-none" />
        <div className="mt-2 h-5 w-48 animate-pulse rounded-md bg-muted motion-reduce:animate-none" />
        <div className="mt-8 grid grid-cols-1 gap-6 border-t border-border pt-8 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-3 w-16 animate-pulse rounded-md bg-muted motion-reduce:animate-none" />
              <div className="h-5 w-40 animate-pulse rounded-md bg-muted motion-reduce:animate-none" />
            </div>
          ))}
        </div>
        <div className="mt-8 flex gap-2 border-t border-border pt-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-8 w-28 animate-pulse rounded-md bg-muted motion-reduce:animate-none" />
          ))}
        </div>
      </CertificateFrame>
    </div>
  );
}

function NotFoundCard() {
  return (
    <CertificateFrame>
      <div className="mb-6 flex justify-center md:absolute md:right-2 md:top-[-8px] md:mb-0">
        <div
          aria-hidden="true"
          className="h-24 w-24 rounded-full border border-dashed border-muted-foreground"
        />
      </div>
      <h1 className="font-serif text-2xl font-medium">{t.notFound}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t.notFoundDescription}</p>
      <Link
        href="/"
        className={`mt-6 inline-flex h-10 items-center rounded-md bg-muted px-4 text-sm font-medium text-foreground hover:bg-muted/80 ${focusRing}`}
      >
        {t.backHome}
      </Link>
    </CertificateFrame>
  );
}

export default function PublicVerificationPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const { data: verification, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["publicVerification", token],
    queryFn: () => getPublicVerification(token),
  });

  const chainSteps = [
    messages.home.chain.claim,
    messages.home.chain.evidence,
    messages.home.chain.attestation,
    messages.home.chain.verified,
  ].map((label) => ({ label, completed: true }));

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 md:px-8">
          <Link href="/" className={`font-serif text-lg font-bold text-foreground ${focusRing}`}>
            {messages.home.title}
          </Link>
          <span className="text-[13px] text-muted-foreground">{t.topBarLabel}</span>
        </div>
      </header>

      <main className="mx-auto max-w-[720px] px-4 pb-16 pt-4 md:pt-10">
        {isLoading ? (
          <CertificateSkeleton />
        ) : isError ? (
          error instanceof ApiError && error.status === 404 ? (
            <NotFoundCard />
          ) : (
            <Alert variant="error">
              <p>{error instanceof NetworkError ? error.message : messages.errors.generic}</p>
              <div className="mt-3">
                <Button variant="secondary" size="sm" onClick={() => refetch()}>
                  {t.retry}
                </Button>
              </div>
            </Alert>
          )
        ) : verification ? (
          <>
            <CertificateFrame>
              <div className="mb-6 flex justify-center md:absolute md:right-2 md:top-[-8px] md:mb-0">
                <VerifiedSeal size="lg" label={t.sealLabel} />
              </div>

              <p className="font-mono text-xs text-muted-foreground">{t.recordHeading}</p>

              <div className="mt-6">
                <h1 className="font-serif text-[32px] font-semibold leading-10">
                  {verification.talent_name}
                </h1>
                <p className="mt-2 font-serif text-xl font-medium text-muted-foreground">
                  {verification.title}
                </p>
              </div>

              <dl className="mt-8 grid grid-cols-1 gap-6 border-t border-border pt-8 md:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium text-muted-foreground">{t.organizationLabel}</dt>
                  <dd className="mt-1 flex flex-wrap items-center gap-2 text-base">
                    <span>{verification.organization_name}</span>
                    <TrustLevelBadge level={verification.organization_trust_level} />
                  </dd>
                  {verification.organization_domain && (
                    <dd className="mt-1 font-mono text-[13px] text-muted-foreground">
                      {t.domainLabel}: {verification.organization_domain}
                    </dd>
                  )}
                </div>
                {verification.institution_name && (
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">{t.institutionLabel}</dt>
                    <dd className="mt-1 flex flex-wrap items-center gap-2 text-base">
                      <span>{verification.institution_name}</span>
                      {verification.institution_trust_level && (
                        <TrustLevelBadge level={verification.institution_trust_level} />
                      )}
                    </dd>
                  </div>
                )}
                {(verification.started_on || verification.ended_on) && (
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">{t.periodLabel}</dt>
                    <dd className="mt-1 text-base tabular-nums">
                      {verification.started_on ? formatDate(verification.started_on, true) : "-"} –{" "}
                      {verification.ended_on ? formatDate(verification.ended_on, true) : "-"}
                    </dd>
                  </div>
                )}
                <div>
                  <dt className="text-xs font-medium text-muted-foreground">{t.verifiedAtLabel}</dt>
                  <dd className="mt-1 text-base tabular-nums">{formatDate(verification.verified_at)}</dd>
                </div>
              </dl>

              {verification.organization_trust_level === "T1" && (
                <Alert variant="warning" role="note" className="mt-4 p-3 text-sm">
                  {t.unverifiedOrganizationNotice}
                </Alert>
              )}

              <section className="mt-8 border-t border-border pt-6">
                <h2 className="mb-4 text-xs text-muted-foreground">{t.chainCaption}</h2>
                <ChainProgress steps={chainSteps} />
              </section>

              {verification.attested_skills.length > 0 && (
                <section className="mt-8 border-t border-border pt-6">
                  <h2 className="mb-3 font-serif text-xl font-medium">{t.attestedSkillsTitle}</h2>
                  <ul className="flex flex-wrap gap-2">
                    {verification.attested_skills.map((skill, idx) => (
                      <li
                        key={idx}
                        className="inline-flex min-h-8 items-center gap-1 rounded-md border border-border bg-card px-3 py-1 text-sm"
                      >
                        <span className="font-medium">{skill.name_tr}</span>
                        {skill.attestor_organization && (
                          <span className="text-[13px] text-muted-foreground">
                            · {skill.attestor_organization}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <footer className="mt-10 border-t border-dashed border-border pt-4">
                <div className="flex flex-col gap-1 font-mono text-xs text-muted-foreground md:flex-row md:justify-between">
                  <span>
                    {t.recordNo}: {token.slice(0, 8)}…
                  </span>
                  <span className="tabular-nums">
                    {t.stampBrand} · {formatDateTime(verification.verified_at)}
                  </span>
                </div>
                <p className="mt-2 text-[13px] text-muted-foreground">
                  {t.verifiedStatement.replace("{date}", formatDate(verification.verified_at))}
                </p>
              </footer>
            </CertificateFrame>

            <p className="mt-6 text-center">
              <Link
                href="/"
                className={`text-[13px] text-muted-foreground hover:text-foreground hover:underline ${focusRing}`}
              >
                {t.whatIs}
              </Link>
            </p>
          </>
        ) : null}
      </main>
    </div>
  );
}
