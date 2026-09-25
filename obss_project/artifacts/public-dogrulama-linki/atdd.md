---
task_slug: public-dogrulama-linki
jira_id: YET-106
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
  - backend/alembic/versions/ (yeni migration — VerifiedExperience.public_token kolonu)
  - backend/app/models/verified_experience.py (public_token alanı eklenecek)
  - backend/app/services/verified_experience.py veya visibility_service.py (token doğrulama + payload üretimi — YET-124)
  - backend/app/api/public.py (mevcut, GET /public/v/{token} ucu eklenecek — YET-125)
  - backend/tests/test_public_verification.py (yeni)
  - backend/tests/authorization/test_public_verification_authz.py (yeni)
---

# ATDD — public-dogrulama-linki

## Jira Kaynağı
[YET-106 — Public doğrulama linki GET /public/v/{token}](https://kuyusuzyusuf123.atlassian.net/browse/YET-106)
PLAN.md Faz 3 — madde 3.2. Sahip: @be1.
Hedef (Jira'dan birebir): "token ile herkese açık doğrulama ucu."
Alt görevler (Jira'da tanımlı, bu atdd.md'de AC'lere dönüştürüldü):
- YET-124 — Servis: token doğrulama + payload üretimi
- YET-125 — GET /public/v/{token} ucu (auth gerektirmez, rate-limit)
- YET-126 — Yetkilendirme testi: geçersiz/expired/revoked token → 404

**Önemli:** Bu görev, projenin kendi dokümanlarında (`docs/API.md §2.9`,
`docs/AUTHORIZATION.md` §F, `docs/DATABASE.md`, `docs/DOMAIN.md`) zaten
birebir tanımlanmış — atdd aşamasında tahmin YAPILMADI, doğrudan bu
dokümanlardan alındı (aşağıda alıntılanmıştır).

## Persona
Kimlik doğrulaması olmayan üçüncü taraf — `docs/API.md`'nin kendi ifadesiyle
"jürinin telefonundan açacağı uç." (docs/API.md §2.9'dan birebir)

## Hedef (Neden)
Bu uç, "beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirinin dış
dünyaya sunduğu tek-ekran kanıtıdır — YET-105'in (`/public/p/{slug}`, genel
profil) tamamlayıcısı, ama burada odak tek bir doğrulanmış deneyim kaydı.
Bu uç olmadan ürünün "kanıt paylaşılabilir" iddiası çalışmaz.

## User Story
As a kimliksiz ziyaretçi (jüri/işveren, elinde bir paylaşım linki)
I want bir doğrulama linkini açıp o kaydın gerçekliğini görmek
So that talent'ın iddiasını login olmadan, tek ekranda doğrulayabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `VerifiedExperience.public_token` ile eşleşen, `visibility='PUBLIC'` olan bir kayıt, When `GET /public/v/{token}` çağrılır, Then `200` + şu JSON şeması döner: `{title, talent_name, organization_name, organization_trust_level, institution_name, started_on, ended_on, verified_at, attested_skills: [{name_tr, claim_type, attestor_organization}]}` (plan.md Kararlar madde 1: `attestor_name` yerine `attestor_organization` — `Organization.name`, `attestor_org_id` üzerinden; `User`/`Attestation` şemasında kişi adı için kaynak yok, `docs/API.md §2.9`'un `attestor_name` örneği bu görevde gerçekleştirilemez).
2. [Critical] Given var olmayan bir token, When `GET /public/v/{token}` çağrılır, Then `404` + proje hata zarfı (`{code, message, request_id}`, `docs/API.md §1.4`, `app/core/errors.py::ApiError`) döner.
3. [Critical] **AC-S2 (threat-model)** Given `visibility != 'PUBLIC'` olan var olan bir token, When `GET /public/v/{token}` çağrılır, Then AC-2 ile **`code`/`message` alanları birebir aynı** `404` döner (`docs/AUTHORIZATION.md` F6) — enumeration'a karşı, tek WHERE'de (`public_token=... AND visibility='PUBLIC'`) birleşik sorgu.
4. [High] **AC-S1 (threat-model)** Given yeni `public_token` kolonunun üretim mekanizması, When kod incelenir, Then kriptografik olarak güvenli bir RNG (`secrets.token_urlsafe` veya eşdeğeri) ile **≥128 bit** entropili token üretilir — `uuid.uuid4()` gibi tahmin edilebilir/düşük-entropili bir kaynak KULLANILMAZ. Test edilebilir hali: üretilen token'ın karakter kümesi/uzunluğu belirli bir minimum entropiye karşılık gelir (ör. `urlsafe_b64` alfabesinde ≥22 karakter).
5. [Medium] **AC-S4 (threat-model)** Given AC-1'in response şeması, When incelenir, Then `talent_id`, `user_id`, `email`, `institution_id` gibi dahili/PII alanları response'ta **kesinlikle** bulunmaz — sadece `docs/API.md`'nin belirttiği 9 alan.
6. [Medium] Given `verified_experiences` snapshot semantiği (`docs/DOMAIN.md §3.13`), When ilişkili `Organization`/`Institution` kaydı silinmiş veya adı değişmiş olsa bile, Then response snapshot alanlarından (`organization_name_snapshot` vb.) okunmaya devam eder — canlı FK join'e bağımlı DEĞİLDİR.
7. [Low] Given DB bağlantı hatası, When `GET /public/v/{token}` çağrılır, Then `500` + proje hata zarfı döner, stack trace sızdırılmaz.

**Kapsam dışı bırakılan AC (F5/410 — bilinçli, aşağıya bakın):** `docs/AUTHORIZATION.md`'nin F5 satırı ("iptal edilmiş doğrulama linki → 410 Gone") bu görevde **uygulanmaz** — DB'de "iptal" (revoke) durumunu temsil edecek hiçbir kolon/mekanizma yok (`VerifiedExperience` modelinde `revoked_at` alanı yok). Bu, F5'i doğru bir gelecek-durum sözleşmesi olarak bırakır ama şu an gerçekleştirilemez bir AC'dir — sessizce atlanmadı, `Unknowns`'a ve `Kapsam Dışı`'na açıkça yazıldı.

## Threat Model
Çağrıldı — AC-S1 (token entropisi), AC-S2 (enumeration), AC-S4 (PII/şema sızıntısı) yukarıdaki Acceptance Criteria'ya (AC-4, AC-3, AC-5) eklendi. STRIDE-lite sonucu: Spoofing/Repudiation/Elevation bu uç için uygulanmaz (auth yok, salt okuma, "yetki" kavramı capability-token modeline indirgeniyor). Asıl risk **Information Disclosure** (token brute-force/enumeration, düşük entropili token üretimi) ve düşük öncelikli **DoS** (rate-limit yok — bkz. Risks, kabul edilen risk). `authz-test` skill'i de çağrıldı; özel test matrisi aşağıda "Güvenlik Test Matrisi" bölümünde.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (geçerli token, visibility='PUBLIC') | `200` + `{"title":"string","talent_name":"string","organization_name":"string","organization_trust_level":"T1..T4","institution_name":"string veya null","started_on":"2026-06-15","ended_on":"2026-08-15","verified_at":"2026-08-20T09:12:00Z","attested_skills":[{"name_tr":"string","claim_type":"COMPETENCE","attestor_organization":"string"}]}` (plan.md Kararlar madde 1: `attestor_name` → `attestor_organization`, docs/API.md §2.9'un örneği bu noktada düzeltildi) | Yok (salt okuma) | Tek ekranda doğrulama kanıtı | AC-1 |
| 2 | Token bulunamadı | `404` + `{"code":"VERIFICATION_NOT_FOUND","message":"Kayıt bulunamadı","request_id":"uuid"}` | Yok | "Doğrulama kaydı bulunamadı" | AC-2 |
| 3 | visibility != 'PUBLIC' | `404` + AYNI `code`/`message` (satır 2 ile) | Yok | Satır 2'den ayırt edilemez | AC-3 |
| 4 | Malformed/boş token (path param) | Boşsa route eşleşmez → FastAPI'nin kendi 404'ü; doluysa DB'de bulunamaz → satır 2 ile aynı davranış | Yok | "Bulunamadı" | AC-2 |
| 5 | DB hatası | `500` + `{"code":"INTERNAL_ERROR","message":"Bir hata oluştu","request_id":"uuid"}` | Yok (transaction yok) | Genel hata sayfası | AC-7 |

Zaman aşımı: Uygulanmaz — tek basit SELECT sorgusu, dış ağ çağrısı yok.
Kısmi başarı: Uygulanmaz — tek okuma (GET) endpoint'i, atomik olarak ya tam veri ya 404/500 döner.
Hiçbir şey yapılamadı ama hata yok: Uygulanmaz — her durum ya veri ya açık hata kodu döner.
Boş sonuç ↔ hata ayrımı: N/A — bu uç tekil kaynak GET'i (liste dönmüyor), boş liste senaryosu yok.
**Uygulanmayan satır (silindi, neden burada):** "İptal edilmiş (revoked) token → 410" (docs/AUTHORIZATION.md F5) — DB'de bu durumu temsil edecek mekanizma yok, bu görevin kapsamı dışında (bkz. Kapsam Dışı, Unknowns).

## Test Strategy
Unit: 70% — token doğrulama servis mantığı (YET-124), visibility filtreleme, payload üretimi, token üretim entropisi testi.
Integration: 20% — endpoint + gerçek DB, `verified_experiences` snapshot okuma, AC-1/AC-2/AC-3/AC-7.
E2E/Authorization: 10% — 404/enumeration senaryoları, public erişim matrisi (F4/F6).

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: yok (backend-only — frontend tarafı YET-112/3.8'de ayrı, `/v/[token]` rotası)
Diğer ölçülebilir kriterler: AC-S1 — üretilen token'ın minimum karakter uzunluğu/alfabesi test edilir (entropi kanıtı olarak).

## Kapsam Dışı
- Profil düzenleme/CRUD, token üretim/paylaşım UI'ı
- Arama/filtreleme/listeleme motoru (MVP dışı — CLAUDE.md yasaklı liste)
- **Rate-limit implementasyonunun kendisi** — `docs/SECURITY.md` bunu kendi "açık soru, final analizde karar verilmemiş" notuyla işaretlemiş; bu görev rate-limit'siz teslim edilir, kabul edilen risk (bkz. Risks).
- **"İptal edilmiş (revoked) token → 410" mekanizması (F5)** — DB'de bu durumu temsil edecek kolon/mekanizma yok; bu görevde uygulanmaz, gelecek bir görev olarak `Unknowns`'a bırakıldı.
- `attested_skills` için ayrı bir servis/model değişikliği — mevcut şemadan (SkillClaim/Attestation ilişkisi) okunur, `plan` adımında netleşecek.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/alembic/versions/` (yeni migration) — `VerifiedExperience.public_token` kolonu (nullable, unique, string) — **kullanıcı onayı gerekiyor, plan adımında sorulacak**
- `backend/app/models/verified_experience.py` (değişecek) — `public_token` alanı eklenecek
- `backend/app/services/*.py` (yeni veya mevcut genişleyecek) — token doğrulama + payload üretimi (YET-124)
- `backend/app/api/public.py` (mevcut, genişleyecek) — `GET /public/v/{token}` ucu (YET-125)
- `backend/tests/test_public_verification.py` (yeni)
- `backend/tests/authorization/test_public_verification_authz.py` (yeni, YET-126 + AC-S1/S2/S4)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki görevden, YET-105) — repo kökü proje klasörüyle aynı (`yetkin360`), sınırsız arama riski yok.

## Rollback Beklentisi
Salt okuma (GET) endpoint'i — DB'ye yazma yok, rollback senaryosu yok. Migration'ın kendi rollback'i (`alembic downgrade -1`) plan/uygulama aşamasında ayrıca doğrulanmalı (CLAUDE.md kuralı).

## Risks
- **Kabul edilen risk — Rate limit yok:** `docs/SECURITY.md` bunun kendi açık sorusu olduğunu belirtiyor (önerilen: 60/dk/IP ama final analizde karar verilmemiş). Bu görev rate-limit'siz teslim edilir; token'ın yüksek entropisi (AC-S1) bu riski kısmen azaltır ama tam telafi etmez. Faz 3 sonrası veya production öncesi ele alınmalı.
- **Kabul edilen risk — Timing side-channel:** "token bulunamadı" ile "visibility != PUBLIC" sorgularının farklı sürede dönme ihtimali teorik bir enumeration kanalı oluşturabilir; YET-105'teki gibi tek sorguda (`public_token=... AND visibility='PUBLIC'`) birleştirilerek azaltılmalı — implementasyon notu, code-copilot'a aktarılmalı.
- **Migration riski:** `public_token` kolonu yeni — mevcut `VerifiedExperience` kayıtlarında bu alan NULL olacak (geriye dönük veri yok). Bu kayıtlar için doğrulama linki üretilmemiş olacak; bu görev sadece YENİ oluşturulan kayıtlar için otomatik üretim ekler, geçmiş kayıtları geriye dönük doldurma (backfill) bu görevin kapsamı dışında — `Unknowns`'a not düşüldü.

## Assumptions
- `public_token`'ın VerifiedExperience oluşturulduğunda (T8 attestation transition sırasında) otomatik üretileceği varsayıldı — "talep üzerine üretim" ayrı bir endpoint/durum yönetimi gerektirir, MVP kapsamını büyütür (Sonnet 5 low alt-ajanı tarafından yanıtlandı, migration kategorisinde olduğu için kullanıcı onayı gerekiyor, `plan` adımında sorulacak).
- `organization_trust_level` alanının `Organization.verification_level` (T1-T4) alanından geldiği varsayıldı — `plan` adımında doğrulanmalı.
- `attested_skills` listesinin kaynağı (Attestation + SkillClaim ilişkisi üzerinden) `plan` adımında kod keşfiyle netleşmeli — bu atdd.md'de tahmin edilmedi.

## Unknowns
- F5/410 (revoked token) mekanizması ne zaman/nasıl uygulanacak — ayrı bir görev mi olacak, yoksa bu görevin genişletilmiş bir versiyonu mu? Kullanıcıya sorulmalı.
- Geçmiş (mevcut) `VerifiedExperience` kayıtları için `public_token` backfill'i yapılacak mı, yoksa sadece yeni kayıtlar mı token alacak?
- `public_token` migration'ının tam şekli (nullable mı, unique constraint mi, index mi) — `plan` adımında kesinleşecek, kullanıcı onayı gerekiyor.

## Güvenlik Test Matrisi (authz-test)
Bu endpoint standart multi-tenant IDOR matrisinden farklı: "yetki" kavramı yok, "capability" (token bilme) = erişim modeli. Saldırgan kimliksiz herkes, hedef "var/yok" ve "PUBLIC/PUBLIC-olmayan" ayrımının response'tan sızmaması. `test-copilot`'a extra_instructions olarak aktarılacak:

| # | Durum | Beklenen | AC |
|---|---|---|---|
| 1 | Var olmayan token | `404` + `{code,message,request_id}` | AC-2 |
| 2 | Var olan token, visibility='PRIVATE' | `404` + satır 1 ile AYNI `code`/`message` | AC-3 (AC-S2) |
| 3 | Var olan token, visibility='INSTITUTION' | `404` + satır 1 ile AYNI `code`/`message` | AC-3 (AC-S2) |
| 4 | Var olan token, visibility='ORGANIZATIONS' | `404` + satır 1 ile AYNI `code`/`message` | AC-3 (AC-S2) |
| 5 | Var olan token, visibility='PUBLIC' | `200` + tam JSON şeması, PII/dahili alan yok | AC-1, AC-5 (AC-S4) |
| 6 | Üretilen token'ın entropisi | `secrets.token_urlsafe` (veya eşdeğeri) kullanıldığı, uzunluğun yeterli olduğu doğrulanır | AC-4 (AC-S1) |

Mock kullanılmaz — gerçek DB'ye gerçek istek atılmalı. Satır 1-4 karşılaştırması `code`/`message` tam eşitliğiyle doğrulanmalı (`request_id` her istekte farklı UUID, karşılaştırma dışı — YET-105'teki gibi).

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Kimlik doğrulamasız üçüncü taraf, "jürinin telefonundan" (docs/API.md §2.9'dan birebir)
2. Ana hedef → Zincirin dış dünyaya sunduğu tek-ekran kanıtı (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path → docs/API.md §2.9 JSON şeması (dokümandan birebir)
4. Token bulunamadı → 404 (docs/API.md'den)
5. visibility != PUBLIC → 404, F6 (docs/AUTHORIZATION.md'den birebir)
6. Revoked token → KAPSAM DIŞI, F5 gelecek iş olarak Unknowns'a yazıldı (Sonnet 5 low alt-ajanı tarafından yanıtlandı — DB'de mekanizma yok, CLAUDE.md "sessizce sapma yok" ilkesi gereği)
7. Token üretimi → migration ile yeni public_token kolonu, otomatik üretim (Sonnet 5 low alt-ajanı tarafından yanıtlandı, Assumptions'a işaretlendi, kullanıcı onayı gerekiyor)
8. Kapsam dışı → rate-limit implementasyonu, token UI, revoke mekanizması (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Test stratejisi → 70/20/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
10. Threat-model tetikleyici → Evet (Sonnet 5 low alt-ajanı tarafından yanıtlandı) → threat-model ve authz-test skill'leri bu oturumda çağrıldı, AC-S1/S2/S4 üretildi.
11. Migration gerekiyor mu → Evet, muhtemelen (Sonnet 5 low alt-ajanı tarafından yanıtlandı) — plan adımında kullanıcıya açıkça sorulacak.
12. Rate-limit → Kapsam dışı/kabul edilen risk (Sonnet 5 low alt-ajanı tarafından yanıtlandı, docs/SECURITY.md'nin kendi açık sorusuna dayanarak)
