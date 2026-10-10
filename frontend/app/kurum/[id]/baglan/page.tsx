"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { FormLayout, PanelIcon, StepsCard, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
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

  const t = messages.kurumBaglan;
  const backLink = (
    <Link href="/profil" className="font-medium underline underline-offset-4">
      {t.successBackLink}
    </Link>
  );

  return (
    <AppShell>
      <PageHeader eyebrow={t.eyebrow} title={t.title} description={t.pageDescription} />
      <PageBody>
        <FormLayout
          form={
            submitted ? (
              <div
                role="status"
                aria-live="polite"
                className="flex items-start gap-3 rounded-lg border border-success/30 bg-success/10 p-4 text-sm text-success"
              >
                <PanelIcon name="check" className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="mb-2 font-medium">{t.successMessage}</p>
                  {backLink}
                </div>
              </div>
            ) : (
              <>
                <p className="text-[15px] leading-6 text-foreground">{t.confirmMessage}</p>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-border bg-background p-4">
                    <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <PanelIcon name="landmark" className="h-4 w-4 text-success" />
                      {t.sharesTitle}
                    </p>
                    <ul className="mt-2 space-y-1.5 text-[13px] text-muted-foreground">
                      {t.sharesItems.map((item) => (
                        <li key={item} className="flex gap-2">
                          <span aria-hidden="true" className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-success" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-lg border border-border bg-background p-4">
                    <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <PanelIcon name="lock" className="h-4 w-4 text-muted-foreground" />
                      {t.notSharedTitle}
                    </p>
                    <ul className="mt-2 space-y-1.5 text-[13px] text-muted-foreground">
                      {t.notSharedItems.map((item) => (
                        <li key={item} className="flex gap-2">
                          <span aria-hidden="true" className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <p className="mt-3 text-[13px] text-muted-foreground">{t.privateNote}</p>

                {errorMessage ? (
                  <Alert variant="error" className="mt-5 text-sm">
                    {errorMessage}
                  </Alert>
                ) : null}

                <div className="mt-6 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => mutation.mutate()}
                    disabled={mutation.isPending}
                    className={actionClass.primary}
                  >
                    {mutation.isPending ? t.submittingButton : t.submitButton}
                  </button>
                  <Link
                    href="/profil"
                    className="inline-flex h-10 items-center rounded-md px-4 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
                  >
                    {t.cancelButton}
                  </Link>
                </div>
              </>
            )
          }
          aside={<StepsCard title={t.stepsTitle} steps={t.steps} />}
        />
      </PageBody>
    </AppShell>
  );
}
