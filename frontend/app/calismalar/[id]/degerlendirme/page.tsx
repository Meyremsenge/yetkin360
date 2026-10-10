"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { ChainLegend, PageBody, PageHeader } from "@/components/page-layout";
import { ActionLink, PanelGrid, PanelIcon, StatusPill, StepsCard } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { getEngagement } from "@/lib/api/engagements";
import { CHAIN_PROGRESS, STATUS_TONE } from "@/lib/ui/engagement-chain";
import { EvaluationForm } from "./evaluation-form";
import messages from "@/messages/tr.json";

const d = messages.degerlendirme;
const RATING_ORDER = Object.keys(d.guide) as (keyof typeof d.guide)[];

export default function DegerlendirmePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [justSubmitted, setJustSubmitted] = useState(false);

  const { data: engagement, isLoading, isError } = useQuery({
    queryKey: ["engagement", id],
    queryFn: () => getEngagement(id),
  });

  const backHref = `/calismalar/${id}`;
  const progress = engagement ? CHAIN_PROGRESS[engagement.status] ?? { done: 0 } : undefined;

  return (
    <AppShell>
      <PageHeader
        back={{ href: backHref, label: d.backLink }}
        eyebrow={d.eyebrow}
        title={d.title}
        description={d.subtitle}
      >
        {progress ? <ChainLegend current={progress.done} broken={progress.broken} /> : null}
      </PageHeader>

      <PageBody>
        {isLoading ? (
          <div role="status" className="space-y-4">
            <span className="sr-only">{messages.shell.loading}</span>
            <div aria-hidden="true" className="h-20 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
            <div aria-hidden="true" className="h-64 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
          </div>
        ) : isError || !engagement ? (
          <Alert variant="error" className="text-sm">
            {messages.calismalar.detailLoadError}
          </Alert>
        ) : (
          <PanelGrid
            main={
              <>
                <section className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-border bg-sand/60 p-5">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-card text-foreground">
                      <PanelIcon name="briefcase" />
                    </span>
                    <div className="min-w-0">
                      <h2 className="font-serif text-xl font-medium leading-7 text-foreground">{engagement.title}</h2>
                      <p className="mt-0.5 text-sm text-muted-foreground">
                        {messages.calismalar.kind[engagement.kind]} · {engagement.organization_name}
                      </p>
                    </div>
                  </div>
                  <StatusPill tone={STATUS_TONE[engagement.status] ?? "default"}>
                    {messages.calismalar.status[engagement.status]}
                  </StatusPill>
                </section>

                {engagement.status !== "PENDING_EVALUATION" ? (
                  <div className="rounded-xl border border-border bg-card p-5">
                    <Alert variant="info" className="text-sm">
                      {d.notEligibleMessage}
                    </Alert>
                    <ActionLink href={backHref} variant="neutral" icon="arrowRight" className="mt-4">
                      {d.backLink}
                    </ActionLink>
                  </div>
                ) : justSubmitted ? (
                  <div className="y360-rise rounded-xl border border-success/30 bg-success/[0.07] p-5">
                    <div role="status" aria-live="polite" className="flex items-start gap-3">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-success text-background">
                        <PanelIcon name="check" />
                      </span>
                      <div>
                        <p className="font-serif text-lg font-semibold text-success">{d.successMessage}</p>
                        <p className="mt-0.5 text-sm text-foreground">{d.successNext}</p>
                      </div>
                    </div>
                    <ActionLink href={backHref} variant="outline" icon="arrowRight" className="mt-4">
                      {d.backLink}
                    </ActionLink>
                  </div>
                ) : (
                  <EvaluationForm engagementId={id} onSubmitted={() => setJustSubmitted(true)} />
                )}
              </>
            }
            aside={
              <>
                <div className="rounded-xl border border-border bg-card p-5">
                  <p className="font-serif text-lg font-semibold text-foreground">{d.guideTitle}</p>
                  <dl className="mt-3 space-y-3">
                    {RATING_ORDER.map((option) => (
                      <div key={option}>
                        <dt className="text-sm font-medium text-foreground">{d.rating[option]}</dt>
                        <dd className="text-[13px] text-muted-foreground">{d.guide[option]}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <StepsCard title={d.afterTitle} steps={d.afterSteps} />
              </>
            }
          />
        )}
      </PageBody>
    </AppShell>
  );
}
