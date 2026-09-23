# Plan — yet-84-85-evidence-kaydi-indirme
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/api/evidence.py` | `POST /evidence` ve `GET /evidence/{id}/download-url` eklenir; mevcut `POST /evidence/upload-url` ile aynı router/dosya, aynı stil (docstring'de AC referansları, `ApiError` kullanımı, `principal.is_suspended`/`talent_id is None` kontrol sırası PLAN 2.5 ile birebir tutarlı olmalı — AC-1, AC-2, AC-5..13, AC-S1..S7) | medium |
| `backend/app/services/storage.py` | `generate_presigned_get_url(bucket, object_key, ttl)` fonksiyonu eklenir (mevcut `generate_presigned_post`'un GET karşılığı, aynı `boto3` client kurulum kalıbı, aynı `EndpointConnectionError`/`ConnectTimeoutError` yakalama) — AC-5, AC-10, AC-11 | low |
| `backend/app/models/__init__.py` | Yeni `Evidence` modeli `__all__`'a eklenir (mevcut kalıp: her model burada re-export ediliyor) | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/models/evidence.py` | `Evidence` SQLAlchemy modeli — final analiz §12.2 şeması, **`deliverable_id` kolonu HARİÇ** (kullanıcı kararı: `deliverables` tablosu yok, bu görevden tamamen çıkarıldı — bkz. atdd.md Kapsam Dışı). `id` UUIDv7 PK, `owner_talent_id` FK, `kind`/`provenance`/`scan_status` CHECK constraint'leri, `visibility` default `PRIVATE`, `deleted_at` nullable. `TimestampMixin` kullanılıp kullanılmayacağı **Open Questions**'da. |
| `backend/app/services/evidence.py` | İş mantığı: `create_evidence()` (storage_key prefix doğrulama AC-S1, evidence+outbox+audit tek transaction AC-1/AC-S7), `get_download_url()` (sahiplik+scan_status kontrolü AC-5/6/7/S2/S3, audit AC-S6) |
| `backend/app/schemas/evidence.py`'ye eklenecek: `EvidenceCreateRequest`, `EvidenceResponse`, `EvidenceDownloadUrlResponse` | Request/response DTO'ları (mevcut dosyaya eklenir, yeni dosya değil — bkz. Files to Modify'e taşınmalı, aşağıda not edildi) |
| `backend/alembic/versions/<yeni_revizyon>_add_evidence_table.py` | `evidence` tablosu migration'ı — `down_revision = '0410b8ecfed7'` (gerçek head, zincir doğrulandı). Soft-delete (append-only DEĞİL) olduğu için `audit_events` tarzı immutability trigger YOK. |
| `backend/tests/test_evidence_service.py` | Unit testler (services/evidence.py, services/storage.py'nin yeni fonksiyonu) |
| `backend/tests/authorization/test_evidence_record_download.py` | Yetkilendirme testleri (AC-S1..S3, AC-4, AC-6, AC-9) |

**Düzeltme:** `schemas/evidence.py` yeni dosya değil, mevcut dosyaya ekleme — "Files to Modify" tablosuna taşınmalı:

| File | Why | Risk |
|------|-----|------|
| `backend/app/schemas/evidence.py` | `EvidenceCreateRequest`, `EvidenceResponse`, `EvidenceDownloadUrlResponse` eklenir (mevcut `EvidenceUploadUrlRequest/Response` ile aynı dosya, aynı stil) | low |

## Dependencies
- `app.services.authorization.Principal`, `can()`, `get_scoped_or_404()` — mevcut merkezî yetkilendirme, çıplak `select(Evidence)` yasak (CLAUDE.md). **`scoped_evidence()` fonksiyonu henüz yok, bu görevde `authorization.py`'ye eklenmeli** (mevcut `scoped_talent_profiles` kalıbını takip eder: `principal.kind == "TALENT"` ise `Evidence.owner_talent_id == principal.talent_id`, aksi halde boş sonuç — admin/koordinatör dahil hiçbir rol PRIVATE evidence'ı `scoped_*` üzerinden göremez, bu CLAUDE.md'nin "PRIVATE kanıt admin'e de kapalı" kuralıyla uyumlu).
- `app.services.audit.log_audit_event(session, actor_user_id, actor_ip, action, subject_type, subject_id, result, metadata=None)` — **mevcut ve doğrudan kullanılabilir** (AC-S6/AC-S7). `subject_type="evidence"` olarak çağrılmalı.
- `app.models.outbox.Outbox` — mevcut, `topic="evidence.scan_requested"`, `payload={"evidence_id": str(id), "storage_key": ..., "bucket": settings.s3_bucket}` ile aynı transaction'da `session.add()`.
- `app.services.storage.generate_presigned_post` (mevcut) — yeni `generate_presigned_get_url` bunun yanına, aynı `boto3.client("s3", ...)` kurulum kalıbını tekrar kullanır (kod tekrarını azaltmak için ortak bir `_s3_client()` yardımcı fonksiyonuna çıkarma **düşünülebilir** ama zorunlu değil — mevcut `generate_presigned_post` da kendi client'ını kuruyor, tutarlılık için aynı kalıp izlenmeli).
- `app.core.config.settings` — `s3_bucket`, `s3_presigned_url_ttl_seconds` (upload için 900) yanına **yeni bir sabit gerekiyor**: indirme TTL'i için `evidence_download_url_ttl_seconds = 300` (veya benzeri isim) — mevcut `s3_presigned_url_ttl_seconds`'ı override etmemeli, ayrı bir config alanı.
- `app.core.deps.require_csrf` — PLAN 2.5'teki gibi state-changing (`POST /evidence`) uçta kullanılmalı; `GET /evidence/{id}/download-url` idempotent GET olduğu için CSRF gerekmeyebilir (mevcut kalıpta CSRF sadece POST'larda var) — **Open Questions'a eklendi**.

## Migration Required?
**Evet.** `evidence` tablosu final analiz §12.2 şemasıyla ilk kez oluşturuluyor. Kullanıcı onayı alındı (bu görev başlamadan önce).

- `down_revision`: `'0410b8ecfed7'` (gerçek head — zincir doğrulandı: `0410b8ecfed7` hiçbir migration tarafından `down_revision` olarak referans edilmiyor).
- CHECK constraint'ler DB seviyesinde (`kind`, `provenance`, `scan_status` — final analiz §12.2 birebir).
- FK: `owner_talent_id → talent_profiles.id` (NOT NULL). **`deliverable_id` kolonu bu migration'da YOK** (kullanıcı kararı — bkz. Open Questions #1, çözüldü).
- Index: `(owner_talent_id) WHERE deleted_at IS NULL` — final analiz §12.2'de belirtildiği gibi (`deliverable_id` index'i bu kolon olmadığı için de yok).
- `evidence` append-only DEĞİL → immutability trigger YOK (audit_events'ten farklı, outbox'a benzer mutable model).
- `alembic upgrade head` ve `alembic downgrade -1` ikisi de test edilmeli (CLAUDE.md doğrulama matrisi).

## Risks
(atdd.md'den taşınan/netleştirilen)
- `size_bytes`/`mime_type` tutarlılığı worker'a kadar doğrulanmıyor (atdd.md Risks'te zaten var, aynen taşındı).
- `storage_key` üzerinde UNIQUE constraint yok, idempotency belirsizliği (atdd.md Risks'te zaten var).
- Yeni `scoped_evidence()` fonksiyonunun `authorization.py`'ye eklenmesi — mevcut dosyada değişiklik, dikkatli yazılmalı (default-deny prensibi korunmalı, CLAUDE.md: "Yetkilendirme ... mantığı değişikliği" onay gerektiren işlemler listesinde — **code-copilot/test-copilot öncesi kullanıcıya ayrıca bildirilmeli**, zaten `authorization.py`'ye yeni fonksiyon EKLEMEK, var olanı değiştirmek değil, ama CLAUDE.md'nin ruhu gereği dikkat çekiliyor).

## Open Questions

1. ~~**[KRİTİK] `deliverable_id` FK'sinin hedeflediği `deliverables` tablosu kod tabanında yok.**~~ **ÇÖZÜLDÜ (kullanıcı kararı):** `deliverable_id` alanı bu görevden tamamen çıkarıldı — migration'da kolon yok, `POST /evidence` body'sinde kabul edilmiyor, AC-4 atdd.md'den silindi/Kapsam Dışı'na taşındı. PLAN 2.4 tamamlandığında ayrı bir migration+endpoint güncellemesiyle eklenecek.

2. **CSRF gereksinimi `GET /evidence/{id}/download-url` için var mı?** PLAN 2.5'teki `POST /evidence/upload-url` `require_csrf` kullanıyor (state-changing). `POST /evidence` de state-changing olduğu için CSRF gerekir. `GET /evidence/{id}/download-url` idempotent bir GET — mevcut kod tabanında CSRF sadece POST'larda görülüyor, GET'lerde muhtemelen gerekmez ama teyit edilmedi (`app/core/deps.py` bu görevde okunmadı, token bütçesi için ertelendi). **test-copilot aşamasında `require_csrf`'nin GET'lerde kullanılıp kullanılmadığı `app/core/deps.py`'den bir kez kontrol edilmeli.**

3. **`Evidence` modelinde `updated_at` olmalı mı?** Final analiz §12.2 şema listesinde `updated_at` kolonu yok (sadece diğer tablolarda `TimestampMixin` örnekleri var), ama `scan_status` worker tarafından güncellenecek (mutable alan) — `updated_at` olmadan "ne zaman tarandı" bilgisi kaybolur. **Öneri: `TimestampMixin` kullan (created_at + updated_at), diğer mutable tablolarla (outbox hariç, o da `processed_at` ile aynı sorunu ayrı çözmüş) tutarlı olur.** Kullanıcı onayı istenmese de code-copilot bu kararı uygulayabilir (final analiz şemasına ek, çelişki değil).

## Sonraki Adım
Açık soru #1 (deliverable_id) kullanıcıya doğrudan soruldu ve çözüldü (yukarıda). Kalan açık sorular (#2 CSRF/GET, #3 updated_at) düşük riskli, `test-copilot`/`code-copilot` sırasında çözülebilir — Sonnet 5 low alt-ajanına dispatch edilmedi çünkü ikisi de kod yazımı sırasında tek bir dosya okumasıyla netleşecek küçük kararlar (ayrı bir alt-ajan çağrısını gerektirecek belirsizlik değil).

`plan.md` ve `atdd.md` (deliverable_id kaldırılarak güncellendi) hazır. Sonraki pipeline adımı: `test-copilot` (bu plan'ın "Files to Modify"/"New Files" listesini dosya kapsamı olarak kullanacak, test-first — red step).
