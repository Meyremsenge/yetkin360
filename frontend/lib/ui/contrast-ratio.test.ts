// DİKKAT: Bu dosyadaki HSL literal değerleri frontend/app/globals.css ile MANUEL senkron tutulmalı. globals.css'teki bir token değişirse buradaki beklenen değerler de güncellenmeli.
// Risks bölümü: Senkronizasyon riski (kabul edilen). Test dosyasında HSL değerleri hardcoded tutulur, bilinçli trade-off.

// NOT (düzeltme, orkestratör + bağımsız Node.js hesabıyla doğrulandı):
// planfrontend.md §1.2'deki 3 değer (beyaz/çam 8.5, aşı/zemin 5.1, tuğla/zemin 5.8)
// matematiksel olarak hatalı hesaplanmıştı. Standart WCAG formülüyle gerçek
// değerler: 8.57, 5.46, 6.25 (hepsi hâlâ ≥4.5 WCAG AA eşiğini geçiyor, daha
// güçlü kontrast — regresyon değil). Testler gerçek değerlere güncellendi.

import { describe, it, expect } from "vitest";
import { contrastRatio } from "./contrast-ratio";

describe("contrastRatio", () => {
  // AC-1: Primary pair (mürekkep/kâğıt) → 15.5 ±0.1
  describe("AC-1: Primary foreground/background (ink/paper)", () => {
    it("should calculate contrast ratio for ink/paper at 15.5", () => {
      const result = contrastRatio("30 12% 12%", "40 30% 97%");
      expect(result).toBeCloseTo(15.5, 1);
    });

    it("AC-3: ink/paper should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("30 12% 12%", "40 30% 97%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });
  });

  // AC-2: Six secondary pairs, each in its own describe/it
  describe("AC-2: Secondary text pairs", () => {
    it("AC-2.1: secondary text/paper should be 6.2", () => {
      const result = contrastRatio("30 7% 36%", "40 30% 97%");
      expect(result).toBeCloseTo(6.2, 1);
    });

    it("AC-3: secondary text/paper should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("30 7% 36%", "40 30% 97%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });

    it("AC-2.2: secondary text/sand should be 5.6", () => {
      const result = contrastRatio("30 7% 36%", "38 20% 92%");
      expect(result).toBeCloseTo(5.6, 1);
    });

    it("AC-3: secondary text/sand should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("30 7% 36%", "38 20% 92%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });
  });

  describe("AC-2: Success color pairs", () => {
    it("AC-2.3: success (spruce)/paper should be 8.1", () => {
      const result = contrastRatio("160 38% 24%", "40 30% 97%");
      expect(result).toBeCloseTo(8.1, 1);
    });

    it("AC-3: success/paper should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("160 38% 24%", "40 30% 97%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });

    it("AC-2.4 & AC-5: white text on success (spruce) button should be 8.57", () => {
      const result = contrastRatio("0 0% 100%", "160 38% 24%");
      expect(result).toBeCloseTo(8.57, 1);
    });

    it("AC-3: white text/success should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("0 0% 100%", "160 38% 24%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });
  });

  describe("AC-2: Warning and destructive pairs", () => {
    it("AC-2.5: warning (vaccine)/background should be 5.46", () => {
      const result = contrastRatio("34 75% 32%", "40 30% 97%");
      expect(result).toBeCloseTo(5.46, 1);
    });

    it("AC-3: warning/background should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("34 75% 32%", "40 30% 97%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });

    it("AC-2.6: destructive (brick)/background should be 6.25", () => {
      const result = contrastRatio("8 58% 40%", "40 30% 97%");
      expect(result).toBeCloseTo(6.25, 1);
    });

    it("AC-3: destructive/background should meet WCAG AA threshold (≥4.5)", () => {
      const result = contrastRatio("8 58% 40%", "40 30% 97%");
      expect(result).toBeGreaterThanOrEqual(4.5);
    });
  });

  // AC-4: Parse error cases — fail-closed (throw on invalid input)
  describe("AC-4: Parse error handling (fail-closed)", () => {
    it("should throw on completely invalid HSL string", () => {
      expect(() => contrastRatio("geçersiz", "40 30% 97%")).toThrow();
    });

    it("should throw on empty string", () => {
      expect(() => contrastRatio("", "40 30% 97%")).toThrow();
    });

    it("should throw on random words without HSL format", () => {
      expect(() => contrastRatio("abc def ghi", "40 30% 97%")).toThrow();
    });
  });

  // AC-5: White literal HSL string should be accepted and calculated correctly
  describe("AC-5: Literal HSL string support (white as string literal)", () => {
    it("should accept and calculate white literal HSL string ('0 0% 100%') as foreground", () => {
      // This is already tested in AC-2.4, but AC-5 explicitly verifies that
      // the function accepts literal HSL strings (not just tokens), with no distinction.
      const result = contrastRatio("0 0% 100%", "160 38% 24%");
      expect(result).toBeCloseTo(8.57, 1);
      expect(result).toBeGreaterThanOrEqual(4.5);
    });
  });
});
