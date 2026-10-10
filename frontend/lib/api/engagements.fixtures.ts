import type { EngagementViewer } from "./engagements";

/**
 * Test helper: a viewer block that allows nothing; override what the scenario needs.
 * Mirrors the server default for a viewer with no actions (e.g. an observer).
 */
export function makeViewer(overrides: Partial<EngagementViewer> = {}): EngagementViewer {
  return {
    relation: "OBSERVER",
    allowed_transitions: [],
    reason_required: [],
    can_add_task: false,
    can_add_deliverable: false,
    can_evaluate: false,
    can_attest: false,
    attest_blocker: null,
    ...overrides,
  };
}
