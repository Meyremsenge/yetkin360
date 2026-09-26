---
task_slug: koordinator-dashboard-frontend
jira_id: YET-113
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 85
performance_target: "<500ms (client fetch dahil; backend zaten <200ms garanti ediyor)"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - frontend/app/kurum/[id]/panel/page.tsx (yeni)
  - frontend/lib/api/institutions.ts (yeni)
  - frontend/lib/types/institution.ts (yeni, veya institutions.ts içine gömülü tipler)
  - nav bileşeni (link eklemek için — hangi dosya olduğu netleşmedi, bkz. Unknowns)
---

# ATDD — koordinator-dashboard-frontend

## Jira Kaynağı
[YET-113 — [PLAN 3.9] Frontend: koordinatör dashboard](https://kuyusuzyusuf123.atlassian.net/browse/YET-113)
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.9.\nSahip: @fe"
Tip: Görev · Öncelik: Medium · Durum: Yapılacaklar
Not: Jira issue'sunda ayrı bir Acceptance Criteria alanı yok — kaynak PLAN.md 3.9 satırı ve backend karşılığı `obss_project/artifacts/koordinator-dashboard-ucu/atdd.md` (YET-107, zaten kodlanmış ve merge edilmiş).
Saga: bu oturumda Saga MCP sunucusuna bağlanılamadı (araç listesinde hiç yok, deferred tool aramasında da bulunamadı) — `saga_task_id` kaydedilemedi, ilerleyen bir oturumda `jira-sync`/`saga` skill'i ile senkronize edilmeli.

## Persona
INST_ADMIN veya COORDINATOR rolündeki kurum yetkilisi (üniversite/MYO staj koordinatörü) — backend endpoint'i zaten sadece bu rollere 200 dönüyor; frontend'de görünürlük (nav linki) `/me` çağrısının `institutions` alanı doluysa gösterilir, bu sadece UX kolaylığıdır (bkz. `.claude/rules/frontend.md`: "Rol kontrolü yalnız UX içindir").

## Hedef (Neden)
Backend'de zaten var olan `GET /institutions/{id}/dashboard` ucunun döndürdüğü veriyi (onay bekleyen + değerlendirme bekleyen engagement'lar) kurum koordinatörüne görsel bir panelde göstermek — koordinatörün "hangi stajlar onayımı bekliyor / hangi bitmiş stajın değerlendirmesi hâlâ gelmedi" sorularını tek bakışta cevaplamak (bkz. `koordinator-dashboard-ucu/atdd.md` Hedef bölümü, final-analiz §14).

## User Story
As a kurum koordinatörü (COORDINATOR/INST_ADMIN)
I want kendi kurumumun onay bekleyen ve değerlendirme bekleyen engagement'larını bir panelde görmek
So that Excel yerine bu bilgiyi anlık ve görsel olarak takip edebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış COORDINATOR/INST_ADMIN, kendi kurumunda 3 `PENDING_APPROVAL` ve 7 `PENDING_EVALUATION` engagement varken, When `/kurum/{institution_id}/panel` sayfası açılır, Then sayfa `GET /institutions/{institution_id}/dashboard` çağırır ve iki sayaç kartı (`3`, `7`) + iki liste (başlık + tarih) gösterir.
2. [Critical] Given kurumda hiç bekleyen engagement yoksa (backend `200` + `summary` sıfır + iki liste `[]` döner), When panel açılır, Then hata YOK — her liste için ayrı, tasarlanmış empty-state metni gösterilir ("Onay bekleyen staj yok" / "Değerlendirme bekleyen staj yok"), sayaçlar `0` gösterir.
3. [Critical] Given kullanıcı `/me` çağrısında hiçbir kuruma üye değil (institutions boş), When kullanıcı bu sayfaya doğrudan URL ile gelir, Then sayfa nav'da hiç linklenmez VE backend zaten 404 döneceği için (kullanıcı institution_ids scope'unda değil) frontend bu 404'ü genel "Bu kuruma erişiminiz yok" mesajıyla gösterir — 403 çağrışımlı bir metin kullanılmaz. (AC-S2)
4. [High] Given backend `401` döner (oturum sonlanmış), When panel açılır, Then kullanıcı genel auth-guard davranışıyla `/giris` sayfasına yönlendirilir (mevcut `should-redirect`/oturum-bitti akışı, yeni bir mekanizma eklenmez).
5. [High] Given backend `500`/network hatası (fetch reddi, timeout), When panel açılır, Then TanStack Query `isError` durumunda `aria-live` ile duyurulan bir hata mesajı + "Tekrar dene" butonu gösterilir — sessiz başarısızlık YOK.
6. [Critical] Given kullanıcı URL'deki `institution_id`'yi kendi kurumundan farklı bir değere manuel değiştirirse, When sayfa yeniden render olur, Then TanStack Query cache key'i `institution_id`'yi içerir (`["institution-dashboard", institutionId]`) — önceki kurumun cache'lenmiş verisi yeni institution_id için asla (geçici olarak dahi) ekranda görünmez; backend zaten bu id'yi kendi scope'unda değilse 404 döner ve o durumda hiçbir veri render edilmez. (AC-S1)
7. [Medium] Given `pending_approval`/`pending_evaluation` listelerindeki `title` alanı kullanıcı tarafından girilmiş serbest metin içerebilir (engagement başlığı), When liste render edilir, Then React'in varsayılan escape'i kullanılır, `dangerouslySetInnerHTML` KULLANILMAZ — XSS riski React'in kendi davranışıyla kapatılır, ekstra sanitizasyon gerekmez.

## Threat Model
Çağrıldı — STRIDE-lite uygulandı (`threat-model` skill'i ile), AC-S1/AC-S2 yukarıdaki Acceptance Criteria'ya eklendi.

- **Spoofing**: Mevcut httpOnly cookie oturumu kullanılıyor, yeni bir kimlik doğrulama mekanizması eklenmiyor — atlandı.
- **Tampering**: En gerçek risk burada — `institution_id` URL path parametresinden gelir, kullanıcı tarafından serbestçe değiştirilebilir. Backend zaten bu id'yi `principal.institution_ids` ile karşılaştırıp 404 döner (bkz. `koordinator-dashboard-ucu`), ama **frontend'in kendi hatası** olası: TanStack Query cache key'i institution_id'yi içermezse (ör. sabit `["dashboard"]` key kullanılırsa), kurum A'nın panelinden kurum B'nin URL'ine geçildiğinde React, yeni fetch tamamlanana kadar A'nın cache'lenmiş verisini B'nin sayfasında gösterebilir — bu bir cross-tenant veri sızıntısı olur (sunucu değil, istemci kaynaklı). → AC-S1.
- **Repudiation**: GET-only, state değişmiyor — atlandı.
- **Info disclosure**: 404 mesajı "kurum var ama yetkin yok" ile "kurum hiç yok" arasında ayrım yapmamalı (backend zaten aynı mesajı dönüyor); frontend bu mesajı olduğu gibi göstermeli, kendi tahminiyle zenginleştirmemeli (ör. "Bu kurum size ait değil" gibi kurumun varlığını ima eden bir metin yazılmaz). → AC-S2.
- **DoS**: Sayfalama backend'de yok (kabul edilmiş risk, bkz. backend atdd'si) — frontend bu riski büyütmüyor, ek bir önlem gerekmiyor, atlandı.
- **Elevation**: Nav linkinin görünürlüğü sadece UX'tir; gerçek yetki kararı her istekte backend'de verilir (401/404). Frontend'de "rol X ise erişim var" şeklinde bir client-only guard YOK — böyle bir guard yanlışlıkla gerçek bir yetkilendirme sınırı sanılabilir, bilinçli olarak eklenmedi.

`authz-test` skill'i bu görevde çağrılmadı: yetkilendirme kararı tamamen backend'de zaten test edilmiş (`koordinator-dashboard-ucu` içinde `pytest tests/authorization`), bu görev yeni bir authz dalı eklemiyor — sadece var olan kararı tüketiyor.

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışını değiştirmiyor, sadece bir REST endpoint'i tüketen bir UI sayfası. Bölüm silindi.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (bekleyen kayıtlar var) | Backend `200` + `summary` + iki liste | Yok (salt okunur) | İki sayaç kartı + iki liste (başlık + tarih) | AC-1 |
| 2 | Boş liste (kurumda bekleyen yok) | Backend `200` + `summary` sıfır + `[]` | Yok | İki ayrı empty-state metni, sayaçlar `0` | AC-2 |
| 3 | Kaynak yok / yetkisiz kurum | Backend `404 {"code":"NOT_FOUND","message":"Kurum bulunamadı."}` | Yok | Backend mesajı olduğu gibi (zenginleştirilmeden) gösterilir | AC-3 |
| 4 | Oturumsuz istek | Backend `401` | Login'e yönlendirme (mevcut auth-guard akışı) | `/giris` sayfası | AC-4 |
| 5 | Dış bağımlılık hatası (network/500/timeout) | TanStack Query `isError: true` | Yok (TanStack Query varsayılan retry'ı çalışır) | `aria-live` hata mesajı + "Tekrar dene" butonu | AC-5 |
| 6 | Tenant değişimi (URL'de institution_id manuel değiştirilir) | Cache key `institution_id` içerir → yeni fetch tamamlanana kadar önceki verinin GÖRÜNMEMESİ | Yok | Yükleniyor durumu, ardından yeni kurumun verisi ya da 404 | AC-6 |

Kısmi başarı: **Uygulanmaz** — tek bir GET endpoint'i tüketiliyor, iki liste aynı response'ta birlikte gelir; "bir kısmı geldi kalanı gelmedi" durumu API sözleşmesinde yok. TanStack Query'nin `stale-while-revalidate` davranışı nedeniyle arka planda yeniden deneme başarısız olursa eski veri ekranda kalmaya devam edebilir — bu bir kısmi başarı DEĞİL, "eski ama geçerli veri + arka planda güncelleme başarısız" durumudur; küçük bir "veriler güncellenemedi" notu ile ayırt edilir (silinmedi, çünkü gerçekten oluşabilir bir durum).
Hiçbir şey yapılamadı ama hata da yok: Kurumun hiç bekleyen kaydı yoksa `200` + boş listeler + sıfır sayaçlar döner (AC-2) — sessiz bir "başarı" iddiası taşımaz, çünkü zaten bir yazma işlemi yoktu, sadece "veri yok" gösteriliyor.
Boş sonuç ↔ hata ayrımı: "Veri yok" (kurumun bekleyen kaydı yok) → `200` + boş liste + empty-state. "Yetkin yok" (başka kurum veya oturum yok) → `404`/`401`. İkisi asla aynı UI metnini paylaşmaz.

## Test Strategy
Unit/Component: 70% — sayfa bileşeni (empty-state, sayaç render, tarih formatlama), API client fonksiyonu (`getDashboard`) başarı/hata dallanması, cache-key testi (AC-S1).
Integration: 20% — TanStack Query + mock API (MSW veya benzeri) ile loading/error/success geçişleri, 404/401 senaryoları.
E2E: 10% — happy path: COORDINATOR olarak login → panele git → sayaçları ve listeleri doğrula.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: <500ms (client-side fetch + render dahil; backend zaten <200ms garanti ediyor, kalan pay network+render)
Memory: —
Görsel/UI kriteri: Empty-state'ler tasarlanmış olmalı (CLAUDE.md/frontend.md kuralı: "Boş durum tasarlanmadan ekran bitmiş sayılmaz"); klavye ile tam gezinme, görünür focus, kontrast 4.5:1, hata mesajları `aria-live` ile duyurulur — bu kriterler `verify` adımında `vision-test` skill'iyle kontrol edilmeli.
Diğer ölçülebilir kriterler: Yeni bir HTTP ucu eklenmiyor (var olanı tüketiyor), bu yüzden CLAUDE.md'nin "yeni endpoint = yetkilendirme testi zorunlu" kuralı bu görevde tetiklenmiyor (backend'de zaten karşılanmış).

## Kapsam Dışı
- Hatırlatma gönderme UI'ı (PLAN 3.4 backend'i `yet-108-toplu-hatirlatma-ucu` ile var, ama frontend'i ayrı bir görev/Jira maddesi olmalı — bu görev salt-okunur bir dashboard).
- Kurum admin ekranları (PLAN 3.10, ayrı görev).
- Filtreleme/sıralama/sayfalama — backend bunları desteklemiyor (YAGNI, MVP kapsamı dışı, bkz. backend atdd'si).
- Birden fazla kuruma üye kullanıcı için kurum seçici (switcher) UI'ı — MVP'de tek kurum varsayımı (bkz. Unknowns), gerekirse ayrı görev.

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/app/kurum/[id]/panel/page.tsx` — yeni sayfa (client component, TanStack Query)
- `frontend/lib/api/institutions.ts` — yeni API client dosyası, `getDashboard(institutionId)`
- `frontend/lib/types/institution.ts` (veya `institutions.ts` içine gömülü) — `DashboardResponse`, `PendingItem` tipleri
- Nav bileşeni — hangi dosya olduğu netleşmedi (bkz. Unknowns), `plan` adımında Grep ile bulunmalı

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı bu oturumda net biçimde teyit edilmedi ama pratikte gözlemlendi: git reposunun kökü proje klasörüyle aynı (`C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\yetkin360`). Sonraki adımlar (plan/code-copilot/test-copilot/red-team) arama kapsamını bu klasörle sınırlı tutmalı.

## Rollback Beklentisi
Sayfa salt-okunur (GET-only tüketici) — state rollback'i yok. Hata durumunda (404/401/500) hiçbir yerel/sunucu state'i değişmez, sadece UI hata durumu gösterir.

## Risks
- MVP'de kullanıcının tek bir kuruma üye olduğu varsayılıyor; çoklu kurum üyeliği durumunda hangi `institution_id`'nin gösterileceği netleşmemiş (bkz. Unknowns) — bu risk kabul edilmiş değil, `plan` adımında netleştirilmeli.
- `saga_task_id` bu oturumda oluşturulamadı (Saga MCP bu oturumda hiç bağlı değildi) — iş takibi Saga'dan kopuk kalabilir.

## Assumptions
- Kullanıcının `/me` çağrısındaki `institutions` listesinde tam olarak bir kurum olduğu varsayıldı (MVP ölçeğinde koordinatörlerin tek kuruma üye olacağı varsayımı) — kullanıcı onayı alınmadı, varsayım olarak işaretli.
- Route'un `frontend/app/kurum/[id]/panel/page.tsx` altında olacağı varsayıldı (mevcut `calismalar/[id]` kalıbıyla tutarlı) — kesinleşmiş bir isimlendirme kararı değil, `plan` adımında değiştirilebilir.

## Unknowns
- `GET /me` response'unun `institutions: unknown[]` alanı yalnızca `{id, name}` döndürüyor, kullanıcının o kurumdaki ROLÜNÜ (COORDINATOR/ADMIN) döndürmüyor — bu bir backend gap'i olabilir, `plan` adımında teyit edilmeli (backend değişikliği gerekiyorsa bu görevin kapsamı dışına taşar, ayrı bir görev/uyarı olarak işaretlenmeli).
- Kullanıcı birden fazla kuruma üyeyse (institutions.length > 1) hangi institution_id'nin varsayılan olarak gösterileceği netleşmedi (bkz. Risks).
- Nav bileşeninin tam dosya yolu bu ATDD adımında bulunamadı — `plan` adımında Grep ile belirlenmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → INST_ADMIN/COORDINATOR, nav linki `/me.institutions` doluysa gösterilir (Sonnet 5 low alt-ajanı tarafından yanıtlandı: backend zaten sadece bu rollere 200 dönüyor, frontend görünürlüğü UX'tir).
2. Ana hedef/neden → onay+değerlendirme takibini görsel panelde göstermek (Sonnet 5 low alt-ajanı tarafından yanıtlandı: backend atdd'sinden aktarıldı).
3. Happy path (route, veri şekli, component tipi) → `frontend/app/kurum/[id]/panel/page.tsx`, client component + TanStack Query, iki sayaç + iki liste (Sonnet 5 low alt-ajanı tarafından yanıtlandı: cookie auth + retry ihtiyacı client component'i gerektiriyor).
4. Edge case'ler (boş liste, kurumsuz kullanıcı) → boş: empty-state; kurumsuz: nav'da linklenmez + backend 404 jenerik mesajla gösterilir (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi tablosu → dolduruldu, "girdi geçersiz/eksik" satırı silindi çünkü bu sayfada kullanıcı girdisi yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör tarafından "kısmi başarı" satırı stale-while-revalidate senaryosuyla güçlendirildi).
6. Başarı ölçütü → coverage 85%, performance <500ms (Sonnet 5 low alt-ajanı tarafından yanıtlandı: backend'in <200ms'ine client fetch payı eklendi).
7. Kapsam dışı → hatırlatma UI/admin ekranları/filtreleme-sayfalama/kurum switcher (Sonnet 5 low alt-ajanı tarafından yanıtlandı + orkestratör tarafından switcher eklendi).
8. Bağımlılıklar → yeni sayfa + yeni API client + yeni tipler + nav (dosyası netleşmedi) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
9. Performans/güvenlik kısıtı → React default escape yeterli, dangerouslySetInnerHTML yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı; orkestratör tarafından threat-model adımında Tampering/Info-disclosure AC-S1/AC-S2 eklendi).
10. Rollback → salt-okunur, state rollback yok; hata mesajları sessiz değil (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → otomatik test (component + TanStack Query mock) zorunlu (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLAUDE.md doğrulama matrisi gereği).
12. Test stratejisi oranı → 70/20/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: component ağırlıklı, TanStack Query geçişleri ayrı katman).
13. Threat-model tetikleyici (çok-kiracılı sınır) → AC-S1 (tenant cache-key izolasyonu) ve AC-S2 (jenerik 404 mesajı) eklendi (orkestratör tarafından `threat-model` skill'i ile, STRIDE-lite: Tampering ve Info disclosure kategorileri geçerli bulundu, Spoofing/Repudiation/DoS atlandı, Elevation'da client-only guard bilinçli olarak eklenmedi).
