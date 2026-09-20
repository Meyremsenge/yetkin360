# Plan — yet-3-yetkilendirme-test-iskeleti
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, UI/component dosyası yok).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/tests/test_authorization.py | İçeriği `tests/authorization/` paketine taşınacak, sonra silinecek (AC-2) — CLAUDE.md'nin dosya silme onay kuralı gereği silme işlemi kullanıcıya ayrıca bildirilecek | medium |

## New Files
| File | Purpose |
|------|---------|
| backend/tests/authorization/__init__.py | Paket işareti (boş) |
| backend/tests/authorization/conftest.py | Ortak fixture'lar: Org A/B, Talent A/B, ilgili `User`/`OrganizationMember`/`Principal` nesneleri + `session` fixture'ı (mevcut `test_authorization.py`'den taşınır) + "boş matris = FAIL" collection guard'ı (AC-5) |
| backend/tests/authorization/test_matrix.py | `pytest.mark.parametrize` ile docs/AUTHORIZATION.md formatında (aktör, kaynak, eylem, beklenen) matris satırları — mevcut `can()`/`scoped_organizations()`/`scoped_talent_profiles()` yüzeyinin test edilebilir alt-kümesi (AC-1, AC-2, AC-6) |
| backend/tests/authorization/test_can_defaults.py | `can()`'ın default-deny/AC-S1 testleri — YET-2'den taşınan parametrize `kind_value` testi burada yaşar |

## Dependencies
- `backend/app/services/authorization.py` — `Principal`, `can()`, `scoped_organizations()`, `scoped_talent_profiles()`, `get_scoped_or_404()` (okunur, değiştirilmez)
- `backend/app/models/identity.py` — `User`, `Organization`, `OrganizationMember`, `TalentProfile`, `Institution`, `InstitutionMember` (fixture'lar için)
- `docs/AUTHORIZATION.md` §5 — matris formatının kaynağı (okunur, değiştirilmez)
- Mevcut `backend/tests/test_authorization.py` — içerik kaynağı, taşınacak

## Migration Required?
Hayır — sadece test dosyaları, şema değişikliği yok.

## Risks
- (atdd.md'den) `test_authorization.py`'nin silinmesi CLAUDE.md'nin onay kuralına tabi — bu adımı code-copilot/test-copilot **silmeden önce** kullanıcıya bildirecek, otomatik silmeyecek.
- Fixture'ların (Org A/B, Talent A/B) `conftest.py`'ye taşınması sırasında testler arası izolasyon (her testin kendi transaction'ı, `test_authorization.py`'deki mevcut `session` fixture deseni) korunmalı — authz-test ilkesi (YET-2'den): "boş liste PASS'e çevrilmez" testleri de taşınmalı, kaybolmamalı.

## Open Questions
(Boş — repo keşfi atdd.md'deki tüm varsayımları doğruladı: `can()`/`scoped_*()` mevcut, `test_authorization.py` mevcut ve taşınabilir durumda, CI `pytest -q` ile yeni paketi otomatik keşfedecek (pytest.ini'de testpaths kısıtı yok, sadece ruff/mypy config var), pytest zaten kurulu. Test framework netleşti: pytest + gerçek Postgres (mevcut desen).)
