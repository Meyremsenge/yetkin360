"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { forgotPassword } from "@/lib/api/client";
import { forgotPasswordSchema, type ForgotPasswordFormData } from "@/lib/auth/schemas";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { AuthLayout } from "@/components/ui/auth-layout";

type Status = "idle" | "loading" | "success" | "error";

interface ErrorState {
  message: string;
  isRateLimited?: boolean;
}

export default function ForgotPasswordPage() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const [status, setStatus] = useState<Status>("idle");
  const [errorState, setErrorState] = useState<ErrorState | null>(null);

  const onSubmit = async (data: ForgotPasswordFormData) => {
    try {
      setStatus("loading");
      setErrorState(null);
      await forgotPassword(data.email);
      setStatus("success");
    } catch (err) {
      setStatus("error");

      // Duck-typing: check for error object with status property
      if (err && typeof err === "object") {
        const errObj = err as Record<string, unknown>;

        if (errObj.status === 429) {
          setErrorState({
            message: messages.errors.rateLimited,
            isRateLimited: true,
          });
        } else if ("status" in errObj) {
          // Has status but doesn't match above — generic error
          setErrorState({
            message: messages.errors.generic,
          });
        } else {
          // No status property — network error
          setErrorState({
            message: messages.errors.network,
          });
        }
      } else {
        // Generic unknown error
        setErrorState({
          message: messages.errors.network,
        });
      }
    }
  };

  return (
    <AuthLayout
      brandSentence={messages.authLayout.brandSentence}
      links={[{ href: "/giris", label: messages.home.loginLink }]}
    >
        <h1 className="text-2xl font-bold mb-6 text-slate-900">
          {messages.sifreUnuttum.title}
        </h1>

        {status === "success" && (
          <div
            role="alert"
            aria-live="assertive"
            className="rounded-md bg-green-50 border border-green-200 p-4 mb-6"
          >
            <p className="text-sm text-green-700 font-medium">
              {messages.sifreUnuttum.sentMessage}
            </p>
          </div>
        )}

        {errorState && (
          <div
            role="alert"
            aria-live="assertive"
            className="rounded-md bg-red-50 border border-red-200 p-4 mb-6"
          >
            <p className="text-sm text-red-700 font-medium">{errorState.message}</p>
          </div>
        )}

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
        >
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-900 mb-2">
              e-posta
            </label>
            <input
              {...register("email")}
              type="email"
              id="email"
              autoComplete="email"
              placeholder="ornek@example.com"
              disabled={status === "success" || (status === "error" && errorState?.isRateLimited)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
            />
            {errors.email && (
              <p className="text-sm text-red-600 mt-1">{errors.email.message}</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={isSubmitting || status === "success" || (status === "error" && errorState?.isRateLimited)}
            className={status === "loading" || isSubmitting ? "opacity-50 cursor-not-allowed" : ""}
          >
            gönder
          </Button>
        </form>
    </AuthLayout>
  );
}
