import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  availableTransitions,
  isReasonRequired,
  listEngagements,
  getEngagement,
  transitionEngagement,
  createEngagement,
} from "./engagements";
import type { EngagementDetail, EngagementStatus, EngagementSummary } from "./engagements";
import * as client from "./client";
import { ApiError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

/**
 * PLAN 2.11/2.12: Engagement API katmanı testleri.
 *
 * API çağrıları apiFetch() ile mock'lanıyor. Gerçek backend entegrasyonu başında mock'lar kaldırılacak.
 */

describe("lib/api/engagements", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

    it("EVALUATED/VERIFIED/DISPUTED/RESOLVED için genel /transitions ucundan aday yok (YET-194/IS-04)", () => {
      // EVALUATED: sistem tarafından otomatik tetiklenir (değerlendirme gönderimi).
      // VERIFIED: ayrı bir uçtan yapılır (POST .../attestations), /transitions değil.
      // DISPUTED/RESOLVED: docs/STATE_MACHINE.md §7 — backend'de hiç gerçeklenmemiş.
      // Üçü de bu yüzden burada [] döner; UI'da yanlış bir geçiş düğmesi oluşmasın.
      expect(availableTransitions("EVALUATED")).toEqual([]);
      expect(availableTransitions("VERIFIED")).toEqual([]);
      expect(availableTransitions("DISPUTED")).toEqual([]);
      expect(availableTransitions("RESOLVED")).toEqual([]);
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

  /**
   * AC-1: listEngagements → apiFetch("/engagements") çağrısı yapılır
   * Dönen değer AYNEN response'u yansıtır.
   */
  describe("listEngagements (apiFetch mock)", () => {
    it("AC-1: apiFetch('/engagements') çağrılır ve {items: [...]} döner", async () => {
      const mockResponse: { items: EngagementSummary[] } = {
        items: [
          {
            id: "eng-1",
            title: "Frontend Staj",
            kind: "INTERNSHIP",
            status: "ACTIVE",
            organization_name: "Acme A.Ş.",
            version: 1,
            updated_at: "2026-09-27T10:00:00Z",
          },
        ],
      };

      mockApiFetch.mockResolvedValueOnce(mockResponse);

      const result = await listEngagements();

      expect(result).toEqual(mockResponse);
      expect(result.items[0]).toHaveProperty("id");
      expect(result.items[0]).toHaveProperty("status");
      expect(result.items[0]).not.toHaveProperty("tasks");
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements");
    });

    it("AC-1: Çok sayıda engagement'ı döner", async () => {
      const mockResponse: { items: EngagementSummary[] } = {
        items: [
          {
            id: "eng-1",
            title: "Engagement 1",
            kind: "INTERNSHIP",
            status: "ACTIVE",
            organization_name: "Org 1",
            version: 1,
            updated_at: "2026-09-27T10:00:00Z",
          },
          {
            id: "eng-2",
            title: "Engagement 2",
            kind: "CAPSTONE",
            status: "PENDING_APPROVAL",
            organization_name: "Org 2",
            version: 1,
            updated_at: "2026-09-27T11:00:00Z",
          },
        ],
      };

      mockApiFetch.mockResolvedValueOnce(mockResponse);

      const result = await listEngagements();

      expect(result.items).toHaveLength(2);
      expect(result.items[0].id).toBe("eng-1");
      expect(result.items[1].id).toBe("eng-2");
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements");
    });

    it("AC-7: Boş liste → {items: []} döner (hata değil)", async () => {
      const emptyResponse: { items: EngagementSummary[] } = {
        items: [],
      };

      mockApiFetch.mockResolvedValueOnce(emptyResponse);

      const result = await listEngagements();

      expect(result).toEqual({ items: [] });
      expect(result.items).toHaveLength(0);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements");
    });
  });

  /**
   * AC-4: getEngagement(id) → apiFetch("/engagements/{id}") çağrısı yapılır
   * tasks ve deliverables dahil tam detay döner.
   * AC-5/AC-6: 404 hatasında ApiError fırlatılır (403 değil).
   */
  describe("getEngagement (apiFetch mock)", () => {
    it("AC-4: apiFetch('/engagements/{id}') çağrılır, tasks/deliverables dahil döner", async () => {
      const mockDetail: EngagementDetail = {
        id: "eng-1",
        title: "Frontend Staj",
        kind: "INTERNSHIP",
        status: "ACTIVE",
        organization_name: "Acme A.Ş.",
        talent_id: "talent-1",
        organization_id: "org-1",
        institution_id: "inst-1",
        reason: null,
        version: 1,
        created_at: "2026-09-01T09:00:00Z",
        updated_at: "2026-09-27T10:00:00Z",
        tasks: [{ id: "task-1", title: "Tasarım görev", status: "DONE" }],
        deliverables: [
          { id: "del-1", title: "Tasarım dosyası", submitted_at: "2026-09-20T15:00:00Z" },
        ],
      };

      mockApiFetch.mockResolvedValueOnce(mockDetail);

      const result = await getEngagement("eng-1");

      expect(result).toEqual(mockDetail);
      expect(result.id).toBe("eng-1");
      expect(result.status).toBe("ACTIVE");
      expect(result.tasks).toHaveLength(1);
      expect(result.deliverables).toHaveLength(1);
      expect(result.talent_id).toBe("talent-1");
      expect(result.organization_id).toBe("org-1");
      expect(result.institution_id).toBe("inst-1");
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1");
    });

    it("AC-4: Detay response'u tüm alanları içerir", async () => {
      const mockDetail: EngagementDetail = {
        id: "eng-2",
        title: "Backend Projesi",
        kind: "CAPSTONE",
        status: "PENDING_EVALUATION",
        organization_name: "Veri Bilimi Ltd.",
        talent_id: "talent-2",
        organization_id: "org-2",
        institution_id: null,
        reason: "Başarıyla tamamlandı",
        version: 3,
        created_at: "2026-08-15T08:00:00Z",
        updated_at: "2026-09-25T14:00:00Z",
        tasks: [
          { id: "task-1", title: "Backend API", status: "DONE" },
          { id: "task-2", title: "Test yazma", status: "IN_PROGRESS" },
        ],
        deliverables: [
          { id: "del-1", title: "API dokümanı", submitted_at: "2026-09-18T10:00:00Z" },
          { id: "del-2", title: "Test raporu", submitted_at: "2026-09-24T16:00:00Z" },
        ],
      };

      mockApiFetch.mockResolvedValueOnce(mockDetail);

      const result = await getEngagement("eng-2");

      expect(result.talent_id).toBe("talent-2");
      expect(result.organization_id).toBe("org-2");
      expect(result.institution_id).toBeNull();
      expect(result.reason).toBe("Başarıyla tamamlandı");
      expect(result.created_at).toBe("2026-08-15T08:00:00Z");
      expect(result.tasks).toHaveLength(2);
      expect(result.deliverables).toHaveLength(2);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-2");
    });

    it("AC-5: Var olmayan ID → 404 ApiError fırlatılır", async () => {
      const notFoundError = new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: "Engagement bulunamadı.",
        requestId: null,
      });

      mockApiFetch.mockRejectedValueOnce(notFoundError);

      await expect(getEngagement("nonexistent-id")).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
      });
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/nonexistent-id");
    });

    it("AC-6: Kapsam dışı ID (başka tenant) → 404 ApiError fırlatılır (403 değil)", async () => {
      const forbiddenError = new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: "Engagement bulunamadı.",
        requestId: null,
      });

      mockApiFetch.mockRejectedValueOnce(forbiddenError);

      await expect(getEngagement("eng-other-tenant")).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
      });

      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-other-tenant");
    });

    it("Davranış Sözleşmesi: 404 kodu tam olarak 404 olmalı, 403 değil", async () => {
      const error = new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: "Engagement bulunamadı.",
        requestId: null,
      });
      mockApiFetch.mockRejectedValueOnce(error);

      try {
        await getEngagement("eng-404");
        expect.fail("Should have thrown");
      } catch (err) {
        if (err instanceof ApiError) {
          expect(err.status).toBe(404); // Tam eşleşme, 403 değil
          expect(err.code).toBe("NOT_FOUND");
        }
      }

      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-404");
    });
  });

  /**
   * AC-8: transitionEngagement → apiFetch("/engagements/{id}/transitions", {method: "POST", ...}) çağrısı yapılır
   * Dönen EngagementDetail tam olarak response'u yansıtır.
   */
  describe("transitionEngagement (apiFetch mock)", () => {
    it("AC-8: apiFetch('/engagements/{id}/transitions') POST çağrısı yapılır, updated detail döner", async () => {
      const updatedDetail: EngagementDetail = {
        id: "eng-1",
        title: "Frontend Staj",
        kind: "INTERNSHIP",
        status: "PENDING_APPROVAL",
        organization_name: "Acme A.Ş.",
        talent_id: "talent-1",
        organization_id: "org-1",
        institution_id: "inst-1",
        reason: null,
        version: 2,
        created_at: "2026-09-01T09:00:00Z",
        updated_at: "2026-09-27T11:00:00Z",
        tasks: [{ id: "task-1", title: "Tasarım görev", status: "DONE" }],
        deliverables: [
          { id: "del-1", title: "Tasarım dosyası", submitted_at: "2026-09-20T15:00:00Z" },
        ],
      };

      mockApiFetch.mockResolvedValueOnce(updatedDetail);

      const result = await transitionEngagement("eng-1", {
        to_status: "PENDING_APPROVAL",
        version: 1,
      });

      expect(result).toEqual(updatedDetail);
      expect(result.status).toBe("PENDING_APPROVAL");
      expect(result.version).toBe(2);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/transitions", {
        method: "POST",
        body: {
          to_status: "PENDING_APPROVAL",
          version: 1,
        },
      });
    });

    it("AC-8: reason alanı ile geçiş (CANCELLED) başarılı olur", async () => {
      const cancelledDetail: EngagementDetail = {
        id: "eng-2",
        title: "Backend Projesi",
        kind: "CAPSTONE",
        status: "CANCELLED",
        organization_name: "Veri Bilimi Ltd.",
        talent_id: "talent-2",
        organization_id: "org-2",
        institution_id: null,
        reason: "Kurum tarafından iptal edildi.",
        version: 3,
        created_at: "2026-08-15T08:00:00Z",
        updated_at: "2026-09-27T12:00:00Z",
        tasks: [],
        deliverables: [],
      };

      mockApiFetch.mockResolvedValueOnce(cancelledDetail);

      const result = await transitionEngagement("eng-2", {
        to_status: "CANCELLED",
        version: 2,
        reason: "Kurum tarafından iptal edildi.",
      });

      expect(result.status).toBe("CANCELLED");
      expect(result.reason).toBe("Kurum tarafından iptal edildi.");
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-2/transitions", {
        method: "POST",
        body: {
          to_status: "CANCELLED",
          version: 2,
          reason: "Kurum tarafından iptal edildi.",
        },
      });
    });

    it("AC-8: Version conflict (409) ApiError fırlatılır", async () => {
      const conflictError = new ApiError({
        status: 409,
        code: "CONFLICT",
        message: "Engagement güncellenmiş, version uyuşmazlığı.",
        requestId: null,
      });

      mockApiFetch.mockRejectedValueOnce(conflictError);

      await expect(
        transitionEngagement("eng-1", {
          to_status: "PENDING_APPROVAL",
          version: 1,
        })
      ).rejects.toMatchObject({ status: 409, code: "CONFLICT" });

      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/transitions", {
        method: "POST",
        body: {
          to_status: "PENDING_APPROVAL",
          version: 1,
        },
      });
    });

    it("AC-8: İllegal geçiş (422) ApiError fırlatılır", async () => {
      const illegalError = new ApiError({
        status: 422,
        code: "ILLEGAL_TRANSITION",
        message: "Bu geçiş tanımlı değildir.",
        requestId: null,
      });

      mockApiFetch.mockRejectedValueOnce(illegalError);

      await expect(
        transitionEngagement("eng-1", {
          to_status: "ACTIVE" as EngagementStatus,
          version: 1,
        })
      ).rejects.toMatchObject({ status: 422, code: "ILLEGAL_TRANSITION" });
    });
  });

  /**
   * YET-202/ENT-01: createEngagement — talent kendi engagement'ını oluşturur.
   */
  describe("createEngagement", () => {
    it("happy path - POST /engagements çağırır, oluşturulan kaydı döner", async () => {
      const response = {
        id: "eng-new-1", talent_id: "talent-1", organization_id: "org-1", institution_id: "inst-1",
        kind: "INTERNSHIP", title: "Yeni Staj", status: "DRAFT", version: 1, reason: null,
        created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z",
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createEngagement({
        talent_id: "talent-1", organization_id: "org-1", kind: "INTERNSHIP", title: "Yeni Staj", institution_id: "inst-1",
      });

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements", {
        method: "POST",
        body: { talent_id: "talent-1", organization_id: "org-1", kind: "INTERNSHIP", title: "Yeni Staj", institution_id: "inst-1" },
      });
    });

    it("institution_id opsiyonel - olmadan çağrılabilir", async () => {
      mockApiFetch.mockResolvedValueOnce({
        id: "eng-new-2", talent_id: "talent-1", organization_id: "org-1", institution_id: null,
        kind: "SHORT_PROJECT", title: "x", status: "DRAFT", version: 1, reason: null,
        created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z",
      });

      await createEngagement({ talent_id: "talent-1", organization_id: "org-1", kind: "SHORT_PROJECT", title: "x" });

      expect(mockApiFetch).toHaveBeenCalledWith("/engagements", {
        method: "POST",
        body: { talent_id: "talent-1", organization_id: "org-1", kind: "SHORT_PROJECT", title: "x", institution_id: undefined },
      });
    });

    it("404 ORGANIZATION_NOT_FOUND - geçersiz link için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "ORGANIZATION_NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(
        createEngagement({ talent_id: "talent-1", organization_id: "org-missing", kind: "INTERNSHIP", title: "x" })
      ).rejects.toMatchObject({ status: 404, code: "ORGANIZATION_NOT_FOUND" });
    });

    it("400 INSTITUTION_MISMATCH - talent'ın kendi institution_id'siyle uyuşmazsa ApiError fırlatır", async () => {
      const error = new ApiError({ status: 400, code: "INSTITUTION_MISMATCH", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(
        createEngagement({ talent_id: "talent-1", organization_id: "org-1", kind: "INTERNSHIP", title: "x", institution_id: "wrong-inst" })
      ).rejects.toMatchObject({ status: 400, code: "INSTITUTION_MISMATCH" });
    });

    it("422 - geçersiz kind/boş title için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(
        createEngagement({ talent_id: "talent-1", organization_id: "org-1", kind: "INTERNSHIP", title: "" })
      ).rejects.toMatchObject({ status: 422 });
    });
  });
});
