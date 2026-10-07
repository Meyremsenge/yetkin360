# Test Diff — fe03-token-font-degisimi
_Reference: atdd.md, plan.md_

## Genişletilen/Güncellenen Dosyalar
- `frontend/app/layout.test.tsx` — "AC-1" describe bloğu güncellendi: eski "Inter" testi SİLİNDİ, yerine 3 font (Source_Serif_4/IBM_Plex_Sans/IBM_Plex_Mono) + latin-ext testleri eklendi (5 test).
- `frontend/app/globals-css.test.ts` — AC-3 (7 test), AC-4 (2 test), AC-6 (5 test) describe blokları eklendi.
- `frontend/vitest.setup.ts` — `next/font/google` mock'una 3 yeni font eklendi, mevcut `Inter` mock'u KORUNDU.

## AC → Test eşleşmesi
| AC | Test |
|---|---|
| AC-1 (3 font import) | layout.test.tsx "AC-1" (3 yeni test: Source_Serif_4, IBM_Plex_Sans, IBM_Plex_Mono + güncellenen render testi) |
| AC-2 (latin-ext Türkçe karakter) | layout.test.tsx "AC-1" → "latin-ext desteği var" testi |
| AC-3 (7 token yeni HSL değeri) | globals-css.test.ts "AC-3" (7 test) |
| AC-4 (background/foreground) | globals-css.test.ts "AC-4" (2 test) |
| AC-5 (tam suite regresyon) | `verify` adımında tam suite koşusu |
| AC-6 (yeni token'lar + fontFamily) | globals-css.test.ts "AC-6" (5 test) |

## Durum
Testler şu an **red** bekleniyor (19 test, implementasyon henüz yok). `code-copilot` bir sonraki adım.

## Not
`vitest.setup.ts` test altyapısı dosyası güncellendi — bu test dosyası değil ama `code-copilot`'un bu mock'lara dayanarak `layout.tsx`'i yazması gerekiyor (gerçek Google Fonts export adlarıyla: `Source_Serif_4`, `IBM_Plex_Sans`, `IBM_Plex_Mono`).
