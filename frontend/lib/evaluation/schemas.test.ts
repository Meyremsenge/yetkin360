import { describe, it, expect } from "vitest";
import { evaluationFormSchema, evaluationItemSchema } from "./schemas";

describe("lib/evaluation/schemas", () => {
  describe("evaluationItemSchema", () => {
    it("geçerli bir item'ı kabul eder", () => {
      const result = evaluationItemSchema.safeParse({
        criterion: "Python kullanımı",
        rating: "EXCEEDS",
        comment: "Çok iyi",
      });
      expect(result.success).toBe(true);
    });

    it("comment opsiyoneldir", () => {
      const result = evaluationItemSchema.safeParse({
        criterion: "Zamanında teslim",
        rating: "NOT_OBSERVED",
      });
      expect(result.success).toBe(true);
    });

    it("boş criterion'ı reddeder", () => {
      const result = evaluationItemSchema.safeParse({ criterion: "", rating: "MEETS" });
      expect(result.success).toBe(false);
    });

    it("geçersiz rating değerini reddeder", () => {
      const result = evaluationItemSchema.safeParse({ criterion: "X", rating: "GREAT" });
      expect(result.success).toBe(false);
    });

    it("NOT_OBSERVED diğer rating değerleri gibi geçerlidir (D8)", () => {
      const result = evaluationItemSchema.safeParse({ criterion: "X", rating: "NOT_OBSERVED" });
      expect(result.success).toBe(true);
    });
  });

  describe("evaluationFormSchema", () => {
    it("en az bir item olmayan formu reddeder", () => {
      const result = evaluationFormSchema.safeParse({ items: [] });
      expect(result.success).toBe(false);
    });

    it("private_note opsiyoneldir", () => {
      const result = evaluationFormSchema.safeParse({
        items: [{ criterion: "X", rating: "MEETS" }],
      });
      expect(result.success).toBe(true);
    });

    it("geçerli bir form (items + private_note) kabul edilir", () => {
      const result = evaluationFormSchema.safeParse({
        items: [{ criterion: "X", rating: "MEETS" }],
        private_note: "Sadece kurum içi not",
      });
      expect(result.success).toBe(true);
    });
  });
});
