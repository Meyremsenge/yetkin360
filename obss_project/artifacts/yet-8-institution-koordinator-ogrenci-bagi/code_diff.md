# Code Diff — yet-8-institution-koordinator-ogrenci-bagi

## Oluşturulan Dosyalar
- `backend/app/api/deps.py` — `get_session`, `get_current_principal` (GEÇİCİ stub, YET-4 gelince JWT ile değişecek; `X-Debug-User-Id` header'ından gerçek DB sorgusuyla Principal kurar)
- `backend/app/models/institution_link_request.py` — `InstitutionLinkRequest` modeli (PENDING/APPROVED/REJECTED, partial unique index)
- `backend/app/services/institution.py` — `create_institution`, `invite_member`, `request_institution_link`, `approve_institution_link`
- `backend/app/api/institutions.py` — 4 endpoint (AC-1, AC-2, AC-3, AC-3b)
- `backend/tests/conftest.py` — paylaşılan `session`/`client` fixture'ları (sadeleştirildi, aşağıya bak)
- `backend/alembic/versions/c5d6e7f8g9h0_institution_link_requests.py` — yeni migration (kullanıcı onayı alındı)

## Değiştirilen Dosyalar
- `backend/app/services/authorization.py` — `scoped_institutions()` eklendi, `can()`'a Institution dalı eklendi, `Principal`'a `institution_admin_ids` alanı eklendi (default `[]`, dataclass sonuna taşındı — geriye uyumlu). **Mevcut YET-2 fonksiyonlarının davranışı değişmedi.**
- `backend/app/main.py` — institutions router include edildi
- `backend/app/models/__init__.py` — `InstitutionLinkRequest` export edildi

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar (önemli — şeffaflık için kaydediliyor)
1. **Gerçek privilege-escalation açığı (kritik, code-copilot'un ilk turunda bulundu, kod hiç commit edilmeden düzeltildi):** İlk implementasyon `invite_member_endpoint`'in yetkisini `principal.kind == "INST_ADMIN"` GLOBAL bayrağıyla kontrol ediyordu. `deps.py`'deki `kind`, kullanıcının TÜM kurumlar arasındaki "en yüksek yetkisi" olarak hesaplanıyor — bir kullanıcı Kurum A'da ADMIN, Kurum B'de sadece COORDINATOR ise, global `kind="INST_ADMIN"` olup Kurum B'ye de ADMIN-only eylemi (üye davet) yapabiliyordu. Düzeltme: `Principal`'a `institution_admin_ids` (per-kurum admin listesi, `org_admin_ids` ile simetrik) eklendi, `can()` ve `invite_member_endpoint` artık global `kind` yerine bu per-kurum listeyi kontrol ediyor.
2. **Regresyon (bu düzeltmenin kendi hatası, hemen yakalanıp düzeltildi):** `institution_admin_ids` alanı ilk eklendiğinde default değeri yoktu — bu, merge edilmiş YET-3'ün 39 testini kırdı (`Principal(...)` çağıran her yer bu yeni zorunlu alanı bilmiyordu). Alan default'lu hale getirilip dataclass'ın sonuna taşındı, `pytest tests/authorization -q` tekrar 41 PASS/6 SKIP oldu.
3. **`institution_link_requests` model tanım hatası:** `UniqueConstraint(postgresql_where=...)` SQLAlchemy'de desteklenmiyor — `Index(unique=True, postgresql_where=text(...))` ile değiştirildi (model + migration).
4. **`decided_at` her zaman `None` yazılıyordu** (audit alanı boş bırakılıyordu) — gerçek zaman damgasıyla (`datetime.now(UTC)`) düzeltildi.
5. **Test fixture kırılganlığı:** İlk `conftest.py`, "hangi kullanıcı çağırıyor" bilgisini fixture isimlerini tahmin ederek buluyordu — birden fazla user fixture'ı olan testlerde yanlış kullanıcı seçiliyordu. Kalıcı çözüm: testler artık `X-Debug-User-Id` header'ını AÇIKÇA gönderiyor, `get_current_principal` override'ı kaldırıldı (gerçek implementasyon test ediliyor, daha güvenilir).
6. **mypy: 2 tip hatası** (`get_session`'ın generator dönüş tipi, `approve_institution_link`'e `UUID | None` geçirilmesi) — düzeltildi.

## Kalan Sınırlamalar
- Gerçek JWT auth (YET-4) henüz yok — `X-Debug-User-Id` production'a asla gitmemeli, YET-4 tamamlanınca `get_current_principal` gerçek token doğrulamasıyla değiştirilmeli.
- Davet e-postası (`outbox` deseni) implement edilmedi — atdd.md'de zaten kapsam notu olarak işaretli, bu görevin AC'lerinde zorunlu değildi.
- T2-T4 doğrulama seviyeleri kapsam dışı (sadece T1).

## Doğrulama (bağımsız olarak tekrar tekrar çalıştırıldı)
- `pytest tests/test_institution.py tests/test_institution_authorization.py tests/authorization -q` → **67 passed, 6 skipped, 0 failed**
- `ruff check .` → All checks passed!
- `mypy app` → Success: no issues found in 16 source files
- `alembic upgrade head` → migration başarıyla uygulandı, gerçek Postgres'e karşı test edildi
