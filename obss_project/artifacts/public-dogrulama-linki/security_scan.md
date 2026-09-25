# Security Scan — public-dogrulama-linki

## Kapsam
`backend/app/api/public.py`, `backend/app/services/verified_experience.py`, `backend/app/services/authorization.py`, `backend/app/models/verified_experience.py`, `backend/alembic/versions/m4n5o6p7q8r9_...`, `backend/tests/test_public_verification.py`, `backend/tests/authorization/test_public_verification_authz.py`

## Gate Sonuçları
| Gate | Sonuç | Not |
|---|---|---|
| secrets (detect-secrets) | PASS | İlk koşumda test dosyalarında 5 "Base64 High Entropy String" bulgusu çıktı — incelendi, hepsi test fixture'larındaki kurgusal `public_token` string'leri (`"test_token_..."` öneki, gerçek servisle ilişkisi yok). `--accept-secrets` ile baseline'a kaydedildi. |
| python_sast (bandit) | PASS | 0 bulgu |
| python_deps (pip-audit) | N/A | Tarayıcı proje kökünde bağımlılık manifesti bulamadı (bkz. YET-105'te aynı not) |
| node_deps | N/A | package.json yok |

**Verdict: PASS**

Not: Sadece bilinen imza taraması. IDOR/enumeration için `authz-test` (bu görevde çağrıldı, atdd.md'ye AC-S2 olarak işlendi) ve `red-team` geçerli.
