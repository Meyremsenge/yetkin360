"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { EmptyCard, FIELD_CLASS, LoadError, LoadingBlock, statusTone } from "@/components/admin/admin-ui";
import { PageBody, PageHeader } from "@/components/page-layout";
import { PanelGrid, PanelSection, StatusPill, actionClass } from "@/components/panel-kit";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ComplaintAttachmentLink } from "@/components/complaint-attachment-link";
import { adminGetComplaint, adminTransition, type ComplaintAction } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";
import { actionRequiresReason, allowedActions, transitionSchema } from "@/lib/complaints/rules";
import { formatDate } from "@/lib/complaints/format";
import messages from "@/messages/tr.json";

const t = messages.adminComplaints;

/** C8: admin şikayet detayı + geçiş düğmeleri. UPHOLD geri alınamaz → onay diyaloğu. */
export default function AdminSikayetDetayPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  const queryClient = useQueryClient();
  const QUERY_KEY = ["admin", "complaint", id] as const;

  const [action, setAction] = useState<ComplaintAction | null>(null);
  const [text, setText] = useState("");
  const [textError, setTextError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [done, setDone] = useState(false);

  const { data: complaint, isLoading, isError, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => adminGetComplaint(id),
    enabled: id !== "",
  });

  // Single dynamic field whose schema depends on the chosen action: plain Zod parse (see apply()).

  const transition = useMutation({
    mutationFn: (vars: { action: ComplaintAction; text: string }) =>
      adminTransition(id, {
        action: vars.action,
        // Optimistic lock: a decision by another admin since this page loaded is a 409 (AC-20).
        ...(typeof complaint?.version === "number" ? { version: complaint.version } : {}),
        ...(vars.text
          ? // Only REQUEST_EXPLANATION reads `note` server-side; every other action reads
            // `reason` (ACCEPT_EXPLANATION silently drops a `note`).
            vars.action === "REQUEST_EXPLANATION"
            ? { note: vars.text }
            : { reason: vars.text }
          : {}),
      }),
    onSuccess: async () => {
      setAction(null);
      setText("");
      setConfirming(false);
      setDone(true);
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: ["admin", "complaints"] });
    },
    onError: async (err) => {
      setConfirming(false);
      if (err instanceof ApiError && err.status === 409) {
        setAction(null);
        await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      }
    },
  });

  function choose(next: ComplaintAction) {
    setAction(next);
    setText("");
    setTextError(null);
    setConfirming(false);
    setDone(false);
    transition.reset();
  }

  function apply() {
    if (!action) return;
    const parsed = transitionSchema(action).safeParse({ text });
    if (!parsed.success) {
      setTextError(t.form.required);
      return;
    }
    setTextError(null);
    if (action === "UPHOLD" && !confirming) {
      setConfirming(true);
      return;
    }
    transition.mutate({ action, text: parsed.data.text });
  }

  const statusLabels = t.statusLabel as Record<string, string>;
  const actions = allowedActions(complaint?.status);
  const created = formatDate(complaint?.created_at);

  let errorText: string | null = null;
  if (transition.isError) {
    const err = transition.error;
    errorText =
      err instanceof ApiError && err.status === 409 ? t.errors.INVALID_TRANSITION : t.errors.generic;
  }

  return (
    <AppShell>
      <main>
        <PageHeader
          eyebrow={messages.shell.groupAdmin}
          title={t.title}
          back={{ href: "/admin/sikayetler", label: t.detail.back }}
        />
        <PageBody>
          <div aria-live="polite">
            {isLoading ? (
              <LoadingBlock label={t.loading} />
            ) : isError ? (
              <LoadError message={error instanceof ApiError && error.status === 404 ? t.notFound : t.loadError} />
            ) : !complaint ? (
              <EmptyCard icon="inbox" title={t.notFound} />
            ) : (
              <PanelGrid
                main={
                  <article className="space-y-6">
                    <section className="rounded-xl border border-border bg-card p-5">
                      <dl className="grid gap-4 text-sm sm:grid-cols-3">
                        <div>
                          <dt className="text-xs text-muted-foreground">{t.detail.status}</dt>
                          <dd className="mt-1">
                            <StatusPill tone={statusTone(complaint.status ?? "OPEN")}>
                              {(complaint.status && statusLabels[complaint.status]) || statusLabels.OPEN}
                            </StatusPill>
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs text-muted-foreground">{t.detail.subject}</dt>
                          <dd className="mt-1 font-medium text-foreground">
                            {(t.subjectType as Record<string, string>)[complaint.subject_type] ?? complaint.subject_type}
                            {complaint.subject_label ? ` - ${complaint.subject_label}` : ""}
                          </dd>
                        </div>
                        {created ? (
                          <div>
                            <dt className="text-xs text-muted-foreground">{t.detail.createdAt}</dt>
                            <dd className="mt-1 text-foreground">{created}</dd>
                          </div>
                        ) : null}
                      </dl>
                      {complaint.subject_still_pending === false && (
                        <p className="mt-4 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
                          {t.stalePending}
                        </p>
                      )}
                    </section>

                    {complaint.description ? (
                      <PanelSection icon="mail" title={t.detail.description}>
                        <p className="whitespace-pre-wrap text-[15px] leading-6 text-foreground">{complaint.description}</p>
                      </PanelSection>
                    ) : null}

                    <PanelSection icon="link" title={t.detail.attachments}>
                      {(complaint.attachments ?? []).length === 0 ? (
                        <p className="text-sm text-muted-foreground">{t.detail.noAttachments}</p>
                      ) : (
                        <ul className="space-y-1 text-sm">
                          {(complaint.attachments ?? []).map((att, index) => (
                            <li key={att.id}>
                              <ComplaintAttachmentLink
                                admin
                                complaintId={complaint.id}
                                attachmentId={att.id}
                                label={att.filename ?? `${t.detail.attachmentOpen} ${index + 1}`}
                                errorText={t.errors.downloadFailed}
                              />
                            </li>
                          ))}
                        </ul>
                      )}
                    </PanelSection>

                    <PanelSection icon="clipboard" title={t.detail.explanation}>
                      {complaint.explanation_text ? (
                        <p className="whitespace-pre-wrap text-[15px] leading-6 text-foreground">{complaint.explanation_text}</p>
                      ) : (
                        <p className="text-sm text-muted-foreground">{t.detail.noExplanation}</p>
                      )}
                    </PanelSection>

                    {(complaint.events ?? []).length > 0 && (
                      <PanelSection icon="clock" title={t.detail.history}>
                        <ul className="space-y-1.5 text-sm text-muted-foreground">
                          {(complaint.events ?? []).map((ev, index) => {
                            const when = formatDate(ev.created_at);
                            const parts = [
                              when,
                              ev.action,
                              ev.to_status ? (statusLabels[ev.to_status] ?? ev.to_status) : null,
                              ev.note,
                            ].filter(Boolean);
                            return <li key={ev.id ?? index}>{parts.join(" - ")}</li>;
                          })}
                        </ul>
                      </PanelSection>
                    )}
                  </article>
                }
                aside={
                  <section className="rounded-xl border border-border bg-card p-5">
                    <h2 className="mb-3 font-serif text-lg font-semibold text-foreground">{t.detail.actions}</h2>

                    {done && !transition.isError && (
                      <p role="status" className="mb-3 text-sm text-success">
                        {t.success}
                      </p>
                    )}
                    {errorText && (
                      <p role="alert" className="mb-3 text-sm text-destructive">
                        {errorText}
                      </p>
                    )}

                    {actions.length === 0 ? (
                      <p className="text-sm text-muted-foreground">{t.detail.noActions}</p>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {actions.map((a) => (
                          <button
                            key={a}
                            type="button"
                            aria-pressed={action === a}
                            onClick={() => choose(a)}
                            className={cn(
                              a === "UPHOLD" || a === "DISMISS" ? actionClass.dangerOutline : actionClass.neutral,
                              "w-full",
                              action === a && "ring-2 ring-success ring-offset-1"
                            )}
                          >
                            {t.actions[a]}
                          </button>
                        ))}
                      </div>
                    )}

                    {action && (
                      <div className="mt-4 space-y-2">
                        <label htmlFor="transition-text" className="block text-sm font-medium">
                          {actionRequiresReason(action)
                            ? action === "REQUEST_EXPLANATION"
                              ? t.form.noteLabel
                              : t.form.reasonLabel
                            : t.form.optionalLabel}
                        </label>
                        <textarea
                          id="transition-text"
                          rows={4}
                          value={text}
                          onChange={(e) => setText(e.target.value)}
                          aria-invalid={textError ? true : undefined}
                          className={cn(FIELD_CLASS, "h-auto py-2")}
                        />
                        <p role="alert" className="text-xs text-destructive">
                          {textError}
                        </p>
                        <button type="button" onClick={apply} disabled={transition.isPending} className={cn(actionClass.primary, "w-full")}>
                          {transition.isPending ? t.form.submitting : t.form.submit}
                        </button>
                      </div>
                    )}

                    {confirming && (
                      <div
                        role="alertdialog"
                        aria-modal="true"
                        aria-labelledby="uphold-confirm-title"
                        aria-describedby="uphold-confirm-body"
                        className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 p-4"
                      >
                        <h3 id="uphold-confirm-title" className="font-semibold">
                          {t.confirm.title}
                        </h3>
                        <p id="uphold-confirm-body" className="mt-1 text-sm">
                          {t.confirm.body}
                        </p>
                        <div className="mt-3 flex gap-2">
                          <Button
                            type="button"
                            variant="destructive"
                            disabled={transition.isPending}
                            onClick={() => transition.mutate({ action: "UPHOLD", text: text.trim() })}
                          >
                            {t.confirm.confirm}
                          </Button>
                          <Button type="button" variant="secondary" onClick={() => setConfirming(false)}>
                            {t.confirm.cancel}
                          </Button>
                        </div>
                      </div>
                    )}
                  </section>
                }
              />
            )}
          </div>
        </PageBody>
      </main>
    </AppShell>
  );
}
