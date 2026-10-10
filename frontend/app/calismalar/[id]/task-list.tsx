"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { verifyTask } from "@/lib/api/tasks";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const c = messages.calismalar;

const TASK_BADGE: Record<string, string> = {
  PLANNED: "bg-muted text-muted-foreground",
  IN_PROGRESS: "bg-warning/10 text-warning",
  DONE: "bg-success/10 text-success",
};

/**
 * Görev listesi. Öğrencinin eklediği görev, kuruluş üyesi ya da kurum
 * koordinatörü onaylayana kadar "Doğrulanmadı" etiketiyle görünür.
 * `canVerify` yalnız "Onayla" düğmesini gösterip göstermemeye karar verir
 * (öğrenciye gösterilmez); yetki kararı sunucudadır.
 */
export function TaskList({
  engagement,
  canVerify,
  onChange,
}: {
  engagement: EngagementDetail;
  canVerify: boolean;
  onChange: () => void;
}) {
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (taskId: string) => verifyTask(engagement.id, taskId),
    onSuccess: () => {
      setError(null);
      onChange();
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.code === "TASK_ALREADY_VERIFIED") {
        // Someone else verified it meanwhile: not an error, just stale data.
        setError(null);
        onChange();
        return;
      }
      if (err instanceof ApiError && err.status === 403) {
        setError(c.taskVerifyForbiddenError);
        return;
      }
      if (err instanceof ApiError && err.code === "PRECONDITION_FAILED") {
        setError(c.taskVerifyNotAllowedError);
        onChange();
        return;
      }
      setError(c.taskVerifyError);
    },
  });

  return (
    <>
      <ul className="divide-y divide-border rounded-lg border border-border">
        {engagement.tasks.map((task) => (
          <li key={task.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
            <span className="text-foreground">{task.title}</span>
            <span className="flex shrink-0 items-center gap-2">
              {!task.verified && (
                <span className="rounded-full bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning">
                  {c.taskUnverifiedBadge}
                </span>
              )}
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  TASK_BADGE[task.status] ?? TASK_BADGE.PLANNED
                )}
              >
                {(c.taskStatus as Record<string, string>)[task.status] ?? task.status}
              </span>
              {!task.verified && canVerify && (
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate(task.id)}
                  aria-label={c.taskVerifyButtonLabel.replace("{title}", task.title)}
                >
                  {mutation.isPending && mutation.variables === task.id ? c.taskVerifyingButton : c.taskVerifyButton}
                </Button>
              )}
            </span>
          </li>
        ))}
      </ul>
      {error && (
        <div
          role="alert"
          className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </div>
      )}
    </>
  );
}
