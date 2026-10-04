import { describe, it, expect, vi, beforeEach } from "vitest";
import { createDeliverable } from "./deliverables";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

describe("lib/api/deliverables", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createDeliverable", () => {
    it("happy path - title+description+skill_id gönderir, 201 yanıtını döner", async () => {
      const response = {
        id: "deliv-1",
        engagement_id: "eng-1",
        skill_id: "skill-1",
        title: "Final Rapor",
        description: "Kapsamlı proje raporu",
        submitted_by_user_id: "user-1",
        submitted_at: "2026-10-04T00:00:00Z",
        created_at: "2026-10-04T00:00:00Z",
        updated_at: "2026-10-04T00:00:00Z",
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createDeliverable("eng-1", { title: "Final Rapor", description: "Kapsamlı proje raporu", skill_id: "skill-1" });

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/deliverables", {
        method: "POST",
        body: { title: "Final Rapor", description: "Kapsamlı proje raporu", skill_id: "skill-1" },
      });
    });

    it("opsiyonel alanlar olmadan da çalışır", async () => {
      mockApiFetch.mockResolvedValueOnce({
        id: "deliv-2", engagement_id: "eng-1", skill_id: null, title: "Kod",
        description: null, submitted_by_user_id: "user-1", submitted_at: "2026-10-04T00:00:00Z",
        created_at: "2026-10-04T00:00:00Z", updated_at: "2026-10-04T00:00:00Z",
      });

      const result = await createDeliverable("eng-1", { title: "Kod" });

      expect(result.title).toBe("Kod");
    });

    it("403 FORBIDDEN - TALENT olmayan kullanıcı için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 403, code: "FORBIDDEN", message: "Bu işlemi yapma yetkiniz yok.", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createDeliverable("eng-1", { title: "x" })).rejects.toMatchObject({ status: 403, code: "FORBIDDEN" });
    });

    it("422 PRECONDITION_FAILED - engagement ACTIVE değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "PRECONDITION_FAILED", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createDeliverable("eng-1", { title: "x" })).rejects.toMatchObject({ status: 422, code: "PRECONDITION_FAILED" });
    });

    it("422 INVALID_REQUEST - geçersiz skill_id için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "INVALID_REQUEST", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createDeliverable("eng-1", { title: "x", skill_id: "bad" })).rejects.toMatchObject({ code: "INVALID_REQUEST" });
    });

    it("404 NOT_FOUND - kapsam dışı engagement için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createDeliverable("eng-missing", { title: "x" })).rejects.toMatchObject({ status: 404 });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(createDeliverable("eng-1", { title: "x" })).rejects.toBeInstanceOf(NetworkError);
    });
  });
});
