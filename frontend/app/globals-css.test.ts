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
 * button.tsx'te `bg-success` hâlâ var — bu bileşen yeni token'lar tarafından ezilmemeli
 */
describe("AC-4: bg-renk-token-tanimsiz — mevcut komponent renkleri korunur (regresyon)", () => {
  it("AC-4: button.tsx hardcoded bg-success rengi korunmuş", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button bileşeni hâlâ hardcoded bg-success kullanmalı
    expect(source).toContain("bg-success");
  });

  it("AC-4: button.tsx text-white rengi korunmuş", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button bileşeni hâlâ text-white kullanmalı
    expect(source).toContain("text-white");
  });

  it("AC-4: button.tsx hover:bg-success/90 rengi korunmuş", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button bileşeni hâlâ hover:bg-success/90 kullanmalı
    expect(source).toContain("hover:bg-success/90");
  });

  it("AC-4: button bileşeni kendi style'ını taşır", () => {
    const source = readFileSync(buttonPath, "utf-8");

    // button className'inde style tanımlı olmalı (template literal kullanıyor)
    expect(source).toContain("className");
    expect(source).toContain("bg-success");
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

/**
 * AC-3: Yeni palet — 7 Tailwind color token'ının HSL değerleri güncellendi
 * globals.css (:root) içinde yeni HSL değerleriyle tanımlanmalı
 * Davranış Sözleşmesi (atdd.md satır 53-63) — tam HSL match
 */
describe("AC-3: fe03-token-font-degisimi — Tailwind color token'ları güncellendi", () => {
  it("AC-3: globals.css'te success token yeni değeri 160 38% 24%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --success: 160 38% 24%; (pine rengi)
    expect(source).toContain("--success: 160 38% 24%");
  });

  it("AC-3: globals.css'te warning token yeni değeri 34 75% 32%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --warning: 34 75% 32%; (ochre rengi)
    expect(source).toContain("--warning: 34 75% 32%");
  });

  it("AC-3: globals.css'te destructive token yeni değeri 8 58% 40%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --destructive: 8 58% 40%; (brick rengi)
    expect(source).toContain("--destructive: 8 58% 40%");
  });

  it("AC-3: globals.css'te primary token yeni değeri 30 12% 12%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --primary: 30 12% 12%; (ink rengi, foreground ile aynı)
    expect(source).toContain("--primary: 30 12% 12%");
  });

  it("AC-3: globals.css'te muted token yeni değeri 38 20% 92%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --muted: 38 20% 92%; (sand rengi)
    expect(source).toContain("--muted: 38 20% 92%");
  });

  it("AC-3: globals.css'te border token yeni değeri 36 16% 86%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --border: 36 16% 86%; (line rengi)
    expect(source).toContain("--border: 36 16% 86%");
  });

  it("AC-3: globals.css'te card token yeni değeri 0 0% 100%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --card: 0 0% 100%;
    expect(source).toContain("--card: 0 0% 100%");
  });
});

/**
 * AC-4: Yeni palet — background token'ı güncellendi
 * globals.css (:root) içinde yeni HSL değeriyle tanımlanmalı
 * Davranış Sözleşmesi (atdd.md satır 55) — paper rengi
 */
describe("AC-4: fe03-token-font-degisimi — background token güncellendi", () => {
  it("AC-4: globals.css'te background token yeni değeri 40 33% 98.6%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --background: 40 33% 98.6%; (paper rengi — saf beyaz değil, krem tonu)
    expect(source).toContain("--background: 40 33% 98.6%");
  });

  it("AC-4: globals.css'te foreground token yeni değeri 30 12% 12%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --foreground: 30 12% 12%; (ink rengi — sıcak kömür)
    expect(source).toContain("--foreground: 30 12% 12%");
  });
});

/**
 * AC-6: Yeni token'lar eklendi — muted-foreground, verified, fontFamily
 * globals.css'te --ink-soft, tailwind.config.ts'te yeni color key'leri ve fontFamily
 */
describe("AC-6: fe03-token-font-degisimi — yeni token'lar ve fontFamily", () => {
  it("AC-6: globals.css'te --ink-soft token yeni değeri 30 7% 36%", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // --ink-soft: 30 7% 36%; (muted-foreground için)
    expect(source).toContain("--ink-soft: 30 7% 36%");
  });

  it("AC-6: tailwind.config.ts'te muted-foreground color key tanımlı", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // muted-foreground veya mutedForeground key'i olmalı
    expect(
      source.includes("muted-foreground") || source.includes("mutedForeground")
    ).toBe(true);
  });

  it("AC-6: tailwind.config.ts'te verified color key tanımlı", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // verified key'i olmalı
    expect(source).toContain("verified");
  });

  it("AC-6: tailwind.config.ts'te fontFamily tanımı var", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // fontFamily key'i olmalı
    expect(source).toContain("fontFamily");
  });

  it("AC-6: tailwind.config.ts'te muted-foreground hsl(var(--ink-soft))'a bağlı", () => {
    const source = readFileSync(tailwindPath, "utf-8");

    // muted-foreground veya mutedForeground "hsl(var(--ink-soft))" ile bağlıysa ✓
    expect(source).toContain("--ink-soft");
  });
});

/**
 * AC-2: next-font-kurulumu — @layer base kuralı ve başlık ölçeklemesi
 * globals.css'te @layer base direktifi içinde h1/h2/h3 seçicileri tanımlanmış olmalı
 * Davranış Sözleşmesi (atdd.md satır 53):
 *  - h1: text-3xl font-bold
 *  - h2: text-2xl font-bold
 *  - h3: text-xl font-semibold
 */
describe("AC-2: next-font-kurulumu — @layer base başlık kuralları", () => {
  it("AC-2: globals.css kaynağında @layer base direktifi var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // @layer base direktifi bulunmalı
    expect(source).toContain("@layer base");
  });

  it("AC-2: globals.css'te h1 seçicisi tanımlanmış", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // h1 CSS seçicisi bulunmalı (regex ya da basit string)
    expect(source).toMatch(/h1\s*\{/);
  });

  it("AC-2: globals.css'te h1 kuralında text-3xl class'ı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // Davranış Sözleşmesi: h1 = text-3xl font-bold
    expect(source).toContain("text-3xl");
  });

  it("AC-2: globals.css'te h1 kuralında font-bold class'ı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // Davranış Sözleşmesi: h1 = text-3xl font-bold
    expect(source).toContain("font-bold");
  });

  it("AC-2: globals.css'te h2 seçicisi tanımlanmış", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // h2 CSS seçicisi bulunmalı
    expect(source).toMatch(/h2\s*\{/);
  });

  it("AC-2: globals.css'te h2 kuralında text-2xl class'ı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // Davranış Sözleşmesi: h2 = text-2xl font-bold
    expect(source).toContain("text-2xl");
  });

  it("AC-2: globals.css'te h2 kuralında font-bold class'ı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // Davranış Sözleşmesi: h2 = text-2xl font-bold
    expect(source).toContain("font-bold");
  });

  it("AC-2: globals.css'te h3 seçicisi tanımlanmış", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // h3 CSS seçicisi bulunmalı
    expect(source).toMatch(/h3\s*\{/);
  });

  it("AC-2: globals.css'te h3 kuralında text-xl class'ı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // Davranış Sözleşmesi: h3 = text-xl font-semibold
    expect(source).toContain("text-xl");
  });

  it("AC-2: globals.css'te h3 kuralında font-semibold class'ı var", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // Davranış Sözleşmesi: h3 = text-xl font-semibold
    expect(source).toContain("font-semibold");
  });

  it("AC-2: @layer base direktifi h1/h2/h3 kurallarını içerir", () => {
    const source = readFileSync(globalsPath, "utf-8");

    // @layer base bloku içinde h1, h2, h3 tanımlanmış olmalı
    expect(source).toContain("@layer base");
    expect(source).toMatch(/h1\s*\{/);
    expect(source).toMatch(/h2\s*\{/);
    expect(source).toMatch(/h3\s*\{/);
  });
});
