# Code Diff — bg-renk-token-tanimsiz
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `frontend/app/globals.css` — `:root` içine 9 shadcn-standart renk token'ı (`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--border`, `--destructive`, `--success`, `--warning`); `html { color-scheme: light; }`; `body { @apply bg-background text-foreground antialiased; }`.
- `frontend/tailwind.config.ts` — `theme.extend.colors` içine 9 token'ın `hsl(var(--...))` bağlantısı.
- `frontend/app/layout.tsx` — `<body>` elemanına `className="bg-background text-foreground antialiased"` eklendi (globals.css'teki `@apply` kuralı derleme zamanı CSS'e gömüldüğü için JSX render çıktısında görünmez; bu yüzden hem CSS kuralı hem className gerekli).

## Oluşturulan Dosyalar
Yok.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | globals.css `:root` + `body { @apply ... }` + layout.tsx `className` |
| AC-2 | globals.css `html { color-scheme: light; }` |
| AC-3 | tailwind.config.ts `theme.extend.colors` |
| AC-4 | button.tsx/input.tsx/label.tsx'e dokunulmadı (regresyon yok) |
| AC-5 | globals.css + tailwind.config.ts tutarlı token isimleri |

## Dokunulmayan Dosyalar (bilinçli)
- `frontend/components/ui/button.tsx`, `input.tsx`, `label.tsx` — kapsam dışı, hardcoded renkleri korundu.
- Test dosyaları (`layout.test.tsx`, `globals.test.css.ts`) — değiştirilmedi.

## Orkestratör Doğrulaması
`git status --short` ile üç dosyanın (`globals.css`, `tailwind.config.ts`, `layout.tsx`) gerçekten değiştiği doğrulandı; `Read` ile içerikleri satır satır incelendi — TODO/placeholder/kapsam dışı değişiklik yok. Alt-ajanın "1014/1014 test PASS" iddiası burada tekrar koşulmadı — bu doğrulama `verify` adımına ait.

## Görsel/UI Kriteri
Bu görev `.css`/`.tsx` dosyalarına dokunuyor — `verify` adımında gate 11 (`vision-test`) N/A değil, AKTİF çalışmalı.
