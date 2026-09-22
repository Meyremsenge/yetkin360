# Code Diff — yet-13-auth-ekranlari (green step)
_6 sıralı/paralel Haiku alt-ajanı ile yazıldı. Her adım `git status --short` + `npx vitest run`/`eslint`/`tsc` ile bu oturumda bizzat doğrulandı — alt-ajan özetlerine güvenilmedi._

## Sonuç
**22 test dosyası, 504 test — hepsi geçiyor.** `eslint app components lib middleware.ts` → 0 hata/0 uyarı.

## Yeni Dosyalar
| Dosya | Amaç |
|---|---|
| frontend/lib/utils.ts | shadcn `cn()` helper |
| frontend/lib/auth/schemas.ts | Zod: registerSchema, loginSchema, forgotPasswordSchema, resetPasswordSchema |
| frontend/components/ui/input.tsx, label.tsx | shadcn temel primitifleri |
| frontend/app/giris/form.tsx | Giriş formu (client component, RHF+Zod) |
| frontend/app/kayit/{page.tsx,form.tsx} | Kayıt sayfası+formu |
| frontend/app/e-posta-dogrula/page.tsx | Otomatik token doğrulama sayfası |
| frontend/app/sifre-unuttum/page.tsx | Şifre unuttum formu |
| frontend/app/sifre-sifirla/page.tsx | Şifre sıfırlama formu |
| frontend/vitest.setup.ts | `@testing-library/jest-dom/vitest` import (matcher setup) |

## Değişen Dosyalar
| Dosya | Ne değişti |
|---|---|
| frontend/app/giris/page.tsx | Placeholder → gerçek form (server component + `form.tsx` client component) |
| frontend/lib/api/client.ts | `register`, `login`, `verifyEmail`, `forgotPassword`, `resetPassword` eklendi (positional parametreli — testlerin pinlediği imza) |
| frontend/lib/auth/should-redirect.ts | `isPublicRoute`'a 4 route eklendi + query-string'i pathname'den ayıklama düzeltmesi (token'lı URL'ler için gerekli) |
| frontend/messages/tr.json | 44 yeni anahtar (kayit.*, epostaDogrula.*, sifreUnuttum.*, sifreSifirla.*, giris.* genişleme, errors.rateLimited) + errors.network metni test regex'iyle uyumlu hale getirildi (app-shell.tsx'te de kullanılıyor, testi kontrol edildi — kırılmadı) |
| frontend/package.json | +react-hook-form, +zod, +@hookform/resolvers, +clsx, +tailwind-merge, +@testing-library/user-event (dev), +@testing-library/jest-dom (dev) — hepsi kullanıcı onayıyla (plan.md §1, §1b + oturum içi jest-dom onayı) |
| frontend/vitest.config.ts | `setupFiles: ["./vitest.setup.ts"]` eklendi |

## Bu Oturumda Bulunup Düzeltilen Sorunlar
1. `client.test.ts`'te fazladan `});` (sözdizimi hatası) — tek satır silindi.
2. `client.test.ts`'teki "New auth functions" describe bloğu yanlışlıkla dış `describe("apiFetch")` bloğunun dışında kalmış, `beforeEach` mock'unu miras almıyordu — kendi `beforeEach`/`afterEach`'i eklendi.
3. `client.ts`'teki `register`/`login`/`resetPassword` object-parametre alıyordu, testler positional bekliyordu — testler doğru referans alınarak `client.ts` düzeltildi (register/login sayfaları da güncellendi).
4. `giris/form.tsx` ve `kayit/form.tsx`'te `error instanceof ApiError` kontrolü, testlerin duck-typed mock hatalarıyla (`new Error()` + bolted-on `.status`) eşleşmiyordu — diğer 3 sayfanın (e-posta-dogrula, sifre-unuttum, sifre-sifirla) zaten kullandığı duck-typing desenine çevrildi.
5. `kayit/form.tsx`'teki 1500ms `setTimeout` yönlendirme gecikmesi test timeout'unu aşıyordu — kaldırıldı, yönlendirme hemen yapılıyor.
6. `@testing-library/jest-dom` eksikti (`toHaveAttribute` vb. matcher'lar çalışmıyordu) — kullanıcı onayıyla eklendi.
7. 5 test dosyasında 58 `no-explicit-any` lint hatası + 11 kullanılmayan değişken uyarısı — test davranışı değiştirilmeden (sadece tip/temizlik) düzeltildi.

## Bilinen, Kapsam Dışı Bırakılan Bulgu
`npx tsc --noEmit -p .` bu oturumda hâlâ bazı hatalar veriyor (`@testing-library/react`'ten `screen`/`waitFor` export edilemiyor gibi) — ama bu hatalar **bu görevden önce var olan, dokunulmamış dosyalarda da** (`app/error.test.tsx`, `app/not-found.test.tsx`, `app/page.test.tsx`) çıkıyor; YET-13'ün bir regresyonu değil, projenin `tsc --noEmit` kurulumunda önceden var olan bir boşluk (muhtemelen vitest'in kendi type-check'i vitest üzerinden geçiyor, düz `tsc` farklı moduleResolution davranışı sergiliyor). `verify` adımında ayrıca raporlanacak, bu görevin kapsamında DÜZELTİLMEDİ (ayrı bir altyapı konusu).

## Sonraki Adım
`verify` — kalite kapılarının tamamı (lint/typecheck/test/security vb.) çalıştırılacak.
