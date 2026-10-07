# Code Diff — next-font-kurulumu
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `frontend/app/layout.tsx` — `next/font/google`'dan `Inter` import edildi, `<body>` className'ine `inter.className` eklendi (mevcut `bg-background text-foreground antialiased` korunarak).
- `frontend/app/globals.css` — `@layer base` içinde `h1`/`h2`/`h3` için `text-3xl font-bold`/`text-2xl font-bold`/`text-xl font-semibold` eklendi.
- `frontend/vitest.setup.ts` — `next/font/google`'ın global test mock'u eklendi (`Inter: () => ({ className: "mock-inter-font" })`) — test ortamında (jsdom) gerçek Next.js font-loading webpack mekanizması çalışmadığından gerekli, mevcut Next.js projelerinde standart pratik.

## Oluşturulan Dosyalar
Yok.

## Review Sürecinde Bulunan ve Düzeltilen Sorun
Bir test (`layout.test.tsx`, AC-1) `expect(result).toContain("className")` ile yanlış bir şey arıyordu — `renderToStaticMarkup` JSX'i gerçek HTML'e çevirir, HTML'de `className` hiçbir zaman literal olarak geçmez (her zaman `class` olur). İmplementasyon doğruydu (`<body class="mock-inter-font ...">` doğru render ediliyordu), test yanlış yazılmıştı. Orkestratör gerçek test koşusuyla (alt-ajanın "1 test yanlış yazılmış" iddiasına güvenmeden) doğrulayıp test dosyasını düzeltti — artık mock class adının (`mock-inter-font`) varlığını arıyor.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | `layout.tsx` Inter import + `inter.className` |
| AC-2 | `globals.css` `@layer base` h1/h2/h3 |
| AC-3 | Mevcut `bg-background text-foreground antialiased` string'i korundu (silinmedi, eklendi) |
| AC-4 | Statik testle doğrulanamaz — `verify` adımında canlı build/tarayıcı kontrolü gerekli |
| AC-5 | 52/52 test (yerel koşu) + `verify`'da tam 1134+ test suite koşusu |

## Orkestratör Doğrulaması
`git status --short` ile 3 dosyanın değiştiği, test dosyalarının (içerik olarak) dokunulmadığı doğrulandı (satır sayıları test-copilot'un bıraktığıyla birebir aynı). `Read` ile `layout.tsx`/`globals.css`/`vitest.setup.ts` satır satır incelendi. Testler GERÇEKTEN çalıştırıldı (alt-ajanın "1134 PASS" gibi bir iddiası bu görevde yoktu ama "1 test yanlış yazılmış" iddiası doğrulandı) — düzeltme sonrası 52/52 PASS.

## Görsel/UI Kriteri
Bu görev `.tsx`/`.css` dosyalarına dokunuyor ve TÜM sayfaları etkiliyor (layout her sayfayı sarmalıyor) — `verify` adımında canlı tarayıcı kontrolü (gate 7/12, tam vision-test değil ama `getComputedStyle` ile font-family doğrulaması) AKTİF olmalı, N/A değil.
