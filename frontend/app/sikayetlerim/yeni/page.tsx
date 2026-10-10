"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { createComplaint, uploadAttachment, type ComplaintSubjectType } from "@/lib/api/complaints";
import { ApiError } from "@/lib/api/errors";
import {
  complaintFormSchema,
  validateAttachment,
  MAX_ATTACHMENTS,
  type ComplaintFormValues,
} from "@/lib/complaints/rules";
import messages from "@/messages/tr.json";

const t = messages.complaints;

function parseSubjectType(value: string | null): ComplaintSubjectType | null {
  return value === "ENGAGEMENT" || value === "CERTIFICATE_CHECK" ? value : null;
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) return t.errors.rateLimited;
    if (err.status === 404) return t.errors.notFound;
    if (err.code === "TOO_EARLY") return t.errors.TOO_EARLY;
    if (err.code === "ALREADY_OPEN") return t.errors.ALREADY_OPEN;
    if (err.code === "NOT_PENDING") return t.errors.NOT_PENDING;
  }
  return messages.errors.generic;
}

/** C8: şikayet formu. Konu (subject_type/subject_id) sorgu parametresinden gelir. */
function YeniSikayetContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const params = useSearchParams();
  const subjectType = parseSubjectType(params?.get("subject_type") ?? null);
  const subjectId = params?.get("subject_id") ?? null;

  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [partialId, setPartialId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ComplaintFormValues>({
    resolver: zodResolver(complaintFormSchema),
    defaultValues: { description: "" },
  });

  const submit = useMutation({
    mutationFn: async (values: ComplaintFormValues) => {
      if (!subjectType || !subjectId) throw new Error("missing subject");
      const created = await createComplaint({
        subject_type: subjectType,
        subject_id: subjectId,
        description: values.description,
      });
      let failed = false;
      for (const file of files) {
        try {
          await uploadAttachment(created.id, file);
        } catch {
          failed = true;
        }
      }
      return { id: created.id, failed };
    },
    onSuccess: async ({ id, failed }) => {
      await queryClient.invalidateQueries({ queryKey: ["complaints"] });
      if (failed) setPartialId(id);
      else router.push(`/sikayetlerim/${encodeURIComponent(id)}`);
    },
  });

  function onFilesChange(list: FileList | null) {
    setFileError(null);
    const picked = Array.from(list ?? []);
    const next = [...files, ...picked];
    if (next.length > MAX_ATTACHMENTS) {
      setFileError(t.validation.fileCount);
      return;
    }
    for (const file of picked) {
      const problem = validateAttachment(file);
      if (problem) {
        setFileError(t.validation[problem]);
        return;
      }
    }
    setFiles(next);
  }

  const canSubmit = !!subjectType && !!subjectId;

  return (
    <AppShell>
      <main className="mx-auto max-w-2xl p-6">
        <h1 className="mb-2 text-2xl font-bold">{t.form.title}</h1>
        <p className="mb-6 text-sm text-muted-foreground">{t.form.intro}</p>

        {!canSubmit ? (
          <div role="alert" className="rounded-md border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
            {t.form.missingSubject}
          </div>
        ) : partialId ? (
          <div role="alert" className="rounded-md border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
            <p>{t.errors.attachmentFailed}</p>
            <Link
              href={`/sikayetlerim/${encodeURIComponent(partialId)}`}
              className="mt-2 inline-block font-medium underline underline-offset-4"
            >
              {t.detail.viewDetail}
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit((values) => submit.mutate(values))}
            noValidate
            className="space-y-5"
          >
            <p className="text-sm">
              <span className="font-medium">{t.form.subjectLabel}: </span>
              {t.subjectType[subjectType]}
            </p>

            <div>
              <label htmlFor="complaint-description" className="mb-1 block text-sm font-medium">
                {t.form.descriptionLabel}
              </label>
              <textarea
                id="complaint-description"
                rows={6}
                aria-describedby="complaint-description-hint complaint-description-error"
                aria-invalid={errors.description ? true : undefined}
                className="block w-full rounded-md border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-success/25"
                {...register("description")}
              />
              <p id="complaint-description-hint" className="mt-1 text-xs text-muted-foreground">
                {t.form.descriptionHint}
              </p>
              <p id="complaint-description-error" role="alert" className="mt-1 text-xs text-destructive">
                {errors.description?.message
                  ? (t.validation as Record<string, string>)[errors.description.message] ?? errors.description.message
                  : null}
              </p>
            </div>

            <div>
              <label htmlFor="complaint-files" className="mb-1 block text-sm font-medium">
                {t.form.attachmentsLabel}
              </label>
              <input
                id="complaint-files"
                type="file"
                multiple
                accept="application/pdf,image/jpeg,image/png"
                onChange={(e) => {
                  onFilesChange(e.target.files);
                  e.target.value = "";
                }}
                className="block w-full text-sm"
              />
              <p className="mt-1 text-xs text-muted-foreground">{t.form.attachmentsHint}</p>
              <p role="alert" className="mt-1 text-xs text-destructive">
                {fileError}
              </p>
              {files.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {files.map((file, index) => (
                    <li key={`${file.name}-${index}`} className="flex items-center justify-between text-sm">
                      <span className="truncate">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => setFiles(files.filter((_, i) => i !== index))}
                        className="text-xs text-destructive underline"
                      >
                        {t.form.removeFile}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {submit.isError && (
              <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {errorMessage(submit.error)}
              </div>
            )}

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={submit.isPending}>
                {submit.isPending ? t.form.submitting : t.form.submit}
              </Button>
              <Link href="/sikayetlerim" className="text-sm underline underline-offset-4">
                {t.form.back}
              </Link>
            </div>
          </form>
        )}
      </main>
    </AppShell>
  );
}

// useSearchParams() needs a Suspense boundary, otherwise `next build` fails while prerendering.
export default function YeniSikayetPage() {
  return (
    <Suspense fallback={null}>
      <YeniSikayetContent />
    </Suspense>
  );
}
