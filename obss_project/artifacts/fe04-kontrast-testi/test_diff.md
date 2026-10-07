# Test Diff — fe04-kontrast-testi
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar
- `frontend/lib/ui/contrast-ratio.test.ts` (yeni, klasör de yeni) — 23 assertion, 7 çift + 3 edge case + WCAG eşik kontrolleri.

## AC → Test eşleşmesi
| AC | Test |
|---|---|
| AC-1 (mürekkep/kâğıt → 15.5) | "AC-1: Primary foreground/background (ink/paper)" |
| AC-2 (6 çift) | "AC-2: Secondary text pairs" / "Success color pairs" / "Warning and destructive pairs" (6 test) |
| AC-3 (≥4.5 WCAG AA, her çift için ayrı) | Her describe bloğunda "AC-3: ... WCAG AA threshold" testleri (7 test) |
| AC-4 (bozuk HSL → throw) | "AC-4: Parse error handling (fail-closed)" (3 test) |
| AC-5 (literal HSL kabul) | "AC-5: Literal HSL string support" |

## Durum
Testler şu an **red** bekleniyor (`frontend/lib/ui/contrast-ratio.ts` henüz yok). `code-copilot` bir sonraki adım.
