---
name: Frontend kuralları
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.css"
  - "frontend/**"
---

# Frontend

Detay: `docs/yetkin360-final-analiz.md` §14.

## Kararlar (tartışma yok, uygula)

- Sunucu durumu: **TanStack Query**. Yerel durum: React state. **Redux yok** — uygulamanın durumu neredeyse tamamen sunucu durumu.
- Form: React Hook Form + Zod
- Stil: Tailwind + shadcn/ui
- Auth: httpOnly cookie — token'a JS'ten erişilmez, `localStorage` kullanılmaz
- API tipleri OpenAPI'den üretilir, elle yazılmaz

## Güvenlik

- `dangerouslySetInnerHTML` **yasak**
- Rol kontrolü yalnız UX içindir (kullanıcıya yapamayacağını göstermemek). **Güvenlik sınırı değildir** — sunucu her isteği tekrar kontrol eder.
- Hassas veri response'da gelmemeli; gelmişse frontend'de gizlemek çözüm değil, backend hatasıdır → bildir.

## Erişilebilirlik (MVP'de bile atlanmaz)

Müşteri kamu üniversitesi olabilir; erişilebilirlik satın alma şartı olabilir.

- Semantik HTML, her form alanında `<label>`
- Klavye ile tam gezinme, görünür focus
- Kontrast 4.5:1
- Hata mesajları `aria-live` ile duyurulur

shadcn/ui (Radix tabanlı) bunların çoğunu hazır getirir — elle çözmeye çalışma.

## UX

- **Boş durum (empty state) tasarlanmadan ekran bitmiş sayılmaz.** "Henüz bir şey yok" yetmez — ne yapılacağını söyle.
- Onboarding kısa: uzun form kullanıcıyı kaçırır.

## Doğrulama

- Stil değişikliği → `npm run lint`
- Mantık değişikliği → `npm run typecheck` + ilgili bileşen testi

Tüm test paketini her CSS değişikliğinde çalıştırma.
