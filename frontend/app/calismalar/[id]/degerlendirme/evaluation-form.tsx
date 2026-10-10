"use client";

import { useState } from "react";
import { useForm, useFieldArray, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import {
  evaluationFormSchema,
  type EvaluationFormData,
  type EvaluationRating,
} from "@/lib/evaluation/schemas";
import { submitEvaluation } from "@/lib/api/evaluation";
import { ApiError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

/**
 * PLAN 2.13/YET-100/YET-101: Kurum tarafı değerlendirme formu.
 * items[] dinamik liste (useFieldArray) + rating (4 eşit seçenek, NOT_OBSERVED
 * dahil — D8) + private_note (kurum içi, öğrenciye gösterilmez — D9).
 */

const RATING_OPTIONS: EvaluationRating[] = ["BELOW", "MEETS", "EXCEEDS", "NOT_OBSERVED"];

const FIELD_CLASS =
  "block w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";
const LABEL_CLASS = "mb-1 block text-sm font-medium text-foreground";
const ERROR_CLASS = "mt-1 text-xs text-destructive";

const fill = (template: string, n: number) => template.replace("{n}", String(n));

const emptyItem = () => ({ criterion: "", rating: "NOT_OBSERVED" as EvaluationRating, comment: "" });

export function EvaluationForm({
  engagementId,
  onSubmitted,
}: {
  engagementId: string;
  onSubmitted: () => void;
}) {
  const [rootError, setRootError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EvaluationFormData>({
    resolver: zodResolver(evaluationFormSchema),
    defaultValues: {
      items: [emptyItem()],
      private_note: "",
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "items" });
  const watchedItems = useWatch({ control, name: "items" });

  const onSubmit = async (data: EvaluationFormData) => {
    setRootError(null);
    try {
      await submitEvaluation(engagementId, "ORG_TO_TALENT", data);
      onSubmitted();
    } catch (error) {
      if (error instanceof ApiError) {
        // Backend hem "zaten değerlendirilmiş" hem "artık PENDING_EVALUATION değil"
        // durumlarını AYNI kodla (409 CONFLICT) döner — ikisi de tek bir mesaj,
        // ve engagement query'si yeniden çekilir ki sayfa güncel duruma göre
        // formu gizleyip uygun mesajı göstersin (bkz. degerlendirme/page.tsx).
        if (error.code === "CONFLICT") {
          setRootError(messages.degerlendirme.conflictError);
          queryClient.invalidateQueries({ queryKey: ["engagement", engagementId] });
          return;
        }
        if (error.code === "FORBIDDEN") {
          setRootError(messages.calismalar.transitionForbiddenError);
          return;
        }
      }
      setRootError(messages.errors.generic);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div className="space-y-4">
        {fields.map((field, index) => (
          <section key={field.id} className="y360-step-in rounded-xl border border-border bg-card p-5">
            <div className="flex items-start justify-between gap-4">
              <span className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                <span
                  aria-hidden="true"
                  className="flex h-6 w-6 items-center justify-center rounded-full border border-border bg-background text-foreground"
                >
                  {index + 1}
                </span>
                {fill(messages.degerlendirme.criterionCaption, index + 1)}
              </span>
              {fields.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => remove(index)}
                  aria-label={fill(messages.degerlendirme.removeItemAria, index + 1)}
                  className="-mt-1 inline-flex items-center gap-1.5 text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                >
                  <svg
                    viewBox="0 0 24 24"
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6" />
                  </svg>
                  {messages.degerlendirme.removeItemButton}
                </Button>
              )}
            </div>

            <div className="mt-2">
              <label htmlFor={`items.${index}.criterion`} className={LABEL_CLASS}>
                {messages.degerlendirme.criterionLabel}
              </label>
              <input
                {...register(`items.${index}.criterion`)}
                id={`items.${index}.criterion`}
                placeholder={messages.degerlendirme.criterionPlaceholder}
                aria-invalid={errors.items?.[index]?.criterion ? true : undefined}
                className={FIELD_CLASS}
              />
              {errors.items?.[index]?.criterion && (
                <div role="alert" className={ERROR_CLASS}>
                  {errors.items[index]?.criterion?.message}
                </div>
              )}
            </div>

            <fieldset className="mt-4">
              <legend className={LABEL_CLASS}>{messages.degerlendirme.ratingLabel}</legend>
              {/* D8: NOT_OBSERVED diğer üçüyle birebir eşit görünürlükte — ayrı/gizli değil. */}
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {RATING_OPTIONS.map((option) => {
                  const selected = watchedItems?.[index]?.rating === option;
                  return (
                    <label
                      key={option}
                      className={cn(
                        "flex min-h-10 cursor-pointer items-center justify-center rounded-md border px-3 py-2 text-center text-sm font-medium focus-within:ring-2 focus-within:ring-success",
                        selected
                          ? "border-success bg-success/10 text-success"
                          : "border-border bg-card text-foreground hover:bg-muted",
                      )}
                    >
                      <input
                        type="radio"
                        value={option}
                        className="sr-only"
                        {...register(`items.${index}.rating`)}
                      />
                      {messages.degerlendirme.rating[option]}
                    </label>
                  );
                })}
              </div>
              {errors.items?.[index]?.rating && (
                <div role="alert" className={ERROR_CLASS}>
                  {errors.items[index]?.rating?.message}
                </div>
              )}
            </fieldset>

            <div className="mt-4">
              <label htmlFor={`items.${index}.comment`} className={LABEL_CLASS}>
                {messages.degerlendirme.commentLabel}
              </label>
              <textarea
                {...register(`items.${index}.comment`)}
                id={`items.${index}.comment`}
                rows={2}
                className={FIELD_CLASS}
              />
            </div>
          </section>
        ))}
      </div>

      {errors.items?.message && (
        <div role="alert" className={ERROR_CLASS}>
          {errors.items.message}
        </div>
      )}

      <div className="mt-4">
        <Button
          type="button"
          variant="secondary"
          onClick={() => append(emptyItem())}
          className="inline-flex items-center gap-2 border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          {messages.degerlendirme.addItemButton}
        </Button>
      </div>

      <section className="mt-8 rounded-xl border border-border bg-sand/60 p-5">
        <label
          htmlFor="private_note"
          className="mb-2 flex items-center gap-2 text-base font-semibold text-foreground"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="5" y="11" width="14" height="9" rx="2" />
            <path d="M8 11V8a4 4 0 018 0v3" />
          </svg>
          {messages.degerlendirme.privateNoteLabel}
        </label>
        <textarea {...register("private_note")} id="private_note" rows={3} className={FIELD_CLASS} />
        <p className="mt-2 text-[13px] text-muted-foreground">
          {messages.degerlendirme.privateNoteHint}
        </p>
        {errors.private_note && (
          <div role="alert" className={ERROR_CLASS}>
            {errors.private_note.message}
          </div>
        )}
      </section>

      {rootError && (
        <Alert variant="error" className="mt-6 text-sm">
          {rootError}
        </Alert>
      )}

      <div className="sticky bottom-0 z-10 mt-8 flex items-center justify-between gap-4 border-t border-border bg-background py-4">
        <span className="text-[13px] text-muted-foreground">
          {fill(messages.degerlendirme.criteriaCount, fields.length)}
        </span>
        <Button
          type="submit"
          disabled={isSubmitting}
          className="bg-success text-background hover:bg-success/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 disabled:opacity-60 max-md:flex-1"
        >
          {isSubmitting ? messages.degerlendirme.submittingButton : messages.degerlendirme.submitButton}
        </Button>
      </div>
    </form>
  );
}
