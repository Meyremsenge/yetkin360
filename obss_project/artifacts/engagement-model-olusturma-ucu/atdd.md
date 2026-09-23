---
task_slug: engagement-model-olusturma-ucu
jira_id: null
saga_task_id: null
threat_model: done
priority: critical
coverage_target: 80
performance_target: "<200ms"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/alembic/versions/ (yeni migration)
  - backend/app/models/engagement.py (yeni)
  - backend/app/services/engagement.py (yeni)
  - backend/app/api/engagements.py (yeni)
  - backend/app/main.py (router include)
  - backend/app/core/authorization.py (can()/scoped_engagements() — Engagement case eklenir)
  - backend/tests/authorization/test_matrix.py ("YET-7 pending" notlarının kapatılması)
---

# ATDD — engagement-model-olusturma-ucu

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (PLAN.md 2.1). Saga MCP bu ortamda mevcut değil (bağlı değil) — `saga_task_id: null`.

## Persona
- **TALENT** (öğrenci): kendi stajı/projesi için engagement başlatır.
- **ORG:MEMBER** (organizasyon üyesi): kendi organizasyonunda bir talent adına engagement başlatır.
(kullanıcı mesajından: docs/API.md §2.6 — "ORG:MEMBER veya TALENT")

## Hedef (Neden)
Engagement, `beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirinin başlangıç noktası. Bu uç olmadan zincir hiç başlamaz — kanıt, tanıklık, attestation, verified experience hepsi bir engagement'a bağlanır. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: zincirin ilk halkası olduğu gerekçesiyle)

## User Story
As a talent veya organizasyon üyesi
I want yeni bir engagement (staj/proje) kaydı oluşturmak
So that çalışma platformda takip edilip sonunda doğrulanmış deneyime dönüşebilsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçerli `talent_id` (kendi talent_profile'ı veya çağıranın org'una ait), `organization_id` (çağıranın üyesi olduğu org), `kind` (CHECK kümesinden), `title`, When `POST /engagements` çağrılır, Then `201` döner, `status: "DRAFT"`, `version: 1`, DB'ye tek satır INSERT edilir, aynı transaction'da `audit_event` yazılır.
2. [Critical] Given `title=""` veya `kind` CHECK kümesi dışında bir değer, When `POST /engagements` çağrılır, Then `422` döner (Pydantic/FastAPI validation), DB'ye dokunulmaz.
3. [Critical] Given `talent_id` veya `organization_id` sistemde hiç yok, When `POST /engagements` çağrılır, Then `404` döner, DB'ye dokunulmaz.
4. [Critical] Given TALENT rolündeki kullanıcı, kendi `talent_id`'si dışında başka bir talent_id ile engagement açmaya çalışır, When `POST /engagements` çağrılır, Then `404` döner (**403 değil** — proje kuralı, kaynak varlığı sızdırılmaz).
5. [High] Given `institution_id` verilmiş ama bu değer `talent_profiles.institution_id` ile eşleşmiyor, When `POST /engagements` çağrılır, Then `400` döner (iş kuralı ihlali — kaynak yok değil, geçersiz kombinasyon).
6. [Critical] (AC-S1) Given TALENT rolündeki A kullanıcısı, When body'de B kullanıcısının `talent_id`'si gönderilirse, Then `404` döner, hiçbir engagement satırı oluşmaz.
7. [Critical] (AC-S2) Given ORG:MEMBER rolündeki Org A üyesi, When body'de üyesi olmadığı Org B'nin `organization_id`'si gönderilirse, Then `404` döner, hiçbir engagement satırı oluşmaz.
8. [High] (AC-S3) Given herhangi bir principal, When `institution_id` principal'ın gerçek `talent_profile.institution_id`'siyle eşleşmiyorsa, Then `400` döner ve response body institution'ın var olup olmadığını ayırt eden bilgi (ör. "kurum bulunamadı" vs "kurum eşleşmiyor") içermez — tek tip mesaj.
9. [Medium] (AC-S4) Given `confidential: true` gönderilmiş bir istek başarısız olursa (400/404/422), Then hata response'unda veya sunucu loglarında `title`/`description` içeriği yer almaz.

## Threat Model
Çağrıldı — AC-S1..AC-S4 yukarıdaki Acceptance Criteria'ya eklendi (STRIDE-lite: Tampering — `talent_id`/`organization_id`/`institution_id` client'tan gelir, server-side scoped kontrol zorunlu; Elevation — yetki `can()`/`scoped_engagements()` ile sunucuda kontrol edilir, rol adı UI'da değil; Info disclosure — 404-not-403 kuralı ve institution eşleşme mesajı sızıntı yapmaz). Spoofing ve Repudiation mevcut auth/audit altyapısı tarafından zaten karşılanıyor, yeni AC gerektirmedi. DoS (rate limit) kabul edilen risk olarak Risks bölümüne yazıldı. Yetkilendirme AC'leri üretildiği için `test-copilot`/`plan` aşamasında `authz-test` skill'i de çağrılmalı (IDOR/tenant-leakage kalıbı).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | `201` + `{"id":"...","talent_id":"...","organization_id":"...","institution_id":null,"kind":"INTERNSHIP","title":"...","status":"DRAFT","version":1,"created_at":"2026-09-22T10:00:00Z"}` | `engagements` tablosuna 1 satır INSERT + aynı tx'te `audit_event` | Yeni engagement objesi | AC-1 |
| 2 | Girdi eksik/geçersiz (`title=""`, `kind="FOO"`) | `422` + `{"detail":[{"loc":["body","kind"],"msg":"value is not a valid enumeration member","type":"value_error"}]}` | Yok | Alan bazlı hata listesi | AC-2 |
| 3 | `talent_id`/`organization_id` sistemde yok | `404` + `{"detail":"Not found"}` | Yok | Genel "bulunamadı" | AC-3 |
| 4 | TALENT başkasının `talent_id`'siyle dener | `404` (403 DEĞİL) + `{"detail":"Not found"}` | Yok | Kaynak yokmuş gibi görünür | AC-4, AC-S1 |
| 5 | ORG:MEMBER üyesi olmadığı `organization_id` ile dener | `404` + `{"detail":"Not found"}` | Yok | Kaynak yokmuş gibi görünür | AC-S2 |
| 6 | `institution_id` talent'a bağlı değil | `400` + `{"detail":"institution_id does not match talent's institution"}` | Yok | Tek tip iş kuralı hatası | AC-5, AC-S3 |
| 7 | Dış bağımlılık hatası (DB bağlantı hatası) | `500` + genel hata mesajı, iç detay sızdırılmaz | `audit_event` YAZILMAZ — `get_session` exception'da rollback yapar, hiçbir şey commit edilmez | "Sunucu hatası, tekrar deneyin" | — |

Kısmi başarı: engagement INSERT + audit_event INSERT **aynı transaction'da** yapılır. Biri başarısız olursa `get_session`'ın exception-üzerinde-rollback davranışı yüzünden **tüm transaction geri alınır** — engagement DB'de görünmez, retry güvenlidir. Ayrı/erken commit YOK; tek commit sınırı fonksiyonun sonunda.

Hiçbir şey yapılamadı ama hata da yok: Bu uç için böyle bir senaryo **yok** — create idempotent değildir, her çağrı ya `201` ya bir `4xx/5xx` döner. Sessiz no-op riski yok (satır silinmedi, sadece bu uçta uygulanamaz olduğu için).

Boş sonuç ↔ hata ayrımı: Bu bir create ucu, boş sonuç kavramı yok — ya kaynak oluşur (201) ya oluşmaz (4xx/5xx net kodla).

## Test Strategy
Unit: 70% — servis katmanı iş kuralları (CHECK eşlemeleri, sahiplik kontrolü, institution eşleşmesi, 404-vs-400 ayrımı)
Integration: 20% — DB + auth akışı (gerçek session, gerçek can()/scoped_engagements())
E2E: 10% — tek happy-path (kayıt → login → POST /engagements → 201)

## Benchmark / Başarı Ölçütü
Coverage Target: 80% (services/)
Performance Target: <200ms (proje genel backend hedefi — engagement'a özel ayrık eşik dokümanlarda yok)
Memory: —
Görsel/UI kriteri: yok (bu görev backend-only, frontend 2.11'de)
Diğer: `pytest tests/authorization -q` tamamı yeşil kalmalı (mevcut 71 passed + bu görevle YET-7 skip'lerinden ilgili olanlar unskip edilip geçmeli)

## Kapsam Dışı
- `GET /engagements`, `GET /engagements/{id}` (okuma uçları — ayrı ele alınacak, bu görev sadece POST)
- `POST /engagements/{id}/transitions` (durum makinesi — PLAN 2.2)
- Task/Deliverable (PLAN 2.4)
- Dosya yükleme/Evidence (PLAN 2.5)
- Frontend engagement ekranları (PLAN 2.11)
- Rate limiting (kabul edilen risk, aşağıda)

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/alembic/versions/` — yeni migration (`engagements` tablosu, CHECK kısıtları, index'ler: `(organization_id,status)`, `(talent_id,status)`, `(institution_id,status)`, partial `(status) WHERE status='PENDING_EVALUATION'`)
- `backend/app/models/engagement.py` (yeni ORM modeli)
- `backend/app/services/engagement.py` (yeni — iş mantığı burada, router'da değil)
- `backend/app/api/engagements.py` (yeni router, `POST /engagements`)
- `backend/app/main.py` (router include)
- `backend/app/core/authorization.py` — `can()`/`scoped_engagements()` içine Engagement case'i (docs/AUTHORIZATION.md §2'de tanımlı, kodda "YET-7 pending" olarak skip edilmiş durumda)
- `backend/tests/authorization/test_matrix.py` — ilgili skip notlarının kapanması (satır 469, 501, 509 civarı — "Engagement model and scoped_engagements() not yet implemented")

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposu kökü proje klasörü mü yoksa daha geniş bir dizin mi net değil. Sonraki adımlarda (plan/code-copilot/test-copilot) arama `yetkin360/` ile sınırlı tutulmalı, kök dizinden sınırsız `grep -r`/`git log -p --all` çalıştırılmamalı.

## Rollback Beklentisi
Hata durumunda DB'de kalıntı kalmaz — `get_session` her exception'da `session.rollback()` yapar, engagement + audit_event tek transaction'da yazılır (bkz. Davranış Sözleşmesi "Kısmi başarı" satırı). Bu, 2026-09-22 postmortem koşumunda tespit edilen "flush edilmiş ama commit edilmemiş veri sessizce kaybolabilir" riskine karşı **açıkça tek-transaction, tek-commit-sınırı** tasarlanmıştır — servis fonksiyonu ara `flush()` yapıp sonra farklı bir koşulda hata fırlatmamalı.

## Risks
- **Rate limiting yok**: `POST /engagements` için MVP'de rate limit uygulanmıyor — 1.6'daki `/auth/forgot-password` kararıyla tutarlı (Faz 5.2/5.6 kapsamına bırakıldı, final analiz §39 MVP dışı listesiyle uyumlu). Kabul edilen risk, kasıtlı.
- `scoped_engagements()` bu görevle ilk kez yazılacak — docs/AUTHORIZATION.md §2'de tanımı var ama kod tarafında hiç yok (test_matrix.py'de "pending" skip). İlk implementasyon riski taşır, authz-test ile doğrulanmalı.

## Assumptions
- `institution_id` doğrulaması `talent_profiles.institution_id` tek (nullable) FK alanı üzerinden yapılır — M:N ilişki değil (docs/DOMAIN.md §3.2, doğrulandı, alt-ajanın öne sürdüğü "net değil" varsayımı yanlıştı, düzeltildi).
- AUTHORIZATION.md'deki "POST /engagements — kim başlatabilir?" açık sorusu, kullanıcının onayıyla STATE_MACHINE.md/API.md lehine çözüldü: ORG:MEMBER veya TALENT ikisi de oluşturabilir.
- `Engagement.kind` enum'u DOMAIN.md'nin 4 değeri (`INTERNSHIP|CAPSTONE|SHORT_PROJECT|PART_TIME`) esas alınarak düzeltildi; docs/DATABASE.md bu görev başlamadan önce güncellendi (kullanıcı onayıyla).

## Unknowns
- `planned_hours`, `supervisor_user_id`, `started_on`/`ended_on` alanlarının bu ilk create isteğinde zorunlu mu opsiyonel mi olduğu API.md'de net değil (DOMAIN.md nullable diyor) — nullable/opsiyonel kabul edildi, create sırasında zorunlu tutulmuyor.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Talent kendi stajı için başlatır (birincil), ORG:MEMBER de aynı ucu kullanabilir (Sonnet 5 low alt-ajanı tarafından yanıtlandı: API.md + STATE_MACHINE.md tutarlılığı gerekçesiyle)
2. Ana hedef/neden → Zincirin başlangıç noktası, bu uç olmadan zincir çalışmaz (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path → yukarıdaki JSON örneği (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
4. Edge case'ler (FK yok / institution eşleşmesi / yetkisiz talent_id) → yukarıdaki AC-3/4/5 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Davranış sözleşmesi tablosu → yukarıda, tam doldurulmuş (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
6. Benchmark → coverage ≥80%, <200ms p95 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: proje genel varsayımı)
7. Kapsam dışı → yukarıda listelendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Bağımlılıklar → yukarıda listelendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Güvenlik kısıtı → confidential alanı loglanmaz, sahiplik kontrolü zorunlu (Sonnet 5 low alt-ajanı tarafından yanıtlandı) — threat-model adımında AC-S1..S4'e genişletildi
10. Rollback → get_session rollback garantisi, kalıntı kalmaz (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Kabul kriteri sahibi → otomatik test (pytest tests/authorization) yeterli (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Test stratejisi → 70/20/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı, proje varsayımı)
13. institution_id ilişki şeması → talent_profiles.institution_id tek FK (kullanıcı/kod tabanından doğrulandı, alt-ajanın varsayımı düzeltildi)
14. Engagement.kind enum çelişkisi (DOMAIN.md vs DATABASE.md) → kullanıcı DOMAIN.md'yi (4 değer) onayladı, DATABASE.md düzeltildi
15. threat-model tetikleyici → var (auth/yetkilendirme, kullanıcı girdisi, çok-kiracılı sınır) → AC-S1..S4 üretildi
