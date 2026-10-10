"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ActionLink, SideCard } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { updateOrganization, type OrganizationResponse } from "@/lib/api/organizations";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";

const t = messages.kurulusPanel.showcase;

/** Public showcase: admins switch it; everyone may open /o/{id}. */
export function ShowcaseCard({ org, canManage }: { org: OrganizationResponse; canManage: boolean }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const isPublic = org.showcase_public === true;

  const mutation = useMutation({
    mutationFn: (next: boolean) => updateOrganization(org.id, { showcase_public: next }),
    onSuccess: (updated) => {
      setError(null);
      queryClient.setQueryData(["organization", org.id], updated);
    },
    onError: () => setError(t.error),
  });

  return (
    <SideCard title={t.title} hint={t.hint}>
      {canManage ? (
        <div className="flex items-center justify-between gap-3 text-sm">
          <span id="showcase-switch-label" className="font-medium text-foreground">
            {t.toggleLabel}
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={isPublic}
            aria-labelledby="showcase-switch-label"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate(!isPublic)}
            className={cn(
              "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success disabled:opacity-60",
              isPublic ? "border-success bg-success" : "border-border bg-muted"
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "inline-block h-4 w-4 rounded-full bg-background shadow transition-transform",
                isPublic ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>
      ) : null}
      <p className="mt-2 text-sm text-muted-foreground" aria-live="polite">
        {isPublic ? t.on : t.off}
      </p>
      <div aria-live="polite">
        {error ? (
          <Alert variant="error" className="mt-2 text-sm">
            {error}
          </Alert>
        ) : null}
      </div>
      <ActionLink href={`/o/${org.id}`} variant="neutral" icon="globe" className="mt-3 w-full">
        {t.view}
      </ActionLink>
    </SideCard>
  );
}
