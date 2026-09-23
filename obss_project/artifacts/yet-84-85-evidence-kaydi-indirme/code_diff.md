# Code Diff — yet-84-85-evidence-kaydi-indirme
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
| Dosya | Amaç |
|---|---|
| `backend/app/models/evidence.py` | `Evidence` SQLAlchemy modeli — final analiz §12.2 şeması (`deliverable_id` HARİÇ, kullanıcı kararı) |
| `backend/app/services/evidence.py` | İş mantığı: `create_evidence()`, `get_download_url()` |
| `backend/alembic/versions/0a1b2c3d4e5f_add_evidence_table.py` | `evidence` tablosu migration'ı — `down_revision='0410b8ecfed7'` |

## Değiştirilen Dosyalar
| Dosya | Değişiklik |
|---|---|
| `backend/app/models/__init__.py` | `Evidence` eklendi |
| `backend/app/services/storage.py` | `generate_presigned_get_url()` eklendi (kendi içinde `EndpointConnectionError`/`ConnectTimeoutError` yakalar → `ApiError(503)`) |
| `backend/app/services/authorization.py` | `scoped_evidence()` eklendi (TALENT kendi evidence'ı, admin dahil diğerleri boş sonuç) |
| `backend/app/schemas/evidence.py` | `EvidenceCreateRequest`, `EvidenceResponse`, `EvidenceDownloadUrlResponse` eklendi |
| `backend/app/api/evidence.py` | `POST /evidence`, `GET /evidence/{id}/download-url` eklendi (mevcut `POST /evidence/upload-url` değişmedi) |
| `backend/app/core/config.py` | `evidence_download_url_ttl_seconds = 300` eklendi |

Migration uygulandı: `alembic upgrade head` (kullanıcı onayı ile) — `upgrade head` ve `downgrade -1` ikisi de doğrulandı, sonra tekrar `upgrade head`.

## Review'da bulunan ve düzeltilen gerçek hatalar (code-copilot'un ilk turundan)

Alt-ajanın kendi özetine güvenmedim, her turda `git status`/`Read`/gerçek `pytest` çalıştırmasıyla bağımsız doğruladım. 3 düzeltme turu gerekti:

1. **Çıplak sorgu (CLAUDE.md ihlali):** `get_download_url()` içinde admin-403 dalı `session.query(Evidence).filter_by(...)` kullanıyordu — merkezi yetkilendirmeyi bypass ediyordu. `select(Evidence).where(...)` + `session.execute(...).scalars().first()` ile düzeltildi.
2. **Admin/talent_id çakışması:** `GET /evidence/{id}/download-url` endpoint'i `principal.talent_id is None` kontrolünü admin için istisnasız uyguluyordu — admin (tipik olarak `talent_id=None`) servise hiç ulaşamıyor, AC-S3'ün 403 FORBIDDEN dalı ölü kod kalıyordu. `principal.talent_id is None and not principal.is_platform_admin` ile düzeltildi. Rate-limit anahtarı da `talent_id or user_id` fallback'ine alındı.
3. **Kind allowlist ön-kontrolü eksikti:** `create_evidence()` geçersiz `kind` değerini DB CHECK constraint'e kadar götürüyordu, ham `IntegrityError` sızdırıyordu (AC-8 ve AC-S4 ihlali). Servis katmanına `ALLOWED_EVIDENCE_KINDS` ön-kontrolü eklendi (PLAN 2.5'in `validate_content_type()` kalıbıyla tutarlı).
4. **Ölü kod (kod tekrarı):** `storage.py`'ye MinIO hata yakalama eklenince `services/evidence.py`'deki aynı işi yapan `try/except (EndpointConnectionError, ConnectTimeoutError)` ölü kod haline geldi — kaldırıldı.

## Test dosyalarında bulunan ve düzeltilen hatalar (test-copilot'un kendi kusurları)
test-copilot aşamasında yazılan testlerde 3 kategori hata vardı (implementasyon değil, test dosyalarının kendi kusuru):
1. Yanlış import (`app.core.security` yerine `app.core.errors` olmalıydı) — 6 yer.
2. Yanlış attribute erişimi (`ApiError.error_code` yerine `ApiError.detail["code"]` olmalıydı).
3. `scan_status` alanının ayrı bir JSON alanı yerine `message` metni içinde arandığını varsayan hatalı assertion (projenin sabit `{code, message, request_id}` hata şemasıyla uyumsuzdu).
4. `audit_events` (append-only) tablosuna `DELETE` denemesi — trigger tarafından reddediliyordu, test izolasyonu `subject_id` filtresine çevrildi.

## Mimari çelişki: AC-13 düzeltildi (atdd.md güncellendi, kullanıcı onayı ile)
Orijinal AC-13 "suspended kullanıcı → 403 ACCOUNT_SUSPENDED" diyordu. Gerçek test çalıştırması, mevcut auth katmanının (`app/core/deps.py:get_current_user`, PLAN 1.x'ten beri projede tutarlı) SUSPENDED kullanıcıyı zaten `401 UNAUTHENTICATED` ile reddettiğini ortaya çıkardı — servis/endpoint katmanındaki `403 ACCOUNT_SUSPENDED` kontrolüne hiçbir zaman ulaşılamıyordu (ölü kod). Kullanıcıya soruldu → "atdd.md'yi gerçeğe uydur" seçildi. atdd.md AC-13 güncellendi, servis/endpoint'teki ölü `is_suspended` kontrolleri kaldırıldı, test 401 bekleyecek şekilde düzeltildi.

## Acceptance Criteria Doğrulaması
Tüm 19 AC (AC-1,2,3,5-13, AC-S1-S7; AC-4 kapsam dışı) test_diff.md'nin kapsama matrisiyle eşleşen testlerle karşılanıyor. Ayrıntı için test_diff.md'ye bakınız.

## Test Sonucu (bağımsız doğrulandı)
```
pytest tests/test_evidence_service.py tests/authorization/test_evidence_record_download.py -q
→ 55 passed, 0 failed

pytest -q (tüm paket, regresyon kontrolü)
→ 414 passed, 8 skipped, 0 failed
```

## CAVEMAN Uygunluğu
- 3 yeni dosya (model, service, migration) — hepsi gerekli, spekülatif değil.
- `deliverable_id` dahil edilmedi (kullanıcı kararı).
- Ölü kod bulundu ve temizlendi (2 kez: admin dalı öncesi çıplak sorgu, sonra storage.py/evidence.py hata yakalama tekrarı).
- Mevcut kod kalıpları (PLAN 2.5: `ApiError`, `validate_content_type` benzeri ön-kontrol, `scoped_*` kalıbı) takip edildi.

## Sonraki Adım
Implementasyon yeşil ve bağımsız doğrulandı. Sonraki pipeline adımı: `verify` (kalan kalite kapitleri: lint/typecheck/authz-test tam paket/security-scan vb.).
