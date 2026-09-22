# Plan — yet-13-auth-ekranlari
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/giris/page.tsx | Placeholder yerine gerçek form (AC-2/3/4/9/10/11/12) | medium — mevcut testler (giris/page.test.tsx) "form YOK" varsayıyor, tamamen yeniden yazılacak |
| frontend/lib/api/client.ts | `register`/`login`/`verifyEmail`/`forgotPassword`/`resetPassword` fonksiyonları eklenir (mevcut `apiFetch` üstüne ince sarmalayıcılar) | low — ekleme, mevcut `apiFetch`/`performFetchWithRefresh` davranışı değişmez |
| frontend/lib/auth/should-redirect.ts | `isPublicRoute` allowlist'e `/kayit`, `/e-posta-dogrula`, `/sifre-unuttum`, `/sifre-sifirla` eklenir — yoksa middleware bu sayfaları cookie'siz kullanıcı için `/giris`'e yönlendirir, akış kırılır | **high — auth mantığı, CLAUDE.md gereği kod yazılmadan önce açık onay gerekir** |
| frontend/messages/tr.json | `kayit`, `sifreUnuttum`, `sifreSifirla`, `epostaDogrula` anahtarları + `giris` genişler (form etiketleri, hata mesajları) | low |

## New Files
| File | Purpose |
|------|---------|
| frontend/app/kayit/page.tsx | Kayıt formu (AC-1, AC-9, AC-S1) |
| frontend/app/kayit/page.test.tsx | Kayıt sayfası testi |
| frontend/app/e-posta-dogrula/page.tsx | Token'ı otomatik POST eden doğrulama sayfası (AC-5, AC-6, AC-S3) |
| frontend/app/e-posta-dogrula/page.test.tsx | Doğrulama sayfası testi |
| frontend/app/sifre-unuttum/page.tsx | E-posta gir → her zaman aynı mesaj (AC-7, AC-S2) |
| frontend/app/sifre-unuttum/page.test.tsx | Test |
| frontend/app/sifre-sifirla/page.tsx | Token + yeni şifre formu (AC-8, AC-6, AC-S3) |
| frontend/app/sifre-sifirla/page.test.tsx | Test |
| frontend/lib/api/client.test.ts (mevcut dosyaya EKLEME, yeni dosya değil) | register/login/verifyEmail/forgotPassword/resetPassword fonksiyon testleri — **not: aşağıda "Dependencies" altında düzeltildi, bu satır New Files'ta yanlış, gerçek karşılığı "Files to Modify" listesinde `client.ts` yanına eklenmeli** |
| frontend/lib/auth/register-schema.ts (veya form içi validasyon — Open Question #1'e bağlı) | Client-side validasyon (email format, password ≥8, şifre eşleşme) |

Not: `lib/api/client.test.ts` yeni dosya değil, mevcut dosyaya test eklenir — "Files to Modify" tablosuna taşınmalı (yazım hatası, aşağıda düzeltiliyor).

### Düzeltilmiş dosya listesi (net)
**Modify:** `frontend/app/giris/page.tsx`, `frontend/app/giris/page.test.tsx`, `frontend/lib/api/client.ts`, `frontend/lib/api/client.test.ts`, `frontend/lib/auth/should-redirect.ts`, `frontend/lib/auth/should-redirect.test.ts`, `frontend/messages/tr.json`, `frontend/messages/tr.test.ts`
**New:** `frontend/app/kayit/{page.tsx,page.test.tsx}`, `frontend/app/e-posta-dogrula/{page.tsx,page.test.tsx}`, `frontend/app/sifre-unuttum/{page.tsx,page.test.tsx}`, `frontend/app/sifre-sifirla/{page.tsx,page.test.tsx}`

## Dependencies
- `apiFetch` (lib/api/client.ts) — genel HTTP katmanı, değişmeden kullanılır; yeni auth fonksiyonları bunun üstüne ince sarmalayıcı olur (bkz. `fetchMe`/`useLogout` deseni: `lib/session/fetch-me.ts:40`, `lib/session/use-session.ts:118`).
- `ApiError`/`NetworkError` (lib/api/errors.ts) — DEĞİŞMEZ; `error.status`/`error.code` üzerinden switch edilecek (423→ACCOUNT_LOCKED, 410→TOKEN_EXPIRED, 400→INVALID_TOKEN gibi kodlar backend body'sinden zaten geliyor, yeni error sınıfı gerekmiyor).
- `useSession`/`SESSION_QUERY_KEY` (lib/session/use-session.ts) — login başarılı olduğunda `queryClient.invalidateQueries(SESSION_QUERY_KEY)` ile senkronize edilmeli (mevcut `useLogout`'un `queryClient.clear()` deseniyle simetrik).
- `buildLoginUrl` (lib/auth/should-redirect.ts:9) — login/register/reset sonrası `/giris`'e dönüşte tekrar kullanılabilir (open-redirect'siz, AC-S5 ile tutarlı).
- `Button` (components/ui/button.tsx) — mevcut basit buton; **shadcn/ui değil**, düz Tailwind. Aşağıdaki Open Question #1 buna bağlı.
- `ErrorBanner` (components/error-banner.tsx) — form-üstü genel hata göstermek için (network/429/423 gibi alan-bağımsız hatalarda) tekrar kullanılabilir.

## Migration Required?
Hayır — bu görev yalnız frontend, hiçbir DB şeması değişmiyor.

## Risks
(atdd.md'den taşındı + netleşen)
- Backend'de `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password` uçları henüz implemente değil (grep ile doğrulandı: `backend/app/schemas/auth.py` sadece `RegisterRequest`/`LoginRequest` içeriyor) — testler `apiFetch`'i mock'layacağı için engel değil, ama bu üç sayfa gerçek backend'e karşı manuel doğrulanamayacak (yalnız kod/test seviyesinde).
- `should-redirect.ts` değişikliği auth mantığına dokunuyor → onay gerekli (aşağıda Open Question #2 olarak da soruluyor, netlik için).
- `giris/page.test.tsx`'in TAMAMI mevcut "form YOK" testleriyle çelişecek (AC-6 orijinal testleri: `<form> YOK`, `<input> YOK`, `<button type=submit> YOK`) — bu testler test-copilot aşamasında KASITLI olarak silinip yerine gerçek form testleri yazılacak; red-team'e bu kasıtlı silme not düşülmeli (davranış değişikliği, regresyon değil).

## Open Questions — KARARA BAĞLANDI (kullanıcı onayı alındı)

**1. Form kütüphanesi seçimi → KARAR: (a) Kurala uy — RHF + Zod + shadcn/ui eklenir.**
`.claude/rules/frontend.md` uygulanacak. Eklenecek bağımlılıklar: `react-hook-form`, `zod`, `@hookform/resolvers`, ve shadcn/ui temel primitifleri (`@radix-ui/react-label`, `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `tailwind-merge`).

**1b. [Test-copilot sırasında ortaya çıktı, kullanıcı onayladı] `@testing-library/user-event` devDependency eklenir.**
Haiku alt-ajanlarının yazdığı `giris/page.test.tsx` ve `kayit/page.test.tsx` bu paketi 20 yerde kullanıyor (kurulu değildi). `package.json`'a `devDependencies` altına eklenecek. Bu, `package.json`'ı "Files to Modify"e ekler ve şu yeni dosyaları gerektirir:
  - `frontend/lib/utils.ts` (shadcn `cn()` helper)
  - `frontend/components/ui/input.tsx`, `frontend/components/ui/label.tsx`, `frontend/components/ui/form.tsx` (shadcn form primitifleri, RHF `Controller` ile)
  - `frontend/lib/auth/schemas.ts` — Zod şemaları: `registerSchema` (email, password min 8, full_name), `loginSchema`, `forgotPasswordSchema`, `resetPasswordSchema` (new_password min 8 + tekrar alanı `refine` ile eşleşme kontrolü)
  Mevcut `components/ui/button.tsx` (düz Tailwind) korunur, shadcn'e taşınmaz (bu görevin kapsamı değil — sadece forma özgü primitifler eklenir).

**2. `should-redirect.ts` → KARAR: Evet, ekle.**
`isPublicRoute`'a `/kayit`, `/e-posta-dogrula`, `/sifre-unuttum`, `/sifre-sifirla` eklenecek — `/giris` ile birebir aynı desen (`pathname === X || pathname.startsWith(X + "/")`).

**3. Giriş sonrası varsayılan yönlendirme hedefi.**
atdd.md'de varsayım: `next` yoksa `/`. middleware.ts/should-redirect.ts'de ayrı bir `/panel` sabiti yok — bu varsayım doğrulandı (kod okunarak), ek onay gerekmiyor.

### Güncellenmiş dosya listesi (kararlar sonrası final)
**Modify:** `frontend/package.json`, `frontend/app/giris/page.tsx`, `frontend/app/giris/page.test.tsx`, `frontend/lib/api/client.ts`, `frontend/lib/api/client.test.ts`, `frontend/lib/auth/should-redirect.ts`, `frontend/lib/auth/should-redirect.test.ts`, `frontend/messages/tr.json`, `frontend/messages/tr.test.ts`
**New:** `frontend/lib/utils.ts`, `frontend/components/ui/{input,label,form}.tsx`, `frontend/lib/auth/schemas.ts` (+ `schemas.test.ts`), `frontend/app/kayit/{page.tsx,page.test.tsx}`, `frontend/app/e-posta-dogrula/{page.tsx,page.test.tsx}`, `frontend/app/sifre-unuttum/{page.tsx,page.test.tsx}`, `frontend/app/sifre-sifirla/{page.tsx,page.test.tsx}`
