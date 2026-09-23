"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { getEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { TransitionActions } from "./transition-actions";
import messages from "@/messages/tr.json";

export default function CalismaDetayPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const ENGAGEMENT_QUERY_KEY = ["engagement", id] as const;

  const { data: engagement, isLoading, isError, error } = useQuery({
    queryKey: ENGAGEMENT_QUERY_KEY,
    queryFn: () => getEngagement(id),
  });

  return (
    <AppShell>
      <div className="p-6 max-w-4xl mx-auto">
        <Link href="/calismalar" className="text-sm text-slate-600 hover:underline">
          ← {messages.calismalar.detailBackLink}
        </Link>

        {isLoading ? (
          <p className="text-slate-600 mt-4">{messages.shell.loading}</p>
        ) : isError ? (
          <div role="alert" className="mt-4 rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error instanceof ApiError && error.status === 404
              ? messages.calismalar.detailNotFound
              : messages.calismalar.detailLoadError}
          </div>
        ) : engagement ? (
          <>
            <h1 className="text-2xl font-bold mt-4 mb-2">{engagement.title}</h1>
            <div className="text-sm text-slate-600 mb-6">
              {messages.calismalar.kind[engagement.kind]} · {engagement.organization_name}
            </div>

            <dl className="grid grid-cols-2 gap-4 mb-6 bg-slate-50 p-4 rounded-md border border-slate-200">
              <div>
                <dt className="text-xs text-slate-500">{messages.calismalar.statusLabel}</dt>
                <dd className="font-medium">{messages.calismalar.status[engagement.status]}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">{messages.calismalar.updatedAtLabel}</dt>
                <dd className="font-medium">
                  {new Date(engagement.updated_at).toLocaleString("tr-TR")}
                </dd>
              </div>
            </dl>

            {engagement.reason && (
              <div className="mb-6 rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
                {messages.calismalar.reasonLabel}: {engagement.reason}
              </div>
            )}

            <TransitionActions
              engagement={engagement}
              onSuccess={() => queryClient.invalidateQueries({ queryKey: ENGAGEMENT_QUERY_KEY })}
            />

            <section className="mt-8">
              <h2 className="text-lg font-bold mb-3">{messages.calismalar.tasksTitle}</h2>
              {engagement.tasks.length === 0 ? (
                <p className="text-sm text-slate-600">{messages.calismalar.emptyTasksMessage}</p>
              ) : (
                <ul className="space-y-2">
                  {engagement.tasks.map((task) => (
                    <li key={task.id} className="bg-white p-3 rounded-md border border-slate-200 text-sm">
                      {task.title} <span className="text-slate-500">({task.status})</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="mt-8">
              <h2 className="text-lg font-bold mb-3">{messages.calismalar.deliverablesTitle}</h2>
              {engagement.deliverables.length === 0 ? (
                <p className="text-sm text-slate-600">{messages.calismalar.emptyDeliverablesMessage}</p>
              ) : (
                <ul className="space-y-2">
                  {engagement.deliverables.map((deliverable) => (
                    <li
                      key={deliverable.id}
                      className="bg-white p-3 rounded-md border border-slate-200 text-sm"
                    >
                      {deliverable.title}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
