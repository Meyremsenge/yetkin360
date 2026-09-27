"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { verifyEmail } from "@/lib/api/client";
import messages from "@/messages/tr.json";
import Link from "next/link";

type Status = "idle" | "verifying" | "success" | "error";

interface ErrorState {
  message: string;
}

function EmailVerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams?.get("token");

  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<ErrorState | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError({
        message: messages.epostaDogrula.tokenInvalid,
      });
      return;
    }

    const verify = async () => {
      try {
        setStatus("verifying");
        await verifyEmail(token);
        setStatus("success");
        setError(null);
      } catch (err) {
        setStatus("error");

        // Duck-typing: check for error object with status property
        if (err && typeof err === "object") {
          const errObj = err as Record<string, unknown>;

          if (errObj.status === 410 || errObj.code === "TOKEN_EXPIRED") {
            setError({
              message: "Bağlantı süresi dolmuş.",
            });
          } else if (errObj.status === 400 || errObj.code === "INVALID_TOKEN") {
            setError({
              message: "Bağlantı geçersiz.",
            });
          } else if ("status" in errObj) {
            // Has status but doesn't match above — generic error
            setError({
              message: messages.epostaDogrula.tokenInvalid,
            });
          } else {
            // No status property — network error
            setError({
              message: messages.errors.network,
            });
          }
        } else {
          // Generic unknown error
          setError({
            message: messages.epostaDogrula.tokenInvalid,
          });
        }
      }
    };

    verify();
  }, [token]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full p-6">
        <h1 className="text-2xl font-bold mb-6 text-slate-900">
          E-Posta Doğrulama
        </h1>

        <div
          role={status === "success" ? undefined : "alert"}
          aria-live={status === "success" ? undefined : "assertive"}
          className="mb-6"
        >
          {status === "verifying" && (
            <div className="rounded-md bg-blue-50 border border-blue-200 p-4">
              <p className="text-sm text-blue-700">
                {messages.epostaDogrula.verifying}
              </p>
            </div>
          )}

          {status === "success" && (
            <div role="status" className="rounded-md bg-green-50 border border-green-200 p-4">
              <p className="text-sm text-green-700 font-medium mb-4">
                {messages.epostaDogrula.success}
              </p>
              <Link
                href="/giris"
                className="text-sm text-green-700 underline hover:text-green-800"
              >
                Giriş sayfasına dön
              </Link>
            </div>
          )}

          {status === "error" && error && (
            <div className="rounded-md bg-red-50 border border-red-200 p-4">
              <p className="text-sm text-red-700 font-medium mb-4">
                {error.message}
              </p>
              <Link
                href="/kayit"
                className="text-sm text-red-700 underline hover:text-red-800"
              >
                tekrar iste
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function EmailVerifyPage() {
  return (
    <Suspense fallback={null}>
      <EmailVerifyContent />
    </Suspense>
  );
}
