"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { updateTalentProfile } from "@/lib/api/client";
import { SESSION_QUERY_KEY } from "@/lib/session/use-session";
import { talentProfileSchema, TalentProfileFormData } from "@/lib/talent/schemas";
import messages from "@/messages/tr.json";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface ProfileFormProps {
  initialData: Record<string, unknown>;
}

export default function ProfileForm({ initialData }: ProfileFormProps) {
  const queryClient = useQueryClient();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<TalentProfileFormData>({
    resolver: zodResolver(talentProfileSchema),
    defaultValues: {
      headline: (initialData.headline as string | null | undefined) ?? undefined,
      department: (initialData.department as string | null | undefined) ?? undefined,
      study_year: (initialData.study_year as number | null | undefined) ?? undefined,
      city: (initialData.city as string | null | undefined) ?? undefined,
      // AC-S3: Keep backend value for visibility
      visibility: (initialData.visibility as "PRIVATE" | "INSTITUTION" | "ORGANIZATIONS" | "PUBLIC" | null | undefined) ?? undefined,
      public_slug: (initialData.public_slug as string | null | undefined) ?? undefined,
    },
  });

  const onSubmit = async (data: TalentProfileFormData) => {
    try {
      setSuccessMessage(null);
      setGeneralError(null);

      // Call updateTalentProfile with positional parameters
      await updateTalentProfile(
        data.headline ?? null,
        data.department ?? null,
        data.study_year ?? null,
        data.city ?? null,
        data.visibility ?? null,
        data.public_slug ?? null
      );

      // Success: invalidate session cache and show message
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
      setSuccessMessage(messages.profil.successMessage);

      // Clear message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      // Duck-typing error handling (no instanceof)
      if (error && typeof error === "object") {
        const errObj = error as Record<string, unknown>;

        // AC-3: 409 SLUG_TAKEN → show error under public_slug field
        if (errObj.status === 409 && errObj.code === "SLUG_TAKEN") {
          setError("public_slug", {
            message: messages.errors.slugTaken,
          });
        } else if ("status" in errObj) {
          // Has status but doesn't match above — generic error
          setGeneralError(messages.errors.generic);
        } else {
          // No status property — network error
          setGeneralError(messages.errors.network);
        }
      } else {
        // Generic unknown error
        setGeneralError(messages.errors.generic);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 rounded-md bg-slate-50 p-6 border border-slate-200">
      {/* General error banner */}
      {generalError && (
        <div
          role="alert"
          aria-live="polite"
          className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
        >
          {generalError}
        </div>
      )}

      {/* Success message */}
      {successMessage && (
        <div
          role="status"
          aria-live="polite"
          className="rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-600"
        >
          {successMessage}
        </div>
      )}

      {/* Headline field */}
      <div>
        <Label htmlFor="headline">{messages.profil.headline}</Label>
        <Input
          {...register("headline")}
          id="headline"
          type="text"
          placeholder="Yazılım Geliştirici"
        />
        {errors.headline && (
          <div className="text-xs text-red-600 mt-1">{errors.headline.message}</div>
        )}
      </div>

      {/* Department field */}
      <div>
        <Label htmlFor="department">{messages.profil.department}</Label>
        <Input
          {...register("department")}
          id="department"
          type="text"
          placeholder="Mühendislik"
        />
        {errors.department && (
          <div className="text-xs text-red-600 mt-1">{errors.department.message}</div>
        )}
      </div>

      {/* Study Year field */}
      <div>
        <Label htmlFor="study_year">{messages.profil.studyYear}</Label>
        <Input
          {...register("study_year", { valueAsNumber: true })}
          id="study_year"
          type="number"
          min="0"
          max="10"
          placeholder="3"
        />
        {errors.study_year && (
          <div className="text-xs text-red-600 mt-1">{errors.study_year.message}</div>
        )}
      </div>

      {/* City field */}
      <div>
        <Label htmlFor="city">{messages.profil.city}</Label>
        <Input
          {...register("city")}
          id="city"
          type="text"
          placeholder="İstanbul"
        />
        {errors.city && (
          <div className="text-xs text-red-600 mt-1">{errors.city.message}</div>
        )}
      </div>

      {/* Visibility field */}
      <div>
        <Label htmlFor="visibility">{messages.profil.visibility}</Label>
        <select
          {...register("visibility")}
          id="visibility"
          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
        >
          <option value="">Seçiniz</option>
          <option value="PRIVATE">Özel (Sadece Ben)</option>
          <option value="INSTITUTION">Kurum (Kurumum)</option>
          <option value="ORGANIZATIONS">Kuruluşlar</option>
          <option value="PUBLIC">Herkese Açık</option>
        </select>
        {errors.visibility && (
          <div className="text-xs text-red-600 mt-1">{errors.visibility.message}</div>
        )}
      </div>

      {/* Public Slug field */}
      <div>
        <Label htmlFor="public_slug">{messages.profil.publicSlug}</Label>
        <Input
          {...register("public_slug")}
          id="public_slug"
          type="text"
          placeholder="profil-linkim"
        />
        {errors.public_slug && (
          <div className="text-xs text-red-600 mt-1">{errors.public_slug.message}</div>
        )}
      </div>

      {/* AC-11: Submit button with loading state */}
      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full"
      >
        {isSubmitting ? messages.profil.savingButton : messages.profil.saveButton}
      </Button>
    </form>
  );
}
