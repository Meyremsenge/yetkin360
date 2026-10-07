# Test Diff — admin-link-rol-sizintisi
_Reference: atdd.md, plan.md_

## Oluşturulan/Genişletilen Dosyalar
- `backend/tests/test_talent.py` (genişletildi) — `TestGetMe` sınıfına 2 fixture (`platform_admin_user`, `platform_admin_talent`) + 2 test eklendi.
- `frontend/components/app-shell.test.tsx` (genişletildi) — "YET-245" describe bloğu, 6 test.
- `frontend/messages/tr.json` (genişletildi) — `shell.engagementsLink`/`shell.profileLink` eklendi (test dosyalarının referans aldığı sabitler).

## AC → Test eşleşmesi
| AC | Test | Dosya |
|---|---|---|
| AC-1 (happy path admin) | `test_get_me_admin_user_is_platform_admin_true` | backend/tests/test_talent.py |
| AC-1 (happy path admin, frontend render) | `AC-1: is_platform_admin=true iken admin linklerini TAM EŞLEŞMEYLE göster` | frontend/components/app-shell.test.tsx |
| AC-2 (admin değil) | `test_get_me_non_admin_user_is_platform_admin_false` | backend/tests/test_talent.py |
| AC-2 (admin değil, frontend) | `AC-2: is_platform_admin=false iken admin linklerini HİÇ gösterme` | frontend/components/app-shell.test.tsx |
| AC-3 (loading, fail-closed) | `AC-3: isPending=true (loading) iken admin linklerini gösterme` | frontend/components/app-shell.test.tsx |
| AC-4 (null/undefined, fail-closed) | `AC-4: is_platform_admin=undefined ... fail-closed` | frontend/components/app-shell.test.tsx |
| AC-5 (üst bar — Çalışmalarım/Profil) | 2 test (admin olan/olmayan) | frontend/components/app-shell.test.tsx |
| AC-S1 (backend 404 regresyonu) | **Zaten mevcut** — `backend/tests/authorization/test_admin_authz.py` (`test_non_admin_cannot_read_verification_queue_404` vb.) | — |
| AC-S2 (fazla rol alanı yok) | Her iki backend testinin içindeki assertion'lar (`institution_admin_ids`/`org_admin_ids`/`supervisor_institution_ids` not in) | backend/tests/test_talent.py |

## Durum
Testler şu an **red** bekleniyor:
- Backend: `GetMeResponse`/`UserResponse` şemasında `is_platform_admin` alanı yok → `assert "is_platform_admin" in data["user"]` başarısız olacak.
- Frontend: `app-shell.tsx`'te admin linkleri koşulsuz render ediliyor (AC-2/3/4 kırmızı), "Çalışmalarım"/"Profil" linki hiç yok (AC-5 kırmızı).

`code-copilot` bir sonraki adım.
