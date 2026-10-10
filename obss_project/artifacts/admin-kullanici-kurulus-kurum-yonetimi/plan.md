# Plan — admin-kullanici-kurulus-kurum-yonetimi

Kaynak: `atdd.md` (aynı klasör). Migration yok. `admin.py`, `admin.ts`, mevcut admin sayfaları değişmez.

## Keşif bulguları
- `users.status` CHECK: `PENDING, ACTIVE, SUSPENDED, DELETED` → U2 şemaya uygun.
- `organizations.status`, `institutions.status`: CHECK yok (ilk migration `b82aa928fbd2`, model `identity.py`).
- Auth katmanı SUSPENDED'ı zaten reddediyor: `core/deps.py:45` (access token → 401),
  `services/auth.py:501` (login), `services/auth.py:645` (refresh). Kimlik doğrulama koduna dokunmak gerekmiyor.
- `tests/authorization/test_admin_router_gate.py::test_no_admin_path_is_served_outside_the_gated_router`
  `/admin` yollarını yalnız `admin.router`'dan bekliyor → ikinci gated router eklenince kırılır;
  test, gated router listesini kapsayacak şekilde genişletilir (koruma zayıflamaz, yeni uçlar da matrise girer).
- Test `client` fixture'ı `get_current_user`'ı override ediyor ve durumu kontrol etmiyor → "askıdaki eski
  admin" ve AC-S6 testi gerçek `get_current_user` + gerçek access token ile yazılır.

## Dosya etkisi
| Dosya | İş |
|---|---|
| `backend/app/services/admin_directory.py` (yeni) | `list_users/organizations/institutions` (limit+1), `set_user_suspended`, `set_organization_suspended`, `set_institution_suspended`, `set_institution_verification_level`; her yazma aynı oturumda `log_audit_event`; servis girişinde `is_platform_admin` tekrar kontrol edilir |
| `backend/app/api/admin_directory.py` (yeni) | Router (`/admin`, `require_platform_admin`), Pydantic şemaları, hata eşlemesi |
| `backend/app/main.py` | 1 import + 1 `include_router` |
| `backend/tests/authorization/test_admin_directory_authz.py` (yeni) | rol × uç matrisi, kombinasyonlar, AC-S6/S7/S8, AC-11 |
| `backend/tests/authorization/test_admin_router_gate.py` | gated router listesi |
| `frontend/lib/api/admin-directory.ts` + test (yeni) | API client |
| `frontend/components/admin/{confirm-dialog,directory-ui}.tsx` (yeni) | onay diyaloğu, sayfalama/arama ortak parçaları |
| `frontend/app/admin/{kullanicilar,kuruluslar,kurumlar}/page.tsx` + test (yeni) | ekranlar |
| `frontend/components/app-shell.tsx`, `frontend/messages/tr.json` | 3 bağlantı satırı, 3 ad alanı + 3 `shell` anahtarı |
| `docs/API.md`, `docs/AUTHORIZATION.md` | yalnız yeni uç satırları |

## Sıra
1. Backend testleri (kırmızı) → servis + router + main.py (yeşil).
2. Frontend client testi + sayfa testleri (kırmızı) → client + sayfalar (yeşil).
3. Doküman satırları. 4. verify.

## Son-admin kilidi
Aktif platform admin satırları `ORDER BY id FOR UPDATE` + `populate_existing` ile kilitlenir; kilit sonrası
aktör hâlâ aktif admin değilse veya hedef dışında aktif admin kalmıyorsa `409`. İki adminin birbirini
eşzamanlı askıya alması bu sayede sıfır adminle bitmez.
