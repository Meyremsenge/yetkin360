# Code Diff — engagement-task-deliverable
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `backend/app/models/task_deliverable.py` — `EngagementTask`, `Deliverable` SQLAlchemy modelleri (`Base`+`TimestampMixin`, `uuid7_default` deseni, mevcut `engagement.py` ile birebir).
- `backend/alembic/versions/i0j1k2l3m4n5_add_engagement_tasks_deliverables.py` — `engagement_tasks` + `deliverables` tabloları, `down_revision=h9i0j1k2l3m4` (mevcut tek head).

## Değiştirilen Dosyalar
- `backend/app/models/__init__.py` — `EngagementTask`, `Deliverable` export edildi.
- `backend/app/services/engagement.py` — `transition_table`'a T5 (`ACTIVE`→`PENDING_EVALUATION`, precondition `has_deliverable`, gerçek `SELECT COUNT(*)` sorgusu) + `create_engagement_task()`, `create_deliverable()` servis fonksiyonları.
- `backend/app/api/engagements.py` — `POST /{id}/tasks`, `POST /{id}/deliverables` route'ları + `PostTaskRequest/Response`, `PostDeliverableRequest/Response` Pydantic şemaları (ORM'den ayrı).

## Migration — gerçekten uygulandı ve doğrulandı
```
backend> .venv/Scripts/python.exe -m alembic upgrade head
Running upgrade h9i0j1k2l3m4 -> i0j1k2l3m4n5, add engagement tasks and deliverables tables

backend> .venv/Scripts/python.exe -m alembic downgrade -1
Running downgrade i0j1k2l3m4n5 -> h9i0j1k2l3m4  (temiz düştü)

backend> .venv/Scripts/python.exe -m alembic upgrade head
Running upgrade h9i0j1k2l3m4 -> i0j1k2l3m4n5  (tekrar uygulandı)
```
Proje kuralı gereği (`.claude/rules/database.md`) hem upgrade hem downgrade
gerçek PostgreSQL'e karşı doğrulandı.

## AC Karşılama Durumu
Tüm AC-1..AC-7 ve AC-S1..AC-S5 kriterleri karşılanıyor, gerçek testlerle
kanıtlandı:
```
backend> .venv/Scripts/python.exe -m pytest tests/test_engagement_tasks.py tests/test_engagement_deliverables.py tests/test_engagement_transitions.py -q
51 passed
backend> .venv/Scripts/python.exe -m pytest -q   (tam paket, regresyon kontrolü)
413 passed, 4 skipped
```

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar

1. **AC-S5 testlerinde tasarım hatası (test_diff.md kapsamı, kod değil):**
   `TestTaskScopeCheckOrder`/`TestDeliverableScopeCheckOrder`'daki 2 test
   "eksik `title`" ile scope-check sırasını kanıtlamaya çalışıyordu, ama
   FastAPI/Pydantic zorunlu bir alanı (`min_length=1`) route handler'ı hiç
   çalıştırmadan framework seviyesinde 422 ile reddediyor — "scope-check
   validation'dan önce çalışsın" senaryosu eksik-alan durumunda teknik
   olarak test edilemez. Kullanıcı onayıyla test payload'ı "geçerli ama
   çapraz-kurum/çapraz-talent hedefli" bir title'a çevrildi, assertion'lar
   (404/NOT_FOUND) değişmedi. **Ders:** Pydantic-seviyeli zorunlu-alan
   kontrolü ile uygulama-seviyeli (handler içi) doğrulama sırası aynı
   şeyi test etmiyor — "scope önce çalışsın" AC'leri yalnız handler-içi
   semantik kontrollerle (ör. geçersiz enum string'i, YET-65'teki
   `to_status=FOOBAR` deseni) anlamlı, framework-seviyeli 422'lerle değil.

2. **`create_deliverable()`'da naive `datetime.now()` (kod bulgusu):**
   `submitted_at` alanı `.claude/rules/database.md`'nin "Zaman: timestamptz,
   UTC, yerel saat varsayımı yasak" kuralını ihlal ediyordu — mevcut
   `TimestampMixin` (`created_at`/`updated_at`) her zaman UTC-aware
   (`func.now()`, DB-side) kullanırken, yeni kod Python tarafında saf yerel
   saat yazıyordu. `datetime.now(timezone.utc)` ile düzeltildi (tek satır +
   bir import). Migration'daki kolon zaten `timestamptz` olarak doğru
   tanımlıydı — sadece Python tarafındaki değer üretimi yanlıştı.

## Kalan Sınırlamalar
Yok — atdd.md'nin Kapsam Dışı bıraktığı her şey (evidence_ids[], task_skills
iş mantığı, dosya yükleme, frontend, GET/PATCH/DELETE uçları) bilinçli
olarak yazılmadı.

## Varsayımlar
Yok — implementasyon test_diff.md'deki testlerin beklediği tam alan/şema
isimleriyle birebir uyumlu, gerçek test koşumuyla doğrulandı.

## CAVEMAN Self-Review
- Yeni dosya: sadece 1 (`task_deliverable.py`, iki modeli aynı dosyada tutmak — `engagement.py`'nin kendisi tek dosyada tutulmuyor olsa da, iki küçük ilişkili model için ayrı dosya CAVEMAN'a aykırı değil, mevcut proje zaten domain-bazlı dosyalama kullanıyor örn. `skill.py`/`skill_claim.py`).
- Yeni soyutlama: yok — `scoped_tasks()`/`scoped_deliverables()` YAZILMADI, mevcut `scoped_engagements()`+`get_scoped_or_404()` yeniden kullanıldı (plan.md'nin kararı).
- Yeni yardımcı fonksiyon: yok, sadece 2 servis fonksiyonu (AC'lerin gerektirdiği asgari).
- `task_skills` tablosu oluşturulmadı (plan.md kararı, spekülatif şema önlendi).
