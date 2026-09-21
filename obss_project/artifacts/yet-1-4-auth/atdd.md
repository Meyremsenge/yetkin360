---
task_slug: yet-1-4-auth
jira_id: YET-27..YET-30
saga_task_id: null
priority: critical
threat_model: done  # geriye dönük çalıştırıldı — bkz. "Threat-Model Notu" ve AC-S1..S3
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 70
  e2e: 10
affected_modules:
  - backend/app/models/auth.py
  - backend/alembic/versions/ffcf10979a51_add_refresh_tokens_table.py
  - backend/app/core/security.py
  - backend/app/core/deps.py
  - backend/app/core/errors.py
  - backend/app/services/auth.py
  - backend/app/schemas/auth.py
  - backend/app/api/auth.py
  - backend/app/main.py
  - backend/tests/authorization/test_auth_endpoints.py
  - backend/tests/authorization/test_auth_refresh_real_session.py
  - backend/tests/test_audit_events.py
---

# ATDD — yet-1-4-auth

> **Not: bu doküman geriye dönük yazıldı.** PLAN 1.4 kullanıcının doğrudan
> "uygula" talimatıyla, ATDD akışından geçmeden kodlandı ve halihazırda
> tamamlanmış durumda (testler yeşil, commit edildi: `81d3c48`, `fb924f1`).
> Bu dosya, ATDD pipeline'ının sonraki adımları (plan/test-copilot/
> code-copilot/verify/red-team) referans alabilsin diye, gerçekleşmiş
> kararları ve mevcut davranışı belgeler — soru-cevap turu içermez çünkü
> sorulacak sorular zaten kod ve önceki konuşma ile yanıtlanmış durumda.

> **Threat-Model Notu:** Bu görev, `atdd` skill'inin threat-model
> tetikleyici listesindeki **iki** kategoriye açıkça giriyor — kimlik
> doğrulama/yetkilendirme ve yeni HTTP endpoint'ler (`/auth/register`,
> `/login`, `/refresh`, `/logout`). Kod zaten yazılıp commit edildikten
> (`81d3c48`, `fb924f1`) sonra, `atdd` skill'ine sonradan eklenen 5b
> kuralına uymak için `threat-model` skill'i **geriye dönük** çalıştırıldı
> — STRIDE-lite analizi yapıldı, sonuçlar aşağıdaki AC listesinin sonuna
> `AC-S1`/`AC-S2`/`AC-S3` olarak eklendi. Normal akışta bu, kod yazılmadan
> **önce** yapılırdı; burada tersine, mevcut koda karşı yapıldı. AC-S1
> gerçek bir bulgudur ve kullanıcının karar vermesi gerekiyor (düzeltilsin
> mi, kabul edilen risk mi).

## Jira Kaynağı
YET-27, YET-28, YET-29, YET-30 — kullanıcı tarafından "PLAN 1.4'ü (Auth:
kayıt, giriş, token yenileme, çıkış) uygula" talimatıyla verildi.
`jira-sync` çağrılmadı; Jira'daki gerçek User Story/AC metni bu oturumda
çekilmedi. Aşağıdaki User Story ve AC'ler, PLAN.md 1.4 maddesi +
docs/API.md §1.7/§2.1 + docs/SECURITY.md §3/§6'dan türetildi — Jira'daki
issue metniyle birebir örtüştüğü doğrulanmadı.

## Persona
- **Yeni ziyaretçi** — platforma ilk kez kayıt olan (öğrenci/talent).
- **Kayıtlı kullanıcı** — giriş yapan, oturumu süresi dolunca yenileyen,
  çıkış yapan herhangi bir rol (talent, kurum üyesi, koordinatör, admin).
- **Saldırgan** — hesap ele geçirme, kullanıcı numaralandırma, CSRF, refresh
  token çalma senaryolarını deneyen taraf (docs/SECURITY.md §4 senaryo 6, 9, 10).

## Hedef (Neden)
`beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirinin ön koşulu:
herkesin aynı kapıdan, rolsüz kaydolabildiği, oturumunun güvenli (httpOnly
cookie, rotasyonlu refresh token) yönetildiği bir kimlik doğrulama temeli
olmadan hiçbir sonraki endpoint güvenle yazılamaz.

## User Story
As a **kayıt olmak isteyen ziyaretçi**
I want **e-posta + şifre + ad-soyad ile kaydolabilmek, giriş yapabilmek,
oturumumu sessizce yenileyebilmek ve çıkış yapabilmek**
So that **rolümü kendim beyan etmeden, güvenli bir oturumla platformu
kullanabileyim**

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given geçerli e-posta/şifre/ad-soyad, When `POST /auth/register`
   çağrılır, Then `201` + `user_id` döner; aynı transaction'da boş bir
   `talent_profiles` satırı oluşur; `role` alanı isteğe eklense bile yok sayılır.
2. [Critical] Given kayıtlı e-posta, When `POST /auth/register` tekrar aynı
   e-postayla çağrılır, Then `409 EMAIL_TAKEN` döner.
3. [Critical] Given doğru e-posta/şifre, When `POST /auth/login` çağrılır,
   Then `200` + `{user_id, role, email_verified}` döner ve `access_token`
   (15dk, httpOnly), `refresh_token` (30gün, httpOnly, path=/auth/refresh),
   `csrf_token` (JS okuyabilir) cookie'leri set edilir; token değerleri
   response gövdesinde **hiçbir yerde** geçmez.
4. [Critical] Given yanlış şifre VEYA kayıtsız e-posta, When `POST /auth/login`
   çağrılır, Then ikisi için de aynı `401 INVALID_CREDENTIALS` + "E-posta
   veya şifre hatalı." mesajı döner (kullanıcı numaralandırma yok).
5. [High] Given ardışık 10 başarısız giriş denemesi, When 11. deneme (doğru
   şifreyle bile) yapılır, Then `423 ACCOUNT_LOCKED` döner.
6. [Critical] Given geçerli bir refresh_token cookie'si, When `POST /auth/refresh`
   çağrılır, Then eski token revoke edilir, yeni bir refresh+access+csrf
   token seti issue edilir (`204` + yeni cookie'ler).
7. [Critical] Given daha önce rotasyonla revoke edilmiş bir refresh token
   tekrar sunulursa (çalınma sinyali), When `POST /auth/refresh` çağrılır,
   Then `401 INVALID_REFRESH_TOKEN` döner VE o token'ın **tüm ailesi**
   (rotasyonla üretilmiş sonraki token dahil) revoke edilir.
8. [High] Given refresh_token cookie'si hiç yok, When `POST /auth/refresh`
   çağrılır, Then `401 INVALID_REFRESH_TOKEN` döner.
9. [Medium] Given süresi dolmuş bir refresh token, When `POST /auth/refresh`
   çağrılır, Then `401 INVALID_REFRESH_TOKEN` döner.
10. [Critical] Given geçerli oturum + doğru `X-CSRF-Token` header'ı, When
    `POST /auth/logout` çağrılır, Then `204` döner, tüm cookie'ler silinir,
    refresh token ailesi revoke edilir (sonraki refresh denemesi 401 verir).
11. [Critical] Given geçerli oturum ama `X-CSRF-Token` header'ı eksik/yanlış,
    When `POST /auth/logout` çağrılır, Then `403 CSRF_FAILED` döner (bu,
    docs/API.md §2.1'in belirttiği, 404-değil-403 kuralının tek istisnası).
12. [High] Given oturum yok (access_token cookie'si yok/geçersiz), When
    `POST /auth/logout` çağrılır, Then `401 UNAUTHENTICATED` döner —
    CSRF kontrolünden **önce** çalışır (401 önceliklidir).

**Güvenlik AC'leri (`threat-model` skill'i, geriye dönük çalıştırıldı — bkz.
yukarıdaki Threat-Model Notu). STRIDE-lite: Tampering ve Elevation
kategorilerinde açık bulunmadı (role hep sunucuda hesaplanıyor, yetki
kontrolleri doğru sırada); aşağıdakiler Information Disclosure ve
Repudiation kategorilerinde çıktı.**

13. [High] **AC-S1 (Information Disclosure — kullanıcı numaralandırma):**
    Given kayıtlı bir e-posta, When `POST /auth/register` o e-postayla
    tekrar çağrılır, Then şu anki davranış `409 EMAIL_TAKEN` döner — bu,
    saldırganın hangi e-postaların platformda kayıtlı olduğunu tek istekle
    öğrenmesine izin verir. **docs/SECURITY.md §4 senaryo 10 ile doğrudan
    çelişir** ("Kayıt/şifre sıfırlamada tek tip cevap"). Bu, `/auth/
    forgot-password`'ün zaten uyguladığı (`204` her zaman) desenin
    `/auth/register`'da uygulanmamış hâli. **Kabul edilen risk olarak mı
    bırakılacak yoksa düzeltilecek mi kullanıcı karar vermeli** — düzeltme
    `201` dönüp e-postayı gerçekte kaydetmemek (var olan hesaba "birisi bu
    e-postayla kayıt denemesi yaptı" bildirimi outbox'tan atmak, PLAN 1.5/1.6
    bağımlılığı) anlamına gelir ve register akışının UX'ini değiştirir; bu
    yüzden burada sadece işaretleniyor, düzeltme bu görevin kapsamında
    **yapılmadı**.
14. [Medium] **AC-S2 (Repudiation — access token çalınması sınırı):** Given
    bir saldırgan access_token cookie'sini (XSS dışı bir yolla, örn. tarayıcı
    geçmişi/paylaşılan makine) ele geçirir, When bu token'la istek atılırsa,
    Then hiçbir mekanizma bu token'ı erken iptal edemez (JWT stateless,
    `decode_access_token` sadece imza+süre kontrol eder, DB'ye bakmaz) —
    saldırgan token'ın kalan ömrü boyunca (en fazla 15dk) geçerli kalır.
    **Kabul edilen risk**: TTL kısa (15dk) tutularak mitigasyon zaten
    docs/SECURITY.md §5'te bilinçli bir tasarım kararı; giriş bildirimi/oturum
    iptal listesi MVP dışı (V2, docs/SECURITY.md §4 senaryo 6).
15. [Low] **AC-S3 (Repudiation — audit_events actor_ip proxy arkasında
    yanlış olabilir):** Given tek-VPS + Nginx production kurulumu, When
    `_client_ip()` `request.client.host`'a bakar, Then reverse-proxy'nin
    kendi IP'si gerçek saldırgan IP'si yerine `audit_events`'e yazılabilir
    (zaten Risks bölümünde not edilmişti, burada AC'ye bağlandı). Düzeltme:
    `X-Forwarded-For` desteği — bu görevin kapsamında **yapılmadı**, ayrı
    takip gerekiyor (Nginx güven zinciri kurulmadan header'a körü körüne
    güvenmek IP spoofing'e açar, bu yüzden tek başına yapılmamalı).

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: register | `201` + `{user_id}` | `users` + `talent_profiles` satırı, `audit_events` (USER_REGISTER, SUCCESS) | "Kayıt başarılı" | AC-1 |
| 1b | Happy path: login | `200` + `{user_id, role, email_verified}` + 3 cookie | `failed_login_count` sıfırlanır, yeni `refresh_tokens` satırı, audit SUCCESS | Giriş yapılmış oturum | AC-3 |
| 1c | Happy path: refresh | `204` + 3 yeni cookie | eski token `revoked_at` set edilir, yeni satır eklenir, audit SUCCESS | Oturum sessizce yenilenir | AC-6 |
| 1d | Happy path: logout | `204`, cookie'ler silinir | refresh ailesi revoke, audit SUCCESS | Oturum kapanır | AC-10 |
| 2 | Girdi geçersiz/eksik (örn. kısa şifre, format bozuk e-posta) | `422` Pydantic doğrulama hatası (FastAPI default) | yok | Form hatası | — (ortak hata kodu, docs/API.md §1.5) |
| 3 | Kaynak yok (bilinmeyen e-posta ile login) | `401 INVALID_CREDENTIALS` — **yanlış şifreyle aynı mesaj** | audit DENIED (`actor_user_id=None`) | "E-posta veya şifre hatalı" | AC-4 |
| 4 | Yetkisiz erişim (logout, oturumsuz) | `401 UNAUTHENTICATED` | yok | Giriş sayfasına yönlendirme | AC-12 |
| 4b | Yetkisiz erişim (logout, CSRF yok/yanlış) | `403 CSRF_FAILED` | yok | Genel hata (frontend sessizce retry edebilir) | AC-11 |
| 5 | Dış bağımlılık hatası (DB bağlantısı kopar) | `500` (FastAPI default, ele alınmadı) | `get_session` rollback yapar | Genel hata sayfası | Kapsam dışı — bkz. aşağı |
| 6 | Zaman aşımı (refresh token expired) | `401 INVALID_REFRESH_TOKEN` | cookie'ler temizlenir | Yeniden giriş istenir | AC-9 |
| 7 | **Kısmi başarı**: refresh token reuse-detection, family'yi revoke edip sonra `InvalidRefreshToken` fırlatıyor | `401 INVALID_REFRESH_TOKEN` VE family-revoke **kalıcı olarak** commit edilir | `RefreshToken.revoked_at` tüm ailede set edilir + `REFRESH_TOKEN_REUSE_DETECTED` audit event'i | "Oturum yenilenemedi", çalınan token bir daha işe yaramaz | AC-7 |
| 8 | **Hiçbir şey yapılamadı ama hata yok**: `logout` refresh_token cookie'si yoksa | `204` (idempotent — hata değil) | Sadece `USER_LOGOUT` audit event'i yazılır, revoke edilecek token yoktur | Oturum kapanmış gibi görünür (access_token zaten siliniyor) | Kasıtlı — logout'un amacı "oturumu sonlandır", refresh cookie'nin olmaması bunu engellemez |

**Kısmi başarı — GERÇEK BUG bulundu ve düzeltildi (bu kontrol sırasında):**
İlk yazılan koda göre `refresh_tokens()` reuse-detection dalında family'nin
tamamını `revoked_at` ile işaretleyip `session.flush()` yapıyor, sonra
`InvalidRefreshToken` fırlatıyordu. Router bunu yakalayıp `ApiError`
(bir `HTTPException`) fırlatıyor; bu da `get_session`'ın generator
dependency'sindeki `except Exception: session.rollback()` bloğuna
düşüyordu — yani **family-revoke hiç commit edilmeden rollback ile geri
alınıyordu**. Sonuç: çalınmış bir refresh token tespit edilip "aile
tamamen iptal edildi" audit kaydı yazılsa da, rotasyonla üretilmiş kardeş
token production'da hâlâ geçerli kalıyordu — reuse-detection'ın **tek**
güvenlik amacı boşa çıkıyordu.

Bulgu, `backend/tests/authorization/test_auth_endpoints.py`'nin bunu
YAKALAYAMADIĞI tespit edilerek ortaya çıktı: o dosyadaki `client` fixture'ı
`get_session`'ı `tests/authorization/conftest.py`'deki paylaşılan `session`
fixture'ıyla (savepoint modu, asla commit etmeyen) override ediyor —
flush edilen her şey test boyunca "görünür" kaldığı için gerçek
commit/rollback sınırları hiç test edilmiyordu. Gerçek `get_session`
kullanan bağımsız bir script ile doğrulandı, sonra bunu kalıcı olarak
yakalayan `backend/tests/authorization/test_auth_refresh_real_session.py`
eklendi (override YOK, gerçek ayrı bir engine/connection kullanıyor).

Düzeltme: `app/services/auth.py`'de reuse-detection dalına, exception
fırlatılmadan hemen önce `session.commit()` eklendi — bu, family-revoke'un
sonrasında ne olursa olsun kalıcı olmasını garanti eder. Kırmızı-yeşil
disipliniyle doğrulandı: düzeltme geçici olarak geri alınıp yeni testin
gerçekten kırmızı çıktığı, sonra tekrar eklenip yeşile döndüğü teyit
edildi.

**Yan etki — test kirliliği tespit edildi ve ayrıca düzeltildi:** Bu
doğrulama sırasında çalıştırılan gerçek login/refresh çağrıları,
`audit_events` tablosuna (append-only, silinemez) kalıcı `USER_LOGIN`
satırları bıraktı. Bu, var olan `backend/tests/test_audit_events.py::
test_log_audit_event_inserts_row` testinin `action="USER_LOGIN"` filtresiyle
tek satır varsaymasını bozdu (`MultipleResultsFound`). O testin filtresi,
kendi sabit `subject_id`'sini de içerecek şekilde daraltıldı — bu, PLAN
1.4 kapsamının dışında ama bu görev tarafından tetiklenen bir yan etki
olduğu için burada belgeleniyor.

**Kısmi başarı (genel):** Bu tek örnek dışında, kod tabanında ağ çağrısı
(e-posta, S3) auth akışında yok; register/login/refresh'in geri kalan
state değişiklikleri tek bir PostgreSQL transaction'ında (`get_session`)
gerçekleşiyor ve hata durumunda tamamen rollback ile geri alınıyor —
gerçek kısmi durum DB'de kalıcı olmuyor. reuse-detection, "commit sonra
hata dön" desenine ihtiyaç duyan **tek** istisnaydı.

**Hiçbir şey yapılamadı ama hata yok:** `logout` refresh_token cookie'si
olmadan çağrılırsa sessizce `204` döner (satır 8) — bu **kasıtlı**, çünkü
logout'un sözleşmesi "oturumu sonlandır" demektir, zaten olmayan bir
refresh token'ı revoke edememek bir hata değildir. Access token cookie'si
her durumda silinir.

**Boş sonuç ↔ hata ayrımı:** Login'de "kayıtsız e-posta" ile "yanlış şifre"
kasıtlı olarak **aynı** `401 INVALID_CREDENTIALS` sonucunu üretir (docs/
SECURITY.md §4.2 — kullanıcı numaralandırmayı önlemek için tasarım gereği
ayrım yok, bu bir sözleşme kusuru değil). Refresh'te ise "token yok" (401,
`request.cookies.get` None) ile "token var ama geçersiz/expired/revoked"
(401, servis katmanı `InvalidRefreshToken`) durumları farklı kod yollarından
geçer ama **aynı** HTTP durum kodu ve `code` alanını döner — bilinçli, çünkü
ayrım yapmak saldırgana token formatı hakkında bilgi sızdırır.

**Uygulanmamış/ertelenmiş satırlar ve neden:**
- E-posta doğrulama zorunluluğu (`401 EMAIL_NOT_VERIFIED`) **uygulanmadı** —
  PLAN 1.6'ya bırakıldı çünkü outbox (PLAN 1.5) olmadan doğrulama e-postası
  gönderilemez; register sonrası kullanıcı `email_verified_at=NULL` ile
  hemen login olabiliyor (bu davranış PLAN 1.6'da kısıtlanacak).
- Dış bağımlılık hatası (satır 5) için özel bir hata haritalama
  eklenmedi — FastAPI'nin varsayılan `500` davranışına bırakıldı; MVP
  kapsamında ayrı bir gereksinim olarak belirtilmediği için.

## Test Strategy
Unit: 20% — `app/core/security.py` (hash/verify/JWT encode-decode) saf
fonksiyonlar, servis katmanındaki dallanma mantığı.
Integration: 70% — iki dosya, iki farklı `get_session` stratejisiyle:
- `tests/authorization/test_auth_endpoints.py` (15 test): `get_session`
  dependency override edilerek `tests/authorization/conftest.py`'deki
  paylaşılan savepoint `session` fixture'ı kullanılır — hızlı, izole, ama
  **gerçek commit/rollback sınırlarını test etmez** (bkz. bulgu aşağıda).
- `tests/authorization/test_auth_refresh_real_session.py` (1 test):
  override YOK, gerçek `get_session`'ı ve ayrı bir engine/connection'ı
  kullanır — request-scoped commit/rollback davranışını gerçekten test
  eder. Bu dosyanın var olma nedeni, kontrol sırasında bulunan gerçek bir
  bug (aşağıdaki Davranış Sözleşmesi tablosunun 7. satırı).
E2E: 10% — kapsanmadı; frontend henüz auth akışını tüketmiyor (PLAN
1.13'te kayıt ekranı ayrı madde). İleride Playwright ile happy-path
register→login→refresh→logout senaryosu eklenebilir.

## Benchmark / Başarı Ölçütü
Coverage Target: 85% (backend `app/services/auth.py` + `app/api/auth.py`
+ `app/core/security.py` + `app/core/deps.py` için) — ölçülmedi, mevcut
proje coverage aracı (`pytest-cov` vb.) requirements.txt'te yok; bu bir
**varsayım/hedef**, gerçek ölçüm PLAN'ın sonraki bir doğrulama adımında
yapılmalı.
Performance Target: yok — MVP'de tanımlı bir SLA yok.
Diğer ölçülebilir kriterler: `pytest tests/authorization -q` tamamı yeşil
(gerçekleşti: 57 passed, 6 skipped — kontrol sırasında eklenen 1 regresyon
testiyle 56'dan 57'ye çıktı), tam paket `pytest -q` yeşil (88 passed, 6
skipped), `ruff check` ve `mypy app` temiz (gerçekleşti), migration
`upgrade head` → `downgrade -1` → `upgrade head` döngüsü hatasız
(gerçekleşti). Ayrıca: kontrol sırasında bulunan reuse-detection
rollback bug'ı için kırmızı-yeşil disipliniyle doğrulama yapıldı (düzeltme
geçici geri alınıp yeni test kırmızı çıktığı, tekrar eklenince yeşile
döndüğü teyit edildi).

## Kapsam Dışı
- E-posta doğrulama (`/auth/verify-email`) — PLAN 1.6.
- Şifre sıfırlama (`/auth/forgot-password`, `/auth/reset-password`) — PLAN 1.6.
- Outbox / e-posta gönderimi — PLAN 1.5.
- Rate limiting (login 5/dk/IP, kayıt 3/saat/IP vb., docs/SECURITY.md §3) —
  Nginx/PostgreSQL sayaç katmanı bu görevde eklenmedi.
- `users.is_platform_admin` sütunu — docs/DOMAIN.md'de tanımlı ama
  `User` modelinde (app/models/identity.py) yok; `role` hesaplaması bu
  sütun olmadan üyelik tablolarından (`InstitutionMember`,
  `OrganizationMember`) çıkarım yapıyor, platform admin'i tespit edemiyor.
- MFA, giriş bildirimi (docs/SECURITY.md §4 senaryo 6) — V2.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/auth.py` (yeni) — `RefreshToken`
- `backend/app/models/__init__.py` — export eklendi
- `backend/alembic/versions/ffcf10979a51_add_refresh_tokens_table.py` (yeni)
- `backend/app/core/security.py` (yeni) — Argon2id, JWT, opak refresh token, SHA-256 hash
- `backend/app/core/deps.py` (yeni) — `get_session`, `get_current_user`, `require_csrf`
- `backend/app/core/errors.py` (yeni) — `ApiError`
- `backend/app/services/auth.py` (yeni) — register/authenticate/refresh_tokens/logout/summarize_role
- `backend/app/schemas/auth.py` (yeni) — Pydantic request/response şemaları
- `backend/app/api/auth.py` (yeni) — router, cookie set/clear, `_client_ip`
- `backend/app/main.py` — router include + `{code,message,request_id}` exception handler
- `backend/tests/authorization/test_auth_endpoints.py` (yeni) — 15 test,
  override edilmiş `get_session` (savepoint), `role`/`email_verified`
  assert'leri kontrol sırasında eklendi
- `backend/tests/authorization/test_auth_refresh_real_session.py` (yeni,
  kontrol sırasında eklendi) — 1 regresyon testi, override YOK, gerçek
  `get_session`
- `backend/tests/test_audit_events.py` (kontrol sırasında düzeltildi) —
  `test_log_audit_event_inserts_row` filtresi `subject_id` ile daraltıldı
  (gerekçe: aşağıdaki Davranış Sözleşmesi notu)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu oturumda git reposunun kökü zaten
`C:\Users\Meyrem\Desktop\P\yetkin360` olarak çalışıldı ve backend
aramaları `backend/` altına Glob ile sınırlı tutuldu. Kök dizinde devasa
bir git geçmişi gözlemlenmedi ama teyit edilmedi.

## Rollback Beklentisi
Migration: `alembic downgrade -1` test edildi ve çalışıyor (refresh_tokens
tablosunu ve index'lerini kaldırır). Kod tarafında rollback = commit
edilmemiş dosyaları geri almak (henüz commit atılmadı).

## Risks
- `docs/DOMAIN.md`'deki `users.is_platform_admin` sütununun eksik olması,
  ileride platform admin akışlarını (PLAN ilerleyen maddeleri) etkileyebilir
  — ayrı bir migration/karar gerekiyor.
- Reverse-proxy arkasında gerçek client IP'si `X-Forwarded-For` ile
  gelmeli; şu anki `_client_ip()` doğrudan `request.client.host`'a bakıyor,
  tek-VPS + Nginx production kurulumunda bu proxy IP'sini yazabilir
  (audit_events'te gerçek saldırgan IP'si değil, proxy IP'si görünür).
- **Süreç riski (genel ders):** `get_session`'ı savepoint fixture'ıyla
  override eden test deseni (`test_auth_endpoints.py`), request-scoped
  commit/rollback sınırlarını hiç test etmiyor. Bu görevde bu yüzden
  gerçek bir güvenlik bug'ı (reuse-detection'ın rollback ile geri
  alınması) 15 testin tamamı yeşilken fark edilmedi — ancak kod elle,
  gerçek `get_session` ile ayrıca doğrulanınca ortaya çıktı. Aynı desenle
  yazılan ileriki testler (PLAN 1.6+ auth akışları, engagement durum
  geçişleri) benzer commit/rollback hatalarını kaçırabilir; en az bir
  gerçek-session entegrasyon testi olmayan yeni bir "revoke sonra hata
  fırlat" deseni yazılırsa `red-team`/`verify` adımında bu özellikle
  sorgulanmalı.

## Assumptions
- `role` alanının login response'unda "en yüksek yetkili üyelik" anlamına
  geldiği varsayıldı (docs/API.md bunu açıkça tanımlamıyor) — kullanıcı
  onaylamadı, **varsayım**.
- Refresh token TTL'i boyunca (`REFRESH_TOKEN_TTL_DAYS`) `csrf_token`
  cookie ömrünün de aynı süre olması varsayıldı — dokümanda "oturum"
  (session) ömürlü olması yazıyor, farklı yorumlanabilir.

## Unknowns
- Jira YET-27..30'un tam metni bu oturumda çekilmedi; buradaki AC'lerin
  Jira'daki AC'lerle birebir örtüştüğü teyit edilmedi.
- Coverage yüzdesi gerçek bir araçla ölçülmedi.

## Sorular ve Cevaplar (ham kayıt)
1. Migration oluşturulup uygulanabilir mi? → Evet, oluştur ve uygula
   (kullanıcı, `AskUserQuestion` ile — bu görev ATDD'den geçmediği için
   soru doğrudan kullanıcıya soruldu, alt-ajana değil).
2. PLAN 1.4 kapsamı e-posta doğrulama/şifre sıfırlamayı içersin mi? →
   "En mantıklısını uygula" (kullanıcı) → sadece 1.4 (register/login/
   refresh/logout), e-posta doğrulama zorunluluğu 1.6'ya bırakıldı
   (gerekçe: outbox tablosu henüz yok).
3. Geri kalan tüm kategoriler (persona, happy path, edge case, test
   stratejisi oranı vb.) → (kod ve docs/API.md, docs/SECURITY.md,
   PLAN.md'den çıkarıldı — bu geriye dönük belgeleme olduğu için ayrıca
   sorulmadı, zaten uygulanmış davranış temel alındı).
