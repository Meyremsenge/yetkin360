# Plan — yet-70-attestation-verified-experience-uretimi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | Yeni `Attestation`/`VerifiedExperience` modellerini export'a ekle (mevcut `Evaluation`/`EvaluationItem` deseniyle aynı) | low |
| `backend/app/services/authorization.py` | `scoped_attestations()` (varsa okuma ucu için, bu görevde sadece yazma var — gerekmeyebilir), `can()`'a Attestation/VerifiedExperience resource dalları eklenmez çünkü scope kontrolü `scoped_engagements()` üzerinden zaten yapılıyor (AC-S2) | low |
| `backend/app/api/engagements.py` | `POST /engagements/{id}/attestations` route'u eklenir — mevcut `post_engagement_evaluation`'ın hemen altına, aynı desenle (Pydantic request/response modelleri + HTTPException eşlemeleri) | medium |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/models/attestation.py` | `Attestation` modeli — append-only, `attestor_user_id != talent.user_id` CHECK (kısıt migration'da), `claim_type`/`requested_claim_type` alanları |
| `backend/app/models/verified_experience.py` | `VerifiedExperience` modeli — snapshot alanları (kurum adı, tarih, rol — canlı FK değil, düz metin/kopya) |
| `backend/app/services/attestation.py` | T8 iş mantığı: §3.11 6 kriter kontrolü, downgrade_reasons üretimi, tek transaction (Attestation+VerifiedExperience+SkillSignal+AuditEvent+Outbox+Engagement.status güncellemesi) |
| `backend/alembic/versions/<yeni>_add_attestations_and_verified_experiences.py` | Yeni tablolar: `attestations`, `verified_experiences` + CHECK constraint'ler + index'ler |
| `backend/tests/test_attestation.py` | Servis katmanı testleri (AC-1/2/3/7/8/9, downgrade kombinasyonları) |
| `backend/tests/test_attestation_authorization.py` | Yetkilendirme/tenant-izolasyon testleri (AC-4, AC-5, AC-S1..AC-S5) |

## Dependencies
- `app.services.authorization.Principal`, `get_scoped_or_404`, `scoped_engagements` — YET-69'daki (`evaluation.py`) desenle birebir aynı: engagement önce `scoped_engagements()` ile çekilir, `None` ise `EngagementNotFoundError` → API'de 404.
- `app.services.audit.log_audit_event` — AuditEvent yazımı için (evaluation.py'deki kullanım birebir kopyalanacak).
- `app.services.outbox` — bildirim satırı için (mevcut servis fonksiyonunu incelemek gerekiyor, muhtemelen `enqueue()` benzeri bir yardımcı var; yoksa doğrudan `Outbox` modeliyle `session.add()`).
- `app.models.Engagement` (`status`, `version`, `institution_id`, `organization_id`, `supervisor_user_id`, `talent_id`) — T8 geçişinin ana kaynağı.
- `app.models.identity.Organization` (`verification_level`, `verified_at`) — §3.11 kriter 4 (attestor ≥T2 doğrulanmış kurum) kontrolü için.
- `app.models.task_deliverable.Deliverable` (`engagement_id`) — §3.11 kriter 3 (en az bir Deliverable var) kontrolü için. **Not:** `Deliverable`'ın "o yetkinliğe bağlanmış" ilişkisi (bir skill_id ile) şu an modelde YOK (`Deliverable`'da `skill_id` alanı yok, sadece `title`/`description`/`engagement_id`). Bu bir **Open Question** (aşağıda).
- `app.models.skill_signal.SkillSignal` (`source_type=ATTESTATION` artık gerçek kullanım kazanıyor).
- Route deseni: `backend/app/api/engagements.py`'deki `post_engagement_evaluation` (satır 552-660 civarı) — aynı `try/except` → `HTTPException` eşleme deseni, aynı 401 kontrolü, aynı `session.commit()` çağrısı.
- **Version alanı:** atdd.md'de `If-Match` header varsayılmıştı ama gerçek proje deseni (`post_engagement_transitions`, satır 248-363) `version`'ı **request body**'de alıyor (`TransitionEngagementRequest.version`), header değil. Bu görev de aynı deseni kullanacak — atdd.md'deki AC-6/AC-S5'in "version" referansı body alanı olarak yorumlanacak (davranışı değiştirmiyor, sadece taşıma yeri; kullanıcıya ayrıca sorulmuyor çünkü proje-genelinde zaten tek bir tutarlı desen var).

## Migration Required?
**Evet.** Yeni `attestations` ve `verified_experiences` tabloları (§3.11/§5'in gerektirdiği append-only tablolar, CLAUDE.md §"Veri" listesinde zaten adı geçiyor).

İçerik:
- `attestations`: `id` (UUIDv7 PK), `engagement_id` (FK), `subject_type` (CHECK: EVIDENCE|DELIVERABLE|ENGAGEMENT|SKILL_CLAIM), `subject_id`, `claim_type` (CHECK: PARTICIPATION|CONTRIBUTION|COMPETENCE|CONDUCT — gerçekleşen), `requested_claim_type` (aynı CHECK, istemcinin istediği — düşürme öncesi), `attestor_user_id` (FK users), `attestor_org_id` (FK organizations, nullable), `skill_id` (FK skills, nullable), `statement` (nullable text), `downgrade_reasons` (JSONB, nullable — düşürülmediyse boş liste), `revoked_at`/`revoke_reason` (nullable — bu görevde yazılmaz, YET-93/94 için şimdiden kolon açılır), `created_at`.
  - `CheckConstraint("attestor_user_id != talent.user_id")` — **doğrudan kolonlar arası CHECK olarak yazılamaz** çünkü `talent.user_id` başka tablodan; bu kısıt DB seviyesinde ancak bir trigger veya `talent_id`'yi de attestations tablosuna denormalize edip `CHECK(attestor_user_id != talent_user_id)` şeklinde eklenerek uygulanabilir. **Open Question** (aşağıda) — `plan` bunu netleştirmeden `code-copilot` bu kısmı yanlış yorumlayabilir.
- `verified_experiences`: `id` (UUIDv7 PK), `talent_id` (FK), `engagement_id` (FK), `organization_name_snapshot`, `role_snapshot`, `started_on_snapshot`, `ended_on_snapshot`, `institution_name_snapshot` (nullable), `claim_type` (o an ki, PARTICIPATION/COMPETENCE), `visibility` (CHECK: PRIVATE|PUBLIC vb. — tek mutable alan, DOMAIN.md D6/D9), `created_at`.

Migration `down_revision`: mevcut tek head `ee96f63a4231` (`merge skill_signals and evaluation branches`) — doğrulandı (`alembic history` çalıştırıldı, tek head).

**Migration oluşturmadan/uygulamadan önce kullanıcıya sorulacak** (CLAUDE.md kuralı — bu adımda henüz oluşturulmadı, `code-copilot`/uygulama aşamasında ayrıca onay istenecek).

## Risks
(atdd.md'den taşınan + yeni bulunanlar)
- **Outbox transaction yorumu netleşti:** `.claude/rules/database.md` açıkça "Engagement → VERIFIED geçişi tek transaction: status + VerifiedExperience + SkillSignal'ler + Attestation + AuditEvent + outbox satırı" diyor — atdd.md'deki risk notu (outbox'ın transaction içinde mi dışında mı olduğu) bu proje kuralıyla **çözüldü**: outbox satırı transaction İÇİNDE yazılır (asıl e-posta gönderimi ayrı worker'da, dışarıda).
- 6 kriterin kombinasyonel test matrisi büyük olabilir — `test-copilot`'a temsili senaryolar (happy path, tek kriter eksik ×5, hepsi eksik) yazması, tam 2^5 kombinasyon değil, talimatı verilecek.
- `Deliverable` modelinde `skill_id` alanı yok (bkz. Open Questions) — kriter 3'ün tam anlamıyla uygulanması bu görevde MVP ölçüsünde basitleştirilebilir.

## Open Questions

1. **`Deliverable` ↔ skill ilişkisi yok.** DOMAIN.md §3.11 kriter 3 "en az bir Deliverable var ve **o yetkinliğe bağlanmış**" diyor, ama mevcut `Deliverable` modelinde (`task_deliverable.py`) `skill_id` kolonu yok — sadece `engagement_id`, `title`, `description`. MVP için şu iki seçenekten biri seçilmeli:
   (a) Kriter 3'ü basitleştir: "engagement'ta en az 1 Deliverable var" (skill'e bağlı olma kontrolü atlanır, `NO_DELIVERABLE_FOR_SKILL` yerine `NO_DELIVERABLE` kodu kullanılır),
   (b) Bu görevde `Deliverable`'a nullable `skill_id` FK kolonu ekleyen küçük bir ek migration yapılır.

2. **`attestor_user_id != talent.user_id` CHECK constraint nasıl uygulanır?** SQL CHECK constraint'ler aynı tablo içindeki kolonlar arasında çalışır, cross-table değil. Seçenekler:
   (a) `attestations` tablosuna `talent_id` kolonu da denormalize edilir (zaten `VerifiedExperience`'da snapshot mantığı var, tutarlı olur) → `CHECK(attestor_user_id != talent_user_id)` doğrudan yazılabilir,
   (b) DB trigger (`BEFORE INSERT`) ile `talent_profiles`/`engagements` join'i üzerinden kontrol,
   (c) Sadece servis katmanında kontrol (DB CHECK yok) — ama bu, CLAUDE.md'nin "kısıtlar veritabanında olur, sadece uygulama kontrolü yetmez" kuralına aykırı.
   **Öneri: (a)** — en basit ve mevcut snapshot desenine en uygun.

3. `downgrade_reasons` JSONB mi yoksa ayrı bir `attestation_downgrade_reasons` tablosu mu (çoklu kod için)? **Öneri: JSONB liste** (`["NO_DELIVERABLE_FOR_SKILL", ...]`) — append-only bir satırda birden fazla kodu tutmak için normalize tablo gereksiz karmaşıklık (CAVEMAN ilkesi).

Kullanıcıya sorulacak: yukarıdaki 1(a) vs 1(b) ve 2(a) tercih onayı — geri kalanı (3) düşük riskli, öneriyle devam edilebilir.

## Kararlar (kullanıcı onayıyla)
1. **Deliverable-skill ilişkisi:** Seçenek (a) — basitleştirilmiş kontrol. Kriter 3 sadece "engagement'ta ≥1 Deliverable var" olarak uygulanır, `skill_id` kolonu eklenmez, downgrade kodu `NO_DELIVERABLE` (atdd.md'deki `NO_DELIVERABLE_FOR_SKILL` yerine).
2. **Self-attestation CHECK:** Seçenek (a) — `attestations` tablosuna `talent_id` kolonu denormalize edilir, `CheckConstraint("attestor_user_id != talent_id")` doğrudan bu tabloda yazılır.
3. **downgrade_reasons:** JSONB liste (öneri onaylı sayılır, ayrıca sorulmadı).
