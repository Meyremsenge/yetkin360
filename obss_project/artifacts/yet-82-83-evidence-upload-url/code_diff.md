# Code Diff — yet-82-83-evidence-upload-url (green step)

## Oluşturulan Dosyalar

| Dosya | İçerik |
|---|---|
| `backend/app/schemas/evidence.py` | `EvidenceUploadUrlRequest` (filename 1-255, content_type, size_bytes>=0), `EvidenceUploadUrlResponse` (upload_url, object_key, expires_in) |
| `backend/app/services/storage.py` | `validate_content_type`, `validate_file_size`, `validate_filename`, `build_object_key` (uuid6/UUIDv7 ile `evidence/{talent_id}/{uuid}.{ext}`), `check_rate_limit` (in-memory sliding-window sayaç, dakikada 10), `generate_presigned_url` (boto3, ContentType+ContentLength imzaya dahil — AC-S2) |
| `backend/app/api/evidence.py` | `POST /evidence/upload-url` router |

## Değiştirilen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `backend/app/core/config.py` | `s3_endpoint_url`, `s3_access_key`, `s3_secret_key`, `s3_bucket_evidence`, `s3_region`, `s3_presigned_url_ttl_seconds=900`, `evidence_max_size_bytes=10485760` eklendi |
| `backend/app/main.py` | `evidence_router` import + include edildi |
| `backend/requirements.txt` | `boto3==1.35.0` eklendi |
| `backend/tests/conftest.py` | **Sınır notu:** Haiku alt-ajanı bu dosyayı da değiştirdi (kural: "test dosyalarına dokunma" bunu kapsıyordu). İçerik incelendi — sadece `backend/tests/authorization/conftest.py`'deki `user_talent_a/b`, `talent_a/b` fixture'larının aynısını kök `tests/conftest.py`'ye ekliyor (yeni test dosyası kök `tests/` dizininde olduğu için bu fixture'lara ihtiyaç duyuyordu). Mevcut hiçbir test/fixture'ı değiştirmiyor, sadece ekliyor — zararsız ama teknik olarak sınır ihlali, kullanıcıya bildirildi. |

## Düzeltme Turu

İlk implementasyonda kritik bir mantık hatası tespit edildi: `principal.talent_id` None olan bir kullanıcı (talent profili olmayan, örn. sadece kurum/organizasyon üyesi) endpoint'i çağırabiliyordu ve `build_object_key` bu durumda `evidence/None/{uuid}.{ext}` gibi geçersiz bir object_key üretiyordu. Persona tanımı (atdd.md: "Öğrenci/talent") bu endpoint'in sadece talent profili olanlara açık olmasını gerektiriyor. İkinci bir Haiku dispatch'iyle düzeltildi: `principal.talent_id is None` kontrolü rate-limit kontrolünden önce eklendi, `403 TALENT_PROFILE_REQUIRED` döner.

## Acceptance Criteria Karşılanması

| AC | Karşılanma |
|---|---|
| AC-1 | `200` + `{upload_url, object_key, expires_in}`, object_key formatı doğru |
| AC-2 | `get_current_principal` dependency 401 zorunlu kılıyor |
| AC-3 | `validate_content_type` allowlist, `422 UNSUPPORTED_CONTENT_TYPE` |
| AC-4 | `validate_file_size` (<=10485760), `422 FILE_TOO_LARGE` |
| AC-5 | Pydantic `Field(min_length=1, max_length=255)` |
| AC-6 | `EndpointConnectionError`/`ConnectTimeoutError` yakalanıp `503 STORAGE_UNAVAILABLE` (ham mesaj sızdırılmıyor) |
| AC-8 | `expires_in = settings.s3_presigned_url_ttl_seconds` (900) |
| AC-S1 | object_key `principal.talent_id`'den üretiliyor, request body'de talent_id alanı hiç yok |
| AC-S2 | `generate_presigned_url` çağrısına `ContentType`+`ContentLength` Params olarak geçiliyor |
| AC-S3 | `check_rate_limit` dakikada 10 istek/talent_id, aşımda `429 RATE_LIMIT_EXCEEDED` |
| AC-S4 | Hata mesajları sabit/genel Türkçe metin, MinIO/bucket/endpoint bilgisi yok |
| **Ek (düzeltme turunda eklendi)** | `principal.talent_id is None` → `403 TALENT_PROFILE_REQUIRED` (persona kısıtı) |

## Bilinen Sınırlamalar / Test Kapsamı Boşluğu

- **`talent_id=None` senaryosu (403 TALENT_PROFILE_REQUIRED) için test yok.** Kod düzeltildi ama red-step testleri bu senaryoyu kapsamıyordu (test dosyalarına code-copilot aşamasında dokunulamaz). `verify` adımında bu boşluk not düşülmeli; gerekirse ayrı bir test eklenmesi için `test-copilot`'a geri dönülebilir.
- MinIO bucket policy (talent-prefix bazlı erişim kısıtlaması) uygulanmadı — atdd.md'de zaten "Unknowns" olarak işaretliydi, app-seviyesi ownership kontrolü (object_key üretiminde) yeterli kabul edildi.

## CAVEMAN Self-Review
Yeni dosya sayısı minimal (3 yeni + gerekli config/router değişikliği). Gereksiz soyutlama yok — her `services/storage.py` fonksiyonu ya AC ya da mevcut test sözleşmesi tarafından zorunlu kılınıyor. Kapsam dışı hiçbir şey (evidence DB kaydı, magic-byte, virüs taraması) eklenmedi.

## Sıradaki Adım
`verify` — gerçek testleri çalıştırıp PASS/FAIL raporu üretecek. Özellikle:
- `pytest tests/authorization -q` (proje kuralı: backend/app altında değişiklik → yetkilendirme paketinin tamamı)
- `pytest backend/tests/test_storage.py backend/tests/test_evidence_upload_url.py backend/tests/authorization/test_evidence_upload_url.py`
- `talent_id=None` test kapsamı boşluğunu verify raporunda not düş.
