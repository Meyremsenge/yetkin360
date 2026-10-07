# Plan — fe03-token-font-degisimi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (`.css`/`.tsx`). Discover/Audit/Design Direction atlandı — tasarım yönü zaten `planfrontend.md`'de tam olarak belirlenmiş (HSL değerleri, font aileleri dahil), bu görev mekanik bir uygulama, estetik karar vermiyor.

## Discover (kod okuma)
- `frontend/app/globals-css.test.ts` — mevcut testler SADECE `hsl(var(--background))` gibi değişken-referansı kalıplarını (`toContain`) arıyor, hiçbir test tam HSL sayısal değerine (`222 47% 11%` gibi) bağımlı değil. **atdd.md'nin AC-7 Unknown'ı burada çözüldü: regresyon riski yok, değer değişikliği hiçbir mevcut testi kırmaz.**
- `frontend/app/layout.test.tsx` — mevcut testler `next/font/google` import'u ve `"Inter"` string'inin VARLIĞINI arıyor (`toContain("Inter")`) — bu test, Inter kaldırılıp 3 yeni font eklenince KIRMIZI olacak (beklenen, kasıtlı bir davranış değişikliği — AC-1).
- `frontend/vitest.setup.ts` — mevcut `vi.mock("next/font/google", () => ({ Inter: () => ({ className: "mock-inter-font" }) }))` — SADECE `Inter` export'unu mock'luyor. Yeni 3 font (`Source_Serif_4`, `IBM_Plex_Sans`, `IBM_Plex_Mono`) için de mock eklenmesi gerekecek, yoksa `layout.tsx`'in import'u test ortamında patlar (gerçek Google Fonts export'u olmayan isimler mock'ta tanımlı değilse `undefined is not a function` hatası).
- `frontend/tailwind.config.ts` — mevcut `colors` objesi var, `fontFamily` hiç tanımlı değil (Tailwind'in kendi varsayılan `font-sans`/`font-serif`/`font-mono` stack'i kullanılıyor demek, override edilmemiş).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/globals.css | 9 token'ın HSL değerleri güncellenecek + `--ink-soft` (yeni) eklenecek (AC-3/4/5) | low — sadece değer değişimi |
| frontend/tailwind.config.ts | `colors`'a `mutedForeground`/`verified` eklenecek, `fontFamily`'ye `sans`/`serif`/`mono` (next/font CSS değişkenleri üzerinden) eklenecek (AC-1/AC-6) | low |
| frontend/app/layout.tsx | Inter yerine 3 font import edilecek, `subsets` `latin-ext` içerecek (AC-1/AC-2) | medium — TÜM sayfaları etkiliyor |
| frontend/vitest.setup.ts | `vi.mock("next/font/google", ...)` 3 yeni font export'u için genişletilecek (test altyapısı, mevcut `Inter` mock'u KALDIRILMAYACAK çünkü başka bir test onu arıyor olabilir — kontrol edilecek) | low |

## New Files
Yok.

## Dependencies
- `next/font/google`'ın `Source_Serif_4`, `IBM_Plex_Sans`, `IBM_Plex_Mono` export adlarının doğru olduğu `code-copilot`'un build denemesinde (gate 2) doğrulanacak — yanlışsa derleme hatası anında görülür, düzeltme kolay (Next.js'in kendi hata mesajı doğru ismi önerir).
- Mevcut `layout.test.tsx`'teki "Inter" arayan test KASITLI olarak kırmızı olacak ve `test-copilot`'un yeni testleriyle DEĞİŞTİRİLECEK (üzerine yazılacak, atdd.md AC-1'e göre) — bu bir regresyon değil, bilinçli davranış değişikliği.

## Migration Required?
Hayır — saf frontend CSS/config/TSX değişikliği.

## Risks
(atdd.md'den) `layout.tsx` TÜM sayfaları etkiliyor — AC-7'nin (tam suite regresyon) kapsaması şart; az önce doğrulandığı gibi bu risk düşük (testler HSL değerine bağımlı değil).
(plan aşamasında bulunan) `vitest.setup.ts`'in güncellenmesi gerekiyor — güncellenmezse TÜM testler (sadece bu görevin değil, mevcut 1155 testin tamamı, çünkü `layout.tsx` her yerde import ediliyor olabilir) import hatasıyla kırılır. `test-copilot`'a bu açıkça anlatılmalı.

## Open Questions
Yok — tüm kararlar atdd.md'de netleşti, keşif sırasında bulunan ek bilgiler (test bağımlılığı yok, vitest.setup.ts güncellemesi gerekiyor) `code-copilot`'a aktarılacak.
