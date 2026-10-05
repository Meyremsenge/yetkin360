"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { useSession } from "@/lib/session/use-session";
import { createEngagement, type EngagementKind } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";

const KIND_OPTIONS: EngagementKind[] = ["INTERNSHIP", "CAPSTONE", "SHORT_PROJECT", "PART_TIME"];

/**
 * YET-202/ENT-01: Engagement oluşturma — link-tabanlı akış (YET-197'deki kurum
 * bağlanma deseniyle aynı felsefe: organizasyon bir arama/seçim ekranı değil,
 * paylaştığı link ile bulunur — backend'de böyle bir arama ucu yok).
 *
 * talent_id ve institution_id kullanıcıdan ASLA elle istenmez — oturumdan
 * otomatik doldurulur. institution_id verilirse backend onu talent'ın kendi
 * institution_id'siyle eşleştirmek ZORUNDA (INSTITUTION_MISMATCH, 400) —
 * elle girilebilir bir alan olsa bu hatayı anlamsız yere tetikler.
 */
export default function CalismaOlusturPage() {
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
      <AppShell>
        <div className="p-6 max-w-lg mx-auto">
          <div role="alert" className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.calismaOlustur.missingLinkMessage}
          </div>
        </div>
      </AppShell>
    );
  }

  if (!session.isPending && !talentId) {
    return (
      <AppShell>
        <div className="p-6 max-w-lg mx-auto">
          <div role="alert" className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            {messages.calismaOlustur.notATalentMessage}
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="p-6 max-w-lg mx-auto">
        <Link href="/calismalar" className="text-sm text-slate-600 hover:underline">
          ← {messages.calismalar.detailBackLink}
        </Link>

        <h1 className="text-2xl font-bold mt-4 mb-6">{messages.calismaOlustur.title}</h1>

        <form onSubmit={handleSubmit} className="space-y-4 bg-slate-50 p-6 rounded-md border border-slate-200">
          <div>
            <Label htmlFor="engagement-kind">{messages.calismaOlustur.kindLabel}</Label>
            <select
              id="engagement-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value as EngagementKind)}
              className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
            >
              {KIND_OPTIONS.map((k) => (
                <option key={k} value={k}>
                  {messages.calismalar.kind[k]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="engagement-title">{messages.calismaOlustur.titleLabel}</Label>
            <Input id="engagement-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>

          {formError && (
            <div role="alert" aria-live="polite" className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
              {formError}
            </div>
          )}

          <Button type="submit" disabled={mutation.isPending} className="w-full">
            {mutation.isPending ? messages.calismaOlustur.submittingButton : messages.calismaOlustur.submitButton}
          </Button>
        </form>
      </div>
    </AppShell>
  );
}
