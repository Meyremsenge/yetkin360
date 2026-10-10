"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { updateTalentAbout } from "@/lib/api/client";
import { ABOUT_MAX_LENGTH } from "@/lib/api/portfolio";
import { SESSION_QUERY_KEY } from "@/lib/session/use-session";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ProfileSection, labelClass, primaryButtonClass } from "./profile-ui";

const t = messages.profil;

// Raw length, same measure as the server's max_length check (before trimming).
const aboutSchema = z.object({
  about: z.string().max(ABOUT_MAX_LENGTH, t.aboutTooLong.replace("{max}", String(ABOUT_MAX_LENGTH))),
});
type AboutForm = z.infer<typeof aboutSchema>;

type Status = "idle" | "saved" | "error";

/** "Hakkımda": the student's own words. Always labelled as a claim, never as verified. */
export default function AboutSection({ initialAbout }: { initialAbout: string | null }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>("idle");
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<AboutForm>({
    resolver: zodResolver(aboutSchema),
    defaultValues: { about: initialAbout ?? "" },
  });

  const length = useWatch({ control, name: "about" })?.length ?? 0;
  const over = length > ABOUT_MAX_LENGTH;

  const onSubmit = async (data: AboutForm) => {
    setStatus("idle");
    try {
      await updateTalentAbout(data.about);
      reset({ about: data.about.trim() });
      setStatus("saved");
      await queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    } catch {
      setStatus("error");
    }
  };

  return (
    <ProfileSection title={t.aboutTitle} description={t.aboutDescription}>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="about-text" className={cn(labelClass, "mb-0")}>
            {t.aboutLabel}
          </label>
          <span className="inline-flex items-center rounded-full border border-dashed border-border bg-sand/60 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
            {messages.publicProfile.selfDeclared}
          </span>
        </div>
        <textarea
          id="about-text"
          rows={6}
          placeholder={t.aboutPlaceholder}
          aria-describedby="about-counter about-kvkk"
          aria-invalid={over || undefined}
          className={cn(
            "mt-1.5 block w-full resize-y rounded-md border border-border bg-card px-3 py-2 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/70",
            "hover:border-muted-foreground/40 focus-visible:border-success focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/25",
            over && "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/25"
          )}
          {...register("about")}
        />
        <div className="mt-1.5 flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <p id="about-kvkk" className="text-xs text-muted-foreground">
            {t.aboutKvkkNote} {t.aboutPublicNote}
          </p>
          <p
            id="about-counter"
            className={cn("font-mono text-xs tabular-nums", over ? "text-destructive" : "text-muted-foreground")}
          >
            {t.aboutCounter.replace("{n}", String(length)).replace("{max}", String(ABOUT_MAX_LENGTH))}
          </p>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <Button type="submit" size="sm" disabled={isSubmitting || over || !isDirty} className={primaryButtonClass}>
            {isSubmitting ? t.aboutSaving : t.aboutSave}
          </Button>
          <p aria-live="polite" className="text-sm">
            {errors.about ? (
              <span className="text-destructive">{errors.about.message}</span>
            ) : status === "saved" ? (
              <span className="text-success">{t.aboutSaved}</span>
            ) : status === "error" ? (
              <span className="text-destructive">{t.aboutError}</span>
            ) : null}
          </p>
        </div>
      </form>
    </ProfileSection>
  );
}
