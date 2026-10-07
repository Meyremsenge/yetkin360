# Code Diff — tasarim-sistemi-temel-bilesenler
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `frontend/components/ui/button.tsx` — `variant` (primary/secondary/destructive/ghost, varsayılan primary) ve `size` (sm/md/lg, varsayılan md) prop'ları eklendi. `cn()` (clsx+tailwind-merge) ile class birleştirme, `className` en sonda (override garantisi).

## Oluşturulan Dosyalar
- `frontend/components/ui/card.tsx` — tek tip Card bileşeni.
- `frontend/components/ui/badge.tsx` — 4 variant'lı Badge.
- `frontend/components/ui/alert.tsx` — 4 variant'lı Alert.

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar
1. **İlk `button.tsx` implementasyonu icat edilmiş bir kural içeriyordu:** `hasBackgroundOverride = className?.includes("bg-")` kontrolü, className "bg-" içeriyorsa variant'ın hover class'ını TAMAMEN siliyordu. Bu atdd.md'de hiç yazmayan bir kısayoldu, hem gereksizdi (tailwind-merge zaten çakışan hover class'larını doğru çözer) hem de yanlış davranış üretiyordu (sadece arka plan rengini override eden bir çağıran, istemeden hover'ını da kaybediyordu). Orkestratör kod incelemesiyle (alt-ajanın "tüm testler PASS" raporuna güvenmeden) bulundu, ikinci bir Haiku dispatch'iyle kaldırıldı — artık `hoverClasses[variant]` koşulsuz ekleniyor, `cn()`/tailwind-merge çakışmayı kendi çözüyor.
2. **Bir test (AC-5, `button.test.tsx`) substring-çakışması nedeniyle yanlışlıkla kırmızıydı:** `not.toContain("bg-destructive")` araması, kalması GEREKEN `hover:bg-destructive/90` class'ını da (substring olarak "bg-destructive" içerdiği için) yakalayıp testi kırıyordu — implementasyon doğruydu, test yanlış yazılmıştı. Test dosyası, tam token eşleşmesi (`className.split(" ")` + `not.toContain`) kullanacak şekilde düzeltildi.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | `button.tsx` variant="primary" (varsayılan) → mevcut class'lar korundu |
| AC-2 | `button.tsx` variant="destructive" → `bg-destructive`/`hover:bg-destructive/90` |
| AC-3 | `button.tsx` variant="secondary"/"ghost" |
| AC-4 | `button.tsx` size="sm"/"md"/"lg" |
| AC-5 | `cn()` ile className en sonda, tailwind-merge çakışmayı çözer |
| AC-6 | `alert.tsx` 4 variant |
| AC-7 | `badge.tsx` 4 variant |
| AC-8 | `card.tsx` |
| AC-9 | Gerçek test koşusuyla doğrulandı (bkz. Orkestratör Doğrulaması) |

## Dokunulmayan Dosyalar (bilinçli)
- `input.tsx`, `label.tsx`, `app-shell.tsx`, `skills-section.tsx` — kapsam dışı, dokunulmadı.
- cva bağımlılığı eklenmedi (atdd.md'nin Assumptions bölümü, kullanıcı onaylı).

## Orkestratör Doğrulaması
`git status --short` ile dosyaların değiştiği doğrulandı. `Read` ile tüm 4 dosya satır satır incelendi — bu incelemede icat edilmiş `hasBackgroundOverride` kısayolu bulunup düzeltildi (yukarıya bkz.). Alt-ajanın "1134 test PASS" iddiası GERÇEKTEN koşturularak doğrulanmadı önce — gerçek koşuda 1 test FAIL çıktı (yukarıdaki #2), düzeltildi. Düzeltme sonrası `npx vitest run components/ui/{button,card,badge,alert}.test.tsx` → **95/95 PASS**.

## Görsel/UI Kriteri
Bu görev `.tsx` dosyalarına dokunuyor AMA atdd.md'nin kendi kararı: hiçbir sayfa bu bileşenleri henüz KULLANMIYOR (migrasyon kapsam dışı) — `verify` adımında gate 11/12 (`vision-test`) **N/A** olmalı, sadece `button.tsx`'in mevcut kullanıcılarının (app-shell/skills-section) regresyonsuz kaldığı tam test suite koşusuyla doğrulanmalı.
