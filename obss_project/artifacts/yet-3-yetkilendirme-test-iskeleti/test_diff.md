# Test Diff — yet-3-yetkilendirme-test-iskeleti

## Oluşturulan Dosyalar
- `backend/tests/authorization/__init__.py` (yeni, boş paket işareti)
- `backend/tests/authorization/conftest.py` (yeni) — ortak `session` fixture'ı (YET-2'den taşındı) + Org A/B, Talent A/B fixture'ları + AC-5 "boş matris = FAIL" guard (`pytest_collection_modifyitems`)
- `backend/tests/authorization/test_can_defaults.py` (yeni) — `can()` default-deny testleri
- `backend/tests/authorization/test_matrix.py` (yeni) — parametrize matris + tenant izolasyonu + placeholder skip'ler

`backend/tests/test_authorization.py` (mevcut, eski) **henüz silinmedi** — CLAUDE.md'nin dosya silme onay kuralı gereği, silme kararı kullanıcıya soruluyor (bkz. aşağıdaki not).

## Acceptance Criteria → Test Eşlemesi
| AC | Test |
|---|---|
| AC-1 | `test_matrix.py::TestPrincipalAcceptsAllKindValues::test_principal_accepts_kind` (9× parametrize) |
| AC-2 | `test_matrix.py::TestScopedFunctionsReturnSelectObjects` (2 test) |
| AC-3 | `test_matrix.py::TestCanTrueForOwnResourceFalseForOthers` (2 test) |
| AC-4 | `test_matrix.py::TestFutureResourcesPlaceholders` (6 gerekçeli `pytest.skip`) |
| AC-5 | `conftest.py::pytest_collection_modifyitems` (boş koleksiyon → `pytest.exit`) |
| AC-6 / AC-S1 | `test_can_defaults.py` — 9×kind + bilinmeyen resource türü (default-deny) |
| AC-S2 | `test_matrix.py::TestTenantIsolationOrganizations` + `TestTenantIsolationTalentProfiles` |
| AC-S4 | `test_matrix.py::TestGetScopedOr404` (3 test) |
| AC-S5 | `test_matrix.py::TestCanDefenseInDepth` (2 test) |

Collection sonucu: **45 test** toplandı (39 çalıştırılabilir + 6 gerekçeli skip). Alt-ajan `can()`/`scoped_*()` mevcut implementasyona karşı çalıştırıp (bu görev yeni iş mantığı yazmıyor, sadece mevcut YET-2 kodunu yeniden organize ediyor) 9 AC-1 testinin PASS, 6 AC-4 testinin SKIPPED olduğunu doğruladı — implementasyon zaten var olduğu için bu görevde klasik "red" beklenmiyor (bkz. atdd.md Davranış Sözleşmesi, satır 1 "Happy path").

## Bekleyen Karar (kullanıcıya sorulacak)
`backend/tests/test_authorization.py` (eski dosya) içeriği yeni pakete taşındı ve genişletildi. CLAUDE.md: "Dosya/klasör silme... önce açık onay al." Silinsin mi, yoksa geçiş dönemi için ikisi birden mi dursun (geçici çakışma riski: iki dosyada da aynı testler — CI'da toplam test sayısı şişer ama davranış çakışmaz)?
