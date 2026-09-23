# Verify Report — engagement-task-deliverable
_Reference: atdd.md, plan.md, test_diff.md, code_diff.md_

CI referansı: `.github/workflows/ci.yml` (backend job) — `ruff check .`,
`mypy app`, `alembic upgrade head`, `pytest -q`. Aşağıdaki komutlar birebir
bu invocation'lara uyuyor (venv: `backend/.venv`).

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` ile 7 dosya doğrulandı (3 modified, 4 yeni) |
| 2 | Build/derleme | PASS | `mypy app` başarılı, ayrıca `ruff check` sözdizimini doğruluyor |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase değil, PostgreSQL+SQLAlchemy+Alembic; **ama migration var** → alembic upgrade/downgrade ayrıca gerçek DB'ye karşı doğrulandı (aşağıya bkz.) |
| 4 | Lint | PASS (1 tur düzeltmeyle) | İlk koşuda 2 `F401` hatası (kullanılmayan `uuid4` import'u, iki yeni test dosyasında) — `test-copilot`'a minimal düzeltme dispatch edildi, ikinci koşuda `ruff check .` → "All checks passed!" |
| 5 | Type check | PASS | `mypy app` → "Success: no issues found in 43 source files" |
| 6 | Unit/integration testler | PASS | `pytest tests/test_engagement_tasks.py tests/test_engagement_deliverables.py tests/test_engagement_transitions.py -q` → 51 passed; tam paket `pytest -q` → **413 passed, 4 skipped** (skip'ler bu görevden önce vardı, kapsam dışı) |
| 7 | E2E testler | N/A | Backend-only, ayrı e2e suite yok; atdd.md'nin minimal e2e hedefi (ACTIVE→task→deliverable→T5) mevcut integration testleriyle zaten kapsanıyor |
| 8 | Lighthouse (performans) | N/A | Web UI kapsamda değil |
| 9 | Erişilebilirlik | N/A | Web UI kapsamda değil |
| 10 | Güvenlik taraması | PASS | `security-scan`, değişen 7 dosyaya scope'lanmış: `secrets: PASS`, `python_sast: PASS`, `python_deps`/`node_deps`: N/A (manifest yok) — **verdict: PASS** |
| 11 | AI code review | PENDING | `red-team` adımına bırakıldı |
| 12 | Görsel regresyon | N/A | Web UI kapsamda değil |
| 13 | DAST (ZAP) | N/A | Web UI kapsamda değil |
| 14 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor |

## Migration Doğrulaması (proje kuralı: her ikisi de çalışmalı)
```
alembic downgrade -1   → h9i0j1k2l3m4'e temiz düştü
alembic upgrade head   → i0j1k2l3m4n5'e tekrar uygulandı, hatasız
```
Bu, `code-copilot` aşamasında bir kez, `verify` aşamasında ikinci kez
(bağımsız doğrulama olarak) çalıştırıldı — ikisinde de aynı temiz sonuç.

## AC → Test Mapping
Bkz. `test_diff.md`'deki tam tablo (AC-1..AC-7, AC-S1..AC-S5). Özet: tümü
PASS. AC-S5 testlerinde bir tasarım düzeltmesi yapıldı (bkz. `code_diff.md`
"Review Sürecinde Bulunan ve Düzeltilen Sorunlar" — FastAPI'nin zorunlu-alan
validasyonunun handler'dan önce çalışması nedeniyle "eksik alan" senaryosu
"geçerli ama çapraz-tenant" senaryosuna çevrildi, assertion'lar değişmedi).

## Coverage / Quality Notes
- `code_diff.md`'de not edilen bir gerçek düzeltme: `create_deliverable()`'daki
  naive `datetime.now()` → `datetime.now(timezone.utc)` (proje UTC kuralına
  uyum). `verify` bunu tekrar test koşumuyla doğruladı (413 passed).
- Test piramidi atdd.md'nin öngördüğü 10/80/10'a uygun: 51 yeni/ilgili testin
  tamamı HTTP-uç (integration) seviyesinde, ayrı unit test eklenmedi (mevcut
  `scoped_engagements()`/`get_scoped_or_404()` zaten unit test kapsamında).

## Refactor Aday Kontrolü
Unit testler (gate 6) PASS. Değişen dosyalar (`task_deliverable.py`,
`engagement.py`'ye eklenen 2 servis fonksiyonu, `engagements.py`'ye eklenen
2 route) mevcut dosya konvansiyonunu (transition_table deseni, route
şablonu) birebir takip ediyor — tekrar eden sihirli sayı, derin nesting,
uzun parametre listesi veya ölü kod yok. `create_engagement_task()` ve
`create_deliverable()` arasında bir miktar yapısal benzerlik var (ikisi de
UUID parse → scope check → status check → rol check → INSERT → audit) ama
bu 2 fonksiyonluk bir tekrar, ortak bir helper'a çıkarmak CAVEMAN ilkesine
göre şimdilik gereksiz (3. bir benzer fonksiyon eklendiğinde tekrar
değerlendirilebilir — "3 kere tekrar" kuralı). **Refactor adayı yok**
(diff zaten minimal/CAVEMAN'a uygun).
