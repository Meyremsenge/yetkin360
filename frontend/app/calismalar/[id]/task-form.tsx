"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { createTask } from "@/lib/api/tasks";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SkillPicker } from "@/components/skill-picker";
import messages from "@/messages/tr.json";

const c = messages.calismalar;

/**
 * YET-202/ENT-01: Çalışmaya yeni bir görev ekler.
 * - Kuruluş üyesi / koordinatör: çalışma ACTIVE iken; görev doğrulanmış oluşur.
 * - Öğrenci (`isSubject`): çalışma DRAFT veya ACTIVE iken; görev doğrulanmamış
 *   oluşur ve kuruluş ya da kurum onaylayana kadar öyle kalır.
 * Form yalnız sunucunun `viewer.can_add_task` dediği kullanıcıya görünür (SPRINT A);
 * `isSubject` yalnız "doğrulanmamış görev" ipucunu seçer.
 *
 * Görev yokken form açık gelir (ilk iş görev yazmak); varsa "Görev ekle" ile açılır.
 * Eklemeden sonra form açık kalır ve başlığa odaklanır: birkaç görev art arda girilir.
 */
export function TaskForm({
  engagement,
  onSuccess,
  isSubject = false,
}: {
  engagement: EngagementDetail;
  onSuccess: () => void;
  isSubject?: boolean;
}) {
  const [open, setOpen] = useState(engagement.tasks.length === 0);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [skillId, setSkillId] = useState<string | null>(null);
  // SkillPicker keeps its own search text; a new key gives the next task a clean picker.
  const [skillPickerKey, setSkillPickerKey] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const focusTitle = useRef(false);

  useEffect(() => {
    if (open && focusTitle.current) {
      focusTitle.current = false;
      titleRef.current?.focus();
    }
  });

  useEffect(() => {
    if (!successMessage) return;
    const timer = setTimeout(() => setSuccessMessage(null), isSubject ? 5000 : 3000);
    return () => clearTimeout(timer);
  }, [successMessage, isSubject]);

  const reset = () => {
    setTitle("");
    setDescription("");
    setDueAt("");
    setSkillId(null);
    setSkillPickerKey((key) => key + 1);
    setFormError(null);
  };

  const mutation = useMutation({
    mutationFn: () =>
      createTask(engagement.id, {
        title: title.trim(),
        description: description.trim() || undefined,
        due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
        skill_id: skillId ?? undefined,
      }),
    onSuccess: () => {
      reset();
      setSuccessMessage(isSubject ? c.taskAddedUnverifiedMessage : c.taskAddedMessage);
      focusTitle.current = true;
      onSuccess();
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setFormError(c.transitionForbiddenError);
          return;
        }
        if (error.code === "PRECONDITION_FAILED") {
          setFormError(c.taskNotActiveError);
          onSuccess(); // durum artık ACTIVE olmayabilir — güncel veriyi getir
          return;
        }
        if (error.code === "INVALID_REQUEST") {
          setFormError(c.taskInvalidSkillError);
          return;
        }
      }
      setFormError(messages.errors.generic);
    },
  });

  // deliverable-form.tsx'teki desenle aynı: izin artık yoksa AMA henüz okunmamış
  // bir mesaj varsa erken dönme — aksi halde başarı mesajı bir render sonra
  // (yeniden yüklenen viewer izni kaldırınca) okunamadan kaybolur.
  if (!engagement.viewer.can_add_task && !formError && !successMessage) {
    return null;
  }

  const status = successMessage ? (
    <p
      role="status"
      aria-live="polite"
      className="flex items-start gap-2 rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success"
    >
      <svg viewBox="0 0 24 24" className="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {successMessage}
    </p>
  ) : null;

  if (!open || !engagement.viewer.can_add_task) {
    return (
      <div className="mb-4 space-y-3">
        {status}
        {engagement.viewer.can_add_task ? (
          <button
            type="button"
            onClick={() => {
              focusTitle.current = true;
              setOpen(true);
            }}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-muted-foreground/40 px-4 py-3 text-sm font-medium text-foreground transition-colors hover:border-success hover:bg-success/[0.04] hover:text-success focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
            {c.openTaskForm}
          </button>
        ) : null}
      </div>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMessage(null);
    mutation.mutate();
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-labelledby="task-form-title"
      className="mb-5 rounded-lg border border-border bg-background p-4 sm:p-5"
    >
      <h3 id="task-form-title" className="font-serif text-base font-semibold text-foreground">
        {c.addTaskTitle}
      </h3>
      <p className="mt-1 text-[13px] text-muted-foreground">{c.taskFormIntro}</p>
      {isSubject && (
        <p className="mt-3 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs leading-5 text-warning">
          {c.taskUnverifiedHint}
        </p>
      )}

      <div className="mt-4 space-y-4">
        <div>
          <Label htmlFor="task-title">{c.taskTitleLabel}</Label>
          <Input
            id="task-title"
            ref={titleRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={c.taskTitlePlaceholder}
            required
          />
        </div>

        <div>
          <Label htmlFor="task-description">{c.taskDescriptionLabel}</Label>
          <textarea
            id="task-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={c.taskDescriptionPlaceholder}
            rows={3}
            className="block min-h-[96px] w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/70 transition-colors hover:border-muted-foreground/40 focus:border-success focus:outline-none focus:ring-2 focus:ring-success/25"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-[180px_minmax(0,1fr)]">
          <div>
            <Label htmlFor="task-due-at">{c.taskDueAtLabel}</Label>
            <Input
              id="task-due-at"
              type="date"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              aria-describedby="task-due-at-hint"
            />
            <p id="task-due-at-hint" className="mt-1.5 text-xs text-muted-foreground">
              {c.taskDueAtHint}
            </p>
          </div>
          <div className="min-w-0">
            <SkillPicker key={skillPickerKey} value={skillId} onChange={setSkillId} label={c.taskSkillLabel} />
            <p className="mt-1.5 text-xs text-muted-foreground">{c.taskSkillHint}</p>
          </div>
        </div>
      </div>

      {formError && (
        <p
          role="alert"
          aria-live="polite"
          className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {formError}
        </p>
      )}
      {status ? <div className="mt-4">{status}</div> : null}

      <div className="mt-5 flex flex-wrap items-center justify-end gap-2 border-t border-border pt-4">
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            reset();
            setOpen(false);
          }}
          className="h-10 text-muted-foreground hover:text-foreground"
        >
          {c.taskCancelButton}
        </Button>
        <Button
          type="submit"
          disabled={mutation.isPending}
          className="h-10 px-5 text-background disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2"
        >
          {mutation.isPending ? c.addingTaskButton : c.addTaskButton}
        </Button>
      </div>
    </form>
  );
}
