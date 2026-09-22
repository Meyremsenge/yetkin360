import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import RootLayout from "@/app/layout";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const layoutPath = join(__dirname, "layout.tsx");

/**
 * AC-9: Root layout — <html lang="tr">, metin messages/tr.json'dan.
 * dangerouslySetInnerHTML yasak.
 */

describe("RootLayout (app/layout.tsx)", () => {
  describe("AC-9: <html lang='tr'>", () => {
    it("AC-9: renderToStaticMarkup <html lang='tr'> içerir", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      expect(result).toContain('lang="tr"');
    });

    it("AC-9: Türkçe dil ayarı HTML'de yapılı", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test</p>
        </RootLayout>
      );

      expect(result).toMatch(/<html[^>]*lang="tr"[^>]*>/);
    });
  });

  describe("AC-9: children render edilir", () => {
    it("AC-9: children metni renderToStaticMarkup sonucunda gözükür", () => {
      const testContent = "İçerik test metni";
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>{testContent}</p>
        </RootLayout>
      );

      expect(result).toContain(testContent);
    });

    it("AC-9: JSX children render edilir", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <main>
            <h1>Ana sayfa</h1>
          </main>
        </RootLayout>
      );

      expect(result).toContain("Ana sayfa");
    });

    it("AC-9: multiple children render edilir", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>Birinci</p>
          <p>İkinci</p>
          <p>Üçüncü</p>
        </RootLayout>
      );

      expect(result).toContain("Birinci");
      expect(result).toContain("İkinci");
      expect(result).toContain("Üçüncü");
    });
  });

  describe("AC-9: dangerouslySetInnerHTML yasak", () => {
    it("AC-9: layout kaynağında dangerouslySetInnerHTML yok", () => {
      const source = readFileSync(layoutPath, "utf-8");

      expect(source).not.toContain("dangerouslySetInnerHTML");
    });
  });

  describe("AC-9: HTML yapısı", () => {
    it("AC-9: <html> elemanı vardır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test</p>
        </RootLayout>
      );

      expect(result).toContain("<html");
    });

    it("AC-9: <head> elemanı vardır (metadata)", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test</p>
        </RootLayout>
      );

      // head olabilir veya meta tags var
      expect(result).toMatch(/<head|<meta|charset/i);
    });

    it("AC-9: <body> elemanı vardır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test</p>
        </RootLayout>
      );

      expect(result).toContain("<body");
    });
  });

  describe("Davranış Sözleşmesi satır 1: Uygulama açılır", () => {
    it("Davranış 1: layout Türkçe ayarlarla render edilir", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>Uygulama başlıyor</p>
        </RootLayout>
      );

      expect(result).toContain('lang="tr"');
      expect(result).toContain("Uygulama başlıyor");
    });
  });

  describe("AC-1: Providers (TanStack Query, client)", () => {
    it("AC-1: layout sunucu bileşeni kalır ama Providers client tarafında", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // Providers import'u veya kullanımı
      expect(source).toMatch(/Providers|QueryClientProvider/i);
    });
  });
});
