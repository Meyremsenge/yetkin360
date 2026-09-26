# Plan — yet-108-toplu-hatirlatma-ucu
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/api/institutions.py` | Yeni route `POST /{institution_id}/reminders` eklenecek. Dosya zaten var (305 satır), aynı pattern zaten kullanılıyor: `invite_member_endpoint` (satır 134) institution-scope + role check + `HTTPException(404)` + `session.flush()` şablonunu birebir gösteriyor — aynı iskelet izlenecek. | low |
| `backend/app/services/authorization.py` | **Değişiklik gerekmeyebilir** — `scoped_institutions()` (satır 106) zaten `principal.kind in ("INST_ADMIN","COORDINATOR")` + `institution_id.in_(principal.institution_ids)` kontrolünü yapıyor (AC-4/AC-5/AC-S1/AC-S2 için yeterli), `scoped_engagements()` (satır 183) aynı şekilde COORDINATOR/INST_ADMIN için `institution_id.in_(principal.institution_ids)` filtresi uyguluyor (AC-3/AC-S3 için yeterli). **`code-copilot` bu iki fonksiyonu DEĞİŞTİRMEDEN, olduğu gibi çağırmalı** — yeni bir yetkilendirme dalı eklemek risklidir (mevcut yetkilendirme testlerini bozabilir). | low (sadece okunacak, değiştirilmeyecek) |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/services/reminder.py` | `create_reminders(institution_id, engagement_ids, template, actor_user_id, session) -> int` — `scoped_engagements()` ile filtreleme, her geçerli engagement için `Outbox` satırı (`topic="reminder.evaluation_pending"` veya `template` değerine göre), tek `AuditEvent` (subject_type="INSTITUTION", subject_id=institution_id, action="REMINDERS_TRIGGERED", metadata'da işlenen engagement_id listesi + template), `queued_count` döner. `attestation.py`'nin `Outbox(topic=..., payload={...})` + `session.add()` deseni birebir izlenecek (satır 369-379). |
| `backend/app/schemas/reminder.py` | `ReminderCreate` (Pydantic, `engagement_ids: list[uuid.UUID]`, `template: str`, `min_length=1` engagement_ids için — AC-2), `ReminderResponse` (`queued_count: int`) — `evaluation.py`'deki `Field(...)` konvansiyonu izlenecek. |
| `backend/tests/test_reminders.py` | AC-1, AC-2, AC-3, AC-6, AC-7 (happy path, boş dizi, cross-tenant filtreleme, tümü filtrelendi, geçersiz template). |
| `backend/tests/authorization/test_reminders_authorization.py` | AC-4, AC-5, AC-S1, AC-S2, AC-S3, AC-S6 (cross-tenant 404, rol yetersiz 404, audit_event içeriği). CLAUDE.md kuralı: her endpoint için en az 1 pozitif + 1 negatif (çapraz-kiracı) test zorunlu. |

## Dependencies
- `app.services.authorization.scoped_institutions`, `scoped_engagements`, `get_scoped_or_404`, `Principal` — DEĞİŞTİRİLMEYECEK, olduğu gibi çağrılacak.
- **`app.services.audit.log_audit_event()`** (test-copilot aşamasında keşfedildi, `attestation.py:352`'de kullanılıyor) — `AuditEvent(...)`'i DOĞRUDAN inşa etmek yerine BU fonksiyon çağrılmalı: otomatik PII guard içeriyor (`password`, `password_hash`, `email`, `tc_kimlik_no` anahtarları metadata'da varsa `ValueError` fırlatıyor). AC-S6'yı (audit'te PII olmaması) kod seviyesinde garanti eden savunma bu — sadece testte assert etmek yerine gerçek bir guard var. `code-copilot` bunu manuel `AuditEvent()` yerine kullanmalı. İmza: `log_audit_event(session, actor_user_id, actor_ip, action, subject_type, subject_id, result, metadata=None)`.
- `app.models.Outbox` — mevcut model, `attestation.py:369-379`'daki `Outbox(topic=..., payload={...})` + `session.add()` deseni izlenecek.
- `app.models.AuditEvent.event_metadata` — Python attribute adı `event_metadata` (DB kolonu `metadata`), test dosyalarında bu isimle doğru kullanılmış, `code-copilot` da bunu bilmeli (yalnız `log_audit_event()` üzerinden dolaylı kullanılacağı için doğrudan bu attribute'u set etmeyecek).
- `app.api.deps.get_current_principal`, `get_session` — mevcut dependency injection, diğer institutions.py route'larıyla aynı.
- Router zaten `app/api/institutions.py`'de mount edilmiş durumda (`main.py`'ye ekstra kayıt gerekmez — `plan` aşamasında `main.py`'de institutions router'ının zaten include edildiği görüldü, aksi belirlenirse `code-copilot` bunu ayrıca doğrulasın).

## Migration Required?
**Hayır.** ATDD'de belirtildiği gibi dedup/throttle bu görev kapsamı dışı bırakıldığı için yeni kolon/tablo gerekmiyor. `Outbox` ve `AuditEvent` tabloları zaten var ve değişmeden kullanılacak.

## Risks
- (atdd.md'den taşındı) Dedup olmadan aynı engagement için tekrar tekrar hatırlatma tetiklenebilir — kabul edilen MVP sınırlaması.
- (atdd.md'den taşındı) `engagement_ids[]` üst sınırı yok — kabul edilen DoS riski, Faz 5.6'ya bırakıldı.
- (atdd.md'den taşındı) `429` bu uçta fiilen tetiklenmeyecek (genel rate-limit altyapısı yok).
- **Yeni bulgu:** `Principal.kind` alanı "en yüksek rol" anlamına geliyor (dataclass docstring'i açıkça uyarıyor: "kind alone" per-resource karar için yeterli değil). `scoped_institutions`/`scoped_engagements` buna rağmen `kind` + `institution_ids` kombinasyonunu kullanıyor — bu KODUN MEVCUT, test edilmiş davranışı; bu görev onu değiştirmiyor, sadece tüketiyor. Teorik olarak, birden fazla kurumda farklı rolleri olan bir kullanıcı için sınır durumları olabilir ama bu önceden var olan bir mimari karar, bu PLAN maddesinin kapsamında düzeltilmeyecek.
- `template` alanının gerçek enum değerleri henüz netleşmedi (atdd.md Unknowns) — `code-copilot` bunu serbest `str` (min_length=1) olarak alacak, katı bir enum'a bağlamayacak; ileride bir enum kararlaştırılırsa ayrı görev.

## Open Questions
Yok — `plan` aşamasındaki kod keşfi, atdd.md'nin bıraktığı tüm belirsizlikleri (institutions.py var mı, hangi yetkilendirme fonksiyonları kullanılacak, migration gerekli mi) gerçek koddan doğrulayarak kapattı. Sonnet 5 alt-ajanına yönlendirilecek açık soru yok.
