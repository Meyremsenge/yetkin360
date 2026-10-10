"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { listOrganizationDirectory } from "@/lib/api/organizations";
import messages from "@/messages/tr.json";

const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";

/**
 * PLAN 3.53: öğrenci tüm kuruluşlardan serbestçe arayıp seçebilsin — backend
 * GET /organizations (scoped_organization_directory, üyelikten bağımsız).
 * Seçilen kuruluş /calismalar/olustur?organization_id=X'e yönlendirir.
 */
export default function KurulusSecPage() {
  const [query, setQuery] = useState("");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["organization-directory", query],
    queryFn: () => listOrganizationDirectory(query),
  });

  const items = data ?? [];

  return (
    <AppShell>
      <div className="max-w-[720px] px-4 py-8 md:px-6 lg:px-10">
        <Link
          href="/calismalar"
          className="mb-4 inline-flex items-center gap-2 rounded-sm text-sm text-muted-foreground hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        >
          <span aria-hidden="true">←</span>
          {messages.calismalar.detailBackLink}
        </Link>

        <h1 className="mt-4 font-serif text-[32px] font-semibold leading-10 text-foreground">
          {messages.kurulusSec.title}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">{messages.kurulusSec.description}</p>

        <div className="mt-6">
          <label htmlFor="organization-search" className="sr-only">
            {messages.kurulusSec.searchLabel}
          </label>
          <input
            id="organization-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={messages.kurulusSec.searchPlaceholder}
            className="block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
          />
        </div>

        <div className="mt-6">
          {isLoading ? (
            <div role="status" aria-busy="true" aria-label={messages.kurulusSec.loadingLabel} className="space-y-3">
              {[0, 1, 2].map((n) => (
                <div key={n} aria-hidden="true" className={`h-16 w-full ${pulse}`} />
              ))}
            </div>
          ) : isError ? (
            <Alert variant="error" className="flex items-center justify-between gap-4">
              <span>{messages.kurulusSec.loadError}</span>
              <Button variant="secondary" size="sm" onClick={() => void refetch()}>
                {messages.kurulusSec.retry}
              </Button>
            </Alert>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">{messages.kurulusSec.emptyMessage}</p>
          ) : (
            <ul className="space-y-3">
              {items.map((org) => (
                <li key={org.id}>
                  <Link
                    href={`/calismalar/olustur?organization_id=${org.id}`}
                    className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card p-4 hover:border-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                  >
                    <div>
                      <p className="font-medium text-foreground">{org.name}</p>
                      {org.domain ? (
                        <p className="text-sm text-muted-foreground">{org.domain}</p>
                      ) : null}
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {messages.kurulusSec.verificationLevel[
                        org.verification_level as keyof typeof messages.kurulusSec.verificationLevel
                      ] ?? org.verification_level}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </AppShell>
  );
}
