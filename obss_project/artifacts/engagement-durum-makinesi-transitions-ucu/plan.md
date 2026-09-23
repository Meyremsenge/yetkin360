# Plan — engagement-durum-makinesi-transitions-ucu
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/engagement.py` | Yeni `transition_engagement(session, principal, engagement_id, to_status, version, reason=None)` fonksiyonu eklenir. Mevcut `TalentNotFoundError`/`OrganizationNotFoundError`/`InstitutionMismatchError`'a ek olarak yeni domain exception'lar gerekir: `IllegalTransitionError`, `PreconditionFailedError`, `TransitionForbiddenError`, `VersionConflictError`, `EngagementNotFoundError` (404 için — mevcut `TalentNotFoundError`/`OrganizationNotFoundError` bu anlama gelmiyor, karışıklık olur) | medium |
| `backend/app/api/engagements.py` | Yeni route `POST /{id}/transitions` — request/response DTO'ları, yeni exception→HTTP kodu eşlemesi (422/403/404/409) | medium |
| `backend/app/services/authorization.py` | **Dokunulmaz** — mevcut `scoped_engagements()` zaten fetch+404-vs-no-access ayrımını çözüyor (`get_scoped_or_404` ile). Geçiş-özel yetki kontrolü (institution_id/organization_id eşleşmesi + transition tablosu) `engagement.py`'nin kendi servis fonksiyonunda kalır — `can()`'a yeni bir Engagement case eklemek gerekmez çünkü karar transition tablosuna (kimin hangi status→status yapabileceği) bağlı, tekil bir action/resource çiftine değil. **Not: atdd.md'nin affected_modules'ünde bu dosya olarak listelenmişti, kod keşfinde gereksiz olduğu görüldü — düzeltildi.** | low |
| `backend/tests/authorization/test_matrix.py` | Yeni transition-özel testler (403/404 ayrımı, version conflict) | low |

## New Files
Yok — mevcut `engagement.py`/`engagements.py` dosyalarına eklenir (yeni dosya açmak CAVEMAN'a aykırı, tek bir küçük entity'nin ikinci bir işlemi).

## Dependencies
- `app.services.authorization.scoped_engagements()`, `get_scoped_or_404()` — kaynağı çekmek ve 404-vs-no-access'i tek adımda çözmek için (mevcut, `app/services/authorization.py:154-167`)
- `app.services.audit.log_audit_event()` — her geçişte zorunlu AuditEvent
- `app.services.outbox.enqueue(session, topic, payload)` — bildirim kuyruğu (mevcut, `app/services/outbox.py:64`). **`reason` alanı payload'a KONULMAMALI** — `enqueue()`'nun PII guard'ı `private_note`/`token`/`email` gibi sabit anahtarları yakalıyor ama serbest metin `reason`'ı yakalamaz, aynı önlem `create_engagement`'taki `title`/`description` kararıyla tutarlı olmalı.
- `Engagement` modeli (mevcut, `status`/`version` kolonları zaten var)
- Optimistic locking: SQLAlchemy `session.execute(update(Engagement).where(Engagement.id==id, Engagement.status==expected_status, Engagement.version==expected_version).values(status=new_status, version=Engagement.version+1))` deseni — ORM `session.flush()` ile obje üzerinden `version` artırmak yerine **doğrudan `UPDATE ... WHERE`** kullanılmalı, çünkü ORM'nin "load-then-save" deseni kendi başına race condition'a karşı korumasızdır (iki eşzamanlı istek aynı ORM objesini yükleyip ikisi de kendi version'ını +1 yapabilir). `result.rowcount == 0` → `VersionConflictError` (409).

## Migration Required?
**Hayır** — `engagements.status`/`engagements.version` kolonları ve CHECK kısıtı PLAN 2.1'de zaten var (kod keşfinde teyit edildi: `app/models/engagement.py`, `status` CHECK 10 değer içeriyor, `version` NOT NULL server_default 1).

## Risks
- (atdd.md'den taşındı) Rate limiting yok — kabul edilen risk.
- (atdd.md'den taşındı) `reason` serbest metin — outbox/audit payload'ına konulmamalı.
- **Yeni bulunan risk:** ORM'nin `session.flush()` ile obje-yükle-değiştir-kaydet deseni optimistic locking'i YANLIŞ uygular (iki eşzamanlı istek aynı satırı okuyup ikisi de "başarılı" görebilir, SQLAlchemy'nin `version_id_col` mekanizması kullanılmıyorsa). Bu görevde ham `UPDATE ... WHERE status=... AND version=...` + `rowcount` kontrolü kullanılmalı — bu, `create_engagement`'ın kullandığı `session.add()`+`session.flush()` deseninden FARKLI bir desen, code-copilot'a açıkça belirtilmeli.
- **Yeni bulunan risk:** 5 yeni domain exception sınıfı (`IllegalTransitionError` vb.) `create_engagement`'ın kullandığı 3 exception'a ek geliyor — dosyanın karmaşıklığı artıyor ama transition tablosunun kendisi (STATE_MACHINE.md §4.3) 5 farklı HTTP kodu istiyor, azaltılamaz (CAVEMAN gerekçesi: her kod farklı bir gerçek durumu temsil ediyor, birleştirilirse istemci doğru mesajı gösteremez).

## Open Questions
Yok.
