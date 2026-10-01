# API.md — API Sözleşmesi

REST API'nin uç listesi, yetki gereksinimleri, şema özetleri, hata kodları.

**Kaynak:** `yetkin360-final-analiz.md` §34 (uç listesi), §13.4 (tasarım kuralları).

**Bu dosya sözleşmedir.** [PLAN.md](../PLAN.md) "sözleşme önce" kuralı gereği:
bir ucun sözleşmesi burada yazılmadan `@fe` o ekranı yapamaz. Sözleşme yazılır →
`@fe` mock ile ilerler → backend gerçeğini bağlar.

**İlgili dosyalar:**
- Kim hangi uca erişebilir (test edilebilir matris) → [AUTHORIZATION.md](AUTHORIZATION.md)
- Alan adları ve tipler → [DATABASE.md](DATABASE.md)
- Durum geçiş kuralları → [STATE_MACHINE.md](STATE_MACHINE.md)
- Dosya yükleme güvenliği, rate limit → [SECURITY.md](SECURITY.md)

---

## 1. Tasarım kuralları

### 1.1 Temel

| Kural | Değer |
|---|---|
| Stil | REST |
| Taban yol | *(yok — router'lar kök dizinde mount edilir, ör. `/auth/login`, `/engagements`)* |
| Format | JSON, `application/json; charset=utf-8` |
| Zaman | ISO 8601, **UTC**, `Z` sonekiyle |
| ID | UUIDv7, string |
| Alan adları | İngilizce, `snake_case` |
| Kullanıcıya dönen mesajlar | **Türkçe** |

### 1.2 BOLA'ya karşı: sahiplik URL'den çıkarılır

> **Kritik tasarım kuralı: Kaynak sahipliği URL'den çıkarılmalı, gövdeden değil.**

```
✅ GET /engagements/{id}          → servis, kullanıcının erişimini KONTROL EDER
❌ GET /engagements?org_id={id}   → org_id'ye güvenmek = BOLA
```

BOLA (Broken Object Level Authorization) API saldırılarının ~%40'ında görülüyor
ve OWASP API Security Top 10'da hem 2019 hem 2023 sürümünde **1 numara**.
Çok kiracılı, kimlik doğrulamalı, nesne merkezli bir API olarak bu,
Yetkin360'ın **en olası ihlal vektörüdür**.

İstemciden gelen hiçbir `org_id`, `institution_id`, `talent_id` parametresine
yetki kararı için güvenilmez. Kapsam, oturumdan gelir.

### 1.3 Yetkisiz erişimde 404

> **Kural: Yetkisiz erişimde `403` değil `404` dönülür.**

`403` kaynağın varlığını sızdırır ("bu ID var ama senin değil" → enumeration).

| Durum | Kod |
|---|---|
| Kimlik doğrulanmamış (token yok/geçersiz) | `401` |
| Kimlik doğrulanmış, kaynak yok **veya** erişim yok | **`404`** |
| Kimlik doğrulanmış, kaynak erişilebilir ama eylem yasak | `403` |

Üçüncü satırın örneği: kendi engagement'ını görebilen öğrenci, onu `VERIFIED`
yapmaya kalkarsa `403` alır — kaynağın varlığı zaten biliniyor, sızıntı yok.
Ayrım ve her satırın testi → [AUTHORIZATION.md](AUTHORIZATION.md).

### 1.4 Hata formatı

Tüm hatalar aynı gövdeyi döner:

```json
{
  "code": "ENGAGEMENT_NOT_FOUND",
  "message": "Kayıt bulunamadı",
  "request_id": "018f3c2a-..."
}
```

| Alan | Açıklama |
|---|---|
| `code` | Makine tarafından okunan, sabit, `SCREAMING_SNAKE_CASE` |
| `message` | **Türkçe**, kullanıcıya gösterilebilir. Teknik detay sızdırmaz |
| `request_id` | Log ile eşleştirme için. Destek talebinde kullanıcı bunu verir |

Doğrulama hatalarında ek alan:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Girdi doğrulanamadı",
  "request_id": "...",
  "fields": { "email": "Geçerli bir e-posta adresi girin" }
}
```

**Kural:** İç hata (stack trace, SQL, dosya yolu) asla `message` alanına çıkmaz.

### 1.5 Ortak hata kodları

Aşağıdaki kodlar her uçta oluşabilir; uç tablolarında tekrarlanmaz.

| HTTP | `code` | Ne zaman |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Pydantic doğrulaması başarısız |
| `401` | `UNAUTHENTICATED` | Token yok, geçersiz veya süresi dolmuş |
| `401` | `EMAIL_NOT_VERIFIED` | E-posta doğrulanmadan yazma denemesi |
| `403` | `FORBIDDEN` | Kaynak görünür ama eylem yasak |
| `404` | `NOT_FOUND` | Kaynak yok **veya** erişim yok |
| `409` | `CONFLICT` | Optimistic locking çakışması, benzersizlik ihlali |
| `413` | `PAYLOAD_TOO_LARGE` | Dosya/gövde boyut sınırı aşıldı |
| `429` | `RATE_LIMITED` | Hız sınırı aşıldı (bkz. [SECURITY.md](SECURITY.md)) |
| `500` | `INTERNAL_ERROR` | Beklenmeyen hata. Detay yalnız logda |

### 1.6 Sayfalama

| Uç türü | Yöntem | Gerekçe |
|---|---|---|
| **Liste uçları** | **Cursor** (`created_at, id` bileşik) | Offset derin sayfalarda `OFFSET 10000` ile lineer yavaşlar ve eşzamanlı ekleme olduğunda kayıt atlar |
| Admin ekranları | Offset kabul edilebilir | Küçük veri, sayfa numarası UX'i gerekli |

**Cursor isteği:**
```
GET /engagements?limit=20&cursor=eyJjcmVhdGVkX2F0IjoiMjAyNi0wOS0xNVQxMDowMDowMFoiLCJpZCI6Ii4uLiJ9
```

**Cursor cevabı:**
```json
{
  "items": [ ... ],
  "next_cursor": "eyJjcmVhdGVk...",
  "has_more": true
}
```

| Parametre | Varsayılan | Sınır |
|---|---|---|
| `limit` | 20 | maks. 100 |
| `cursor` | — | Opak base64. İstemci içeriğini yorumlamaz |

`next_cursor` `null` ise son sayfadır. **Toplam sayı (`total`) dönülmez** —
büyük tabloda `COUNT(*)` pahalıdır. Gerekirse ayrı bir sayım ucu eklenir.

### 1.7 Kimlik doğrulama

**Karar (final analiz §15.3, [SECURITY.md](SECURITY.md) §6):** Token'lar
**response gövdesinde dönmez.** Tarayıcı cookie'leri taşır.

| Konu | Karar |
|---|---|
| Access token | JWT, **15 dk** (`ACCESS_TOKEN_TTL_MINUTES`), `httpOnly` + `Secure` + `SameSite=Lax` cookie |
| Refresh token | **Veritabanında**, 30 gün (`REFRESH_TOKEN_TTL_DAYS`), rotating, ayrı `httpOnly` cookie |
| Rotasyon | Her `/auth/refresh` yeni çift üretir; eski refresh token geçersizleşir |
| Yeniden kullanım tespiti | Kullanılmış bir refresh token tekrar gelirse **o ailenin tümü iptal edilir** (çalınma sinyali) |
| CSRF | `SameSite=Lax` + double-submit token: `csrf_token` cookie'si (JS okuyabilir) + `X-CSRF-Token` başlığı |
| Şifre | **Argon2id** |

**Neden gövde değil cookie:** `localStorage`'daki token, herhangi bir XSS
açığını tam hesap ele geçirmesine çevirir. `httpOnly` cookie JavaScript'ten
okunamaz. Gerekçenin tamamı: [SECURITY.md](SECURITY.md) §6.

**İstemci sonucu:** Frontend token saklamaz, `Authorization` başlığı kurmaz.
Tüm istekler `credentials: "include"` ile gider; yazma isteklerine
`X-CSRF-Token` başlığı eklenir.

### 1.8 Yetki sütununun okunuşu

Uç tablolarındaki **Yetki** sütunu kısaltmaları:

| Kısaltma | Anlamı |
|---|---|
| — | Kimlik doğrulaması gerekmez (public) |
| `AUTH` | Herhangi bir doğrulanmış kullanıcı |
| `TALENT` | Talent profili olan kullanıcı, **kendi** kaydı |
| `ORG:ADMIN` | Kurumda `ADMIN` rolü |
| `ORG:MEMBER` | Kurumda `ADMIN` veya `MEMBER` |
| `ORG:SUPERVISOR` | Engagement'ın `supervisor_user_id` alanındaki kişi |
| `INST:COORD` | Kurumda `COORDINATOR` veya `ADMIN` |
| `ADMIN` | `users.is_platform_admin = true` |

Kesin, test edilebilir matris → [AUTHORIZATION.md](AUTHORIZATION.md).

---

## 2. Uçlar

### 2.1 Kimlik doğrulama — `/auth`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/auth/register` | — | `email`, `password`, `full_name` | `201` — `user_id` (her zaman, kayıtlı e-postada bile) | `422`, `429` |
| `POST` | `/auth/login` | — | `email`, `password` | `200` — `user_id`, `role`, `email_verified` + **3 cookie** | `401 INVALID_CREDENTIALS`, `423 ACCOUNT_LOCKED`, `429` |
| `POST` | `/auth/refresh` | — | — (refresh cookie'den) | `204` + **yenilenmiş cookie'ler** | `401 INVALID_REFRESH_TOKEN` |
| `POST` | `/auth/logout` | `AUTH` | — | `204` + cookie'ler silinir | — |
| `POST` | `/auth/verify-email` | — | `token` | `204` | `400 INVALID_TOKEN`, `410 TOKEN_EXPIRED` |
| `POST` | `/auth/resend-verification` | oturum + CSRF | — | `204` (her zaman) | `401`, `403 CSRF_FAILED` |
| `POST` | `/auth/forgot-password` | — | `email` | `204` (her zaman) | `429` |
| `POST` | `/auth/reset-password` | — | `token`, `new_password` | `204` | `400 INVALID_TOKEN`, `410 TOKEN_EXPIRED` |

**Cookie'ler.** `/auth/login` ve `/auth/refresh` üç cookie yazar:

| Cookie | `httpOnly` | Ömür | İçerik |
|---|---|---|---|
| `access_token` | ✅ | 15 dk | JWT |
| `refresh_token` | ✅ | 30 gün | Opak değer; karşılığı DB'de |
| `csrf_token` | ❌ (JS okumalı) | oturum | Double-submit için rastgele değer |

Üçü de `Secure` + `SameSite=Lax`. `refresh_token` cookie'sinin `Path` değeri
`/auth` — yalnız `/auth/*` uçlarına gider; `/auth/logout` da token ailesini
iptal edebilsin diye `/auth/refresh` ile sınırlı değildir (YET-185). Eski
`/auth/refresh` yollu cookie login/refresh/logout sırasında silinir.

**Kritik davranışlar:**
- Yazma metotlarında (`POST`/`PATCH`/`DELETE`) `X-CSRF-Token` başlığı
  `csrf_token` cookie'siyle eşleşmezse → `403 CSRF_FAILED`. Bu, kaynağın
  varlığını sızdırmadığı için 404 kuralının istisnasıdır.
- `/auth/refresh` kullanılmış bir token alırsa → **token ailesinin tamamı
  iptal edilir**, `401 INVALID_REFRESH_TOKEN`, `audit_events`'e kayıt düşer.
- `/auth/resend-verification` doğrulanmamış oturum sahibine yeni link gönderir ve önceki kullanılmamış
  linkleri geçersiz kılar. Zaten doğrulanmış hesap ya da sınır aşımı (1/dakika, 5/saat — kayıt
  token'ı dahil) sessiz no-op'tur: yine `204`, yeni token/outbox satırı yok. Alıcı her zaman hesabın
  kendi adresidir (oturumdan; istekten gelmez).
- `/auth/forgot-password` **e-posta kayıtlı olmasa da `204`** döner. Aksi hâlde
  hangi e-postaların kayıtlı olduğu sızar (kullanıcı numaralandırma).
- `/auth/register` aynı prensiple **kayıtlı bir e-postayla çağrılsa da her
  zaman `201`** döner (`EMAIL_TAKEN` gibi ayırt edici bir kod yok) — var olan
  hesap dokunulmadan kalır, dönen `user_id` gerçek değildir. Var olan hesap
  sahibine "e-postan tekrar kullanılmaya çalışıldı" bildirimi outbox
  (PLAN 1.5) üzerinden atılacak; MVP'de henüz yok.
- `/auth/login` başarısızlığında "e-posta yanlış" / "şifre yanlış" ayrımı
  **yapılmaz** — tek mesaj: "E-posta veya şifre hatalı."
- `failed_login_count` eşiği aşılınca `locked_until` dolar → `423`.
- Kayıt sonrası e-posta doğrulanana kadar **hiçbir yazma işlemi yapılamaz**
  → `401 EMAIL_NOT_VERIFIED`.

**Karar — kayıtta rol seçimi yoktur.** `register` isteği `role` almaz.

Herkes aynı şekilde kaydolur; sunucu **tek transaction'da** `users` +
`talent_profiles` satırını birlikte açar ([DATABASE.md](DATABASE.md) §"Kullanıcı
kaydı"). Talent profili boş alanlarla doğar, kullanıcı `PATCH /talents/me` ile
doldurur.

Gerekçe:
- `users` tablosunda **`role` sütunu yoktur.** Rol kişiye değil **üyeliğe**
  aittir: `institution_members.role`, `organization_members.role`.
- Kullanıcı kendi rolünü **beyan edemez.** Koordinatör veya kurum üyeliği
  yalnız davetle verilir — aksi hâlde herkes kendini koordinatör ilan ederdi.
- Kayıt ekranı ([PLAN.md](../PLAN.md) 1.13) tek akış: e-posta, şifre, ad soyad.

Kurumdan biri platforma katılırken de aynı kapıdan girer; kurum üyeliği
sonradan eklenir. Bu kişinin talent profili boş kalır, zararı yoktur.

### 2.2 Profil ve yetkinlik — `/me`, `/talents`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `GET` | `/me` | `AUTH` | — | `200` — `user`, `talent_profile?`, `organizations[]`, `institutions[]` | — |
| `GET` | `/talents/{id}` | `AUTH` | — | `200` — profil (**`visibility`'ye göre budanmış**) | `404` |
| `PATCH` | `/talents/me` | `TALENT` | `headline?`, `department?`, `study_year?`, `city?`, `visibility?`, `public_slug?` | `200` — güncel profil | `409 SLUG_TAKEN` |
| `GET` | `/talents/me/skills` | `TALENT` | — | `200` — `items[]` (`skill`, `claimed_level`) | — |
| `POST` | `/talents/me/skills` | `TALENT` | `skill_id`, `claimed_level?` | `201` | `404 SKILL_NOT_FOUND`, `409 ALREADY_CLAIMED` |
| `DELETE` | `/talents/me/skills/{skill_id}` | `TALENT` | — | `204` | `404` |
| `GET` | `/talents/me/signals` | `TALENT` | `skill_id?` | `200` — **kanıt dökümü** | — |

**`GET /talents/{id}` görünürlük budaması:** Cevap gövdesi isteği yapanın kim
olduğuna göre **daralır** — `PRIVATE` alanlar hiç dönmez. Bu bir yetki kontrolü
değil, alan seviyesinde filtredir. Kurallar → [AUTHORIZATION.md](AUTHORIZATION.md).

**`GET /talents/me/signals` — ürünün kalbi.** "Neden STRONG?" sorusunun cevabı.
Her sinyal kaynağıyla birlikte döner:

```json
{
  "items": [
    {
      "skill": { "id": "...", "name_tr": "Python", "slug": "python" },
      "signals": [
        {
          "source_type": "ATTESTATION",
          "strength": "STRONG",
          "occurred_at": "2026-08-14T00:00:00Z",
          "attested_by": { "name": "Acme Yazılım A.Ş.", "trust_level": "T3" },
          "superseded": false
        },
        { "source_type": "SELF_CLAIM", "strength": "NONE", "occurred_at": "..." }
      ]
    }
  ]
}
```

> Sinyal listesi **ham** dönülür; tek bir "seviye" sayısı hesaplanıp dönülmez.
> Bir yetkinliğin seviyesi bir kolon değildir ([DOMAIN.md](DOMAIN.md) §3.14).

### 2.3 Yetkinlik taksonomisi — `/skills`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `GET` | `/skills` | `AUTH` | `q?`, `category?`, `limit?`, `cursor?` | `200` — `items[]` (`id`, `slug`, `name_tr`, `name_en`, `category`, `parent_id`) | — |

- Yalnız `status = 'ACTIVE'` skill'ler döner.
- `q` araması `name_tr` + `name_en` + `slug` üzerinde çalışır.
- **Serbest metin skill oluşturma ucu yoktur.** Kullanıcı öneri gönderebilir,
  admin onaylar (§2.8).

### 2.4 Kurum — `/organizations`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/organizations` | `AUTH` | `name`, `domain?`, `legal_id?` | `201` — kurum (`verification_level: T1`) | `409 LEGAL_ID_TAKEN` |
| `GET` | `/organizations/{id}` | `AUTH` | — | `200` — kurum | `404` |
| `POST` | `/organizations/{id}/members` | `ORG:ADMIN` | `email`, `role` | `201` — davet | `404`, `409 ALREADY_MEMBER` |
| `POST` | `/organizations/{id}/verify-domain` | `ORG:ADMIN` | — | `200` — `dns_txt_record`, `status` | `404`, `400 FREE_EMAIL_DOMAIN` |

**Domain doğrulama (T1 → T2):** Uç bir DNS TXT kaydı üretir. Kurum bu kaydı
domain'ine ekler, uç yeniden çağrılır, doğrulanırsa `verification_level = 'T2'`
olur. **Ücretsiz posta sağlayıcıları (gmail, hotmail vb.) reddedilir**
→ `400 FREE_EMAIL_DOMAIN`.

T3 ve T4 bu uçtan verilmez — T3 admin kuyruğundan (§2.8), T4 koordinatör
onayından gelir.

### 2.5 Üniversite / koordinatör — `/institutions`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `GET` | `/institutions/{id}/dashboard` | `INST:COORD` | — | `200` — özet sayaçlar | `404` |
| `GET` | `/institutions/{id}/engagements` | `INST:COORD` | `status?`, `limit?`, `cursor?` | `200` — `items[]` | `404` |
| `POST` | `/institutions/{id}/reminders` | `INST:COORD` | `engagement_ids[]`, `template` | `202` — `queued_count` | `404`, `429` |

**Dashboard cevabı** — koordinatörün "durumu bir bakışta gör" ihtiyacı:

```json
{
  "counts_by_status": { "ACTIVE": 42, "PENDING_EVALUATION": 7, "VERIFIED": 118 },
  "pending_evaluation": [ { "engagement_id": "...", "talent_name": "...",
                            "organization_name": "...", "days_waiting": 12 } ],
  "unapproved": [ { "engagement_id": "...", "submitted_at": "..." } ]
}
```

**`/reminders` `202` döner, `200` değil** — e-postalar `outbox` üzerinden
asenkron gönderilir, istek anında gönderilmez ([DATABASE.md](DATABASE.md) §5).

### 2.6 Engagement — `/engagements`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/engagements` | `ORG:MEMBER` veya `TALENT` | `talent_id`, `organization_id`, `institution_id?`, `kind`, `title`, `started_on?`, `ended_on?`, `confidential?` | `201` — engagement (`status: DRAFT`) | `404`, `400` |
| `GET` | `/engagements/{id}` | taraflardan biri | — | `200` — engagement + `available_transitions[]` | `404` |
| `GET` | `/engagements` | `AUTH` | `status?`, `role?`, `limit?`, `cursor?` | `200` — **yalnız erişilebilir olanlar** | — |
| `POST` | `/engagements/{id}/transitions` | duruma göre | `to_status`, `version`, `reason?` | `200` — güncel engagement | `403`, `404`, `409`, `422 ILLEGAL_TRANSITION`, `422 PRECONDITION_FAILED` |
| `POST` | `/engagements/{id}/tasks` | `ORG:SUPERVISOR` veya `TALENT` | `title`, `status?` | `201` | `404`, `403` |
| `POST` | `/engagements/{id}/deliverables` | `TALENT` | `title`, `description?`, `task_id?`, `evidence_ids[]` | `201` | `404`, `403`, `422 EVIDENCE_REQUIRED` |

**`GET /engagements` listesinde `org_id` parametresi yoktur** (§1.2).
Kapsam oturumdan çıkarılır; `role` parametresi yalnız **kendi** erişilebilir
kayıtlarını filtreler (`talent` / `organization` / `institution`).

#### Tek geçiş ucu: `POST /engagements/{id}/transitions`

> Durum geçişleri için **tek bir uç** vardır. Bu, durum makinesini tek yerde
> tutar ve her geçişe ayrı uç yazmaktan daha güvenlidir — her uçta
> yetkilendirmeyi tekrar yazma riski ortadan kalkar.

İstek:
```json
{ "to_status": "ACTIVE", "version": 3, "reason": null }
```

| Hata | Anlamı |
|---|---|
| `409 CONFLICT` | `version` eski — başkası aynı anda değiştirdi. İstemci yeniden okur |
| `422 ILLEGAL_TRANSITION` | Bu durumdan o duruma geçiş **tanımlı değil** |
| `422 PRECONDITION_FAILED` | Geçiş tanımlı ama ön koşul sağlanmıyor (ör. değerlendirme yok) |
| `403 FORBIDDEN` | Geçiş tanımlı, ön koşul tamam, ama **bu aktör yetkili değil** |

Bu üç hatanın ayrı olması kasıtlıdır: istemci kullanıcıya doğru mesajı gösterebilir.

`GET /engagements/{id}` cevabındaki `available_transitions[]`, **bu kullanıcının
şu anda yapabileceği** geçişleri listeler — frontend butonları bundan üretir,
durum makinesini kendisi hesaplamaz.

Tüm geçişler, ön koşullar ve yetkili aktörler → [STATE_MACHINE.md](STATE_MACHINE.md).

### 2.7 Kanıt ve dosya — `/evidence`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/evidence/upload-url` | `TALENT` | `filename`, `mime_type`, `size_bytes` | `200` — `upload_url`, `storage_key`, `expires_at` | `400 UNSUPPORTED_TYPE`, `413` |
| `POST` | `/evidence` | `TALENT` | `storage_key` veya `external_uri`, `kind`, `provenance`, `title`, `skill_ids[]?`, `deliverable_id?` | `201` — evidence (`scan_status: PENDING`) | `400`, `404` |
| `GET` | `/evidence/{id}/download-url` | erişim hakkı olan | — | `200` — `download_url`, `expires_at` | `404`, `409 SCAN_PENDING`, `409 SCAN_INFECTED` |

**Üç adımlı yükleme akışı:**

```
1. POST /evidence/upload-url   → imzalı URL al (dosya henüz gitmedi)
2. PUT  <upload_url>           → dosya doğrudan object storage'a (backend'den geçmez)
3. POST /evidence              → kayıt oluştur, scan_status=PENDING
```

Neden üç adım: dosya backend sunucusundan **geçmez** — bellek ve zaman aşımı
riski ortadan kalkar. Güvenlik kontrolleri (magic-byte, `{uuid}.{ext}` yeniden
adlandırma, boyut sınırı) → [SECURITY.md](SECURITY.md).

**`download-url` sahiplikten değil erişim hakkından çıkar:** URL'deki `{id}`
üzerinden servis, isteği yapanın bu kanıtı görme hakkı olup olmadığını kontrol
eder. `scan_status != 'CLEAN'` ise indirme verilmez.

### 2.8 Değerlendirme, tanıklık, itiraz

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/engagements/{id}/evaluation` | `ORG:SUPERVISOR` veya `TALENT` | `direction`, `items[]`, `private_note?` | `201` | `403`, `404`, `409 ALREADY_SUBMITTED`, `422 INVALID_STATUS` |
| `POST` | `/engagements/{id}/attestations` | `ORG:SUPERVISOR` / `INST:COORD` | `subject_type`, `subject_id`, `claim_type`, `skill_id?`, `statement?` | `201` — **gerçekleşen `claim_type` ile** | `403`, `404`, `422` |
| `POST` | `/attestations/{id}/revoke` | tanıklığı yapan | `revoke_reason` | `200` | `403`, `404`, `409 ALREADY_REVOKED` |
| `POST` | `/engagements/{id}/dispute` | `TALENT` veya `ORG:MEMBER` | `reason` | `200` | `403`, `404`, `422` |

**`items[]` şeması** (`POST /evaluation`):
```json
{
  "direction": "ORG_TO_TALENT",
  "items": [
    { "skill_id": "...", "criterion": "Python kullanımı", "rating": "EXCEEDS", "comment": "..." },
    { "skill_id": null,  "criterion": "Zamanında teslim",  "rating": "NOT_OBSERVED" }
  ],
  "private_note": "Öğrenciye gösterilmez"
}
```

- `rating` değerleri: `BELOW` | `MEETS` | `EXCEEDS` | **`NOT_OBSERVED`**.
  `NOT_OBSERVED` birinci sınıf bir cevaptır ve formda **her zaman seçilebilir**
  olmalıdır ([DOMAIN.md](DOMAIN.md) D8).
- `private_note` **hiçbir okuma ucunda dönmez** — öğrenciye, public profile ve
  loglara çıkmaz (D9).
- Değerlendirme gönderildikten sonra **değiştirilemez** (append-only).

**Attestation'ın kritik davranışı — sessiz düşürme:**

> İstemci `claim_type: "COMPETENCE"` gönderse bile, [DOMAIN.md](DOMAIN.md) §3.11
> ön koşullarından biri eksikse kayıt **`PARTICIPATION` olarak** oluşturulur.
> İstek **reddedilmez** — düşürülür.

Bu yüzden `201` cevabı **gerçekleşen** `claim_type`'ı içerir ve istemci bunu
kullanıcıya göstermelidir:

```json
{
  "id": "...",
  "claim_type": "PARTICIPATION",
  "requested_claim_type": "COMPETENCE",
  "downgrade_reasons": ["ENGAGEMENT_TOO_SHORT", "NO_DELIVERABLE_FOR_SKILL"]
}
```

> ❓ AÇIK SORU: `downgrade_reasons` kodlarının tam listesi final analizde yok.
> §3.11'deki 6 ön koşuldan türetilebilir ama kesin kod adları
> [PLAN.md](../PLAN.md) 2.8 yazılırken kesinleşmeli.

**`/revoke` yan etkisi:** Tanıklık geri çekilince ilgili `skill_signals`
kayıtları `superseded` olur — **silinmez** (D12). Tek transaction.

**`/dispute` MVP kapsamı:** `DISPUTED` akışı [PLAN.md](../PLAN.md) R.3 —
"vakit kalırsa" maddesidir. Uç sözleşmesi burada tanımlı ama hackathon
MVP'sinde gerçeklenmeyebilir.

### 2.9 Public — `/public`

**Kimlik doğrulaması gerektirmez.** Sıkı rate limit uygulanır ([SECURITY.md](SECURITY.md)).

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `GET` | `/public/p/{slug}` | — | — | `200` — public profil | `404` |
| `GET` | `/public/v/{token}` | — | — | `200` — **doğrulama kaydı** | `404` |

**`/public/v/{token}` — jürinin telefonundan açacağı uç.** Ürünün tüm iddiasının
tek ekrandaki kanıtı:

```json
{
  "title": "Backend Geliştirme Stajı",
  "talent_name": "Ahmet Y.",
  "organization_name": "Acme Yazılım A.Ş.",
  "organization_trust_level": "T3",
  "institution_name": "XYZ Üniv. Bilgisayar Müh.",
  "started_on": "2026-06-15",
  "ended_on": "2026-08-15",
  "verified_at": "2026-08-20T09:12:00Z",
  "attested_skills": [
    { "name_tr": "Python", "claim_type": "COMPETENCE", "attestor_name": "Mehmet K." }
  ]
}
```

- Veriler `verified_experiences` **snapshot'ından** okunur — kurum silinse,
  adını değiştirse veya platformdan ayrılsa bile link çalışmaya devam eder
  ([DOMAIN.md](DOMAIN.md) §3.13).
- `visibility != 'PUBLIC'` ise `404`.
- Token tahmin edilemez olmalıdır (rastgele, ≥128 bit).
- `/public/p/{slug}` yalnız `talent_profiles.visibility = 'PUBLIC'` profilleri
  döner; `PRIVATE` alanlar hiç yer almaz.

### 2.10 Admin — `/admin`

**Tümü `ADMIN` yetkisi gerektirir** (`users.is_platform_admin = true`).

| Metot | Yol | İstek | Cevap | Hatalar |
|---|---|---|---|---|
| `GET` | `/admin/verification-queue` | `limit?`, `offset?` | `200` — bekleyen kurum doğrulamaları | — |
| `POST` | `/admin/organizations/{id}/verification-level` | `verification_level`, `note?` | `200` | `404`, `422` |

- Admin uçları **offset sayfalama** kullanabilir (§1.6).
- Her doğrulama seviyesi değişikliği `audit_events` üretir.
- Bu uçlar T3 verilmesi içindir; T1/T2 otomatik, T4 koordinatör onayıyla gelir.

> ❓ AÇIK SORU: Admin skill yönetimi ucu ([PLAN.md](../PLAN.md) 3.6 "skill
> yönetimi") §34 listesinde yok. Kullanıcı skill önerisi gönderme ucu ve admin
> onay ucu gerekiyor mu, yoksa MVP'de skill'ler yalnız seed'den mi gelecek?

---

## 3. Uç özeti

Toplam **38 uç**. Hackathon fazlarına dağılımı → [PLAN.md](../PLAN.md).

| Grup | Uç sayısı | Faz |
|---|---|---|
| `/auth` | 7 | 1 |
| `/me`, `/talents` | 7 | 1 |
| `/skills` | 1 | 1 |
| `/organizations` | 4 | 1 |
| `/institutions` | 3 | 3 |
| `/engagements` | 6 | 2 |
| `/evidence` | 3 | 2 |
| Değerlendirme / tanıklık / itiraz | 4 | 2 |
| `/public` | 2 | 3 |
| `/admin` | 2 | 3 |

**Definition of Done hatırlatması:** Yeni uç = **aynı commit'te yetkilendirme
testi**. Testsiz uç commit edilmez (CLAUDE.md). Her ucun test satırı →
[AUTHORIZATION.md](AUTHORIZATION.md).
