/**
 * Completed chain steps per engagement status; `broken` marks the step where
 * the chain stopped (1-based). Shared by the engagement list and detail pages.
 */
export const CHAIN_PROGRESS: Record<string, { done: number; broken?: number }> = {
  DRAFT: { done: 0 },
  PENDING_APPROVAL: { done: 0 },
  ACTIVE: { done: 1 },
  PENDING_EVALUATION: { done: 2 },
  EVALUATED: { done: 2 },
  VERIFIED: { done: 4 },
  RESOLVED: { done: 4 },
  REJECTED: { done: 0, broken: 1 },
  CANCELLED: { done: 1, broken: 2 },
  DISPUTED: { done: 3, broken: 4 },
};

export type StatusTone = "default" | "success" | "error" | "warning";

export const STATUS_TONE: Record<string, StatusTone> = {
  DRAFT: "default",
  PENDING_APPROVAL: "warning",
  ACTIVE: "default",
  PENDING_EVALUATION: "warning",
  EVALUATED: "default",
  VERIFIED: "success",
  RESOLVED: "success",
  REJECTED: "error",
  CANCELLED: "error",
  DISPUTED: "error",
};
