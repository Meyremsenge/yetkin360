import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import GlobalError from "@/app/global-error";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const globalErrorPath = join(__dirname, "global-error.tsx");

/**
 * AC-6: global-error.tsx — root layout çökerse.
 * AC-S4: error.message YOKTUR, messages/tr.json import'u YOKTUR.
 * Kendi html/body'si.
 */

describe("GlobalError (global-error.tsx)", () => {
  describe("AC-6: Root layout çökerse", () => {
    it("AC-6: renderToStaticMarkup sonuç string'dir", () => {
      const mockReset = vi.fn();
      const error = new Error("Root layout crashed");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(typeof result).toBe("string");
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe("AC-6: html/body yapısı", () => {
    it("AC-6: <html lang='tr'> içerir", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(result).toContain('<html lang="tr"');
    });

    it("AC-6: <body> elemanı içerir", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(result).toContain("<body");
    });
  });

  describe("AC-S4: error.message DOM'a yazılmaz", () => {
    it("AC-S4: error.message YOKTUR", () => {
      const mockReset = vi.fn();
      const error = new Error("SELECT * FROM users; secret-token-xyz");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(result).not.toContain("SELECT * FROM users");
      expect(result).not.toContain("secret-token-xyz");
    });

    it("AC-S4: error.stack YOKTUR", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");
      error.stack = "Error: Test\n    at someFunction (file.tsx:100)";

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(result).not.toContain("at someFunction");
      expect(result).not.toContain("file.tsx");
    });

    it("AC-S4: hassas veriler sızdırılmaz", () => {
      const mockReset = vi.fn();
      const error = new Error(
        "Failed to fetch from private API: https://secret-api.internal/data?token=xyz"
      );

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(result).not.toContain("secret-api");
      expect(result).not.toContain("token=xyz");
    });
  });

  describe("AC-6 / AC-S4: messages/tr.json import'u YOKTUR", () => {
    it("AC-S4: kaynak kodu messages/tr.json import'ını içermez", () => {
      const source = readFileSync(globalErrorPath, "utf-8");

      expect(source).not.toContain("messages/tr.json");
      expect(source).not.toContain("messages/tr");
    });
  });

  describe("AC-6: Türkçe metin asgari düzey", () => {
    it("AC-6: 'Yeniden dene' veya benzeri Türkçe buton metni vardır", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      // Asgari Türkçe metin (hardcoded, messages'a bağımlı değil)
      expect(result).toMatch(/Yeniden dene|Tekrar dene|Dene/i);
    });

    it("AC-6: HTML asgari yapıda (kendi html/body)", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      // Kendi html/body tanımı var
      expect(result).toMatch(/<html/i);
      expect(result).toMatch(/<body/i);
      expect(result).toMatch(/<\/body>/i);
      expect(result).toMatch(/<\/html>/i);
    });
  });

  describe("AC-6: reset callback", () => {
    it("AC-6: yeniden dene butonu render edilir", () => {
      const mockReset = vi.fn();
      const error = new Error("Test");

      const result = renderToStaticMarkup(
        <GlobalError error={error} reset={mockReset} />
      );

      expect(result).toContain("button");
    });
  });

  describe("Davranış Sözleşmesi satır 3: Root layout çökerse", () => {
    it("Davranış 3: renderToStaticMarkup çalışır, error yoktur", () => {
      const mockReset = vi.fn();
      const error = new Error("Root layout render error");

      expect(() => {
        renderToStaticMarkup(
          <GlobalError error={error} reset={mockReset} />
        );
      }).not.toThrow();
    });
  });
});
