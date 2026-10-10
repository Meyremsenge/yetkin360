# Verify — sikayet-backend (2026-10-10)

Testler ayrı bir DB'de koşuldu (`TEST_DATABASE_URL` = dev URL + `_sikayet_test`, ayarlardan türetildi, ekrana
basılmadı). Sebep: paralel ajanların ortak `_test` DB'sini oturum başında `DROP … WITH (FORCE)` etmesi.

| Gate | Komut | Sonuç |
|---|---|---|
| Migration başı | `alembic heads` | PASS — tek baş `q7c1m2p3l4n5` |
| Migration ileri/geri | `alembic upgrade head` → `downgrade -1` → `upgrade head` (dev DB) | PASS |
| Kendi testlerim | `pytest tests/test_complaints.py tests/authorization/test_complaints_authz.py` | PASS — 150/150 |
| Yetkilendirme paketi | `pytest tests/authorization -q` | 1321 geçti, 9 skip, **2 kırık** (bana ait değil, aşağıda) |
| Tüm paket | `pytest -q --ignore=tests/test_certificate_check_handler.py` | 2186 geçti, 10 skip, **2 kırık** (aynı ikisi) |
| Lint | `ruff check .` | PASS |
| Tip | `mypy app` | PASS (87 dosya) |
| Güvenlik (security-scan) | — | N/A — çalıştırılmadı (orkestratör kapsamı dışı) |

Kırıklar (kaynak: kullanıcının commit'lenmemiş `backend/app/services/engagement.py` değişikliği — talent'a görev
oluşturma izni; bu pakete ait değil, dokunulmadı):
- `test_multi_role_self_dealing.py::TestMultiRoleSelfDealingScenario19::test_s_create_task_on_own_e2_active_403` (201 ≠ 403)
- `test_multi_role_self_dealing.py::TestMultiRoleSelfDealingScenario22::test_m_create_task_member_not_admin_403`

Toplanamayan: `tests/test_certificate_check_handler.py` — `ModuleNotFoundError: cv2` (venv'de opencv yok; önceden var olan ortam sorunu).

Değiştirilen mevcut testler (sözleşme bilinçli genişledi):
- `test_admin_router_gate.py`: `GATED_ROUTERS`'a `admin_complaints_router` eklendi (yeni /admin router'ı da gate'li olmalı).
- `test_discover_authz.py`: `ORGANIZATION_CARD_FIELDS`'a `upheld_complaint_count` eklendi (C7).

Refactor adayı: `services/complaint.py` ~700 satır; ek yükleme kısmı ayrı modüle bölünebilir — davranış değişikliği
gerektirmez, şimdilik bırakıldı.
