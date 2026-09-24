# Plan — yet-69-degerlendirme-formu-semasi
_Reference: atdd.md_

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | Yeni `Evaluation`, `EvaluationItem` modellerini export'a ekle (mevcut pattern: her model burada import+`__all__`) | low |
| `backend/app/services/engagement.py` | `transition_table`'a `("PENDING_EVALUATION", "EVALUATED")` satırı eklenir — AC-2/AC-6 (T7 geçişi). `create_evaluation()` (yeni serviste) bu geçişi tetikleyecek şekilde `transition_engagement()`'ı çağırabilir YA DA `evaluation.py` kendi içinde aynı transaction'da doğrudan `UPDATE` yapabilir (bkz. Open Questions — mevcut `transition_engagement()` optimistic locking + version parametresi istiyor, ama evaluation submit akışında client bir `version` göndermeyecek) | **medium** — mevcut transition mekanizmasıyla nasıl entegre olacağı netleşmeli |
| `backend/app/api/engagements.py` | `POST /{engagement_id}/evaluation` ucu eklenir (mevcut router'a, `post_engagement_deliverables`'ın hemen altına, aynı dosya içi pattern) | low |

## New Files

| File | Purpose |
|------|---------|
| `backend/app/models/evaluation.py` | `Evaluation` (evaluations tablosu: id, engagement_id FK, evaluator_user_id FK, direction CHECK, submitted_at, private_note, UNIQUE(engagement_id, evaluator_user_id, direction)) + `EvaluationItem` (evaluation_items: id, evaluation_id FK CASCADE, skill_id FK nullable, criterion, rating CHECK, comment). `evidence.py`'deki CheckConstraint/Index pattern'ini takip et. |
| `backend/app/schemas/evaluation.py` | `EvaluationItemCreate`, `EvaluationCreate` (request), `EvaluationItemResponse`, `EvaluationResponse` (response — **`private_note` alanı yok**, `schemas/evidence.py` pattern'ini takip et) |
| `backend/app/services/evaluation.py` | `create_evaluation()` — yetki kontrolü (`scoped_engagements` ile engagement'ı çek), durum kontrolü (`PENDING_EVALUATION` zorunlu → 409), direction/rol tutarlılığı (AC-S3), `evaluator_user_id` principal'dan (AC-S2), NOT_OBSERVED için comment zorunlu değil (AC-3), skill_id doğrulama (AC-8), UNIQUE ihlali yakalama → domain exception (AC-7), T7 geçişini tetikleme (sadece ORG_TO_TALENT, AC-2), audit event. `engagement.py`'deki `create_deliverable()` ile aynı iskelet (try/except IntegrityError, log_audit_event). |
| `backend/alembic/versions/<yeni_id>_add_evaluations_table.py` | `evaluations` + `evaluation_items` tabloları (down_revision=`i0j1k2l3m4n5`, mevcut tek head) — **kullanıcı onayı gerekir, aşağıya bakınız** |
| `backend/tests/test_evaluation.py` | Servis + endpoint testleri (happy path AC-1/2/3, edge case AC-4/6/7/8/9) — `tests/test_engagement_deliverables.py` pattern'i takip edilir |
| `backend/tests/test_evaluation_authorization.py` | Yetkilendirme testleri (AC-5, AC-S1/S2/S3, private_note sızıntı testi) — **`tests/authorization/` klasörü DEĞİL**, mevcut projede engagement authz testleri `tests/test_engagement_authorization.py` adıyla kök `tests/` altında duruyor; atdd.md'de yazılan `tests/authorization/test_evaluation_authz.py` yolu **düzeltildi**, gerçek pattern'e uyduruldu (bkz. Open Questions) |

## Dependencies

- `app.services.authorization.Principal`, `get_scoped_or_404`, `scoped_engagements` — mevcut, değişiklik gerekmiyor (evaluation ayrı bir `scoped_evaluations()` gerektirmiyor; erişim her zaman `scoped_engagements` üzerinden engagement'a ulaşılarak sağlanıyor, `evidence.py`'nin aksine evaluation'ın kendi ayrı bir sahiplik zinciri yok)
- `app.services.audit.log_audit_event` — mevcut, `create_evaluation()` ve T7 geçişi için kullanılacak
- `app.services.outbox.enqueue` — **muhtemelen gerekmiyor** (atdd.md Rollback Beklentisi: ağ çağrısı yok). Ama T7 geçişi bir koordinatör bildirimi tetiklemeli mi? `transition_engagement()`'taki mevcut pattern sadece `PENDING_APPROVAL` için outbox kullanıyor (satır 365-376), `PENDING_EVALUATION`/`EVALUATED` için outbox YOK — bu görevde de eklenmemeli (final analizde açık değil, scope creep riski, Kapsam Dışı'na uyumlu)
- `app.models.Engagement`, `app.models.Skill` (skill_id FK doğrulaması için `app.models.skill.Skill`)
- `app.api.deps.get_current_principal`, `get_session` — mevcut

## Migration Required?

**Evet.** Yeni `evaluations` + `evaluation_items` tabloları (final analiz §12 şeması). Mevcut tek alembic head: `i0j1k2l3m4n5` (add_engagement_tasks_deliverables). Yeni migration bunu `down_revision` alacak.

Taslak yapı (uygulama öncesi CLAUDE.md gereği **ayrıca açık onay istenecek**):
```python
op.create_table(
    'evaluations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('engagement_id', sa.UUID(), nullable=False),
    sa.Column('evaluator_user_id', sa.UUID(), nullable=False),
    sa.Column('direction', sa.String(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('private_note', sa.String(), nullable=True),
    sa.Column('created_at', ...), sa.Column('updated_at', ...),
    sa.CheckConstraint("direction IN ('ORG_TO_TALENT','TALENT_TO_ORG')", name='ck_evaluations_direction'),
    sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id']),
    sa.ForeignKeyConstraint(['evaluator_user_id'], ['users.id']),
    sa.UniqueConstraint('engagement_id', 'evaluator_user_id', 'direction', name='uq_evaluations_engagement_evaluator_direction'),
    sa.PrimaryKeyConstraint('id'),
)
op.create_table(
    'evaluation_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('evaluation_id', sa.UUID(), nullable=False),
    sa.Column('skill_id', sa.UUID(), nullable=True),
    sa.Column('criterion', sa.String(), nullable=False),
    sa.Column('rating', sa.String(), nullable=False),
    sa.Column('comment', sa.String(), nullable=True),
    sa.CheckConstraint("rating IN ('BELOW','MEETS','EXCEEDS','NOT_OBSERVED')", name='ck_evaluation_items_rating'),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
    sa.PrimaryKeyConstraint('id'),
)
```
Downgrade: `drop_table('evaluation_items')` sonra `drop_table('evaluations')`.

## Risks

atdd.md'den taşınan/güncellenen riskler:

- **T7 geçişinin YET-88 (paralel çalışılıyor olabilir) ile çakışma riski** — `engagement.py`'nin `transition_table` sözlüğüne dokunuluyor, aynı dosyaya YET-88 da muhtemelen dokunacak (`EVALUATED→VERIFIED` satırı ekleyecek). **Merge çatışması riski somut** — kullanıcı commit öncesi takım arkadaşıyla senkron olmalı (atdd.md'de zaten not düşülmüştü, burada teyit ediliyor).
- **YENİ BULGU (plan aşamasında keşfedildi):** Mevcut `transition_engagement()` fonksiyonu `version` parametresi zorunlu kılıyor (optimistic locking) ve doğrudan public bir arayüz. Evaluation submit sırasında client bir `version` göndermeyecek (evaluation body'sinde `version` yok, atdd.md'de de yok). Bu yüzden T7 geçişi muhtemelen `transition_engagement()`'ı **çağırmamalı** — `create_evaluation()` kendi içinde `engagement.status`'u aynı transaction'da güncellemeli (kendi versiyonunu okuyup +1 yaparak, client'tan almadan). Bu, mevcut transition_table pattern'inden bir sapma — **Open Questions'a taşındı, code-copilot başlamadan netleştirilmeli.**
- **YENİ BULGU (plan aşamasında keşfedildi):** atdd.md'nin AC-5/AC-S3'te önerdiği "yetkisiz erişimde 404" kuralı, mevcut kod tabanındaki gerçek pattern ile kısmen çelişiyor: `engagements.py`'deki mevcut uçlar (`post_engagement_tasks`, `post_engagement_deliverables`) **403 FORBIDDEN** kullanıyor "kaynak zaten scope içinde görünür ama bu spesifik aksiyona yetkisi yok" durumunda (örn. TALENT task oluşturamaz → 403, ORG_MEMBER deliverable submit edemez → 403). Bu CLAUDE.md'nin 404 kuralını ihlal etmiyor çünkü — o kural "kaynağın varlığını gizle" diyor, burada kaynak zaten `scoped_engagements` ile görünür/bilinir durumda, sadece aksiyon reddediliyor. **atdd.md'deki AC-S3 (direction/rol tutarsızlığında 422 önerisi) ve AC-5'in "404" vurgusu gözden geçirilmeli**: gerçek pattern'e göre olması gereken — engagement hiç scope'ta değilse (başka org/institution) → 404; engagement scope'ta ama bu kullanıcı bu yönde (direction) değerlendirme yapamıyorsa (örn. talent ORG_TO_TALENT göndermeye çalışıyor) → 403 FORBIDDEN (mevcut `TransitionForbiddenError` pattern'i).

## Open Questions

1. **T7 geçişi nasıl tetiklenecek?** `create_evaluation()` kendi içinde `engagement.status`'u doğrudan `UPDATE` mi yapacak (client version göndermeden, optimistic locking'i bu akışta atlayarak), yoksa `transition_engagement()`'a versiyon bilgisini serviste okuyup mu geçirecek? Mevcut kod `version` zorunlu tutuyor ve bunu client'tan alıyor — evaluation akışında client version bilmiyor/göndermiyor.
2. **Yetkisiz/yanlış-rol durumunda HTTP kodu:** atdd.md AC-5/AC-S3'te önerilen "404/422" yerine, mevcut kod tabanı pattern'i "engagement scope dışıysa 404, scope içinde ama yanlış rol/yön ise 403" diyor. Bu, atdd.md'nin ilgili AC'lerinin **düzeltilmesini** gerektirir mi, yoksa bilinçli bir sapma mı olacak? (CLAUDE.md: "sessizce sapma, sor" — bu yüzden Open Question olarak işaretlendi, code-copilot bunu kendi başına karar vermemeli.)
3. **`tests/authorization/` vs `tests/test_engagement_authorization.py` yol tutarsızlığı** çözüldü (plan.md'de düzeltildi) — ama teyit: bu projede `tests/authorization/` klasörü sadece merkezi/genel yetkilendirme matrisi testleri (`test_matrix.py`, `test_can_defaults.py`) için mi kullanılıyor, modül-özel authz testleri (`test_engagement_authorization.py`, `test_evidence_record_download.py`) hep kök `tests/` altında mı kalıyor? Örnekler bunu doğruluyor (evidence, engagement) — evaluation için de aynı pattern (`tests/test_evaluation_authorization.py`) izlenecek, **CLAUDE.md komut tablosundaki `pytest tests/authorization -q` komutu bu görevde YETERLİ DEĞİL**, `pytest tests/ -k evaluation -q` veya tüm paket de çalıştırılmalı (doğrulama matrisi zaten "yetkilendirme/kimlik doğrulama → tests/authorization tamamı + ilgili testler" diyor, "ilgili testler" kısmı `test_evaluation_authorization.py`'yi kapsıyor).

## Kararlar (Sonnet 5 low alt-ajanı tarafından yanıtlandı)

1. **T7 tetikleme mekanizması:** `create_evaluation()` kendi içinde `engagement.status`'u aynı transaction'da doğrudan günceller (serviste `version`'ı okuyup +1 yaparak, client'tan almadan); `transition_engagement()`'ı client-version parametresiyle çağırmaz. Gerekçe: evaluation submit body'sinde `version` alanı yok/olmamalı — T7 bir public transition endpoint'i değil, evaluation submit'in yan etkisi (atdd.md Assumptions ile tutarlı).

2. **403 vs 404 düzeltmesi — atdd.md'ye uygulandı (aşağıya bakınız).** Bilinçli sapma olarak işlendi, sessizce değil: mevcut kod tabanı pattern'i (`post_engagement_tasks`/`post_engagement_deliverables`) "scope dışı → 404, scope içi ama yanlış rol/yön → 403" ayrımını zaten netleştirmiş, CLAUDE.md'nin 404 kuralını ihlal etmiyor (kural kaynağın varlığını gizlemekle ilgili; kaynak zaten `scoped_engagements` ile görünürken aksiyonun reddi ayrı bir şey).

3. **`tests/test_evaluation_authorization.py` (kök `tests/` altında) — teyit edildi.** `tests/authorization/` klasörü yalnız merkezi/genel matris testlerine (`test_matrix.py`, `test_can_defaults.py`) ayrılmış; modül-özel authz testleri (evidence, engagement) hep kök `tests/` altında. Evaluation için de aynı pattern.

## Sonraki Adım
`plan.md` hazır, açık sorular çözüldü. Sıradaki adım `test-copilot` (red step) — bu plan.md'nin "Files to Modify"/"New Files" listesi dosya kapsamı olarak kullanılmalı, atdd.md'den yeniden türetilmemeli.
