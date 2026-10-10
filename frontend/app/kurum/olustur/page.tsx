"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { PageBody, PageHeader } from "@/components/page-layout";
import { FormLayout, StepsCard, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { createInstitution } from "@/lib/api/institutions";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import messages from "@/messages/tr.json";

/**
 * YET-202/ENT-01: Yeni kurum oluşturma. Çağıran otomatik ADMIN olur.
 * Tek alan: ad. Domain alanı YOK — backend GUV-09 ile her zaman yok sayıyor
 * (bkz. lib/api/institutions.ts), göstermek kullanıcıyı yanıltır.
 */
export default function KurumOlusturPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createInstitution(name.trim()),
    onSuccess: (institution) => {
      router.push(`/kurum/${institution.id}/panel`);
    },
    onError: () => {
      setFormError(messages.errors.generic);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    mutation.mutate();
  };

  const t = messages.kurumOlustur;

  return (
    <AppShell>
      <PageHeader eyebrow={t.eyebrow} title={t.title} description={t.pageDescription} />
      <PageBody>
        <FormLayout
          form={
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="institution-name">{t.nameLabel}</Label>
                <Input id="institution-name" value={name} onChange={(e) => setName(e.target.value)} required />
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
