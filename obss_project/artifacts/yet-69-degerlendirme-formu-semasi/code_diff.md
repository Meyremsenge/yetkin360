# Code Diff — yet-69-degerlendirme-formu-semasi
_Reference: atdd.md, plan.md, test_diff.md_

## Doğrulanan Değişiklikler (Read ile teyit edildi, alt-ajan özetine güvenilmedi)

`git status --short` çıktısı:
```
 M backend/app/api/engagements.py
 M backend/app/models/__init__.py
?? backend/alembic/versions/j1k2l3m4n5o6_add_evaluations_table.py
?? backend/app/models/evaluation.py
?? backend/app/schemas/evaluation.py
?? backend/app/services/evaluation.py
```
Test dosyaları (`test_evaluation.py`, `test_evaluation_authorization.py`) **dokunulmamış** — sadece `??` (yeni), önceki `test-copilot` adımından kalan, değiştirilmemiş.

## Yeni Dosyalar

| Dosya | İçerik |
|---|---|
| `backend/app/models/evaluation.py` | `Evaluation` (evaluations tablosu) + `EvaluationItem` (evaluation_items tablosu), `evidence.py` pattern'i takip edilmiş (CheckConstraint, Index, uuid7_default, TimestampMixin) |
| `backend/app/schemas/evaluation.py` | `EvaluationItemCreate`, `EvaluationItemResponse`, `EvaluationCreate`, `EvaluationResponse` — **`private_note` alanı `EvaluationResponse`'ta yok** (AC-S1 doğrulandı, Read ile teyit edildi) |
| `backend/app/services/evaluation.py` | `create_evaluation()` — engagement scope kontrolü, durum kontrolü (409), direction/rol tutarlılığı (403), skill_id ön-doğrulama (422), UNIQUE ihlali yakalama (409), T7 geçişi (sadece ORG_TO_TALENT), audit event (private_note payload'a girmiyor) |
| `backend/alembic/versions/j1k2l3m4n5o6_add_evaluations_table.py` | `evaluations` + `evaluation_items` tabloları, `down_revision='i0j1k2l3m4n5'` (doğru — mevcut tek head) |

## Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `backend/app/models/__init__.py` | `Evaluation`, `EvaluationItem` import + `__all__`'a eklendi |
| `backend/app/api/engagements.py` | `POST /{engagement_id}/evaluation` ucu eklendi (satır 548-682); `app.services.evaluation`'dan import edilen exception sınıfları `Eval*` prefix'iyle alias'landı (mevcut `app.services.engagement` exception isimleriyle çakışmasın diye — doğru çözüm) |

**Not:** `backend/app/services/engagement.py`'ye **dokunulmadı** — plan.md'de "transition_table'a satır eklenebilir" ihtimali vardı, ama alt-ajan T7 mantığını tamamen `services/evaluation.py` içinde (`engagement.status`'u doğrudan UPDATE ederek) izole etti. Bu, plan.md'nin Risks bölümünde işaretlenen "YET-88 ile merge çakışması" riskini **ortadan kaldırıyor** — iki görev artık aynı dosyaya dokunmuyor.

## Acceptance Criteria Doğrulaması (Read ile, dosya içeriği üzerinden)

| AC | Karşılandı mı | Kanıt |
|---|---|---|
| AC-1 (happy path 201) | ✅ | `create_evaluation()` + `post_engagement_evaluation()` — engagements.py:552-682 |
| AC-2 (T7, ORG_TO_TALENT→EVALUATED) | ✅ | evaluation.py:177-207, aynı transaction'da UPDATE |
| AC-3 (NOT_OBSERVED, comment opsiyonel) | ✅ | schemas/evaluation.py — `comment` alanı `None` default, rating validasyonunda ayrım yok |
| AC-4 (items[] boş/criterion eksik → 422) | ✅ | `EvaluationCreate.items` `min_length=1`, `EvaluationItemCreate.criterion` `min_length=1` (Pydantic) |
| AC-5 (scope dışı → 404) | ✅ | evaluation.py:83-89, `get_scoped_or_404` |
| AC-6 (yanlış durum → 409) | ✅ | evaluation.py:91-95 |
| AC-7 (UNIQUE → 409) | ✅ | evaluation.py:146-154, `IntegrityError` yakalanıp `DuplicateEvaluationError` |
| AC-8 (geçersiz skill_id → 422) | ✅ | evaluation.py:120-133, yazmadan önce ön-kontrol |
| AC-9 (TALENT_TO_ORG, status değişmez) | ✅ | evaluation.py:177, `if direction == "ORG_TO_TALENT"` koşulu |
| AC-S1 (private_note asla response'ta yok) | ✅ | schemas/evaluation.py:82-104, alan tanımlı değil |
| AC-S2 (evaluator_user_id principal'dan) | ✅ | evaluation.py:140, `principal.user_id`; request şemasında böyle bir alan yok |
| AC-S3 (direction/rol tutarsızlığı → 403) | ✅ | evaluation.py:97-118 |

## Definition of Done Kontrolü
- TODO/FIXME/placeholder: yok (tek `pass` satırı meşru bir except bloğu, zaten doğrulanmış skill_id'nin ikinci UUID parse'ında sessizce geçiliyor — placeholder değil).
- Kapsam dışı özellik yazılmamış: EVALUATED→VERIFIED geçişi, Attestation, SkillSignal, frontend — hiçbiri yok.
- Mevcut `transition_table`'daki 5 geçiş satırı bozulmamış (dosyaya dokunulmadı).
- Yeni soyutlama: 5 domain exception sınıfı (`EngagementNotFoundError`, `IllegalTransitionError`, `TransitionForbiddenError`, `DuplicateEvaluationError`, `InvalidSkillError`) — mevcut `engagement.py`'deki pattern'le birebir tutarlı, gerekçeli.

## Küçük Not (kritik değil, kayıt için)
`Evaluation.engagement_id` FK'sinde `ondelete="CASCADE"` var; `Deliverable`/`EngagementTask` modellerinde (plan.md'nin referans aldığı pattern) bu yok. `engagements` tablosu zaten hiç silinmediği (append-only) için pratikte etkisi yok, ama tutarlılık için düzeltilebilir — bloklayıcı değil, `refactor` adımında ele alınabilir.

## Sonraki Adım
`verify` — testleri gerçekten çalıştırıp PASS/FAIL raporlayacak (migration `alembic upgrade head` ile uygulanmalı, kullanıcı onayı zaten alındı).
