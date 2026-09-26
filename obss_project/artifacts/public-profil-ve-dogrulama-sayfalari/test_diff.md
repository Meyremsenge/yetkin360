# test_diff.md — public-profil-ve-dogrulama-sayfalari

## Oluşturulan/Genişletilen Dosyalar
- `frontend/lib/auth/should-redirect.test.ts` — GENİŞLETİLDİ, 6 yeni test (mevcut korundu)
- `frontend/app/p/[slug]/page.test.tsx` — YENİ, 5 test
- `frontend/app/v/[token]/page.test.tsx` — YENİ, 4 test

## AC → Test Eşleştirme
| AC | Test |
|---|---|
| AC-6 (public erişim, `/p/`) | `should-redirect.test.ts`: "allows '/p/{slug}' without cookies" + trailing-slash + cookie-varken varyantları |
| AC-6 (public erişim, `/v/`) | `should-redirect.test.ts`: "allows '/v/{token}' without cookies" + cookie-varken varyantı |
| **AC-7/AC-S2 (KRİTİK regresyon)** | `should-redirect.test.ts`: "AC-7 (KRİTİK regresyon): '/p/' prefix kontrolü '/profil'i yanlışlıkla public yapmamalı" — `/profil` hâlâ `buildLoginUrl` sonucunu TAM eşleşmeyle döndürmeli |
| AC-1 | `p/[slug]/page.test.tsx`: happy path render |
| AC-3 | `p/[slug]/page.test.tsx`: 404 "Kayıt bulunamadı" |
| AC-5 | `p/[slug]/page.test.tsx`: boş liste → 404 değil, boş durum mesajı |
| AC-8 (p) | `p/[slug]/page.test.tsx`: network hatası → genel mesaj |
| AC-9 (p) | `p/[slug]/page.test.tsx`: düz metin render |
| AC-2 | `v/[token]/page.test.tsx`: happy path render |
| AC-4 | `v/[token]/page.test.tsx`: 404 "Kayıt bulunamadı" |
| AC-8 (v) | `v/[token]/page.test.tsx`: timeout hatası → genel mesaj |
| AC-9 (v) | `v/[token]/page.test.tsx`: düz metin render |

## Durum
RED (beklenen) — `frontend/lib/api/public.ts`, `frontend/app/p/[slug]/page.tsx`, `frontend/app/v/[token]/page.tsx` henüz yok; `should-redirect.ts`'in `isPublicRoute()`'u `/p/`/`/v/` içermiyor.

## Kritik not
AC-7 regresyon testi bu görevin en önemli test satırı — `code-copilot`'un `isPublicRoute()`'a ekleyeceği prefix kontrolünün `pathname.startsWith("/p/")` (eğik çizgili) olduğunu, `/profil`'i etkilemediğini bu test kanıtlayacak.
