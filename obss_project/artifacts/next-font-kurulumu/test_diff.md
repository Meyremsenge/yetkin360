# Test Diff — next-font-kurulumu
_Reference: atdd.md, plan.md_

## Genişletilen Dosyalar
- `frontend/app/layout.test.tsx` — AC-1 (3 test), AC-3 (4 test), AC-5 (3 test) describe blokları eklendi.
- `frontend/app/globals-css.test.ts` — AC-2 (11 test) describe bloğu eklendi.

## AC → Test eşleşmesi
| AC | Test dosyası / describe bloğu |
|---|---|
| AC-1 (next/font/google + Inter import) | layout.test.tsx → "AC-1: next-font-kurulumu — Inter font import'u" (3 test) |
| AC-2 (@layer base h1/h2/h3) | globals-css.test.ts → "AC-2: next-font-kurulumu — @layer base başlık kuralları" (11 test) |
| AC-3 (mevcut class'lar korunur, regresyon yok) | layout.test.tsx → "AC-3: next-font-kurulumu — mevcut sayfalar regresyon yok" (4 test) |
| AC-4 (derleme zamanı self-host) | Bu AC kod-okuma testiyle doğrulanamıyor (build çıktısına bakmak gerekir) — `verify` adımında canlı build/tarayıcı kontrolüyle doğrulanacak, not düşüldü. |
| AC-5 (tam suite regresyon) | layout.test.tsx → "AC-5: next-font-kurulumu — regresyon" (3 test, render sağlamlığı) + `verify`'da tam 1134 test suite koşusu |

## Durum
Testler şu an **red** bekleniyor (implementasyon henüz yok — `layout.tsx`'te font import'u yok, `globals.css`'te `@layer base` yok). `code-copilot` bir sonraki adım.

## Not
AC-4 (self-host/ağ bağımlılığı yok) statik test dosyasıyla doğrulanamaz — `verify` adımında gerçek `npm run build` çıktısında `fonts.googleapis.com` referansı olmadığının ve canlı tarayıcıda `getComputedStyle` ile font-family'nin doğrulanması gerekiyor.
