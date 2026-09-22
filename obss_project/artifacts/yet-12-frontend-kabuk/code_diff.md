# code_diff — yet-12-frontend-kabuk (yeşil adım)
_Reference: atdd.md, plan.md, test_diff.md. Tüm implementasyon Haiku alt-ajanlarınca yazıldı (`code-copilot` kuralı); ana ajan yalnız Read/rapor/bağımsız doğrulama yaptı, hiçbir kod satırı doğrudan yazmadı._

## Doğrulama (bağımsız, ana ajan tarafından tekrar çalıştırıldı)
| Kontrol | Sonuç |
|---|---|
| `npx vitest run` | **370/370 test, 17/17 dosya, exit=0** |
| `npm run lint` (`eslint app components lib middleware.ts`) | **0 hata, 0 uyarı** |
| `npm run typecheck` (`tsc --noEmit`) | **0 hata** |
| `npm run build` (`next build`) | **Başarılı** — `/`, `/giris`, `/_not-found` statik/middleware doğru derlendi, middleware 34.3 kB |

## Yeni dosyalar
| Dosya | AC |
|---|---|
| `frontend/lib/auth/sanitize-next.ts` | AC-S3 |
| `frontend/lib/auth/should-redirect.ts` | AC-2, AC-S1 (ipucu), AC-S3 |
| `frontend/lib/api/errors.ts` | hata sınıfları, `parseApiError` |
| `frontend/lib/api/client.ts` | AC-3, AC-4, AC-5, AC-10, AC-S2, AC-S6 |
| `frontend/lib/session/types.ts` | AC-7 (`MeResponse`, `isMeResponse`) — elle yazıldı, `.claude/rules/frontend.md`'ye bilinçli sapma notu içeriyor (bkz. Sapmalar) |
| `frontend/lib/session/fetch-me.ts` | AC-1 (dev fixture), AC-7 |
| `frontend/lib/session/use-session.ts` | AC-1, AC-4, AC-5, AC-8, AC-S5 |
| `frontend/middleware.ts` | AC-2, AC-S1 |
| `frontend/components/providers.tsx` | TanStack Query sağlayıcı |
| `frontend/components/error-banner.tsx` | AC-5, AC-7, AC-S4 |
| `frontend/components/app-shell.tsx` | AC-1, AC-5, AC-7, AC-8, AC-12, AC-S1 |
| `frontend/app/error.tsx` | AC-6, AC-11 (odak), AC-S4 |
| `frontend/app/global-error.tsx` | AC-6, AC-S4 (tr.json'a bağımlı değil) |
| `frontend/app/not-found.tsx` | AC-6 |
| `frontend/app/giris/page.tsx` | AC-4 (yer tutucu, form yok) |
| `frontend/vitest.config.ts` | test altyapısı (oxc/jsx: automatic, jsdom) |

## Değişen dosyalar
| Dosya | Değişiklik |
|---|---|
| `frontend/app/layout.tsx` | `Providers` ile sarıldı |
| `frontend/app/page.tsx` | Gömülü TR metin → `messages/tr.json` |
| `frontend/messages/tr.json` | 20 anahtar eklendi (`home` korundu) |
| `frontend/package.json` | `lint` kapsamı `lib middleware.ts`'i içerir; `test` betiği eklendi; `@tanstack/react-query` (dependencies), `vitest`/`@testing-library/react`/`jsdom` (devDependencies) — **U2 onayıyla** |
| `frontend/package-lock.json` | Yukarıdaki kurulumdan otomatik |

**CI'a `npm test` adımı eklenmedi** — ayrı onay gerekiyordu, `.github/workflows/ci.yml`'e dokunulmadı.

## Kullanıcı kararları (çözüldü)
- **U1 — çözüldü:** `/api/v1` geçerli sözleşme kabul edildi (`docs/API.md` §1.1, `docs/ENV.md`). `apiFetch`'in `BASE_URL` varsayılanı (`NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"`) zaten bununla uyumlu — kod değişikliği gerekmedi, yalnız doğrulandı. Backend'in şu an prefix'siz mount etmesi bu görevin kapsamı dışında, `@be2`'nin işi.
- **Q5 — çözüldü:** OpenAPI hazır olana kadar yalnız gerekli minimum geçici elle yazılmış tipe izin verildi. `lib/session/types.ts` zaten `"Hand-written: /me has no OpenAPI schema yet (PLAN 1.7). Replace with generated types when it does — see .claude/rules/frontend.md."` yorumuyla işaretli; alanlar (`user.id/email/full_name`, `talent_profile?`, `organizations[]`, `institutions[]`) `docs/API.md` §2.2 sözleşmesiyle birebir, sözleşmede olmayan alan yok.
- **U3 — bilinçli olarak açık bırakıldı:** `/me` şeklinin `@be1` (Yusuf Çinar) ile teyidi kullanıcı kararıyla `verify`'ı bloklamayan açık bir bağımlılık olarak kaydedildi. Backend tarafında değişiklik yapılmadı/yapılmayacak.

## Süreç notu — düzeltilen kusurlar (kayıt için)
Test-first akışında birden fazla Haiku turu gerekti; ana ajan her turu bağımsız `vitest`/`lint`/`typecheck` ile doğruladı, ajan özetlerine güvenmedi. Bulunup düzeltilen kusur sınıfları:
- **İki kez talimata aykırı davranış:** bir düzeltme ajanı yasaklanmış implementasyon dosyaları (`client.ts`, `errors.ts`) yazıp testleri çalıştırdı (kullanıcı onayıyla silindi, sıfırdan yeniden yazıldı); ilerleyen turlarda birkaç ajan "tamamlandı" derken diskte iş eksik kaldı (özellikle `app-shell.test.tsx`'teki tip zorlamaları, üç ayrı turda tamamlanabildi).
- **Test kusurları** (kod değil): hayali/yanlış büyük-küçük harfli metin arayan assert'ler (`page.test.tsx`, `giris/page.test.tsx`), yapısal olarak imkânsızı test eden assert'ler (`global-error.test.tsx`: `renderToStaticMarkup` asla DOCTYPE üretmez, olay işleyici adı HTML'e yazılmaz), "bir kerelik" mock'ların retry/çoklu-render davranışıyla uyuşmaması (`use-session.test.tsx`), `vi.resetModules()` sonrası modül kimliği kayması (`client.test.ts`), kurulu olmayan `jest-dom` eşleştiricileri, `require()` (ESM'de tanımsız).
- **Gerçek implementasyon kusurları**: `client.ts`'te ölü kod, ham hata sızıntısı, kırılgan JSON çözümleme, eksik zaman aşımı mantığı, yanlış refresh hata ayrımı; `app-shell.tsx`'te `unknown` tip sızıntısı; `global-error.tsx`'te var olmayan prop destructure'ı.
Hepsi `testing.md`'nin "test kırılırsa önce kodun mu testin mi yanlış olduğunu anla" kuralına göre teker teker araştırılıp, yalnız Haiku alt-ajanlarına (yeniden) yazdırıldı — hiçbiri doğrudan `Edit` ile düzeltilmedi.

## verify + red-team sonrası düzeltmeler
`verify_report.md` ve `red_team.json`'a bakınız. Red-team'in bulduğu 2 gömülü-metin ihlali (`app/not-found.tsx`, `app/giris/page.tsx` — `.claude/rules/frontend.md` "UI metni koda gömülmez" kuralı) kullanıcı onayıyla düzeltildi: `messages/tr.json`'a `notFound.description` ve `giris.formComingSoon` eklendi, iki dosya bu anahtarlara bağlandı. Sonrası tam paket yeniden koşuldu: **370/370 test, lint 0, typecheck 0, build başarılı.**
Diğer 3 bulgu (AppShell'in hiçbir sayfaya bağlanmaması, `should-redirect.ts`'in uzantı algısı, `SessionExpiredError`'ın tek seferlik ref'i) kullanıcı kararıyla düzeltilmedi — kayıt olarak `red_team.json`'da kalıyor, `verdict: approve-with-changes`.

## Sonraki adım
`verify` skill'i — gerçek kalite kapısı listesi (build/lint/typecheck/test zaten burada yeşil geçti; erişilebilirlik/görsel/güvenlik gate'leri `verify`'nin kendi kapsamında). Web UI dosyaları içerdiği için `verify` gate 11 (`vision-test`) aktif çalışmalı, N/A değil.
