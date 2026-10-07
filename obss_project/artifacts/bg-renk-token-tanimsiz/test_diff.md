# Test Diff — bg-renk-token-tanimsiz
_Reference: atdd.md, plan.md_

## Oluşturulan/Genişletilen Dosyalar
- `frontend/app/layout.test.tsx` (genişletildi) — mevcut AC-9 testlerine ek olarak AC-1, AC-2, AC-6 blokları eklendi.
- `frontend/app/globals.test.css.ts` (yeni) — AC-3, AC-4, AC-5 kaynak-dosya testleri.

## AC → Test eşleşmesi
| AC | Test dosyası / describe bloğu |
|---|---|
| AC-1 (happy path: body token class'ları) | `layout.test.tsx` → `AC-1: bg-renk-token-tanimsiz — body arka planı ve metin rengi` (4 test) |
| AC-2 (color-scheme: light) | `layout.test.tsx` → `AC-2: bg-renk-token-tanimsiz — color-scheme: light` (1 test, kaynak-dosya okuma; ilk hatalı render-tabanlı test orkestratör tarafından kaldırıldı — bkz. not) |
| AC-3 (tailwind.config.ts token bağlantısı) | `globals.test.css.ts` → `AC-3: ... tailwind.config.ts token bağlantısı` (3 test) |
| AC-4 (mevcut komponent regresyonu — button.tsx hardcoded renkler korunur) | `globals.test.css.ts` → `AC-4: ... mevcut komponent renkleri korunur` (4 test) |
| Davranış Sözleşmesi satır 5 (kısmi uygulama: :root var, tailwind bağlantısı yok) | `globals.test.css.ts` → `AC-5: ... CSS token ve Tailwind tutarlılığı` (6 test) |
| Davranış Sözleşmesi satır 6 (kısmi uygulama: body class'ı hiç kullanılmıyor) | `layout.test.tsx` → `AC-6: ... body class'ı uygulanması` (2 test) |

## Not — düzeltme
İlk dispatch'te AC-2 bloğunun ilk testi `renderToStaticMarkup` çıktısında "color-scheme"/"light" string'lerini arıyordu — ama bu bilgi `globals.css`'ten (harici stylesheet) geleceği için SSR string'ine hiç karışmaz; doğru implementasyonla bile sonsuza dek kırmızı kalacak bir yanlış-negatiftü. Orkestratör bunu tespit edip ikinci (doğru, kaynak-dosya okuyan) testi koruyarak ilkini sildi.

## Durum
Testler şu an **red** (implementasyon henüz yok — globals.css sadece 3 satır, tailwind.config.ts'in theme.extend'i boş, layout.tsx'te body class'ı yok). `code-copilot` bir sonraki adım.
