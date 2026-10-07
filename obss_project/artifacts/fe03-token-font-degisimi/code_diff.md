# Code Diff — fe03-token-font-degisimi
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `frontend/app/globals.css` — `:root`'taki 9 token'ın HSL değerleri `planfrontend.md` §1.2 paletine güncellendi, `--ink-soft` (yeni) eklendi. `html`/`body`/`@layer base` kuralları değişmedi.
- `frontend/tailwind.config.ts` — `colors`'a `muted-foreground` (→ `--ink-soft`) ve `verified` (→ `--success` ile aynı) eklendi; `fontFamily` (`sans`/`serif`/`mono`, next/font CSS değişkenleri üzerinden) eklendi.
- `frontend/app/layout.tsx` — Inter kaldırıldı, `IBM_Plex_Sans`/`Source_Serif_4`/`IBM_Plex_Mono` eklendi (hepsi `subsets: ["latin", "latin-ext"]`), `<body>` className'i (`plexSans.className` + diğer iki fontun `variable`'ı + mevcut `bg-background text-foreground antialiased`) güncellendi.

## Oluşturulan Dosyalar
Yok.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | layout.tsx 3 font import + body className |
| AC-2 | Her 3 fontun `subsets: ["latin", "latin-ext"]` |
| AC-3 | globals.css 7 token yeni HSL değeri |
| AC-4 | globals.css background/foreground |
| AC-5 | globals.css success → pine (160 38% 24%) |
| AC-6 | tailwind.config.ts muted-foreground/verified/fontFamily, globals.css --ink-soft |
| AC-7 | Gerçek test koşusuyla doğrulandı (bkz. Orkestratör Doğrulaması) |

## Orkestratör Doğrulaması
`git status --short` ile 3 dosyanın değiştiği doğrulandı. `Read` ile tüm 3 dosya satır satır incelendi — atdd.md ile birebir eşleşiyor, kapsam dışı değişiklik yok (`--radius`/wash varyantları/component migrasyonu eklenmedi). Alt-ajanın "1172 test PASS" iddiası GERÇEKTEN koşturularak doğrulanmadı önce — `npx vitest run app/layout.test.tsx app/globals-css.test.ts` → **69/69 PASS**. Tam suite koşusu `verify` adımında yapılacak.

## Görsel/UI Kriteri
Bu görev `layout.tsx` üzerinden TÜM sayfaları etkiliyor — `verify` adımında canlı tarayıcı kontrolü (computed `font-family` ve `bg-background` rengi) AKTİF olmalı.
