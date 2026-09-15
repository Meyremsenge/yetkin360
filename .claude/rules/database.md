---
name: Veritabanı kuralları
paths:
  - "**/models/**"
  - "**/migrations/**"
  - "**/alembic/**"
  - "**/db/**"
  - "**/*schema*.py"
---

# Veritabanı ve şema

Detay gerekirse `yetkin360-final-analiz.md` §12'yi oku (tamamını değil, ilgili alt bölümü).

## Değişmezler

- **Append-only tablolar** — `UPDATE`/`DELETE` yasak:
  `attestations`, `skill_signals`, `evaluations`, `audit_events`, `verified_experiences`
  Tek istisna: `attestations.revoked_at`/`revoke_reason` ve `verified_experiences.visibility`.
- Kısıt veritabanında olur: FK, CHECK, UNIQUE, NOT NULL. Sadece uygulama kontrolü yetmez.
- ID: UUIDv7. Artan integer yasak (enumeration + iş verisi sızıntısı).
- Zaman: `timestamptz`, UTC. Yerel saat varsayımı yasak.
- `verified_experiences` kasıtlı denormalize — kurum adı ve doğrulama seviyesi **snapshot** olarak kopyalanır.

## Silme politikası tabloya göre değişir

| Tablo | Politika |
|---|---|
| `users`, `talent_profiles` | Anonimleştirme (PII temizlenir, satır kalır) |
| `evidence` | Soft delete → 30 gün sonra dosya silinir |
| `attestations`, `verified_experiences`, `audit_events` | **Asla silinmez** |
| `engagement_tasks` | Hard delete serbest |

Prensip: **kişisel veri silinir, olgu kalır.**

## Migration

- **Her zaman geriye uyumlu**: önce ekle → sonra kullan → sonra eskisini kaldır (üç ayrı deploy)
- Uygulanmış migration **düzenlenmez/silinmez** — düzeltme = yeni migration
- Migration oluşturmadan ve uygulamadan önce **kullanıcıya sor**
- Doğrulama: `alembic upgrade head` **ve** `alembic downgrade -1` ikisi de çalışmalı

## Transaction

- Ağ çağrısı (e-posta, S3, AI) **asla açık transaction içinde** → `outbox` tablosuna yaz, worker gönderir
- Engagement → VERIFIED geçişi tek transaction: status + VerifiedExperience + SkillSignal'ler + Attestation + AuditEvent + outbox satırı
- Optimistic locking yalnız `engagements.version` üzerinde — her tabloya ekleme

## Index

Yeni sorgu yazarken index'i de düşün. Kritik olanlar:
- `(institution_id, status)` — koordinatör dashboard
- `(talent_id, skill_id, occurred_at DESC)` — profil sayfası
- `WHERE status='PENDING_EVALUATION'` — partial index, takip ekranı

Gereksiz index ekleme; yazma maliyetini artırır.
