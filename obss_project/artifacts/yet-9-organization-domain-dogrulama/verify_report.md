# Verify Report — yet-9-organization-domain-dogrulama
_GÜNCELLEME (2. tur): Aşağıdaki ilk tur FAIL'lerinden sonra 3 ek Haiku
dispatch'i yapıldı (2× code-copilot: `DomainVerifyRequest` varsayılan değer +
lint temizliği + AC-S5 verify-domain'de de hostname doğrulaması eksikliği;
1× test-copilot: audit action-isim varsayımları, free-email domain test
verisi hatası, TXT-mock format uyumsuzluğu, eksik DNS mock'ları). Her
dispatch sonrası orkestratör BAĞIMSIZ OLARAK (`Bash` ile, alt-ajan raporuna
güvenmeden) `ruff check .`, `mypy app`, `pytest tests/test_organization.py
tests/test_organization_authorization.py -v` ve son olarak proje geneli
`pytest -q` (regresyon) çalıştırdı._

**SONUÇ (2. tur): Gate 4 ve Gate 6 artık PASS.** Detay ve gerekçeler için
altta orijinal 1. tur analizini (kök neden A/B/C) referans olarak koru —
o analiz doğru teşhisti, düzeltmeler ona göre yapıldı. Ek olarak 1. tur
sonrası ikinci bir doğrulama turunda 5 YENİ gerçek sorun daha bulundu
(bunlar 1. turda `DomainVerifyRequest` 422 hatası tüm akışı maskelediği
için görünmüyordu): audit action-isim uyumsuzluğu (test varsayımı),
free-email test verisi hatası (test bug), TXT-mock format uyumsuzluğu
(test bug), AC-9 testinde eksik DNS mock (test bug), ve **AC-S5'in
`verify-domain` ucunda hiç uygulanmamış olması** (gerçek implementasyon
eksiği — `validate_hostname()` sadece `create_organization_endpoint`'te
çağrılıyordu, düzeltildi).

**Güncel gate tablosu:**
| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 4 | Lint | **PASS** | `ruff check .` → "All checks passed!" (proje geneli) |
| 6 | Unit testler | **PASS** | `pytest tests/test_organization.py tests/test_organization_authorization.py -v` → 49/49 PASS. Proje geneli regresyon: `pytest -q` → 212 passed, 6 skipped (skip'ler bu görevden önce vardı, ilgisiz). |
| 5 | Type check | PASS (değişmedi) | `mypy app` → "Success: no issues found in 31 source files" |

Aşağıdaki bölüm 1. turun orijinal (artık çözülmüş) analizidir, izlenebilirlik
için silinmedi:

---

_Reference: atdd.md, code_diff.md, test_diff.md_
_Komutlar `.github/workflows/ci.yml`'deki backend job'ından birebir alındı
(`ruff check .`, `mypy app`, `pytest -q` — `pytest -q` yerine bu görevin
dosyalarına daraltılmış hâli çalıştırıldı, evidence aşağıda)._

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short`/`git diff --cached` ile tüm dosyalar (yeni servis/router/migration, değiştirilen main.py/identity.py/requirements.txt, test dosyaları) gerçekten diskte doğrulandı. |
| 2 | Build/derleme | PASS | `python -c "import app.main"` hatasız (sessiz çıktı = başarı). |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase değil, ham PostgreSQL+SQLAlchemy/Alembic kullanıyor — bu gate bu projede hiç geçerli değil. |
| 4 | Lint | **FAIL** | `ruff check .` → 7 hata: `app/api/organizations.py` (2 kullanılmayan import: `select`, `OrganizationMember`), `app/services/organization.py` (1 kullanılmayan import: `timedelta`), `tests/test_organization_authorization.py` (3 kullanılmayan import: `can`, `scoped_organizations`, `datetime`). Format (`ruff format --check .`) 31 dosyada fark buluyor ama bu **proje genelinde önceden var olan** bir durum (CI zaten `ruff format` çalıştırmıyor, sadece `ruff check`) — bizim 2 yeni dosyamız (`test_organization.py`, `test_organization_authorization.py`) da bu 31'in içinde ama tek başına bloklayıcı değil. |
| 5 | Type check | PASS | `mypy app` → "Success: no issues found in 31 source files". |
| 6 | Unit testler | **FAIL** | `pytest tests/test_organization.py tests/test_organization_authorization.py -q` → **16 failed, 34 passed**. Kök neden analizi aşağıda. |
| 7 | E2E testler | N/A | Bu görev backend-only, e2e suite yok, web UI kapsam dışı. |
| 8 | Lighthouse | N/A | Web UI kapsam dışı. |
| 9 | Erişilebilirlik | N/A | Web UI kapsam dışı. |
| 10 | Güvenlik taraması | PASS | `security-scan` runner: secrets PASS, python_sast (bandit) PASS, python_deps N/A (manifest proje kökünden değil `backend/` altından, tarayıcı bulamadı — bilinen bir aracın limiti, bandit/detect-secrets tarafında bulgu yok). |
| 11 | AI code review | PENDING (red-team) | Ayrı adımda yapılacak. |
| 12 | Görsel regresyon | N/A | Web UI kapsam dışı. |
| 13 | DAST (ZAP) | N/A | Web UI kapsam dışı, threat-model AC-S'leri de rendered UI için değil backend API için üretildi. |
| 14 | İnsan onayı | PENDING | Her zaman son gate, henüz alınmadı. |

## Gate 6 kök neden analizi (16 hata → 3 kök neden)

### Kök neden A — Implementasyon hatası: `verify-domain` gereksiz zorunlu body istiyor (13 test etkileniyor)
`app/api/organizations.py`'deki `verify_domain_endpoint`, `payload: DomainVerifyRequest`
parametresini **varsayılan değersiz** tanımlamış. `DomainVerifyRequest` alanı
olmayan boş bir Pydantic modeli olsa da, varsayılansız olduğu için FastAPI
isteğin body'sinde geçerli bir JSON bekliyor; testler (ve gerçek API.md
sözleşmesi — "body yok") hiç body göndermiyor → FastAPI, endpoint fonksiyonu
hiç çalışmadan **422** döndürüyor. Bu, yetkilendirme kontrolünden (404) bile
ÖNCE gerçekleşiyor — yani `test_non_admin_verify_domain_404` gibi testler bile
bu yüzden 422 alıyor, AC-10 kontrolüne hiç ulaşılmıyor.
**Etkilenen testler (13):** 4× `test_verify_domain_free_email_provider_400`,
`test_verify_domain_pending_no_txt_record`, `test_verify_domain_timeout_returns_pending`,
`test_verify_domain_success_updates_to_t2`, `test_verify_domain_already_verified_in_another_org_409`,
`test_non_admin_verify_domain_404`, `test_verify_domain_rate_limit_429`,
`test_verify_domain_second_call_within_60s_429`, `test_verify_domain_audit_logged`,
`test_verify_domain_success_audit_logged`.
**Düzeltme:** `payload: DomainVerifyRequest = DomainVerifyRequest()` (varsayılan
değer ver) — `code-copilot`'a geri dönülmeli.

### Kök neden B — Test hatası: `AuditEvent.target_id` yanlış alan adı (2 test etkileniyor)
`app/models/audit.py`'deki gerçek alan adı `subject_id` (bkz. `audit.py`
docstring'i ve `log_audit_event(...)` imzası: `subject_type`, `subject_id`).
Test dosyası `AuditEvent.target_id` diye var olmayan bir alan kullanıyor →
`sqlalchemy.exc.InvalidRequestError`.
**Etkilenen testler (2, Kök neden A ile çakışmayanlar):** `test_create_organization_audit_logged`,
`test_invite_member_audit_logged`.
**Düzeltme:** `test-copilot`'a geri dönülmeli — `target_id` → `subject_id`.

### Kök neden C — Test hatası: atdd.md/API.md'de olmayan bir endpoint varsayılmış (1 test)
`test_member_of_org_a_cannot_see_org_b_members_list_404`, `GET /organizations/{id}/members`
diye bir endpoint'in var olduğunu varsayıyor (kendi yorumunda "Assuming there's..."
diyor) — bu endpoint ne atdd.md'nin Acceptance Criteria'sında ne de
`docs/API.md` §2.4 sözleşmesinde var (yalnızca `POST /organizations/{id}/members`
var, `GET` yok). Var olmayan bir route'a `GET` çağrısı FastAPI'de path eşleşip
method eşleşmediği için **405** dönüyor, test **404** bekliyor.
**Düzeltme:** `test-copilot`'a geri dönülmeli — bu test ya silinmeli (kapsam
dışı bir endpoint varsayıyor) ya da AC-S6 gerçek bir uç üzerinden (ör.
`GET /organizations/{id}` — zaten var olan uç) yeniden yazılmalı.

## AC → Test eşlemesi (mevcut durumla)
Detaylı eşleme `test_diff.md`'de. Özet: **34/50 test PASS**, kalan 16'sı
yukarıdaki 3 kök nedene ait — hiçbiri "AC hiç test edilmemiş" değil, üçü de
"test/implementasyon detayında uyumsuzluk".

## Coverage / Quality Notes
- AC-9 (domain-already-verified) testi Kök neden A yüzünden hâlâ FAIL
  görünüyor ama `code_diff.md`'de belgelenen düzeltme (servis içi
  `DomainAlreadyVerifiedError` kontrolü) doğru — asıl engel router
  seviyesindeki body sorunu.
- Pyramid oranı (test_diff.md'nin hedeflediği 70/20/10) bu iki dosyada
  fonksiyonel/HTTP-entegrasyon ağırlıklı — atdd.md'nin öngördüğü unit/
  integration/e2e ayrımı net değil, ama bu görevin AC kapsamı için kabul
  edilebilir (gerçek Postgres + TestClient zaten "integration" seviyesinde).

## Refactor Aday Kontrolü (2. tur — gate 6 artık PASS, kontrol şimdi yapıldı)
`code_diff.md` kapsamındaki dosyalar (`organization.py`, `organizations.py`,
migration) incelendi: ölçülebilir tekrar (institution.py ile yapısal benzerlik
var ama CLAUDE.md "modüller birbirini import etmez" kuralı gereği bu kasıtlı,
paylaşılan bir helper'a çekilemez), sihirli sayı (60sn/3sn zaten AC-11/
performance_target'a bağlı, isimli sabit değil ama doğrudan AC'ye referanslı),
derin nesting (`verify_domain`'de 2 seviye `for` — sığ), uzun parametre listesi
(en fazla 4 parametre) veya ölü kod yok.
**Refactor adayı yok** (diff CAVEMAN'a uygun, minimal) — kontrol fiilen
yapıldı, sessizce atlanmadı.

## Sonuç (1. tur — artık geçmiş durum, üstteki güncellemeye bakınız)
~~Gate 4 (lint) ve Gate 6 (unit test) FAIL.~~ → 2. turda düzeltildi ve
bağımsız olarak doğrulandı, bkz. dosyanın başındaki güncelleme.

## Nihai Durum (2. tur sonrası)
Tüm zorunlu gate'ler PASS/N/A: 1 PASS, 2 PASS, 3 N/A, 4 PASS, 5 PASS, 6 PASS,
7-9/12-13 N/A (web UI kapsam dışı), 10 PASS, 11 PENDING (red-team), 14
PENDING (insan onayı). Sonraki adım: `refactor` aday kontrolü (şimdi
uygulanabilir, testler yeşil) ve ardından `red-team`.
