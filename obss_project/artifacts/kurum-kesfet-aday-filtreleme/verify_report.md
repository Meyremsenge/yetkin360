# Verify Report — kurum-kesfet-aday-filtreleme
_Reference: docs/kesfet-tasarim.md (atdd.md ve plan.md geçersiz; code_diff.md yok — kod doğrudan yazıldı)_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` — Keşfet dosyaları yerinde |
| 2 | Build/derleme | PASS | `npm run build` — `/kesfet` statik rota olarak derlendi; backend uvicorn `--reload` ile yeni uçları sunuyor |
| 3 | Supabase | N/A | Proje Supabase kullanmıyor (PostgreSQL + SQLAlchemy); migration yok |
| 4 | Lint | PASS | `ruff check .` temiz; `npm run lint` 0 hata, 7 uyarı (hepsi önceden var olan dosyalarda). CI'da ayrı formatter adımı yok |
| 5 | Type check | PASS | `mypy app` — 77 dosya temiz; `npm run typecheck` temiz |
| 6 | Unit testler | PASS (1 ilgisiz kırık) | `pytest tests/authorization -q` 957 geçti / 9 atlandı; `pytest tests/test_discover.py` 30 geçti; `pytest -q` tek kırık: `test_certificate_check_handler.py::test_pdf_first_page_is_rendered_at_several_resolutions` — `ModuleNotFoundError: fitz` (yerel ortam, Keşfet dışı); `npm run test` 75 dosya / 1287 test geçti |
| 7 | E2E | N/A | Yapılandırılmış e2e paketi ve Playwright MCP yok; kullanıcı elle test ediyor |
| 8 | Lighthouse | N/A | Lighthouse MCP bu oturumda yok |
| 9 | Erişilebilirlik | N/A | Gate 8'e bağlı; bileşen testleri rol/etiket bazlı sorgularla yazıldı |
| 10 | Güvenlik taraması | INCONCLUSIVE | `scan.py`: `detect-secrets` ve `bandit` kurulu değil (MISSING). Çalıştırıcının "PASS" kararı kanıt değildir |
| 11 | AI code review | PENDING (red-team) | Çalıştırılmadı |
| 12 | Görsel regresyon | N/A | Ekran görüntüsü alınmadı; sayfa tarayıcıda yalnız kullanıcı tarafından açılacak |
| 13 | DAST (ZAP) | N/A | ZAP MCP yok |
| 14 | İnsan onayı | PENDING | Elle test sürüyor |

## Coverage / Quality Notes
- Yetkilendirme matrisi: `tests/authorization/test_discover_authz.py` (kim çağırabilir, yalnız PUBLIC, alan allowlist'i, gizli deneyimden sızıntı, istemci kapsam genişletme, kuruluş dizini).
- Canlı duman testi: anonim `GET /discover/talents` → 401; anonim + bilinmeyen parametre → 401.
- Eksik: ekran görüntüleri, güvenlik tarayıcıları, red-team.
