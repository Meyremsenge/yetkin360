# Code Diff — yet-3-yetkilendirme-test-iskeleti

## Değişiklik: YOK

**Sebebi:** atdd.md'nin "Kapsam Dışı" bölümü açıkça `can()`/`scoped_*()`'in iş mantığının genişletilmesini bu görevin dışında bırakıyor — YET-3 sadece **mevcut** authorization.py yüzeyini test eder, yeni yetki kararı yazmaz. `git status --short backend` doğrulandı: sadece test dosyaları değişti (`backend/tests/authorization/` yeni, `backend/tests/test_authorization.py` silindi), `backend/app/` altında hiçbir dosya dokunulmadı.

## Doğrulama (code-copilot alt-ajanı tarafından)
- `pytest tests/authorization -v --collect-only` → 45 test, collection hatasız.
- Import doğrulaması (`conftest`, `test_can_defaults`, `test_matrix`, `app.services.authorization`) → temiz.
- Fixture'ların kullandığı model alanları (`Organization.legal_id`, `TalentProfile.visibility`/`user_id`/`full_name`, `OrganizationMember` alanları, `User` alanları) gerçek `app/models/identity.py` ile karşılaştırıldı → hepsi mevcut.
- Gerçek Postgres'e karşı tam çalıştırma yapılamadı (bu ortamda DB bağlantısı/Docker kurulu değil) — **bu, `verify` adımında CI'nın (gerçek Postgres servisiyle) yapması gereken iş**, code-copilot'un eksikliği değil.

## Kalan Sınırlama
Testlerin gerçek Postgres'e karşı PASS ettiği bu oturumda doğrulanamadı (bağlantı yok). `verify` adımı bunu CI ortamında veya `docker compose up -d` sonrası doğrulamalı.
