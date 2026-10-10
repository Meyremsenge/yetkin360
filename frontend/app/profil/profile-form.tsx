"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { updateTalentProfile } from "@/lib/api/client";
import { SESSION_QUERY_KEY } from "@/lib/session/use-session";
import { talentProfileSchema, TalentProfileFormData } from "@/lib/talent/schemas";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { ProfileSection, fieldClass, labelClass, primaryButtonClass } from "./profile-ui";

interface ProfileFormProps {
  initialData: Record<string, unknown>;
}

// SPRINT H-0: "Kuruluşlar" visibility has no effect yet, so it is no longer offered.
// The backend still accepts it; a profile already set to it keeps the option (so a
// save does not silently change it) and is told it is effectively private for now.
const ORGANIZATIONS_VISIBILITY = "ORGANIZATIONS";

export default function ProfileForm({ initialData }: ProfileFormProps) {
  const queryClient = useQueryClient();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
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

  const hadOrganizationsVisibility = initialData.visibility === ORGANIZATIONS_VISIBILITY;
  const showsOrganizationsNotice = useWatch({ control, name: "visibility" }) === ORGANIZATIONS_VISIBILITY;

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
    <ProfileSection title={messages.profil.formSection} description={messages.profil.formDescription}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* General error banner */}
        {generalError && (
          <div
            role="alert"
            aria-live="polite"
            className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            {generalError}
          </div>
        )}

        {/* Success message */}
        {successMessage && (
          <div
            role="status"
            aria-live="polite"
            className="rounded-md border border-success/30 bg-success/10 px-4 py-3 text-sm text-success"
          >
            {successMessage}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="headline" className={labelClass}>{messages.profil.headline}</label>
            <input
              {...register("headline")}
              id="headline"
              type="text"
              placeholder="Yazılım Geliştirici"
              className={fieldClass}
            />
            <FieldError message={errors.headline?.message} />
          </div>

          <div>
            <label htmlFor="department" className={labelClass}>{messages.profil.department}</label>
            <input
              {...register("department")}
              id="department"
              type="text"
              placeholder="Mühendislik"
              className={fieldClass}
            />
            <FieldError message={errors.department?.message} />
          </div>

          <div>
            <label htmlFor="study_year" className={labelClass}>{messages.profil.studyYear}</label>
            <input
              {...register("study_year", { valueAsNumber: true })}
              id="study_year"
              type="number"
              min="0"
              max="10"
              placeholder="3"
              className={`${fieldClass} tabular-nums`}
            />
            <FieldError message={errors.study_year?.message} />
          </div>

          <div>
            <label htmlFor="city" className={labelClass}>{messages.profil.city}</label>
            <input
              {...register("city")}
              id="city"
              type="text"
              placeholder="İstanbul"
              className={fieldClass}
            />
            <FieldError message={errors.city?.message} />
          </div>

          <div>
            <label htmlFor="visibility" className={labelClass}>{messages.profil.visibility}</label>
            <select
              {...register("visibility")}
              id="visibility"
              aria-describedby={showsOrganizationsNotice ? "visibility-hint visibility-soon" : "visibility-hint"}
              className={fieldClass}
            >
              <option value="">Seçiniz</option>
              <option value="PRIVATE">Özel (Sadece Ben)</option>
              <option value="INSTITUTION">Kurum (Kurumum)</option>
              {hadOrganizationsVisibility && (
                <option value={ORGANIZATIONS_VISIBILITY}>{messages.profil.visibilityOrganizationsOption}</option>
              )}
              <option value="PUBLIC">Herkese Açık</option>
            </select>
            <p id="visibility-hint" className="mt-1 text-xs text-muted-foreground">
              {messages.profil.visibilityDiscoverHint}
            </p>
            {showsOrganizationsNotice && (
              <p id="visibility-soon" role="status" className="mt-1 text-xs text-warning">
                {messages.profil.visibilityOrganizationsSoon}
              </p>
            )}
            <FieldError message={errors.visibility?.message} />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="public_slug" className={labelClass}>{messages.profil.publicSlug}</label>
            <div className="flex">
              <span className="inline-flex h-10 items-center rounded-l-md border border-r-0 border-border bg-muted px-3 font-mono text-xs text-muted-foreground">
                {messages.profil.slugPrefix}
              </span>
              <input
                {...register("public_slug")}
                id="public_slug"
                type="text"
                placeholder="profil-linkim"
                className={`${fieldClass} rounded-l-none font-mono`}
              />
            </div>
            <FieldError message={errors.public_slug?.message} />
          </div>
        </div>

        {/* AC-11: Submit button with loading state */}
        <div className="pt-2">
          <Button type="submit" disabled={isSubmitting} className={primaryButtonClass}>
            {isSubmitting ? messages.profil.savingButton : messages.profil.saveButton}
          </Button>
        </div>
      </form>
    </ProfileSection>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <div aria-live="polite" className="mt-1.5 text-[13px] text-destructive">
      {message}
    </div>
  );
}
