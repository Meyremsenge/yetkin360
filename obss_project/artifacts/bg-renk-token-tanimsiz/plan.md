# Plan — bg-renk-token-tanimsiz
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (CSS/layout dosyaları + Görsel/UI kriteri dolu).
Design Direction adımı atlandı — bu bir mevcut-UI bug fix'i, yeni tasarım/reshape değil.

## Discover (Playwright/Browser pane — canlı doğrulama)
- `http://localhost:3000/giris` dark color-scheme ile açıldı.
- `getComputedStyle(document.body).backgroundColor` → `"rgba(0, 0, 0, 0)"` — Jira'daki iddia canlı doğrulandı.
- `frontend/components/ui/button.tsx` zaten shadcn tarzı ama `bg-slate-900`/`text-white` gibi **hardcoded** Tailwind renkleri kullanıyor, `bg-background` gibi token kullanmıyor → bu değişiklik mevcut bileşenleri bozmaz (çakışma riski yok, AC-4 ile tutarlı).
- `frontend/components.json` yok — proje shadcn CLI ile kurulmamış, bileşenler elle yazılmış ama "shadcn standardı" token isimlendirmesini (Jira'nın istediği gibi) hâlâ uygulanabilir.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/globals.css | `:root` içine shadcn standardı renk token'ları (`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--border`, `--destructive`, `--success`, `--warning`) eklenecek; `body` seçicisine `@apply bg-background text-foreground antialiased`; `html` seçicisine `color-scheme: light` eklenecek (AC-1, AC-2) | low |
| frontend/tailwind.config.ts | `theme.extend.colors` içine token'ları `hsl(var(--...))` ile bağlama (AC-3) | low |
| frontend/app/layout.tsx | Jira "body'de sınıf yok" diyor ama globals.css'teki `body { @apply ... }` seçicisi zaten tüm body elemanlarına uygulanacağından (Tailwind `@apply` CSS seçici bazlı çalışır, class eklemeye gerek yok) — **bu dosyada değişiklik gerekmeyebilir**. `code-copilot` globals.css'teki yaklaşımı seçerse layout.tsx'e dokunmaz; `body` üzerine doğrudan `className` eklemeyi tercih ederse bu dosya da değişir. Karar code-copilot'a bırakılıyor (ikisi de AC-1'i karşılar). | low |

## New Files
Yok.

## Dependencies
- `frontend/components/ui/*` (button/input/label) — hardcoded renk kullanıyorlar, bu değişiklikten etkilenmezler, dokunulmayacak (kapsam dışı).
- Tailwind JIT derleyicisi: `tailwind.config.ts`'de token tanımlanmadan `bg-background` class'ı kullanılırsa derlenmeyen/geçersiz class olur (atdd.md'nin Davranış Sözleşmesi satır 5 ile eşleşir) — bu yüzden globals.css ve tailwind.config.ts değişiklikleri **aynı commit'te** olmalı.

## Migration Required?
Hayır — saf frontend CSS/config değişikliği, veritabanı/backend'e dokunmuyor.

## Risks
- (atdd.md'den) Mevcut bir komponentin hardcoded rengi ile çakışma — Discover adımında kontrol edildi, `button.tsx`/`input.tsx`/`label.tsx` token kullanmıyor, çakışma riski düşük bulundu.

## Open Questions
Yok — atdd.md'deki Unknowns (layout.tsx'teki mevcut body class'ı) Discover adımında netleşti: `body` elemanının hiç class'ı yok (`<body>`), Jira'nın iddiasıyla birebir örtüşüyor.
