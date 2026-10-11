# SECURITY.md — Güvenlik Mimarisi

OWASP risk analizi, dosya yükleme akışı, hız sınırları, Yetkin360'a özgü saldırı
senaryoları ve sır yönetimi.

**Kaynak:** `yetkin360-final-analiz.md` §16.1–16.5.

> **Bu dosya teknik mimaridir.** Güvenlik açığı bildirimi için repo kökündeki
> [SECURITY.md](../SECURITY.md) dosyasına bakın.

**İlgili dosyalar:**
- Yetkilendirme kuralları ve test matrisi → [AUTHORIZATION.md](AUTHORIZATION.md)
- Hata formatı, 404 kuralı, uç listesi → [API.md](API.md)
- Silme politikası, append-only → [DATABASE.md](DATABASE.md)

> **Açık kaynak notu:** Bu repo herkese açıktır. Bir yetkilendirme açığı herkes
> tarafından okunabilir. Bu, güvenlik kurallarını gevşetmek için değil,
> **sıkılaştırmak** için sebeptir.

---

## 1. OWASP risk tablosu

OWASP Top 10 ve OWASP API Security Top 10 referansıyla, Yetkin360'a
uyarlanmış hâli:

| OWASP riski | Yetkin360'daki karşılığı | Önlem |
|---|---|---|
| **API1: BOLA** | **En yüksek risk.** Org A, Org B'nin engagement'ını okur | Merkezî `can()`, `scoped_*` sorgular, UUIDv7, **404 dönüşü**, her uç için otomatik test |
| API2: Broken Authentication | Token çalınması, brute force | httpOnly cookie, refresh rotation, rate limit, hesap kilitleme |
| **API3: Broken Object Property Level Auth** | **Çok gerçek risk.** `private_note` veya `password_hash` yanlışlıkla response'a girer | Pydantic response şemaları **zorunlu**; ORM modeli asla doğrudan dönmez; request şemalarında sıkı alan listesi (mass-assignment) |
| API4: Kaynak tüketimi | Büyük dosya, pahalı sorgu | Boyut limiti, **zorunlu sayfalama** |
| API5: Function Level Auth | Talent, admin ucuna erişir | Uç bazlı rol bağımlılığı + test |
| A03: Injection | SQL injection | SQLAlchemy parametreli sorgular; **ham SQL yalnız migration'da** |
| A03: XSS | Değerlendirme yorumu, profil metni | React varsayılan escape; `dangerouslySetInnerHTML` **yasak**; CSP |
| CSRF | Cookie tabanlı auth | `SameSite=Lax` + double-submit token |
| **SSRF** | **Gerçek risk:** kullanıcının verdiği URL (GitHub linki) çekiliyor | Allowlist (yalnız `github.com` vb.), özel IP aralıkları engelli, **yönlendirme takip edilmez** |
| A08: Bütünlük | Bağımlılık zinciri | Lock dosyaları, `pip-audit` / `npm audit` CI'da |
| A09: Logging | İhlal tespit edilemez | `audit_events` + güvenlik olayı logları |

### 1.1 En kritik üç risk

Bu üçü ürünün doğasından gelir; diğerleri genel web riskleridir.

**1. BOLA (API1)** — Çok kiracılı, kimlik doğrulamalı, nesne merkezli bir API
olarak en olası ihlal vektörü. Otomatik tarayıcılar yakalayamaz.
Tek savunma sistematik testtir → [AUTHORIZATION.md](AUTHORIZATION.md) §5.

**2. Alan seviyesi sızıntı (API3)** — `private_note` bir kez response şemasına
girerse öğrenci kurumun gizli notunu okur. Önlem mimariden gelir:

> **ORM modeli asla doğrudan response olarak dönülmez.** Pydantic response
> şeması her zaman ayrı tanımlıdır (CLAUDE.md değişmez kuralı).

**3. SSRF** — Öğrenci "GitHub depom" diye bir URL verir, backend onu çeker.
Kullanıcı `http://169.254.169.254/` (bulut metadata) veya `http://localhost:5432`
verirse iç ağ taranır.

| Kural | |
|---|---|
| Allowlist | Yalnız bilinen host'lar (`github.com`, `gitlab.com`) |
| Özel IP aralıkları | `127.0.0.0/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16` **engelli** |
| Yönlendirme | **Takip edilmez** (allowlist'i atlatmanın klasik yolu) |
| DNS | Çözümlenen IP de kontrol edilir (DNS rebinding) |

> **MVP notu:** Hackathon kapsamında dış URL **çekilmiyor** — link yalnız
> `external_uri` olarak saklanıp kullanıcıya gösteriliyor. Bu, SSRF yüzeyini
> sıfırlar. Backend herhangi bir kullanıcı URL'sini çekmeye başladığı anda
> yukarıdaki kuralların tamamı zorunlu hâle gelir.

---

## 2. Dosya yükleme güvenliği

Dokunulmaz dokuz kural. [API.md](API.md) §2.7'deki üç adımlı akışın güvenlik
gerekçesi budur.

| # | Kural | Neden |
|---|---|---|
| 1 | Dosya **asla** uygulama sunucusunda tutulmaz → object storage (MinIO/S3/R2), **private bucket** | Sunucu diski, yedekleme ve izin yönetimi karmaşası |
| 2 | Uzantıya **asla** güvenilmez → içerikten **magic-byte** ile MIME tespiti | `zararlı.exe` → `rapor.pdf` yeniden adlandırması |
| 3 | **Allowlist:** `pdf, png, jpg, docx, zip`. Blacklist **kullanılmaz** | Blacklist her zaman eksiktir |
| 4 | Boyut sınırı: **10 MB/dosya**, kullanıcı başına toplam kota **100 MB** | Kaynak tüketimi (API4) |
| 5 | Dosya adı **asla korunmaz** → `{uuid}.{ext}`. Orijinal ad yalnız DB metadata'sında | Path traversal, null byte, unicode hileleri |
| 6 | Virüs taraması **yükleme sonrası, asenkron**. `scan_status = PENDING` iken **indirilemez** | Senkron tarama isteği kilitler |
| 7 | İndirme: **kısa ömürlü imzalı URL (5 dk)**, her indirmede yetki kontrolü + audit kaydı | Sızan URL sonsuza kadar geçerli olmamalı |
| 8 | **Kullanıcı içeriği ana domainden asla servis edilmez** → ayrı domain/subdomain | Yüklenen HTML/SVG ile aynı-origin XSS. **Gerçek dünyada en sık yapılan dosya güvenliği hatası** |
| 9 | `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` | Tarayıcının içeriği çalıştırmasını engeller |

### 2.1 Akış

```
1. POST /evidence/upload-url
   → istemci: filename, mime_type, size_bytes
   → sunucu: allowlist + boyut kontrolü (ön kontrol)
   → sunucu: {uuid}.{ext} storage_key üretir, imzalı PUT URL döner

2. PUT <upload_url>
   → dosya doğrudan object storage'a gider, backend'den GEÇMEZ

3. POST /evidence
   → sunucu: dosyayı storage'dan okur, MAGIC-BYTE kontrolü yapar
   → uyuşmazsa: dosya silinir, 400 UNSUPPORTED_TYPE
   → uyuşursa: DB kaydı, scan_status = PENDING

4. (asenkron) tarama işçisi
   → scan_status = CLEAN | INFECTED | FAILED

5. GET /evidence/{id}/download-url
   → yetki kontrolü (AUTHORIZATION.md)
   → scan_status != CLEAN ise 409
   → 5 dk ömürlü imzalı URL + audit kaydı
```

> **Adım 3 kritiktir:** Magic-byte kontrolü **adım 1'de yapılamaz** — dosya
> henüz sunucuya ulaşmamıştır. Adım 1'deki kontrol yalnız ön elemedir;
> gerçek kontrol dosya storage'a indikten sonradır.

### 2.2 MVP sapması: virüs taraması

**Hackathon kapsamında ClamAV yoktur** (final analiz §35.3: "virüs taraması —
MIME + boyut kontrolü yeterli, ClamAV'i sonraya bırakın").

| | MVP (hackathon) | Faz 5 ([PLAN.md](PLAN.md) 5.3) |
|---|---|---|
| Magic-byte | ✅ | ✅ |
| Boyut + kota | ✅ | ✅ |
| `{uuid}.{ext}` | ✅ | ✅ |
| İmzalı URL | ✅ | ✅ |
| ClamAV taraması | ❌ — kontrolleri geçen dosya doğrudan `CLEAN` | ✅ |
| Ayrı içerik domain'i | ❌ | ✅ |

> Kural 8 (ayrı domain) MVP'de uygulanmıyor. Bu **bilinçli bir risk kabulüdür**:
> hackathon demosunda yalnız seed verisi ve ekip dosyaları var. Ürün gerçek
> kullanıcı aldığı anda bu kural zorunludur — [PLAN.md](PLAN.md) 5.3.

---

## 3. Hız sınırları (rate limiting)

| Uç | Limit |
|---|---|
| Login | **5/dk/IP** + **10/saat/hesap**, sonra artan gecikme |
| Kayıt | 3/saat/IP |
| Şifre sıfırlama | 3/saat/hesap |
| Dosya yükleme | 20/saat/kullanıcı |
| Arama | 60/dk/kullanıcı |
| Genel API | 300/dk/kullanıcı |
| ~~AI (CV parse)~~ | ~~5/gün/kullanıcı~~ — **MVP'de AI yok** |

**Uygulama: Nginx rate limit + PostgreSQL sayaç. Redis MVP'de gerekmez.**

Limit aşımında `429 RATE_LIMITED` döner ([API.md](API.md) §1.5).

**Kimlik uçları (YET-186, `auth_rate_limits` tablosu, sabit pencere):**

| Uç | IP | Hesap (gönderilen e-posta) |
|---|---|---|
| `POST /auth/login` | 5/dk | 10/saat |
| `POST /auth/register` | 3/saat | 3/saat |
| `POST /auth/forgot-password` | 10/saat | 3/saat |
| `POST /auth/reset-password` | 20/saat | — |
| `POST /auth/verify-email` | 20/saat | — |
| `POST /auth/refresh` | 60/dk | — |

**Keşfet (PLAN R.1):** `GET /discover/talents` ve `GET /discover/organizations` ortak bir kovayı paylaşır — **60/dk/kullanıcı** (yukarıdaki "Arama" satırı), aynı `auth_rate_limits` tablosu, anahtar kullanıcı kimliğinin HMAC'i.

- Yanıt `429 RATE_LIMITED` + `Retry-After` (saniye). Hesap sayacı, hesap var/yok fark etmeksizin gönderilen e-postaya göre tutulur; yanıt numaralandırmaya izin vermez.
- Anahtarlar `HMAC-SHA256(SECRET_KEY, "kova:değer")`; tabloda ham IP/e-posta yoktur. IPv6 istemciler /64 önekiyle gruplanır.
- Sıra: önce hız sınırı (429), sonra YET-175 hesap kilidi (423).
- Bilinen bedel: hesap sayacı, kurbanın e-postasına istek yağdıran saldırganın o hesabın login/şifre sıfırlama isteğini bir süre kısıtlamasına izin verir (e-posta bombardımanını önlemenin karşılığı).
- Dağıtım: IP, `request.client.host`'tan okunur; Caddy arkasında uvicorn `--proxy-headers --forwarded-allow-ips` ile çalıştırılmalıdır, aksi halde herkes tek kovaya düşer ([ENV.md](ENV.md)).
- Kanıt yükleme sınırı hâlâ bellek-içidir (çoklu worker'da etkisiz); DB sayacına taşınması ayrı iş.

> ❓ AÇIK SORU: Public uçlar (`/public/p/{slug}`, `/public/v/{token}`) için
> limit tablosunda satır yok. Bunlar kimlik doğrulaması istemediği için
> IP bazlı bir limit gerekiyor (jüri demosunda da çalışmalı). Öneri:
> 60/dk/IP — ama bu final analizde verilmemiş bir karardır.

---

## 4. Yetkin360'a özgü saldırı senaryoları

Genel web risklerinin ötesinde, **bu ürünün iş modelini hedefleyen** saldırılar.
Ürünün tüm değeri güvenilir tanıklıkta olduğu için 1, 2 ve 4 numara varoluşsaldır.

| # | Senaryo | Önlem |
|---|---|---|
| 1 | **Sahte kurum oluşturma** | T3 için MERSİS + admin onayı; `legal_id` UNIQUE; cooling period |
| 2 | **Sahte doğrulama** (kendi kendine tanıklık) | Self-attestation DB kısıtı; koordinatör ortak onayı; grafik analizi |
| 3 | **Başka kurumun aday verisini okuma** | Merkezî scoping + BOLA testleri (her uç için) |
| 4 | **Değerlendirme manipülasyonu** | Append-only tablolar; itiraz akışı; kurum dağılım izleme |
| 5 | **Sahte evidence** | `provenance` ayrımı; GitHub OAuth doğrulaması (V2); `content_hash` |
| 6 | **Hesap ele geçirme** | Argon2id; MFA (V2); oturum iptali; giriş bildirimi |
| 7 | **Spam kurum** | Domain doğrulama; oran limitleri; admin kuyruğu |
| 8 | **Zararlı dosya yükleme** | §2'nin tamamı |
| 9 | **Enumeration** | UUIDv7; **404 dönüşü**; rate limit |
| 10 | **Kayıt sırasında kullanıcı sayımı** | Kayıt/şifre sıfırlamada **tek tip cevap** ("e-posta gönderildi") |

### 4.1 Senaryo 2 — sahte doğrulama (en kritik)

Ürünün tüm iddiasını çökerten saldırı: kullanıcı kendi kendini doğrular.

| Katman | Önlem | Nerede |
|---|---|---|
| Veritabanı | `attestor_user_id != talent.user_id` kısıtı | [DATABASE.md](DATABASE.md) §2.5 |
| Üyelik grafiği | Aynı kişi hem talent hem attestor olamaz | Servis |
| Zaman | Yeni kurum 30 gün `COMPETENCE` yapamaz | Servis |
| Kota | Kurum başına doğrulanmış üye × ~5/ay | Servis |
| Ortak onay | `COMPETENCE` için koordinatör onayı (T4) | [STATE_MACHINE.md](STATE_MACHINE.md) |
| İzleme | Tek üniversiteye/öğrenci kümesine yoğunlaşma → admin işareti | Faz 5 |

Testleri → [AUTHORIZATION.md](AUTHORIZATION.md) §5.8 (H1–H4).

### 4.2 Senaryo 9 ve 10 — sızdırmadan reddetmek

Bu ikisi **cevap tasarımı** meselesidir, ek altyapı gerektirmez:

| Yanlış | Doğru |
|---|---|
| `403 "Bu kayıt size ait değil"` | `404` — varlık sızdırmaz |
| `404 "Bu e-posta kayıtlı değil"` | `204` — her zaman aynı cevap |
| `401 "Şifre hatalı"` | `401 "E-posta veya şifre hatalı"` |
| Artan integer ID (`/engagements/1042`) | UUIDv7 — tahmin edilemez, sayı sızdırmaz |

Artan ID ayrıca iş verisi sızdırır: `/engagements/1042` "1042 engagement var"
demektir — rakibe verilen ücretsiz metrik.

---

## 5. Kimlik doğrulama ve oturum

**Karar: httpOnly + Secure + `SameSite=Lax` cookie içinde kısa ömürlü JWT
access token (15 dk) + veritabanında saklanan, döndürülen (rotating) refresh
token (30 gün).**

| Konu | Karar | Gerekçe |
|---|---|---|
| Access token | JWT, **15 dk**, httpOnly cookie | `localStorage`'da token = herhangi bir XSS açığı **tam hesap ele geçirmesi**. httpOnly cookie JavaScript'ten okunamaz |
| Refresh token | **Veritabanında**, 30 gün, rotating | JWT'nin en büyük zaafı iptal edilememesidir. DB'de saklanırsa **anında iptal edilebilir** — hesap ele geçirilirse tüm oturumlar kapatılır |
| Yeniden kullanım tespiti | Eski refresh token tekrar kullanılırsa **o ailenin tümü iptal** | Çalınma sinyali |
| CSRF | `SameSite=Lax` + double-submit token | Cookie tabanlı auth'un zorunlu eşlikçisi |
| Şifre | **Argon2id** | OWASP'ın mevcut önerisi. bcrypt'in 72 bayt sınırı ve GPU direnci zayıflığı yok |
| Kilitleme | `failed_login_count` + `locked_until` | Brute force |
| Dağıtım topolojisi | **Tek origin** (HTTPS reverse proxy), cookie'ler `Domain`'siz | Double-submit için `csrf_token` JS ile okunur, middleware `access_token`'ı görür; ayrı alt alan adlarında ikisi de kırılır. `Domain=.x` kardeş alt alan adlarına cookie açar. Production'da `COOKIE_SECURE=false`, `DEBUG=true`, http/localhost origin veya bilinmeyen `ENVIRONMENT` açılışı reddeder (YET-207, [ENV.md](ENV.md) §4) |

---

## 6. Sır yönetimi

| Ortam | Yöntem |
|---|---|
| Geliştirme | `.env` (asla commit edilmez) |
| Production (tek VPS) | Barındırıcı ortam değişkenleri veya `systemd` credential / izinleri kısıtlı dosya |
| Deploy anahtarları | **Ayrı tutulur** — uygulama sırlarıyla karışmaz |

**Zorunlu kurallar:**
- Sırlar **asla** git'e girmez → `gitleaks` pre-commit **ve** CI'da.
- `.env.example` yalnız **placeholder** içerir, gerçek değer içermez.
- Sır sabitleri koda yazılmaz.
- `.env` okunmaz, içeriği çıktıya/commit'e taşınmaz (CLAUDE.md).

> **Açık kaynak riski:** Repo halka açık olduğu için bir kez commit edilen sır
> **kalıcı olarak sızmıştır** — geçmişten silmek yetmez, sır **döndürülmelidir**.
> Faz 3 kapanışında ([PLAN.md](PLAN.md) 3.15) tüm geçmiş taranır.

---

## 7. Loglama ve PII

| Asla loglanmaz | Loglanır |
|---|---|
| Şifre, token, oturum çerezi | `request_id`, uç, HTTP kodu, süre |
| CV içeriği | `user_id` (e-posta değil) |
| `private_note` | `audit_events` (PII'siz `metadata`) |
| Tam e-posta adresi | Maskelenmiş e-posta (`a***@example.com`) |
| Dosya içeriği | `storage_key`, boyut, MIME |

`audit_events.metadata` alanı **jsonb**'dir ve PII içermez — yalnız kimlik
referansları ve durum bilgisi ([DATABASE.md](DATABASE.md) §2.8).

---

## 8. CI güvenlik kontrolleri

Her PR'da çalışır; kırmızıysa merge edilmez.

| Kontrol | Araç | Kırılma koşulu |
|---|---|---|
| Sır taraması | `gitleaks` | Herhangi bir bulgu |
| Python bağımlılıkları | `pip-audit` | Yüksek/kritik açık |
| JS bağımlılıkları | `npm audit` | Yüksek/kritik açık |
| **Yetkilendirme testleri** | `pytest tests/authorization` | Herhangi bir başarısızlık |
| **Uç kapsamı** | Özel kontrol | Yetkilendirme testi olmayan uç var |
| Tip kontrolü | `mypy`, `tsc` | Hata |
| Lint | `ruff`, `eslint` | Hata |

> **Kural: Yeni bir uç eklendiğinde, yetkilendirme testi olmadan CI geçmez.**
> Detay → [AUTHORIZATION.md](AUTHORIZATION.md) §6.

---

### 8.1 Bilinen risk — herkes kurum açıp ADMIN olabiliyor (GUV-02)

`POST /institutions` (ve kayıtta `account_kind`) oturum açmış **herkese** açıktır;
kurumu açan kişi o kurumun `ADMIN`'i olur. Sahte bir kurum açıp kendi adına
koordinatör gibi davranmak mümkündür.

Mevcut azaltıcılar:

- Yeni kurum/kuruluş en düşük doğrulama seviyesiyle başlar; `T3` yalnız platform
  admini tarafından verilir (`/admin/organizations/{id}/verification-level`).
- Kurum ve kuruluş işaretleri için sabit kurallar fraud işareti üretir
  (`fraud_flags`, `/admin/fraud-queue`); karar admin'dedir.
- Doğrulama başvuruları admin kuyruğundan geçer (`/admin/verification-queue`);
  tüm admin kararları `audit_events`'e yazılır.

Kalan risk: kurum açma uç noktası bir onay adımı gerektirmez. Bu MVP için kabul
edilmiştir; çözüm (kurum açma için onay/davet) hackathon sonrası yol haritasındadır.

---

## 9. MVP'de bilinçli olarak ertelenen önlemler

Bu tablo, hackathon jürisine ve katkıcılara **neyin eksik olduğunu ve neden**
olduğunu açıkça söyler. Gizlemek, bilmemekten daha kötüdür.

| Önlem | Neden ertelendi | Ne zaman |
|---|---|---|
| ClamAV virüs taraması | Kurulum ve işletme maliyeti; MVP'de yalnız seed + ekip verisi | Faz 5.3 |
| Ayrı içerik domain'i | DNS + sertifika kurulumu; 3 haftada risk/fayda düşük | Faz 5.3 |
| PostgreSQL RLS | **Yanlış kurulmuş RLS, olmayan RLS'ten tehlikelidir** (§AUTHORIZATION 3) | V2 |
| MFA | Kapsam; MVP'de kullanıcı tabanı yok | V2 |
| GitHub OAuth kanıt doğrulama (T5) | Kapsam | V2 |
| Break-glass admin akışı | MVP'de admin `PRIVATE` evidence'a **hiç** erişemez — daha güvenli varsayılan | Faz 5.4 |
| `audit_events` partition | 3 haftalık veri için gereksiz | Faz 5.4 |
| Bağımlılık taraması otomasyonu | CI'da var, ancak otomatik güncelleme yok | Faz 5 |
