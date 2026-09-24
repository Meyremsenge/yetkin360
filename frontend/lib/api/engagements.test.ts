import { describe, it, expect, beforeEach } from "vitest";
import {
  availableTransitions,
  isReasonRequired,
  listEngagements,
  getEngagement,
  transitionEngagement,
} from "./engagements";
import type { EngagementDetail, EngagementStatus } from "./engagements";

/**
 * PLAN 2.11/2.12: Engagement API katmanı (localStorage mock store) testleri.
 *
 * Store localStorage'da tutulduğu için (bkz. lib/api/engagements.ts dosya başı notu —
 * sekmeler arası paylaşım için bilinçli tercih), her testte `localStorage.clear()` ile
 * sıfırdan seed'e dönülür; aksi halde testler arası state sızar.
 */

describe("lib/api/engagements", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("availableTransitions", () => {
    it("DRAFT için sadece PENDING_APPROVAL adaydır", () => {
      expect(availableTransitions("DRAFT")).toEqual(["PENDING_APPROVAL"]);
    });

    it("PENDING_APPROVAL için ACTIVE ve REJECTED adaydır", () => {
      expect(availableTransitions("PENDING_APPROVAL")).toEqual(["ACTIVE", "REJECTED"]);
    });

    it("ACTIVE için CANCELLED ve PENDING_EVALUATION adaydır", () => {
      expect(availableTransitions("ACTIVE")).toEqual(["CANCELLED", "PENDING_EVALUATION"]);
    });

    it("REJECTED/CANCELLED/PENDING_EVALUATION terminaldir (aday yok)", () => {
      expect(availableTransitions("REJECTED")).toEqual([]);
      expect(availableTransitions("CANCELLED")).toEqual([]);
      expect(availableTransitions("PENDING_EVALUATION")).toEqual([]);
    });
  });

  describe("isReasonRequired", () => {
    it("REJECTED ve CANCELLED için gerekçe zorunludur", () => {
      expect(isReasonRequired("REJECTED")).toBe(true);
      expect(isReasonRequired("CANCELLED")).toBe(true);
    });

    it("ACTIVE/PENDING_APPROVAL/PENDING_EVALUATION için gerekçe zorunlu değildir", () => {
      expect(isReasonRequired("ACTIVE")).toBe(false);
      expect(isReasonRequired("PENDING_APPROVAL")).toBe(false);
      expect(isReasonRequired("PENDING_EVALUATION")).toBe(false);
    });
  });

  describe("listEngagements (mock)", () => {
    it("mock verideki tüm engagement'ları özet olarak döner", async () => {
      const result = await listEngagements();
      expect(result.items.length).toBeGreaterThan(0);
      expect(result.items[0]).toHaveProperty("id");
      expect(result.items[0]).toHaveProperty("status");
      expect(result.items[0]).not.toHaveProperty("tasks");
    });
  });

  describe("getEngagement (mock)", () => {
    it("var olan mock ID için detay (tasks/deliverables dahil) döner", async () => {
      const engagement = await getEngagement("mock-eng-3");
      expect(engagement.id).toBe("mock-eng-3");
      expect(engagement.status).toBe("ACTIVE");
      expect(engagement.tasks.length).toBeGreaterThan(0);
      expect(engagement.deliverables.length).toBeGreaterThan(0);
    });

    it("olmayan ID için 404 NOT_FOUND ApiError fırlatır (yetkisiz erişim gibi görünür)", async () => {
      await expect(getEngagement("does-not-exist")).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
      });
    });
  });

  describe("transitionEngagement (mock durum makinesi)", () => {
    it("geçerli geçiş: DRAFT → PENDING_APPROVAL başarılı, version artar", async () => {
      const before = await getEngagement("mock-eng-1");
      expect(before.status).toBe("DRAFT");

      const updated = await transitionEngagement("mock-eng-1", {
        to_status: "PENDING_APPROVAL",
        version: before.version,
      });

      expect(updated.status).toBe("PENDING_APPROVAL");
      expect(updated.version).toBe(before.version + 1);

      // Kalıcılık: yeniden okununca da güncel durum gelmeli (localStorage'a yazıldı).
      const reread = await getEngagement("mock-eng-1");
      expect(reread.status).toBe("PENDING_APPROVAL");
      expect(reread.version).toBe(before.version + 1);
    });

    it("version uyuşmazlığı → 409 CONFLICT", async () => {
      const before = await getEngagement("mock-eng-1");

      await expect(
        transitionEngagement("mock-eng-1", {
          to_status: "PENDING_APPROVAL",
          version: before.version + 99,
        })
      ).rejects.toMatchObject({ status: 409, code: "CONFLICT" });
    });

    it("iki 'sekme' senaryosu: ilk geçiş başarılı, eski version ile ikinci deneme 409 alır", async () => {
      // Her iki "sekme" de aynı localStorage'ı (aynı origin) paylaşır — burada bunu
      // iki bağımsız getEngagement çağrısıyla simüle ediyoruz.
      const tabA = await getEngagement("mock-eng-3");
      const tabB = await getEngagement("mock-eng-3");
      expect(tabA.version).toBe(tabB.version);

      const afterTabA = await transitionEngagement("mock-eng-3", {
        to_status: "PENDING_EVALUATION",
        version: tabA.version,
      });
      expect(afterTabA.status).toBe("PENDING_EVALUATION");

      // tabB hâlâ eski version'ı taşıyor — bu artık geçersiz.
      await expect(
        transitionEngagement("mock-eng-3", {
          to_status: "CANCELLED",
          version: tabB.version,
          reason: "Sekme B'nin denemesi",
        })
      ).rejects.toMatchObject({ status: 409, code: "CONFLICT" });
    });

    it("tanımsız geçiş (DRAFT → ACTIVE) → 422 ILLEGAL_TRANSITION", async () => {
      const before = await getEngagement("mock-eng-1");

      await expect(
        transitionEngagement("mock-eng-1", {
          to_status: "ACTIVE" as EngagementStatus,
          version: before.version,
        })
      ).rejects.toMatchObject({ status: 422, code: "ILLEGAL_TRANSITION" });
    });

    it("gerekçe zorunlu geçişte reason eksikse → 422 PRECONDITION_FAILED", async () => {
      const before: EngagementDetail = await getEngagement("mock-eng-3");
      expect(before.status).toBe("ACTIVE");

      await expect(
        transitionEngagement("mock-eng-3", {
          to_status: "CANCELLED",
          version: before.version,
        })
      ).rejects.toMatchObject({ status: 422, code: "PRECONDITION_FAILED" });
    });

    it("gerekçe verilirse CANCELLED geçişi başarılı olur ve reason kaydedilir", async () => {
      const before = await getEngagement("mock-eng-3");

      const updated = await transitionEngagement("mock-eng-3", {
        to_status: "CANCELLED",
        version: before.version,
        reason: "Kurum tarafından sonlandırıldı.",
      });

      expect(updated.status).toBe("CANCELLED");
      expect(updated.reason).toBe("Kurum tarafından sonlandırıldı.");
    });
  });
});
