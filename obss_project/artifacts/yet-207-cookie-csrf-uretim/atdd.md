---
task_slug: yet-207-cookie-csrf-uretim
jira_id: YET-207
saga_task_id: null
priority: medium
threat_model: done
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 30
  e2e: 0
affected_modules:
  - backend/app/core/config.py
  - backend/app/api/auth.py (yalnız test; cookie davranışı değişmiyor)
  - docs/ENV.md
  - SECURITY.md / docs/SECURITY.md
  - backend/tests/authorization/ (yeni dosya)
---

# ATDD — yet-207-cookie-csrf-uretim

## Jira Kaynağı
[YET-207 — ENT-07: Üretim dağıtımında cookie/CSRF modeli kırılabilir](https://kuyusuzyusuf123.atlassian.net/browse/YET-207)
Açıklama (birebir): "ORTA (dağıtım riski) · [ŞÜPHE]. Cookie'ler Domain belirtilmeden yazılıyor. Frontend/API farklı alt alan adlarında yayınlanırsa CSRF/middleware kırılır. Yerelde localhost ortak olduğu için görünmüyor. Karar gerektirir: K6 (tek origin reverse proxy mi, Domain=. mi)."
K6 kararı: HATA_DUZELTME_PROMPT.md:145 → (a) tek origin reverse proxy. Kullanıcı bu oturumda doğruladı.

## Sonda kanıtı (test DB yetkin360_test, rate_limit_enabled=False, süreç-içi gerçek API)
- Login Set-Cookie (https taban URL): `access_token` HttpOnly Path=/ SameSite=lax Secure; `refresh_token` HttpOnly Path=/auth SameSite=lax Secure; `csrf_token` (HttpOnly yok) Path=/ SameSite=lax Secure. **Hiçbirinde Domain yok** (host-only).
- Logout silme başlıkları 4 adet, path'ler yazmayla tutarlı (/, /auth, eski /auth/refresh, /): YET-185 tutarlı. Silme başlıklarında Secure/HttpOnly yok (aynı ad+path+host olduğu için tarayıcıda silme çalışır; kozmetik).
- Çift gönderim (aynı host): csrf_token cookie'si + `X-CSRF-Token` ile logout 204. Farklı host'ta (`app.x` / `api.x`) host-only cookie `app.x` üzerindeki `document.cookie`'de görünmez → frontend CSRF başlığı boş → tüm yazmalar 403; middleware da `access_token`'ı göremez (HATA.md ENT-07 mekanizması, kodla tutarlı).
- Sessiz güvensiz düşüşler (Settings, `ENVIRONMENT=production` ile bile **kabul edildi**):
  1. `COOKIE_SECURE=false` → kabul (Secure bayrağı kalkar).
  2. `ALLOWED_ORIGINS=http://...` ve varsayılan `http://localhost:3000` → kabul.
  3. `DEBUG` varsayılanı true → kabul (docs/ENV.md "mutlaka false" diyor).
  4. `COOKIE_SAMESITE`, `COOKIE_DOMAIN` ortam değişkenleri `extra="ignore"` yüzünden **sessizce yok sayılıyor**; docs/ENV.md:58 `COOKIE_SAMESITE`'ı belgeliyor ama kodda alan yok.
  5. `ENVIRONMENT` serbest metin: `prod` gibi yazım hatası "production değil" sayılır → fail-fast atlanır.
  6. docs/ENV.md:57 `COOKIE_SECURE` varsayılanı `false` yazıyor, kod varsayılanı `True`.

## Persona
Platformu üretime kuran geliştirici/operatör (Meyrem) ve açık kaynak repoyu okuyan jüri/katkıcı.

## Hedef (Neden)
Üretimde cookie/CSRF modelinin yalnız desteklenen topolojide (tek origin, HTTPS) çalışması; yanlış yapılandırmanın sessizce güvensiz çalışmak yerine açılışta reddedilmesi; dokümanın kodla uyuşması.

## User Story
As an operator deploying Yetkin360
I want the API to refuse to start with an insecure or unsupported cookie/CORS configuration in production
So that CSRF double-submit and httpOnly cookies cannot silently break or weaken.

## Acceptance Criteria
1. [Critical] Given `ENVIRONMENT=production`, When `COOKIE_SECURE=false`, Then `Settings()` ValueError verir (açılış reddedilir); mesaj ayar adını söyler, değer/sır içermez.
2. [Critical] Given production, When `ALLOWED_ORIGINS` içinde `http://` şeması veya `localhost`/`127.0.0.1`/`[::1]` varsa, Then reddedilir. Aynı kural `FRONTEND_ORIGIN` için.
3. [Critical] Given production, When `DEBUG=true` (varsayılan dahil), Then reddedilir.
4. [Critical] Given production + `COOKIE_SECURE=true` + https origin'ler + `DEBUG=false`, Then `Settings()` açılır; login yanıtında üç cookie `Secure; SameSite=lax`, `Domain` yok, access/refresh `HttpOnly`, csrf_token `HttpOnly` değil (çift gönderim için JS okuyabilmeli).
5. [High] Given `ENVIRONMENT` değeri `development|staging|production` dışında (örn. `prod`, `Production `), Then reddedilir (fail-fast'in yazım hatasıyla atlanmasını önler). Büyük/küçük harf normalize edilmez; reddedilir.
6. [High] Given `ENVIRONMENT=development`, When yerel varsayılanlar (`COOKIE_SECURE=false`, http://localhost:3000, DEBUG=true), Then açılır (yerel geliştirme bozulmaz).
7. [High] Given herhangi bir ortam, When login/refresh, Then hiçbir Set-Cookie başlığında `Domain` yok (host-only sözleşmesi test ile sabitlenir; ileride Domain eklenirse test kırılır).
8. [High] Given logout, Then silme başlıkları yazma path'leriyle birebir (`/`, `/auth`, eski `/auth/refresh`, `/`) ve ad kümesi yazılanlarla aynı (YET-185 tutarlılığı regresyonu).
9. [High] Given tek origin (aynı host) cookie jar, When login → CSRF başlıksız yazma → 403 CSRF_FAILED; başlık eşleşince 2xx/204 (çift gönderim sözleşmesi korunur, 401 önceliği korunur).
10. [Medium] docs/ENV.md: COOKIE_SECURE varsayılanı doğru, `COOKIE_SAMESITE` satırı ve örnek `.env` satırı kaldırılır (Lax sabit), FRONTEND_ORIGIN açıklaması "cookie domain'i" yanlışı düzeltilir, "desteklenen topoloji: yalnız tek origin + reverse proxy (HTTPS); alt alan adı/Domain= desteklenmez" ve açılış reddi kuralları yazılır, uvicorn `--proxy-headers --forwarded-allow-ips` (YET-186) notu aynı bölümde durur. SECURITY.md'ye aynı topoloji notu.
11. [Medium] Hatalı yapılandırma mesajı TÜM sorunları tek seferde listeler (operatör tek tek denemesin).

## Davranış Sözleşmesi
| # | Durum | Dönen değer | Yan etki | Kullanıcı (operatör) ne görür | AC |
|---|---|---|---|---|---|
| 1 | Production + geçerli yapılandırma | `Settings()` döner | yok | uygulama açılır | AC-4 |
| 2 | Production + `COOKIE_SECURE=false` | pydantic ValidationError (ValueError) | süreç başlamaz | mesajda `COOKIE_SECURE` adı | AC-1 |
| 3 | Production + http/localhost origin | ValidationError | süreç başlamaz | hangi ayar (ALLOWED_ORIGINS/FRONTEND_ORIGIN) | AC-2 |
| 4 | Production + DEBUG=true | ValidationError | süreç başlamaz | `DEBUG` adı | AC-3 |
| 5 | ENVIRONMENT bilinmeyen değer | ValidationError | süreç başlamaz | izinli değerler listesi | AC-5 |
| 6 | Development yerel varsayılanlar | `Settings()` döner | yok | açılır | AC-6 |
| 7 | `COOKIE_SAMESITE`/`COOKIE_DOMAIN` env verilmiş | yok sayılır (extra ignore, mevcut) | yok | belge artık bu ayarları sunmaz | AC-10 |
| 8 | Çalışma anında CSRF eksik/uyumsuz yazma | 403 CSRF_FAILED (mevcut sözleşme, DEĞİŞMEZ) | yok | form hatası | AC-9 |
| 9 | Yetkisiz kaynak | 404 (mevcut, DEĞİŞMEZ) | yok | | — |
| 10 | Hız sınırı | 429 RATE_LIMITED (mevcut, DEĞİŞMEZ) | | | — |

Kısmi başarı: yok (açılış ya tamamen kabul ya tamamen ret; birden çok sorun tek hata mesajında listelenir).
Hiçbir şey yapılamadı ama hata yok: yok — geçersiz production yapılandırması sessiz kabul edilmez (AC-1…5 tam bu sınıfı kapatır).
Boş sonuç ↔ hata: yok (HTTP yanıt şekli değişmiyor).
Silinen satırlar: zaman aşımı / dış bağımlılık — doğrulayıcı saf, ağ/DB çağırmaz.

## Threat Model (özet, AC-S)
| Kötüye kullanım | Önlem / test |
|---|---|
| Operatör hatası: production'da Secure=false → cookie'ler HTTP'de sızar | AC-1 fail-fast |
| Yazım hatası ENVIRONMENT=prod ile korumanın atlanması | AC-5 enum |
| Gevşek CORS origin (http/localhost) üretimde kimlikli istek kabul eder | AC-2 |
| Debug hata detayı sızıntısı | AC-3 |
| Domain=.x eklenip kardeş alt alan adı (ör. kullanıcı içeriği sandbox'ı) cookie'yi okur/üstüne yazar (cookie tossing) | AC-7: Domain yok; kapsam dışı tutuldu (karar: yalnız tek origin) |
| SameSite=None ile CSRF savunması zayıflar | Lax sabit, ayar yok (AC-10) |
| Hata mesajı sır sızdırır | AC-1 mesaj yalnız ayar adı/kural, `secret_key`/DB URL yok |
| Fail-fast testi gerçek ortam değişkenlerinden etkilenir | Testler `Settings(_env_file=None, ...)` ile kurulur |

Kimlik/yetki mantığı: ÇALIŞMA ZAMANI yetki/CSRF/cookie kodu DEĞİŞMİYOR; yalnız açılış doğrulaması + regresyon testleri + doküman. 404/403/429 sözleşmeleri aynı.

## Test Strategy
Unit 70% — Settings doğrulayıcı (tablo-güdümlü, her kural + her ihlalin mutasyonla kırılması).
Integration 30% — gerçek API (TestClient https, gerçek get_session) cookie başlıkları, çift gönderim, logout silme tutarlılığı.
E2E 0% — gerçek tarayıcı/subdomain yok; kanıt başlık düzeyinde.

## Benchmark
Coverage: yeni doğrulayıcı satırları %100. `pytest tests/authorization -q` tamamı + tam paket + ruff + mypy. Frontend dokunulmaz (typecheck/lint gerekmez).

## Kapsam Dışı
- `COOKIE_DOMAIN` / alt alan adı topolojisi (karar: yalnız tek origin).
- `__Host-` cookie öneki, silme başlıklarına Secure/HttpOnly eklenmesi (kozmetik, ayrı iş).
- Reverse proxy (Caddy) yapılandırma dosyası ve docker-compose değişikliği.
- Frontend BASE_URL / `/api` önek düzeni (ENV.md `/api/v1` ↔ client.ts varsayılanı farkı: açık takip olarak raporlanır).
- Staging için ayrı kural (yalnız production zorlanır).

## Etkilenen Dosyalar
backend/app/core/config.py, docs/ENV.md, docs/SECURITY.md (+ kök SECURITY.md varsa), backend/tests/authorization/test_cookie_csrf_production.py (yeni). Migration yok, bağımlılık yok, docker-compose/CI yok.

## Proje Ortamı Kısıtı
Arama proje köküyle sınırlı; `.venv` içi okunmadı.

## Rollback
Doğrulayıcı tek validator'dır; geri almak = commit revert. Mevcut dağıtımlar: production'da `ENVIRONMENT=production` + eski gevşek ayar ile çalışan kurulum açılışta düşer (istenen davranış; ENV.md kontrol listesi zaten bunları zorunlu kılıyor).

## Risks
- `ENVIRONMENT` varsayılanı `development` kalır: operatör hiç ayarlamazsa korumalar devreye girmez. Bu bilinçli: üretim kontrol listesi (ENV.md) `ENVIRONMENT=production`'ı zorunlu kılar. Alternatif (varsayılanı production yapmak) yerel kurulumu bozar → önerilmedi.
- Mevcut testler/CI `ENVIRONMENT` ayarlıyorsa etkilenebilir → tam paket koşusuyla doğrulanır.

## Assumptions
- Production'da frontend ve API aynı origin üzerinden reverse proxy ile sunulur; `ALLOWED_ORIGINS` yine de gerçek https origin'i içerir (CORS tek origin'de pratikte kullanılmaz ama listede kalır).
- `FRONTEND_ORIGIN` başka yerde kullanılıyorsa (grep ile doğrulanacak) kural onu da kapsar.

## Unknowns
- Caddy/uvicorn gerçek dağıtım dosyaları repoda yok; topoloji notu belgeden ibaret kalır.

## Sorular ve Cevaplar
1. Topoloji → "Yalnız tek origin" (kullanıcı, AskUserQuestion, bu oturum).
2. Yanlış yapılandırma → "ENVIRONMENT=production ise başlatmayı reddet" (kullanıcı).
3. COOKIE_SAMESITE → "Ayarı kaldır, Lax sabit" (kullanıcı).
4. Persona, hedef, happy path, kapsam dışı, test oranı, kabul sahibi: Jira + bu oturumdaki görev metninden; alt-ajan kullanılmadı (kullanıcı "ALT-AJAN YOK" dedi). Test oranı 70/30/0 önerim, onay bekliyor.
