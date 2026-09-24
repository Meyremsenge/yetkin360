# Code Diff — yet-72-attestation-revoke

## Oluşturulan Dosyalar
- `backend/alembic/versions/l3m4n5o6p7q8_add_attestations_immutability_and_revoke_exception.py` — (1) `attestations` tablosuna yeni immutability trigger (`revoked_at`/`revoke_reason` istisnasıyla), (2) `skill_signals_before_update_delete()` fonksiyonu `CREATE OR REPLACE` ile güncellendi (`superseded_by_id` set-once istisnasıyla). **Uygulandı** (`alembic upgrade head` + `downgrade -1` + re-upgrade, hepsi PASS).

## Değiştirilen Dosyalar
- `backend/app/services/authorization.py` — yeni `scoped_attestations()` (ownership-bazlı, kullanılmıyor ama gelecekte faydalı olabilir diye bırakıldı).
- `backend/app/services/attestation.py` — `AttestationNotFoundError`, `RevokeForbiddenError`, `AttestationAlreadyRevokedError` exception sınıfları + `revoke_attestation()` fonksiyonu.
- `backend/app/api/engagements.py` — yeni `attestations_router` (prefix `/attestations`), `POST /{attestation_id}/revoke` route'u.
- `backend/app/main.py` — `attestations_router` kaydedildi.

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar
Bkz. `verify_report.md`'nin "Coverage / Quality Notes" bölümü — özet: çıplak `select()` + 403/404 bilgi sızıntısı (kritik güvenlik), yanlış router prefix (routing bug), 26 yerde gereksiz `session.expunge_all()` (test bug), tombstone testinin skill_id vermemesi + `AuditEvent.occurred_at` yanlış alan adı, mypy Optional uyuşmazlığı.

## AC Karşılanması (özet)
AC-1..AC-8, AC-S1..AC-S3 — tek transaction (Attestation update + tombstone SkillSignal + superseded_by_id + AuditEvent), engagement-scope üzerinden 403/404 ayrımı, race-safe UPDATE WHERE revoked_at IS NULL, revoke_reason metni audit'e yazılmıyor.

## CAVEMAN Self-Review
Yeni dosya sayısı minimum (1 migration) — mevcut `evaluation.py`/`attestation.py` deseniyle tutarlı, ekstra soyutlama yok.
