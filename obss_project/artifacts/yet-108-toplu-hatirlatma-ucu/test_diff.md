# Test Diff — yet-108-toplu-hatirlatma-ucu
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar
- `backend/tests/test_reminders.py` (yeni)
- `backend/tests/authorization/test_reminders_authorization.py` (yeni)

Durum: **RED (beklenen)** — `backend/app/api/institutions.py`'de `POST /{institution_id}/reminders`
route'u, `backend/app/services/reminder.py` ve `backend/app/schemas/reminder.py` henüz yok.
Testler ya import hatası ya da `404 route not found` ile başarısız olacak. Bu görev bu aşamada
testleri ÇALIŞTIRMADI (verify aşamasının işi) — dosyaların diskte doğru yerde olduğu ve AC
kapsamının eksiksiz olduğu doğrulandı (presence check).

## AC → Test Eşlemesi

| AC | Test dosyası | Test fonksiyonu |
|---|---|---|
| AC-1 (happy path) | test_reminders.py | `test_happy_path_single_engagement_202`, `test_happy_path_multiple_engagements_202` |
| AC-2 (boş/eksik engagement_ids) | test_reminders.py | `test_empty_engagement_ids_400`, `test_missing_engagement_ids_field_400` |
| AC-3 (cross-institution kısmi başarı) | test_reminders.py | `test_partial_success_cross_institution_202` |
| AC-4 (cross-tenant path → 404) | test_reminders_authorization.py | `test_coordinator_different_institution_404` |
| AC-5 (yetkisiz rol → 404) | test_reminders_authorization.py | `test_talent_cannot_trigger_reminders_404`, `test_org_member_cannot_trigger_reminders_404` |
| AC-6 (tümü filtrelendi → 202/0) | test_reminders.py | `test_all_filtered_202_zero_queued` |
| AC-7 (geçersiz template → 400) | test_reminders.py | `test_empty_template_400`, `test_missing_template_400` |
| AC-S1 (id enumeration — var/yok 404 farkı yok) | test_reminders_authorization.py | `test_same_404_for_nonexistent_and_foreign_institution` |
| AC-S2 (rol yükseltme → 404) | test_reminders_authorization.py | `test_role_elevation_attempt_talent_to_coordinator_404` |
| AC-S3 (id enumeration — queued_count sızıntısı yok) | test_reminders_authorization.py | `test_id_enumeration_defense_queued_count_reveals_scope`, `test_id_enumeration_cross_institution_engagement_silent_filter` |
| AC-S6 (audit'te PII yok) | test_reminders_authorization.py | `test_audit_event_no_pii_on_successful_reminder_trigger` |
| — (pozitif kontrol, CLAUDE.md zorunluluğu) | test_reminders_authorization.py | `test_positive_case_coordinator_can_trigger_reminders_202`, `test_positive_case_institution_admin_can_trigger_reminders_202` |

Davranış Sözleşmesi satır 7 (kısmi başarı) → `test_partial_success_cross_institution_202`.
Davranış Sözleşmesi satır 8 (hiçbir şey yapılamadı, hata yok) → `test_all_filtered_202_zero_queued`.

**Kasıtlı olarak test edilmeyen (atdd.md kararı):** institution-level throttle (429),
engagement-level dedup, `engagement_ids[]` üst sınırı — hiçbiri hiçbir kaynakta tanımlı değil,
bu görev bunları uygulamıyor (bkz. atdd.md "429/dedup/cap doğrulama sonucu").

## Presence-check bulguları (kalite incelemesi değil)
- `test_happy_path_single_engagement_202` outbox `topic` değerini `("reminder.evaluation_pending", "reminder")` olarak esnek kabul ediyor — atdd.md'de topic adı sabitlenmedi, bu kabul edilebilir bir esneklik.
- `AuditEvent.event_metadata` attribute adı testlerde doğru kullanılmış (modelde doğrulandı: Python attribute `event_metadata`, DB kolonu `metadata`).
- `InstitutionMember.role` alanı testlerde `"COORDINATOR"`/`"ADMIN"` olarak kullanılmış — `backend/app/models/identity.py`'deki CHECK constraint ile eşleşiyor (alt-ajan raporunda doğrulandı).
- AC-6 testinde (`test_all_filtered_202_zero_queued`) outbox kaydı olmadığı doğrulanıyor ama audit_event'in de oluşmadığı ayrıca assert edilmemiş (atdd.md satır 8 "yan etki: yok" diyor) — küçük bir kapsama boşluğu, `code-copilot`/`verify` aşamasında not düşülebilir, engelleyici değil.

## Sıradaki Adım
`code-copilot` — bu testleri yeşile çıkaracak implementasyonu yazacak (`backend/app/services/reminder.py`,
`backend/app/schemas/reminder.py`, `backend/app/api/institutions.py`'ye yeni route). `plan.md`'nin
güncellenmiş "Dependencies" bölümüne göre `AuditEvent`'i doğrudan değil `app.services.audit.log_audit_event()`
üzerinden kullanmalı (otomatik PII guard içeriyor).
