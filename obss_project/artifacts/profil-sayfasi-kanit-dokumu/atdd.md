---
task_slug: profil-sayfasi-kanit-dokumu
jira_id: YET-111
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 75
  integration: 25
  e2e: 0
affected_modules:
  - frontend/app/profil/page.tsx
  - frontend/app/profil/evidence-section.tsx (yeni)
  - frontend/lib/api/client.ts
  - frontend/messages/tr.json
  - backend/app/api/verified_experiences.py (yeni — GET /talents/me/verified-experiences)
  - backend/app/services/authorization.py (yeni scoped_own_verified_experiences())
  - backend/tests/test_verified_experiences_authorization.py (yeni)
---

# ATDD — profil-sayfasi-kanit-dokumu

## Jira Kaynağı
[YET-111 — [PLAN 3.7] Frontend: profil sayfası — kanıt dökümü (signal + verified experience)](https://kuyusuzyusuf123.atlassian.net/browse/YET-111)
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.7.\nSahip: @fe"
Tip: Görev · Öncelik: Medium · Durum: Yapılacaklar
Not: Jira'da ayrı bir Acceptance Criteria alanı yok — kaynak PLAN.md 3.7 satırı ve final-analiz.md §35 API listesi ("GET /api/v1/talents/me/signals — kanıt dökümü").
Saga: bu oturumda Saga MCP sunucusuna bağlanılamadı — `saga_task_id` kaydedilemedi.

## Persona
Kendi profiline bakan, kimliği doğrulanmış TALENT — oturum sahibi, `principal.talent_id` ile scope'lanmış.

## Hedef (Neden)
Talent'ın beyan ettiği yetkinliklerin arkasında biriken somut kanıtı (skill signal geçmişi) VE doğrulanmış deneyimlerini (verified experience) profilinde tek yerde görebilmesi — bu olmadan kullanıcı sadece `SkillClaim` (beyan) listesini görüyor, `beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirinin "kanıt" ve "doğrulanmış deneyim" halkaları profilde hiç görünmüyor.

## User Story
As a kimliği doğrulanmış talent
I want profilimde skill sinyallerimin (kanıtlarımın) ve doğrulanmış deneyimlerimin dökümünü görmek
So that beyan ettiğim yetkinliklerin arkasında ne kadar somut kanıt biriktiğini ve hangi deneyimlerimin doğrulandığını (görünürlük seviyesinden bağımsız, kendi profilimde) takip edebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir talent'ın `GET /talents/me/signals` ucundan dönen en az 1 skill grubunda sinyalleri varken, When profil sayfası açılır, Then "Kanıt Dökümü" bölümünde sinyaller `skill.name_tr`'ye göre gruplanmış kartlar halinde, her grup içinde `occurred_at` azalan sırada gösterilir; her satırda `source_type`, `strength`, yerelleştirilmiş tarih ve `attested_by` (varsa isim, yoksa "Kendi beyanı") görünür.
2. [High] Given talent'ın hiç skill sinyali yoksa (`items: []`), When profil sayfası açılır, Then boş durum mesajı ("Henüz kanıt sinyali yok") gösterilir — hata değil.
3. [High] Given `GET /talents/me/signals` isteği başarısız olursa (network/500), When profil sayfası açılır, Then `role="alert"` ile "Kanıt dökümü yüklenemedi" mesajı + "Tekrar dene" butonu gösterilir; `ProfileForm`/`SkillsSection` bölümleri bundan etkilenmez (bağımsız sorgu, hata izolasyonu).
4. [Medium] Given bir sinyal `superseded: true` ise, When listelenirken, Then satır listeden gizlenmez, soluk/üstü çizili stil + "Geçersiz kılındı" rozetiyle (aria-label ile ekran okuyucuya da iletilir) işaretlenir.
5. [Medium] Given bir sinyalin `attested_by` alanı `null` ise (SELF_CLAIM), When listelenirken, Then "Kendi beyanı" etiketiyle gösterilir, harici tanık isimlerinden görsel olarak ayrışır.
6. [High] Given herhangi bir metin alanı (`skill.name_tr`, `attested_by` ismi, `organization_name_snapshot`) kullanıcı/harici kaynaklı olabilir, When render edilirken, Then `dangerouslySetInnerHTML` KULLANILMAZ, düz metin olarak basılır.
7. [Critical] Given kimliği doğrulanmış bir talent'ın kendi `verified_experiences` kayıtları (visibility'den BAĞIMSIZ, PRIVATE dahil) varken, When `GET /talents/me/verified-experiences` çağrılır, Then 200 + kendi kayıtlarının tamamı (organization_name_snapshot, role_snapshot, started_on_snapshot, ended_on_snapshot, institution_name_snapshot, claim_type, visibility, public_token, created_at) döner.
8. [High] Given talent'ın hiç verified experience'ı yoksa, When uç çağrılır, Then 200 + `{items: []}` döner — hata değil.
9. [Critical] Given kimliği doğrulanmış bir talent A, When `GET /talents/me/verified-experiences` çağrılır, Then SADECE talent A'nın kendi kayıtları döner — başka hiçbir talent'ın kaydı hiçbir koşulda sızmaz (AC-S1).
10. [High] Given oturumsuz (unauthenticated) bir istek, When `GET /talents/me/verified-experiences` çağrılır, Then 401 döner (AC-S2).
11. [High] Given kimliği doğrulanmış ama talent profili olmayan bir principal (ör. sadece ORG_MEMBER/COORDINATOR), When uç çağrılır, Then 404 döner (AC-S3 — talent olmayan bir hesabın "kendi" talent verisi yoktur, kaynak yok sayılır).
12. [High] Given profil sayfası açılır, When hem sinyal hem verified experience verisi yükleniyor/yüklendi, Then iki bölüm birbirinden bağımsız `useQuery` ile çekilir — biri hata verirse diğeri etkilenmez.

## Threat Model
Çağrıldı — yeni bir HTTP ucu (`GET /talents/me/verified-experiences`) eklendiği için tetikleyici var (kişisel veri + kimlik doğrulama/yetkilendirme + yeni endpoint). STRIDE-lite:
- **Spoofing**: mevcut oturum/JWT doğrulaması (`get_current_principal`) kullanılıyor, yeni bir mekanizma eklenmiyor — atlandı.
- **Tampering**: `talent_id` İSTEMCİDEN gelmiyor (URL'de yok, body'de yok) — filtre her zaman `principal.talent_id`'den (oturumdan) kurulur. → AC-S1.
- **Repudiation**: GET-only, state değişmiyor — atlandı.
- **Info disclosure**: en yüksek risk — bu uç `visibility` filtresi UYGULAMADAN tüm kayıtları döner (kasıtlı: kendi profiline bakan kişi kendi PRIVATE kaydını da görmeli), bu yüzden `talent_id` filtresinin principal'dan doğru kurulması kritik. → AC-S1, AC-S3 (talent olmayan principal'a 404, veri sızdırmaz).
- **DoS**: sayfalama yok — kabul edilmiş risk (bkz. Risks), tek talent'ın kayıt sayısı küçük.
- **Elevation**: yetki kontrolü sunucuda (`principal.talent_id is None` → 404, `principal.user_id is None` → 401), UI'da gizleme değil. → AC-S2, AC-S3.

Yeni scoped fonksiyon: `scoped_own_verified_experiences(session, principal)` — `authorization.py`'ye eklenir, `VerifiedExperience.talent_id == principal.talent_id` ile filtreler (mevcut `scoped_public_verified_experiences`'tan farklı: visibility kontrolü YOK, çünkü sahibi kendi verisine bakıyor).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / UI durumu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (sinyal var) | `items` listesi grup grup render edilir | Yok (salt okuma) | Skill adına göre gruplanmış sinyal kartları, tarih sırasıyla | AC-1 |
| 2 | Sinyal yok (`items: []`) | Boş durum bileşeni | Yok | "Henüz kanıt sinyali yok" mesajı | AC-2 |
| 3 | API hatası (500/network) | `isError` state | Yok — retry butonu kullanıcı eylemiyle yeniden fetch tetikler | `role="alert"` ile "Kanıt dökümü yüklenemedi" + "Tekrar dene" butonu | AC-3 |
| 4 | `superseded: true` olan sinyal | Aynı listede kalır, soluk/üstü çizili stil + rozet | Yok | "Geçersiz kılındı" etiketi, veri gizlenmez | AC-4 |
| 5 | `attested_by: null` (SELF_CLAIM) | Aynı satır tipi, sabit metin | Yok | "Kendi beyanı" etiketi | AC-5 |
| 6 | Verified experience — happy path (kendi kayıtları) | `200 {"items": [{"id","organization_name_snapshot","role_snapshot","started_on_snapshot","ended_on_snapshot","institution_name_snapshot","claim_type","visibility","public_token","created_at"}...]}` | Yok | Doğrulanmış deneyim kartları | AC-7 |
| 7 | Verified experience yok | `200 {"items": []}` | Yok | Boş durum mesajı | AC-8 |
| 8 | Başka talent'ın kaydı (cross-talent) | Asla dönmez — `scoped_own_verified_experiences` `principal.talent_id` ile filtreler | Yok | (İlgisiz) | AC-9/AC-S1 |
| 9 | Oturumsuz istek | `401 {"code":"UNAUTHORIZED","message":"Kimlik doğrulama gerekli."}` | Yok | Giriş gerekli mesajı | AC-10/AC-S2 |
| 10 | Talent profili olmayan principal | `404 {"code":"NOT_FOUND","message":"Talent bulunamadı."}` | Yok | "Bulunamadı" | AC-11/AC-S3 |

Kısmi başarı: **Uygulanmaz** — hem sinyal bileşeni hem yeni verified-experience ucu salt-okunur (GET-only), DB'ye yazma yapmıyor, "bir kısmı yazıldı kalanı yazılamadı" durumu oluşamaz.
Hiçbir şey yapılamadı ama hata yok: Sinyal/verified-experience yoksa `200 + {items: []}` döner (AC-2, AC-8) — boş liste açıkça "veri yok" durumudur, hata değildir.
Boş sonuç ↔ hata ayrımı: "Veri yok" (`items: []`, 200) ile "hata" (network/500 veya 401/404) net ayrılır — frontend'de TanStack Query'nin `isError`/`data` ayrımıyla, backend'de `principal.talent_id is None` kontrolünün `scoped_own_verified_experiences` çağrısından ÖNCE yapılmasıyla sağlanır.

## Test Strategy
Unit/Component: 75% — `evidence-section.tsx` için (mevcut `skills-section.test.tsx` deseniyle) happy path, boş durum, hata durumu, superseded rozeti, SELF_CLAIM etiketi testleri + backend `scoped_own_verified_experiences()` unit testi.
Integration: 25% — TanStack Query + mock API ile sayfa (`profil/page.tsx`) üzerinden entegrasyon + backend `GET /talents/me/verified-experiences` uç testleri (`pytest tests/authorization -q` dahil, AC-S1-S3 için ZORUNLU).
E2E: 0% — proje genelinde frontend component görevlerinde e2e kullanılmıyor (mevcut pattern).

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Yok (statik render, ek performans hedefi tanımlanmadı)
Memory: Yok
Görsel/UI kriteri: WCAG 2.1 AA kontrast (min 4.5:1), durum/hata mesajları `aria-live="polite"` (kritik hata `role="alert"`), tüm etkileşimli öğeler (Tekrar Dene butonu) Tab ile erişilebilir. Bu kriter `verify` adımında `vision-test`/erişilebilirlik kontrolüyle doğrulanmalı — buraya not düşülmezse unutulur.
Diğer ölçülebilir kriterler: —

## Kapsam Dışı
- Attestation/verified-experience detay sayfası, itiraz/challenge akışı.
- Profil düzenleme (zaten `ProfileForm` ile var).
- Sinyal filtreleme/arama/sıralama UI'ı, sinyal ekleme/silme (bu bölüm salt-okunur).
- Sayfalama — MVP'de tüm liste tek seferde çekilir (sinyal sayısı düşük varsayımı).

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/app/profil/page.tsx` — yeni bölümü render edecek şekilde güncellenir
- `frontend/app/profil/evidence-section.tsx` (yeni) — `skills-section.tsx` deseniyle, hem sinyal hem verified-experience alt-bölümlerini render eder
- `frontend/lib/api/client.ts` — yeni `getMySignals()` (mevcut `GET /talents/me/signals`) + `getMyVerifiedExperiences()` (yeni `GET /talents/me/verified-experiences`) fonksiyonları
- `frontend/messages/tr.json` — yeni UI metinleri (Türkçe, koda gömülmez)
- `backend/app/api/verified_experiences.py` (yeni) — `GET /talents/me/verified-experiences` route + Pydantic response şeması (mevcut `skill_signals.py` deseniyle)
- `backend/app/services/authorization.py` — yeni `scoped_own_verified_experiences(session, principal)` fonksiyonu
- `backend/tests/test_verified_experiences_authorization.py` (yeni) — AC-S1-S3 pozitif/negatif testleri (`pytest tests/authorization -q` kapsamında)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökü proje klasöründen daha geniş olabilir. Sonraki adımlar arama kapsamını `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\yetkin360` ile sınırlı tutmalı.

## Rollback Beklentisi
Salt-okunur görüntüleme bileşeni — state mutasyonu yok. API hatasında sadece kendi bölümü hata durumuna düşer, `ProfileForm`/`SkillsSection` etkilenmez (bağımsız `useQuery` çağrısı, hata izolasyonu component bazında).

## Risks
- Bu görev artık hem frontend hem backend değişikliği içeriyor (Jira "Sahip: @fe" diyordu, kullanıcı onayıyla backend ucu da eklendi) — sahiplik/PR kapsamı gerçek ekip pratiğinde iki kişiye bölünebilir, tek bir PR'da birleştirmek gerçek dünyada @fe/@be1 arası koordinasyon gerektirebilir. Bu proje bağlamında (hackathon, tek geliştirici havuzu) sorun değil.
- Yeni endpoint = CLAUDE.md'nin "yeni endpoint = aynı commit'te yetkilendirme testi" kuralı zorunlu — `code-copilot`/`test-copilot` bunu atlamamalı.

## Assumptions
- Response şekli (`items[].skill`, `items[].signals[]` — sinyal ucu) mevcut `backend/app/api/skill_signals.py`'deki gerçek şemadan alındı (varsayım değil, kod okunarak doğrulandı).
- Verified-experience response alan seti doğrudan `VerifiedExperience` modelinin (`backend/app/models/verified_experience.py`) kolonlarından alındı (varsayım değil, kod okunarak doğrulandı) — `public_token` alanı da dahil edildi çünkü sahibi kendi paylaşılabilir linkini görebilmeli.
- `scoped_own_verified_experiences`'ın visibility filtresi UYGULAMAMASI (sahibi tüm kendi kayıtlarını, PRIVATE dahil, görür) kasıtlı bir tasarım kararı — final-analiz §15.4'teki "TalentProfile (sahip): RW" ilkesiyle tutarlı (sahip kendi verisine tam erişir).

## Unknowns
- Yok — kullanıcı onayıyla kapsam netleşti, açık soru kalmadı.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → kimliği doğrulanmış TALENT, kendi profili (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef/neden → beyan-kanıt zincirinin kanıt halkasını profilde görünür kılmak (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path (bölüm yapısı, alanlar) → skill'e göre gruplu sinyal kartları (Sonnet 5 low alt-ajanı tarafından yanıtlandı, gerçek response şeması kod okumasıyla teyit edildi).
4. Edge case'ler → boş durum, API hatası, superseded, SELF_CLAIM (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi tablosu → dolduruldu, "verified experience" satırı kapsam kararı nedeniyle çıkarıldı (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
6. Başarı ölçütü → WCAG 2.1 AA + %80 coverage (Sonnet 5 low alt-ajanı tarafından yanıtlandı, proje `frontend.md` erişilebilirlik kuralına dayanıyor).
7. Kapsam dışı → detay sayfası/itiraz/filtreleme/sayfalama (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. **Kritik karar — verified experience kapsama dahil mi?** → İlk turda Sonnet 5 low alt-ajanı (a) seçeneğini (çıkar) önermişti; kullanıcıya PLAN.md'nin tamamı (3.1-3.16) tarandığında "own verified experience" ucunun HİÇBİR yerde planlanmadığı raporlandı, kullanıcı **"ekle eksik kalmasın"** dedi — verified experience bu göreve DAHİL edildi, yeni bir backend ucu (`GET /talents/me/verified-experiences`) + `scoped_own_verified_experiences()` eklendi. **(kullanıcı mesajından, doğrudan onay)**
9. Performans/güvenlik kısıtı → dangerouslySetInnerHTML yasak, frontend rol kontrolü sadece UX, backend'de talent_id principal'dan kurulur (Sonnet 5 low alt-ajanı + orkestratör tarafından, `frontend.md`/final-analiz §15.4 kuralına dayanıyor).
10. Rollback → salt-okunur, hata izolasyonu component bazında (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → otomatik test (component test + vitest, backend authz testi) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi oranı → 75/25/0 (Sonnet 5 low alt-ajanı + orkestratör: backend authz testleri integration payını artırdı, e2e proje genelinde kullanılmıyor).
13. Threat-model tetikleyici kontrolü → yeni HTTP ucu eklendiği için tetikleyici VAR, AC-S1-S3 eklendi (orkestratör tarafından, STRIDE-lite değerlendirmesi, madde 8'deki kapsam kararından sonra yeniden değerlendirildi).
