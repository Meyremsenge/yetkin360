# Plan — tasarim-sistemi-temel-bilesenler
_Reference: atdd.md_

Frontend-pipeline: tetikleyici teknik olarak var (`.tsx` dosyaları) ama alt adımları atlandı:
- **Discover atlandı** — hiçbir sayfa bu bileşenleri henüz kullanmayacak (migrasyon kapsam dışı), canlı tarayıcıda gezinmek yeni bileşenler hakkında bilgi vermez; mevcut token sistemi (globals.css/tailwind.config.ts, YET-244'te kuruldu) zaten statik kod okumasıyla biliniyor.
- **Audit atlandı** — mevcut UI'da Card/Badge/Alert implementasyonu yok (yeni ekleniyorlar), audit edilecek bir şey yok; `button.tsx` zaten atdd.md aşamasında incelendi.
- **Design Direction atlandı** — bu bir yeni-UI/kapsamlı-reshape değil; Jira zaten somut variant isimlerini (primary/secondary/destructive/ghost, error/success/warning/info) belirlemiş ve YET-244'te kurulan token sistemine (shadcn-standart, light tema) bağlı kalınacak, yeni bir estetik yön seçilmiyor.

## Discover (kod okuma)
- `frontend/components/ui/button.tsx` — şu an: `className = ""` prop'u alıp `` `rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 ${className}` `` şeklinde template literal ile birleştiriyor (template literal, `cn()`/twMerge DEĞİL — bu önemli, AC-5'in "className kazanır" davranışı şu an zaten template literal sonunda olduğu için ÇALIŞIYOR, ama twMerge'e geçersek çakışan class'larda (`bg-slate-900` vs `bg-destructive`) ikisi de literal string olarak kalır, twMerge olmadan İKİSİ DE DOM'da görünür (son yazılan kazanır CSS specificity'de, ama her ikisi de class listesinde kalır) — `cn()` kullanmak bu belirsizliği twMerge ile netleştirir, gerçek çakışma çözümü sağlar).
- `frontend/lib/utils.ts` — `cn()` zaten `clsx` + `twMerge` kullanıyor (shadcn-standart desen), yeni bileşenler bunu kullanacak.
- `frontend/components/ui/input.tsx`, `label.tsx` — bu görevde DOKUNULMAYACAK (atdd.md'nin kapsamı sadece Button/Card/Badge/Alert).
- `frontend/app/globals.css`, `frontend/tailwind.config.ts` — `--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--border`, `--destructive`, `--success`, `--warning` token'ları ZATEN var (YET-244), yeni bileşenler bunları kullanacak, yeni token eklenmeyecek.
- `frontend/components/app-shell.tsx` — mevcut `<Button>` çağrısı (`className="bg-slate-600 hover:bg-slate-700"`) ve `skills-section.tsx`'teki (`className="bg-red-600 hover:bg-red-700..."`) — bunlar AC-5/AC-9'un regresyon kanıtı, bu dosyalara DOKUNULMAYACAK ama testleri bu görevden sonra da PASS kalmalı.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/components/ui/button.tsx | `variant`/`size` prop'ları eklenecek, template literal yerine `cn()` kullanılacak (AC-1/2/3/4/5/9) | medium — zaten kullanımda, geriye dönük uyumluluk kritik |

## New Files
| File | Purpose |
|------|---------|
| frontend/components/ui/card.tsx | AC-8: tek tip Card bileşeni |
| frontend/components/ui/badge.tsx | AC-7: variant'lı Badge bileşeni |
| frontend/components/ui/alert.tsx | AC-6: variant'lı Alert bileşeni |

## Dependencies
- `frontend/lib/utils.ts`'teki mevcut `cn()` (clsx + tailwind-merge) — yeni bağımlılık eklenmeyecek (cva YOK, atdd.md'nin Assumptions bölümünde gerekçeli).
- Tailwind JIT: `tailwind.config.ts`'de zaten tanımlı `bg-destructive`, `bg-muted`, `text-success` vb. class'lar kullanılacak, yeni config değişikliği gerekmiyor.

## Migration Required?
Hayır — saf frontend bileşen kodu, backend/DB'ye dokunmuyor.

## Risks
(atdd.md'den) `button.tsx` genişletmesi tek gerçek risk taşıyan değişiklik — AC-9'un (tam suite regresyon testi, 1039 mevcut test) bu riski kapsaması şart.
(plan aşamasında bulunan) Mevcut `button.tsx` template literal kullanıyor, `cn()`'e geçiş davranışı İNCE şekilde değiştirebilir (twMerge çakışan class'ları gerçekten KALDIRIR, template literal ikisini de bırakırdı) — bu AC-5'in TAM olarak istediği düzeltme (çakışma çözümü), ama `code-copilot`'a bu farkın BİLİNÇLİ bir davranış değişikliği olduğu (regresyon değil, iyileştirme) açıkça anlatılmalı.

## Open Questions
Yok — atdd.md'deki tüm kararlar (cva yerine clsx/tailwind-merge, kapsam daraltma) netleşti. Plan aşamasında bulunan tek ek bilgi (template literal → cn() geçişinin twMerge semantiği) `code-copilot`'a aktarılacak, kullanıcıya tekrar sorulmasına gerek yok.
