# Test Diff — tasarim-sistemi-temel-bilesenler
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar
- `frontend/components/ui/button.test.tsx` (yeni, 38 test) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-9.
- `frontend/components/ui/card.test.tsx` (yeni, 13 test) — AC-8.
- `frontend/components/ui/badge.test.tsx` (yeni, 21 test) — AC-7.
- `frontend/components/ui/alert.test.tsx` (yeni, 27 test) — AC-6.

Toplam: 99 test.

## AC → Test eşleşmesi
| AC | Test dosyası |
|---|---|
| AC-1 (happy path, geriye dönük uyumluluk) | button.test.tsx → "AC-1: ..." (6 test) |
| AC-2 (destructive) | button.test.tsx → "AC-2: ..." (4 test) |
| AC-3 (secondary/ghost) | button.test.tsx → "AC-3: ..." (5 test) |
| AC-4 (size sm/md/lg) | button.test.tsx → "AC-4: ..." (9 test) |
| AC-5 (className override, KRİTİK) | button.test.tsx → "AC-5: ..." (4 test) |
| AC-9 (mevcut çağıran regresyonu) | button.test.tsx → "AC-9: ..." (6 test) |
| AC-6 (Alert variant'ları) | alert.test.tsx (27 test) |
| AC-7 (Badge variant'ları) | badge.test.tsx (21 test) |
| AC-8 (Card) | card.test.tsx (13 test) |

## Not — düzeltme
İlk dispatch'te 4 dosyanın tamamında geçersiz bir JSX kalıbı vardı: `<Button variant="primary" as any>`. `as any` JSX'te bir type-cast değil — iki ayrı anlamsız boolean prop (`as`, `any`) olarak parse edilir ve niyet edilen tip-atlatma işlevini yerine getirmiyordu; `typecheck` gate'ini kıracaktı. Orkestratör bunu tespit edip tüm 4 dosyada (button: 22, badge: 17, alert: 23 — toplam 62 yer) `as any` metnini kaldırarak düzeltti, geri kalan JSX (variant/size/className/children) aynen korundu.

## Durum
Testler şu an **red** bekleniyor (implementasyon henüz yok — `card.tsx`/`badge.tsx`/`alert.tsx` hiç yok, `button.tsx`'te `variant`/`size` prop'u yok). `code-copilot` bir sonraki adım.
