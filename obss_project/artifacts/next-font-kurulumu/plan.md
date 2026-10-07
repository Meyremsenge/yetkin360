# Plan — next-font-kurulumu
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (`.tsx`/`.css`). Discover/Audit/Design Direction atlandı — bu bir estetik yön seçimi değil, Jira+kullanıcının zaten belirlediği (Inter font, Jira'nın önerdiği başlık ölçeği) mekanik bir kurulum.

## Discover (kod okuma)
- `frontend/app/layout.tsx` — mevcut `<body className="bg-background text-foreground antialiased">`, font class'ı yok.
- `frontend/app/globals.css` — `@tailwind` direktifleri + `:root` token'ları + `body`/`html` kuralları var (YET-244), hiç `@layer base` veya h1/h2/h3 kuralı yok.
- `node_modules/next/font/google` dosyasına doğrudan erişim bu ortamda engellendi (izin hatası) — ama `next/font/google` Next.js 13+'tan beri stabil bir özellik, Next.js 16.3.8'de de desteklendiği resmi dokümantasyonla biliniyor. `verify`'ın build gate'i (gate 2) bunu zaten kanıtlayacak; eğer import hata verirse `code-copilot`'un kendi build denemesinde görülür.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/layout.tsx | `next/font/google`'dan `Inter` import edilip `<body>`'ye className olarak eklenecek (AC-1) | low |
| frontend/app/globals.css | `@layer base` içinde `h1`/`h2`/`h3` varsayılan class'ları eklenecek (AC-2) | low |

## New Files
Yok.

## Dependencies
- Yeni npm paketi yok — `next/font/google`, `next` paketinin kendi alt-modülü.
- Mevcut `body` class'ları (`bg-background text-foreground antialiased`) korunacak, font class'ı bunlara EK olacak (üzerine yazmayacak).

## Migration Required?
Hayır — saf frontend CSS/TSX değişikliği.

## Risks
(atdd.md'den) `layout.tsx` her sayfayı sarmaladığı için bu değişiklik TÜM sayfaları etkiliyor — AC-5'in (tam suite regresyon testi, 1134 test) bu riski kapsaması şart.

## Open Questions
Yok.
