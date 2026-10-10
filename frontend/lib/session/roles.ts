// Role helpers for routing and navigation. UX only: access to every page is
// still decided on the server (AC-S1), nothing here grants or denies access.

import type { MeResponse } from "./types";

export const ADMIN_HOME = "/admin/dogrulama-kuyrugu";
export const INDIVIDUAL_HOME = "/calismalar";

type MeRoles = Pick<MeResponse, "organizations" | "institutions"> & {
  user?: { is_platform_admin?: boolean; [key: string]: unknown };
};

function firstId(items: unknown[] | undefined): string | null {
  for (const item of items ?? []) {
    if (typeof item === "object" && item !== null) {
      const id = (item as { id?: unknown }).id;
      if (typeof id === "string" && id) return id;
    }
  }
  return null;
}

/** Member of at least one organization or institution. */
export function isOrgSide(me: MeRoles | null | undefined): boolean {
  if (!me) return false;
  return firstId(me.organizations) !== null || firstId(me.institutions) !== null;
}

/** Default landing page after login when no `next` is given. */
export function homePathFor(me: MeRoles | null | undefined): string {
  if (!me) return INDIVIDUAL_HOME;
  if (me.user?.is_platform_admin === true) return ADMIN_HOME;
  const orgId = firstId(me.organizations);
  if (orgId) return `/kurulus/${encodeURIComponent(orgId)}/panel`;
  const instId = firstId(me.institutions);
  if (instId) return `/kurum/${encodeURIComponent(instId)}/panel`;
  return INDIVIDUAL_HOME;
}
