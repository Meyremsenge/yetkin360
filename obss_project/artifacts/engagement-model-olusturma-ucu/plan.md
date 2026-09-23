# Plan — engagement-model-olusturma-ucu
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, "Etkilenen Dosyalar" ve "Görsel/UI kriteri" boş).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | Yeni `Engagement` modelini export listesine ekle (bkz. mevcut `SkillClaim` deseni) | low |
| `backend/app/main.py` | Yeni `engagements` router'ını `include_router` ile bağla (bkz. `institutions_router` deseni, main.py:7,25) | low |
| `backend/app/services/authorization.py` | `scoped_engagements()` fonksiyonu eklenir (docs/AUTHORIZATION.md §2'de tanımlı, kodda hiç yok — `test_matrix.py`'de "YET-7 pending" skip'li). `Principal.talent_id`/`org_ids`/`institution_ids` zaten mevcut, ek alan gerekmiyor. `can()`'a Engagement case eklenmez — create işlemi ownership kontrolünü servis katmanında (aşağıda) yapar, `can()` yalnız read/admin_update gibi var-olan-kaynak eylemlerinde kullanılıyor (mevcut desende User/Organization/Institution örnekleri gibi) | medium — merkezi yetkilendirme dosyası, `pytest tests/authorization -q` tamamı bu değişiklikten sonra tekrar çalıştırılmalı |
| `backend/tests/authorization/test_matrix.py` | Satır ~469, 501, 509 civarındaki "YET-7 pending: Engagement model and scoped_engagements() not yet implemented" skip'leri kaldırılıp gerçek assertion'a çevrilir | medium |

**Not (atdd.md'deki hatalı yol düzeltmesi):** atdd.md'nin `affected_modules`'ünde `app/core/authorization.py` yazıyordu — gerçek dosya **`app/services/authorization.py`**. Kod keşfinde düzeltildi, code-copilot bu düzeltilmiş yolu kullanmalı.

## New Files
| File | Purpose |
|------|---------|
| `backend/alembic/versions/<hash>_add_engagements_table.py` | `engagements` tablosu: CHECK kısıtları (`kind`, `status`, `ended_on>=started_on`), 4 index (`(organization_id,status)`, `(talent_id,status)`, `(institution_id,status)`, partial `(status) WHERE status='PENDING_EVALUATION'`), FK'ler (`talent_profiles`, `organizations`, `institutions` nullable, `users` nullable) |
| `backend/app/models/engagement.py` | `Engagement` ORM modeli (mevcut `app/models/skill_claim.py` deseniyle: `Base`, `TimestampMixin`, tablo adı `engagements`) |
| `backend/app/services/engagement.py` | İş mantığı: `create_engagement(session, principal, payload)` — sahiplik kontrolü (talent_id/organization_id/institution_id), `log_audit_event` çağrısı (mevcut `app/services/audit.py`), domain exception'lar (`TalentNotFoundError`, `OrganizationNotFoundError`, `InstitutionMismatchError` — `skill_claim.py`'deki `SkillNotFoundError` deseniyle) |
| `backend/app/api/engagements.py` | `POST /engagements` router'ı — Pydantic request/response DTO'ları, `{code, message, request_id}` hata gövdesi deseni (mevcut `app/api/talent_skills.py` deseniyle, **atdd.md'deki `{"detail":"..."}` şekli YANLIŞ — düzeltildi**) |

## Dependencies
- `app.api.deps.get_current_principal`, `get_session` (mevcut, `talent_skills.py`'de kullanılan desen)
- `app.services.authorization.Principal`, yeni `scoped_engagements()`
- `app.services.audit.log_audit_event` — aynı transaction'da audit event için (PII guard'lı, `title`/`description` gibi serbest metin alanları `metadata`'ya KONULMAMALI — audit.py'nin PII guard'ı sadece password/email/tc_kimlik_no'yu yakalıyor, serbest metin sızıntısı servis kodunda elle önlenmeli)
- `app.models.identity.TalentProfile`, `Organization`, `Institution` — sahiplik/eşleşme kontrolü için (`TalentProfile.institution_id` tek FK, atdd.md'de doğrulandı)

## Migration Required?
**Evet.** Yeni `engagements` tablosu — CLAUDE.md kuralı gereği migration oluşturma/uygulama **açık onay** gerektirir (bu plan.md onayı bunu kapsamaz, ayrıca sorulacak).

## Risks
- (atdd.md'den taşındı) Rate limiting yok — kabul edilen risk, MVP kapsamı.
- (atdd.md'den taşındı) `scoped_engagements()` ilk kez yazılıyor — authz-test ile doğrulanmalı.
- **Yeni bulunan risk:** `app/services/authorization.py` merkezi dosya; buraya dokunmak `tests/authorization/test_matrix.py`'deki **tüm** diğer aktörlerin testlerini de etkileyebilir (import hatası/syntax hatası tüm suite'i kırar) — değişiklik küçük ve izole (yeni fonksiyon eklemek, var olanı değiştirmemek) olmalı.
- **Yeni bulunan risk:** `audit.py`'nin PII guard'ı yalnız sabit anahtar listesini (`password`, `email`, `tc_kimlik_no`) kontrol ediyor — `title`/`description` gibi serbest metin alanlarını audit `metadata`'sına hiç koymamak servis kodunun sorumluluğu (guard bunu yakalamaz).

## Open Questions
Yok.
