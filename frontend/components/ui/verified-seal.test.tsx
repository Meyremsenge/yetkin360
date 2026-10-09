import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerifiedSeal } from "./verified-seal";

/**
 * ATDD — VerifiedSeal bileşeni testleri (fe12-landing-sicil-gazetesi)
 * Prop sözleşmesi (varsayım): name?: string; issuedAt?: string; registryNo?: string
 * Mühür rengi: çam yeşili design token (bg-success / text-success).
 */

describe("VerifiedSeal Component", () => {
  describe("AC-6: name prop'u yok — crash yok, sahte isim yok", () => {
    it("AC-6: name verilmeden render edildiğinde hata fırlatmamalı", () => {
      expect(() => render(<VerifiedSeal />)).not.toThrow();
    });

    it("AC-6: name undefined ile render edildiğinde hata fırlatmamalı", () => {
      expect(() => render(<VerifiedSeal name={undefined} />)).not.toThrow();
    });

    it("AC-6: name boş string ile render edildiğinde hata fırlatmamalı", () => {
      expect(() => render(<VerifiedSeal name="" />)).not.toThrow();
    });

    it("AC-6: name verilmediğinde 'Ad Soyad' placeholder metni render EDİLMEMELİ", () => {
      const { container } = render(<VerifiedSeal />);
      expect(screen.queryByText("Ad Soyad")).toBeNull();
      expect(container.textContent).not.toContain("Ad Soyad");
    });

    it("AC-6: name boş string iken 'Ad Soyad' placeholder metni render EDİLMEMELİ", () => {
      const { container } = render(<VerifiedSeal name="" />);
      expect(container.textContent).not.toContain("Ad Soyad");
    });
  });

  describe("Davranış 5: dolu prop'larla render", () => {
    it("AC-6: name prop'unun metni görünmeli", () => {
      render(
        <VerifiedSeal
          name="Ayşe Yılmaz"
          issuedAt="01.10.2026"
          registryNo="SG-2026-000123"
        />
      );
      expect(screen.getByText("Ayşe Yılmaz")).toBeTruthy();
    });

    it("AC-6: tarih (issuedAt) prop'unun metni görünmeli", () => {
      render(
        <VerifiedSeal
          name="Ayşe Yılmaz"
          issuedAt="01.10.2026"
          registryNo="SG-2026-000123"
        />
      );
      expect(screen.getByText("01.10.2026")).toBeTruthy();
    });

    it("AC-6: sicil no (registryNo) prop'unun metni görünmeli", () => {
      render(
        <VerifiedSeal
          name="Ayşe Yılmaz"
          issuedAt="01.10.2026"
          registryNo="SG-2026-000123"
        />
      );
      expect(screen.getByText("SG-2026-000123")).toBeTruthy();
    });
  });

  describe("AC-6 / Davranış 5: çam yeşili mühür rengi (design token)", () => {
    it("AC-6: root element className'de bg-success token'ı BULUNMALI", () => {
      const { container } = render(
        <VerifiedSeal
          name="Ayşe Yılmaz"
          issuedAt="01.10.2026"
          registryNo="SG-2026-000123"
        />
      );
      const tokens = Array.from(container.querySelectorAll("*")).flatMap((el) =>
        Array.from(el.classList)
      );
      expect(tokens.includes("bg-success") || tokens.includes("text-success")).toBe(true);
    });

    it("AC-6: name verilmeden render edildiğinde de bg-success veya text-success token'ı BULUNMALI", () => {
      const { container } = render(<VerifiedSeal />);
      const tokens = Array.from(container.querySelectorAll("*")).flatMap((el) =>
        Array.from(el.classList)
      );
      expect(tokens.includes("bg-success") || tokens.includes("text-success")).toBe(true);
    });
  });
});
