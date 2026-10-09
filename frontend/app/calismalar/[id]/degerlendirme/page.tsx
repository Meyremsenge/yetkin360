"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { getEngagement } from "@/lib/api/engagements";
import { EvaluationForm } from "./evaluation-form";
import messages from "@/messages/tr.json";

const BACK_BUTTON_CLASS =
  "mt-4 inline-flex h-10 items-center rounded-md border border-border bg-muted px-4 text-sm font-medium text-foreground hover:bg-muted/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";

export default function DegerlendirmePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [justSubmitted, setJustSubmitted] = useState(false);

  const { data: engagement, isLoading, isError } = useQuery({
    queryKey: ["engagement", id],
    queryFn: () => getEngagement(id),
  });

  const backHref = `/calismalar/${id}`;

  return (
    <AppShell>
      <div className="max-w-[960px] px-4 py-8 md:px-6 lg:px-10">
        <Link
          href={backHref}
          className="text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        >
          ← {messages.degerlendirme.backLink}
        </Link>

        <h1 className="mt-4 font-serif text-[32px] font-semibold leading-10 text-foreground">
          {messages.degerlendirme.title}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">{messages.degerlendirme.subtitle}</p>

        {isLoading ? (
          <div role="status" className="mt-6 space-y-4">
            <span className="sr-only">{messages.shell.loading}</span>
            <div aria-hidden="true" className="h-20 animate-pulse rounded-lg bg-muted" />
            <div aria-hidden="true" className="h-64 animate-pulse rounded-lg bg-muted" />
          </div>
        ) : isError || !engagement ? (
          <Alert variant="error" className="mt-6 text-sm">
            {messages.calismalar.detailLoadError}
          </Alert>
        ) : (
          <>
            <section className="mt-6 flex items-start justify-between gap-4 rounded-lg border border-border bg-sand p-5">
              <div>
                <h2 className="font-serif text-xl font-medium leading-7 text-foreground">
                  {engagement.title}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {messages.calismalar.kind[engagement.kind]} · {engagement.organization_name}
                </p>
              </div>
              <Badge variant="warning" className="shrink-0">
                {messages.calismalar.status[engagement.status]}
              </Badge>
            </section>

            <div className="mt-8">
              {engagement.status !== "PENDING_EVALUATION" ? (
                <>
                  <Alert variant="warning" className="text-sm">
                    {messages.degerlendirme.notEligibleMessage}
                  </Alert>
                  <Link href={backHref} className={BACK_BUTTON_CLASS}>
                    {messages.degerlendirme.backLink}
                  </Link>
                </>
              ) : justSubmitted ? (
                <>
                  <Alert variant="success" className="text-sm">
                    {messages.degerlendirme.successMessage}
                  </Alert>
                  <Link href={backHref} className={BACK_BUTTON_CLASS}>
                    {messages.degerlendirme.backLink}
                  </Link>
                </>
              ) : (
                <EvaluationForm engagementId={id} onSubmitted={() => setJustSubmitted(true)} />
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
