"use client";

import { useQuery } from "@tanstack/react-query";
import {
  EmptyState,
  Initials,
  PanelSection,
  StatusPill,
  actionClass,
  formatTemplate,
} from "@/components/panel-kit";
import { listInstitutionPartners } from "@/lib/api/institutions";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.kurumPanel;
const levels = messages.kurulusSec.verificationLevel as Record<string, string>;

/** Organizations the institution's students work with, with their counts. */
export function PartnersSection({ institutionId }: { institutionId: string }) {
  const query = useQuery({
    queryKey: ["institution-partners", institutionId],
    queryFn: () => listInstitutionPartners(institutionId),
  });
  const partners = query.data?.items ?? [];

  return (
    <PanelSection
      id="is-birlikleri"
      icon="briefcase"
      title={t.partnersTitle}
      hint={t.partnersHint}
      count={query.isSuccess ? partners.length : undefined}
      flush={partners.length > 0}
    >
      {query.isLoading ? (
        <div
          aria-hidden="true"
          className="h-20 animate-pulse rounded-lg bg-muted motion-reduce:animate-none"
        />
      ) : query.isError ? (
        <div className="flex items-center justify-between gap-4 text-sm text-destructive">
          <span>{t.partnersError}</span>
          <button
            type="button"
            onClick={() => void query.refetch()}
            className={cn(actionClass.neutral, "h-8 px-3 text-[13px]")}
          >
            {messages.errors.retry}
          </button>
        </div>
      ) : partners.length === 0 ? (
        <EmptyState
          icon="briefcase"
          title={t.partnersEmptyTitle}
          hint={t.partnersEmptyHint}
        />
      ) : (
        <ul className="divide-y divide-border">
          {partners.map((partner) => (
            <li
              key={partner.organization_id}
              className="flex flex-wrap items-center gap-3 px-5 py-3.5"
            >
              <Initials name={partner.organization_name} />
              <span className="min-w-[60%] flex-1 sm:min-w-0">
                <span className="block truncate font-medium text-foreground">
                  {partner.organization_name}
                </span>
                <span className="mt-0.5 block text-xs text-muted-foreground">
                  {levels[partner.verification_level] ??
                    partner.verification_level}
                </span>
              </span>
              <span className="flex flex-wrap items-center gap-2">
                <StatusPill tone="default">
                  {formatTemplate(t.partnerStudents, {
                    n: partner.student_count,
                  })}
                </StatusPill>
                <StatusPill tone="default">
                  {formatTemplate(t.partnerEngagements, {
                    n: partner.engagement_count,
                  })}
                </StatusPill>
                <StatusPill
                  tone={partner.verified_count > 0 ? "success" : "default"}
                >
                  {formatTemplate(t.partnerVerified, {
                    n: partner.verified_count,
                  })}
                </StatusPill>
              </span>
            </li>
          ))}
        </ul>
      )}
    </PanelSection>
  );
}
