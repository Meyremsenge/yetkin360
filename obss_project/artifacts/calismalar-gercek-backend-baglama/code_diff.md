# Code Diff — calismalar-gercek-backend-baglama
_Green step (code-copilot, 2 ayrı Haiku alt-ajan turu: backend + frontend)_

## Değiştirilen Dosyalar
- `backend/app/services/engagement.py` — `list_engagements()` ve
  `get_engagement_detail()` eklendi (`scoped_engagements`/`get_scoped_or_404`
  mevcut kalıbını kullanıyor, N+1 yok — Organization JOIN/tek ek sorgu).
- `backend/app/api/engagements.py` — `GET /engagements`, `GET /engagements/{id}`
  + yeni Pydantic response modelleri (`EngagementSummaryResponse`,
  `EngagementDetailResponse`, `TaskSummaryResponse`, `DeliverableSummaryResponse`).
- `backend/tests/authorization/conftest.py` — redundant `session` fixture
  override kaldırıldı (parent conftest'e devredildi) — bağımsız doğrulandı,
  tüm `tests/authorization` paketi (346 test) regresyon olmadan geçiyor.
- `frontend/lib/api/engagements.ts` — `USE_MOCK_LIST`/`USE_MOCK_DETAIL` ve
  tüm mock store kodu (149 satır) silindi; `listEngagements`/`getEngagement`/
  `transitionEngagement` artık her zaman gerçek `apiFetch` çağırıyor.
  `availableTransitions()`/`isReasonRequired()` değişmedi.
- `frontend/lib/api/engagements.test.ts` — kaldırılan mock durum makinesini
  test eden 6 eski test silindi (AC-9'un doğal sonucu — artık var olmayan
  bir özelliği test ediyorlardı), yerine `transitionEngagement`'ın gerçek
  `apiFetch` davranışını doğrulayan 4 yeni test eklendi.
- `frontend/vitest.setup.ts` — localStorage polyfill (test ortamı için,
  mock store silinmeden önce bazı testlerin dolaylı bağımlılığı).

## Diskte doğrulandı
`git status --short` ile 6 dosyanın `M` olduğu teyit edildi.

## AC Kapsama (bağımsız test çalıştırmayla doğrulandı)
| AC | Durum |
|---|---|
| AC-1,2,3 (liste + tenant izolasyonu) | `pytest tests/authorization/test_engagement_authorization.py::TestEngagementList` → PASS |
| AC-4 (detay: tasks+deliverables) | `TestEngagementDetail::test_get_engagement_detail_returns_all_fields_ac4` → PASS |
| AC-5,6,AC-S1,AC-S2 (404, var/yok ayırt edilemez, IDOR) | `TestEngagementDetail` kalan testler → PASS |
| AC-7 (boş liste) | PASS |
| AC-8 (sayfalama) | PASS |
| AC-9 (mock temizliği) | Doğrulandı — `grep -c "USE_MOCK\|localStorage" engagements.ts` → 0 (localStorage kalıntısı yok) |

## Bağımsız doğrulama sonuçları
- `pytest tests/authorization -q` → **346 passed, 4 skipped** (regresyon yok, +14 yeni test dahil)
- `pytest -q` (tam backend) → **798 passed, 13 failed** (13 hata bu görevden ÖNCE de vardı, `test_outbox_worker.py`/`test_seed.py`'de, ilgisiz — `git stash` ile daha önce doğrulandı)
- `npx vitest run lib/api/engagements.test.ts` → **18/18 PASS**
- `npx tsc --noEmit` → 0 hata
- `npx vitest run` (tam frontend) → 815 passed, 8 failed (4 dosyada — hepsi bu görevden ÖNCE de var olan, dokunulmamış dosyalarda: `evaluation-form.test.tsx`, `evidence-upload-form.test.tsx`, `kurum/[id]/panel/page.test.tsx`, `lib/api/evaluation.test.ts`)

## Test dosyalarına dokunuldu mu?
Evet — ama SADECE test-copilot yetkisiyle: (1) yeni 20 test eklendi (red
step), (2) AC-9'un doğal sonucu olan 6 obsolete test silinip 4 yenisiyle
değiştirildi. İkisi de ayrı, gerekçeli dispatch'lerle yapıldı, implementasyon
dosyalarına code-copilot dışında kimse dokunmadı.
