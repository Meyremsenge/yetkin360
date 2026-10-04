# test_diff — yet-217-test-izolasyonu
_Yazan: Haiku alt-ajanları (test-copilot). Orkestratör test kodu yazmadı._

## Yeni
- `backend/tests/test_db_isolation.py` (13 test, **KIRMIZI**: `tests/_testdb.py` yok → import hatası). Hedef: AC-1/2/3, sözleşme satır 4/8.
  - URL türetme (yerel `_test`, CI `test` aynen, çift `_test` yok, `TEST_DATABASE_URL` önceliği, güvensiz ad → RuntimeError, parola mesajda yok), `maintenance_url`, canlı `current_database()` "test" ile biter.
  - Not: AC-3'ün "dev DB'de iz kalmaz" kısmı birim testle yazılamaz; verify adımında dev DB satır sayıları önce/sonra karşılaştırılacak.

## Değişen (bayat testler; ürün kodu değişmedi)
- `frontend/lib/api/evaluation.test.ts` — `vi.mock("./engagements")` (AC-4). Yeşil (6).
- `frontend/app/calismalar/[id]/evidence-upload-form.test.tsx`, `.../degerlendirme/evaluation-form.test.tsx` — beklenti `messages.errors.generic` (AC-5). Yeşil.
- `frontend/app/kurum/[id]/panel/page.test.tsx` — regex `/erişiminiz|yetkin/i` → `/erişiminiz yok|yetkiniz yok/i` (AC-6). Kök neden: AppShell'in render ettiği "Yetkinlik Yönetimi" bağlantısı regex'e eşleşiyordu (aralıklı değil, deterministik). Yeşil (11).

## Dikkat (red-team'e)
- Panel testinde AppShell'in koordinatöre "Yetkinlik Yönetimi" (admin) bağlantısı gösterip göstermediği doğrulanmadı; sadece UX, güvenlik sınırı değil ama ayrı bulgu olabilir.
- `test_db_isolation.py` 293 satır; gereğinden uzun olabilir, refactor/red-team değerlendirsin.
