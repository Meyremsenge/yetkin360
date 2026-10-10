# Verify — admin-kullanici-kurulus-kurum-yonetimi (2026-10-10)

| Kapı | Komut | Sonuç |
|---|---|---|
| Paket backend testleri | `pytest tests/authorization/test_admin_directory_authz.py tests/authorization/test_admin_router_gate.py -q` | 148 geçti, 1 kırık (aşağıda) |
| Yetkilendirme paketi tamamı | `pytest tests/authorization -q` | 1193 geçti, 9 atlandı, 5 kırık, 85 error — **hiçbiri bu paketin dosyalarında değil** |
| Lint | `ruff check .` | PASS |
| Tip | `mypy app` | PASS (83 dosya) |
| Frontend lint | `npm run lint` | PASS (0 hata, 7 uyarı — hepsi başka dosyalarda) |
| Frontend tip | `npm run typecheck` | PASS |
| Vitest | `vitest run lib/api/admin-directory.test.ts app/admin/{kullanicilar,kuruluslar,kurumlar} app/admin/page.test.tsx components/app-shell.test.tsx` | 52/52 PASS |
| Security-scan / vision-test / e2e | — | N/A (çalıştırılmadı; dev server başlatma yasak) |

## Kırıkların sahibi
- `test_admin_router_gate.py::test_no_admin_path_is_served_outside_the_gated_router` — fark yalnız
  `GET /admin/audit-events` ve `GET /admin/fraud-flags/history` (+ şikayet uçları): başka ajanların router'ları
  `GATED_ROUTERS` listesine eklenmemiş. Bu paketin uçları listede ve geçiyor.
- `test_complaints_authz.py` (85 error + 1 fail) — şikayet ajanının yarım işi (`POST /complaints` TypeError).
- `test_multi_role_self_dealing.py` (2) — kullanıcının commit'lenmemiş `services/engagement.py` değişikliği alanı.
- `test_reminder_outbox_limits.py` (1) — `OperationalError` /institutions/{id}/reminders; bu paketle ilgisiz.

## Refactor adayı
`api/admin_directory.py`'deki `_call(fn, *args)` yardımcı fonksiyonu tip güvenliğini kaybediyor
(`type: ignore`). İstisna eşlemesi bir FastAPI exception handler'a taşınabilir — davranış değişmez.
