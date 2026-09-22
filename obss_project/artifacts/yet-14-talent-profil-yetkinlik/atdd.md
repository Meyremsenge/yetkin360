---
task_slug: yet-14-talent-profil-yetkinlik
jira_id: YET-14
saga_task_id: null
priority: high
threat_model: done
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 55
  integration: 40
  e2e: 0
affected_modules:
  - frontend/app/profil/ (yeni)
  - frontend/lib/api/client.ts (updateTalentProfile, getMySkills, addSkill, removeSkill, listSkills eklenir)
  - frontend/lib/session/types.ts (MeResponse.talent_profile'a somut alan tipi eklenir — şu an Record<string, unknown>)
  - frontend/components/app-shell.tsx (İLK KEZ gerçek bir sayfada kullanılır)
  - frontend/messages/tr.json (yeni UI metinleri)
---

# ATDD — yet-14-talent-profil-yetkinlik

## Jira Kaynağı
[YET-14 — Frontend: talent profil + yetkinlik beyanı ekranı](https://kuyusuzyusuf123.atlassian.net/browse/YET-14)
User Story (Jira'dan birebir): "As a talent I want a profile screen where I can declare my skills So that my claims are visible to others before any evidence or attestation is attached"
Not (Jira açıklamasından birebir): "PLAN.md Faz 1, madde 1.14. Owner: frontend. Bağımlılık (sözleşme önce kuralı): 1.7/1.11'in API sözleşmesi."

## Persona
TALENT rolündeki kullanıcı (öğrenci/genç profesyonel). Kurumsal/koordinatör kullanıcı bu ekrana erişmeye çalışırsa kendi talent profili olmadığı için 404 alır (Sonnet 5 low alt-ajanı tarafından yanıtlandı: backend zaten "kayıtta users+talent_profiles birlikte açılır" dediği için her user'ın bir talent_profile'ı var, ama rol ayrımı ürün kararı olarak netleşmemiş — bu Unknowns'a taşındı).

## Hedef (Neden)
Ürünün "beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirinin İLK halkası: kullanıcı kanıt/tanıklık eklenmeden önce en azından kendi beyanını (profil + yetkinlik listesi) görünür kılabilsin.

## User Story
As a talent
I want a profile screen where I can declare my skills
So that my claims are visible to others before any evidence or attestation is attached

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `/profil` sayfası (AppShell içinde, korumalı rota), When kullanıcı sayfayı açar, Then mevcut profil bilgileri (`headline`, `department`, `study_year`, `city`, `visibility`, `public_slug`) `GET /me`'den (`fetch-me.ts`) gelen `talent_profile` ile önceden doldurulmuş gösterilir.
2. [Critical] Given profil formu, When kullanıcı alanları düzenleyip kaydeder, Then `PATCH /talents/me` çağrılır, 200 dönerse form güncel veriyle senkronlanır ve başarı mesajı gösterilir.
3. [High] Given profil formu, When `public_slug` zaten başka biri tarafından kullanılıyorsa (409 SLUG_TAKEN), Then hata `public_slug` alanının ALTINDA gösterilir, diğer alanlar etkilenmez.
4. [Critical] Given `/profil` sayfasındaki yetkinlik bölümü, When sayfa açılır, Then `GET /talents/me/skills` ile mevcut yetkinlikler listelenir (`skill.name_tr`, `claimed_level`).
5. [Critical] Given yetkinlik ekleme formu, When kullanıcı `GET /skills` taksonomisinden bir skill arayıp seçer ve opsiyonel `claimed_level` ile "ekle"ye basar, Then `POST /talents/me/skills` çağrılır, 201 dönerse liste `refetch`/invalidate edilerek güncellenir (optimistic update YOK).
6. [High] Given yetkinlik ekleme formu, When kullanıcı zaten sahip olduğu bir skill'i eklemeye çalışırsa, Then dropdown/arama sonucunda bu skill ZATEN filtrelenmiş olarak GÖRÜNMEZ (proaktif); backend yine de 409 ALREADY_CLAIMED dönerse (senkronizasyon farkı — örn. iki sekme) genel bir "zaten eklediniz" mesajı gösterilir (reaktif yedek).
7. [Medium] Given yetkinlik ekleme formu, When seçilen skill backend'de artık yoksa (404 SKILL_NOT_FOUND — taksonomi güncelliğini yitirmiş), Then taksonomi listesi yeniden çekilir ve kullanıcıya "bu yetkinlik artık mevcut değil, listeyi yeniledik" bilgi mesajı gösterilir.
8. [Critical] Given yetkinlik listesi, When kullanıcı bir yetkinliğin yanındaki "kaldır" butonuna basar (onay istenmeden, direkt), Then `DELETE /talents/me/skills/{skill_id}` çağrılır, 204 dönerse liste güncellenir (`refetch`/invalidate).
9. [Medium] Given yetkinlik kaldırma, When backend 404 dönerse (zaten silinmiş — senkronizasyon farkı), Then liste zaten güncel kabul edilir, sessiz `refetch` yapılır, kullanıcıya hata gösterilmez (bu satır zaten istenen sonuca ulaşmış sayılır — "hiçbir şey yapılamadı ama hata yok" değil, "istenen zaten gerçekleşmiş" durumu).
10. [High] Given herhangi bir işlem (profil kaydet/skill ekle/skill çıkar), When ağ hatası/timeout oluşursa, Then genel "bağlantı hatası, tekrar deneyin" mesajı gösterilir, buton tekrar aktif olur.
11. [High] Given herhangi bir form/buton, When submit/tıklama sırasında işlem devam ediyorsa, Then buton disabled+loading olur, ikinci tıklama ek istek göndermez.
12. [Medium] Given `GET /me` yanıtı, When `talent_profile` `null`/eksik dönerse (beklenmeyen durum — backend garantisi "her user'ın talent_profile'ı var" ile çelişir), Then sessizce boş form GÖSTERİLMEZ; açık bir "profiliniz yüklenemedi, lütfen destek ile iletişime geçin" hata state'i gösterilir (veri bütünlüğü ihlali gizlenmez).
13. [High] **AC-S1 (arama debounce + XSS hijyeni):** Given yetkinlik arama input'u, When kullanıcı yazmaya devam ederken, Then her tuş vuruşunda AYRI bir `GET /skills` isteği GİTMEZ (en az 300ms debounce); arama sonuçları render edilirken `dangerouslySetInnerHTML` KULLANILMAZ.
14. [High] **AC-S2 (public_slug XSS hijyeni):** Given `public_slug` alanı, When form render edilir/kaydedilir, Then `public_slug` değeri hiçbir yerde `dangerouslySetInnerHTML` ile ham HTML olarak basılmaz (bu alan ileride bir public profil sayfasında render edilecek — XSS'e karşı ilk savunma noktası).
15. [Medium] **AC-S3 (visibility sessizce genişletilmez):** Given profil formu ilk yüklendiğinde, When backend'den gelen `visibility` değeri (`PRIVATE`/`INSTITUTION`/`ORGANIZATIONS`/`PUBLIC`) form state'ine yazılır, Then kullanıcı `visibility` alanına hiç dokunmadan "kaydet"e basarsa, PATCH body'sinde gönderilen `visibility` MEVCUT (backend'den gelen) değerdir — formun boş/varsayılan bir state'i değil, asla daha açık bir görünürlüğe (örn. otomatik `PUBLIC`) sessizce düşmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Profil düzenleme happy path | 200 güncel profil | Form state senkronlanır | Başarı mesajı | AC-2 |
| 2 | Profil — SLUG_TAKEN | 409 SLUG_TAKEN | Yok | `public_slug` altında hata | AC-3 |
| 3 | Skill ekleme happy path | 201 | Liste invalidate/refetch | Yeni skill listede görünür | AC-5 |
| 4 | Skill ekleme — zaten sahip | 409 ALREADY_CLAIMED (reaktif yedek; proaktif olarak zaten önlenir) | Yok | "Zaten eklediniz" mesajı | AC-6 |
| 5 | Skill ekleme — taksonomide yok | 404 SKILL_NOT_FOUND | Taksonomi yeniden çekilir | "Artık mevcut değil, liste yenilendi" | AC-7 |
| 6 | Skill çıkarma happy path | 204 | Liste invalidate/refetch | Skill listeden kaybolur | AC-8 |
| 7 | Skill çıkarma — zaten yok | 404 | Sessiz refetch | Hata gösterilmez (zaten istenen durumda) | AC-9 |
| 8 | Ağ hatası (herhangi bir işlem) | — (fetch reddi) | Buton tekrar aktif | "Bağlantı hatası, tekrar deneyin" | AC-10 |
| 9 | `GET /me` — `talent_profile` null/eksik | 200 ama `talent_profile: null` | Form render edilmez | Açık hata state'i (destek mesajı) | AC-12 |

Kısmi başarı: Bu görevde tek bir atomik işlem içinde kısmi başarı oluşmaz (profil kaydetme ve skill ekleme/çıkarma birbirinden bağımsız, ayrı istekler) — ama "profil kaydedildi, skill listesi o an yüklenemedi" gibi bir sayfa-seviyesi kısmi durum mümkün: bu durumda profil formu kendi başarı mesajını gösterir, skill listesi kendi bağımsız hata state'ini gösterir (ikisi birbirini maskelemez, TanStack Query'nin ayrı query key'leri sayesinde).
Hiçbir şey yapılamadı ama hata da yok: Çift submit UI seviyesinde engellenir (AC-11) — ikinci tıklama hiçbir isteği TETİKLEMEZ, dolayısıyla "sessiz başarı" senaryosu oluşmaz.
Boş sonuç ↔ hata ayrımı: `GET /talents/me/skills` boş `items: []` dönerse ("henüz yetkinlik eklemediniz" boş durumu) ile ağ hatası/500 (hata state'i) UI'da AÇIKÇA farklı gösterilir — aynı "boş liste" görünümü kullanılmaz.

## Test Strategy
Unit: 55% — form validasyon (public_slug format kontrolü varsa client-side), debounce fonksiyonu, hata kodu → mesaj eşleme, proaktif skill filtreleme mantığı.
Integration: 40% — `/profil` sayfası + mock `apiFetch` ile happy path + her hata kodu (409/404/network) senaryosu, TanStack Query invalidate davranışı, AppShell içinde render.
E2E: 0% — YET-12/13 ile tutarlı, bu pipeline'da e2e yok.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Skill'lerin liste/chip gösterimi ve form hata mesajlarının `aria-live` ile duyurulması `verify` adımında gerekirse `vision-test` ile kontrol edilir. Kesin bir "chip" tasarım kısıtı bağlamda verilmedi — Assumptions'a taşındı.
Diğer ölçülebilir kriterler: `npm run lint && npm run typecheck` zorunlu.

## Kapsam Dışı
- `GET /talents/me/signals` (kanıt dökümü, "neden STRONG?" gösterimi) — ayrı bir görev.
- `GET /talents/{id}` (başkasının profilini görüntüleme, visibility budaması) — ayrı bir görev.
- Skill taksonomisine yeni skill önerme akışı (serbest metin skill oluşturma ucu zaten yok).
- Backend'in kendi yetkilendirme/authz testleri (bu görev sadece frontend; backend'in `TALENT` scope kontrolü zaten kendi test paketinde kapsanıyor varsayılır).

## Etkilenen Dosyalar/Modüller (bilinen)
- Yeni: `frontend/app/profil/page.tsx` + form component(ler)i + testler
- Değişen: `frontend/lib/api/client.ts` — `updateTalentProfile`, `listSkills`, `getMySkills`, `addSkill`, `removeSkill` eklenir (mevcut `apiFetch` üstüne, `fetchMe` zaten `lib/session/fetch-me.ts`'te var, GET /me için YENİDEN yazılmaz)
- Değişen: `frontend/lib/session/types.ts` — `MeResponse.talent_profile` şu an `Record<string, unknown> | null` (gevşek, OpenAPI şeması yok notu) — bu görevde somut alanlarla (`headline`, `department`, `study_year`, `city`, `visibility`, `public_slug`) güçlendirilebilir (opsiyonel, plan aşamasında karar verilecek)
- Değişen: `frontend/components/app-shell.tsx` — İLK KEZ gerçek bir sayfada (`/profil`) kullanılacak (YET-12 red-team'inin bulduğu "AppShell hiçbir sayfada kullanılmıyor" bulgusu burada kapanıyor)
- Değişen: `frontend/messages/tr.json` — yeni UI metinleri

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı: git reposunun kökü proje klasörüyle aynı (önceki YET-13 oturumunda doğrulanmıştı), devasa/harici bir geçmiş yok.

## Rollback Beklentisi
Skill ekleme/çıkarma optimistic update KULLANMIYOR (TanStack Query invalidate/refetch modeli) — bu yüzden backend hatası durumunda "eski hale dönme" (rollback) ihtiyacı yok, UI zaten sunucudaki gerçek duruma göre yeniden çizilir. Profil formu da başarısız PATCH'te form state'ini kullanıcının girdiği (henüz kaydedilmemiş) değerlerde bırakır — kullanıcı tekrar deneyebilir, veri kaybı olmaz.

## Risks
- Backend'de `/talents/me/skills` (GET/POST/DELETE) ve `/skills` uçları henüz implemente değil (YET-11, başka bir geliştiriciye atanmış, "Yapılacaklar"da) — kullanıcı onayıyla "sözleşme önce" kuralına göre `docs/API.md`'ye göre mock ile ilerleniyor (YET-13'teki aynı desen). Backend bitince ek entegrasyon testi gerekmeyecek.
- `MeResponse.talent_profile`'ın gevşek tipi (`Record<string, unknown>`) — bu görev somut alanlara ihtiyaç duyuyor, tip güçlendirmesi `plan` aşamasında netleştirilecek.
- Kabul edilen risk: Frontend, skill ekleme/çıkarma çağrılarında hiçbir `user_id`/`talent_id` parametresi göndermiyor (tüm uçlar `/me` altında, backend session'dan kimliği çıkarıyor) — bu tasarımsal olarak IDOR riskini ortadan kaldırıyor, ayrı bir AC-S gerektirmiyor (kod incelemesiyle doğrulanacak, backend'in kendi authz'ı zaten bu sınırı çiziyor).

## Assumptions
- Route adı `/profil` (mevcut Türkçe route konvansiyonuyla tutarlı: `/giris`, `/kayit`, `/sifre-unuttum`).
- Skill'lerin listede "chip"/etiket olarak gösterilmesi — kesin bir tasarım kısıtı verilmedi, en basit/erişilebilir gösterim (liste öğesi + kaldır butonu) `code-copilot` aşamasında tercih edilebilir.
- Kurumsal/koordinatör kullanıcının bu sayfaya erişimi konusunda net bir ürün kararı yok — Unknowns'a taşındı, backend zaten her user için talent_profile açtığından pratikte bu senaryo nadiren oluşur.

## Unknowns
- Kurumsal/koordinatör rolündeki bir kullanıcı `/profil`'e giderse tam olarak ne görmeli (kendi boş talent_profile'ı mı, yoksa bir uyarı mı)? Şu anki varsayım: backend her user için talent_profile açtığından normal akış çalışır, ayrı bir dal gerekmez.
- `public_slug` için client-side format validasyonu (backend'in beklediği karakter seti) — backend şemasından netleşmedi, `plan` aşamasında kontrol edilecek.

## Sorular ve Cevaplar (ham kayıt)
1-18: Sonnet 5 low alt-ajanı tarafından yanıtlandı (persona, happy path akışları, edge case'ler, optimistic-update kararı — YOK, TanStack invalidate tercih edildi, test stratejisi, kapsam dışı, coverage, bağımlılıklar, rollback, kabul kriteri sahibi) — tam gerekçeler subagent raporunda, atdd.md'ye özetlenerek işlendi.
19 (threat-model, 5b adımı): Tetikleyici VAR (kimlik doğrulanmış kullanıcı verisi, kullanıcı girdisi, yeni HTTP çağrıları) → threat-model skill'i çağrıldı, AC-S1..AC-S3 üretildi ve yukarıdaki AC listesine gömüldü.
- Bu oturumda doğrudan kod okunarak (subagent'a değil) doğrulandı: `lib/session/fetch-me.ts`/`types.ts`'te GET /me zaten var (`fetchMe`, yeniden yazılmayacak); `lib/api/client.ts`'te henüz talent/skill fonksiyonu YOK; backend `visibility` enum'u gerçekte 4 değerli (`PRIVATE/INSTITUTION/ORGANIZATIONS/PUBLIC`, varsayılan `INSTITUTION`) — subagent'ın varsaydığı PUBLIC/PRIVATE ikilisi YANLIŞTI, düzeltildi.
