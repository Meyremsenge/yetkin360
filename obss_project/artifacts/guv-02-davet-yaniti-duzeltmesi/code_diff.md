# Code Diff — guv-02-davet-yaniti-duzeltmesi

## Değiştirilen dosyalar
- `backend/app/api/organizations.py` — `ApiError` kullanımı, yanıt `201→202`, `{"status":"queued"}`, rol validasyonu elle (Literal DEĞİL), `AlreadyMemberError`/`ValueError` yakalanıp 202'ye çevriliyor, her ikisinde de audit.
- `backend/app/api/institutions.py` — aynı desen + AC-6 (audit event, `INVITE_INSTITUTION_MEMBER`) + outbox enqueue (yeni, `email.institution_member_invited` topic'i).
- `backend/app/services/institution.py` — `AlreadyMemberError` eklendi (organization.py'den import EDİLMEDİ, CLAUDE.md modüler kuralına uygun kendi tanımı), `invite_member()`'daki UPSERT kaldırıldı.
- `docs/API.md` — org member satırı güncellendi (`201→202`, `409 ALREADY_MEMBER` kaldırıldı), institution member ucu yeni eklendi (önceden hiç dokümante değildi).
- `backend/app/services/organization.py` — DEĞİŞMEDİ (router'ın `ValueError`'ı zaten yakalaması yeterliydi, servis tarafında değişiklik gerekmedi).

## Review sürecinde bulunan ve düzeltilen gerçek sorun
İlk implementasyonda `organizations.py`'nin `except AlreadyMemberError:` bloğu, `log_audit_event`'in `metadata` parametresine `"email": payload.email` koyuyordu. `app/services/audit.py`'nin kendi PII guard'ı (`_check_pii_in_metadata`) `email` anahtarını gördüğünde `ValueError` fırlatıyor — bu, AC-4 ("zaten üye" senaryosu) her tetiklendiğinde audit çağrısının içeride patlayıp **beklenmedik 500 hatasına** yol açacağı, CLAUDE.md'nin "loglanmaz: tam e-posta" kuralını da ihlal eden gerçek bir bug'dı. Kod incelemesiyle (bağımsız `git diff` okuması, sub-agent'ın kendi "tamamlandı" raporuna güvenilmeden) yakalandı, ikinci bir Haiku dispatch'iyle düzeltildi ve `grep` ile bağımsız doğrulandı.

## AC Eşlemesi
| AC | Nasıl karşılandı |
|---|---|
| AC-1 | Bilinen e-posta → üyelik + outbox enqueue + audit (`SUCCESS`) → `202 {"status":"queued"}` |
| AC-2 | Bilinmeyen e-posta → `ValueError` yakalanır, PII'siz audit, üyelik yok → `202 {"status":"queued"}` |
| AC-3 | `if payload.role not in (...)` elle kontrol (Pydantic Literal DEĞİL — plan.md'nin DÜZELTME notu uygulandı) → `422 ApiError{code:"INVALID_ROLE"}` |
| AC-4 | `AlreadyMemberError` yakalanır, PII'siz audit (düzeltme sonrası), rol değişmez → `202 {"status":"queued"}` |
| AC-5 | `invite_member()`'ın UPSERT'ü kaldırıldığı için zaten üye olan (tek ADMIN dahil) hiçbir şekilde rol değiştiremiyor |
| AC-6 | `institutions.py`'ye yeni `log_audit_event(..., action="INVITE_INSTITUTION_MEMBER", ...)` eklendi (önceden hiç yoktu) |
| AC-7/AC-S1 | Mevcut tenant izolasyonu (`scoped_organizations` + `org_admin_ids`) korunuyor, dokunulmadı |
| AC-8/AC-S5 | Mevcut tenant izolasyonu (`institution_admin_ids`) korunuyor, dokunulmadı |

## Red-team sonrası düzeltmeler (2. tur)
- **`organizations.py`**: `invite_org_member(...)` çağrısı kendi dar `try/except AlreadyMemberError/ValueError` bloğuna alındı; `enqueue`/başarı-audit çağrıları bu bloğun DIŞINA (`if member:`) taşındı — artık `enqueue`/`log_audit_event`'ten gelebilecek bir `ValueError` yanlışlıkla "bilinmeyen e-posta" sayılamaz.
- **`institutions.py`**: Aynı düzeltme tutarlılık için buraya da uygulandı (red-team yalnız organizations.py'yi işaretlemişti, ama institutions.py'de birebir aynı desen vardı — orkestratör tarafından fark edilip ek olarak düzeltildi).
- **`institution.py`**: `invite_member()`'ın başına `organization.py`'deki ile tutarlı rol validasyonu eklendi (`if role not in ("ADMIN","COORDINATOR"): raise ValueError(...)`) — savunma-derinliği, router zaten önce 422 döndürdüğü için normal akışta ulaşılmıyor.

Her iki turdan sonra da `pytest tests/authorization -q` (361 passed, 4 skipped) ve `pytest tests/test_organization.py tests/test_institution.py -q` (40 passed) bağımsız olarak tekrar çalıştırılıp doğrulandı; `ruff`/`mypy` temiz.

## Kalan sınırlamalar
- Davranış Sözleşmesi satır 8 (kısmi başarı: outbox enqueue aynı transaction'da başarısız) — test yazılmadığı gibi implementasyonda da özel bir dal yok; zaten transaction atomikliği (SQLAlchemy) bunu doğal olarak "hepsi ya da hiçbiri" yapıyor, ekstra kod gerekmedi.

## Varsayımlar
- Audit action ismi `"INVITE_INSTITUTION_MEMBER"` — test_diff.md'nin varsaydığı isimle birebir aynı seçildi.
- Institution invite'ın outbox topic'i `"email.institution_member_invited"` — org'daki `"email.organization_member_invited"` deseniyle tutarlı, yeni bir isim (öncesinde institution tarafında outbox hiç yoktu).

## CAVEMAN self-review
- Yeni dosya: yok.
- Yeni class: `AlreadyMemberError` (institution.py) — AC-4/AC-5 için zorunlu, organization.py'deki eşdeğerinden BAĞIMSIZ tanımlandı (modüller birbirinin iç dosyasını import etmesin kuralına uygun).
- Yeni helper fonksiyon: yok.
- Dead code/TODO: yok.
- Kapsam dışı ekleme: yok (AUTHZ-01/A-08'e dokunulmadı, davet+kabul akışı eklenmedi — atdd.md'nin kapsam dışı listesiyle tutarlı).
