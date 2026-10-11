"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { apiFetch, login } from "@/lib/api/client";
import { loginSchema, type LoginFormData } from "@/lib/auth/schemas";
import { sanitizeNext } from "@/lib/auth/sanitize-next";
import messages from "@/messages/tr.json";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { SESSION_QUERY_KEY } from "@/lib/session/use-session";
import { fetchMe } from "@/lib/session/fetch-me";
import { homePathFor } from "@/lib/session/roles";
import { DEMO_ACCOUNTS, DEMO_ADMIN_EMAIL, DEMO_PASSWORD, demoAccountsEnabled } from "@/lib/demo-accounts";
import { DEMO_ACCOUNTS_ANCHOR } from "@/components/ui/demo-accounts-link";

const DEFAULT_AFTER_LOGIN = "/calismalar";
const ADMIN_AFTER_LOGIN = "/admin/dogrulama-kuyrugu";
const ADMIN_ROLE = "PLATFORM_ADMIN";

const fieldClass =
  "y360-autofill h-11 bg-card border-border px-3.5 text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:border-success focus:ring-success/25 motion-reduce:transition-none";
const labelClass = "mb-1.5 text-foreground";
const fieldErrorClass = "mt-1.5 text-[13px] text-destructive";

function useQueryClientSafe() {
  try {
    return useQueryClient();
  } catch {
    return null;
  }
}

/**
 * `adminOnly` is the /admin/giris variant: same POST /auth/login, but a
 * non-admin account is signed straight back out and shown the generic
 * credentials error. This is UX only — every /admin/* request is still
 * decided on the server (require_platform_admin).
 */
export default function LoginForm({
  nextPath,
  adminOnly = false,
  showDemoAccounts = false,
  footer,
}: {
  nextPath?: string;
  adminOnly?: boolean;
  showDemoAccounts?: boolean;
  /** Rendered right under the submit button (e.g. register / forgot password links). */
  footer?: ReactNode;
}) {
  const router = useRouter();
  const queryClient = useQueryClientSafe();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    setValue,
    setFocus,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      const result = await login(data.email, data.password);
      const isAdmin = result?.role === ADMIN_ROLE;

      if (adminOnly && !isAdmin) {
        // Drop the session that was just created; a failed sign-out must not
        // hide the error from the user.
        await apiFetch("/auth/logout", { method: "POST" }).catch(() => undefined);
        if (queryClient) {
          await queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
        }
        setError("root", { message: messages.giris.invalidCredentials });
        return;
      }

      // Invalidate session cache (if provider available)
      if (queryClient) {
        await queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
      }

      // Redirect (sanitize next path to prevent open redirect).
      // "/" is the public landing page, so a logged-in user goes to the app instead.
      // An admin has no student pages, so their default is the admin queue.
      const safeNext = sanitizeNext(nextPath);
      if (safeNext !== "/") {
        router.push(safeNext);
        return;
      }
      let fallback = isAdmin ? ADMIN_AFTER_LOGIN : DEFAULT_AFTER_LOGIN;
      if (!isAdmin) {
        // Role-based landing page; a failed /me read must not block the login.
        try {
          fallback = homePathFor(await fetchMe());
        } catch {
          fallback = DEFAULT_AFTER_LOGIN;
        }
      }
      router.push(fallback);
    } catch (error) {
      // Duck-typing: check for error object with status property
      if (error && typeof error === "object") {
        const errObj = error as Record<string, unknown>;

        if (errObj.status === 401 && errObj.code === "INVALID_CREDENTIALS") {
          // General message, no field-specific error
          // A browser often autofills another saved password for a demo
          // e-mail; tell the visitor the shared demo password instead.
          const isDemoEmail = DEMO_ACCOUNTS.some((account) => account.email === data.email.trim().toLowerCase());
          const hint =
            isDemoEmail && !adminOnly && demoAccountsEnabled()
              ? ` ${messages.giris.demo.wrongPasswordHint.replace("{password}", DEMO_PASSWORD)}`
              : "";
          setError("root", {
            message: messages.giris.invalidCredentials + hint,
          });
        } else if (errObj.status === 423 && errObj.code === "ACCOUNT_LOCKED") {
          setError("root", {
            message: messages.giris.accountLocked,
          });
        } else if (errObj.status === 422 && errObj.fields) {
          // Field-specific validation errors
          const fields = errObj.fields as Record<string, string>;
          Object.entries(fields).forEach(([field, message]) => {
            setError(field as keyof LoginFormData, {
              message,
            });
          });
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

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div>
        <Label htmlFor="email" className={labelClass}>{messages.giris.emailLabel}</Label>
        <Input
          {...register("email")}
          id="email"
          type="email"
          placeholder={messages.giris.placeholder}
          autoComplete="username"
          className={fieldClass}
        />
        {errors.email && (
          <div className={fieldErrorClass}>{errors.email.message}</div>
        )}
      </div>

      <div>
        <Label htmlFor="password" className={labelClass}>{messages.giris.passwordLabel}</Label>
        <Input
          {...register("password")}
          id="password"
          type="password"
          placeholder={messages.giris.passwordLabel}
          autoComplete="current-password"
          className={fieldClass}
        />
        {errors.password && (
          <div className={fieldErrorClass}>{errors.password.message}</div>
        )}
      </div>

      {errors.root && (
        <div
          aria-live="polite"
          className="rounded-md border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
        >
          {errors.root.message}
        </div>
      )}

      <Button
        type="submit"
        disabled={isSubmitting}
        size="lg"
        className="h-11 w-full bg-success text-background transition-colors hover:bg-success/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-success disabled:opacity-70 motion-reduce:transition-none"
      >
        {isSubmitting ? "..." : messages.giris.login}
      </Button>

      {footer}

      {showDemoAccounts && !adminOnly && (
        <DemoAccounts
          onPick={(email) => {
            setValue("email", email, { shouldValidate: true });
            setValue("password", DEMO_PASSWORD, { shouldValidate: true });
          }}
        />
      )}
      {showDemoAccounts && adminOnly && (
        <DemoAdmin
          onPick={() => {
            setValue("email", DEMO_ADMIN_EMAIL, { shouldValidate: true });
            setFocus("password");
          }}
        />
      )}
    </form>
  );
}

function DemoAdmin({ onPick }: { onPick: () => void }) {
  const demo = messages.giris.demo;
  return (
    <section aria-labelledby="demo-admin-title" className="rounded-md border border-border bg-card px-4 py-4">
      <h2 id="demo-admin-title" className="text-sm font-semibold text-foreground">
        {demo.adminTitle}
      </h2>
      <button
        type="button"
        onClick={onPick}
        aria-label={demo.adminFillLabel}
        className="mt-2 flex w-full flex-col items-start gap-0.5 rounded px-1 py-2 text-left transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success motion-reduce:transition-none"
      >
        <span className="text-[13px] font-medium text-foreground">{demo.adminRole}</span>
        <span className="break-all font-mono text-[12px] text-muted-foreground">{DEMO_ADMIN_EMAIL}</span>
      </button>
      <p className="mt-2 text-[13px] text-muted-foreground">{demo.adminPasswordHint}</p>
    </section>
  );
}

function DemoAccounts({ onPick }: { onPick: (email: string) => void }) {
  const demo = messages.giris.demo;
  return (
    <section id={DEMO_ACCOUNTS_ANCHOR} aria-labelledby="demo-accounts-title" className="scroll-mt-6 rounded-md border border-border bg-card px-4 py-4">
      <h2 id="demo-accounts-title" className="text-sm font-semibold text-foreground">
        {demo.title}
      </h2>
      <p className="mt-1 text-[13px] text-muted-foreground">{demo.hint}</p>
      <p className="mt-2 text-[13px] text-muted-foreground">
        {demo.passwordLabel} <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-foreground">{DEMO_PASSWORD}</code>
      </p>
      <ul className="mt-3 divide-y divide-border">
        {DEMO_ACCOUNTS.map(({ role, email }) => (
          <li key={email}>
            <button
              type="button"
              onClick={() => onPick(email)}
              aria-label={demo.fillLabel.replace("{role}", demo.roles[role])}
              className="flex w-full flex-col items-start gap-0.5 rounded px-1 py-2 text-left transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success motion-reduce:transition-none"
            >
              <span className="text-[13px] font-medium text-foreground">{demo.roles[role]}</span>
              <span className="break-all font-mono text-[12px] text-muted-foreground">{email}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[12px] text-muted-foreground">{demo.adminHint}</p>
    </section>
  );
}
