"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { createOrganization } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";

/**
 * YET-202/ENT-01: Yeni organizasyon oluşturma. Çağıran otomatik ADMIN olur
 * (backend tarafında — burada rol seçimi yok). Domain opsiyonel: girilmezse
 * panelde alan adı doğrulama bölümü gösterilmez (doğrulanacak bir domain yok).
 */
export default function KurulusOlusturPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [legalId, setLegalId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      createOrganization({
        name: name.trim(),
        domain: domain.trim() || undefined,
        legal_id: legalId.trim() || undefined,
      }),
    onSuccess: (org) => {
      router.push(`/kurulus/${org.id}/panel`);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === "LEGAL_ID_TAKEN") {
        setFormError(messages.kurulusOlustur.legalIdTakenError);
        return;
      }
      if (error instanceof ApiError && error.code === "VALIDATION_ERROR") {
        setFormError(messages.kurulusOlustur.validationError);
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

  return (
    <AppShell>
      <div className="p-6 max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.kurulusOlustur.title}</h1>

        <form onSubmit={handleSubmit} className="space-y-4 bg-slate-50 p-6 rounded-md border border-slate-200">
          <div>
            <Label htmlFor="org-name">{messages.kurulusOlustur.nameLabel}</Label>
            <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div>
            <Label htmlFor="org-domain">{messages.kurulusOlustur.domainLabel}</Label>
            <Input
              id="org-domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder={messages.kurulusOlustur.domainPlaceholder}
            />
            <p className="text-xs text-slate-500 mt-1">{messages.kurulusOlustur.domainHint}</p>
          </div>

          <div>
            <Label htmlFor="org-legal-id">{messages.kurulusOlustur.legalIdLabel}</Label>
            <Input id="org-legal-id" value={legalId} onChange={(e) => setLegalId(e.target.value)} />
          </div>

          {formError && (
            <div role="alert" aria-live="polite" className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
              {formError}
            </div>
          )}

          <Button type="submit" disabled={mutation.isPending} className="w-full">
            {mutation.isPending ? messages.kurulusOlustur.submittingButton : messages.kurulusOlustur.submitButton}
          </Button>
        </form>
      </div>
    </AppShell>
  );
}
