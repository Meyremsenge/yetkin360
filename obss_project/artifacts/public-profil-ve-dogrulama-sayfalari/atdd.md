---
task_slug: public-profil-ve-dogrulama-sayfalari
jira_id: YET-112
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 30
  e2e: 0
affected_modules:
  - frontend/lib/auth/should-redirect.ts
  - frontend/app/p/[slug]/page.tsx (yeni)
  - frontend/app/v/[token]/page.tsx (yeni)
  - frontend/lib/api/public.ts (yeni)
  - frontend/messages/tr.json
---

# ATDD — public-profil-ve-dogrulama-sayfalari

## Jira Kaynağı
[YET-112 — [PLAN 3.8] Frontend: public profil /p/[slug] + doğrulama /v/[token]](https://kuyusuzyusuf123.atlassian.net/browse/YET-112)
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.8.\nSahip: @fe"
Tip: Görev · Öncelik: Medium · Durum: Yapılacaklar
Not: Backend zaten tamamlanmış ve production'da (YET-105 `GET /public/talents/{slug}`, YET-106 `GET /public/v/{token}`, ikisi de auth-free). Bu görev sadece frontend.
Saga: bu oturumda Saga MCP sunucusuna bağlanılamadı — `saga_task_id` kaydedilemedi.

## Persona
Kimliği doğrulanmamış (anonim) herhangi bir ziyaretçi — işveren, tanıdık, bir doğrulama linkini tıklayan üçüncü taraf. Hiçbir hesabı yok, giriş yapmıyor.

## Hedef (Neden)
Bir yeteneğin doğrulanmış deneyimini/tanıklığını üçüncü bir tarafın hesap açmadan, sadece bir link ile anında görebilmesi — projenin "beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirinin dışa açılan son halkası.

## User Story
As an anonim ziyaretçi
I want bir yeteneğin public profilini (`/p/[slug]`) veya bir doğrulama linkini (`/v/[token]`) hesap açmadan görüntülemek
So that bu bilgiye link üzerinden anında güvenle erişebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçerli bir `slug`, When `/p/{slug}` ziyaret edilir, Then `GET /public/talents/{slug}` çağrılır, `display_name` başlık olarak ve `verified_experiences` listesi (organization_name_snapshot, role_snapshot, tarih aralığı, claim_type) kart/liste halinde gösterilir — tümü düz metin.
2. [Critical] Given geçerli bir `token`, When `/v/{token}` ziyaret edilir, Then `GET /public/v/{token}` çağrılır, `title`, `talent_name`, `organization_name`+`organization_trust_level`, `institution_name`, tarih aralığı, `verified_at`, `attested_skills` listesi gösterilir.
3. [High] Given var olmayan/geçersiz bir `slug`, When `/p/{slug}` ziyaret edilir, Then backend'in 404 body'sindeki `message` ("Kayıt bulunamadı") gösterilir — private/institution/organizations görünürlüğü ile var-olmayan slug arasında frontend'de de HİÇBİR AYRIM yapılmaz (backend zaten aynı 404'ü döndürüyor, frontend bunu farklı yorumlamaz).
4. [High] Given var olmayan/geçersiz bir `token`, When `/v/{token}` ziyaret edilir, Then aynı şekilde "Kayıt bulunamadı" gösterilir.
5. [High] Given geçerli bir `slug` ama `verified_experiences: []` (boş liste), When `/p/{slug}` ziyaret edilir, Then sayfa 404 DEĞİL 200 render edilir, `display_name` görünür + "henüz doğrulanmış deneyim yok" boş durum mesajı gösterilir.
6. [Critical/AC-S1] Given kimliği doğrulanmamış (cookie'siz) bir ziyaretçi, When `/p/{slug}` veya `/v/{token}` ziyaret edilir, Then middleware bu isteği `/giris`'e YÖNLENDİRMEZ — sayfa doğrudan render edilir. **Bu, mevcut `isPublicRoute()` allowlist'ine `/p/` ve `/v/` eklenmesini gerektiren bir düzeltmedir — düzeltilmeden bu özellik hiç çalışmaz (public olması gereken sayfalar şu an giriş ekranına yönlendiriyor).**
7. [Critical/AC-S2] Given `isPublicRoute()`'a `/p/` ve `/v/` eklendiğinde, When mevcut korumalı `/profil` sayfası (kimliksiz) ziyaret edilir, Then `/profil` HÂLÂ `/giris`'e yönlendirilir — `/p/` öneki kontrolü `/profil`'i YANLIŞLIKLA public yapmaz (prefix kontrolü eğik çizgili olmalı: `pathname.startsWith("/p/")`, `pathname.startsWith("/p")` DEĞİL).
8. [Medium] Given API isteği network hatası (500/timeout) alırsa, When sayfa render edilirken, Then 404'ten AYRI, genel bir hata mesajı gösterilir — spesifik kayıt bilgisi sızdırılmaz.
9. [High] Given `display_name`/`organization_name_snapshot`/`talent_name` gibi kullanıcı kaynaklı metin alanları, When render edilirken, Then `dangerouslySetInnerHTML` KULLANILMAZ, düz metin render edilir.
10. [Medium] Given `/p/[slug]` ve `/v/[token]` sayfaları, When ziyaret edilirken, Then `AppShell` KULLANILMAZ (oturum gerektiren bir kabuk, kimliksiz ziyaretçide hataya/yanlış ekrana yol açar) — kendi minimal, session'sız bir layout kullanılır.

## Threat Model
Çağrıldı — bu görev auth-adjacent bir dosyayı (`should-redirect.ts` middleware mantığı) değiştiriyor ve kişisel veri (yetenek adı, kurum adı, tanıklık bilgisi) gösteriyor, tetikleyici var. STRIDE-lite:
- **Spoofing**: Bu sayfalar kimlik doğrulama içermiyor (kasıtlı, tasarımın parçası) — atlandı.
- **Tampering**: `slug`/`token` URL'den geliyor ama bu API'nin TASARIMI (public link paylaşımı) — backend zaten bunları doğruluyor, frontend sadece geçiriyor. Sızıntı riski yok çünkü backend visibility kontrolünü zaten uyguluyor.
- **Repudiation**: GET-only, state değişmiyor — atlandı.
- **Info disclosure**: İki risk bulundu: (1) `isPublicRoute()`'a eklenecek prefix kontrolü dikkatsizce yazılırsa (`startsWith("/p")` eğik çizgisiz) mevcut KORUMALI `/profil` sayfasını da yanlışlıkla public yapabilir — bu ciddi bir yetkilendirme kaçağı olurdu. → AC-S2 (AC-7). (2) Bu sayfalar için `apiFetch` yerine credentials içermeyen basit `fetch()` kullanılmalı — public bir sayfaya giden istekte oturum çerezinin (varsa) gereksiz yere gönderilmesi önlenir. → AC-9'a bağlı karar (bkz. Assumptions).
- **DoS**: Backend ucunda rate limit yok — bu backend'in kapsamı (YET-105/106'da zaten karara bağlanmış), bu görevde tekrar ele alınmıyor, kabul edilmiş risk.
- **Elevation**: Yok — bu görev yeni bir yetki seviyesi açmıyor, tam tersine var olan bir kapalı kapıyı (middleware yönlendirmesi) açıyor; asıl risk "çok fazla açmak" (AC-S1/AC-S2 bunu kapsıyor).

**En kritik AC-S: AC-S2 (AC-7)** — `isPublicRoute()` güncellemesi `/profil`'i yanlışlıkla public yapmamalı. Bu, `test-copilot`'un mutlaka test etmesi gereken bir regresyon senaryosu.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen UI durumu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — `/p/{slug}` | Render edilmiş sayfa | Yok | Yetenek adı + doğrulanmış deneyim kartları | AC-1 |
| 2 | Happy path — `/v/{token}` | Render edilmiş sayfa | Yok | Doğrulama detayları | AC-2 |
| 3 | `/p/{slug}` geçersiz | 404 UI durumu | Yok | "Kayıt bulunamadı" | AC-3 |
| 4 | `/v/{token}` geçersiz | 404 UI durumu | Yok | "Kayıt bulunamadı" | AC-4 |
| 5 | `/p/{slug}` geçerli, boş liste | 200, boş durum bileşeni | Yok | Ad görünür + "henüz doğrulanmış deneyim yok" | AC-5 |
| 6 | Kimliksiz ziyaretçi erişimi | Middleware yönlendirmez | `isPublicRoute()` güncellemesi | Sayfa doğrudan açılır | AC-6/AC-S1 |
| 7 | `/profil` (korumalı) kimliksiz erişim | Middleware YÖNLENDİRİR | Yok | `/giris`'e yönlendirilir (DEĞİŞMEZ) | AC-7/AC-S2 |
| 8 | API network hatası | Genel hata durumu | Yok | Genel hata mesajı (404'ten ayrı metin) | AC-8 |

Kısmi başarı: **Uygulanmaz** — salt-okunur GET sayfaları, DB'ye yazma yok.
Hiçbir şey yapılamadı ama hata yok: `verified_experiences: []` durumu 200 + boş durum mesajıdır (AC-5), 404 ile karıştırılmaz.
Boş sonuç ↔ hata ayrımı: "Veri yok" (boş liste, 200) ile "kayıt yok" (404) ile "sunucu hatası" (network/500) ÜÇ AYRI UI durumudur — hiçbiri aynı mesajı paylaşmaz.

## Test Strategy
Unit/Component: 70% — `page.tsx` bileşenleri (happy path, 404, boş liste, network hatası render testleri, mevcut `[id]/page.test.tsx` deseniyle).
Integration: 30% — `should-redirect.test.ts`'e YENİ senaryolar: `/p/{slug}` ve `/v/{token}` için `shouldRedirect()` `null` (yönlendirme yok) dönmeli (AC-6); **`/profil` için hâlâ yönlendirme dönmeli** (AC-7, regresyon testi — bu proje kuralı gereği ZORUNLU).
E2E: 0% — proje genelinde frontend görevlerinde e2e kullanılmıyor.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Yok
Memory: Yok
Görsel/UI kriteri: Temel semantik HTML (başlık hiyerarşisi), WCAG AA kontrast. SEO: `generateMetadata` ile sayfa başlığı (paylaşılabilir bir link olduğu için faydalı, ama kritik değil — Medium önemde bir ek, atdd'de Critical değil).
Diğer ölçülebilir kriterler: AC-7 (regresyon testi) mutlaka `pytest`/`vitest` koşusunda yeşil olmalı, commit'e bu test olmadan girilmez.

## Kapsam Dışı
- Paylaşım butonu, OG image/sosyal medya kartı, PDF/yazdırma, analytics/görüntülenme sayacı.
- Profil düzenleme linki (bu sayfa anonim ziyaretçi için, sahibi zaten `/profil`'i kullanıyor).
- Backend'de rate limit/DoS koruması (backend'in kendi kapsamı, zaten karara bağlanmış).
- `apiFetch`'in `BASE_URL` fallback'indeki `/api/v1` tutarsızlığı (bu görevden önce var, muhtemelen `.env.local`'de override ediliyor — bu görevin kapsamı dışı, sadece not düşüldü).

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/lib/auth/should-redirect.ts` — `isPublicRoute()`'a `/p/` ve `/v/` prefix kontrolü eklenir (eğik çizgili, `/profil` ile çakışmayacak şekilde)
- `frontend/lib/auth/should-redirect.test.ts` — AC-6/AC-7 regresyon testleri eklenir
- `frontend/app/p/[slug]/page.tsx` (yeni) — public profil sayfası, AppShell KULLANMAZ
- `frontend/app/v/[token]/page.tsx` (yeni) — doğrulama sayfası, AppShell KULLANMAZ
- `frontend/lib/api/public.ts` (yeni) — `getPublicProfile(slug)`, `getPublicVerification(token)` — basit `fetch()` (credentials yok), `apiFetch` DEĞİL
- `frontend/messages/tr.json` — yeni UI metinleri

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — arama kapsamı `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\yetkin360` ile sınırlı tutulmalı.

## Rollback Beklentisi
Salt-okunur sayfalar — state mutasyonu yok. Hata durumunda kullanıcı sadece 404/genel hata mesajı görür.

## Risks
- `isPublicRoute()` değişikliği YANLIŞ yazılırsa (ör. eğik çizgisiz prefix) ciddi bir yetkilendirme kaçağına (mevcut korumalı sayfaların public olması) yol açabilir — bu yüzden AC-7 regresyon testi ZORUNLU, atlanamaz.
- Backend'in `generateMetadata` ile SEO başlığı üretmesi client component'lerde (mevcut proje deseni tamamen `"use client"`) doğrudan çalışmaz — Next.js'te `generateMetadata` server component'lerde çalışır. Bu görev mevcut client-component deseniyle tutarlı kalacaksa SEO meta tag'i (Medium, Critical değil) atlanabilir ya da ayrı bir server-side `layout.tsx`'te ele alınabilir — plan aşamasında netleşmeli.

## Assumptions
- `apiFetch` yerine basit `fetch()` kullanılması kararı (Sonnet 5 low alt-ajanı tarafından): credentials/CSRF gereksiz karmaşıklık, public uçlar hiç 401 dönmüyor.
- Ortak minimal bir layout (paylaşılan, AppShell'siz) tercih edildi çünkü iki route da aynı "session'sız kabuk" ihtiyacını paylaşıyor — ama tek dosyalık page.tsx içine gömmek de kabul edilebilir minimal alternatif, plan aşamasında kod keşfiyle netleşebilir.

## Unknowns
- SEO meta tag'i (`generateMetadata`) için server/client component mimarisi netleşmedi — plan aşamasında kod keşfiyle çözülmeli (bkz. Risks).

## Sorular ve Cevaplar (ham kayıt)
1. Persona → anonim ziyaretçi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Hedef → doğrulanmış deneyimin hesapsız görülebilmesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path (her iki sayfa) → backend response şemasından birebir (kod okumasıyla teyit edildi).
4. Edge case'ler → 404, yükleniyor, boş liste (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → dolduruldu, middleware regresyon satırı (AC-7) eklendi (orkestratör tarafından, kod keşfinde bulunan kritik tuzak).
6. Başarı ölçütü → WCAG AA temel + SEO (Medium) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → paylaşım/OG image/PDF/analytics (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. **Kritik keşif — isPublicRoute() güncellemesi zorunlu + AppShell kullanılamaz** → orkestratör tarafından kod okumasıyla bulundu, Sonnet 5 low alt-ajanı tarafından teyit edildi ve gerekçelendirildi.
9. Performans/güvenlik → basit fetch() (apiFetch değil), dangerouslySetInnerHTML yasak (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → salt-okunur, state mutasyonu yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → otomatik test (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → 70/30/0, `/profil` regresyon testi zorunlu (Sonnet 5 low alt-ajanı + orkestratör).
13. Threat-model tetikleyici → auth-adjacent dosya + kişisel veri, AC-S1/AC-S2 eklendi (orkestratör tarafından, STRIDE-lite: en kritik bulgu `/profil` prefix çakışma riski).
