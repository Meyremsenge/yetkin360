# Plan — yet-12-frontend-kabuk
_Reference: atdd.md (onaylandı: "devam et"). Proje kökü doğrulandı: `/Users/elifsarahan/Desktop/yetkin360`. Salt-okunur keşif; uygulama dosyalarına dokunulmadı._

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `frontend/app/layout.tsx` | AC-9/AC-1: `<html lang="tr">` zaten var; `Providers` (TanStack Query, client) + `AppShell` ile sarmalanır, `metadata` metinleri `tr.json`'a taşınır. Layout server component kalır. | medium |
| `frontend/app/page.tsx` | AC-9: şu an başlık/slogan/"Başla" **koda gömülü** (kural ihlali). `messages/tr.json`'daki `home.*` anahtarlarından okunmalı. `/` korumalı mı kararı için Open Question Q2. | low |
| `frontend/messages/tr.json` | YET-51: yalnız `home` var. Eklenecek anahtar grupları: `shell`, `session` (oturum sona erdi, yüklenemedi, tekrar dene), `errors` (genel, ağ, zaman aşımı, destek kodu), `notFound`, `giris` (yer tutucu), boş durum metinleri (AC-12). | low |
| `frontend/package.json` | (a) `lint` betiği `eslint app components` → yeni `lib/` ve `middleware.ts` **lint dışında kalıyor**; kapsam genişletilmeli (Q1). (b) Bağımlılıklar **yalnız kullanıcı onayıyla** (U2). (c) Vitest onaylanırsa `test` betiği. | high (bağımlılık) |
| `frontend/package-lock.json` | Bağımlılık eklenirse otomatik değişir. Onay olmadan dokunulmaz. | high |
| `.github/workflows/ci.yml` | **Yalnız Vitest onaylanırsa:** frontend işine `npm test` adımı. CI değişikliği = onay gerektirir (CLAUDE.md). | medium |

`frontend/tailwind.config.ts` içerik glob'u yalnız `app/**` ve `components/**` tarıyor → `className` içeren her bileşen bu iki dizinde durmalı; `lib/` yalnız mantık (JSX/className yok). Bu yüzden config değişmez.

## New Files
| File | Purpose |
|------|---------|
| `frontend/middleware.ts` | YET-53/AC-2: `matcher` + `shouldRedirect` çağrısı, `307 → /giris?next=`. Edge runtime — Node API yok. |
| `frontend/lib/auth/should-redirect.ts` | Saf karar fonksiyonu: `(pathname, cookies) → yönlendirme hedefi \| null`. İpucu: `access_token` VEYA `csrf_token` varlığı. Public allowlist (Q2). |
| `frontend/lib/auth/sanitize-next.ts` | AC-S3: `next` yalnız tek-`/` göreli yol; aksi `/`. |
| `frontend/lib/api/errors.ts` | `ApiError{code,message,request_id}`, `NetworkError`, `parseApiError` (`docs/API.md` §1.4). |
| `frontend/lib/api/client.ts` | Tek `fetch` sarmalayıcı: `credentials:"include"`, yazmada `X-CSRF-Token` (cookie'den), 10 sn `AbortController`, 401 → **single-flight** `/auth/refresh` → tek tekrar (AC-3/S2/S6). `Authorization` yok, token saklanmaz. |
| `frontend/lib/session/types.ts` | `/me` cevabı tipi (`docs/API.md` §2.2) + tip koruyucu `isMeResponse` (AC-7). |
| `frontend/lib/session/fetch-me.ts` | `/me` çağrısı; mock/gerçek ayrımı **yalnız bu dosyanın gövdesinde** (Q4). |
| `frontend/lib/session/use-session.ts` | `["session"]` sorgu anahtarı, retry politikası (GET ≤ 2, üstel), logout ve cache temizliği (AC-4/5/8/S5). |
| `frontend/components/providers.tsx` | `"use client"`: `QueryClientProvider`. |
| `frontend/components/app-shell.tsx` | Header/gövde iskeleti, `aria-busy` yükleme, boş durum (AC-1/12). |
| `frontend/components/error-banner.tsx` | `role="alert"`, "Tekrar dene", varsa "Destek kodu" (AC-5/7/S4). |
| `frontend/app/error.tsx` | YET-54/AC-6: segment sınırı, `reset`, odak başlığa. Ham `error.message` **gösterilmez** (AC-S4). |
| `frontend/app/global-error.tsx` | Root layout çökerse; kendi `html/body`'si, `tr.json`'a bağımlı olmayan asgari Türkçe metin. |
| `frontend/app/not-found.tsx` | AC-6: 404 + ana sayfa/giriş bağlantısı. |
| `frontend/app/giris/page.tsx` | **Yalnız yer tutucu** (yönlendirme hedefi kırık olmasın); form yok (1.13). `?neden=oturum-bitti` mesajı `aria-live`. |
| `frontend/vitest.config.ts`, `frontend/lib/**/*.test.ts`, `frontend/components/*.test.tsx` | **Yalnız U2 onaylanırsa.** Onaysızsa yazılmaz, "bilinen boşluk" raporlanır. |

Web UI dosyaları (`.tsx`, sayfa bileşenleri) içerdiği için **`verify` gate 11 (`vision-test`) N/A değil, aktif çalışacak**; ekran görüntüsü için `frontend-audit`/Playwright araçları gerekir (kurulu değil, U7).

## Dependencies
- Sözleşme: `docs/API.md` §1.4 (hata gövdesi), §1.5 (kodlar), §1.7 (cookie/CSRF), §2.1 (`/auth/login|refresh|logout`), §2.2 (`/me`).
- Backend: `backend/app/api/auth.py` — cookie'ler `access_token` (path `/`, 15 dk), `refresh_token` (path `/auth/refresh`), `csrf_token` (path `/`, JS okur); `/auth/logout` `X-CSRF-Token` ister; `backend/app/main.py` CORS `allow_credentials=True`, origin `ALLOWED_ORIGINS`.
- Env: `NEXT_PUBLIC_API_BASE_URL` (`docs/ENV.md` §Frontend, varsayılan `http://localhost:8000/api/v1`). Taban yol uyuşmazlığı U1.
- Kütüphane: `@tanstack/react-query` v5 (React 19 destekli) — **onay bekliyor**. Mevcut: Next 15.5, React 19.0, Tailwind 3.4, TS 5.7 strict.
- Kurallar: `.claude/rules/frontend.md` (Redux yok, localStorage yok, `dangerouslySetInnerHTML` yasak, TR metin `tr.json`'dan, erişilebilirlik).
- CI (`.github/workflows/ci.yml` frontend): `npm ci` → `lint` → `typecheck` → `build`. Bu üçü yeşil kalmalı.

## Migration Required?
**Hayır.** Yalnız frontend; veritabanı/şema değişikliği yok.

## Risks
- `lint` betiği yeni dizinleri kapsamıyor → mantık dosyaları sessizce lint'siz kalır (Q1).
- `frontend/node_modules` yok → doğrulama için önce mevcut lockfile'dan `npm ci` gerekir (yeni bağımlılık değil ama ağ erişimi ister).
- Middleware yalnız ipucu (atdd Risks); `/me` gerçek olmadan mock'a dayanıyor → sözleşme kayması riski tek dosyaya (`fetch-me.ts`) hapsedilir.
- Refresh single-flight hatalıysa paralel refresh **token ailesini iptal eder** (`docs/API.md` §1.7) → en yüksek riskli mantık, birim testi zorunlu (AC-S6). Test altyapısı onaylanmazsa bu mantık otomatik test edilemez.
- CSP/güvenlik başlıkları kapsam dışı (PLAN 3.12/3.14).

## Open Questions
**Kullanıcı kararı gerekli (alt-ajana SORULMAZ — onay/yetki meselesi):**
- **U1** API taban yolu: `/api/v1` mi, prefix'siz mi? (docs ↔ backend uyuşmazlığı)
- **U2** Bağımlılık onayı: `@tanstack/react-query`; test için `vitest` + `@testing-library/react` + `jsdom`. Onaylanırsa CI'a `npm test` eklemek de ayrıca onay ister.
- **U3** `/me` şeklinin `@be1` ile teyidi (kullanıcı iletir).
- **Q5** `.claude/rules/frontend.md` "API tipleri OpenAPI'den üretilir, elle yazılmaz" der; `/me` backend'de yok, üretilecek şema yok. `lib/session/types.ts` ve `lib/api/errors.ts`'i **geçici elle yazılmış tipler** olarak yazmak kurala aykırı bir sapmadır — onay/karar gerekli (sessiz sapma yok).

**Teknik, varsayılan seçilebilir (Sonnet alt-ajanına soruldu):**
- **Q1** `lint` kapsamı: `eslint app components` → `lib` ve `middleware.ts`'i de kapsasın mı, yoksa mantık `app/` altına mı konsun?
- **Q2** Hangi rotalar public? Şu an yalnız `/` (açılış) var. Middleware "varsayılan korumalı + public allowlist" mi, "varsayılan public + korumalı liste" mi? `/` açılış sayfası korumalı olursa yok olur.
- **Q3** Kod yerleşimi: `frontend/lib/*` + `frontend/components/*` uygun mu (tailwind glob'u `lib`'i taramıyor)?
- **Q4** `/me` mock'u nasıl etkinleşecek: dev'de sabit fixture mı, env bayrağı mı (yeni env değişkeni `.env.example` güncellemesi gerektirir)?

## Kararlar
_(Sonnet 5 alt-ajanı tarafından yanıtlandı — kullanıcı kararı DEĞİL; kullanıcı onayı gerektirenler aşağıda "Hâlâ açık" altında.)_

- **Q1 — lint kapsamı:** `lint` betiği `eslint app components lib middleware.ts` olur; mantık `lib/`'de kalır. *(Gerekçe: en kritik mantık — single-flight refresh, `shouldRedirect`, `sanitizeNext` — lint dışında kalırsa sessiz boşluk olur.)* Değişen tek şey `package.json` betik satırı; bağımlılık değişikliği değildir.
- **Q2 — rota politikası:** "Varsayılan korumalı + public allowlist" (fail-closed). Başlangıç allowlist: `/`, `/giris`, `/_next/*`, `favicon`, statik dosyalar. 1.13'te `/kayit` vb. bilinçli eklenir. *(Gerekçe: unutulan yeni ekran korumalı kalır; `/` açılış sayfası kaybolmaz.)*
- **Q3 — yerleşim:** `frontend/lib/*` (yalnız mantık, JSX/className yok) + `frontend/components/*`; `tailwind.config.ts` değişmez. *(Gerekçe: Tailwind glob'u yalnız `app/**` ve `components/**`'i tarar.)* Kural: `lib/`'e className sızmaz.
- **Q4 — mock:** `fetch-me.ts` içinde `NODE_ENV !== "production"` iken sabit fixture, production'da gerçek `GET /me`; yeni env değişkeni yok, `.env.example`/`docs/ENV.md` değişmez. *(Gerekçe: env eklemek onay yükü; ayrım tek dosyada kalır.)*
  - **Ana ajanın eklediği uyarı (alt-ajan cevabında yok):** dev'de fixture her zaman 200 döndüğü için `AC-S1` (sahte cookie → `/giris`), `AC-3/4` (401→refresh) ve `AC-7` (boş gövde) **dev sunucuda elle bile denenemez**. Fixture'ın senaryo seçilebilir olması (ör. `?mock=401|5xx|empty` yalnız dev'de) test edilebilirlik için gereklidir; bu, "yeni env yok" kararıyla çelişmez ama plana ek iş olarak girer. Ayrıca `next build` sonrası fixture'ın production bundle'a sızmadığı kontrol edilmeli.

## Hâlâ açık (kullanıcı kararı — alt-ajan karar veremez)
- **U1** API taban yolu (`/api/v1` mi, prefix'siz mi)
- **U2** `@tanstack/react-query` + (`vitest`, `@testing-library/react`, `jsdom`) bağımlılık onayı; Vitest ise CI'a `npm test` adımı da ayrıca onay
- **U3** `/me` şekli `@be1` ile teyit
- **Q5** "API tipleri OpenAPI'den üretilir" kuralı ↔ geçici elle yazılmış `/me` ve `ApiError` tipleri

## Sonraki adım
`test-copilot` (kırmızı adım) — **U2 çözülmeden başlamaz**: test yazmak için test aracı gerekir. `code-copilot` yalnız kırmızı testler var olduktan sonra.
