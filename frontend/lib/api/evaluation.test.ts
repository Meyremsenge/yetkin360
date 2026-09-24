import { describe, it, expect, beforeEach } from "vitest";
import { submitEvaluation, hasSubmittedEvaluation } from "./evaluation";
import type { EvaluationFormData } from "@/lib/evaluation/schemas";

/**
 * PLAN 2.13: Kurum tarafı değerlendirme mock API testleri.
 * mock-eng-5 seed verisinde PENDING_EVALUATION durumundadır (bkz. lib/api/engagements.ts).
 * mock-eng-3 ACTIVE'dir — INVALID_STATUS senaryosu için kullanılır.
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
    localStorage.clear();
  });

  it("PENDING_EVALUATION durumundaki engagement için başarıyla gönderilir", async () => {
    const record = await submitEvaluation("mock-eng-5", "ORG_TO_TALENT", validForm);

    expect(record.engagement_id).toBe("mock-eng-5");
    expect(record.direction).toBe("ORG_TO_TALENT");
    expect(record.id).toBeTruthy();
    expect(record.submitted_at).toBeTruthy();
  });

  it("private_note dönen kayıtta YOKTUR (D9)", async () => {
    const record = await submitEvaluation("mock-eng-5", "ORG_TO_TALENT", validForm);
    expect(record).not.toHaveProperty("private_note");
  });

  it("hasSubmittedEvaluation gönderim öncesi false, sonrası true döner", async () => {
    expect(await hasSubmittedEvaluation("mock-eng-5", "ORG_TO_TALENT")).toBe(false);
    await submitEvaluation("mock-eng-5", "ORG_TO_TALENT", validForm);
    expect(await hasSubmittedEvaluation("mock-eng-5", "ORG_TO_TALENT")).toBe(true);
  });

  it("aynı engagement + direction için ikinci gönderim 409 ALREADY_SUBMITTED verir", async () => {
    await submitEvaluation("mock-eng-5", "ORG_TO_TALENT", validForm);

    await expect(submitEvaluation("mock-eng-5", "ORG_TO_TALENT", validForm)).rejects.toMatchObject({
      status: 409,
      code: "ALREADY_SUBMITTED",
    });
  });

  it("PENDING_EVALUATION olmayan bir engagement için 422 INVALID_STATUS verir", async () => {
    await expect(submitEvaluation("mock-eng-3", "ORG_TO_TALENT", validForm)).rejects.toMatchObject({
      status: 422,
      code: "INVALID_STATUS",
    });
  });

  it("olmayan bir engagement için 404 NOT_FOUND verir (getEngagement üzerinden)", async () => {
    await expect(
      submitEvaluation("does-not-exist", "ORG_TO_TALENT", validForm)
    ).rejects.toMatchObject({ status: 404 });
  });
});
