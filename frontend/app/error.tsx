"use client";

import { useEffect, useRef } from "react";
import { ApiError } from "@/lib/api/errors";
import { ErrorBanner } from "@/components/error-banner";
import messages from "@/messages/tr.json";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // AC-11: Move focus to heading on mount
  useEffect(() => {
    if (headingRef.current) {
      headingRef.current.focus();
    }
  }, []);

  const requestId =
    error instanceof ApiError ? error.requestId : undefined;

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md">
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="text-2xl font-bold mb-4 text-slate-900 focus:outline-none"
        >
          Bir Hata Oluştu
        </h1>

        <ErrorBanner
          message={messages.errors.generic}
          requestId={requestId}
          onRetry={reset}
        />
      </div>
    </div>
  );
}
