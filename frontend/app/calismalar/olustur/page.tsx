"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { useSession } from "@/lib/session/use-session";
import { createEngagement, type EngagementKind } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import messages from "@/messages/tr.json";

const KIND_OPTIONS: EngagementKind[] = ["INTERNSHIP", "CAPSTONE", "SHORT_PROJECT", "PART_TIME"];

const pulse = "animate-pulse rounded-md bg-muted motion-reduce:animate-none";
const labelClass = "mb-1 block text-xs font-medium text-muted-foreground";
const fieldClass =
  "block h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success";

function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <div className="max-w-[640px] px-4 py-8 md:px-6 lg:px-10">
        <Link
          href="/calismalar"
          className="mb-4 inline-flex items-center gap-2 rounded-sm text-sm text-muted-foreground hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        >
          <span aria-hidden="true">←</span>
          {messages.calismalar.detailBackLink}
        </Link>
        <div className="mt-4">{children}</div>
      </div>
    </AppShell>
  );
}

function InfoState({ message }: { message: string }) {
  return (
    <Alert variant="info" className="text-sm">
      {message}
    </Alert>
  );
}

/**
 * YET-202/ENT-01: Engagement oluşturma — link-tabanlı akış (YET-197'deki kurum
 * bağlanma deseniyle aynı felsefe: organizasyon bir arama/seçim ekranı değil,
 * paylaştığı link ile bulunur — backend'de böyle bir arama ucu yok).
 *
 * talent_id ve institution_id kullanıcıdan ASLA elle istenmez — oturumdan
 * otomatik doldurulur. institution_id verilirse backend onu talent'ın kendi
 * institution_id'siyle eşleştirmek ZORUNDA (INSTITUTION_MISMATCH, 400) —
 * elle girilebilir bir alan olsa bu hatayı anlamsız yere tetikler.
 *
 * Suspense sarmalı: useSearchParams() App Router'da CSR-bailout için bir
 * Suspense sınırı gerektirir, yoksa `next build` prerender'da hata verir
 * (bkz. e-posta-dogrula/page.tsx'teki aynı desen).
 */
function CalismaOlusturContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const organizationId = searchParams.get("organization_id");
  const session = useSession();

  const [kind, setKind] = useState<EngagementKind>("INTERNSHIP");
  const [title, setTitle] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const talentId = session.data?.talent_profile?.id;
  const institutionId = session.data?.talent_profile?.institution_id;

  const mutation = useMutation({
    mutationFn: () => {
      if (!organizationId || !talentId) {
        return Promise.reject(new Error("missing_precondition"));
      }
      return createEngagement({
        talent_id: talentId,
        organization_id: organizationId,
        kind,
        title: title.trim(),
        institution_id: institutionId ?? undefined,
      });
    },
    onSuccess: (engagement) => {
      router.push(`/calismalar/${engagement.id}`);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === "ORGANIZATION_NOT_FOUND") {
        setFormError(messages.calismaOlustur.invalidLinkError);
        return;
      }
      setFormError(messages.errors.generic);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    mutation.mutate();
  };

  if (!organizationId) {
    return (
      <PageFrame>
        <InfoState message={messages.calismaOlustur.missingLinkMessage} />
        <Link
          href="/calismalar/kurulus-sec"
          className="mt-4 inline-flex items-center gap-1.5 rounded-sm text-sm font-medium text-success hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
        >
          {messages.calismaOlustur.missingLinkPickerLink}
        </Link>
      </PageFrame>
    );
  }

  if (session.isPending) {
    return (
      <PageFrame>
        <div role="status" aria-busy="true" aria-label={messages.calismaOlustur.loadingLabel} className="space-y-4">
          <div className={`h-8 w-64 ${pulse}`} />
          <div className={`h-4 w-full ${pulse}`} />
          <div className={`h-10 w-full ${pulse}`} />
          <div className={`h-10 w-full ${pulse}`} />
        </div>
      </PageFrame>
    );
  }

  if (!talentId) {
    return (
      <PageFrame>
        <InfoState message={messages.calismaOlustur.notATalentMessage} />
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <h1 className="font-serif text-[32px] font-semibold leading-10">{messages.calismaOlustur.title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{messages.calismaOlustur.description}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        <div>
          <label htmlFor="engagement-kind" className={labelClass}>
            {messages.calismaOlustur.kindLabel}
          </label>
          <select
            id="engagement-kind"
            value={kind}
            onChange={(e) => setKind(e.target.value as EngagementKind)}
            className={fieldClass}
          >
            {KIND_OPTIONS.map((k) => (
              <option key={k} value={k}>
                {messages.calismalar.kind[k]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="engagement-title" className={labelClass}>
            {messages.calismaOlustur.titleLabel}
          </label>
          <input
            id="engagement-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={messages.calismaOlustur.titlePlaceholder}
            required
            className={fieldClass}
          />
        </div>

        {formError && (
          <Alert variant="error" aria-live="polite" className="p-3 text-sm">
            {formError}
          </Alert>
        )}

        <Button
          type="submit"
          disabled={mutation.isPending}
          className="bg-success text-background hover:bg-success/90 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
        >
          {mutation.isPending ? messages.calismaOlustur.submittingButton : messages.calismaOlustur.submitButton}
        </Button>
      </form>
    </PageFrame>
  );
}

export default function CalismaOlusturPage() {
  return (
    <Suspense fallback={null}>
      <CalismaOlusturContent />
    </Suspense>
  );
}
