"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { resetPassword } from "@/lib/api/client";
import { resetPasswordSchema, type ResetPasswordFormData } from "@/lib/auth/schemas";
import messages from "@/messages/tr.json";
import Link from "next/link";
import { Button } from "@/components/ui/button";

type Status = "idle" | "loading" | "success" | "error";

interface ErrorState {
  message: string;
}

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams?.get("token");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  // react-hooks/set-state-in-effect: token eksikliği render sırasında zaten
  // bilinen bir durum (searchParams'tan senkron okunur) — effect içinde
  // setState yerine lazy initializer ile başlangıç değeri olarak hesaplanır.
  const [status, setStatus] = useState<Status>(() => (token ? "idle" : "error"));
  const [errorState, setErrorState] = useState<ErrorState | null>(() =>
    token ? null : { message: messages.epostaDogrula.tokenInvalid }
  );

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) {
      setStatus("error");
      setErrorState({
        message: messages.epostaDogrula.tokenInvalid,
      });
      return;
    }

    try {
      setStatus("loading");
      setErrorState(null);
      await resetPassword(token, data.new_password);
      setStatus("success");
    } catch (err) {
      setStatus("error");

      // Duck-typing: check for error object with status property
      if (err && typeof err === "object") {
        const errObj = err as Record<string, unknown>;

        if (errObj.status === 410 || errObj.code === "TOKEN_EXPIRED") {
          setErrorState({
            message: "Bağlantı süresi dolmuş.",
          });
        } else if (errObj.status === 400 || errObj.code === "INVALID_TOKEN") {
          setErrorState({
            message: "Bağlantı geçersiz.",
          });
        } else if (errObj.status === 429) {
          setErrorState({
            message: messages.errors.rateLimited,
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

  if (status === "error" && !token) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="max-w-md w-full p-6">
          <h1 className="text-2xl font-bold mb-6 text-slate-900">
            {messages.sifreSifirla.title}
          </h1>
          <div
            role="alert"
            aria-live="assertive"
            className="rounded-md bg-red-50 border border-red-200 p-4"
          >
            <p className="text-sm text-red-700 font-medium mb-4">
              {errorState?.message}
            </p>
            <Link
              href="/sifre-unuttum"
              className="text-sm text-red-700 underline hover:text-red-800"
            >
              Şifre sıfırlama talebinde bulun
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full p-6">
        <h1 className="text-2xl font-bold mb-6 text-slate-900">
          {messages.sifreSifirla.title}
        </h1>

        {status === "success" && (
          <div
            role="alert"
            aria-live="assertive"
            className="rounded-md bg-green-50 border border-green-200 p-4 mb-6"
          >
            <p className="text-sm text-green-700 font-medium mb-4">
              {messages.sifreSifirla.success}
            </p>
            <Link
              href="/giris"
              className="text-sm text-green-700 underline hover:text-green-800"
            >
              Giriş sayfasına dön
            </Link>
          </div>
        )}

        {errorState && status === "error" && (
          <div
            role="alert"
            aria-live="assertive"
            className="rounded-md bg-red-50 border border-red-200 p-4 mb-6"
          >
            <p className="text-sm text-red-700 font-medium mb-4">
              {errorState.message}
            </p>
            {(errorState.message.includes("süresi dolmuş") ||
              errorState.message.includes("geçersiz")) && (
              <Link
                href="/sifre-unuttum"
                className="text-sm text-red-700 underline hover:text-red-800"
              >
                Şifre sıfırlama talebinde bulun
              </Link>
            )}
          </div>
        )}

        {status !== "success" && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label
                htmlFor="new_password"
                className="block text-sm font-medium text-slate-900 mb-2"
              >
                yeni şifre
              </label>
              <input
                {...register("new_password")}
                type="password"
                role="textbox"
                id="new_password"
                autoComplete="new-password"
                disabled={isSubmitting}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
              />
              {errors.new_password && (
                <p className="text-sm text-red-600 mt-1">
                  {errors.new_password.message}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="password_confirm"
                className="block text-sm font-medium text-slate-900 mb-2"
              >
                yeni şifre tekrar
              </label>
              <input
                {...register("password_confirm")}
                type="password"
                role="textbox"
                id="password_confirm"
                autoComplete="new-password"
                disabled={isSubmitting}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
              />
              {errors.password_confirm && (
                <p className="text-sm text-red-600 mt-1">
                  {errors.password_confirm.message}
                </p>
              )}
            </div>

            <Button type="submit" disabled={isSubmitting}>
              sıfırla
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordContent />
    </Suspense>
  );
}
