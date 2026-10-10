"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createPortfolioItem,
  deletePortfolioItem,
  listPortfolio,
  updatePortfolioItem,
  type EngagementCertificate,
  type PortfolioBadge,
  type PortfolioItem,
  type PortfolioItemInput,
} from "@/lib/api/portfolio";
import { recordEvidence, requestUploadUrl, uploadFileToStorage, validateFile } from "@/lib/api/evidence";
import { ApiError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { VerifiedSeal } from "@/components/ui/verified-seal";
import { cn } from "@/lib/utils";
import { EmptyNote, ProfileSection, SkeletonRows, fieldClass, focusRingClass, labelClass, primaryButtonClass } from "./profile-ui";

const t = messages.profil;
const PORTFOLIO_QUERY_KEY = ["talent-portfolio"] as const;
const providerLabels = t.providers as Record<string, string>;

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "PORTFOLIO_LIMIT_REACHED") return t.portfolioLimit;
    if (err.code === "EVIDENCE_ALREADY_IN_PORTFOLIO") return t.portfolioAlreadyLinked;
  }
  return t.portfolioError;
}

function formatMonth(isoDate: string): string {
  return new Intl.DateTimeFormat("tr-TR", { year: "numeric", month: "long" }).format(new Date(`${isoDate}T00:00:00`));
}

function hostOf(url: string): string | null {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}

/** Badge chip: confirmed is pine + seal-free check, self-declared is dashed sand, rejected is brick. */
export function PortfolioBadgeChip({ badge }: { badge: PortfolioBadge }) {
  const styles: Record<PortfolioBadge, string> = {
    COORDINATOR_CONFIRMED: "border-success/40 bg-success/10 text-success",
    SELF_DECLARED: "border-dashed border-border bg-sand/60 text-muted-foreground",
    COORDINATOR_REJECTED: "border-destructive/30 bg-destructive/10 text-destructive",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium", styles[badge])}>
      {(t.portfolioBadge as Record<string, string>)[badge]}
    </span>
  );
}

function ConsentSwitch({ item }: { item: PortfolioItem }) {
  const queryClient = useQueryClient();
  const [failed, setFailed] = useState(false);
  const mutation = useMutation({
    mutationFn: (next: boolean) => updatePortfolioItem(item.id, { show_on_profile: next }),
    onMutate: () => setFailed(false),
    onError: () => setFailed(true),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PORTFOLIO_QUERY_KEY }),
  });
  const labelId = `portfolio-consent-${item.id}`;
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        role="switch"
        aria-checked={item.show_on_profile}
        aria-labelledby={labelId}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(!item.show_on_profile)}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors disabled:opacity-50",
          item.show_on_profile ? "border-success bg-success" : "border-border bg-muted",
          focusRingClass
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "inline-block h-3.5 w-3.5 rounded-full bg-card shadow-sm transition-transform motion-reduce:transition-none",
            item.show_on_profile ? "translate-x-[18px]" : "translate-x-[2px]"
          )}
        />
      </button>
      <span id={labelId} className="text-sm text-foreground" title={t.portfolioShowHint}>
        {t.portfolioShowOnProfile}
      </span>
      <span aria-live="polite" className="text-[13px] text-destructive empty:hidden">
        {failed ? t.portfolioError : ""}
      </span>
    </div>
  );
}

function PortfolioRow({ item }: { item: PortfolioItem }) {
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => deletePortfolioItem(item.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PORTFOLIO_QUERY_KEY }),
  });
  const confirmed = item.badge === "COORDINATOR_CONFIRMED";
  const host = item.external_url ? hostOf(item.external_url) : null;
  const meta = [item.issuer, item.issued_on ? formatMonth(item.issued_on) : null].filter(Boolean).join(" · ");

  return (
    <li
      className={cn(
        "rounded-md border p-4",
        confirmed ? "border-success/40 bg-success/5" : "border-dashed border-border bg-card"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
            {(t.portfolioKind as Record<string, string>)[item.kind]}
          </p>
          <p className="mt-0.5 flex items-center gap-2 font-medium text-foreground">
            {confirmed ? <VerifiedSeal size="sm" label={t.portfolioBadge.COORDINATOR_CONFIRMED} /> : null}
            <span className="break-words">{item.title}</span>
          </p>
          {meta ? <p className="text-sm text-muted-foreground">{meta}</p> : null}
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {item.credential_id ? <span className="font-mono">{item.credential_id}</span> : null}
            {host ? <span className="font-mono">{host} ↗</span> : null}
            {item.evidence_id ? <span>{t.portfolioHasFile}</span> : null}
          </div>
        </div>
        <PortfolioBadgeChip badge={item.badge} />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <ConsentSwitch item={item} />
        <button
          type="button"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
          aria-label={t.portfolioDeleteLabel.replace("{title}", item.title)}
          className={cn("text-sm text-muted-foreground underline-offset-4 hover:text-destructive hover:underline disabled:opacity-50", focusRingClass)}
        >
          {t.portfolioDelete}
        </button>
      </div>
      {remove.isError ? (
        <p role="alert" className="mt-2 text-[13px] text-destructive">
          {errorMessage(remove.error)}
        </p>
      ) : null}
    </li>
  );
}

function EngagementCertificateRow({ cert }: { cert: EngagementCertificate }) {
  const queryClient = useQueryClient();
  const provider = cert.provider ? providerLabels[cert.provider] ?? cert.provider : providerLabels.UNKNOWN;
  const add = useMutation({
    mutationFn: () =>
      createPortfolioItem({
        kind: "CERTIFICATE",
        title: t.engagementCertDefaultTitle.replace("{provider}", provider),
        evidence_id: cert.evidence_id,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PORTFOLIO_QUERY_KEY }),
  });
  const decision = (t.engagementCertDecision as Record<string, string>)[cert.decision ?? "NONE"];

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{provider}</p>
        <p className="text-xs text-muted-foreground">
          {cert.credential_id ? <span className="mr-2 font-mono">{cert.credential_id}</span> : null}
          <span className={cn(cert.decision === "CONFIRMED" && "text-success", cert.decision === "REJECTED" && "text-destructive")}>
            {decision}
          </span>
        </p>
        {add.isError ? (
          <p role="alert" className="mt-1 text-[13px] text-destructive">
            {errorMessage(add.error)}
          </p>
        ) : null}
      </div>
      {cert.portfolio_item_id ? (
        <span className="text-sm text-success">{t.engagementCertAdded}</span>
      ) : (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={add.isPending || cert.decision === "REJECTED"}
          onClick={() => add.mutate()}
          className={focusRingClass}
        >
          {t.engagementCertAdd}
        </Button>
      )}
    </li>
  );
}

const todayMonth = () => new Date().toISOString().slice(0, 7);

const addSchema = z.object({
  kind: z.enum(["CERTIFICATE", "WORK"]),
  title: z.string().trim().min(1, t.portfolioTitleRequired).max(120),
  issuer: z.string().trim().max(120),
  issued_month: z
    .string()
    .refine((v) => v === "" || /^\d{4}-\d{2}$/.test(v), t.portfolioDateFormat)
    .refine((v) => v === "" || v <= todayMonth(), t.portfolioFutureDate),
  credential_id: z.string().trim().max(100),
  external_url: z
    .string()
    .trim()
    .max(500)
    .refine((v) => v === "" || /^https:\/\/[^\s/$.?#].[^\s]*$/i.test(v), t.portfolioUrlInvalid),
});
type AddForm = z.infer<typeof addSchema>;

const EMPTY_FORM: AddForm = { kind: "CERTIFICATE", title: "", issuer: "", issued_month: "", credential_id: "", external_url: "" };

/** Uploads the optional file through the existing secure flow (presigned POST → record, scanned by worker). */
async function uploadShowcaseFile(file: File, kind: AddForm["kind"]): Promise<string> {
  const validation = validateFile(file);
  if (!validation.ok) throw new Error(validation.message);
  const upload = await requestUploadUrl(file);
  await uploadFileToStorage(upload.upload_url, upload.upload_fields, file);
  const record = await recordEvidence({
    object_key: upload.object_key,
    kind: kind === "CERTIFICATE" ? "CERTIFICATE" : validation.kind,
    mime_type: file.type,
    size_bytes: file.size,
  });
  return record.id;
}

function AddPortfolioForm() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<"idle" | "uploading" | "saving">("idle");
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<AddForm>({ resolver: zodResolver(addSchema), defaultValues: EMPTY_FORM });
  const kind = useWatch({ control, name: "kind" });

  const pickFile = (candidate: File | undefined) => {
    setFormError(null);
    if (!candidate) return;
    const validation = validateFile(candidate);
    if (!validation.ok) {
      setFormError(validation.message);
      return;
    }
    setFile(candidate);
  };

  const onSubmit = async (data: AddForm) => {
    setFormError(null);
    try {
      let evidenceId: string | null = null;
      if (file) {
        setPhase("uploading");
        evidenceId = await uploadShowcaseFile(file, data.kind);
      }
      setPhase("saving");
      const input: PortfolioItemInput = {
        kind: data.kind,
        title: data.title,
        issuer: data.issuer || null,
        issued_on: data.issued_month ? `${data.issued_month}-01` : null,
        credential_id: data.credential_id || null,
        external_url: data.external_url || null,
        evidence_id: evidenceId,
      };
      await createPortfolioItem(input);
      reset(EMPTY_FORM);
      setFile(null);
      await queryClient.invalidateQueries({ queryKey: PORTFOLIO_QUERY_KEY });
    } catch (err) {
      setFormError(err instanceof ApiError ? errorMessage(err) : err instanceof Error && err.message ? err.message : t.portfolioError);
    } finally {
      setPhase("idle");
    }
  };

  const busy = phase !== "idle";
  const fieldError = (message?: string) =>
    message ? <p className="mt-1 text-xs text-destructive">{message}</p> : null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 border-t border-border pt-5" aria-labelledby="portfolio-add-title">
      <h3 id="portfolio-add-title" className="font-serif text-lg font-medium text-foreground">
        {t.portfolioAddTitle}
      </h3>

      <fieldset className="mt-3">
        <legend className={labelClass}>{t.portfolioKindLabel}</legend>
        <div className="inline-flex rounded-md border border-border bg-muted p-0.5">
          {(["CERTIFICATE", "WORK"] as const).map((value) => (
            <label
              key={value}
              className={cn(
                "cursor-pointer rounded px-3 py-1.5 text-sm transition-colors focus-within:ring-2 focus-within:ring-success",
                kind === value ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <input type="radio" value={value} className="sr-only" {...register("kind")} />
              {(t.portfolioKind as Record<string, string>)[value]}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor="portfolio-title" className={labelClass}>
            {t.portfolioTitleLabel}
          </label>
          <input id="portfolio-title" className={fieldClass} placeholder={t.portfolioTitlePlaceholder} aria-invalid={!!errors.title || undefined} {...register("title")} />
          {fieldError(errors.title?.message)}
        </div>
        <div>
          <label htmlFor="portfolio-issuer" className={labelClass}>
            {t.portfolioIssuerLabel}
          </label>
          <input id="portfolio-issuer" className={fieldClass} placeholder={t.portfolioIssuerPlaceholder} {...register("issuer")} />
        </div>
        <div>
          <label htmlFor="portfolio-issued" className={labelClass}>
            {t.portfolioIssuedOnLabel}
          </label>
          <input id="portfolio-issued" type="month" max={todayMonth()} className={fieldClass} aria-invalid={!!errors.issued_month || undefined} {...register("issued_month")} />
          {fieldError(errors.issued_month?.message)}
        </div>
        <div>
          <label htmlFor="portfolio-credential" className={labelClass}>
            {t.portfolioCredentialLabel}
          </label>
          <input id="portfolio-credential" className={cn(fieldClass, "font-mono")} {...register("credential_id")} />
        </div>
        <div>
          <label htmlFor="portfolio-url" className={labelClass}>
            {t.portfolioUrlLabel}
          </label>
          <input id="portfolio-url" type="url" inputMode="url" className={fieldClass} placeholder={t.portfolioUrlPlaceholder} aria-invalid={!!errors.external_url || undefined} {...register("external_url")} />
          {fieldError(errors.external_url?.message)}
        </div>
      </div>

      <div className="mt-4">
        <p className={labelClass}>{t.portfolioFileLabel}</p>
        <label
          htmlFor="portfolio-file"
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pickFile(e.dataTransfer.files?.[0]);
          }}
          className={cn(
            "flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-muted-foreground/30 bg-card px-4 py-4 text-sm transition-colors hover:border-success hover:bg-success/[0.04] focus-within:border-success focus-within:ring-2 focus-within:ring-success/25",
            dragging && "border-success bg-success/[0.06]",
            busy && "pointer-events-none opacity-60"
          )}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
            </svg>
          </span>
          <span className="min-w-0">
            <span className="block text-foreground">{file ? t.portfolioFileSelected.replace("{name}", file.name) : t.portfolioDropHint}</span>
            <span className="block text-xs text-muted-foreground">{t.portfolioFileHint}</span>
          </span>
        </label>
        {/* accept is a picker convenience only; validateFile() + the server's magic-byte check decide. */}
        <input
          id="portfolio-file"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.docx"
          className="sr-only"
          disabled={busy}
          onChange={(e) => {
            pickFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        {file ? (
          <button
            type="button"
            onClick={() => setFile(null)}
            className={cn("mt-1 text-xs text-muted-foreground underline-offset-4 hover:underline", focusRingClass)}
          >
            {t.portfolioFileRemove}
          </button>
        ) : null}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" disabled={busy} className={primaryButtonClass}>
          {phase === "uploading" ? t.portfolioUploading : phase === "saving" ? t.portfolioSubmitting : t.portfolioSubmit}
        </Button>
        <p className="text-xs text-muted-foreground">{t.portfolioShowHint}</p>
      </div>
      <p aria-live="polite" role="status" className="mt-2 text-sm text-destructive empty:hidden">
        {formError ?? ""}
      </p>
    </form>
  );
}

export default function PortfolioSection() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: PORTFOLIO_QUERY_KEY, queryFn: listPortfolio });
  const items = data?.items ?? [];
  const engagementCerts = data?.engagement_certificates ?? [];

  return (
    <ProfileSection title={t.portfolioTitle} description={t.portfolioDescription}>
      {isLoading ? <SkeletonRows rows={2} /> : null}
      {isError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span>{t.portfolioLoadError}</span>
          <Button variant="secondary" size="sm" onClick={() => refetch()} className={focusRingClass}>
            {t.retryButton}
          </Button>
        </div>
      ) : null}

      {!isLoading && !isError ? (
        items.length === 0 ? (
          <EmptyNote title={t.portfolioEmpty} hint={t.portfolioEmptyHint} />
        ) : (
          <ul className="space-y-3">
            {items.map((item) => (
              <PortfolioRow key={item.id} item={item} />
            ))}
          </ul>
        )
      ) : null}

      {engagementCerts.length > 0 ? (
        <div className="mt-6">
          <h3 className="font-serif text-lg font-medium text-foreground">{t.engagementCertsTitle}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{t.engagementCertsHint}</p>
          <ul className="mt-2 divide-y divide-border">
            {engagementCerts.map((cert) => (
              <EngagementCertificateRow key={cert.evidence_id} cert={cert} />
            ))}
          </ul>
        </div>
      ) : null}

      <AddPortfolioForm />
    </ProfileSection>
  );
}
