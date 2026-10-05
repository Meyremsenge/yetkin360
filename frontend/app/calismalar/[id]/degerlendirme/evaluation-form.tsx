"use client";

import { useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import {
  evaluationFormSchema,
  type EvaluationFormData,
  type EvaluationRating,
} from "@/lib/evaluation/schemas";
import { submitEvaluation } from "@/lib/api/evaluation";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";

/**
 * PLAN 2.13/YET-100/YET-101: Kurum tarafı değerlendirme formu.
 * items[] dinamik liste (useFieldArray) + rating (4 eşit seçenek, NOT_OBSERVED
 * dahil — D8) + private_note (kurum içi, öğrenciye gösterilmez — D9).
 */

const RATING_OPTIONS: EvaluationRating[] = ["BELOW", "MEETS", "EXCEEDS", "NOT_OBSERVED"];

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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-4">
        {fields.map((field, index) => (
          <div key={field.id} className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <Label htmlFor={`items.${index}.criterion`}>{messages.degerlendirme.criterionLabel}</Label>
                <Input
                  {...register(`items.${index}.criterion`)}
                  id={`items.${index}.criterion`}
                  placeholder={messages.degerlendirme.criterionPlaceholder}
                />
                {errors.items?.[index]?.criterion && (
                  <div className="text-xs text-red-600 mt-1">
                    {errors.items[index]?.criterion?.message}
                  </div>
                )}
              </div>
              {fields.length > 1 && (
                <Button
                  type="button"
                  onClick={() => remove(index)}
                  className="bg-red-600 hover:bg-red-700 px-3 py-1 text-xs mt-6"
                >
                  {messages.degerlendirme.removeItemButton}
                </Button>
              )}
            </div>

            <div className="mt-3">
              <Label>{messages.degerlendirme.ratingLabel}</Label>
              {/* D8: NOT_OBSERVED diğer üçüyle birebir eşit görünürlükte — ayrı/gizli değil. */}
              <div className="flex flex-wrap gap-4 mt-1">
                {RATING_OPTIONS.map((option) => (
                  <label key={option} className="flex items-center gap-1.5 text-sm text-slate-700">
                    <input type="radio" value={option} {...register(`items.${index}.rating`)} />
                    {messages.degerlendirme.rating[option]}
                  </label>
                ))}
              </div>
              {errors.items?.[index]?.rating && (
                <div className="text-xs text-red-600 mt-1">{errors.items[index]?.rating?.message}</div>
              )}
            </div>

            <div className="mt-3">
              <Label htmlFor={`items.${index}.comment`}>{messages.degerlendirme.commentLabel}</Label>
              <textarea
                {...register(`items.${index}.comment`)}
                id={`items.${index}.comment`}
                rows={2}
                className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
              />
            </div>
          </div>
        ))}
      </div>

      {errors.items?.message && <div className="text-xs text-red-600">{errors.items.message}</div>}

      <Button type="button" onClick={() => append(emptyItem())} className="bg-slate-600 hover:bg-slate-700">
        {messages.degerlendirme.addItemButton}
      </Button>

      <div className="border-t pt-4">
        <Label htmlFor="private_note">{messages.degerlendirme.privateNoteLabel}</Label>
        <p className="text-xs text-slate-500 mb-1">{messages.degerlendirme.privateNoteHint}</p>
        <textarea
          {...register("private_note")}
          id="private_note"
          rows={3}
          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
        />
        {errors.private_note && (
          <div className="text-xs text-red-600 mt-1">{errors.private_note.message}</div>
        )}
      </div>

      {rootError && (
        <div
          role="alert"
          aria-live="polite"
          className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
        >
          {rootError}
        </div>
      )}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? messages.degerlendirme.submittingButton : messages.degerlendirme.submitButton}
      </Button>
    </form>
  );
}
