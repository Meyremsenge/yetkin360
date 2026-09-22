---
task_slug: yet-12-frontend-kabuk
jira_id: YET-12
saga_task_id: null
priority: medium
threat_model: done
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 25
  e2e: 5
affected_modules:
  - frontend/app/layout.tsx
  - frontend/app/error.tsx
  - frontend/app/global-error.tsx
  - frontend/app/not-found.tsx
  - frontend/app/giris/page.tsx
  - frontend/middleware.ts
  - frontend/lib/ (api istemcisi, session hook, parseApiError, shouldRedirect)
  - frontend/messages/tr.json
  - frontend/package.json (yalnız kullanıcı onayıyla — bkz. Unknowns U2)
---

# ATDD — yet-12-frontend-kabuk

## Jira Kaynağı
[YET-12 — [PLAN 1.12] Frontend kabuk: layout, oturum yönetimi, korumalı rota, hata sınırı](https://kuyusuzyusuf123.atlassian.net/browse/YET-12)

> Not: `jira-sync` skill'i repoda yok. Bu bağlam oturumda Atlassian MCP ile (salt-okunur) çekildi; Jira'ya hiçbir şey yazılmadı.

User Story (Jira'dan birebir): "As any user, I want a consistent app shell with session handling and protected routes, So that I only ever see screens I'm authorized to see, and errors don't crash the whole app"

AC (Jira'dan): Jira kaydında Given-When-Then AC yok; açıklama yalnız PLAN.md Faz 1 madde 1.12 (owner: frontend) ve "sözleşme önce" kuralına atıf yapıyor. Aşağıdaki AC'ler bu atdd.md'de türetildi.

Alt görevler (Jira): YET-51 root layout + Türkçe metin dosyası (`messages/tr.json`) entegrasyonu · YET-52 oturum durumu context/hook, httpOnly cookie ile senkron · YET-53 korumalı rota (middleware) — girişsiz erişimde `/giris`'e yönlendirme · YET-54 error boundary + genel hata sayfası.

## Persona
Platformu kullanan herhangi bir kişi (öğrenci/talent, koordinatör, kurum üyesi). Tarayıcıda oturumu httpOnly cookie ile taşıyor; JS token'a erişemiyor.

## Hedef (Neden)
Sonraki tüm frontend ekranlarının (1.13 kayıt/giriş, 1.14 profil, Faz 2-3 ekranları) üzerine oturacağı ortak kabuk: tutarlı layout, tek bir oturum kaynağı, girişsiz kullanıcıyı korumalı ekrandan uzak tutan yönlendirme ve uygulamanın tamamını çökertmeyen hata sınırı. Bu olmadan her ekran oturum ve hata mantığını kendi başına yeniden yazar.

## User Story
As any user
I want a consistent app shell with session handling and protected routes
So that I only ever see screens I'm authorized to see, and errors don't crash the whole app

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. **AC-1** [Critical] Given geçerli bir oturum, When kullanıcı korumalı bir sayfaya gider, Then middleware geçirir, `GET /me` (mock → gerçek) 200 döner, `["session"]` cache'i `docs/API.md` §2.2 şekliyle dolar ve sayfa Türkçe layout içinde render edilir (önce `aria-busy` iskeleti).
2. **AC-2** [Critical] Given ne `access_token` ne `csrf_token` cookie'si var, When korumalı bir yola gidilir, Then middleware `307` ile `/giris?next=<yol>` yönlendirir ve korumalı içerik için hiçbir veri isteği atılmaz.
3. **AC-3** [Critical] Given API bir isteğe `401 UNAUTHENTICATED` döner, When istemci bunu alır, Then tam **1** sessiz `POST /auth/refresh` denenir; aynı anda gelen birden çok 401 **tek bir in-flight refresh promise'ini** paylaşır; başarılıysa (204) asıl istek tam 1 kez tekrarlanır; döngü yoktur.
4. **AC-4** [Critical] Given refresh de `401` döner (veya tekrarlanan istek yine 401), When bu olur, Then `["session"]` ve tüm sorgu cache'i temizlenir, `/giris?next=<mevcut yol>&neden=oturum-bitti` yönlendirmesi yapılır ve "Oturumunuz sona erdi" mesajı `aria-live` ile duyurulur.
5. **AC-5** [High] Given ağ hatası veya 10 sn zaman aşımı, When bir istek başarısız olur, Then oturum silinmez, kullanıcı `/giris`'e atılmaz; cache varsa üstte `role="alert"` bandı + "Tekrar dene" gösterilir, cache yoksa boş sayfa değil hata durumu ekranı çizilir; GET en fazla 2 otomatik retry, yazma isteğinde otomatik retry yok.
6. **AC-6** [High] Given render sırasında beklenmeyen hata / var olmayan rota, When bu olur, Then `error.tsx` (segment, "Tekrar dene"), `global-error.tsx` (root layout çökerse, `messages`'a bağımlı olmayan asgari Türkçe metin, kendi `html/body`'si) ve `not-found.tsx` (404 + ana sayfa/giriş bağlantısı) uygulamayı beyaz ekrana düşürmeden çalışır.
7. **AC-7** [High] Given `/me` 200 döner ama gövde boş/şekilsiz (204 dahil), When tip koruyucu doğrulama başarısız olur, Then sonuç "geçersiz yanıt" sayılır, cache'e yazılmaz, oturum ne açık ne kapalı varsayılır, korumalı içerik gösterilmez ve "Bilgileriniz şu an yüklenemedi" + "Tekrar dene" + destek kodu görünür; `talent_profile` yokluğu geçerli boş durumdur, hata değildir.
8. **AC-8** [High] Given logout başarısız olur (non-2xx/ağ), When kullanıcı çıkış yapmaya çalışır, Then oturum "açık" kabul edilir, "Çıkış tamamlanamadı, lütfen tekrar deneyin" (`role="alert"`) gösterilir ve başarılı çıkış iddiası yapılmaz; logout 2xx dönerse istemci tüm sorgu cache'ini temizleyip `/giris`'e gider.
9. **AC-9** [High] Given root layout, When uygulama açılır, Then `<html lang="tr">` vardır, tüm kullanıcıya görünen metinler `messages/tr.json`'dan gelir (koda gömülmez, YET-51), `dangerouslySetInnerHTML` kullanılmaz.
10. **AC-10** [Medium] Given `401 EMAIL_NOT_VERIFIED`, When API bunu döner, Then refresh denenmez, hata kodu `401 UNAUTHENTICATED`'dan ayrı işlenir ve e-posta doğrulama uyarısı gösterilir (ekranın kendisi 1.13'te).
11. **AC-11** [Medium] Given kabuk ekranları, When klavye ile gezilir, Then tüm akış erişilebilir, focus görünür, kontrast ≥ 4.5:1, hata alanları `aria-live`/`role="alert"`, hata sayfalarında odak başlığa taşınır.
12. **AC-12** [Medium] Given `organizations[]`/`institutions[]` boş, When kabuk render edilir, Then "Henüz bir kuruluşunuz yok" benzeri, ne yapılacağını söyleyen boş durum gösterilir ve hata ile karıştırılmaz.

**Güvenlik kriterleri (threat-model, `AC-S<n>`):**

13. **AC-S1** [Critical] (Spoofing/Elevation) Given tarayıcıda elle set edilmiş sahte `access_token=x` cookie'si, When korumalı yola gidilir, Then en fazla sayfa iskeleti çizilir; `/me` 401 dönünce (refresh de başarısız) `/giris`'e yönlendirilir ve **hiçbir kullanıcı verisi render edilmez**. Middleware güvenlik sınırı değildir; yalnız yönlendirme ipucudur.
14. **AC-S2** [Critical] (Tampering — CSRF/token) Given herhangi bir `POST/PATCH/DELETE`, When istemci gönderir, Then `credentials: "include"` ve `X-CSRF-Token` = `csrf_token` cookie değeri eklenir; `Authorization` başlığı kurulmaz; token `localStorage`/`sessionStorage`/JS değişkenlerinde tutulmaz ve JWT istemcide decode edilmez (birim testi: API istemcisi kodunda bunlar yok).
15. **AC-S3** [Critical] (Tampering — open redirect) Given `/giris?next=<değer>`, When `next` `//evil.com`, `https://evil.com`, `/\evil.com`, `javascript:...` veya tek `/` ile başlamayan herhangi bir şeyse, Then yok sayılır ve `/` kullanılır; yalnız aynı origin'e ait tek-`/`'lı göreli yol kabul edilir.
16. **AC-S4** [Critical] (Info disclosure) Given `new Error("SELECT * FROM users ... stack")` fırlatan bir bileşen, When hata sınırı devreye girer, Then DOM'da `error.message` veya stack **yoktur**; yalnız `tr.json`'daki genel Türkçe metin ve (yalnız `ApiError`'dan geliyorsa) `request_id` "Destek kodu" olarak görünür; loglara PII/gövde yazılmaz.
17. **AC-S5** [High] (Info disclosure — paylaşımlı cihaz) Given logout veya refresh başarısızlığı, When oturum biter, Then TanStack Query cache'i tamamen temizlenir; geri tuşu ile önceki kullanıcının korumalı verisi görünmez.
18. **AC-S6** [High] (DoS/refresh fırtınası) Given aynı anda N adet 401, When refresh tetiklenir, Then `POST /auth/refresh` **tam 1 kez** gider (rotating refresh + yeniden-kullanım tespiti nedeniyle paralel çağrı token ailesini iptal edip kullanıcıyı düşürürdü — `docs/API.md` §1.7); refresh sonucu 401/429/ağ hatasıysa yeniden deneme döngüsü yoktur.

## Agentic Değerlendirme Kriterleri
(Bölüm silindi — görev bir LLM agent davranışını değiştirmiyor.)

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: geçerli oturum, korumalı sayfa | Middleware geçirir; `/me` 200 `{user, talent_profile?, organizations[], institutions[]}` | `["session"]` cache dolar (yalnız okuma) | Kısa `aria-busy` iskeleti, sonra Türkçe layout + sayfa | AC-1, AC-9 |
| 2 | Cookie yok | Middleware `307 → /giris?next=<yol>` | Korumalı veri isteği atılmaz | `/giris` (yer tutucu) | AC-2, AC-S3 |
| 2b | Cookie var ama bozuk/süresi geçmiş | Sayfa açılır, `/me` 401 → 1 refresh → başarısızsa `/giris` | Session cache temizlenir; `next` doğrulanır | `/giris` + "Oturumunuz sona erdi" (aria-live) | AC-3, AC-4, AC-S1 |
| 3 | Var olmayan rota | `not-found.tsx`, HTTP 404 | Yok | "Sayfa bulunamadı" + ana sayfa/giriş bağlantısı | AC-6 |
| 4 | Yetkisiz erişim (girişsiz korumalı sayfa) | Middleware `307 → /giris`; API tarafında `401 UNAUTHENTICATED` (yetkisiz kaynakta backend `404`, istemci not-found gösterir) | Korumalı içerik render edilmez | `/giris`; kaynak varlığı ipucu verilmez | AC-2, AC-S1 |
| 5 | Dış bağımlılık hatası (5xx / fetch throw) | Tipli `ApiError{code,message,request_id}` veya `NetworkError`; GET ≤ 2 retry | Oturum silinmez, yönlendirme yok, PII loglanmaz | `role="alert"` bandı, Türkçe mesaj, "Tekrar dene", varsa "Destek kodu" | AC-5, AC-S4 |
| 6 | Zaman aşımı | `AbortController` 10 sn → `NetworkError(timeout)`; refresh döngüsü tetiklenmez | Bekleyen istek iptal, oturum korunur, yazmada retry yok | "İstek zaman aşımına uğradı. Tekrar deneyin." + düğme | AC-5, AC-S6 |
| 7a | Kısmi: oturum var ama `/me` başarısız | `/me` 5xx/ağ: cache varsa korunur + "veriler güncellenemedi"; yoksa hata ekranı; `/me` 401: 1 refresh sonra `/giris` | Yönlendirme yok (401 hariç) | Eski veri + uyarı bandı veya hata ekranı + "Tekrar dene" | AC-5, AC-3 |
| 7b | Kısmi: logout | Bkz. AC-8 ve Unknowns U5 | Cache temizliği yalnız başarılı logout'ta | "Çıkış tamamlanamadı…" (`role="alert"`) | AC-8, AC-S5 |
| 8 | Hiçbir şey yapılamadı ama hata yok (`/me` 200 ama boş/şekilsiz gövde, 204) | Tip koruyucu başarısız → "geçersiz yanıt"; session "bilinmiyor" | Cache'e yazılmaz; log'a yalnız kod/istek kimliği | "Bilgileriniz şu an yüklenemedi" + "Tekrar dene" + destek kodu | AC-7, AC-12 |

Kısmi başarı: yukarıda 7a/7b. Kural: sunucu durumu doğrudur; istemci "başarılı" iddiasını yalnız sunucu yanıtına (2xx) bağlar.
Hiçbir şey yapılamadı ama hata da yok: satır 8 — sessiz "oturum var" varsayımı YASAK.
Boş sonuç ↔ hata ayrımı: `organizations[]` boş = geçerli boş durum (AC-12); şekilsiz/boş gövde = hata (AC-7); `talent_profile` yok = hata değil.

## Test Strategy
Unit: 70% — saf fonksiyonlar: `shouldRedirect(pathname, cookies)`, `sanitizeNext`, `parseApiError`, `/me` tip koruyucusu, refresh single-flight mantığı, CSRF başlık kurucusu.
Integration: 25% — bileşen + mock fetch: session sağlayıcı/hook, 401→refresh→tekrar akışı, hata sınırı render'ı (AC-S4), logout akışı.
E2E: 5% — Lighthouse (erişilebilirlik) ve elle tarayıcı kontrolü (`/`, `/giris`, 404). Otomatik e2e aracı eklenmez.
**Koşul:** Frontend'de test altyapısı yok; Vitest + React Testing Library + jsdom eklenmesi bağımlılık onayı gerektirir (U2). Onay çıkmazsa asgari yol: kararlar saf fonksiyonlara çıkarılır, doğrulama `npm run lint` + `npm run typecheck` + `next build` + elle kontrol listesi olur ve bu **"bilinen boşluk" olarak raporlanır** (`CLAUDE.md`: frontend mantık → typecheck + bileşen testi).

## Benchmark / Başarı Ölçütü
Coverage Target: kabuk mantığı dosyalarında (`lib/session`, `lib/api`, middleware karar fonksiyonu) satır ≥ 80%, dallanma ≥ 70%; saf görsel bileşenlerde zorunlu hedef yok.
Performance Target: yok.
Görsel/UI kriteri: layout bozulmamalı; hata durumlarında boş beyaz sayfa olmamalı; hata mesajları görünür ve `aria-live` ile duyurulmalı (`verify` adımında `vision-test`/`frontend-audit` ile kontrol edilebilir).
Diğer ölçülebilir kriterler: `npm run lint` ve `npm run typecheck` 0 hata; `next build` başarılı; Lighthouse erişilebilirlik ≥ 95 (`/`, `/giris`, 404) — araç kurulu değilse elle; axe kritik/ciddi ihlal 0; klavye ile tam gezinme.

## Kapsam Dışı
Giriş/kayıt formları ve doğrulama (1.13), e-posta doğrulama ve şifre sıfırlama ekranları, rol bazlı gerçek dashboard'lar ve menü içeriği (yalnız boş iskelet), profil/talent ekranları (1.14+), çoklu dil altyapısı, backend değişikliği, `/me`'nin gerçek backend implementasyonu (PLAN 1.7, `@be1`), CSP/güvenlik başlıkları (bkz. Risks), React Hook Form/Zod/shadcn ek bileşenleri/axios/Redux/Zustand/Playwright. `/giris` için yalnız **yer tutucu sayfa** (yönlendirme hedefi kırık olmasın diye), form yok.

## Etkilenen Dosyalar/Modüller (bilinen)
Mevcut: `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/messages/tr.json`, `frontend/components/ui/button.tsx`. Yeni (öneri, `plan` adımında kesinleşir): `frontend/middleware.ts`, `frontend/app/error.tsx`, `frontend/app/global-error.tsx`, `frontend/app/not-found.tsx`, `frontend/app/giris/page.tsx`, `frontend/lib/*`. Kural: `docs/API.md` §1.4 hata gövdesi, §1.7 cookie/CSRF, §2.1 auth uçları, §2.2 `/me`.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı: git reposunun kökü proje klasörünün kendisi (`/Users/elifsarahan/Desktop/yetkin360`), ~82 dosya, geniş bir üst dizin repo'su değil. Yine de sonraki adımlarda arama `frontend/` ve `docs/` ile sınırlı tutulur; `node_modules`/`.next` taranmaz.

## Rollback Beklentisi
Kalıcı istemci durumu yoktur (localStorage yasak, optimistic update yok) → geri alınacak yerel değişiklik kalmaz. Başarısız logout'ta oturum "açık" kabul edilir, hata gösterilir, kullanıcı yeniden dener. Kod düzeyinde rollback: `feat/1.12-frontend-kabuk` dalı `main`'e merge edilmeden atılabilir.

## Risks
- **Middleware yalnız ipucudur.** `access_token` 15 dk'da düşer, `refresh_token` path'i `/auth/refresh` olduğu için middleware onu görmez; ipucu `access_token` VEYA `csrf_token` (30 gün) varlığıdır. Sonuç: ipucu var ama oturum bitmişse iskelet çizilir, `/me` 401 ile `/giris`'e gidilir. Korumalı veri zaten sunucudan gelmez (AC-S1). Bu bilinçli kabul edilen tasarım.
- `csrf_token` cookie'si oturum bitince de 30 gün kalabilir → "yanlış pozitif" yönlendirme ipucu; zararsız (yukarıdaki akış düzeltir).
- **Kabul edilen risk:** CSP/güvenlik başlıkları 1.12 kapsamında değil; PLAN 3.12 (güvenlik geçişi) ve 3.14 (deploy) maddelerine bırakıldı. Rate limit backend'in sorumluluğu (`docs/SECURITY.md`).
- `/me` gerçek olmadan yazıldığı için sözleşme kayması riski: gerçek uç şekli farklı çıkarsa yalnız tek fetch fonksiyonunun gövdesi değişmeli.
- Refresh single-flight'ta hata olursa kullanıcı sessizce tüm token ailesini kaybedebilir (AC-S6 bunu test eder).

## Assumptions
- `/me` istemcide tek fetch fonksiyonunun arkasında mock'lanır; oturum TanStack Query anahtarı `["session"]` üzerinden okunur. *(Sonnet alt-ajanı)*
- Oturum kaynağı `/me`'dir; login cevabındaki `user_id/role/email_verified` yalnız ilk cache tohumudur. *(Sonnet alt-ajanı)*
- HTTP için yerleşik `fetch` yeterli (axios yok). *(Sonnet alt-ajanı)*
- Rol bilgisi yalnız UX içindir; istemci JWT'yi asla decode etmez, rol kararı `/me`'den gelir.
- `@fe` (Elif Sara) kabul sahibidir; başkasının maddesine (PLAN 1.7) dokunulmaz, sözleşme uyumu sahibinden teyit edilir.

## Unknowns
- **U1 — API taban yolu:** `docs/API.md` §1.1 `/api/v1` diyor, `docs/ENV.md` `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` diyor; ama `backend/app/main.py` router'ı prefix'siz (`/auth/...`) mount ediyor. Hangisi doğru? Tek `NEXT_PUBLIC_API_BASE_URL` sabitiyle soyutlanacak; karar `@be2`/kullanıcıdan gerekli. (CLAUDE.md: sessiz sapma yok.)
- **U2 — Bağımlılık onayı (CLAUDE.md: onay şart):** `@tanstack/react-query` (kural gereği zorunlu) ve test için `vitest` + `@testing-library/react` + `jsdom`. React Hook Form/Zod bu maddede EKLENMEZ (1.13'te).
- **U3 — `/me` sözleşme teyidi:** PLAN 1.7 sahibi `@be1` (Yusuf Çinar) ile `docs/API.md` §2.2 şeklinin yazılı teyidi (CONTRIBUTING: başkasının maddesine dokunmadan haber ver).
- **U4 — Alt-ajan cevabındaki hatalar (düzeltildi, kayıt için):** Soru 10'da kabul sahibi "Elif Sarahan (ürün/proje sahibi)" ve "tek kişilik hackathon ekibi" denmiş; doğrusu 3 kişilik ekip ve `@fe` = Elif Sara. Kabul sahibi kararı kullanıcıya aittir.
- **U5 — Logout kısmi başarı davranışı:** Alt-ajan "logout 204 dönse bile `/me` ile doğrula, hâlâ 200 ise oturumu açık kabul et" önerdi. Bu, JS'in silemediği httpOnly cookie'ler için ek bir doğrulama isteği ve karmaşıklık getiriyor. AC-8'de sade sürüm yazıldı (2xx → temizle + yönlendir; hata → oturum açık + uyarı). Ek `/me` doğrulaması istenip istenmediği onayda netleşmeli.
- **U6 — Mock stratejisi:** `/me` mock'unun nerede/hangi koşulda devreye girdiği (dev'e özel fixture mı, env bayrağı mı) belirsiz; yeni env değişkeni gerekiyorsa `.env.example` güncellemesi gerekir.
- **U7 — Ölçüm araçları:** Lighthouse/axe bu ortamda kurulu değil; erişilebilirlik hedefi elle doğrulanabilir mi, `frontend-audit` (Lighthouse MCP) kullanılabilir mi belirsiz.

## Sorular ve Cevaplar (ham kayıt)
Yanıtlayan: **Sonnet 5 alt-ajanı** (skill 4z adımı; kullanıcı cevabı DEĞİL, bağlam verilerek araç kullanmadan üretildi).
1. Oturum kaynağı → `GET /me` tek fetch fonksiyonu arkasında mock; TanStack Query `["session"]`; login cevabı yalnız ilk tohum. Gerekçe: sözleşme önce kuralı, localStorage yasağı.
2. Middleware → yalnız yönlendirme ipucu (`csrf_token` VEYA `access_token` varlığı); asıl karar `/me` 401. Gerekçe: access_token 15 dk'da düşer, refresh cookie'si middleware'e gelmez.
3. Süresi dolan access token → tek sessiz refresh (eşzamanlı 401'ler tek promise), başarılıysa asıl istek 1 kez tekrar; başarısızsa cache temizle, `/giris?next&neden=oturum-bitti`; 429/ağ hatasında oturum silinmez; `EMAIL_NOT_VERIFIED` ayrı.
4. Hata sınırı → `error.tsx` + `global-error.tsx` + `not-found.tsx`; `request_id` "Destek kodu"; stack/ham mesaj asla.
5. Ölçütler → lint/typecheck 0 hata, build, Lighthouse a11y ≥ 95, axe 0, klavye, kontrast; test aracı onaya sunulur, onaysız asgari yol + "bilinen boşluk".
6. Kapsam dışı → 1.13/1.14 ekranları, rol bazlı içerik, i18n, backend, gerçek `/me`; `/giris` yalnız yer tutucu.
7. Bağımlılık → şart: TanStack Query; test için Vitest+RTL+jsdom (onayla); eklenmez: RHF, Zod, shadcn ek, e2e, Redux/Zustand, axios.
8. Ağ hatası/timeout → oturum silinmez, `/giris`'e atılmaz; cache varsa uyarı bandı, yoksa hata ekranı; GET ≤ 2 retry; yazmada retry yok; optimistic update yok.
9. Test oranı → 70/25/5; coverage kabuk mantığında satır ≥ 80%, dal ≥ 70%.
10. Kabul sahibi → *(alt-ajan "Elif Sarahan / tek kişilik ekip" dedi — hatalı, bkz. U4)*; `/me` sözleşme uyumu backend sahibiyle teyit; taban yol uyuşmazlığı kullanıcıya sorulacak.
Kullanıcı mesajından, tekrar sorulmadı: persona ve hedef (Jira user story), alt görev listesi (Jira), kabul için repo kuralları (`CLAUDE.md`, `.claude/rules/frontend.md`).
