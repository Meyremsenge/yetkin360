---
task_slug: yet-70-attestation-verified-experience-uretimi
jira_id: YET-70
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 90
performance_target: "p95 < 300ms (tek transaction, outbox dışarıda)"
memory_target: null
test_strategy:
  unit: 50
  integration: 40
  e2e: 10
affected_modules:
  - backend/app/models/attestation.py (yeni)
  - backend/app/models/verified_experience.py (yeni)
  - backend/app/models/skill_signal.py (source_type=ATTESTATION kullanımı)
  - backend/app/services/attestation.py (yeni)
  - backend/app/api/engagements.py (POST /engagements/{id}/attestations)
  - backend/app/services/authorization.py (can()/scoped_* — COORD/SUPERVISOR)
  - backend/alembic/versions/ (yeni migration: attestations, verified_experiences)
---

# ATDD — yet-70-attestation-verified-experience-uretimi

## Jira Kaynağı
[YET-70 — [PLAN 2.8] Attestation + VerifiedExperience üretimi (tek transaction)](https://kuyusuzyusuf123.atlassian.net/browse/YET-70)
Açıklama (Jira'dan birebir): "T8 (EVALUATED→VERIFIED): Attestation + VerifiedExperience snapshot + SkillSignal + AuditEvent tek transaction'da (STATE_MACHINE.md §5). DOMAIN.md §3.11 COMPETENCE ön koşulları."

Alt görevler:
- [YET-88](https://kuyusuzyusuf123.atlassian.net/browse/YET-88) — T8 tek transaction: Attestation + VerifiedExperience snapshot + SkillSignal + AuditEvent
- [YET-89](https://kuyusuzyusuf123.atlassian.net/browse/YET-89) — DOMAIN.md §3.11 COMPETENCE ön koşulları (6 kriter) + PARTICIPATION düşürme mantığı
- [YET-90](https://kuyusuzyusuf123.atlassian.net/browse/YET-90) — POST /engagements/{id}/attestations ucu

Atanan: Meyrem (Jira görünen adı "Meyrsem" — muhtemel yazım hatası, düzeltilmedi).

AC kaynağı (STATE_MACHINE.md §5 + DOMAIN.md §3.11 + API.md §2.8, birebir):
- T8: `EVALUATED → VERIFIED`, yetki `INST:COORD`; `institution_id` NULL ise `ORG:SUPERVISOR`.
- 6 adımlık tek transaction (STATE_MACHINE.md §5, adım 1-5 içeride, adım 6 `outbox` dışında).
- COMPETENCE 6 ön koşul (DOMAIN.md §3.11) — biri eksikse `PARTICIPATION`'a düşer, geçiş reddedilmez.
- S6/S7/S9 test senaryoları (STATE_MACHINE.md §4.x): TALENT dener → `403`; koordinatör dener → `200`; eski `version` → `409 CONFLICT`.

## Persona
Kurum koordinatörü (`INST:COORD`, üniversite bağlamında) veya doğrudan kurum süpervizörü (`ORG:SUPERVISOR`, `institution_id` NULL olan engagement'larda) — kendi panelinden, `EVALUATED` durumundaki bir engagement için tanıklık (attestation) gönderir ve böylece deneyimi doğrulanmış hale getirir.

## Hedef (Neden)
Zincirin son ve en kritik halkası: `beyan → kanıt → tanıklık → doğrulanmış deneyim`. Bu uç olmadan `Evaluation` (taraf beyanı) asla üçüncü kişilere gösterilebilir, doğrulanmış bir deneyime (`VerifiedExperience`) dönüşmez — platformun tüm değer önerisi bu adıma bağlı.

## User Story
As an `INST:COORD` (veya kurumsal bağlamda `ORG:SUPERVISOR`)
I want `EVALUATED` durumundaki bir engagement için tanıklık göndermek
So that öğrencinin deneyimi doğrulanmış (`VERIFIED`) hale gelsin ve `SkillSignal`/`VerifiedExperience` üretilsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given `EVALUATED` durumunda bir engagement, tüm COMPETENCE ön koşulları (DOMAIN.md §3.11, 6 kriter) sağlanmış, When yetkili `INST:COORD`/`ORG:SUPERVISOR` `POST /engagements/{id}/attestations` ile `claim_type: COMPETENCE` gönderir, Then `201` döner, `Attestation(claim_type=COMPETENCE)` + `VerifiedExperience` (snapshot) + `SkillSignal(source_type=ATTESTATION)` + `AuditEvent` tek transaction içinde yazılır, `engagement.status=VERIFIED` olur, `version` artar, bildirim `outbox`'a (transaction dışında değil, transaction İÇİNDE satır olarak) yazılır.

2. [Critical] Given `EVALUATED` durumunda bir engagement, COMPETENCE ön koşullarından 1+ eksik, When aynı istek gönderilir, Then `201` döner (**reddedilmez**), `Attestation.claim_type=PARTICIPATION` olarak kaydedilir, cevap gövdesi `requested_claim_type: "COMPETENCE"` ve `downgrade_reasons: [...]` içerir, `VerifiedExperience`/`SkillSignal`/`AuditEvent` yine de PARTICIPATION baz alınarak üretilir, `engagement.status=VERIFIED` olur.

3. [Critical] Given engagement `EVALUATED` durumunda değil (örn. hâlâ `ACTIVE`), When T8 tetiklenir, Then `409 CONFLICT` (`INVALID_STATE_TRANSITION`) döner, hiçbir yazma olmaz.

4. [Critical] Given istek TALENT tarafından gönderiliyor, When `POST /engagements/{id}/attestations`, Then `403` döner (STATE_MACHINE.md S6 — genel "403 değil 404" kuralının **belgelenmiş istisnası**: TALENT engagement'ın bilinen tarafı, kaynağın varlığı zaten ona görünür, sızdırılacak bir şey yok).

5. [High] Given istek, engagement'ın tarafı olmayan/başka kuruma ait bir `INST:COORD`/`ORG:SUPERVISOR` tarafından gönderiliyor, When `POST /engagements/{id}/attestations`, Then `404` döner (bu durumda genel kural geçerli — kaynağın varlığı bu aktöre sızdırılmaz).

6. [High] Given eski `version` header'ı (`If-Match`) ile eşzamanlı çakışan istek, When T8 tetiklenir, Then `409 CONFLICT` döner (`VERSION_MISMATCH`), hiçbir yazma olmaz.

7. [Medium] Given `subject_type`/`claim_type` eksik veya geçersiz enum değeri, When istek gönderilir, Then `422` döner, alan bazlı hata mesajı.

8. [Medium] Given engagement için zaten bir `Attestation` mevcut (aynı `subject_type`+`subject_id`+`attestor`), When tekrar `POST` edilir, Then `409 CONFLICT` (`ATTESTATION_ALREADY_EXISTS`) döner — append-only tablo, ikinci yazma yok.

9. [Medium] Given `institution_id IS NULL` (üniversitesiz, doğrudan kurumsal engagement), When `ORG:SUPERVISOR` T8'i tetikler, Then §3.11 madde 6 (koordinatör onayı) kontrol listesinden **çıkarılır** — bu kriter eksikliği downgrade nedeni ÜRETMEZ, sadece diğer 5 kriter değerlendirilir.

10. [Critical] **AC-S1 (Tampering)** Given istek gövdesinde `attestor_user_id` (veya benzeri kimlik alanı) saldırgan tarafından başka bir kullanıcının id'siyle doldurulmuş, When `POST /engagements/{id}/attestations` çağrılır, Then sunucu bu alanı **tamamen yok sayar** — gerçek `attestor_user_id` her zaman oturumdan (JWT/session) türetilir; kaydedilen `Attestation.attestor_user_id`, body'deki değerden bağımsız olarak oturum sahibinin id'sidir.

11. [Critical] **AC-S2 (Elevation/Tenant isolation)** Given `INST:COORD`, kendi kurumuna değil **başka bir üniversiteye** bağlı bir engagement için `POST /engagements/{id}/attestations` çağırıyor, When istek gönderilir, Then `404` döner (kaynağın varlığı bu aktöre sızdırılmaz), hiçbir `Attestation`/`VerifiedExperience`/`SkillSignal`/`AuditEvent` satırı yazılmaz — `scoped_engagements()` ile filtrelenir, çıplak `select(Engagement)` kullanılmaz.

12. [High] **AC-S3 (Tampering — self-attestation bypass)** Given attestor ile talent aynı `user_id`'ye sahip (bir kullanıcı hem kurum yetkilisi hem o engagement'ın öğrencisi), When `POST /engagements/{id}/attestations` çağrılır, Then istek DB'ye ulaşmadan **servis katmanında** reddedilir — `409 CONFLICT` (`SELF_ATTESTATION_FORBIDDEN`) döner; DB'deki `attestor_user_id != talent.user_id` CHECK constraint bu servis kontrolünün **ikinci savunma hattıdır** (constraint tetiklenirse `IntegrityError` yakalanıp aynı `409` koduna çevrilir, ham DB hatası/stack trace istemciye asla dönmez).

13. [High] **AC-S4 (Tampering — claim_type/downgrade manipülasyonu)** Given istemci `claim_type: COMPETENCE` ile birlikte istek gövdesinde var olmayan/sahte bir `deliverable_id`, `prerequisites_met: true` gibi §3.11 kontrolünü atlatmaya yönelik ek alanlar gönderiyor, When istek işlenir, Then bu ek alanlar Pydantic şemasında **tanımlı değildir ve kabul edilmez** (`extra="forbid"` veya eşdeğeri) — §3.11'in 6 kriteri **yalnızca** sunucu tarafında, o an DB'deki gerçek `Deliverable`/`Evaluation`/üyelik kayıtlarına bakılarak hesaplanır; istemciden hiçbir "ön koşul sağlandı" sinyali kabul edilmez.

14. [Critical] **AC-S5 (Race condition — çifte VERIFIED)** Given aynı `EVALUATED` engagement için iki eşzamanlı `POST /engagements/{id}/attestations` isteği (aynı `version` ile) art arda gönderiliyor, When ikisi de işlenmeye çalışılır, Then **sadece biri** `201` alır ve `version` artırır; diğeri `409 CONFLICT` (`VERSION_MISMATCH`) alır — DB seviyesinde `UPDATE ... WHERE version = X` koşuluyla korunur (evaluation.py'deki YET-69 deseniyle aynı), hiçbir koşulda iki `VerifiedExperience`/iki `VERIFIED` geçişi oluşmaz.

## Threat Model
Çağrıldı — `AC-S1`..`AC-S5` yukarıdaki Acceptance Criteria'ya eklendi (threat-model skill'i, 2026-09-24).

STRIDE-lite değerlendirmesi:
- **S**poofing: Mevcut JWT/session auth mekanizması değişmiyor — bu görevin kapsamı dışında, ayrı bir tetikleyici yok.
- **T**ampering: AC-S1 (attestor_user_id), AC-S4 (claim_type/downgrade manipülasyonu) — istemciden gelen hiçbir alana güvenilmiyor.
- **R**epudiation: STATE_MACHINE.md §5 adım 5 zaten her attestation için `AuditEvent` zorunlu kılıyor (AC-1/AC-2'de kapsanmış) — ek AC gerekmedi.
- **I**nfo disclosure: AC-5 (mevcut) + AC-S2 (cross-tenant) — 404 ile kaynak varlığı sızdırılmıyor.
- **D**oS: Bu uç tekil kaynak oluşturma (rate-limit/sayfalama konusu yok); MVP kapsamında rate-limit **kabul edilen risk** olarak bırakıldı (bkz. Risks — tek VPS, hackathon MVP, genel bir rate-limit stratejisi ayrı bir platform-seviyesi karardır, bu görevin AC'si değildir).
- **E**levation: AC-4 (TALENT→403), AC-S2 (cross-institution→404), AC-S3 (self-attestation→409) — yetki her zaman sunucuda kontrol ediliyor.

`authz-test` skill'i (AC-4, AC-5, AC-S2, AC-S3 yetkilendirme/tenant-izolasyon AC'leri ürettiği için) `plan`/`test-copilot` adımında IDOR/tenant-leakage testleri için ayrıca çağrılmalı.

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — COMPETENCE, tüm ön koşullar sağlanmış | `201` | Tek transaction: Attestation+VerifiedExperience+SkillSignal+AuditEvent+outbox satırı | `{"id":"...", "claim_type":"COMPETENCE", "requested_claim_type":"COMPETENCE", "downgrade_reasons":[]}` | AC-1 |
| 2 | Girdi geçersiz (`claim_type`/`subject_type` eksik/geçersiz enum) | `422` | Yok | `{"detail":[{"loc":["body","claim_type"],"msg":"value is not a valid enumeration member"}]}` | AC-7 |
| 3 | Engagement yok / yetkisiz aktörün erişemeyeceği kayıt | `404` | Yok | `{"detail":"Not Found"}` | AC-5 |
| 4 | Yetkisiz rol — TALENT dener | `403` (S6 istisnası — bkz. AC-4) | Yok | `{"detail":"Forbidden"}` | AC-4 |
| 5 | Engagement durumu `EVALUATED` değil | `409` | Yok | `{"detail":"INVALID_STATE_TRANSITION","current_status":"ACTIVE","expected_status":"EVALUATED"}` | AC-3 |
| 6 | Eski `version` ile çakışma | `409` | Yok | `{"detail":"CONFLICT","reason":"VERSION_MISMATCH"}` | AC-6 |
| 7 | **Kısmi başarı** — COMPETENCE istenip 1+ ön koşul eksik | `201` (reddedilmez, düşürülür) | Tek transaction: Attestation(PARTICIPATION)+VerifiedExperience+SkillSignal+AuditEvent+outbox | `{"id":"...", "claim_type":"PARTICIPATION", "requested_claim_type":"COMPETENCE", "downgrade_reasons":["NO_DELIVERABLE_FOR_SKILL"]}` | AC-2 |
| 8 | Attestation zaten var (tekrar gönderim) | `409` | Yok | `{"detail":"ATTESTATION_ALREADY_EXISTS","existing_attestation_id":"..."}` | AC-8 |

Kısmi başarı: Satır 7 — COMPETENCE isteniyor ama ön koşul eksik durumunda geçiş **asla reddedilmez**; `PARTICIPATION`'a otomatik düşürülür ve tüm zincir (VerifiedExperience/SkillSignal/AuditEvent) PARTICIPATION baz alınarak yine de tek transaction'da tamamlanır. "Hiçbir şey yapılamadı ama hata da yok" durumu bu görevde **oluşmaz** — 6 kriterden hepsi eksik olsa bile en azından PARTICIPATION seviyesinde kayıt oluşur (çünkü kriter 1, 2 asıl engagement/süre kontrolüdür ve bunlar zaten T8'in ön şartı EVALUATED olduğundan genelde sağlanmıştır); eğer kriter 1 (karşılıklı onay) bile sağlanmamışsa bu, AC-3'teki durum kontrolüne (EVALUATED olmayan engagement) denk gelir ve 409 ile zaten engellenir — dolayısıyla "PARTICIPATION'a bile düşürülemeyen" bir dal yoktur.
Boş sonuç ↔ hata ayrımı: Bu uçta liste dönmediği için (tekil kaynak oluşturma) doğrudan uygulanmaz — N/A.

## Test Strategy
Unit: 50% — özellikle §3.11'in 6 kriterinin kombinasyonel dallanması (`services/attestation.py`) ve downgrade_reasons üretimi.
Integration: 40% — gerçek DB transaction'ı (tek transaction atomikliği, append-only CHECK constraint, `attestor_user_id != talent.user_id`), migration uygulanmış şema üzerinde.
E2E: 10% — happy path (AC-1) + 403 (AC-4) + 409 version conflict (AC-6) senaryoları (STATE_MACHINE.md S6/S7/S9 ile birebir örtüşür).

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: p95 < 300ms (transaction içi 5 adım, ağ çağrısı yok — outbox okuma/gönderme ayrı süreç)
Görsel/UI kriteri: yok (bu görev backend-only, frontend ayrı bir PLAN maddesi).
Diğer: `pytest tests/authorization -q` tamamı yeşil kalmalı (yeni rol/kaynak kombinasyonu eklendiği için doğrulama matrisi genişler).

## Kapsam Dışı
- `POST /attestations/{id}/revoke` ucu — ayrı görev (YET-72/93/94, PLAN 2.10).
- `DISPUTED` durumu/akışı (T9/T10) — PLAN.md R.3, "vakit kalırsa".
- Anti-abuse cooling period (yeni kurum ilk 30 gün COMPETENCE yapamaz) ve kurum tanıklık kotası — **varsayım olarak bu görevden çıkarıldı**, ayrı takip maddesi gerekir (bkz. Assumptions).
- `downgrade_reasons` kodlarının frontend'de gösterimi — backend sözleşmesi burada sabitlenir, UI ayrı.
- Bildirim/outbox tüketicisinin (e-posta gönderimi) kendisi — sadece `outbox` tablosuna satır yazmak bu görevin kapsamında.
- `≥40 saat` eşiği — MVP'de sadece `≥4 hafta` kullanılacak (bkz. Assumptions).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/attestation.py` (yeni) — `Attestation` modeli.
- `backend/app/models/verified_experience.py` (yeni) — `VerifiedExperience` modeli (snapshot alanları).
- `backend/app/models/skill_signal.py` — `source_type=ATTESTATION` artık gerçek kullanım kazanır.
- `backend/app/services/attestation.py` (yeni) — T8 iş mantığı, §3.11 kontrolü, tek transaction.
- `backend/app/api/engagements.py` — `POST /engagements/{id}/attestations` route eklenir.
- `backend/app/services/authorization.py` — `can()`/`scoped_*()` içine COORD/SUPERVISOR + attestation kaynağı eklenir.
- `backend/alembic/versions/` — yeni migration (`attestations`, `verified_experiences` tabloları + `attestor_user_id != talent.user_id` CHECK).
- Önceki iş bağımlılığı: `backend/app/services/evaluation.py` (YET-69) — T8'in ön koşulu `EVALUATED` durumu, T7'den (evaluation.py) gelir.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu oturumda arama `backend/`, `docs/`, `obss_project/artifacts/` alt dizinleriyle sınırlı tutuldu, repo kökü dışına çıkılmadı.

## Rollback Beklentisi
Tek transaction başarısız olursa (ör. DB constraint ihlali, beklenmeyen exception) SQLAlchemy session `rollback()` ile geri alınır — `app/core/deps.py`'deki mevcut davranış (bkz. proje hafızası/postmortem notu). Kısmi yazma (Attestation var ama VerifiedExperience yok gibi) **hiçbir koşulda** commit edilmemeli — tüm 5 adım ya birlikte commit edilir ya da hiçbiri edilmez.

## Risks
- **Kabul edilen risk (DoS):** `POST /engagements/{id}/attestations` ucunda rate-limit yok — MVP/hackathon kapsamında tek VPS, genel bir rate-limit stratejisi platform-seviyesi ayrı bir karar (bu görevde AC üretilmedi, threat-model STRIDE-lite değerlendirmesinde bilinçli olarak kapsam dışı bırakıldı).
- STATE_MACHINE.md'de "Adım 6 asla transaction içinde yapılmaz" derken outbox'ı "dışında" diye tarif ediyor ama outbox'a satır yazmanın kendisi bir DB yazma işlemi — bu görevde outbox satırını da AYNI transaction içinde (adım 1-5 ile birlikte) yazıyoruz, sadece asıl bildirim gönderimi (e-posta/push) ayrı bir tüketici sürecinde oluyor. Bu yorum farkı `plan` adımında netleştirilmeli.
- 6 kriterin kombinasyonel test matrisi (2^5 = 32 downgrade kombinasyonu, kriter 6 opsiyonel) unit testlerde büyüyebilir — `plan` adımında test sayısı gerçekçi tutulmalı (tam kombinasyon yerine temsili senaryolar).

## Assumptions
- ≥4 hafta / ≥40 saat açık sorusu: **sadece ≥4 hafta** kullanılacak (varsayım — DOMAIN.md'deki "❓ AÇIK SORU" için hackathon kapsamında en deterministik seçenek; kullanıcı onayı gerekir).
- Anti-abuse cooling period (30 gün) ve tanıklık kotası **bu görevde uygulanmayacak**, ayrı bir takip maddesi olarak bırakılacak (varsayım — YET-88/89/90 kapsamı zaten geniş, MVP'nin çekirdek T8 akışını gecikmeden teslim etmek için).
- `downgrade_reasons` kod isimleri (API.md'nin "AÇIK SORU" bıraktığı liste) bu görevde ilk kez sabitleniyor: `ENGAGEMENT_NOT_MUTUALLY_CONFIRMED`, `ENGAGEMENT_DURATION_BELOW_THRESHOLD`, `NO_DELIVERABLE_FOR_SKILL`, `ATTESTOR_NOT_VERIFIED_SUPERVISOR`, `COORDINATOR_CONFIRMATION_MISSING` (kriter 5 — adıyla tanıklık — yapısal olduğu için kod üretmiyor, API şemasında zaten zorunlu alan).
- `POST /engagements/{id}/attestations` hem attestation kaydını oluşturuyor hem T8 geçişini tetikliyor — ayrı bir `/transitions` çağrısı yok (STATE_MACHINE.md'nin 6 adımlık listesiyle ve API.md §2.8'in tek uç tanımıyla tutarlı).

## Unknowns
- `Deliverable` modelinin (kriter 3 — "en az bir Deliverable var ve o yetkinliğe bağlanmış") tam şeması ve "yetkinliğe bağlanma" ilişkisinin nasıl temsil edildiği — `plan` adımında `backend/app/models/deliverable.py` (varsa) okunarak netleştirilmeli.
- `subject_type: ENGAGEMENT` dışında `EVIDENCE`/`DELIVERABLE`/`SKILL_CLAIM` durumlarının bu görevde işlenip işlenmeyeceği (DOMAIN.md `subject_type` enum'ı 4 değer listeliyor) — Jira alt görevleri sadece Engagement bağlamındaki T8'i tarif ediyor, diğer subject_type'lar `plan` adımında kapsam dışı bırakılabilir mi netleşmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Persona/rol → INST:COORD (üniversite) / ORG:SUPERVISOR (institution_id NULL) (Sonnet 5 low alt-ajanı tarafından yanıtlandı: STATE_MACHINE.md T8 satırındaki yetki tanımından birebir)
2. Ana hedef → Zincirin son halkası, doğrulanmış deneyim üretimi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path → Tek uç (POST /attestations) hem oluşturur hem T8'i tetikler (Sonnet 5 low alt-ajanı tarafından yanıtlandı: STATE_MACHINE.md §5 + API.md §2.8 tutarlılığı)
4. downgrade_reasons kodları → 5 kod üretildi (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kullanıcı onayı gerekir — Assumptions'a taşındı)
5. institution_id NULL → madde 6 kontrol listesinden çıkarılır (Sonnet 5 low alt-ajanı tarafından yanıtlandı: DOMAIN.md madde 6'nın kendi şartlaması)
6. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından dolduruldu; TALENT satırı 403→404 genel kuralına rağmen orkestratör tarafından STATE_MACHINE.md S6'ya göre 403 olarak DÜZELTİLDİ)
7. Benchmark → coverage 90%, p95<300ms (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı → revoke, DISPUTED, cooling period, UI gösterimi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Bağımlılıklar → Engagement/Evaluation/SkillSignal + yeni Attestation/VerifiedExperience (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
10. ≥4 hafta/≥40 saat → sadece ≥4 hafta (Sonnet 5 low alt-ajanı tarafından yanıtlandı, varsayım olarak işaretlendi)
11. Test oranı → 50/40/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Riskler/varsayımlar → CHECK constraint bu görevde, cooling period ayrı görevde (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kullanıcı onayı gerekir)
