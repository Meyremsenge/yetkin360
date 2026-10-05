import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const globalsPath = join(__dirname, "globals.css");
const tailwindPath = join(__dirname, "..", "tailwind.config.ts");
const buttonPath = join(__dirname, "..", "components", "ui", "button.tsx");

/**
 * AC-3: tailwind.config.ts'de colors.background token tanımı
 * `tailwind.config.ts`'de `colors.background: "hsl(var(--background))"` tanımlanmış olmalı
 */
describe("AC-3: bg-renk-token-tanimsiz — tailwind.config.ts token bağlantısı", () => {
  it("AC-3: tailwind.config.ts kaynağında background token tanımı var", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // Tam token tanımı araması
    expect(source).toContain('background: "hsl(var(--background))');
  });

  it("AC-3: tailwind.config.ts'de theme.extend.colors içinde background var", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // colors nesnesinde background key'i olmalı
    expect(source).toContain("colors");
    expect(source).toContain("background");
  });

  it("AC-3: tailwind.config.ts'de hsl(var(...)) formatında token var", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // hsl(var(...)) format'ı kullanılmış olmalı
    expect(source).toContain("hsl(var");
  });
});

/**
 * AC-4: Mevcut shadcn bileşenleri hardcoded renk bağlamını korur (regresyon testi)
 * button.tsx'te `bg-slate-900` hâlâ var — bu bileşen yeni token'lar tarafından ezilmemeli
 */
describe("AC-4: bg-renk-token-tanimsiz — mevcut komponent renkleri korunur (regresyon)", () => {
  it("AC-4: button.tsx hardcoded bg-slate-900 rengi korunmuş", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button bileşeni hâlâ hardcoded bg-slate-900 kullanmalı
    expect(source).toContain("bg-slate-900");
  });

  it("AC-4: button.tsx text-white rengi korunmuş", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button bileşeni hâlâ text-white kullanmalı
    expect(source).toContain("text-white");
  });

  it("AC-4: button.tsx hover:bg-slate-700 rengi korunmuş", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button bileşeni hâlâ hover:bg-slate-700 kullanmalı
    expect(source).toContain("hover:bg-slate-700");
  });

  it("AC-4: button bileşeni kendi style'ını taşır", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button className'inde style tanımlı olmalı (template literal kullanıyor)
    expect(source).toContain("className");
    expect(source).toContain("bg-slate-900");
  });
});

/**
 * AC-5: Kısmi uygulama durumu — globals.css (:root) + tailwind.config.ts (colors) tutarlılığı
 * Eğer globals.css'te --background tanımlanmışsa, tailwind.config.ts'de de background key'i olmalı
 * (veya tersi: ikisinin de var olması veya ikisinin de olmaması)
 */
describe("AC-5: bg-renk-token-tanimsiz — CSS token ve Tailwind tutarlılığı", () => {
  it("AC-5: globals.css'te :root token tanımı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // globals.css'te :root { --background: ... } veya benzer tanım olmalı
    expect(source).toContain("--background");
  });

  it("AC-5: tailwind.config.ts'de background token bağlantısı var", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // tailwind.config.ts'te background key'i olmalı
    expect(source).toContain("background");
  });

  it("AC-5: globals.css ve tailwind.config.ts tutarlı şekilde token tanımlandı", () => {
    const globalsSource = readFileSync(globalsPath, "utf-8");
    const tailwindSource = readFileSync(tailwindPath, "utf-8");

    // globals.css'te token varsa, tailwind.config.ts'de de bağlantı olmalı
    const hasBackgroundInGlobals = globalsSource.includes("--background");
    const hasBackgroundInTailwind = tailwindSource.includes("background");

    // Her ikisi de tanımlanmış olmalı veya hiçbiri
    expect(hasBackgroundInGlobals && hasBackgroundInTailwind).toBe(true);
  });

  it("AC-5: globals.css'te foreground token tanımı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // globals.css'te --foreground tanımı olmalı
    expect(source).toContain("--foreground");
  });

  it("AC-5: globals.css body seçicisinde @apply kullanıyor", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // body seçicisinde @apply direktifi olmalı
    expect(source).toContain("@apply");
    expect(source).toContain("body");
  });

  it("AC-5: globals.css'te color-scheme tanımı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // color-scheme: light tanımı olmalı
    expect(source).toContain("color-scheme: light");
  });
});
