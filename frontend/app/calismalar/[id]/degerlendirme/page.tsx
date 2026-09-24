"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { getEngagement } from "@/lib/api/engagements";
import { hasSubmittedEvaluation } from "@/lib/api/evaluation";
import { EvaluationForm } from "./evaluation-form";
import messages from "@/messages/tr.json";

export default function DegerlendirmePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [justSubmitted, setJustSubmitted] = useState(false);

  const { data: engagement, isLoading, isError } = useQuery({
    queryKey: ["engagement", id],
    queryFn: () => getEngagement(id),
  });

  const { data: alreadySubmitted, isLoading: isCheckingSubmitted } = useQuery({
    queryKey: ["evaluation-submitted", id],
    queryFn: () => hasSubmittedEvaluation(id, "ORG_TO_TALENT"),
    enabled: Boolean(engagement),
  });

  return (
    <AppShell>
      <div className="p-6 max-w-2xl mx-auto">
        <Link href={`/calismalar/${id}`} className="text-sm text-slate-600 hover:underline">
          ← {messages.degerlendirme.backLink}
        </Link>

        <h1 className="text-2xl font-bold mt-4 mb-6">{messages.degerlendirme.title}</h1>

        {isLoading || isCheckingSubmitted ? (
          <p className="text-slate-600">{messages.shell.loading}</p>
        ) : isError || !engagement ? (
          <div role="alert" className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {messages.calismalar.detailLoadError}
          </div>
        ) : engagement.status !== "PENDING_EVALUATION" ? (
          <div role="alert" className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.degerlendirme.notEligibleMessage}
          </div>
        ) : justSubmitted || alreadySubmitted ? (
          <div role="status" className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-700">
            {messages.degerlendirme.successMessage}
          </div>
        ) : (
          <EvaluationForm engagementId={id} onSubmitted={() => setJustSubmitted(true)} />
        )}
      </div>
    </AppShell>
  );
}
