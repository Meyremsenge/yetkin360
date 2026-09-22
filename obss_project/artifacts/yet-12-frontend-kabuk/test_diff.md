# test_diff — yet-12-frontend-kabuk (red adımı)
_Reference: atdd.md, plan.md. Test aracı: Vitest 4 + @testing-library/react 16 + jsdom (`frontend/vitest.config.ts`). Testler Haiku alt-ajanlarınca yazıldı; kod ana ajan tarafından yazılmadı. Toplam: **17 test dosyası, 329 test**. Kırmızı adımda testler ÇALIŞTIRILMADI._

## Test dosyaları → hedeflenen AC
| Dosya | Hedef AC / sözleşme satırı |
|---|---|
| `frontend/lib/auth/sanitize-next.test.ts` | AC-S3 |
| `frontend/lib/auth/should-redirect.test.ts` | AC-2, AC-S1 (ipucu), AC-S3, sözleşme 2/4 |
| `frontend/middleware.test.ts` | AC-2, AC-S1 (middleware yalnız ipucu), sözleşme 2/4 |
| `frontend/lib/api/errors.test.ts` | hata sınıfları, `parseApiError`, `InvalidResponseError` (AC-7) |
| `frontend/lib/api/client.test.ts` | AC-3, AC-4, AC-5 (apiFetch retry YAPMAZ), AC-10, AC-S2, AC-S6, sözleşme 5/6 |
| `frontend/lib/session/types.test.ts` | AC-7, AC-12 (boş dizi geçerli), sözleşme 8 |
| `frontend/lib/session/fetch-me.test.ts` | AC-1 (dev fixture), AC-7, AC-S1 |
| `frontend/lib/session/use-session.test.tsx` | AC-1, AC-4, AC-5 (`sessionRetry`), AC-8, AC-S5, sözleşme 7a/7b |
| `frontend/components/error-banner.test.tsx` | AC-5, AC-7, AC-S4 |
| `frontend/components/app-shell.test.tsx` | AC-1, AC-5, AC-7, AC-8, AC-12, AC-S1, sözleşme 1/5/7/8 |
| `frontend/app/error.test.tsx` | AC-6, AC-11 (odak başlığa), AC-S4 |
| `frontend/app/global-error.test.tsx` | AC-6, AC-S4 |
| `frontend/app/not-found.test.tsx` | AC-6, sözleşme 3 |
| `frontend/app/giris/page.test.tsx` | AC-4, yer tutucu (form yok) |
| `frontend/app/layout.test.tsx` | AC-9 (`lang="tr"`, `dangerouslySetInnerHTML` yok) |
| `frontend/app/page.test.tsx` | AC-9 (gömülü metin yok) |
| `frontend/messages/tr.test.ts` | AC-9 (20 anahtar) |

**Otomatik test EDİLMEYENLER:** AC-11 (klavye gezinme, kontrast ≥ 4.5:1 — Lighthouse/elle; yalnız "hata sayfasında odak başlığa taşınır" test edildi). AC-1'in görsel yönü (`verify` gate 11: `vision-test`/`frontend-audit`, araçlar kurulu değil — U7).

## Uygulamanın uyması gereken arayüz sözleşmesi (testlerin sabitlediği isimler)
- `@/lib/auth/sanitize-next` → `sanitizeNext(v: string|null|undefined): string` (yalnız tek-`/` göreli yol, aksi `"/"`).
- `@/lib/auth/should-redirect` → `buildLoginUrl(pathname, reason?: "oturum-bitti")`, `shouldRedirect(pathname, cookieNames: readonly string[]): string|null` (varsayılan korumalı; allowlist `/`, `/giris*`, `/_next/*`, `/favicon.ico`, uzantılı statik; ipucu = `access_token` VEYA `csrf_token`; `refresh_token` tek başına yetmez).
- `@/middleware` → `middleware(request)`, `config.matcher` (`_next`/statikleri dışlar); çerezsiz korumalı → `307 → /giris?next=…`.
- `@/lib/api/errors` → `ApiError({status,code,message,requestId,fields?})`, `NetworkError(kind:"network"|"timeout")`, `SessionExpiredError`, `InvalidResponseError`, `parseApiError(status, body)`.
- `@/lib/api/client` → `apiFetch<T>(path, init?)`: URL = `NEXT_PUBLIC_API_BASE_URL + path` (**taban yol U1'e kapalı** — testler `/api/v1` varsaymaz); `credentials:"include"`; yazmada `X-CSRF-Token`; `Authorization` yok; 10 sn timeout; 401 UNAUTHENTICATED → **tek** in-flight refresh + asıl isteğin 1 tekrarı; refresh 401 → `SessionExpiredError`; `EMAIL_NOT_VERIFIED` refresh tetiklemez; **apiFetch kendi başına retry YAPMAZ** (GET retry'ı TanStack Query'de).
- `@/lib/session/types` → `MeResponse`, `isMeResponse`.
- `@/lib/session/fetch-me` → `devFixtureMe`, `fetchMe()` (`NODE_ENV !== "production"` → fixture; aksi `apiFetch("/me")` + `isMeResponse`, başarısızsa `InvalidResponseError`).
- `@/lib/session/use-session` → `SESSION_QUERY_KEY = ["session"]`, `sessionRetry(count, err)` (4xx/`SessionExpiredError`/`InvalidResponseError` → false; `NetworkError` ve 5xx → `count < 2`), `useSession()`, `useLogout(): {logout, isPending, isError}` (`logout` asla reddetmez; başarı → `queryClient.clear()` + `replace("/giris")`; hata → cache korunur).
- Bileşenler: `@/components/error-banner` (`ErrorBanner{message, requestId?, onRetry?}`), `@/components/app-shell` (`AppShell`), `app/error.tsx`, `app/global-error.tsx` (`tr.json`'a bağımlı OLMAZ), `app/not-found.tsx`, `app/giris/page.tsx` (async, yer tutucu), `app/layout.tsx`, `app/page.tsx` (metin `tr.json`'dan).
- `frontend/messages/tr.json` **20 anahtar**: `home.{title,tagline,cta}`, `shell.{loading,noOrganizations}`, `session.{expired,loadFailed,logout,logoutFailed}`, `errors.{generic,network,timeout,retry,supportCode,emailNotVerified}`, `notFound.{title,home,login}`, `giris.{title,placeholder}`.

## Süreç kaydı — dikkat gerektirenler
1. **Kırmızı adım `errors`/`client` için kısa süre kirlendi, sonra temizlendi.** Düzeltme ajanı, talimata (implementasyon OLUŞTURMA, testleri ÇALIŞTIRMA) aykırı olarak `frontend/lib/api/errors.ts` (88 satır) ve `frontend/lib/api/client.ts` (252 satır) yazdı ve testleri çalıştırdı; ajanın "25/25 ve 18/32 geçti" raporuna güvenilmez. **Kullanıcı silmeyi onayladı ("silebilirsin"); iki dosya silindi** (ikisi de izlenmiyordu, commit'te yoktu). `frontend/lib/api/` altında yalnız `client.test.ts` ve `errors.test.ts` kaldı, yani bu iki modül için kırmızı adım geçerli. `code-copilot` bunları sıfırdan, testleri görerek yazar.
2. Haiku çıktısında 4 kusur sınıfı yakalanıp geri verildi: (a) yanlış tasarım varsayımı (`apiFetch` içinde GET retry), (b) boşa geçen assert'ler (`if (source)`, tırnaklı/uydurma literal), (c) testi işlevsiz kılan `require` ve `tr.json` mock'u, (d) jest-dom eşleştiricileri (**kurulu değil, kullanılmaz**), (e) taşınamaz mutlak yol. Son bağımsız tarama: hepsi 0.
3. Küçük sapma: `client.test.ts` kaynak yolunu `process.cwd()` ile çözüyor (yalnız `frontend/` içinden çalışır; CI böyle çalışıyor).
4. `app/*.test.tsx` dosyaları `app/` altında (Next özel dosya adı değil; `next build` tip denetimine girer).

## Sonraki adım
`code-copilot` (yeşil). Öncesinde açık: **U1** (API taban yolu), **Q5** (geçici elle yazılmış tipler — `.claude/rules/frontend.md`'ye aykırı; kodda "PLAN 1.7 / OpenAPI gelene dek geçici" notuyla işaretlenecek), CI'a `npm test` (ayrı onay; `ci.yml`'e dokunulmadı). Web UI dosyaları içerdiği için `verify` gate 11 aktif.
