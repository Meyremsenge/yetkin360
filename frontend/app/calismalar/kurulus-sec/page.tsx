"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  listApprovers,
  listOrganizationDirectory,
  type OrganizationDirectoryEntry,
} from "@/lib/api/organizations";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { ApproverIdentity, CheckIcon, NewEngagementSteps } from "../yeni-calisma-parts";

const k = messages.kurulusSec;
const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";
const SEARCH_DEBOUNCE_MS = 250;

function verificationLabel(level: string): string {
  return k.verificationLevel[level as keyof typeof k.verificationLevel] ?? level;
}

/**
 * Who can approve at the chosen organization, before the student commits to it.
 * Fetched only for the selected card (the endpoint shares Keşfet's rate limit).
 */
function SelectedOrganizationPanel({ organization }: { organization: OrganizationDirectoryEntry }) {
  const approvers = useQuery({
    queryKey: ["organization-approvers", organization.id],
    queryFn: () => listApprovers(organization.id),
    retry: false,
  });

  return (
    <div className="border-t border-border bg-background/60 px-4 py-5 sm:px-5">
      <h3 className="text-sm font-semibold text-foreground">{k.approversTitle}</h3>
      <p className="mt-1 text-[13px] leading-5 text-muted-foreground">{k.approversHint}</p>

      <div className="mt-4">
        {approvers.isLoading ? (
          <div role="status" aria-busy="true" aria-label={k.approversLoading} className="space-y-2">
            {[0, 1].map((n) => (
              <div key={n} aria-hidden="true" className={`h-12 w-full ${pulse}`} />
            ))}
          </div>
        ) : approvers.isError ? (
          <p className="text-sm text-muted-foreground">{k.approversError}</p>
        ) : (approvers.data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">{k.approversEmpty}</p>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-card">
            {(approvers.data ?? []).map((approver) => (
              <li key={approver.user_id} className="px-3 py-2.5">
                <ApproverIdentity approver={approver} />
              </li>
            ))}
          </ul>
        )}
      </div>

      <Link
        href={`/calismalar/olustur?organization_id=${organization.id}`}
        className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-success px-5 text-sm font-medium text-background transition-colors hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 sm:w-auto"
      >
        {k.continueButton}
        <span aria-hidden="true">→</span>
      </Link>
    </div>
  );
}

function OrganizationCard({
  organization,
  selected,
  onSelect,
}: {
  organization: OrganizationDirectoryEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  const panelId = `organization-${organization.id}-panel`;
  return (
    <li
      className={cn(
        "overflow-hidden rounded-xl border bg-card transition-colors",
        selected ? "border-success ring-1 ring-success" : "border-border hover:border-muted-foreground/50"
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-expanded={selected}
        aria-controls={selected ? panelId : undefined}
        className="flex w-full items-center gap-4 px-4 py-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-success sm:px-5"
      >
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-sand font-serif text-lg font-semibold text-foreground"
        >
          {organization.name.trim().charAt(0).toLocaleUpperCase("tr-TR")}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block break-words font-medium leading-snug text-foreground">{organization.name}</span>
          <span className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[13px] text-muted-foreground">
            {organization.domain ? (
              <span className="font-mono">{organization.domain}</span>
            ) : (
              <span>{k.domainUnverified}</span>
            )}
            <span>{verificationLabel(organization.verification_level)}</span>
          </span>
        </span>
        <span
          aria-hidden="true"
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border",
            selected ? "border-success bg-success text-background" : "border-border text-transparent"
          )}
        >
          <CheckIcon />
        </span>
        {selected ? <span className="sr-only">{k.selectedLabel}</span> : null}
      </button>
      {selected ? (
        <div id={panelId}>
          <SelectedOrganizationPanel organization={organization} />
        </div>
      ) : null}
    </li>
  );
}

function HowItWorks() {
  return (
    <aside className="rounded-xl border border-border bg-card p-5 lg:sticky lg:top-6">
      <h2 className="font-serif text-lg font-semibold text-foreground">{k.guideTitle}</h2>
      <ol className="mt-4 space-y-4">
        {k.guideSteps.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <span
              aria-hidden="true"
              className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-xs",
                index === 0 ? "border-success bg-success/10 text-success" : "border-border text-muted-foreground"
              )}
            >
              {index + 1}
            </span>
            <span>
              <span className="block text-sm font-medium text-foreground">{step.title}</span>
              <span className="block text-[13px] leading-5 text-muted-foreground">{step.body}</span>
            </span>
          </li>
        ))}
      </ol>
    </aside>
  );
}

/**
 * PLAN 3.53: öğrenci tüm kuruluşlardan serbestçe arayıp seçebilsin — backend
 * GET /organizations (scoped_organization_directory, üyelikten bağımsız).
 * Seçilen kart yerinde açılır ve kuruluşun onaylayıcılarını (ad · birim ·
 * maskeli e-posta) gösterir; "devam" /calismalar/olustur?organization_id=X'e gider.
 */
export default function KurulusSecPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["organization-directory", debouncedQuery],
    queryFn: () => listOrganizationDirectory(debouncedQuery),
  });

  const items = data ?? [];

  return (
    <AppShell>
      <PageHeader
        back={{ href: "/calismalar", label: messages.calismalar.detailBackLink }}
        eyebrow={k.eyebrow}
        title={k.title}
        description={k.description}
      >
        <NewEngagementSteps current={1} />
      </PageHeader>

      <PageBody>
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="min-w-0">
            <div className="relative">
              <label htmlFor="organization-search" className="sr-only">
                {k.searchLabel}
              </label>
              <svg
                viewBox="0 0 24 24"
                className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-muted-foreground"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.8}
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" strokeLinecap="round" />
              </svg>
              <input
                id="organization-search"
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={k.searchPlaceholder}
                autoComplete="off"
                className="block h-12 w-full rounded-lg border border-border bg-card pl-11 pr-4 text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25"
              />
            </div>

            <div className="mt-6">
              {isLoading ? (
                <div role="status" aria-busy="true" aria-label={k.loadingLabel} className="space-y-3">
                  {[0, 1, 2].map((n) => (
                    <div key={n} aria-hidden="true" className={`h-[76px] w-full rounded-xl ${pulse}`} />
                  ))}
                </div>
              ) : isError ? (
                <Alert variant="error" className="flex items-center justify-between gap-4">
                  <span>{k.loadError}</span>
                  <Button variant="secondary" size="sm" onClick={() => void refetch()}>
                    {k.retry}
                  </Button>
                </Alert>
              ) : items.length === 0 ? (
                <div className="rounded-xl border border-dashed border-muted-foreground/30 px-6 py-10 text-center">
                  <p className="font-medium text-foreground">{k.emptyMessage}</p>
                  <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{k.emptyHint}</p>
                </div>
              ) : (
                <>
                  <p className="mb-3 flex flex-wrap items-baseline justify-between gap-2 text-[13px] text-muted-foreground">
                    <span className="font-mono tabular-nums">
                      {k.resultCount.replace("{count}", String(items.length))}
                    </span>
                    {selectedId ? null : <span>{k.selectHint}</span>}
                  </p>
                  <ul className="space-y-3">
                    {items.map((organization) => (
                      <OrganizationCard
                        key={organization.id}
                        organization={organization}
                        selected={organization.id === selectedId}
                        onSelect={() => setSelectedId((current) => (current === organization.id ? null : organization.id))}
                      />
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>

          <HowItWorks />
        </div>
      </PageBody>
    </AppShell>
  );
}
