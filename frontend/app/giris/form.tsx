"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { login } from "@/lib/api/client";
import { loginSchema, type LoginFormData } from "@/lib/auth/schemas";
import { sanitizeNext } from "@/lib/auth/sanitize-next";
import messages from "@/messages/tr.json";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { SESSION_QUERY_KEY } from "@/lib/session/use-session";

function useQueryClientSafe() {
  try {
    return useQueryClient();
  } catch {
    return null;
  }
}

export default function LoginForm({ nextPath }: { nextPath?: string }) {
  const router = useRouter();
  const queryClient = useQueryClientSafe();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data.email, data.password);

      // Invalidate session cache (if provider available)
      if (queryClient) {
        await queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
      }

      // Redirect (sanitize next path to prevent open redirect)
      const destination = sanitizeNext(nextPath);
      router.push(destination);
    } catch (error) {
      // Duck-typing: check for error object with status property
      if (error && typeof error === "object") {
        const errObj = error as Record<string, unknown>;

        if (errObj.status === 401 && errObj.code === "INVALID_CREDENTIALS") {
          // General message, no field-specific error
          setError("root", {
            message: messages.giris.invalidCredentials,
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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-md bg-slate-50 p-6 border border-slate-200">
      <div>
        <Label htmlFor="email">{messages.giris.emailLabel}</Label>
        <Input
          {...register("email")}
          id="email"
          type="email"
          placeholder={messages.giris.placeholder}
          autoComplete="username"
        />
        {errors.email && (
          <div className="text-xs text-red-600 mt-1">{errors.email.message}</div>
        )}
      </div>

      <div>
        <Label htmlFor="password">{messages.giris.passwordLabel}</Label>
        <Input
          {...register("password")}
          id="password"
          type="password"
          placeholder={messages.giris.passwordLabel}
          autoComplete="current-password"
        />
        {errors.password && (
          <div className="text-xs text-red-600 mt-1">{errors.password.message}</div>
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
        {isSubmitting ? "..." : messages.giris.login}
      </Button>
    </form>
  );
}
