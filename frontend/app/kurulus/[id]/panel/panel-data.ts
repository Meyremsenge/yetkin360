/**
 * SPRINT F: data and pure rules behind the organization panel.
 *
 * UX only — the server re-checks every action. Which row waits on the
 * organization is decided by lib/ui/engagement-review (#60), not copied here.
 */

import { apiFetch } from "@/lib/api/client";
import type { EngagementStatus, EngagementSummary } from "@/lib/api/engagements";
import { reviewAction, type ReviewerScope } from "@/lib/ui/engagement-review";

/**
 * List row as the panel reads it. `institution_name` and `supervisor_user_id`
 * come with SPRINT D1; until then they are missing and the panel degrades
 * (no university name, nothing "assigned to me").
 */
export interface PanelEngagement extends EngagementSummary {
  institution_name?: string | null;
  supervisor_user_id?: string | null;
}

export const PANEL_LIST_LIMIT = 200;

/**
 * Every engagement of this organization the caller may see (server scope).
 * D1's `organization_id` filter only narrows; the client filter below keeps a
 * member of several organizations correct before D1 lands, too.
 * Lives here, not in lib/api/engagements.ts, because that file belongs to A/D1.
 */
export async function listOrganizationEngagements(organizationId: string): Promise<PanelEngagement[]> {
  const query = new URLSearchParams({ organization_id: organizationId, limit: String(PANEL_LIST_LIMIT) });
  const response = await apiFetch<{ items: PanelEngagement[] }>(`/engagements?${query.toString()}`);
  return (response?.items ?? []).filter((item) => item.organization_id === organizationId);
}

export type OrgRole = "ADMIN" | "MEMBER";

/** The caller's role in this organization from /me (SPRINT A); unknown → MEMBER (no admin controls). */
export function orgRoleOf(organizations: readonly unknown[] | undefined, organizationId: string): OrgRole | null {
  for (const entry of organizations ?? []) {
    if (typeof entry !== "object" || entry === null) continue;
    const ref = entry as { id?: unknown; role?: unknown };
    if (ref.id !== organizationId) continue;
    return ref.role === "ADMIN" ? "ADMIN" : "MEMBER";
  }
  return null;
}

export function isAssignedTo(item: PanelEngagement, userId: string | undefined): boolean {
  return Boolean(userId) && item.supervisor_user_id === userId;
}

export type InboxGroup = "action" | "ongoing" | "done";

const ONGOING: ReadonlySet<EngagementStatus> = new Set<EngagementStatus>(["ACTIVE", "PENDING_APPROVAL", "DRAFT"]);
const DONE: ReadonlySet<EngagementStatus> = new Set<EngagementStatus>(["VERIFIED", "RESOLVED"]);

/**
 * The row's action from the organization side:
 * - evaluate: PENDING_EVALUATION (engagement-review's "evaluate")
 * - startEvaluation: ACTIVE → PENDING_EVALUATION
 * - seal: EVALUATED, no university, caller is ADMIN
 * - awaitingUniversitySeal: EVALUATED with a university (info only)
 */
export type RowAction = "evaluate" | "startEvaluation" | "seal" | "awaitingUniversitySeal";

export function rowAction(item: PanelEngagement, organizationId: string, isAdmin: boolean): RowAction | null {
  const scope: ReviewerScope = { organizationIds: new Set([organizationId]), institutionIds: new Set() };
  if (reviewAction(item, scope) === "evaluate") return "evaluate";
  if (item.status === "ACTIVE") return "startEvaluation";
  if (item.status === "EVALUATED") {
    if (item.institution_id !== null) return "awaitingUniversitySeal";
    return isAdmin ? "seal" : null;
  }
  return null;
}

export function inboxGroup(item: PanelEngagement, organizationId: string, isAdmin: boolean): InboxGroup | null {
  const action = rowAction(item, organizationId, isAdmin);
  if (action === "evaluate" || action === "seal") return "action";
  if (ONGOING.has(item.status) || item.status === "EVALUATED") return "ongoing";
  if (DONE.has(item.status)) return "done";
  return null; // REJECTED, CANCELLED, DISPUTED: not shown
}

export interface InboxGroups {
  action: PanelEngagement[];
  ongoing: PanelEngagement[];
  done: PanelEngagement[];
}

/** Longest wait first in "action"; most recent first elsewhere. */
export function groupInbox(items: PanelEngagement[], organizationId: string, isAdmin: boolean): InboxGroups {
  const groups: InboxGroups = { action: [], ongoing: [], done: [] };
  for (const item of items) {
    const group = inboxGroup(item, organizationId, isAdmin);
    if (group) groups[group].push(item);
  }
  groups.action.sort((a, b) => a.updated_at.localeCompare(b.updated_at));
  groups.ongoing.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  groups.done.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  return groups;
}

export interface PanelSummary {
  awaitingAll: number;
  awaitingMine: number;
  ongoing: number;
  sealed: number;
  universities: number;
}

export function summarize(items: PanelEngagement[], userId: string | undefined): PanelSummary {
  const awaiting = items.filter((item) => item.status === "PENDING_EVALUATION");
  return {
    awaitingAll: awaiting.length,
    awaitingMine: awaiting.filter((item) => isAssignedTo(item, userId)).length,
    ongoing: items.filter((item) => item.status === "ACTIVE" || item.status === "PENDING_APPROVAL").length,
    sealed: items.filter((item) => DONE.has(item.status)).length,
    universities: new Set(items.map((item) => item.institution_id).filter((id): id is string => id !== null)).size,
  };
}

export interface PartnerRow {
  /** null: individual applications (no university). */
  institutionId: string | null;
  name: string | null;
  people: number;
  sealed: number;
}

/** Universities by number of people, individual applications last. */
export function aggregatePartners(items: PanelEngagement[]): PartnerRow[] {
  const rows = new Map<string | null, { name: string | null; people: Set<string>; sealed: number }>();
  for (const item of items) {
    if (item.status === "REJECTED" || item.status === "CANCELLED") continue;
    const key = item.institution_id;
    const row = rows.get(key) ?? { name: null, people: new Set<string>(), sealed: 0 };
    row.name = row.name ?? item.institution_name ?? null;
    row.people.add(item.talent_id);
    if (DONE.has(item.status)) row.sealed += 1;
    rows.set(key, row);
  }
  return [...rows.entries()]
    .map(([institutionId, row]) => ({ institutionId, name: row.name, people: row.people.size, sealed: row.sealed }))
    .sort(
      (a, b) =>
        Number(a.institutionId === null) - Number(b.institutionId === null) ||
        b.people - a.people ||
        (a.name ?? "").localeCompare(b.name ?? "", "tr")
    );
}

export function fill(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((text, [key, value]) => text.replace(`{${key}}`, String(value)), template);
}
