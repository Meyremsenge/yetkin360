"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { FormLayout, StepsCard, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { createOrganization } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";
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

  const t = messages.kurulusOlustur;

  return (
    <AppShell>
      <PageHeader eyebrow={t.eyebrow} title={t.title} description={t.pageDescription} />
      <PageBody>
        <FormLayout
          form={
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="org-name">{t.nameLabel}</Label>
                <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>

              <div>
                <Label htmlFor="org-domain">{t.domainLabel}</Label>
                <Input
                  id="org-domain"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder={t.domainPlaceholder}
                  className="font-mono"
                  aria-describedby="org-domain-hint"
                />
                <p id="org-domain-hint" className="mt-1.5 text-[13px] text-muted-foreground">
                  {t.domainHint}
                </p>
              </div>

              <div>
                <Label htmlFor="org-legal-id">{t.legalIdLabel}</Label>
                <Input
                  id="org-legal-id"
                  value={legalId}
                  onChange={(e) => setLegalId(e.target.value)}
                  className="font-mono"
                />
              </div>

              {formError ? (
                <Alert variant="error" className="text-sm">
                  {formError}
                </Alert>
              ) : null}

              <div className="pt-2">
                <button type="submit" disabled={mutation.isPending} className={actionClass.primary}>
                  {mutation.isPending ? t.submittingButton : t.submitButton}
                </button>
              </div>
            </form>
          }
          aside={<StepsCard title={t.stepsTitle} steps={t.steps} />}
        />
      </PageBody>
    </AppShell>
  );
}
