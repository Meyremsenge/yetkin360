# Plan — fe04-kontrast-testi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok — hiçbir `.tsx`/`.jsx`/`.css`/`.html` dosyası yok (sadece `.ts`, saf fonksiyon + test), "Görsel/UI kriteri" atdd.md'de boş.

## Discover (kod okuma)
- `frontend/lib/*/*.test.ts` — mevcut konvansiyon: her modül kendi klasöründe (`lib/<alan>/<dosya>.test.ts`), aynı klasörde implementasyon dosyası. `lib/ui/` klasörü henüz yok — bu görev onu açacak ilk modül.
- Proje `vitest` kullanıyor, saf fonksiyon testleri için ekstra mock/fixture gerekmiyor (bu görev DOM/React render içermiyor).

## Files to Modify
Yok.

## New Files
| File | Purpose |
|------|---------|
| frontend/lib/ui/contrast-ratio.ts | `hslToRgb`, `relativeLuminance`, `contrastRatio` saf fonksiyonları (AC-1/2/3/4/5) |
| frontend/lib/ui/contrast-ratio.test.ts | 7 çift + 1 edge case testi (atdd.md Davranış Sözleşmesi) |

## Dependencies
- Yeni npm paketi yok (CAVEMAN, atdd.md'nin kararı) — WCAG formülü elle yazılacak.
- `lib/ui/status.ts` (planfrontend.md §1.6'da bahsedilen, henüz yok) ile aynı klasörü paylaşacak — bu görev o dosyayı OLUŞTURMAZ, sadece klasörü açar.

## Migration Required?
Hayır.

## Risks
(atdd.md'den) Senkronizasyon riski kabul edildi — test dosyasındaki HSL literalleri `globals.css` ile manuel senkron tutulmalı, test dosyasına bunu hatırlatan bir yorum eklenecek.

## Open Questions
Yok.
