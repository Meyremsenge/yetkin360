import { describe, it, expect } from "vitest";
import type { EngagementStatus, EngagementSummary } from "@/lib/api/engagements";
import {
  approvedGroup,
  isInReviewerScope,
  reviewAction,
  reviewHref,
  splitForReview,
  type ReviewerScope,
} from "@/lib/ui/engagement-review";

function summary(overrides: Partial<EngagementSummary>): EngagementSummary {
  return {
    id: "eng-1",
    title: "Frontend Stajı",
    kind: "INTERNSHIP",
    status: "ACTIVE",
    organization_id: "org-1",
    institution_id: "inst-1",
    organization_name: "Acme A.Ş.",
    version: 1,
    updated_at: "2026-09-01T00:00:00Z",
    talent_id: "talent-1",
    talent_name: "Ayşe Yılmaz",
    ...overrides,
  };
}

const ORG: ReviewerScope = { organizationIds: new Set(["org-1"]), institutionIds: new Set() };
const INST: ReviewerScope = { organizationIds: new Set(), institutionIds: new Set(["inst-1"]) };
const NONE: ReviewerScope = { organizationIds: new Set(), institutionIds: new Set() };

describe("lib/ui/engagement-review", () => {
  describe("reviewAction", () => {
    it("kurum: onay bekleyen çalışma 'approve', değerlendirilmiş çalışma 'verify'", () => {
      expect(reviewAction(summary({ status: "PENDING_APPROVAL" }), INST)).toBe("approve");
      expect(reviewAction(summary({ status: "EVALUATED" }), INST)).toBe("verify");
    });

    it("kuruluş: değerlendirme bekleyen çalışma 'evaluate'", () => {
      expect(reviewAction(summary({ status: "PENDING_EVALUATION" }), ORG)).toBe("evaluate");
    });

    it("karşı tarafın adımı bu tarafın işlemi sayılmaz", () => {
      expect(reviewAction(summary({ status: "PENDING_APPROVAL" }), ORG)).toBeNull();
      expect(reviewAction(summary({ status: "EVALUATED" }), ORG)).toBeNull();
      expect(reviewAction(summary({ status: "PENDING_EVALUATION" }), INST)).toBeNull();
    });

    it("kurumsuz çalışma kurum kapsamına girmez", () => {
      const item = summary({ status: "PENDING_APPROVAL", institution_id: null });
      expect(reviewAction(item, INST)).toBeNull();
      expect(isInReviewerScope(item, INST)).toBe(false);
    });
  });

  describe("splitForReview", () => {
    it("taslak, reddedilen ve karşı tarafı bekleyen çalışmalar iki listede de yer almaz", () => {
      const hidden: EngagementStatus[] = ["DRAFT", "REJECTED", "PENDING_APPROVAL"];
      const items = hidden.map((status, n) => summary({ id: `eng-${n}`, status }));

      expect(splitForReview(items, ORG)).toEqual({ awaiting: [], approved: [] });
    });

    it("onaydan sonraki her durum 'onaylanan' listesindedir", () => {
      const statuses: EngagementStatus[] = ["ACTIVE", "EVALUATED", "VERIFIED", "RESOLVED", "DISPUTED", "CANCELLED"];
      const items = statuses.map((status, n) => summary({ id: `eng-${n}`, status }));

      const { awaiting, approved } = splitForReview(items, ORG);

      expect(awaiting).toEqual([]);
      expect(approved.map((item) => item.status).sort()).toEqual([...statuses].sort());
    });

    it("işlem bekleyen çalışma onaylananlarda tekrar edilmez", () => {
      const item = summary({ status: "PENDING_EVALUATION" });

      const { awaiting, approved } = splitForReview([item], ORG);

      expect(awaiting).toEqual([{ item, action: "evaluate" }]);
      expect(approved).toEqual([]);
    });

    it("kapsam dışındaki çalışma (kullanıcının kendi çalışması) alınmaz", () => {
      const own = summary({ organization_id: "org-9", institution_id: null });

      expect(splitForReview([own], ORG)).toEqual({ awaiting: [], approved: [] });
      expect(splitForReview([summary({})], NONE)).toEqual({ awaiting: [], approved: [] });
    });

    it("bekleyenler en eskiden, onaylananlar en yeniden sıralanır", () => {
      const items = [
        summary({ id: "new-wait", status: "PENDING_EVALUATION", updated_at: "2026-09-05T00:00:00Z" }),
        summary({ id: "old-wait", status: "PENDING_EVALUATION", updated_at: "2026-09-01T00:00:00Z" }),
        summary({ id: "old-ok", status: "ACTIVE", updated_at: "2026-09-02T00:00:00Z" }),
        summary({ id: "new-ok", status: "VERIFIED", updated_at: "2026-09-06T00:00:00Z" }),
      ];

      const { awaiting, approved } = splitForReview(items, ORG);

      expect(awaiting.map(({ item }) => item.id)).toEqual(["old-wait", "new-wait"]);
      expect(approved.map((item) => item.id)).toEqual(["new-ok", "old-ok"]);
    });
  });

  it("approvedGroup durumları devam eden / doğrulanmış / kapanmış olarak gruplar", () => {
    expect(approvedGroup(summary({ status: "ACTIVE" }))).toBe("ongoing");
    expect(approvedGroup(summary({ status: "VERIFIED" }))).toBe("verified");
    expect(approvedGroup(summary({ status: "CANCELLED" }))).toBe("closed");
    expect(approvedGroup(summary({ status: "DRAFT" }))).toBeNull();
  });

  it("reviewHref değerlendirmede forma, diğerlerinde çalışmaya götürür", () => {
    const item = summary({ id: "eng-7" });
    expect(reviewHref(item, "evaluate")).toBe("/calismalar/eng-7/degerlendirme");
    expect(reviewHref(item, "approve")).toBe("/calismalar/eng-7");
    expect(reviewHref(item, "verify")).toBe("/calismalar/eng-7");
  });
});
