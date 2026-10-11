"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { register as registerUser } from "@/lib/api/client";
import {
  accountKinds,
  registerSchema,
  requireCorporateEmailForOrganization,
  requireEntityNameForNonTalent,
  requireValidMersisWhenGiven,
  type AccountKind,
} from "@/lib/auth/schemas";
import { OrganizationDocumentCheck } from "./organization-document-check";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

const ACCOUNT_KIND_COPY: Record<AccountKind, { label: string; hint: string }> = {
  TALENT: { label: messages.kayit.accountKindTalent, hint: messages.kayit.accountKindTalentHint },
  ORGANIZATION: { label: messages.kayit.accountKindOrganization, hint: messages.kayit.accountKindOrganizationHint },
  INSTITUTION: { label: messages.kayit.accountKindInstitution, hint: messages.kayit.accountKindInstitutionHint },
};

// Form schema: base schema + password confirmation field
const registerFormSchema = registerSchema
  .extend({
    password_confirm: z.string().optional(),
  })
  .refine(
    (data) => {
      // If password_confirm is provided, it must match password
      if (data.password_confirm) {
        return data.password === data.password_confirm;
      }
      return true;
    },
    {
      message: "Şifreler eşleşmiyor",
      path: ["password_confirm"],
    }
  )
  .refine(requireEntityNameForNonTalent, {
    message: "Kuruluş/kurum adı gereklidir",
    path: ["entity_name"],
  })
  .refine(requireCorporateEmailForOrganization, {
    message: messages.kayit.corporateEmailRequired,
    path: ["email"],
  })
  .refine(requireValidMersisWhenGiven, {
    message: messages.kayit.mersisInvalid,
    path: ["legal_id"],
  });

type RegisterFormData = z.infer<typeof registerFormSchema>;

export default function RegisterForm({ showLocalEmailHint = false }: { showLocalEmailHint?: boolean }) {
  const router = useRouter();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerFormSchema),
    defaultValues: { account_kind: "TALENT" },
  });

  const accountKind = watch("account_kind");
  const entityName = watch("entity_name") ?? "";
  const legalId = watch("legal_id") ?? "";

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const mersis = data.account_kind === "ORGANIZATION" ? data.legal_id?.trim() : undefined;
      await registerUser(
        data.email,
        data.password,
        data.full_name,
        data.account_kind,
        data.account_kind === "TALENT" ? undefined : data.entity_name,
        ...(mersis ? [mersis] : [])
      );

      // Success: show message and redirect
      setSuccessMessage(
        data.account_kind === "ORGANIZATION" ? messages.kayit.successOrganization : messages.kayit.success
      );
      // With the local-email hint the user must read the message first; a link replaces the redirect.
      if (!showLocalEmailHint) setTimeout(() => router.push("/giris"), 800);
    } catch (error) {
      // Duck-typing: check for error object with status property
      if (error && typeof error === "object") {
        const errObj = error as Record<string, unknown>;

        if (errObj.status === 422 && errObj.fields) {
          // Field-specific validation errors
          const fields = errObj.fields as Record<string, string>;
          Object.entries(fields).forEach(([field, message]) => {
            setError(field as keyof RegisterFormData, {
              message,
            });
          });
        } else if (errObj.status === 409 && errObj.code === "LEGAL_ID_TAKEN") {
          setError("legal_id", { message: messages.kayit.mersisTaken });
        } else if (errObj.status === 429) {
          setError("root", {
            message: messages.errors.rateLimited,
          });
        } else if ("status" in errObj) {
          // Has status but doesn't match above — generic error
          setError("root", {
            message: messages.errors.generic,
          });
        } else {
          // No status property — network error
          setError("root", {
            message: messages.errors.network,
          });
        }
      } else {
        // Generic unknown error
        setError("root", {
          message: messages.errors.generic,
        });
      }
    }
  };

  if (successMessage) {
    return (
      <div role="status" className="rounded-md bg-green-50 border border-green-200 p-6 text-center">
        <p className="text-green-700">{successMessage}</p>
        {showLocalEmailHint && (
          <>
            <p className="mt-2 text-sm text-green-700">{messages.kayit.demoEmailHint}</p>
            <Link href="/giris" className="mt-3 inline-block text-sm font-medium text-green-800 underline underline-offset-2">
              {messages.home.loginLink}
            </Link>
          </>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-md bg-slate-50 p-6 border border-slate-200">
      <fieldset>
        <legend className="text-sm font-medium mb-2">{messages.kayit.accountKindLabel}</legend>
        <div className="grid grid-cols-3 gap-2">
          {accountKinds.map((kind) => {
            const selected = accountKind === kind;
            const copy = ACCOUNT_KIND_COPY[kind];
            return (
              <label
                key={kind}
                className={cn(
                  "flex min-h-16 cursor-pointer flex-col items-center justify-center gap-1 rounded-md border px-2 py-2 text-center focus-within:ring-2 focus-within:ring-success",
                  selected
                    ? "border-success bg-success/10 text-success"
                    : "border-border bg-card text-foreground hover:bg-muted"
                )}
              >
                <input type="radio" value={kind} className="sr-only" {...register("account_kind")} />
                <span className="text-sm font-medium">{copy.label}</span>
                <span className="text-xs text-muted-foreground">{copy.hint}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {accountKind !== "TALENT" && (
        <div>
          <Label htmlFor="entity_name">{accountKind === "INSTITUTION" ? messages.kayit.entityNameInstitution : messages.kayit.entityNameOrganization}</Label>
          <Input
            {...register("entity_name")}
            id="entity_name"
            type="text"
            placeholder={messages.kayit.accountKindOrganizationHint}
          />
          <p className="text-xs text-muted-foreground mt-1">{messages.kayit.entityNameHint}</p>
          {errors.entity_name && (
            <div className="text-xs text-red-600 mt-1">{errors.entity_name.message}</div>
          )}
        </div>
      )}

      {accountKind === "ORGANIZATION" && (
        <>
          <div>
            <Label htmlFor="legal_id">{messages.kayit.mersisLabel}</Label>
            <Input
              {...register("legal_id")}
              id="legal_id"
              type="text"
              inputMode="numeric"
              maxLength={16}
              autoComplete="off"
              aria-describedby="legal_id_hint"
            />
            <p id="legal_id_hint" className="text-xs text-muted-foreground mt-1">
              {messages.kayit.mersisHint}
            </p>
            {errors.legal_id && (
              <div aria-live="polite" className="text-xs text-red-600 mt-1">
                {errors.legal_id.message}
              </div>
            )}
          </div>

          <OrganizationDocumentCheck entityName={entityName} legalId={legalId} />
        </>
      )}

      <div>
        <Label htmlFor="email">{messages.kayit.emailLabel}</Label>
        <Input
          {...register("email")}
          id="email"
          type="email"
          placeholder={messages.giris.placeholder}
          autoComplete="email"
        />
        {accountKind === "ORGANIZATION" && (
          <p className="text-xs text-muted-foreground mt-1">{messages.kayit.corporateEmailHint}</p>
        )}
        {errors.email && (
          <div className="text-xs text-red-600 mt-1">{errors.email.message}</div>
        )}
      </div>

      <div>
        <Label htmlFor="password">{messages.kayit.passwordLabel}</Label>
        <Input
          {...register("password")}
          id="password"
          type="password"
          placeholder="Yeni şifre"
          autoComplete="new-password"
        />
        {errors.password && (
          <div className="text-xs text-red-600 mt-1">{errors.password.message}</div>
        )}
      </div>

      <div>
        <Label htmlFor="password_confirm">Şifre Tekrar</Label>
        <Input
          {...register("password_confirm")}
          id="password_confirm"
          type="password"
          placeholder="Şifre tekrar"
          autoComplete="new-password"
        />
        {errors.password_confirm && (
          <div className="text-xs text-red-600 mt-1">{errors.password_confirm.message}</div>
        )}
      </div>

      <div>
        <Label htmlFor="full_name">{messages.kayit.fullNameLabel}</Label>
        <Input
          {...register("full_name")}
          id="full_name"
          type="text"
          placeholder="Adı Soyadı"
          autoComplete="name"
        />
        {errors.full_name && (
          <div className="text-xs text-red-600 mt-1">{errors.full_name.message}</div>
        )}
      </div>

      {errors.root && (
        <div
          aria-live="polite"
          className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
        >
          {errors.root.message}
        </div>
      )}

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full"
      >
        {isSubmitting ? "..." : messages.kayit.submit}
      </Button>
    </form>
  );
}
