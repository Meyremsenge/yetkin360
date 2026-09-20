# Test Report — yet-2-yetkilendirme-cekirdegi

## Gerçek Postgres'e karşı (docker-compose, healthy)
- `pytest tests/ -q` → **61 passed** (10 önceki + 30 test_authorization.py + 21 test_audit_events.py)
- `ruff check .` → All checks passed
- `mypy app` → Success: no issues found in 12 source files
- `alembic downgrade -1` → hatasız, `a1b2c3d4e5f6 -> b82aa928fbd2`
- `alembic upgrade head` (round-trip) → hatasız, `b82aa928fbd2 -> a1b2c3d4e5f6`
- `pytest tests/ -q` (round-trip sonrası tekrar) → 61 passed

## code-copilot'un ilk teslimatında bulunan ve düzeltilen gerçek hatalar
(Alt-ajanın kendi raporu "Postgres kurulu değil, testler çalıştırılamadı" diyordu — bu YANLIŞTI, container zaten healthy çalışıyordu. Orkestratör bu iddiaya güvenmedi, testleri bizzat çalıştırdı ve gerçek hatalar buldu.)

1. **Trigger yanlış exception sınıfı fırlatıyordu** (implementasyon hatası): `RAISE EXCEPTION` SQLSTATE belirtmeden yazılmıştı, psycopg/SQLAlchemy bunu `ProgrammingError` olarak sınıflandırıyordu ama testler `IntegrityError` bekliyordu. Düzeltme: `USING ERRCODE = 'integrity_constraint_violation'` eklendi. 4 test etkilendi, hepsi düzeldi.
2. **mypy hatası**: `authorization.py`'de üç fonksiyon `select` (fonksiyon) ile dönüş tipi anotasyonu yapıyordu, geçerli bir tip değil. Düzeltme: `Select` (sınıf) import edilip kullanıldı.
3. **Test dosyasında 4 adet UUID/tipli-nesne karşılaştırma hatası** (test hatası, implementasyon doğruydu): `audit_row.actor_user_id`/`actor_ip`/`subject_id` gerçek Python nesneleri (`uuid.UUID`, `ipaddress.IPv4Address`) olarak dönüyor, testler bunları düz string ile karşılaştırıyordu. Düzeltme: `str(...)` sarmalayıcısı eklendi.
4. **Test dosyasında geçersiz test verisi**: `subject_id="/api/users"` geçerli bir UUID değil, şema ihlali. Düzeltme: gerçek bir UUID string'ine çevrildi.
5. **Ruff: kullanılmayan import'lar** (`text`, `IntegrityError`, `select`) test dosyasında — kaldırıldı.

## Bilinen zayıf testler (test_diff.md'de zaten not düşülmüştü, red-team'e taşınıyor)
- `test_scoped_talent_profiles_tenant_isolation`: gerçek bir çapraz-kiracı (Institution A/B) izolasyon iddiası yapmıyor, sadece kendi profilinin döndüğünü doğruluyor.
- `test_get_scoped_or_404_out_of_scope_and_nonexistent_same_result`: aynı `scoped_select` nesnesini iki kez çalıştırıyor, iki farklı senaryoyu gerçek farklı veri kurulumlarıyla ayırt etmiyor.

## Doğrulanamayan
Yok — bu görevde her şey gerçek Postgres'e karşı doğrulandı.
