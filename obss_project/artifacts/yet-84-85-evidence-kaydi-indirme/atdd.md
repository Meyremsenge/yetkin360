---
task_slug: yet-84-85-evidence-kaydi-indirme
jira_id: YET-68, YET-84, YET-85
saga_task_id: null
priority: critical
threat_model: done
coverage_target: 90
performance_target: "p95 < 400ms"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - api/evidence.py
  - models/evidence.py
  - models/__init__.py
  - services/storage.py
  - services/evidence.py
  - services/authorization.py (yeni scoped_evidence() eklenecek)
  - schemas/evidence.py
  - core/config.py (indirme TTL sabiti)
  - migrations/ (yeni alembic revizyonu, down_revision=i0j1k2l3m4n5 — 054f934 sonrası güncel head)
  - migrations/ (ek revizyon: evidence.deliverable_id kolonu)
  - tests/test_evidence_service.py
  - tests/authorization/test_evidence_record_download.py
  - services/audit.py (mevcut log_audit_event() kullanılacak, değiştirilmeyecek)
  - models/task_deliverable.py (mevcut Deliverable modeli, sadece okunacak/FK referans edilecek)
---

# ATDD — yet-84-85-evidence-kaydi-indirme

## Jira Kaynağı
Jira'ya canlı bağlı değil — kullanıcı tarafından yerel olarak tanımlandı (PLAN 2.6).

## Persona
Öğrenci/talent (beyan sahibi). Önceki PLAN 2.5 ucundan (`POST /evidence/upload-url`) aldığı presigned URL/POST ile dosyayı MinIO'ya zaten yükledi. Şimdi bu yüklemeyi platforma "kanıt" olarak bildiriyor (`POST /evidence`) ve daha sonra kendi kanıtını indirmek istediğinde `GET /evidence/{id}/download-url` çağırıyor.

## Hedef (Neden)
`beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirinde, MinIO'ya yüklenen ham dosya platform için "görünür" değildir — evidence kaydı olmadan tanıklık/doğrulama bu dosyaya bağlanamaz. Bu görev, PLAN 2.5'in ürettiği presigned upload'ı gerçek bir `evidence` satırına dönüştürür (final analiz §18) ve sahiplik kontrollü, kısa ömürlü imzalı URL ile güvenli indirmeyi sağlar.

## User Story
As a öğrenci/talent (beyan sahibi)
I want MinIO'ya yüklediğim dosyayı platforma kanıt olarak kaydetmek ve daha sonra sadece kendi kanıtımı güvenli şekilde indirebilmek
So that beyanımı destekleyen kanıtlar zincire dahil olsun ve başkaları tarafından erişilemesin

## MİMARİ SAPMA NOTU
Final analiz §18/§21.2'ye sapma yok. Ancak **bu görevin git geçmişinde önemli bir düzeltme oldu:**

İlk turda (`plan` adımı) `deliverables`/`engagements` tabloları kod tabanında bulunamamıştı (PLAN 2.1/2.4 henüz merge edilmemişti), bu yüzden `deliverable_id` tamamen kapsam dışı bırakılmıştı ve ilk commit (`f6c98f0`) bu haliyle push edildi. Sonrasında kullanıcı, bu commit'in **çok eski bir `main`'den** (arkadaş tarafından PLAN 2.1/2.4 merge edilmeden önceki bir noktadan) dallandığını fark etti. Kod, güncel `main` üzerine doğru şekilde taşındı (cherry-pick + conflict çözümü) ve `main`'de `Deliverable`/`Engagement` modellerinin **gerçekten var olduğu** doğrulandı — kullanıcı onayıyla `deliverable_id` geri eklendi (bu doküman güncellemesi). Detay: `code_diff.md`'nin "v2 — deliverable_id eklenmesi" bölümü.

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given kimlik doğrulanmış talent kullanıcı (kendi `storage_key`'i ile MinIO'ya dosyayı zaten yükledi), When `POST /evidence` isteğini geçerli `{storage_key, kind, mime_type, size_bytes}` ile gönderir, Then `201 Created` + evidence response şeması (`id, owner_talent_id, kind, provenance=SELF_UPLOADED, storage_key, mime_type, size_bytes, scan_status=PENDING, visibility=PRIVATE, created_at`) döner; aynı transaction içinde `outbox` tablosuna `evidence.scan_requested` topic'iyle bir satır yazılır (payload: `{evidence_id, storage_key, bucket}`).
2. [Critical] Given kimlik doğrulanmamış istek, When `POST /evidence` veya `GET /evidence/{id}/download-url` çağrılır, Then `401 Unauthorized` döner.
3. [Critical] Given `storage_key` alanı `evidence/{principal.talent_id}/...` prefix'iyle başlamıyor (başka bir talent'in prefix'i veya keyfi bir string), When `POST /evidence` çağrılır, Then `422 Unprocessable Entity` + `{error_code: "INVALID_STORAGE_KEY"}` döner (elevation defense — bkz. AC-S1).
4. [Critical] Given `deliverable_id` verilmiş ama bu deliverable'ın bağlı olduğu engagement, çağıran talent'e ait değil (başka bir talent'in engagement'ı), When `POST /evidence` çağrılır, Then `404 Not Found` döner (kaynağın varlığı sızdırılmaz — CLAUDE.md 404 kuralı). Sahiplik zinciri: `Evidence.deliverable_id → Deliverable.id → Deliverable.engagement_id → Engagement.talent_id == principal.talent_id`. **(GERİ EKLENDİ — bkz. Mimari Sapma Notu: `main`'de PLAN 2.4 tamamlanmış, `Deliverable`/`Engagement` modelleri artık gerçekten var, önceki "kapsam dışı" kararı geçersiz hale geldi.)**
5. [Critical] Given evidence kaydı sahibi talent A, When A kendi evidence'ı için `GET /evidence/{id}/download-url` çağırır ve `scan_status=CLEAN`, Then `200 OK` + `{download_url, expires_in: 300}` döner.
6. [Critical] Given evidence talent B'ye ait ve `visibility=PRIVATE`, When talent A (B değil) `GET /evidence/{id}/download-url` çağırır, Then `404 Not Found` döner (403 değil — CLAUDE.md).
7. [Critical] Given evidence `scan_status` `PENDING`, `INFECTED` veya `FAILED`, When sahibi `GET /evidence/{id}/download-url` çağırır, Then `409 Conflict` + `{error_code: "SCAN_NOT_CLEAN", scan_status: "<mevcut durum>"}` döner (dosya indirilemez — CLAUDE.md: "Tarama bitmeden indirilemez").
8. [High] Given `kind` allowlist dışında bir değer (`REPOSITORY/DOCUMENT/IMAGE/LINK/CERTIFICATE` dışı), When `POST /evidence` çağrılır, Then `422 Unprocessable Entity` (Pydantic/CHECK constraint) döner.
9. [High] Given var olmayan bir evidence `id` (UUID formatı geçerli ama kayıt yok), When `GET /evidence/{id}/download-url` çağrılır, Then `404 Not Found` döner.
10. [Medium] Given geçerli istek, When indirme URL'i üretilir, Then `expires_in` her zaman `300` (5 dakika) olur — upload'daki 900sn'den kasıtlı olarak farklı.
11. [High] Given MinIO indirme URL'i üretirken erişilemiyor (bağlantı hatası/timeout), When `GET /evidence/{id}/download-url` çağrılır, Then `503 Service Unavailable` + `{error_code: "STORAGE_UNAVAILABLE"}` döner, iç bucket/endpoint bilgisi sızdırılmaz.
12. [High] Given kimlik doğrulanmış ama talent profili olmayan kullanıcı (`principal.talent_id is None`), When `POST /evidence` çağrılır, Then `403 Forbidden` + `{error_code: "TALENT_PROFILE_REQUIRED"}` döner (PLAN 2.5 ile tutarlı persona kısıtı).
13. [Medium] Given askıya alınmış kullanıcı (`status = "SUSPENDED"`), When `POST /evidence` veya `GET /evidence/{id}/download-url` çağrılır, Then `401 Unauthorized` döner (**düzeltildi — code-copilot sonrası test çalıştırmasında bulundu**: mevcut auth katmanı `app/core/deps.py:get_current_user`, PLAN 1.x'ten beri projede tutarlı olarak `user.status not in ("PENDING", "ACTIVE")` ise zaten 401 ile reddediyor; `Principal.is_suspended` alanına ve servis/endpoint katmanındaki `403 ACCOUNT_SUSPENDED` kontrolüne bu yüzden HİÇBİR ZAMAN ulaşılamıyordu — orijinal AC-13 metni [`403 ACCOUNT_SUSPENDED`] mevcut mimariyle çelişiyordu, kullanıcıya soruldu, "atdd.md'yi gerçeğe uydur" seçildi).

AC-S1. [Critical] Given kimlik doğrulanmış talent A, When `POST /evidence` body'sinde başka bir talent'e ait `storage_key` (`evidence/{B_id}/...`) göndermeye çalışır, Then `422 INVALID_STORAGE_KEY` ile reddedilir — evidence kaydı A'nın adına asla B'nin dosyasıyla oluşturulamaz (Elevation testi).
AC-S2. [High] Given evidence talent B'ye ait, When talent A `GET /evidence/{id}/download-url` dener (PRIVATE/CLEAN farketmeksizin farklı durumlarda), Then her durumda `404` döner — `scan_status` veya `visibility` bilgisi sahiplik kontrolünden ÖNCE sızdırılmaz (yani "409 SCAN_NOT_CLEAN" cevabı sadece gerçek sahibe verilir, B'nin evidence'ına A'nın isteği önce sahiplik kontrolünden geçmeden asla 409/başka bir iç durum kodu görmez).
AC-S3. [High] Given platform admin (`is_admin`), When admin başka bir talent'in PRIVATE evidence'ı için `GET /evidence/{id}/download-url` çağırır, Then `403 Forbidden` döner (final analiz §21.2: admin için istisnai olarak 403 — "admin bile hayır" + break-glass hariç; break-glass mekanizması bu görevin kapsamı dışı).
AC-S4. [Medium] Given `POST /evidence` veya indirme ucu hata döndürür (503, 422, 409 vb.), When hata yanıtı istemciye iletilir, Then yanıt gövdesinde MinIO'nun ham hata mesajı/stack trace'i veya iç bucket/endpoint bilgisi yer almaz (Info Disclosure testi, PLAN 2.5 AC-S4 ile tutarlı).
AC-S5. [High] Given aynı kullanıcı dakikada 10'dan fazla `POST /evidence` veya `download-url` isteği gönderir, When eşik aşılır, Then `429 Too Many Requests` döner (`.claude/rules/security.md`: "Rate limit ... dosya yükleme uçlarında"; PLAN 2.5'teki `check_rate_limit` mekanizması yeniden kullanılır/genişletilir).
AC-S6. [High] Given talent A kendi evidence'ı için `GET /evidence/{id}/download-url` çağırır (başarılı, `200`), Then `audit_events` tablosuna PII/dosya-içeriği taşımayan bir satır yazılır (`actor_user_id, action="evidence.downloaded", subject_id=evidence_id, occurred_at`) — `.claude/rules/security.md`: "İndirme: kısa ömürlü imzalı URL + her indirmede yetki kontrolü + **audit**" kuralı somutlaştırıldı (Repudiation: indirmenin kim tarafından ne zaman yapıldığının izi olmadan, PRIVATE bir kanıdın kim tarafından görüldüğü hiç bilinemez).
AC-S7. [Medium] Given talent A kendi evidence'ı için `POST /evidence` çağırır (başarılı, `201`), Then aynı transaction içinde `audit_events` tablosuna bir satır yazılır (`actor_user_id, action="evidence.created", subject_id=evidence_id, occurred_at`) — oluşturma da izlenebilir olmalı (Repudiation).

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — POST /evidence | `201` + evidence response | DB: evidence satırı (`scan_status=PENDING`) + outbox satırı (`evidence.scan_requested`) + `audit_events` satırı (`evidence.created`), TEK transaction | "Kanıt kaydedildi, taranıyor" | AC-1, AC-S7 |
| 1b | Happy path — GET download-url (CLEAN) | `200` + `{download_url, expires_in: 300}` | DB: `audit_events` satırı (`evidence.downloaded`) — indirme URL üretimiyle aynı istekte, ayrı/kısa bir yazma işlemi | Dosya indirilir | AC-5, AC-S6 |
| 2 | Girdi geçersiz (`storage_key` prefix uyuşmuyor) | `422` + `{error_code: "INVALID_STORAGE_KEY"}` | Yok | "Geçersiz kanıt referansı" | AC-3, AC-S1 |
| 2b | Girdi geçersiz (`kind` allowlist dışı) | `422` (Pydantic) | Yok | Alan altı hata | AC-8 |
| 3 | Kaynak yok (evidence id bulunamadı VEYA başkasına ait PRIVATE) | `404 Not Found` | Yok | "Bulunamadı" | AC-6, AC-9 |
| 3b | Kaynak yok (deliverable_id verilmiş ama başka talent'in engagement'ına ait) | `404 Not Found` | Yok | "Bulunamadı" | AC-4 |
| 4 | Yetkisiz erişim (talent profili yok) | `403` + `{error_code: "TALENT_PROFILE_REQUIRED"}` | Yok | "Bu işlem için talent profili gerekli" | AC-12 |
| 4b | Yetkisiz erişim (admin, PRIVATE evidence) | `403 Forbidden` | Yok | "Erişim reddedildi" | AC-S3 |
| 5 | Dış bağımlılık hatası (MinIO erişilemez) | `503` + `{error_code: "STORAGE_UNAVAILABLE"}` | Yok (transaction rollback, DB'ye yazılmaz) | "Şu an kullanılamıyor, tekrar deneyin" | AC-11 |
| 6 | Zaman aşımı | 5 ile aynı (503, botocore timeout da yakalanır) | Yok | Aynı | AC-11 |
| 7 | **Kısmi başarı** (evidence INSERT başarılı ama outbox INSERT başarısız) | Uygulanmaz — **tek transaction**, ikisi birden commit veya ikisi de rollback olur (final analiz §12: "Ağ çağrısı asla açık transaction içinde yapılmaz" prensibiyle outbox'ın kendisi bir DB satırı, ağ çağrısı değil — bu yüzden aynı transaction'da güvenle yazılabilir). Silindi. | — | — | — |
| 8 | **Tarama bitmeden indirme denemesi** (scan_status PENDING/INFECTED/FAILED) | `409 Conflict` + `{error_code: "SCAN_NOT_CLEAN", scan_status}` | Yok | "Dosya henüz taranıyor / kanıt kullanılamaz" | AC-7 |

**Kısmi başarı:** Satır 7'de açıklandığı gibi uygulanmaz — evidence + outbox tek atomik transaction.
**Hiçbir şey yapılamadı ama hata da yok:** Uygulanmaz — her `POST /evidence` çağrısı ya `201` (ve outbox satırı garantili yazılmış) ya da açık bir hata koduyla sonuçlanır; sessiz no-op senaryosu mümkün değil (transaction ya commit ya rollback).
**Boş sonuç ↔ hata ayrımı:** Bu uçlar liste/koleksiyon dönmüyor (tekil kayıt oluşturma + tekil indirme URL'i), "boş sonuç" kavramı yok. Ancak "kaynak yok" (404) ile "yetkisiz" (de 404) kasıtlı olarak AYNI kod ile temsil ediliyor — CLAUDE.md'nin açık kararı (403 kaynağın varlığını sızdırır); bu iki durumun sunucu loglarında (audit_events, PII olmadan) ayrılabilir olması gerekiyor ama istemciye aynı `404` döner.

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışı içermiyor. Bölüm silindi.

## Test Strategy
Unit: 70% — `services/evidence.py` içindeki `storage_key` prefix doğrulaması (AC-3/AC-S1), `kind`/`provenance` sabitleme mantığı, `deliverable_id` sahiplik kontrolü, indirme TTL sabiti (300sn), scan_status→409 durum eşlemesi, response şeması (ORM'den Pydantic'e dönüşüm).
Integration: 20% — gerçek/test PostgreSQL ile evidence+outbox tek transaction testi (rollback senaryosu dahil), gerçek/mock MinIO ile indirme URL üretimi, auth middleware entegrasyonu, migration `upgrade`/`downgrade` doğrulaması.
E2E: 10% — kimlik doğrulanmış talent'ın tam akışı: `POST /evidence/upload-url` → (test ortamında dosya PUT simülasyonu) → `POST /evidence` → scan_status manuel CLEAN'e çekilir (test fixture) → `GET /evidence/{id}/download-url` → 200.

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: p95 < 400ms (DB round-trip: evidence + outbox tek transaction INSERT'i, PLAN 2.5'in saf hesaplama ucundan daha ağır olduğu için 300ms'den gevşetildi)
Memory: Belirtilmedi
Görsel/UI kriteri: Yok (saf backend API ucu, frontend entegrasyonu kapsam dışı)
Diğer ölçülebilir kriterler: Authorization test matrisi (§21.2) bu iki uç için eksiksiz olmalı — `pytest tests/authorization -q` tamamı geçmeli.

## Kapsam Dışı
- Gerçek magic-byte/byte-level MIME doğrulama ve virüs (ClamAV) taraması — worker'ın işi (ayrı PLAN maddesi).
- `evidence_skills` ilişkilendirmesi — ayrı bir PLAN maddesi olabilir.
- Çoklu dosya yükleme.
- Silme/versiyonlama endpoint'i (`DELETE /evidence/{id}`) — bu görev sadece kayıt oluşturma + indirme.
- `content_hash` hesaplama — worker'a ait (§18), bu API ucunda NULL bırakılır.
- `visibility` değiştirme — her zaman `PRIVATE` başlar, bu POST ucunda kullanıcı tarafından set edilemez; ayrı bir endpoint (ileride) gerekir.
- `storage_key` üzerinde idempotency/upsert mantığı (aynı key'e iki kez POST) — serbest bırakılıyor, her çağrı yeni satır oluşturur (bkz. Unknowns — belirsizlik notu, ekiple teyit önerilir).
- MinIO'ya HEAD/existence check ile dosyanın gerçekten yüklendiğini doğrulama — worker'ın indirme aşamasında doğal olarak keşfedilir (yoksa `scan_status=FAILED`).
- Admin break-glass erişim mekanizması (AC-S3'te bahsi geçiyor ama uygulanmıyor).

## Etkilenen Dosyalar/Modüller (bilinen)
- `models/evidence.py` — yeni SQLAlchemy modeli (evidence tablosu)
- `api/evidence.py` — mevcut dosyaya `POST /evidence` ve `GET /evidence/{id}/download-url` eklenir
- `services/storage.py` — indirme presigned URL üretimi (300sn TTL) eklenir
- `services/evidence.py` — yeni servis dosyası: evidence oluşturma iş mantığı, sahiplik/scan_status kontrolü (`can()`/`scoped_*()` merkezî yetkilendirme kullanılarak)
- `schemas/evidence.py` — `EvidenceCreateRequest`, `EvidenceResponse`, `EvidenceDownloadUrlResponse` eklenir
- yeni alembic migration — `evidence` tablosu (CLAUDE.md: migration için ayrıca onay alınacak)
- `tests/test_evidence_service.py`, `tests/authorization/test_evidence_record_download.py` — yeni testler

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu görev kapsamında ayrıca kontrol edilmedi. Önceki görevin (PLAN 2.5) notuyla tutarlı: sonraki adımlar (plan/code-copilot/test-copilot) arama kapsamını proje klasörüyle (`C:\Users\Meyrem\Desktop\P\yetkin360`) sınırlı tutmalı.

## Rollback Beklentisi
`POST /evidence`: evidence INSERT + outbox INSERT tek transaction'da. Herhangi biri başarısız olursa (örn. DB constraint ihlali, deliverable_id FK hatası) transaction tamamen rollback olur, evidence kaydı da outbox satırı da oluşmaz — istemci hata koduyla bilgilendirilir, tekrar deneyebilir. `GET /evidence/{id}/download-url`: DB'ye yazma yok, MinIO çağrısı başarısız olursa sadece 503 döner, rollback gereken bir durum yok.

## Risks
- **`size_bytes`/`mime_type` alanlarının MinIO'daki gerçek dosyayla tutarlılığı doğrulanmıyor (Tampering, kabul edilen risk):** İstemcinin `POST /evidence` body'sinde bildirdiği `size_bytes`/`mime_type`, presigned POST policy'sinin (PLAN 2.5, AC-S2) izin verdiği değerle aynı olmak ZORUNDA değil — MinIO sadece PUT sırasında policy'yi zorunlu kılar, bu API ucu istemcinin beyanına güvenir. Worker aşamasında gerçek magic-byte doğrulaması yapılınca (`scan_status=FAILED` olabilir) bu tutarsızlık ortaya çıkar, ama DB'deki `mime_type`/`size_bytes` alanları yanlış kalabilir. Azaltma: worker, gerçek değerleri tespit ettiğinde bu alanları güncelleyebilir — bu, worker görevinin (ayrı PLAN maddesi) kapsamına not düşülmeli.
- **`storage_key` idempotency belirsizliği (kabul edilen risk, Sonnet 5 low alt-ajanı tarafından işaretlendi):** Aynı `storage_key` ile iki kez `POST /evidence` çağrılırsa iki ayrı evidence satırı oluşur — bu MVP'de kabul edilebilir ama bir "duplicate kanıt" temizliği gerektirebilir; UNIQUE constraint eklemek bu görevin migration kapsamını büyütür, ertelendi.
- ~~`deliverable_id` sahiplik kontrolü~~ — kapsam dışına alındı (bkz. Kapsam Dışı), risk artık yok.

## Assumptions
- `storage_key` alanı, PLAN 2.5'in ürettiği `object_key` ile birebir aynı kavram — istemci `POST /evidence` body'sinde bunu (upload-url yanıtından aldığı haliyle) tekrar gönderir; server hatırlamaz (stateless HTTP).
- `provenance` bu uçta her zaman `SELF_UPLOADED` olarak sabitlenir, body'de taşınmaz.
- `content_hash` bu API ucunda hesaplanmaz, NULL bırakılır (worker'a bırakılır).
- İndirme URL TTL 300 saniye (5 dakika) — final analiz §18'de açık.
- `visibility` her zaman `PRIVATE` ile başlar, bu POST ucunda değiştirilemez.
- `scan_status` PENDING/INFECTED/FAILED → indirme `409 Conflict` döner (final analizde açık bir HTTP kodu belirtilmemiş, Sonnet 5 low alt-ajanının gerekçeli seçimi: kaynak durumu sorunu, yetki sorunu değil).
- Admin PRIVATE evidence'a erişmeye çalışırsa `403` döner (404 değil) — final analiz §21.2'de bu satır özel olarak `403` ile işaretli, genel 404 kuralının bilinçli istisnası.
- `outbox` topic'i `evidence.scan_requested`, payload `{evidence_id, storage_key, bucket}` — final analizde tanımlı değildi, bu görevde kararlaştırıldı (worker görevinde bu sözleşmeye uyulmalı).
- MinIO'ya yüklemenin gerçekten başarılı olduğunu doğrulayan bir HEAD/existence check YAPILMAZ — worker'ın indirme aşamasında doğal olarak keşfedilir.
- `storage_key` üzerinde UNIQUE constraint yok, aynı key'e tekrar POST serbest (her çağrı yeni satır).

## Unknowns
- `storage_key` idempotency/upsert davranışı ileride ayrı bir karar gerektirebilir (bkz. Risks).
- Admin break-glass mekanizmasının nasıl çalışacağı (hangi endpoint, hangi ek yetkilendirme) bu görevde tanımlı değil, ayrı bir PLAN maddesi olabilir.

## Sorular ve Cevaplar (ham kayıt)
1. Persona/akış → kullanıcı mesajından (önceki PLAN 2.5 bağlamı miras alındı)
2. object_key formatı → kullanıcı mesajından (`evidence/{talent_id}/{uuid7}.{ext}`, PLAN 2.5'te üretildi, değiştirilmedi)
3. Final analiz §18 akışı → final analiz grep ile teyit edildi (İstemci→API→evidence kaydı→outbox→worker)
4. Evidence şeması → final analiz §12.2 grep ile teyit edildi (satır 1035-1050)
5. Append-only değil → final analiz §12.3 grep ile teyit edildi (satır 1159, soft delete + 30 gün)
6. İndirme kuralları → `.claude/rules/security.md` okundu (403 değil 404, tarama bitmeden indirilemez, ana domainden servis edilmez, kısa ömürlü imzalı URL + audit)
7. Sahiplik matrisi → final analiz §21.2 grep ile teyit edildi (satır 1622-1642, admin için istisnai 403)
8. (a) POST /evidence body alanları → Sonnet 5 low alt-ajanı tarafından yanıtlandı: storage_key/kind/mime_type/size_bytes/deliverable_id zorunlu-opsiyonel, provenance body'de yok (gerekçe: stateless HTTP + sahte provenance önleme)
9. (b) outbox topic/payload → Sonnet 5 low alt-ajanı tarafından yanıtlandı: `evidence.scan_requested`, `{evidence_id, storage_key, bucket}` (gerekçe: mevcut `email.*` topic konvansiyonuyla tutarlı, worker'ın ihtiyaç duyacağı minimal alan seti)
10. (c) content_hash ne zaman → Sonnet 5 low alt-ajanı tarafından yanıtlandı: worker'da (gerekçe: API'nin dosya içeriğine erişimi yok, senkron indirme transaction içinde ağ çağrısı yasağına aykırı düşer)
11. (d) indirme TTL → final analiz §18 grep ile zaten teyitliydi: 300sn (5dk), Sonnet 5 low alt-ajanı bunu doğruladı
12. (e) visibility default/set edilebilirlik → Sonnet 5 low alt-ajanı tarafından yanıtlandı: her zaman PRIVATE, bu uçta set edilemez (gerekçe: PUBLIC yapmak ayrı, dikkatli yetkilendirme gerektiren bir işlem)
13. scan_status PENDING/FAILED/INFECTED indirme davranışı → Sonnet 5 low alt-ajanı tarafından yanıtlandı: 409 Conflict (gerekçe: kaynak durumu sorunu, yetki sorunu değil — CLAUDE.md'nin 404 kuralı burada uygulanmaz)
14. storage_key idempotency → Sonnet 5 low alt-ajanı tarafından yanıtlandı: serbest bırakılır, UNIQUE constraint yok (gerekçe: MVP'de basitlik, belirsizlik notu düşüldü)
15. MinIO HEAD/existence check → Sonnet 5 low alt-ajanı tarafından yanıtlandı: yapılmaz (gerekçe: senkron ağ çağrısı transaction kuralına aykırı düşer, worker doğal olarak keşfeder)
16. Test stratejisi → Sonnet 5 low alt-ajanı tarafından yanıtlandı: 70/20/10 (PLAN 2.5 ile tutarlılık)
17. Coverage/performans hedefi → Sonnet 5 low alt-ajanı tarafından yanıtlandı: coverage 90% aynı, performans p95<400ms'e gevşetildi (gerekçe: DB round-trip PLAN 2.5'in saf hesaplama ucundan ağır)
18. Ek kapsam dışı/dahil → Sonnet 5 low alt-ajanı tarafından yanıtlandı: deliverable_id sahiplik kontrolü DAHİL edilmeli (yetkilendirme açığı riski), diğerleri (evidence_skills, silme, çoklu dosya, magic-byte, visibility değiştirme, content_hash, idempotency) kapsam dışı
19. Threat-model tetiği → görev auth/yetkilendirme + dosya indirme/erişim + yeni HTTP endpoint içeriyor → tetiklendi, `threat-model` skill'i çağrıldı: STRIDE-lite analizi yapıldı — Spoofing (AC-2 ile zaten karşılı), Tampering (AC-S1 elevation'a giriyor + `size_bytes`/`mime_type` tutarlılığı kabul edilen risk olarak Risks'e eklendi), **Repudiation (gerçek açık tespit edildi: audit event boşluğu → AC-S6/AC-S7 somut kriterlere çevrildi, indirme VE oluşturma için `audit_events` yazımı AC'ye eklendi)**, Info Disclosure (AC-S2/AC-S4 ile karşılı), DoS (AC-S5 ile karşılı), Elevation (AC-S1/AC-S3/AC-4 ile karşılı). `threat_model: done` olarak işaretlendi.
20. Bu görev yetkilendirme AC'si (AC-S1, AC-S2, AC-S3, AC-6, AC-9) ürettiği için `authz-test` skill'i `plan`/`test-copilot` aşamasında ayrıca çağrılmalı.
21. `plan` adımında kritik bulgu: `deliverables`/`engagements` tabloları kod tabanında yok (PLAN 2.1-2.4 tamamlanmamış) → AC-4 uygulanamaz durumdaydı. Kullanıcıya soruldu → "deliverable_id'yi bu görevden tamamen çıkar" seçildi (3 seçenekten). AC-4 ve `deliverable_id` alanı atdd.md'den tamamen kaldırıldı, Kapsam Dışı'na taşındı.
