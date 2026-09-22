# Verify Report — yet-8-institution-koordinator-ogrenci-bagi
_Reference: atdd.md, plan.md, code_diff.md, test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short backend/app backend/tests backend/alembic` → plan.md/code_diff.md'nin listelediği tüm dosyalar diskte (yeni: api/, models/institution_link_request.py, services/institution.py, tests/conftest.py + 2 test dosyası, migration; değişen: main.py, models/__init__.py, services/authorization.py). |
| 2 | Build/derleme | PASS | `mypy app` zaten import-sanity'yi kapsıyor (aşağıya bak) — ayrıca `pytest` collection'ı hatasız (import hatası yok). |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase kullanmıyor (PostgreSQL + SQLAlchemy/Alembic, doğrudan). |
| 4 | Lint | PASS | `ruff check .` (CI'nin birebir komutu) → "All checks passed!". Formatter: `pyproject.toml`'da `[tool.ruff]` sadece lint ayarı, ayrı format ayarı yok → format kontrolü N/A (proje tanımlamıyor). |
| 5 | Type check | PASS | `mypy app` (CI'nin birebir komutu) → "Success: no issues found in 16 source files". code-copilot sürecinde 2 gerçek tip hatası bulunup düzeltildi (`get_session`'ın generator dönüş tipi, `approve_institution_link`'e `UUID \| None` geçirilmesi). |
| 6 | Unit testler | PASS | `pytest tests/test_institution.py tests/test_institution_authorization.py tests/authorization -q` (gerçek Postgres'e karşı, docker compose) → **67 passed, 6 skipped (YET-7/8/9 için gerekçeli, YET-3'ten devralınan), 0 failed**. Her AC en az bir testle kapsanıyor (aşağıdaki eşleme). |
| 7 | E2E testler | N/A | Ayrı bir e2e suite yok; FastAPI `TestClient` ile yazılan HTTP-seviyesi testler zaten gate 6'da uçtan uca (router→service→DB) çalışıyor, bu görevin kapsamında web UI yok. |
| 8 | Lighthouse (performans) | N/A | Web UI yok, sadece backend API. |
| 9 | Erişilebilirlik | N/A | Aynı gerekçe. |
| 10 | Güvenlik taraması | PASS | `security-scan` skill'i değişen 9 dosyaya karşı çalıştırıldı: `secrets: PASS`, `python_sast (bandit): PASS`, `python_deps: N/A` ("Python bağımlılık manifesti yok" — `requirements.txt` scope'ta olmasına rağmen scanner tanımadı, araç kısıtı olarak not edildi, gerçek bir eksiklik değil çünkü bu görev yeni bağımlılık eklemedi). **Verdict: PASS.** |
| 11 | AI code review | PENDING (red-team) | Sıradaki adım. |
| 12 | Görsel regresyon | N/A | Web UI yok. |
| 13 | DAST (ZAP) | N/A | Web UI yok; threat-model'in ürettiği AC-S1/AC-S2 kriterleri HTTP yüzeyine değil (henüz gerçek auth yok, `X-Debug-User-Id` geçici) servis+router katmanına ait, gerçek bir prod-benzeri hedef yok. |
| 14 | İnsan onayı | PENDING | Her zaman son adım. |

## Migration Doğrulaması (CLAUDE.md zorunlu kılıyor)
- `alembic upgrade head` → PASS (gerçek Postgres'e karşı, `institution_link_requests` tablosu oluşturuldu).
- `alembic downgrade -1` → PASS (tablo temiz şekilde geri alındı).
- `alembic upgrade head` (tekrar) → PASS (yeniden uygulanabilir).
- Testler downgrade/upgrade döngüsünden sonra tekrar çalıştırıldı → **67 passed, 6 skipped, 0 failed** (bozulma yok).

## AC -> Test Mapping
1. AC-1 (kurum oluşturma) → `test_create_institution_basic`, `test_create_institution_without_domain` → **PASS**
2. AC-2 (üye davet) → `test_admin_invites_coordinator`, `test_admin_invites_admin` → **PASS**
3. AC-3 (öğrenci bağ isteği, PENDING) → `test_student_requests_link_creates_pending` → **PASS**
4. AC-3b (koordinatör/admin onayı) → `test_coordinator_approves_link_request`, `test_admin_approves_link_request` → **PASS**
5. AC-4/AC-S1 (COORDINATOR ADMIN-only eylemi yapamaz, 404) → `test_coordinator_invite_member_denied_404`, `test_coordinator_cannot_invite_any_role[ADMIN/COORDINATOR]` → **PASS**
6. AC-5/AC-S2 (BOLA — çapraz kurum erişimi 404) → `test_coordinator_a_cannot_invite_to_institution_b`, `test_admin_a_cannot_invite_to_institution_b`, `test_coordinator_a_cannot_approve_link_request_for_b`, `test_admin_a_cannot_approve_link_request_for_b` → **PASS**
7. AC-6 (aynı domain, 409) → `test_duplicate_domain_returns_409` → **PASS**
8. AC-7 (var olmayan kurum, 404) → `test_invite_member_to_nonexistent_institution` → **PASS**
9. AC-8 (tekrar eden PENDING istek, 409) → `test_duplicate_pending_link_request_409` → **PASS**
10. `can()`/`scoped_institutions()`/`get_scoped_or_404()` unit testleri (Institution-özel) → `TestCanFunctionInstitution`, `TestScopedInstitutions`, `TestGetScopedOr404Institution` → **PASS**

## Coverage / Quality Notes
- Tüm AC'ler (happy path + 4 edge case + 2 AC-S) en az bir testle kapsanıyor — boşluk yok.
- code-copilot sürecinde bulunup düzeltilen gerçek bir **privilege-escalation açığı** vardı (çoklu-kurum senaryosunda global `kind` bayrağına güvenme) — bu, tam da bu testlerin (`test_coordinator_a_cannot_invite_to_institution_b`, `test_admin_a_cannot_invite_to_institution_b`) yakalaması gereken sınıftan bir hataydı ve gerçekten yakalandı (test-first sürecinin kendisi bunu doğruladı — testler yazılmadan bu açık fark edilmezdi).
- Test dosyaları (`test_institution.py`, `test_institution_authorization.py`) artık `X-Debug-User-Id` header'ını açıkça gönderiyor — gerçek `get_current_principal` implementasyonunu test ediyor (mock değil), bu daha güvenilir bir test deseni.

## Refactor Aday Kontrolü
Somut bir aday **yok**: `invite_member_endpoint`/`approve_link_request_endpoint`'teki yetki kontrolü mantığı (`principal.kind` + `institution_admin_ids`/`scoped_institutions` kombinasyonu) biraz tekrar içeriyor ama iki endpoint arasında sadece 3-4 satırlık, ölçülebilir bir "sihirli tekrar" eşiğine ulaşmıyor (ponytail: varsayılan "dokunma"). Derin nesting, uzun parametre listesi veya ölü kod yok. Diff CAVEMAN ilkelerine zaten uygun.

## Red-Team Sonrası Güncelleme
`red-team` (verdict: approve-with-changes) 4 bulgu buldu, hepsi düzeltildi: (1) `approve_link_request_endpoint`'in ilk yetki kapısı global `kind` yerine per-kurum `institution_ids` kontrolüne geçirildi, (2) `Principal.kind`'ın yetkilendirme kararları için tek başına kullanılmaması gerektiği docstring'e eklendi, (3) tek-kullanıcı-çoklu-kurum-karışık-rol regresyon testi eklendi, (4) çıplak select'in kasıtlı olduğu yoruma bağlandı. Bağımsız olarak yeniden doğrulandı: **68 PASS, 6 SKIP, 0 FAIL**, ruff/mypy temiz.

## Sonuç
**Tüm zorunlu gate'ler yeşil, red-team bulguları kapatıldı.** Migration doğrulandı (upgrade+downgrade+re-upgrade), güvenlik taraması temiz, 68 test PASS. Commit'e hazır (insan onayı — gate 14 — hâlâ ayrı ve zorunlu).
