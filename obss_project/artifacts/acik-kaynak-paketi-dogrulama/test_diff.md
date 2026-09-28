# Test Diff — acik-kaynak-paketi-dogrulama

## Oluşturulan dosyalar
- `backend/tests/test_repo_packaging.py` (yeni) — 5 repo-hijyeni regresyon testi.

## AC Eşlemesi
| AC | Test Fonksiyonu | Beklenen durum (red step) |
|---|---|---|
| AC-1 (happy path kurulum) | `test_env_example_exists_at_repo_root`, `test_env_file_is_gitignored`, `test_readme_lists_required_env_example_step` | PASS |
| AC-2 (sır taraması altyapısı) | `test_secrets_baseline_exists` | PASS |
| AC-3 (stale/yanlış kurulum adımı tespiti) | `test_readme_does_not_claim_env_example_missing` | **FAIL (bilerek — kırmızı)** |
| AC-7 satırı (tarama config sağlamlığı) | `test_secrets_baseline_exists` | PASS |

## Not
Bu görev klasik unit/integration/e2e piramidine uymuyor (atdd.md Test Strategy: %70 manuel temiz-ortam kurulumu + %30 otomatik secret-scan). `test_repo_packaging.py`, o %30'un otomatikleştirilebilir küçük dilimini (repo-hijyeni regresyon koruması) kapsıyor — gerçek `detect-secrets` taraması `security-scan` skill'inin (verify aşamasında) işi, burada tekrarlanmadı.

`test_readme_does_not_claim_env_example_missing` şu an kırmızı — plan.md'de bulunan gerçek stale README satırını (README.md:138) doğruluyor. `code-copilot` bu satırı düzeltince yeşile dönmesi beklenir.
