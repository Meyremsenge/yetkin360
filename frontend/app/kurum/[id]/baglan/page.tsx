"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { requestInstitutionLink } from "@/lib/api/institutions";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

/**
 * YET-197/IS-10: Kurumun paylaştığı bağlanma linki (institution_id URL'de).
 * Kurum seçimi/arama UI'ı yok (bilinçli — bkz. plan) — talent bu linke kurumdan ulaşır.
 */
export default function KurumBaglanPage() {
  const params = useParams<{ id: string }>();
  const institutionId = params.id;
  const [submitted, setSubmitted] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => requestInstitutionLink(institutionId),
    onSuccess: () => {
      setErrorMessage(null);
      setSubmitted(true);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          setErrorMessage(messages.kurumBaglan.alreadyPendingError);
          return;
        }
        if (error.status === 404) {
          setErrorMessage(messages.kurumBaglan.notFoundError);
          return;
        }
      }
      if (error instanceof NetworkError) {
        setErrorMessage(error.message);
        return;
      }
      setErrorMessage(messages.kurumBaglan.genericError);
    },
  });

  return (
    <AppShell>
      <div className="p-6 max-w-md mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.kurumBaglan.title}</h1>

        {submitted ? (
          <div
            role="status"
            aria-live="polite"
            className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-700"
          >
            <div className="mb-3">{messages.kurumBaglan.successMessage}</div>
            <Link href="/profil" className="underline font-medium">
              {messages.kurumBaglan.successBackLink}
            </Link>
          </div>
        ) : (
          <>
            <p className="text-slate-700 mb-6">{messages.kurumBaglan.confirmMessage}</p>

            {errorMessage && (
              <div
                role="alert"
                aria-live="polite"
                className="mb-4 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600"
              >
                {errorMessage}
              </div>
            )}

            <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
              {mutation.isPending ? messages.kurumBaglan.submittingButton : messages.kurumBaglan.submitButton}
            </Button>
          </>
        )}
      </div>
    </AppShell>
  );
}
