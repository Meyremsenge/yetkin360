# Code Diff — skillsignal-self-claim-uretimi
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `backend/app/models/skill_signal.py` — `SkillSignal` modeli (DOMAIN.md §3.14 şeması, append-only — sadece `created_at`, `updated_at` yok).
- `backend/app/services/skill_signal.py` — `list_skill_signals()` servis fonksiyonu.
- `backend/app/api/skill_signals.py` — `GET /talents/me/signals` route'u + Pydantic response şemaları.
- `backend/alembic/versions/53299629ffe0_add_skill_signals_table_and_...py` — `skill_signals` tablosu + `audit_events` deseninde DB-seviyesi immutability trigger (`down_revision=i0j1k2l3m4n5`).

## Değiştirilen Dosyalar
- `backend/app/models/__init__.py` — `SkillSignal` export edildi.
- `backend/app/services/authorization.py` — `scoped_skill_signals()` eklendi (`scoped_skill_claims()` deseninin birebir kopyası).
- `backend/app/services/skill_claim.py` — `add_skill_claim()` içine, `SkillClaim` flush edildikten HEMEN SONRA (aynı transaction, `claim.id`/`claim.created_at` artık dolu), bir `SkillSignal(source_type="SELF_CLAIM", strength="NONE", source_id=claim.id, occurred_at=claim.created_at)` INSERT'i eklendi. İki ayrı flush, tek commit sınırı (route katmanında).
- `backend/app/main.py` — `skill_signals_router` import+include edildi.

## Migration — gerçekten uygulandı ve doğrulandı
```
backend> .venv/Scripts/python.exe -m alembic upgrade head
Running upgrade i0j1k2l3m4n5 -> 53299629ffe0, add skill_signals table and immutability trigger
backend> .venv/Scripts/python.exe -m alembic downgrade -1
Running downgrade 53299629ffe0 -> i0j1k2l3m4n5  (temiz düştü)
backend> .venv/Scripts/python.exe -m alembic upgrade head
Running upgrade i0j1k2l3m4n5 -> 53299629ffe0  (tekrar uygulandı)
```

## AC Karşılama Durumu
Tüm AC-1..AC-6, AC-S1, AC-S2 kriterleri karşılanıyor, gerçek testlerle kanıtlandı:
```
backend> .venv/Scripts/python.exe -m pytest tests/test_skill_signals.py tests/authorization/test_skill_signals.py -q
14 passed
backend> .venv/Scripts/python.exe -m pytest -q   (tam paket, regresyon kontrolü)
523 passed, 4 skipped
backend> .venv/Scripts/python.exe -m ruff check .
All checks passed!
backend> .venv/Scripts/python.exe -m mypy app
Success: no issues found in 49 source files
```

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar

1. **mypy tip uyumsuzluğu (kod bulgusu):** `skill_signals.py`'de servis
   fonksiyonu ham `dict` listesi döndürüyordu ama Pydantic response modeli
   (`SkillSignalsGroupResponse`) bekliyordu. `SkillSignalsGroupResponse(**item)`
   dönüşümüyle düzeltildi.
2. **Lint hataları (test dosyalarında, kod değil):** 3 kullanılmayan
   import/değişken (`sqlalchemy.select`, `SkillSignal` importu, `claim_id`
   değişkeni) — `test-copilot`'a minimal düzeltme dispatch edildi.
3. **YANLIŞ ALARM — sahte regresyon:** İlk tam paket koşumunda 15 test
   (`test_outbox_service.py`/`test_outbox_worker.py`) kırmızı çıktı. Kök
   neden kodda DEĞİL — bu oturumda daha önce yapılan MANUEL sunucu
   doğrulamasından (`curl` ile gerçek kullanıcı kaydı/login/evidence-upload
   testi) kalan 1 satırlık `outbox` tablosu kirliliğiydi; `test_outbox_service.py`
   filtre olmadan `scalar_one_or_none()` sorgusu attığı için paylaşılan dev
   DB'deki fazladan satırla çakışıp `MultipleResultsFound` fırlatıyordu.
   Kirli veri (`DELETE FROM outbox` + ilişkili test kullanıcısı) temizlendi,
   tam paket tekrar koşuldu: **523 passed, 0 failed**. **Ders:** bu proje
   `outbox`/auth testleri paylaşılan dev DB'ye karşı transaction-izole
   değil (engagement testlerinin aksine) — manuel canlı doğrulama
   (curl/uvicorn) sonrası test koşumundan önce DB'nin temizlendiğinden
   emin olunmalı.

## Kalan Sınırlamalar
Yok — atdd.md'nin Kapsam Dışı bıraktığı her şey (DELIVERABLE/TASK/EVALUATION/
ATTESTATION kaynakları, gerçek superseded_by_id mantığı, frontend) bilinçli
olarak yazılmadı.

## Varsayımlar
Yok — implementasyon test_diff.md'deki testlerin beklediği tam alan/şema
isimleriyle birebir uyumlu, gerçek test koşumuyla doğrulandı.

## CAVEMAN Self-Review
- Yeni dosya: 4 (model, servis, route, migration) — her biri mevcut domain
  başına dosya deseniyle (örn. `skill_claim.py`/`engagement.py` çifti)
  tutarlı, gerekçeli.
- Yeni soyutlama: `scoped_skill_signals()` — mevcut `scoped_*()` deseninin
  zorunlu bir kopyası (plan.md'nin kararı), yeni bir soyutlama katmanı değil.
- Yeni yardımcı fonksiyon: yok, sadece AC'lerin gerektirdiği asgari
  (`list_skill_signals()`).
- DELIVERABLE/TASK/EVALUATION/ATTESTATION mantığı yazılmadı, `superseded_by_id`
  hep NULL (plan.md kararı, spekülatif kod önlendi).
