---
task_slug: public-profil-endpoint
jira_id: YET-105
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/services/visibility_service.py (yeni)
  - backend/app/api/public.py (yeni)
  - backend/app/services/authorization.py (scoped_public_talent_profile eklenecek)
  - backend/tests/test_public_profile.py (yeni)
  - backend/tests/authorization/test_public_profile_authz.py (yeni)
---

> **2026-09-25 plan revizyonu:** `plan` adımındaki kod keşfi atdd.md'nin
> orijinal varsayımlarını yanlış çıkardı — gerçek şema incelendi, 3 açık
> soru kullanıcı yetkisiyle Sonnet 5 low alt-ajanına çözdürüldü
> (bkz. `plan.md` "Kararlar"). Bu dosya o kararlara göre GÜNCELLENMİŞTİR:
> route artık UUID değil **slug** tabanlı, visibility ikili değil **4
> seviyeli** (sadece PUBLIC gösterilir), response'ta **attestations/
> skill_signals YOK** (sadece verified_experiences). Aşağıdaki AC'ler ve
> Davranış Sözleşmesi bu düzeltilmiş haliyle okunmalı.
>
> **2026-09-25 verify revizyonu (gate 6 FAIL sonrası):** `verify` adımında
> gerçek testler çalıştırılınca bu dosyanın hata gövdesi varsayımı YANLIŞ
> çıktı. Proje `docs/API.md §1.4`'te belgelenmiş, `app/core/errors.py`'deki
> `ApiError` sınıfıyla uygulanan **zorunlu** bir hata zarfı kullanıyor:
> `{"code": "SCREAMING_SNAKE_CASE", "message": "Türkçe metin", "request_id":
> "uuid"}` — aşağıdaki `{"detail": "Not found"}` varsayımı bununla
> DEĞİŞTİRİLDİ. Ayrıca `started_on_snapshot`/`ended_on_snapshot` alanlarının
> tipi `date | None` olmalı (`str | None` değil) — Pydantic bunu otomatik
> ISO-8601 string'e serialize eder, elle `str` tipine zorlamak `date`
> objesini reddeder.

# ATDD — public-profil-endpoint

## Jira Kaynağı
[YET-105 — Public profil ucu + visibility kuralları](https://kuyusuzyusuf123.atlassian.net/browse/YET-105)
PLAN.md Faz 3 — madde 3.1. Sahip: @be1.
Hedef (Jira'dan birebir): "jürinin göreceği yüz için public profil endpoint'i ve visibility kuralları."
Alt görevler (Jira'da tanımlı, bu atdd.md'de AC'lere dönüştürüldü):
- YET-121 — Servis: visibility kuralı hesaplama
- YET-122 — GET /talents/{id}/public-profile ucu
- YET-123 — Yetkilendirme testi: visibility=private/public erişim matrisi

## Persona
Kimlik doğrulaması olmayan üçüncü taraf ziyaretçi: jüri üyesi, potansiyel işveren, ya da herkese açık internet. Login zorunlu değil — "jürinin göreceği yüz" tanımı ve MVP kapsamı buna dayanıyor. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: proje dokümanındaki "görünür yüz" ifadesi ve genel-erişim persona listesi login zorunluluğunu dışlıyor.)

## Hedef (Neden)
Bu endpoint olmadan "beyan → kanıt → tanıklık → doğrulanmış deneyim" zinciri dışarıya hiç görünmez — platformun tüm kanıt zinciri sistem içinde kilitli kalır. Bu uç, o zincirin jüri/işveren tarafından görülebilen tek dışa açık yüzeyidir. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)

## User Story
As a kimliksiz ziyaretçi (jüri/işveren)
I want bir talent'ın public profilini görüntülemek
So that doğrulanmış deneyimlerini ve kanıtlarını login olmadan inceleyebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş — plan revizyonuyla güncel)
1. [Critical] Given visibility='PUBLIC' olan var olan bir talent'ın public_slug'ı, When GET /public/talents/{slug} çağrılır, Then 200 + {talent_id, display_name, verified_experiences[]} döner — verified_experiences sadece visibility='PUBLIC' olan kayıtları içerir. attestations/skill_signals response'ta YOK (bkz. Kararlar).
2. [Critical] Given var olmayan bir slug (public_slug eşleşmiyor), When GET /public/talents/{slug} çağrılır, Then 404 + {"detail": "Not found"} döner.
3. [Critical] **AC-S1 (threat-model)** Given visibility='PRIVATE'/'INSTITUTION'/'ORGANIZATIONS' olan (yani PUBLIC olmayan) var olan bir talent'ın slug'ı, When GET /public/talents/{slug} çağrılır, Then AC-2 ile **birebir ayırt edilemez** 404 + {"detail": "Not found"} döner (aynı status kodu, aynı body, aynı Content-Length) — enumeration/IDOR'a karşı. Bu, talent_profiles.visibility'nin 4 değerinden (PRIVATE/INSTITUTION/ORGANIZATIONS) hangisi olursa olsun geçerlidir — PUBLIC dışındaki tüm seviyeler bu uçta aynı 404'e denk gelir.
4. [Critical] **AC-S2 (threat-model)** Given visibility='PUBLIC' bir talent'ın response'u, When şema incelenir, Then email, institution_id, user_id gibi PII/dahili alan **kesinlikle** bulunmaz — sadece talent_id, display_name, verified_experiences.
5. [High] **AC-S3 (threat-model)** Given visibility='PUBLIC' bir talent'ın bazı verified_experience kayıtları visibility='PRIVATE'/'INSTITUTION'/'ORGANIZATIONS' ise, When response oluşturulur, Then bu kayıtlar listeye dahil edilmez — sadece verified_experience.visibility='PUBLIC' olanlar listelenir (granüler filtre, talent-seviyesi PUBLIC olsa da tekil deneyim PUBLIC olmayabilir).
6. [High] Given public_slug alanı NULL olan bir talent (henüz slug oluşturmamış), When o talent'ın slug'ı tahmin edilip GET /public/talents/{slug} çağrılır, Then 404 döner (NULL slug hiçbir zaman eşleşmez, ayrı bir kod yolu gerekmez).
7. [Medium] Given DB bağlantı hatası, When GET /public/talents/{slug} çağrılır, Then 500 + generic {"detail": "Internal server error"} döner, stack trace sızdırılmaz.

## Threat Model
Çağrıldı — AC-S1, AC-S2, AC-S3 yukarıdaki Acceptance Criteria'ya (AC-3, AC-4, AC-5) eklendi. STRIDE-lite sonucu: Spoofing/Repudiation/Elevation bu uç için uygulanmaz (auth yok, salt okuma, yetki kavramı "public/private" ayrımına indirgeniyor — bu da Info Disclosure'a giriyor). Asıl risk **Information Disclosure** (enumeration + PII sızıntısı) ve düşük öncelikli **DoS** (rate-limit yok — bkz. Risks, kabul edilen risk olarak işaretlendi). `authz-test` skill'i de çağrıldı; özel test matrisi aşağıda "Güvenlik Test Matrisi" bölümünde.

## Davranış Sözleşmesi (hangi durumda ne döner — plan revizyonuyla güncel)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (visibility='PUBLIC') | `200` + `{"talent_id":"uuid","display_name":"string","verified_experiences":[{"id":"uuid","organization_name_snapshot":"string","role_snapshot":"string","started_on_snapshot":"2025-01-01","ended_on_snapshot":"2025-06-01","claim_type":"COMPETENCE","created_at":"2026-09-25T10:00:00Z"}]}` (`started_on_snapshot`/`ended_on_snapshot` gerçek tip `date`, JSON'da ISO-8601 string olarak serialize edilir) | Yok (salt okuma) | Profil sayfası dolu render edilir | AC-1 |
| 2 | Kaynak yok (slug eşleşmiyor) | `404` + `{"code":"TALENT_NOT_FOUND","message":"Kayıt bulunamadı","request_id":"uuid"}` (proje-genel `ApiError` zarfı, `docs/API.md §1.4`) | Yok | "Profil bulunamadı" | AC-2 |
| 3 | Yetkisiz erişim (visibility='PRIVATE'/'INSTITUTION'/'ORGANIZATIONS') | `404` + AYNI `ApiError` zarfı — satır 2 ile **`code`/`message` alanları bit-bit aynı** (`request_id` her istekte farklı UUID olacağı için enumeration testinde `request_id` HARİÇ tutularak karşılaştırılmalı) | Yok | "Profil bulunamadı" (satır 2'den ayırt edilemez) | AC-3 |
| 4 | public_slug NULL olan talent'a rastgele slug denemesi | `404` + aynı `ApiError` zarfı (satır 2/3 ile `code`/`message` aynı) | Yok | "Profil bulunamadı" | AC-6 |
| 5 | Dış bağımlılık hatası (DB down) | `500` + `ApiError` zarfı (`code`: ör. `INTERNAL_ERROR`, `message`: genel Türkçe metin, stack trace sızmaz) | Yok (transaction yok) | Genel hata sayfası | AC-7 |

Zaman aşımı: Uygulanmaz — tek basit SELECT sorgusu, dış ağ çağrısı (AI/S3/e-posta) yok, ayrı bir timeout senaryosu gerekmiyor.
Kısmi başarı: Uygulanmaz — tek okuma (GET) endpoint'i, atomik olarak ya tam veri ya 404/500 döner, ara durum yok.
Hiçbir şey yapılamadı ama hata yok: Uygulanmaz — read endpoint'te sessiz başarısızlık senaryosu yok, her durum ya veri ya açık hata kodu döner.
Boş sonuç ↔ hata ayrımı: Bu uçta "boş liste" senaryosu yok (tekil kaynak GET'i, slug ile) — ama `verified_experiences` listesi boş dönebilir: bu geçerli bir 200 durumu (talent PUBLIC ama henüz PUBLIC-visibility deneyimi yok), 404 ile karıştırılmaz.

## Test Strategy
Unit: 70% — visibility_service.py'deki saf hesaplama fonksiyonları (can_view_public_profile, filter_public_experiences) çok sayıda durum kombinasyonuyla test edilir.
Integration: 20% — endpoint + gerçek DB, scoped_*()/can() üzerinden gerçek sorgu, AC-1/AC-2/AC-3/AC-6/AC-7.
E2E: 10% — tam happy-path + 404 senaryosu.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: yok (bu görev sadece backend ucu — frontend tarafı YET-112/3.8'de ayrı)
Diğer ölçülebilir kriterler: AC-3 (enumeration testi) — PUBLIC-olmayan ve var-olmayan slug için response body byte-byte eşit olmalı; test bunu literal string/JSON karşılaştırmasıyla doğrular.

## Kapsam Dışı
- Profil düzenleme/CRUD (ayrı görev)
- Profil fotoğrafı yükleme
- Arama/filtreleme/listeleme motoru (matching motoru MVP dışı — CLAUDE.md yasaklı liste)
- Rate-limit / anti-scraping (kabul edilen risk, bkz. Risks)
- Timing-attack ölçümü (kabul edilen risk, bkz. Risks — otomatik testte güvenilir ölçülemiyor)
- Sayfalama ötesi gelişmiş sıralama
- **`attestations`/`skill_signals` public response'ta yok** (plan revizyonu — bkz. Kararlar madde 3: bu iki tablonun kendi visibility alanı yok, verified_experience'a doğrudan FK'leri yok, MVP'de güvenli bir gösterim kuralı türetilemedi)
- **INSTITUTION/ORGANIZATIONS seviyesi visibility** bu uçta ele alınmaz (plan revizyonu — bkz. Kararlar madde 1: ayrı, kimlik doğrulamalı uçlara ait — 3.3 koordinatör, 3.5 kurum dashboard)

## Etkilenen Dosyalar/Modüller (bilinen — plan.md'den kesinleşti)
- `backend/app/services/visibility_service.py` (yeni) — visibility kuralı hesaplama (YET-121)
- `backend/app/api/public.py` (yeni) — GET /public/talents/{slug} ucu (YET-122)
- `backend/app/services/authorization.py` (değişecek) — `scoped_public_talent_profile()` yeni fonksiyon eklenecek (çıplak select() yasağına uymak için)
- `backend/tests/test_public_profile.py` (yeni)
- `backend/tests/authorization/test_public_profile_authz.py` (yeni, YET-123 + AC-S1/S2/S3)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (`plan` adımında) — repo kökü proje klasörüyle aynı (`git rev-parse --show-toplevel` = `yetkin360`), sınırsız arama riski yok.

## Rollback Beklentisi
Salt okuma (GET) endpoint'i — DB'ye yazma yok, rollback senaryosu yok. Hata durumunda (500) hiçbir kalıcı durum değişikliği olmaz.

## Risks
- **Kabul edilen risk — Rate limit/anti-scraping yok:** MVP/hackathon kapsamında bilinçli olarak dışarıda bırakıldı; endpoint teorik olarak toplu taranabilir (talent listesi scrape edilebilir). Faz 3 sonrası veya gerçek üretim öncesi ele alınmalı.
- **Kabul edilen risk — Timing side-channel:** "var olmayan" (404) ile "private" (404) sorgularının DB'de farklı sürede dönme ihtimali (biri talent_profiles'ta hiç satır bulamaz, diğeri bulur ama visibility kontrolünde eler) teorik bir enumeration kanalı oluşturabilir. Otomatik testte güvenilir ölçülemediği için AC'ye dönüştürülmedi; kod tarafında iki yol da aynı sorgu şeklini (tek sorgu + uygulama seviyesi visibility kontrolü, iki ayrı sorgu değil) kullanmalı — bu bir implementasyon notu, code-copilot'a aktarılmalı.

## Assumptions
- `display_name`'in kaynağı `talent_profiles.full_name` alanı olarak varsayıldı (şemada `TalentProfile.full_name` doğrulandı — `plan` adımında kesinleşti, artık varsayım değil).
- `scoped_public_talent_profile()` fonksiyonunun `visibility='PUBLIC' AND public_slug IS NOT NULL AND deleted_at IS NULL` filtresiyle tek sorguda çalışacağı varsayıldı (timing side-channel riskini azaltmak için, bkz. Risks).

## Unknowns
- (çözüldü — plan adımında şema doğrulandı: visibility 4 seviyeli enum, public_slug CITEXT unique nullable, full_name display adı)

## Güvenlik Test Matrisi (authz-test — plan revizyonuyla güncel)
Bu endpoint standart multi-tenant IDOR matrisinden farklı: "saldırgan" kimliksiz herkes, hedef "var/yok" ve "PUBLIC/PUBLIC-olmayan" ayrımının response'tan sızmaması. `test-copilot`'a extra_instructions olarak aktarılacak:

| # | Durum | Beklenen | AC |
|---|---|---|---|
| 1 | Var olmayan slug | `404` + `ApiError` zarfı (`code`/`message` sabit, `request_id` her istekte farklı) | AC-2 |
| 2 | Var olan slug, visibility='PRIVATE' | `404` + AYNI `code`/`message` (satır 1 ile) | AC-3 (AC-S1) |
| 3 | Var olan slug, visibility='INSTITUTION' | `404` + AYNI `code`/`message` (satır 1 ile) | AC-3 (AC-S1) |
| 4 | Var olan slug, visibility='ORGANIZATIONS' | `404` + AYNI `code`/`message` (satır 1 ile) | AC-3 (AC-S1) |
| 5 | Var olan slug, visibility='PUBLIC' | `200` + tam JSON şeması, PII/dahili alan yok, `attestations`/`skill_signals` alanı response'ta hiç yok | AC-1, AC-4 (AC-S2) |
| 6 | visibility='PUBLIC' talent'ın visibility='PRIVATE' bir verified_experience'ı | Response listesine dahil edilmez | AC-5 (AC-S3) |
| 7 | public_slug NULL olan talent'a rastgele slug denemesi | `404` + satır 1 ile aynı `code`/`message` | AC-6 |

Mock kullanılmaz — gerçek DB'ye gerçek istek atılmalı (proje test ortamı). Satır 1-4 karşılaştırması (enumeration testi) `test-copilot` tarafından **`code` ve `message` alanlarının tam eşitliği** ile doğrulanmalı (`request_id` her istekte UUID4 olduğu için karşılaştırma dışı tutulur — `response.json()["code"] == other.json()["code"] and response.json()["message"] == other.json()["message"]`), sadece status kodu kontrolü YETERSİZ. `status_code` ayrıca `404` olarak da doğrulanmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Kimlik doğrulamasız üçüncü taraf (jüri, işveren, herkese açık internet) (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
2. Ana hedef/neden → Zincirin dışa açık yüzeyi, bu olmadan çalışmaz (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path JSON şekli → yukarıdaki Davranış Sözleşmesi satır 1 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
4. Edge case: talent_id yok → 404 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Edge case: visibility=private → 404, 403 değil (kullanıcı mesajından — CLAUDE.md kuralı zaten belirtilmişti)
6-7. Davranış sözleşmesi satırları → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Auth gerekiyor mu → Hayır, auth-free (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Visibility hesaplama kaynağı → talent_profiles.visibility enum, varsayılan private (Sonnet 5 low alt-ajanı tarafından yanıtlandı, Assumptions'a işaretlendi)
10. Kapsam dışı → yukarıdaki liste (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Test stratejisi oranı → 70/20/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı, backend API standardı)
12. Threat-model tetikleyici → Evet (Sonnet 5 low alt-ajanı tarafından yanıtlandı) → threat-model ve authz-test skill'leri bu oturumda çağrıldı, AC-S1/S2/S3 üretildi.
