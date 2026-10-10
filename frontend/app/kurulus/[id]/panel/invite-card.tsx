"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PanelIcon, SideCard, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { inviteOrgMember, type OrgMemberRole } from "@/lib/api/organizations";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { FIELD_CLASS, LABEL_CLASS, UNIT_MAX_LENGTH } from "./ui";

const t = messages.kurulusPanel;

/** Admin-only: invite an already registered colleague, optionally with a unit. */
export function InviteCard({ organizationId }: { organizationId: string }) {
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<OrgMemberRole>("MEMBER");
  const [inviteUnit, setInviteUnit] = useState("");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);

  const inviteMutation = useMutation({
    mutationFn: () => {
      const unit = inviteUnit.trim();
      return inviteOrgMember(organizationId, inviteEmail.trim(), inviteRole, unit ? unit : undefined);
    },
    onSuccess: () => {
      setInviteError(null);
      setInviteMessage(t.inviteSuccessMessage);
      setInviteEmail("");
      setInviteUnit("");
      queryClient.invalidateQueries({ queryKey: ["organization-members", organizationId] });
    },
    onError: () => {
      setInviteMessage(null);
      setInviteError(t.inviteErrorMessage);
    },
  });

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInviteMessage(null);
    if (inviteUnit.trim().length > UNIT_MAX_LENGTH) {
      setInviteError(t.inviteUnitTooLong);
      return;
    }
    setInviteError(null);
    inviteMutation.mutate();
  };

  return (
    <SideCard title={t.inviteMemberTitle} hint={t.inviteHint}>
      <form onSubmit={handleInviteSubmit} className="space-y-3">
        <div>
          <label htmlFor="org-invite-email" className={LABEL_CLASS}>
            {t.inviteEmailLabel}
          </label>
          <input
            id="org-invite-email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            required
            className={FIELD_CLASS}
          />
        </div>
        <div>
          <label htmlFor="org-invite-role" className={LABEL_CLASS}>
            {t.inviteRoleLabel}
          </label>
          <select
            id="org-invite-role"
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as OrgMemberRole)}
            className={FIELD_CLASS}
          >
            <option value="MEMBER">{t.memberRole.MEMBER}</option>
            <option value="ADMIN">{t.memberRole.ADMIN}</option>
          </select>
        </div>
        <div>
          <label htmlFor="org-invite-unit" className={LABEL_CLASS}>
            {t.inviteUnitLabel}
          </label>
          <input
            id="org-invite-unit"
            type="text"
            value={inviteUnit}
            onChange={(e) => setInviteUnit(e.target.value)}
            placeholder={t.team.unitPlaceholder}
            className={FIELD_CLASS}
          />
        </div>
        <button type="submit" disabled={inviteMutation.isPending} className={cn(actionClass.neutral, "w-full")}>
          <PanelIcon name="userPlus" className="h-4 w-4" />
          {inviteMutation.isPending ? t.invitingButton : t.inviteButton}
        </button>

        <div aria-live="polite">
          {inviteError ? (
            <Alert variant="error" className="text-sm">
              {inviteError}
            </Alert>
          ) : null}
          {inviteMessage ? (
            <Alert variant="success" className="text-sm">
              {inviteMessage}
            </Alert>
          ) : null}
        </div>
      </form>
    </SideCard>
  );
}
