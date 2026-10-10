import type { EngagementStatus, EngagementSummary } from "@/lib/api/engagements";

/**
 * How an organization member or institution coordinator sees a student's
 * engagement in the list: something they must act on, something they already
 * approved, or not yet theirs to see (drafts, rejected, waiting on the other side).
 *
 * UX only — the server re-checks every action.
 */

/** approve: institution starts/rejects · evaluate: organization evaluates · verify: institution verifies. */
export type ReviewAction = "approve" | "evaluate" | "verify";

export interface ReviewerScope {
  organizationIds: ReadonlySet<string>;
  institutionIds: ReadonlySet<string>;
}

// Statuses an engagement can only reach after the start was approved.
const APPROVED_STATUSES: ReadonlySet<EngagementStatus> = new Set<EngagementStatus>([
  "ACTIVE",
  "PENDING_EVALUATION",
  "EVALUATED",
  "VERIFIED",
  "RESOLVED",
  "DISPUTED",
  "CANCELLED",
]);

export type ApprovedGroup = "ongoing" | "verified" | "closed";

const APPROVED_GROUP: Partial<Record<EngagementStatus, ApprovedGroup>> = {
  ACTIVE: "ongoing",
  PENDING_EVALUATION: "ongoing",
  EVALUATED: "ongoing",
  VERIFIED: "verified",
  RESOLVED: "verified",
  DISPUTED: "closed",
  CANCELLED: "closed",
};

/** True when the engagement belongs to one of the viewer's organizations or institutions. */
export function isInReviewerScope(item: EngagementSummary, scope: ReviewerScope): boolean {
  return (
    scope.organizationIds.has(item.organization_id) ||
    (item.institution_id !== null && scope.institutionIds.has(item.institution_id))
  );
}

/** The step waiting on the viewer's side, if any. */
export function reviewAction(item: EngagementSummary, scope: ReviewerScope): ReviewAction | null {
  const asInstitution = item.institution_id !== null && scope.institutionIds.has(item.institution_id);
  const asOrganization = scope.organizationIds.has(item.organization_id);

  if (asInstitution && item.status === "PENDING_APPROVAL") return "approve";
  if (asInstitution && item.status === "EVALUATED") return "verify";
  if (asOrganization && item.status === "PENDING_EVALUATION") return "evaluate";
  return null;
}

export function approvedGroup(item: EngagementSummary): ApprovedGroup | null {
  return APPROVED_GROUP[item.status] ?? null;
}

export interface ReviewSplit {
  /** Waiting on the viewer, oldest first: the longest wait is on top. */
  awaiting: { item: EngagementSummary; action: ReviewAction }[];
  /** Approved and not waiting on the viewer, most recently updated first. */
  approved: EngagementSummary[];
}

export function splitForReview(items: EngagementSummary[], scope: ReviewerScope): ReviewSplit {
  const awaiting: ReviewSplit["awaiting"] = [];
  const approved: EngagementSummary[] = [];

  for (const item of items) {
    if (!isInReviewerScope(item, scope)) continue;
    const action = reviewAction(item, scope);
    if (action) {
      awaiting.push({ item, action });
    } else if (APPROVED_STATUSES.has(item.status)) {
      approved.push(item);
    }
  }

  awaiting.sort((a, b) => a.item.updated_at.localeCompare(b.item.updated_at));
  approved.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  return { awaiting, approved };
}

/** Where the action is taken: the evaluation form, otherwise the engagement itself. */
export function reviewHref(item: EngagementSummary, action: ReviewAction): string {
  return action === "evaluate" ? `/calismalar/${item.id}/degerlendirme` : `/calismalar/${item.id}`;
}
