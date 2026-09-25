# Security Scan — public-profil-endpoint

## Kapsam
`backend/app/api/public.py`, `backend/app/services/visibility_service.py`, `backend/app/services/authorization.py`, `backend/app/main.py`, `backend/tests/test_public_profile.py`, `backend/tests/authorization/test_public_profile_authz.py`

## Gate Sonuçları
| Gate | Sonuç | Not |
|---|---|---|
| secrets (detect-secrets) | PASS | 0 bulgu |
| python_sast (bandit) | PASS | 0 bulgu |
| python_deps (pip-audit) | N/A | Tarayıcı proje kökünde (`.`) bağımlılık manifesti bulamadı — `backend/requirements.txt` var ama araç repo kökünden çalıştırıldı. Kapsam dışı, blocking değil. |
| node_deps | N/A | package.json yok (backend-only görev) |

**Verdict: PASS** (0 çıkış kodu)

Not: Bu, sadece bilinen imza taramasıdır — iş mantığı/IDOR açıkları için `authz-test` (bu görevde zaten çağrıldı, atdd.md'ye AC-S1/S2/S3 olarak işlendi) ve `red-team` geçerli.
