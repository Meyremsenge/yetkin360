import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import Home from "@/app/page";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const pagePath = join(__dirname, "page.tsx");

/**
 * AC-9: Ana sayfa — metin koda gömülü olmaz, messages/tr.json'dan.
 * Kaya olmayan literaller test eder; mevcut koda gömülü metinleri bulur.
 */

describe("Home (app/page.tsx)", () => {
  describe("AC-9: Metinler messages/tr.json'dan", () => {
    it("AC-9: 'Beyan → Kanıt → Doğrulanmış Deneyim' başlığı render edilir", () => {
      render(<Home />);

      expect(
        screen.getByText(/beyan.*kanıt.*doğrulanmış deneyim/i)
      ).toBeTruthy();
    });

    it("AC-9: tagline metni render edilir", () => {
      render(<Home />);

      expect(
        screen.getByText(
          /beyan.*kanıt.*doğrulanmış deneyim/i
        )
      ).toBeTruthy();
    });

    it("AC-9: CTA metni render edilir", () => {
      render(<Home />);

      expect(screen.getByText(/Başla/)).toBeTruthy();
    });
  });

  describe("AC-9: Koda gömülü metin YOKTUR", () => {
    it("AC-9: kaynak dosyada 'beyan → kanıt' koda gömülü DEĞİLDİR", () => {
      const source = readFileSync(pagePath, "utf-8");
      expect(source).not.toContain("beyan → kanıt");
    });

    it("AC-9: kaynak dosyada 'Başla' düz metin olarak YOKTUR", () => {
      const source = readFileSync(pagePath, "utf-8");
      expect(source).not.toContain("Başla");
    });

    it("AC-9: kaynak dosyada 'Yetkin360' koda gömülü DEĞİLDİR", () => {
      const source = readFileSync(pagePath, "utf-8");
      expect(source).not.toContain("Yetkin360");
    });
  });

  describe("AC-9: dangerouslySetInnerHTML yasak", () => {
    it("AC-9: page.tsx dangerouslySetInnerHTML kullanmaz", () => {
      const source = readFileSync(pagePath, "utf-8");

      expect(source).not.toContain("dangerouslySetInnerHTML");
    });
  });

  describe("AC-9: Temel yapı", () => {
    it("AC-9: sayfa render edilir", () => {
      const { container } = render(<Home />);

      expect(container).toBeTruthy();
    });

    it("AC-9: başlık var", () => {
      render(<Home />);

      const heading = screen.queryByRole("heading");
      expect(heading).not.toBeNull();
    });
  });

  describe("Davranış Sözleşmesi satır 1: Happy path ana sayfa", () => {
    it("Davranış 1: ana sayfa Türkçe metinle render edilir", () => {
      render(<Home />);

      expect(
        screen.getByText(/beyan/i)
      ).toBeTruthy();
    });
  });
});
