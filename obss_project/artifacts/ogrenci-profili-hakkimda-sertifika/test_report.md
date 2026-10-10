# test_report — ogrenci-profili-hakkimda-sertifika (backend)

| Komut | Sonuç |
|---|---|
| `pytest tests/authorization -q` | 976 passed, 9 skipped (skip'ler önceden var) |
| `pytest -q --ignore=tests/authorization --ignore=tests/test_certificate_check_handler.py` | 735 passed, 1 skipped |
| `tests/test_certificate_check_handler.py` | toplanamadı: ortamda `cv2` yok (PLAN 3.55 bağımlılığı, bu değişiklikle ilgisiz) |
| `alembic upgrade head` → `downgrade -1` → `upgrade head` | başarılı |
| `ruff check` (değişen dosyalar) | temiz |
| `mypy app` | 4 hata — hepsi önceden var (`rowcount`, evaluation/engagement/attestation) |

Güncellenen mevcut testler: 3 public alan allowlist testi (`about`, `certificates` eklendi — onaylı tasarım §4.4). Yerine `test_public_certificate_keys_are_an_exact_allowlist` öğe düzeyinde birebir allowlist ekledi.

## Red-team sonrası
- Bulgu 1 (medium, evidence_id silinen kayıtta kilitli kalıyordu) düzeltildi: soft delete `evidence_id`'yi boşaltır. Test: `test_deleted_item_releases_its_evidence`.
- Yeniden çalıştırma: `pytest tests/authorization -q` → 977 passed, 9 skipped.
