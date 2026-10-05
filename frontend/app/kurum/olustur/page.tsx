"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { createInstitution } from "@/lib/api/institutions";
import { Button } from "@/components/ui/button";
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

  return (
    <AppShell>
      <div className="p-6 max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-6">{messages.kurumOlustur.title}</h1>

        <form onSubmit={handleSubmit} className="space-y-4 bg-slate-50 p-6 rounded-md border border-slate-200">
          <div>
            <Label htmlFor="institution-name">{messages.kurumOlustur.nameLabel}</Label>
            <Input id="institution-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          {formError && (
            <div role="alert" aria-live="polite" className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
              {formError}
            </div>
          )}

          <Button type="submit" disabled={mutation.isPending} className="w-full">
            {mutation.isPending ? messages.kurumOlustur.submittingButton : messages.kurumOlustur.submitButton}
          </Button>
        </form>
      </div>
    </AppShell>
  );
}
