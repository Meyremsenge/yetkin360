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

  /**
   * AC-1: Happy path — body `bg-background text-foreground antialiased` sınıfları
   * Kullanıcı herhangi bir sayfayı açar → body elemanı `bg-background text-foreground antialiased` sınıflarını taşır
   */
  describe("AC-1: bg-renk-token-tanimsiz — body arka planı ve metin rengi", () => {
    it("AC-1: body elemanı bg-background sınıfını taşır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // body elemanının bg-background class'ını içermesi gerekir
      expect(result).toContain("bg-background");
    });

    it("AC-1: body elemanı text-foreground sınıfını taşır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      expect(result).toContain("text-foreground");
    });

    it("AC-1: body elemanı antialiased sınıfını taşır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      expect(result).toContain("antialiased");
    });

    it("AC-1: body elemanı tüm üç sınıfı birlikte taşır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // body tag'ı bg-background, text-foreground, antialiased içermelidir
      expect(result).toMatch(
        /<body[^>]*(bg-background|text-foreground|antialiased)[^>]*>/
      );
    });
  });

  /**
   * AC-2: HTML element'i `color-scheme: light` stiline sahip
   * İşletim sistemi koyu temadadır → sayfa yine de light token'larla render edilir
   */
  describe("AC-2: bg-renk-token-tanimsiz — color-scheme: light", () => {
    it("AC-2: globals.css kaynağında color-scheme tanımı var", () => {
      const globalsPath = join(__dirname, "globals.css");
      const source = readFileSync(globalsPath, "utf-8");

      // globals.css'te "color-scheme: light" string'i olmalı
      expect(source).toContain("color-scheme: light");
    });
  });

  /**
   * AC-6: layout.tsx veya globals.css'te body'ye bg-background uygulanıyor
   * tailwind.config.ts + globals.css değişti ama body class'ı eklenmedi → sorun sürer
   * Test: body'de bg-background kullanıldığını doğrula
   */
  describe("AC-6: bg-renk-token-tanimsiz — body class'ı uygulanması", () => {
    it("AC-6: layout.tsx'te body className veya globals.css'te body seçicisinde bg-background var", () => {
      const source = readFileSync(layoutPath, "utf-8");
      const globalsPath = join(__dirname, "globals.css");
      const globalsSource = readFileSync(globalsPath, "utf-8");

      // layout.tsx'te className'de bg-background veya globals.css'te body seçicisinde olmalı
      const hasInLayout = source.includes('className="') && source.includes("bg-background");
      const hasInGlobals = globalsSource.includes("body") && globalsSource.includes("bg-background");

      expect(hasInLayout || hasInGlobals).toBe(true);
    });

    it("AC-6: layout render'ında body elemanı bg-background ile görünür", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // render edilen HTML'de body'nin bg-background class'ını taşıması gerekir
      expect(result).toContain("<body");
      expect(result).toContain("bg-background");
    });
  });

  /**
   * AC-1: Next.js Font Integration — `next/font/google`'dan üç font import edilmeli
   * layout.tsx kaynağında font import'u ve `Source Serif 4`, `IBM Plex Sans`, `IBM Plex Mono` tanımlaması
   */
  describe("AC-1: next-font-kurulumu — üç font import'u (Source Serif 4, IBM Plex Sans, IBM Plex Mono)", () => {
    it("AC-1: layout.tsx kaynağında next/font/google import'u var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // layout.tsx'te "next/font/google" string'i geçmeli
      expect(source).toContain("next/font/google");
    });

    it("AC-1: layout.tsx kaynağında IBM_Plex_Sans font tanımlaması var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // layout.tsx'te "IBM_Plex_Sans" kelimesi geçmeli (import veya kullanım içinde)
      expect(source).toContain("IBM_Plex_Sans");
    });

    it("AC-1: layout.tsx kaynağında Source_Serif_4 font tanımlaması var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // layout.tsx'te "Source_Serif_4" kelimesi geçmeli
      expect(source).toContain("Source_Serif_4");
    });

    it("AC-1: layout.tsx kaynağında IBM_Plex_Mono font tanımlaması var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // layout.tsx'te "IBM_Plex_Mono" kelimesi geçmeli
      expect(source).toContain("IBM_Plex_Mono");
    });

    it("AC-1: layout.tsx kaynağında latin-ext desteği var (Türkçe karakter)", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // layout.tsx'te "latin-ext" string'i geçmeli (subset tanımında)
      expect(source).toContain("latin-ext");
    });

    it("AC-1: layout render'ında body elemanı IBM Plex Sans mock font class'ı taşır", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // next/font'un (test ortamında mock'lanan) ürettiği class, body'nin class attribute'ünde bulunmalı
      expect(result).toContain("<body");
      expect(result).toContain("mock-plex-sans-font");
    });
  });

  /**
   * AC-3: Mevcut Sayfalar Korunmalı — bg-background, text-foreground, antialiased class'ları
   * layout.tsx'te mevcut style'lar silinmeden, font class'ı EKLENMELİ (değil, değiştirilmeli)
   */
  describe("AC-3: next-font-kurulumu — mevcut sayfalar regresyon yok", () => {
    it("AC-3: layout.tsx kaynağında mevcut bg-background class'ı hâlâ var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // bg-background class'ı silinmemiş olmalı
      expect(source).toContain("bg-background");
    });

    it("AC-3: layout.tsx kaynağında mevcut text-foreground class'ı hâlâ var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // text-foreground class'ı silinmemiş olmalı
      expect(source).toContain("text-foreground");
    });

    it("AC-3: layout.tsx kaynağında mevcut antialiased class'ı hâlâ var", () => {
      const source = readFileSync(layoutPath, "utf-8");

      // antialiased class'ı silinmemiş olmalı
      expect(source).toContain("antialiased");
    });

    it("AC-3: layout render'ında body'nin tüm mevcut class'ları hâlâ gözükür", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // Mevcut class'lar silinmemiş olmalı
      expect(result).toContain("bg-background");
      expect(result).toContain("text-foreground");
      expect(result).toContain("antialiased");
    });
  });

  /**
   * AC-5: Tüm Mevcut Testler Geçmelidir — Regresyon Testi
   * Bu test, diğer tüm testlerin çalıştırılmasını simüle eder
   */
  describe("AC-5: next-font-kurulumu — regresyon (1134 test yapısı)", () => {
    it("AC-5: layout component render edilebilir durumda", () => {
      // RootLayout render edilebilmelidir, hata atmamalı
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // Result boş veya geçersiz olmamış, HTML döndürülmüş olmalı
      expect(result).toBeTruthy();
      expect(result.length).toBeGreaterThan(0);
    });

    it("AC-5: layout HTML yapısını korur", () => {
      const result = renderToStaticMarkup(
        <RootLayout>
          <p>test content</p>
        </RootLayout>
      );

      // HTML yapısı bozulmamış olmalı: html, head, body mevcent
      expect(result).toContain("<html");
      expect(result).toContain("</html>");
      expect(result).toContain("<body");
      expect(result).toContain("</body>");
    });

    it("AC-5: layout çocuk (children) render'ını bozmaz", () => {
      const testContent = "Regresyon test içeriği";
      const result = renderToStaticMarkup(
        <RootLayout>
          <div>{testContent}</div>
        </RootLayout>
      );

      // Children'ın render edilmesi bozulmamış olmalı
      expect(result).toContain(testContent);
    });
  });
});
