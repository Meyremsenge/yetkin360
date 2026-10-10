"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { ComplaintAttachmentLink } from "@/components/complaint-attachment-link";
import { getComplaint, submitExplanation } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";
import { explanationSchema, isTerminalStatus, type ExplanationFormValues } from "@/lib/complaints/rules";
import { formatDate } from "@/lib/complaints/format";
import { ComplaintStatusBadge } from "../status-badge";
import messages from "@/messages/tr.json";

const t = messages.complaints;

/**
 * C8 / C5: öğrenci için şikayet detayı; hakkında şikayet açılan yetkili için
 * yönetici notu + gerekçe formu. Yetkili ek göremez (AC-S9).
 */
export default function SikayetDetayPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  const queryClient = useQueryClient();
  const QUERY_KEY = ["complaint", id] as const;

  const { data: complaint, isLoading, isError, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => getComplaint(id),
    enabled: id !== "",
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExplanationFormValues>({
    resolver: zodResolver(explanationSchema),
    defaultValues: { text: "" },
  });

  const explain = useMutation({
    mutationFn: (values: ExplanationFormValues) => submitExplanation(id, values.text),
    onSuccess: async () => {
      reset();
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: ["complaints"] });
    },
  });

  const isRespondent = complaint?.viewer_role === "RESPONDENT";
  const terminal = !!complaint && isTerminalStatus(complaint.status_label);
  const created = formatDate(complaint?.created_at);
  const closed = formatDate(complaint?.closed_at);

  return (
    <AppShell>
      <main className="mx-auto max-w-3xl p-6">
        <Link href="/sikayetlerim" className="text-sm underline underline-offset-4">
          {t.detail.back}
        </Link>

        <div aria-live="polite" className="mt-4">
          {isLoading ? (
            <p className="text-muted-foreground">{t.loading}</p>
          ) : isError ? (
            <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {error instanceof ApiError && error.status === 404 ? t.notFound : t.loadError}
            </div>
          ) : !complaint ? (
            <p className="text-muted-foreground">{t.notFound}</p>
          ) : (
            <article className="space-y-5">
              <header>
                <h1 className="text-2xl font-bold">
                  {isRespondent ? t.explanation.respondentBadge : t.title}
                </h1>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
                  <span>
                    {t.subjectType[complaint.subject_type] ?? complaint.subject_type}
                    {complaint.subject_label ? `: ${complaint.subject_label}` : ""}
                  </span>
                  <ComplaintStatusBadge complaint={complaint} />
                </div>
                <dl className="mt-3 grid gap-1 text-xs text-muted-foreground">
                  {created ? (
                    <div>
                      <dt className="inline font-medium">{t.detail.createdAt}: </dt>
                      <dd className="inline">{created}</dd>
                    </div>
                  ) : null}
                  {closed ? (
                    <div>
                      <dt className="inline font-medium">{t.detail.closedAt}: </dt>
                      <dd className="inline">{closed}</dd>
                    </div>
                  ) : null}
                </dl>
              </header>

              {complaint.description ? (
                <section>
                  <h2 className="mb-1 text-sm font-semibold">{t.detail.description}</h2>
                  <p className="whitespace-pre-wrap text-sm">{complaint.description}</p>
                </section>
              ) : null}

              {!terminal && !isRespondent && (
                <p className="rounded-md border border-border bg-muted p-3 text-sm">{t.detail.inProgressNote}</p>
              )}

              {terminal && complaint.result_reason ? (
                <section>
                  <h2 className="mb-1 text-sm font-semibold">{t.detail.resultReason}</h2>
                  <p className="whitespace-pre-wrap text-sm">{complaint.result_reason}</p>
                </section>
              ) : null}

              {isRespondent && complaint.admin_note ? (
                <section>
                  <h2 className="mb-1 text-sm font-semibold">{t.detail.adminNote}</h2>
                  <p className="whitespace-pre-wrap text-sm">{complaint.admin_note}</p>
                </section>
              ) : null}

              {isRespondent && complaint.status === "EXPLANATION_REQUESTED" && (
                <section className="rounded-lg border border-border p-4">
                  <h2 className="font-semibold">{t.explanation.title}</h2>
                  <p className="mb-3 text-sm text-muted-foreground">{t.explanation.hint}</p>
                  <form onSubmit={handleSubmit((v) => explain.mutate(v))} noValidate className="space-y-3">
                    <label htmlFor="explanation-text" className="block text-sm font-medium">
                      {t.explanation.label}
                    </label>
                    <textarea
                      id="explanation-text"
                      rows={5}
                      aria-invalid={errors.text ? true : undefined}
                      className="block w-full rounded-md border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-success/25"
                      {...register("text")}
                    />
                    <p role="alert" className="text-xs text-destructive">
                      {errors.text?.message
                        ? ((t.explanation as Record<string, string>)[errors.text.message] ??
                          (t.validation as Record<string, string>)[errors.text.message] ??
                          errors.text.message)
                        : null}
                    </p>
                    {explain.isError && (
                      <p role="alert" className="text-sm text-destructive">
                        {messages.errors.generic}
                      </p>
                    )}
                    <Button type="submit" disabled={explain.isPending}>
                      {explain.isPending ? t.explanation.submitting : t.explanation.submit}
                    </Button>
                  </form>
                </section>
              )}

              {isRespondent && complaint.status === "EXPLANATION_SUBMITTED" && (
                <p className="rounded-md border border-border bg-muted p-3 text-sm">{t.explanation.waiting}</p>
              )}

              {!isRespondent && (
                <section>
                  <h2 className="mb-1 text-sm font-semibold">{t.detail.attachments}</h2>
                  {(complaint.attachments ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">{t.detail.noAttachments}</p>
                  ) : (
                    <ul className="space-y-1 text-sm">
                      {(complaint.attachments ?? []).map((att, index) => (
                        <li key={att.id}>
                          <ComplaintAttachmentLink
                            complaintId={complaint.id}
                            attachmentId={att.id}
                            label={att.filename ?? `${t.detail.download} ${index + 1}`}
                            errorText={t.errors.downloadFailed}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}
            </article>
          )}
        </div>
      </main>
    </AppShell>
  );
}
