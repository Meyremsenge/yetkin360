# Plan — yet-82-83-evidence-upload-url
_Reference: atdd.md_

## Codebase Bulguları (mevcut kalıplar)

- **Router kaydı:** `backend/app/main.py` her modülün router'ını `app.include_router(...)` ile elle ekliyor (auth, institutions, organizations, skills). Yeni `evidence_router` aynı şekilde eklenecek.
- **Endpoint kalıbı:** `backend/app/api/skills.py` — router `APIRouter(prefix="/...", tags=[...])`, dependency injection ile `get_current_principal` (auth) + `get_session` (DB) alıyor, hata için `app.core.errors.ApiError(status_code, code, message)` fırlatıyor (main.py'deki `api_error_handler` bunu `{code, message, request_id}` şekline çeviriyor — atdd.md'deki `error_code` alanı bu `code` alanına karşılık geliyor, isimlendirmeyi buna göre hizala).
- **Auth/Principal:** `backend/app/api/deps.py` → `get_current_principal` gerçek JWT (httpOnly cookie) doğrulamasından `Principal` üretiyor; `principal.talent_id` zaten `TalentProfile` tablosundan çekiliyor. **AC-S1 (elevation) doğrudan bununla karşılanır** — `owner_talent_id` body'den değil `principal.talent_id`'den alınacak, ekstra kod gerekmez, sadece body'de böyle bir alan hiç tanımlanmamalı.
- **Config:** `backend/app/core/config.py` — `pydantic-settings` `Settings` sınıfı, `.env`'den okuyor, secret'lar için default yok. Yeni S3/MinIO ayarları aynı sınıfa eklenecek (`s3_endpoint_url`, `s3_access_key`, `s3_secret_key`, `s3_bucket_evidence`, `s3_region` opsiyonel). `docker-compose.yml`'de zaten `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PORT`, `S3_CONSOLE_PORT` env değişkenleri kullanılıyor — isimlendirmeyi bunlarla tutarlı tut.
- **Şema kalıbı:** `backend/app/schemas/skill.py` — sade Pydantic `BaseModel`, response şemaları ayrı sınıf (ORM asla direkt dönülmüyor — CLAUDE.md kuralına zaten uyuluyor). Request şeması için ayrı bir dosyada (`schemas/evidence.py`) hem request hem response modeli tanımlanacak.
- **UUID üretimi:** `uuid6` paketi zaten `requirements.txt`'de var (UUIDv7 için, CLAUDE.md "ID: UUIDv7" kuralı) — `object_key` üretiminde bu kullanılacak, yeni bağımlılık gerekmiyor.
- **MinIO client:** Backend kodunda **hiç MinIO/S3 client kullanımı yok** (`boto3`/`minio` paketi `requirements.txt`'de yok). `docker-compose.yml`'de MinIO servisi çalışıyor (S3 API uyumlu) ama backend'den hiç bağlanılmamış. **Yeni bağımlılık eklenmesi gerekiyor** → CLAUDE.md "Bağımlılık ekleme... için önce açık onay al" kuralı devreye giriyor (bkz. Open Questions).
- **Rate limiting:** Projede hiçbir yerde rate limiting mekanizması yok (`rate limit`, `429`, `Too Many Requests` için tüm backend'de sıfır eşleşme). Redis yasaklı (CLAUDE.md kapsam listesi). AC-S3 için basit bir in-memory veya DB-tabanlı sayaç yazılması gerekecek — bu da projede ilk kez kurulacak bir mekanizma.
- **Migration ihtiyacı:** Bu görev evidence DB kaydı yapmıyor (kapsam dışı, PLAN 2.6), dolayısıyla **migration gerekmiyor.** Rate-limit sayacı DB-tabanlı seçilirse (Redis yerine) yeni bir küçük tablo gerekebilir — bu da migration onayı gerektirir (aşağıda açık soru).

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/main.py` | Yeni `evidence_router`'ı `app.include_router(...)` ile ekle | low |
| `backend/app/core/config.py` | S3/MinIO ayarlarını (`s3_endpoint_url`, `s3_access_key`, `s3_secret_key`, `s3_bucket_evidence`, `s3_presigned_url_ttl_seconds=900`, boyut sınırı `evidence_max_size_bytes=10485760`, allowlist) `Settings` sınıfına ekle | low |
| `backend/requirements.txt` | `boto3` ekle (kullanıcı onayladı) | medium |

## New Files

| File | Purpose |
|------|---------|
| `backend/app/api/evidence.py` | `POST /evidence/upload-url` router — `skills.py` kalıbını takip eder (Depends(get_current_principal), Depends(get_session), ApiError ile hata) |
| `backend/app/services/storage.py` | İş mantığı: content_type allowlist kontrolü, size_bytes kontrolü, filename validasyonu, `object_key` üretimi (`evidence/{talent_id}/{uuid7}.{ext}`), MinIO presigned PUT URL üretimi (Content-Type + Content-Length koşuluyla — AC-S2), rate-limit sayaç kontrolü (AC-S3) |
| `backend/app/schemas/evidence.py` | `EvidenceUploadUrlRequest` (filename, content_type, size_bytes) + `EvidenceUploadUrlResponse` (upload_url, object_key, expires_in) |
| `backend/tests/test_storage.py` | Unit testler: allowlist, boyut sınırı, filename validasyonu, object_key formatı (≥%90 coverage hedefi) |
| `backend/tests/authorization/test_evidence_upload_url.py` | Yetkilendirme testleri: 401 (kimliksiz), AC-S1 (body'de farklı talent_id gönderilse bile kendi `principal.talent_id`'si kullanılır) |
| `backend/tests/test_evidence_upload_url.py` | Integration testler: happy path (mock MinIO), MinIO bağlantı hatası → 503, 422 senaryoları (content_type/boyut/filename), rate-limit 429 |

## Dependencies

- `app.api.deps.get_current_principal`, `get_session` — mevcut, değişmeyecek.
- `app.core.errors.ApiError` — mevcut hata şekli korunacak (`code` alanı atdd.md'deki `error_code` ile eşleştirilecek, örn. `UNSUPPORTED_CONTENT_TYPE`, `FILE_TOO_LARGE`, `STORAGE_UNAVAILABLE`).
- `app.core.config.settings` — yeni S3 alanları buraya eklenecek, `services/storage.py` bunları okuyacak.
- `uuid6` (zaten mevcut) — `object_key`'deki UUIDv7 üretimi için.
- **Yeni:** `boto3` (S3 presigned URL üretimi standart yolu) — henüz projede yok.

## Migration Required?
**Hayır** (evidence DB kaydı bu görevde yapılmıyor, PLAN 2.6'ya ait). Ancak rate-limit sayacı DB-tabanlı seçilirse küçük bir migration gerekebilir — kullanıcı onayına bağlı (bkz. Open Questions, seçenek B).

## Risks
- (atdd.md'den taşındı) Content-Type/Content-Length spoofing riski → AC-S2 ile ele alınacak, `boto3`'ün `generate_presigned_post` (sadece PUT değil, koşullu POST policy) veya `generate_presigned_url` + imzalı header koşulları kullanılmalı — implementasyon detayı `code-copilot` aşamasında netleşecek.
- (atdd.md'den taşındı) MinIO bucket policy'sinin talent-prefix erişim kısıtlaması henüz doğrulanmadı — bu görev kapsamında sadece object_key'in path'i doğru üretilecek, bucket-policy (IAM) seviyesinde kısıtlama ayrı bir altyapı görevi olabilir; **bu görev sadece uygulama-seviyesi kontrolü (her kullanıcı sadece kendi prefix'i için URL alabilir) sağlar, MinIO'nun kendisi başka bir kullanıcının prefix'ine yazılan bir presigned URL'yi engellemez (çünkü URL zaten doğru prefix ile imzalanmıştır) — bu risk kabul edilebilir, çünkü zaten doğru talent_id ile imzalanıyor.**
- Yeni bağımlılık (`boto3`) — paket boyutu ve bakım yükü getirir; alternatif olarak daha hafif `minio` SDK'sı da değerlendirilebilir (aşağıda soru).

## Kararlar (kullanıcı onayladı)

1. **Bağımlılık: `boto3`.** `requirements.txt`'e eklenecek — presigned URL üretimi için `boto3`'ün S3 client'ı (`endpoint_url` ile MinIO'ya yönlendirilir).
2. **Rate limiting altyapısı: in-memory sayaç.** Basit `dict` + zaman penceresi (tek-VPS/tek-process MVP varsayımıyla). Migration gerekmiyor. Not: process restart'ta sıfırlanır, çoklu uvicorn worker'da tutarsız olabilir — MVP'de kabul edilebilir risk olarak atdd.md Risks bölümüne eklenmeli.
3. **Rate limit eşiği: dakikada 10 istek/kullanıcı.**

Bu kararlarla migration ihtiyacı kalmadı — "Migration Required?: Hayır" kesinleşti (rate-limit için DB tablosu seçeneği elendi).
