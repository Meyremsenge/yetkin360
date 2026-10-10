"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createTask } from "@/lib/api/tasks";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SkillPicker } from "@/components/skill-picker";
import messages from "@/messages/tr.json";

/**
 * YET-202/ENT-01: Engagement ACTIVE durumundayken yeni bir görev ekler.
 * TALENT çağıramaz — backend 403 döner, burada rol kontrolü yapılmaz
 * (bkz. deliverable-form.tsx'teki aynı felsefe: duruma göre göster, yetki sunucuda).
 */
export function TaskForm({
  engagement,
  onSuccess,
}: {
  engagement: EngagementDetail;
  onSuccess: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [skillId, setSkillId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      createTask(engagement.id, {
        title: title.trim(),
        description: description.trim() || undefined,
        due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
        skill_id: skillId ?? undefined,
      }),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      setDueAt("");
      setSkillId(null);
      setFormError(null);
      setSuccessMessage(messages.calismalar.taskAddedMessage);
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
          setFormError(messages.calismalar.taskNotActiveError);
          onSuccess(); // durum artık ACTIVE olmayabilir — güncel veriyi getir
          return;
        }
        if (error.code === "INVALID_REQUEST") {
          setFormError(messages.calismalar.taskInvalidSkillError);
          return;
        }
      }
      setFormError(messages.errors.generic);
    },
  });

  // deliverable-form.tsx'teki desenle aynı: durum artık uygun değilse AMA henüz
  // okunmamış bir mesaj varsa erken dönme — aksi halde başarı mesajı bir render
  // sonra (status ACTIVE'den çıkınca) okunamadan kaybolur.
  if (engagement.status !== "ACTIVE" && !formError && !successMessage) {
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
      <h3 className="text-sm font-bold mb-3">{messages.calismalar.addTaskTitle}</h3>

      <div className="mb-3">
        <Label htmlFor="task-title">{messages.calismalar.taskTitleLabel}</Label>
        <Input
          id="task-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>

      <div className="mb-3">
        <Label htmlFor="task-description">{messages.calismalar.taskDescriptionLabel}</Label>
        <textarea
          id="task-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="block w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
        />
      </div>

      <div className="mb-3">
        <Label htmlFor="task-due-at">{messages.calismalar.taskDueAtLabel}</Label>
        <Input
          id="task-due-at"
          type="date"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
        />
      </div>

      <div className="mb-3">
        <SkillPicker value={skillId} onChange={setSkillId} label={messages.calismalar.taskSkillLabel} />
      </div>

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? messages.calismalar.addingTaskButton : messages.calismalar.addTaskButton}
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
