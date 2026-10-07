import { describe, it, expect, vi, beforeEach } from "vitest";
import { submitEvaluation } from "./evaluation";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";
import type { EvaluationFormData } from "@/lib/evaluation/schemas";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

/**
 * YET-203/ENT-02: evaluation.ts artık gerçek POST /engagements/{id}/evaluation'a
 * bağlı (docs/API.md §2.8) — mock/localStorage kaldırıldı.
 */

const validForm: EvaluationFormData = {
  items: [
    { criterion: "Python kullanımı", rating: "EXCEEDS", comment: "Çok iyi" },
    { criterion: "Zamanında teslim", rating: "NOT_OBSERVED" },
  ],
  private_note: "Sadece kurum içi not",
};

describe("lib/api/evaluation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("submitEvaluation", () => {
    it("happy path - doğru payload ile POST eder, items + submitted_at döner", async () => {
      const response = {
        id: "eval-1",
        engagement_id: "eng-5",
        direction: "ORG_TO_TALENT",
        items: [
          { id: "item-1", criterion: "Python kullanımı", skill_id: null, rating: "EXCEEDS", comment: "Çok iyi" },
          { id: "item-2", criterion: "Zamanında teslim", skill_id: null, rating: "NOT_OBSERVED", comment: null },
        ],
        submitted_at: "2026-10-05T00:00:00Z",
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const record = await submitEvaluation("eng-5", "ORG_TO_TALENT", validForm);

      expect(record).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-5/evaluation", {
        method: "POST",
        body: { direction: "ORG_TO_TALENT", items: validForm.items, private_note: validForm.private_note },
      });
    });

    it("private_note dönen kayıtta YOKTUR (D9) — backend zaten döndürmüyor, tip de içermiyor", async () => {
      const response = {
        id: "eval-1", engagement_id: "eng-5", direction: "ORG_TO_TALENT",
        items: [], submitted_at: "2026-10-05T00:00:00Z",
      };
      mockApiFetch.mockResolvedValueOnce(response);

      const record = await submitEvaluation("eng-5", "ORG_TO_TALENT", validForm);

      expect(record).not.toHaveProperty("private_note");
    });

    it("409 CONFLICT - zaten gönderilmiş veya durum uygun değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 409, code: "CONFLICT", message: "Bu yönde zaten değerlendirme gönderilmiş.", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(submitEvaluation("eng-5", "ORG_TO_TALENT", validForm)).rejects.toMatchObject({ status: 409, code: "CONFLICT" });
    });

    it("403 FORBIDDEN - yön/rol uyuşmazlığında ApiError fırlatır", async () => {
      const error = new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(submitEvaluation("eng-5", "ORG_TO_TALENT", validForm)).rejects.toMatchObject({ status: 403 });
    });

    it("404 NOT_FOUND - kapsam dışı engagement için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(submitEvaluation("does-not-exist", "ORG_TO_TALENT", validForm)).rejects.toMatchObject({ status: 404 });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(submitEvaluation("eng-5", "ORG_TO_TALENT", validForm)).rejects.toBeInstanceOf(NetworkError);
    });
  });
});
