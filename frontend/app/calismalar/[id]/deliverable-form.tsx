"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createDeliverable } from "@/lib/api/deliverables";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SkillPicker } from "@/components/skill-picker";
import messages from "@/messages/tr.json";

/**
 * YET-202/ENT-01: Engagement ACTIVE durumundayken yeni bir teslim (deliverable) ekler.
 * Sadece TALENT ekleyebilir; form yalnız sunucunun `viewer.can_add_deliverable` dediği
 * kullanıcıya görünür (SPRINT A). Yetki kararı yine sunucudadır.
 */
export function DeliverableForm({
  engagement,
  onSuccess,
}: {
  engagement: EngagementDetail;
  onSuccess: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [skillId, setSkillId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      createDeliverable(engagement.id, {
        title: title.trim(),
        description: description.trim() || undefined,
        skill_id: skillId ?? undefined,
      }),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      setSkillId(null);
      setFormError(null);
      setSuccessMessage(messages.calismalar.deliverableAddedMessage);
      onSuccess();
      setTimeout(() => setSuccessMessage(null), 2000);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setFormError(messages.calismalar.transitionForbiddenError);
          return;
        }
        if (error.code === "PRECONDITION_FAILED") {
          setFormError(messages.calismalar.deliverableNotActiveError);
          onSuccess(); // durum artık ACTIVE olmayabilir — güncel veriyi getir
          return;
        }
        if (error.code === "INVALID_REQUEST") {
          setFormError(messages.calismalar.deliverableInvalidSkillError);
          return;
        }
      }
      setFormError(messages.errors.generic);
    },
  });

  // transition-actions.tsx'teki desenle aynı: izin artık yoksa AMA henüz okunmamış
  // bir mesaj varsa erken dönme — aksi halde başarı mesajı bir render sonra
  // (status ACTIVE'den çıkınca) okunamadan kaybolur.
  if (!engagement.viewer.can_add_deliverable && !formError && !successMessage) {
    return null;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMessage(null);
    mutation.mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4 rounded-lg border border-dashed border-border bg-background p-4">
      <h3 className="text-sm font-bold mb-3">{messages.calismalar.addDeliverableTitle}</h3>

      <div className="mb-3">
        <Label htmlFor="deliverable-title">{messages.calismalar.deliverableTitleLabel}</Label>
        <Input
          id="deliverable-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>

      <div className="mb-3">
        <Label htmlFor="deliverable-description">{messages.calismalar.deliverableDescriptionLabel}</Label>
        <textarea
          id="deliverable-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
        />
      </div>

      <div className="mb-3">
        <SkillPicker value={skillId} onChange={setSkillId} label={messages.calismalar.deliverableSkillLabel} />
      </div>

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? messages.calismalar.addingDeliverableButton : messages.calismalar.addDeliverableButton}
      </Button>

      {formError && (
        <div role="alert" aria-live="polite" className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-600">
          {formError}
        </div>
      )}

      {successMessage && (
        <div role="status" aria-live="polite" className="mt-3 rounded-md bg-green-50 border border-green-200 p-3 text-sm text-green-600">
          {successMessage}
        </div>
      )}
    </form>
  );
}
