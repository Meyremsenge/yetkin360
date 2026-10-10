"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { EmptyState, Initials, SideCard, StatusPill, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { updateMemberUnit, type OrgMember } from "@/lib/api/organizations";
import { ApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { fill } from "./panel-data";
import { FIELD_CLASS, UNIT_MAX_LENGTH } from "./ui";

const t = messages.kurulusPanel;
const tt = t.team;

/** Members grouped by unit (alphabetical, no unit last). */
export function groupByUnit(members: OrgMember[]): { unit: string | null; members: OrgMember[] }[] {
  const groups = new Map<string | null, OrgMember[]>();
  for (const member of members) {
    const list = groups.get(member.unit) ?? [];
    list.push(member);
    groups.set(member.unit, list);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (a === null ? 1 : b === null ? -1 : a.localeCompare(b, "tr")))
    .map(([unit, list]) => ({
      unit,
      members: [...list].sort((x, y) => x.display_name.localeCompare(y.display_name, "tr")),
    }));
}

export function TeamCard({
  organizationId,
  members,
  isLoading,
  isError,
  onRetry,
  canManage,
  currentUserId,
}: {
  organizationId: string;
  members: OrgMember[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  canManage: boolean;
  currentUserId: string | undefined;
}) {
  return (
    <SideCard title={tt.title} hint={tt.hint}>
      {isLoading ? (
        <div className="h-16 animate-pulse rounded-md bg-muted" aria-hidden="true" />
      ) : isError ? (
        <Alert variant="error" className="flex items-center justify-between gap-3 text-sm">
          <span>{tt.loadError}</span>
          <button type="button" onClick={onRetry} className={actionClass.neutral}>
            {messages.errors.retry}
          </button>
        </Alert>
      ) : members.length === 0 ? (
        <EmptyState icon="users" title={tt.emptyTitle} hint={tt.emptyHint} />
      ) : (
        <div className="space-y-4">
          {groupByUnit(members).map((group) => (
            <section key={group.unit ?? "__none"} aria-label={group.unit ?? tt.noUnit}>
              <h4 className="mb-1.5 text-xs font-medium text-muted-foreground">{group.unit ?? tt.noUnit}</h4>
              <ul className="divide-y divide-border rounded-lg border border-border">
                {group.members.map((member) => (
                  <MemberRow
                    key={member.user_id}
                    organizationId={organizationId}
                    member={member}
                    canManage={canManage}
                    isSelf={member.user_id === currentUserId}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </SideCard>
  );
}

function MemberRow({
  organizationId,
  member,
  canManage,
  isSelf,
}: {
  organizationId: string;
  member: OrgMember;
  canManage: boolean;
  isSelf: boolean;
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(member.unit ?? "");
  const [error, setError] = useState<string | null>(null);
  const inputId = `team-unit-${member.user_id}`;

  const mutation = useMutation({
    mutationFn: () => updateMemberUnit(organizationId, member.user_id, draft.trim() ? draft.trim() : null),
    onSuccess: () => {
      setError(null);
      setEditing(false);
      queryClient.invalidateQueries({ queryKey: ["organization-members", organizationId] });
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiError && err.code === "INVALID_UNIT" ? tt.unitTooLong : tt.unitError);
    },
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (draft.trim().length > UNIT_MAX_LENGTH) {
      setError(tt.unitTooLong);
      return;
    }
    mutation.mutate();
  };

  const name = member.display_name || messages.errors.generic;

  return (
    <li className="px-3 py-2.5 text-sm">
      <div className="flex items-center gap-3">
        <Initials name={name} className="h-8 w-8 shrink-0 text-xs" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-foreground">
            {member.display_name}
            {isSelf ? <span className="ml-1 text-xs font-normal text-muted-foreground">({tt.you})</span> : null}
          </p>
          <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
            <span>{t.memberRole[member.role]}</span>
            {member.email ? <span className="truncate font-mono">{member.email}</span> : null}
          </p>
        </div>
        {member.open_assigned_count > 0 ? (
          <StatusPill tone="warning">{fill(tt.openCount, { count: member.open_assigned_count })}</StatusPill>
        ) : null}
        {canManage && !editing ? (
          <button
            type="button"
            onClick={() => {
              setDraft(member.unit ?? "");
              setError(null);
              setEditing(true);
            }}
            aria-label={fill(tt.editUnitFor, { name: member.display_name })}
            className={cn(actionClass.neutral, "h-8 px-2.5 text-xs")}
          >
            {tt.editUnit}
          </button>
        ) : null}
      </div>

      {canManage && editing ? (
        <form onSubmit={submit} className="mt-2 flex flex-wrap items-end gap-2">
          <div className="min-w-0 flex-1">
            <label htmlFor={inputId} className="sr-only">
              {tt.unitLabel}
            </label>
            <input
              id={inputId}
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={tt.unitPlaceholder}
              className={FIELD_CLASS}
              autoFocus
            />
          </div>
          <button type="submit" disabled={mutation.isPending} className={cn(actionClass.primary, "h-10")}>
            {mutation.isPending ? tt.saving : tt.save}
          </button>
          <button type="button" onClick={() => setEditing(false)} className={cn(actionClass.neutral, "h-10")}>
            {tt.cancel}
          </button>
        </form>
      ) : null}
      <div aria-live="polite">
        {error ? (
          <Alert variant="error" className="mt-2 text-sm">
            {error}
          </Alert>
        ) : null}
      </div>
    </li>
  );
}
