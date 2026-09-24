# Plan — yet-72-attestation-revoke
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/authorization.py` | Yeni `scoped_attestations()` — ownership-bazlı (`attestor_user_id == principal.user_id`), mevcut `scoped_evidence()` deseniyle tutarlı | low |
| `backend/app/services/attestation.py` | Yeni `revoke_attestation()` fonksiyonu — yetki kontrolü, ALREADY_REVOKED kontrolü, tek transaction (Attestation update + tombstone SkillSignal + superseded_by_id update + AuditEvent) | medium |
| `backend/app/api/engagements.py` | `POST /attestations/{id}/revoke` route'u eklenir — mevcut `post_engagement_attestation`'ın hemen altına, aynı Pydantic request/response + HTTPException deseni | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/alembic/versions/<yeni>_add_attestations_immutability_and_revoke_exception.py` | (1) `attestations` tablosuna YENİ bir immutability trigger eklenir (şu an HİÇ trigger yok — sadece CHECK constraint'ler var), `revoked_at`/`revoke_reason` DIŞINDAKİ alanlar için UPDATE'i reddeder. (2) Mevcut `skill_signals_before_update_delete()` trigger fonksiyonu değiştirilir: `superseded_by_id` DIŞINDAKİ alanlar için UPDATE'i reddeder (şu an İSTİSNASIZ reddediyor). |
| `backend/tests/test_attestation_revoke.py` | Servis + endpoint testleri (AC-1..AC-8, AC-S1..AC-S3) |
| `backend/tests/test_attestation_revoke_authorization.py` | Yetkilendirme/ownership testleri (AC-2, AC-3, AC-S2) |

## Dependencies
- `app.services.authorization.Principal`, `get_scoped_or_404` — mevcut desen.
- `app.services.audit.log_audit_event` — AC-S1 gereği `metadata`'ya `revoke_reason` METNİ dahil edilmeyecek (mevcut `evaluation.py`'nin `private_note`'u audit'ten hariç tutma deseniyle aynı).
- `app.models.Attestation` (`revoked_at`, `revoke_reason` — zaten var, YET-70'ten), `app.models.SkillSignal` (`superseded_by_id` — zaten var).
- Route deseni: `backend/app/api/engagements.py`'deki `post_engagement_attestation` (satır ~716+) — aynı try/except → HTTPException eşlemesi, aynı 401 kontrolü.

**Trigger tasarımı (her iki migration parçası için de aynı desen — "sadece belirtilen kolon(lar) değişebilir"):**
```sql
-- attestations için:
CREATE FUNCTION attestations_before_update_delete() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'attestations is append-only (delete forbidden)';
  END IF;
  -- Sadece revoked_at/revoke_reason değişmişse izin ver, başka herhangi bir alan değiştiyse reddet
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.engagement_id IS DISTINCT FROM OLD.engagement_id
     OR NEW.talent_id IS DISTINCT FROM OLD.talent_id OR NEW.claim_type IS DISTINCT FROM OLD.claim_type
     -- ... (tüm diğer alanlar)
  THEN
    RAISE EXCEPTION 'attestations only revoked_at/revoke_reason may be updated (append-only exception)';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```
(Tam kolon listesi `code-copilot`'a bırakılıyor — `backend/app/models/attestation.py`'yi okuyup tüm kolonları sayması gerekiyor.)

## Migration Required?
**Evet, iki parça:**
1. `attestations` tablosuna yeni bir immutability trigger (şu an yok).
2. Mevcut `skill_signals_before_update_delete()` fonksiyonunun (`53299629ffe0` migration'ında oluşturulmuş) `superseded_by_id` istisnasını içerecek şekilde GÜNCELLENMESİ — `CREATE OR REPLACE FUNCTION` ile, yeni bir migration dosyasında (mevcut migration dosyası DÜZENLENMEZ, CLAUDE.md kuralı: "uygulanmış migration düzenlenmez/silinmez").

`down_revision`: mevcut tek head `k2l3m4n5o6p7` (YET-71'in migration'ı) — `alembic heads` ile doğrulanacak.

**Migration oluşturmadan/uygulamadan önce kullanıcıya sorulacak.**

## Risks
(atdd.md'den taşınan + yeni bulunan)
- **Yeni bulunan risk:** `attestations` tablosunda şu an HİÇ immutability trigger yok — bu, YET-70'te bilinçli mi bırakıldı yoksa unutuldu mu belli değil. Bu görev onu ekliyor (atdd.md'nin AC-S3'ü zaten bunu varsayıyordu). Trigger eklemek GERİYE DÖNÜK bir davranış değişikliği — mevcut Attestation satırları (YET-70/71'de oluşturulmuş test verileri hariç, gerçek üretim verisi olmadığı için düşük risk) artık UPDATE edilemez hale gelecek. Bu hackathon/MVP aşamasında sorun değil.
- `evaluations` tablosu da CLAUDE.md'de append-only listelense de HİÇ trigger yok (sadece uygulama katmanı) — bu görevin kapsamı DIŞINDA, ama tutarsızlık olarak not düşülüyor (gelecekte ayrı bir görev/temizlik maddesi olabilir).

## Open Questions
Yok — atdd.md'nin Assumptions bölümü (tombstone SkillSignal deseni) ve kod keşfi (attestations'ta trigger olmadığının doğrulanması) yeterince net, kullanıcıya sorulması gereken yeni bir belirsizlik bulunmadı.
