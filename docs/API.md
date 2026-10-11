# API.md — API Sözleşmesi

REST API'nin uç listesi, yetki gereksinimleri, şema özetleri, hata kodları.

**Kaynak:** `yetkin360-final-analiz.md` §34 (uç listesi), §13.4 (tasarım kuralları).

**Bu dosya sözleşmedir.** [PLAN.md](PLAN.md) "sözleşme önce" kuralı gereği:
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

`request_id` her istekte sunucu tarafından üretilir (istemcinin `X-Request-ID` başlığı
dikkate alınmaz), aynı değer `X-Request-ID` yanıt başlığında ve sunucu hata logunda bulunur.
Bilinmeyen yol `404 NOT_FOUND`, yanlış yöntem `405 METHOD_NOT_ALLOWED` (`Allow` başlığıyla),
işlenmeyen istisna `500 INTERNAL_ERROR` döner; üçü de yukarıdaki gövdeyi taşır.
`ENVIRONMENT=production` iken `/docs`, `/redoc` ve `/openapi.json` kapalıdır (404).

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
| `429` | `RATE_LIMITED` | Hız sınırı aşıldı; `Retry-After` başlığı (saniye) döner (bkz. [SECURITY.md](SECURITY.md)) |
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
| `POST` | `/auth/register` | — | `email`, `password`, `full_name`, `account_kind` (ops., varsayılan `TALENT`), `entity_name` (ops., `account_kind≠TALENT` ise zorunlu), `legal_id` (ops., 16 haneli MERSİS; yalnız `ORGANIZATION`) | `201` — `user_id` (her zaman, kayıtlı e-postada bile) | `422`, `409 LEGAL_ID_TAKEN`, `429` |
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
- `/auth/register`, `account_kind=ORGANIZATION` iken **ücretsiz e-posta sağlayıcı
  adreslerini `422` ile reddeder** (`fields.email`); doğrulama e-postası böylece
  her zaman kurumsal adrese gider. Karar yalnız istekten verilir (hesabın var
  olup olmadığından bağımsız — enumeration sinyali değildir). `legal_id` yalnız
  biçim olarak doğrulanır ve kuruluşa yazılır; kuruluş yine `T1` açılır.
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

**Karar (revize — bkz. PLAN 3.52) — kayıt `role` almaz, ama opsiyonel
`account_kind` ile kuruluş/kurum oluşturabilir.** `users` tablosunda hâlâ
**`role` sütunu yoktur** ve koordinatör/kurum **üyeliği** hâlâ yalnız
davetle verilir — bu ilke değişmedi. `account_kind` bir yetki beyanı
**değildir**; yalnız kayıt sırasında ek olarak bir `Organization` veya
`Institution` satırı açılıp açılmayacağını belirler, çağıran o varlığın
**ADMIN**'i olur.

Herkes aynı şekilde kaydolur; sunucu **tek transaction'da** `users` +
`talent_profiles` satırını birlikte açar ([DATABASE.md](DATABASE.md) §"Kullanıcı
kaydı") — bu her zaman olur, `account_kind` ne olursa olsun. Talent profili
boş alanlarla doğar, kullanıcı `PATCH /talents/me` ile doldurur.

- `account_kind=TALENT` (varsayılan): yalnız kullanıcı + talent profili.
- `account_kind=ORGANIZATION`: yukarıdakine ek olarak `entity_name` ile bir
  `Organization` (T1, `POST /organizations`'la birebir aynı — doğrulanmamış,
  kendiliğinden hizmete açık) oluşturulur, kullanıcı onun ADMIN'i olur.
- `account_kind=INSTITUTION`: aynı şekilde bir `Institution` (T1) oluşturulur,
  kullanıcı onun ADMIN'i olur.

**Bu neden güvenlik ilkesini bozmuyor:** `POST /organizations` ve
`POST /institutions` zaten davetsiz, kimliği doğrulanmış **herhangi bir**
kullanıcıya açıktı (bkz. §2.4/§2.5) — kuruluş/kurum oluşturmak hiçbir zaman
davet gerektirmedi, yalnız T1→T2/T3 **doğrulaması** sonradan ve ayrı bir
admin/domain sürecinden geçer. `account_kind`, kayıt sonrası zaten
yapılabilecek bir işlemi tek adıma indirgiyor — yeni bir güven sınırı
açmıyor. Değişmeyen şey: **koordinatörlük** ve **var olan bir kuruma/kuruluşa
üyelik** hâlâ yalnız davetle (`POST /institutions/{id}/members`,
`POST /organizations/{id}/members`) verilir, kayıt ekranından asla.

Kurumdan biri platforma katılırken de aynı kapıdan girer; `account_kind=TALENT`
ile kaydolup kurum üyeliği sonradan eklenir. Bu kişinin talent profili boş
kalır, zararı yoktur.

### 2.2 Profil ve yetkinlik — `/me`, `/talents`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `GET` | `/me` | `AUTH` | — | `200` — `user`, `talent_profile?`, `organizations[]`, `institutions[]` | — |
| `GET` | `/talents/{id}` | `AUTH` | — | `200` — profil (**`visibility`'ye göre budanmış**) | `404` |
| `PATCH` | `/talents/me` | `TALENT` | `full_name?`, `headline?`, `department?`, `study_year?`, `city?`, `visibility?`, `public_slug?` | `200` — güncel profil | `409 SLUG_TAKEN`, `422 FIELD_REQUIRED` |
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
| `POST` | `/organizations/{id}/members` | `ORG:ADMIN` | `email`, `role` | `202` — `{"status": "queued"}` | `404`, `422 INVALID_ROLE` |
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
| `POST` | `/institutions/{id}/members` | `INST:ADMIN` | `email`, `role` | `202` — `{"status": "queued"}` | `404`, `422 INVALID_ROLE` |
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
Sınırlar (YET-213): `engagement_ids` en fazla 100, `template` kapalı küme
(şimdilik yalnız `evaluation_pending`; dışı `422`), aynı (engagement, template)
için 24 saatte 1 hatırlatma (tekrarlar sessizce atlanır, `queued_count`'a girmez),
kurum başına saatte 20 istek (aşım `429 RATE_LIMITED` + `Retry-After`).
Yetkisiz çağıran her zaman `404` alır ve kota harcamaz.

### 2.6 Engagement — `/engagements`

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/engagements` | `ORG:MEMBER` veya `TALENT` | `talent_id`, `organization_id`, `institution_id?`, `kind`, `title`, `started_on?`, `ended_on?`, `confidential?` | `201` — engagement (`status: DRAFT`) | `404`, `400` |
| `GET` | `/engagements/{id}` | taraflardan biri | — | `200` — engagement + `available_transitions[]` | `404` |
| `GET` | `/engagements` | `AUTH` | `status?`, `role?`, `limit?`, `cursor?` | `200` — **yalnız erişilebilir olanlar**; her satır `organization_id`, `institution_id`, `talent_id`, `talent_name` taşır (kuruluş/kurum tarafı listeyi öğrenciye göre gösterir) | — |
| `POST` | `/engagements/{id}/transitions` | duruma göre | `to_status`, `version`, `reason?`, `notify_user_ids?`, `notify_emails?` | `200` — güncel engagement | `403`, `404`, `409`, `422 ILLEGAL_TRANSITION`, `422 PRECONDITION_FAILED` |
| `GET` | `/engagements/approval-recipients` | `TALENT` (kendi okulu) | — | `200` — çağıranın okulundaki koordinatörler (`user_id`, `display_name`, `email_hint` maskeli); "Yeni çalışma" formu oluşturur oluşturmaz onaya gönderir | `404` (profil ya da okul yok) |
| `GET` | `/engagements/{id}/approval-recipients` | `DRAFT` çalışmayı onaya gönderebilen (öğrenci / kuruluş üyesi) | — | `200` — çalışmanın kurumundaki koordinatörler: `user_id`, `display_name`, `email_hint` (maskeli, ör. `ke•••@uni.edu.tr`) | `404` (kapsam dışı, `DRAFT` değil, kurumsuz — tek gövde) |
| `POST` | `/engagements/{id}/tasks` | Kuruluş üyesi / koordinatör (yalnız `ACTIVE`) veya `TALENT` (kendi çalışması; `DRAFT`, `ACTIVE`) | `title`, `description?`, `due_at?`, `skill_id?` | `201` — görev (`verified`, `verified_at`) | `404`, `403`, `422 PRECONDITION_FAILED` |
| `POST` | `/engagements/{id}/tasks/{task_id}/verify` | Kuruluş üyesi / koordinatör — **öğrenci kendi görevini doğrulayamaz** | — | `200` — görev (`verified: true`) | `404`, `403`, `409 TASK_ALREADY_VERIFIED`, `422 PRECONDITION_FAILED` |
| `POST` | `/engagements/{id}/deliverables` | `TALENT` | `title`, `description?`, `task_id?`, `evidence_ids[]` | `201` | `404`, `403`, `422 EVIDENCE_REQUIRED` |

**`GET /engagements` listesinde `org_id` parametresi yoktur** (§1.2).
Kapsam oturumdan çıkarılır; `role` parametresi yalnız **kendi** erişilebilir
kayıtlarını filtreler (`talent` / `organization` / `institution`).

#### Görev doğrulama

Görevi kimin eklediği, doğrulanmış sayılıp sayılmayacağını belirler:

- **Kuruluş üyesi ya da koordinatör eklerse** görev doğrulanmış oluşur; `skill_id` varsa `TASK` kaynaklı yetkinlik sinyali hemen yazılır.
- **Öğrenci kendi çalışmasına eklerse** görev **doğrulanmamış** oluşur (`verified: false`) ve sinyal üretmez. Sinyal, `…/tasks/{task_id}/verify` çağrıldığında yazılır.
- Doğrulamayı yalnız çalışmanın kuruluş üyesi ya da kurum koordinatörü yapabilir. Öğrenci, aynı zamanda o kuruluşun üyesi ya da koordinatör olsa bile kendi görevini doğrulayamaz (`403`).
- Doğrulama `DRAFT`, `PENDING_APPROVAL`, `REJECTED` ve `CANCELLED` durumlarında yapılamaz (`422`).
- `GET /engagements/{id}` yanıtındaki her görev `verified` alanını taşır.

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

**Okula bağlı türler.** `INTERNSHIP` ve `CAPSTONE` oluşturulurken öğrencinin
profilinde okul varsa `institution_id` gönderilmese de o okul bağlanır; böylece
staj, okul onayını (T1/T2) atlayıp T4 ile kendi kendine aktifleştirilemez.
`SHORT_PROJECT` ve `PART_TIME` okulsuz oluşturulabilir (T4: hemen `ACTIVE`,
doğrulamayı en sonda kuruluş yapar); öğrenci isterse `institution_id` gönderip
okul onayını seçer.

**Onay isteğinin alıcısı (`notify_user_ids` / `notify_emails`).** `DRAFT → PENDING_APPROVAL`
geçişinde **isteğe bağlıdır**, diğer geçişlerde yok sayılır; her biri en fazla 5 öğe.
Verilmezse bildirim kurumun tüm koordinatörlerine gider.

- Arayüz koordinatörü `GET /engagements/{id}/approval-recipients` listesinden seçtirir
  ve kimliğini `notify_user_ids` ile gönderir; öğrenci adres yazmaz.
- O kurumun `COORDINATOR` üyesine ait kimlik/adresler bildirimi **tek başına** alır.
- Başka kurumun koordinatörü, kurum yöneticisi, kuruluş üyesi ya da bilinmeyen bir
  kimlik/adres **hata vermeden yok sayılır**; hiçbiri eşleşmezse bildirim yine tüm
  koordinatörlere gider. Yanıt her durumda aynıdır — istemci kimin kurumda kayıtlı
  olduğunu bu uçtan öğrenemez.
- Onay yetkisi değişmez: kurumun her koordinatörü çalışmayı onaylayabilir. Alan
  yalnız bildirimin kime gideceğini belirler.
- Biçimi bozuk adres ya da 5'ten fazla öğe → `422 VALIDATION_ERROR`.
- Outbox'a adres değil kullanıcı kimliği yazılır (PII).

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
| `POST` | `/evidence/{id}/request-certificate-check` | sahibi (TALENT) | — | `201` — `CertificateCheck` (`status: PENDING`) | `404`, `422 NOT_CERTIFICATE_KIND`, `409 EVIDENCE_NOT_CLEAN`, `409 ALREADY_REQUESTED` |
| `GET` | `/engagements/{id}/certificate-checks` | ilgili talent veya koordinatör/supervisor | — | `200` — `items[]` | `404` |
| `POST` | `/certificate-checks/{id}/resolve` | engagement'ın koordinatörü/supervisor'u | `decision` (`CONFIRMED`/`REJECTED`) | `200` | `404`, `409 NOT_PENDING` |

**PLAN 3.55 — sertifika kontrolü (Udemy/Coursera, faz 2):** öğrencinin açık
rızasıyla (upload anında otomatik DEĞİL — KVKK, final-analiz §11.2) tetiklenir.
AI (`evidence.certificate_check_requested` outbox handler'ı, OpenRouter görsel
modeli) sertifikadaki ismi/kimlik numarasını/QR'ı (QR: OpenCV, deterministik)
çıkarır — hiçbir zaman "doğrulandı" kararı vermez (final-analiz §11.4.2/§39).
İsim eşleşmesi (`name_match`) kod tarafında düz string karşılaştırmasıyla
hesaplanır. Sertifika iki farklı çözünürlükte okunur; sertifika numarası ve
link yalnız okumalar uyuşursa kabul edilir (uyuşmazsa `null`). Udemy ve BTK
doğrulama linki okunan sertifika numarasından kod tarafında üretilir. Resmi
doğrulama sayfası Coursera ve BTK Akademi için otomatik açılır; sayfadaki ad ve
kurs adı sertifikadakilerle karşılaştırılır (`page_name`/`page_match`,
`extracted_course_name`/`page_course_name`/`course_match`). Udemy sayfası bot
korumasının arkasında olduğundan otomatik açılmaz — bu alanlar `null` kalır
("bilinmiyor", "eşleşmiyor" değil) ve koordinatör linki elle kontrol eder.
**Kasıtlı yetkilendirme istisnası:** `scoped_evidence()`'ın
"sadece sahibi görür" kuralına (final-analiz §21.2) dar bir istisna —
`CertificateCheck` özeti (ham dosya DEĞİL) ilgili engagement'ın
koordinatörüne/supervisor'una da açılır, çünkü özelliğin denetim değeri
ancak böyle anlamlıdır. Nihai `CONFIRMED`/`REJECTED` kararını yalnız
koordinatör/supervisor verir.

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
> [PLAN.md](PLAN.md) 2.8 yazılırken kesinleşmeli.

**`/revoke` yan etkisi:** Tanıklık geri çekilince ilgili `skill_signals`
kayıtları `superseded` olur — **silinmez** (D12). Tek transaction.

**`/dispute` MVP kapsamı:** `DISPUTED` akışı [PLAN.md](PLAN.md) R.3 —
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
Kontrol router seviyesindedir (`require_platform_admin`): `/admin` altına eklenen
her uç onu kendiliğinden alır; admin olmayan `404` görür
(`tests/authorization/test_admin_router_gate.py` rota tablosundan üretilir).

**Giriş:** Admin için ayrı bir backend ucu yoktur; `POST /auth/login` kullanılır
ve yanıttaki `role` alanı `PLATFORM_ADMIN` döner. Arayüzde ayrı giriş sayfası
`/admin/giris`'tir: admin olmayan hesap girerse oturum hemen kapatılır ve genel
"e-posta veya şifre hatalı" mesajı gösterilir. Bu bir kullanıcı deneyimi ayrımıdır,
güvenlik sınırı değildir — sınır yukarıdaki sunucu kontrolüdür.

| Metot | Yol | İstek | Cevap | Hatalar |
|---|---|---|---|---|
| `GET` | `/admin/verification-queue` | `limit?`, `offset?` | `200` — bekleyen kurum doğrulamaları | — |
| `POST` | `/admin/organizations/{id}/verification-level` | `verification_level`, `note?` | `200` — `verified_at` yalnız seviye yükselince güncellenir | `404`, `422` |
| `POST` | `/admin/organizations/{id}/verification-reject` | `note?` | `200` — kurum kuyruktan çıkar, seviye değişmez | `404`, `409 NOT_PENDING` |
| `GET` | `/admin/fraud-queue` | `limit?`, `offset?` | `200` — PENDING fraud flag'leri (AI işareti, karar yok) | — |
| `POST` | `/admin/fraud-queue/{id}/resolve` | `outcome` (`CONFIRMED`/`DISMISSED`) | `200` — admin kararı kalıcı kaydedilir | `404`, `409 NOT_PENDING` |
| `GET` | `/admin/fraud-flags/history` | `status?` (`CONFIRMED`/`DISMISSED`), `limit?`, `offset?` | `200` — incelenmiş işaretler, `reviewed_at` ve `reviewed_by_user_id` ile; son incelenen önce | `422` |
| `GET` | `/admin/audit-events` | `action?`, `subject_type?`, `actor_user_id?`, `limit?`, `offset?` | `200` — salt okunur denetim kaydı, yeniden eskiye; aktör yalnız kimlik (e-posta yok), `metadata` izinli anahtarlarla sınırlı | `422` |
| `GET` | `/admin/skills` | `limit?` (≤200), `offset?` | `200` — durumdan bağımsız tüm skill'ler | `422` |
| `POST` | `/admin/skills` | `slug`, `name_tr`, `name_en?`, `category`, `parent_id?` | `201` — yeni skill | `409 CONFLICT` (slug), `422` |
| `PATCH` | `/admin/skills/{id}` | `name_tr?`, `name_en?`, `category?`, `parent_id?`, `status?` (`ACTIVE`/`DEPRECATED`) | `200` | `404`, `409 CONFLICT` (geçersiz durum geçişi), `422` |
| `POST` | `/admin/skills/{id}/deprecate` | — | `200` — `DEPRECATED` | `404` |
| `POST` | `/admin/skills/{id}/merge` | `merged_into_id` | `200` — `MERGED`, `merged_into_id` dolu | `404`, `422` |
| `GET` | `/admin/users` | `q?` (e-posta içinde, loglanmaz), `status?`, `limit?` (≤200), `offset?` | `200` — `{items:[{id,email,status,is_platform_admin,email_verified,created_at}],limit,offset,has_more}`; şifre/token/sayaç alanı yok | `422` |
| `POST` | `/admin/users/{id}/suspend` | — (body yok sayılır) | `200` — `SUSPENDED`; refresh token'lar iptal; zaten askıdaysa değişmez, audit yok | `404` (yok/`DELETED`), `409 LAST_ADMIN_PROTECTED` (kendi hesabı / son aktif admin) |
| `POST` | `/admin/users/{id}/reactivate` | — | `200` — `ACTIVE`; askıda değilse değişmez | `404` |
| `GET` | `/admin/organizations` | `q?` (ad/alan adı/legal_id), `verification_level?`, `status?` (`ACTIVE`/`SUSPENDED`), `limit?`, `offset?` | `200` — aynı zarf; silinmiş kuruluş yok | `422` |
| `POST` | `/admin/organizations/{id}/suspend` · `/reactivate` | — | `200` — idempotent | `404` |
| `GET` | `/admin/institutions` | `q?` (ad/alan adı), `limit?`, `offset?` | `200` — aynı zarf | `422` |
| `POST` | `/admin/institutions/{id}/verification-level` | `verification_level` (`T1`–`T4`), `note?` (saklanmaz, yalnız uzunluk audit'e) | `200` — aynı seviyede değişiklik/audit yok | `404`, `422` |
| `POST` | `/admin/institutions/{id}/suspend` · `/reactivate` | — | `200` — idempotent | `404` |

- Admin uçları **offset sayfalama** kullanabilir (§1.6).
- **Liste zarfı:** liste uçları `{"items":[…], "limit":50, "offset":0, "has_more":false}` döner;
  `has_more` `limit+1` kayıt çekilerek kesin hesaplanır, fazladan kayıt yanıta girmez.
  `limit` 1–200, `offset` ≥ 0; aralık dışı değer `422` (sessiz kırpma yok). Geçerli
  zarf uçları: `verification-queue`, `fraud-queue`, `skills`, `audit-events`, `fraud-flags/history`.
- **Kuruluş doğrulama bildirimi:** seviye yükseltildiğinde veya başvuru reddedildiğinde aynı
  transaction'da `organization.verification_decided` outbox olayı yazılır (yalnız kimlikler ve
  karar); worker kuruluşun aktif `ADMIN` üyelerine e-posta gönderir.
- Her doğrulama seviyesi değişikliği `audit_events` üretir.
- Bu uçlar T3 verilmesi içindir; T1/T2 otomatik, T4 koordinatör onayıyla gelir.
- **Fraud-queue (PLAN 3.54, faz 1):** AI (`attestation.fraud_check_requested`
  outbox handler'ı, OpenRouter) tanıklık metnini (`attestation.statement`)
  tarar ve şüpheliyse `fraud_flags` tablosuna `PENDING` bir satır ekler — AI
  hiçbir zaman `attestations`'a yazmaz ve hiçbir hesabı etkilemez. Nihai karar
  (`CONFIRMED`/`DISMISSED`) yalnızca admin'e aittir (final-analiz §11.4.6).
  `OPENROUTER_API_KEY` boşsa handler sessizce no-op'tur (AI opsiyonel altyapı).
- **Fraud-queue (PLAN 3.56) — kuruluş, kurum ve danışıklı tanıklık:** kuyruk
  öğesinde `subject_type` artık `ATTESTATION` / `ORGANIZATION` / `INSTITUTION`
  olabilir; `signal` işareti üreten kuralın kodu (3.54 işaretlerinde `null`),
  `subject_label` kuruluş/kurum adıdır (tanıklıkta `null`). `model = rules-v1`
  olan işaretler sabit eşikli kurallardan gelir (AI yok, anahtar gerekmez):

  | Özne | `signal` | Tetikleyen olay |
  |---|---|---|
  | Tanıklık | `SELF_ATTESTATION`, `SHARED_EMAIL_DOMAIN`, `DUPLICATE_STATEMENT`, `RAPID_VERIFICATION` | her yeni tanıklık |
  | Kuruluş | `UNVERIFIED_HIGH_VOLUME`, `NEW_ORG_BURST`, `SINGLE_TALENT_ONLY` | her yeni tanıklık |
  | Kurum | `APPROVER_IS_ORG_MEMBER`, `RAPID_BULK_APPROVAL` | koordinatör onayı (T2) |
  | Kuruluş | `AI_ORG_IDENTITY` (AI) | kuruluş oluşturma |

  `AI_ORG_IDENTITY` tek AI çağrısıdır ve yalnız kuruluş düzeyinde veri gönderir
  (ad, alan adı, doğrulama seviyesi, vergi no **verilip verilmediği**) — kişi
  adı, e-posta ve tanıklık metni gitmez. Aynı (özne, sinyal) kuyrukta beklerken
  veya son 30 günde üretilmişse yeniden satır açılmaz. Kural gerekçeleri yalnız
  sayı içerir; ad/e-posta/metin içermez.

> **Karar (güncel):** Admin skill yönetimi yukarıdaki beş uçla yapılır
> (`GET/POST /admin/skills`, `PATCH /admin/skills/{id}`, `…/deprecate`, `…/merge`).
> ❓ AÇIK SORU: kullanıcının skill **önerme** ucu ve buna bağlı admin onay ucu
> hâlâ yok; MVP'de skill'ler admin tarafından veya seed'den gelir.

---

### 2.11 Keşfet — `/discover`

Dizin ve arama; **eşleştirme değil** (puan, öneri, uygunluk sıralaması yok).
Tasarım ve mahremiyet gerekçesi → [kesfet-tasarim.md](kesfet-tasarim.md).

| Metot | Yol | Yetki | İstek (sorgu) | Cevap | Hatalar |
|---|---|---|---|---|---|
| `GET` | `/discover/talents` | `AUTH` (e-posta doğrulanmış) | `q?` (2–64), `skill_id?` (çoklu, maks. 5, hepsi eşleşmeli), `institution_id?`, `department?`, `city?`, `limit?` (20, maks. 50), `cursor?` | `200` — `{items, next_cursor, has_more}` | `401`, `422 VALIDATION_ERROR`, `429 RATE_LIMITED` |
| `GET` | `/discover/organizations` | `AUTH` (e-posta doğrulanmış) | `q?` (2–64), `limit?`, `cursor?` | `200` — `{items, next_cursor, has_more}` | `401`, `422 VALIDATION_ERROR`, `429 RATE_LIMITED` |

**Öğrenci kartı:** `public_slug`, `full_name`, `headline`, `department`, `city`,
`institution_name`, `sealed_skills[]` (ad), `verified_experience_count`.
Yalnız `visibility = 'PUBLIC'` **ve** `public_slug` dolu profiller listelenir —
yani zaten anonim `/public/talents/{slug}` ile okunabilenler. `sealed_skills`
ve sayaç yalnız `PUBLIC` doğrulanmış deneyimlerden türetilir; iptal edilmiş
tanıklık sayılmaz. E-posta, iç kimlikler ve beyan edilmiş (doğrulanmamış)
yetkinlikler **dönmez**.

**Kuruluş kartı:** `id`, `name`, `verification_level`, `domain` (yalnız T2+ ise;
aksi halde `null`). Yalnız `status = 'ACTIVE'` ve silinmemiş kuruluşlar.

- Sıralama sabittir: öğrenciler `created_at DESC, id DESC`, kuruluşlar `name, id`.
- Var olmayan `skill_id` / `institution_id` → `200` + boş liste (`404` değil).
- Bilinmeyen sorgu parametresi (`visibility`, `organization_id`, `role` …) → `422`.
- Hız sınırı iki uç için ortak: **60/dk/kullanıcı**; aşımda `Retry-After` başlığı.
- `DISCOVER_ENABLED=false` iken iki uç da (kimlik doğrulamadan önce) `404` döner.

### 2.12 Şikayet — `/complaints`, `/admin/complaints`

Onay bekleyen bir engagement (`PENDING_APPROVAL`/`PENDING_EVALUATION`) veya sertifika kontrolü
(`decision=PENDING`) `COMPLAINT_MIN_WAIT_DAYS` (7) gün yanıtsız kalırsa öğrenci admine şikayet eder.
Hedef kurum/kuruluş ve yetkili sunucuda özneden türetilir. Liste zarfı: `{items, limit, offset, has_more}`
(`limit` 1–200, varsayılan 50; `has_more` limit+1 ile).

| Metot | Yol | Yetki | İstek | Cevap | Hatalar |
|---|---|---|---|---|---|
| `POST` | `/complaints` | `TALENT` (özne kendisinin) | `{subject_type: ENGAGEMENT\|CERTIFICATE_CHECK, subject_id, description (10–4000)}`; başka alan → 422 | `201` `{id, status:"OPEN", status_label:"IN_PROGRESS", subject_type, subject_id, created_at}` | `404`, `409 TOO_EARLY\|ALREADY_OPEN\|NOT_PENDING`, `422`, `429 RATE_LIMITED` (24 saatte 3) |
| `GET` | `/complaints` | `AUTH` (yalnız kendi şikayetleri) | `limit?`, `offset?` | `200` zarf; öğe `{id, viewer_role:"OWNER", subject_type, subject_id, status_label, description, resolution_reason, created_at, closed_at, attachments[]}` | `401` |
| `GET` | `/complaints/assigned` | `AUTH` (yetkili / yükseltilmiş üye) | `limit?`, `offset?` | `200` zarf; öğe = yetkili görünümü | `401` |
| `GET` | `/complaints/{id}` | sahip → `OWNER` görünümü; yetkili (gerekçe istendikten sonra) veya yükseltme sonrası kurum COORDINATOR/ADMIN · kuruluş ADMIN → `RESPONDENT` görünümü `{id, viewer_role, subject_type, subject_id, status, request_note, explanation_due_at, explanation_text, created_at}` | — | `200` | `401`, `404` |
| `POST` | `/complaints/{id}/explanation` | yalnız türetilmiş yetkili, `EXPLANATION_REQUESTED` iken, bir kez | `{text (1–2000)}` | `200` yetkili görünümü (`EXPLANATION_SUBMITTED`) | `404`, `409 INVALID_TRANSITION`, `422` |
| `POST` | `/complaints/{id}/attachments/upload-url` | sahip, şikayet açıkken | `{filename, content_type: pdf\|jpeg\|png, size_bytes ≤10 MB}` | `200` `{upload_url, upload_fields, object_key, expires_in}` | `404`, `409 COMPLAINT_CLOSED`, `422 UNSUPPORTED_CONTENT_TYPE\|FILE_TOO_LARGE`, `429`, `503` |
| `POST` | `/complaints/{id}/attachments` | sahip; şikayet başına ≤5 | `{storage_key, mime_type, size_bytes}` | `201` `{id, mime_type, size_bytes, created_at}` | `404`, `409 ATTACHMENT_LIMIT_REACHED\|COMPLAINT_CLOSED`, `422 INVALID_FILE_CONTENT\|UPLOAD_NOT_FOUND\|INVALID_STORAGE_KEY`, `503` |
| `GET` | `/complaints/{id}/attachments/{attachment_id}` | yalnız sahip (yetkili → 404) | — | `200` `{download_url, expires_in:300}` (audit) | `404`, `409 ATTACHMENT_CONTENT_CHANGED`, `503` |
| `GET` | `/admin/complaints` | `ADMIN` | `status?` (yoksa açık kuyruk), `limit?`, `offset?` | `200` zarf; öğe `{id, status, subject_type, subject_id, subject_pending, target_type, target_id, target_name, attachment_count, explanation_due_at, created_at}` | `401`, `404`, `422` |
| `GET` | `/admin/complaints/{id}` | `ADMIN` | — | `200` öğe + `{talent_id, talent_name, description, respondent_user_id, request_note, explanation_text, resolution_reason, version, closed_at, attachments[], events[]}` | `404` |
| `GET` | `/admin/complaints/{id}/attachments/{attachment_id}` | `ADMIN` (her indirme audit) | — | `200` `{download_url, expires_in}` | `404`, `409`, `503` |
| `POST` | `/admin/complaints/{id}/transitions` | `ADMIN` | `{action, note?, reason?, version?}` | `200` admin detayı | `404`, `409 INVALID_TRANSITION\|VERSION_CONFLICT\|NO_RESPONDENT\|DEADLINE_NOT_REACHED`, `422` |

Eylemler: `START_REVIEW` (OPEN→UNDER_REVIEW) · `DISMISS` (`reason` zorunlu; OPEN/UNDER_REVIEW→DISMISSED) ·
`REQUEST_EXPLANATION` (`note` zorunlu; OPEN/UNDER_REVIEW→EXPLANATION_REQUESTED, süre `COMPLAINT_EXPLANATION_DAYS`=5) ·
`ACCEPT_EXPLANATION` (EXPLANATION_SUBMITTED→RESOLVED) · `REJECT_EXPLANATION` (EXPLANATION_SUBMITTED→ESCALATED;
EXPLANATION_REQUESTED'dan yalnız süre dolduysa) · `RESOLVE` (ESCALATED→RESOLVED; diğer açık durumlardan yalnız
`subject_pending=false` ise) · `UPHOLD` (ESCALATED→UPHELD). Terminal: DISMISSED/RESOLVED/UPHELD (DB trigger ile geri
alınamaz). Öğrenci iç durumu görmez: `status_label` = `IN_PROGRESS` veya sonuç.
Bildirimler outbox ile: `complaint.explanation_requested` (yetkili), `complaint.escalated` (diğer karar verici üyeler),
`complaint.closed` (öğrenci); e-postada yalnız panel bağlantısı vardır.

**Sayaç (`upheld_complaint_count`):** yalnız admin'in `UPHOLD` kararlarının sayısı (algoritma yok; 0 ise 0).
`/discover/organizations` kartı, `GET /organizations` dizini, `GET /organizations/{id}` ve
`GET /institutions/{id}/dashboard` yanıtlarında döner; metin, öğrenci veya yetkili bilgisi taşımaz.

## 3. Uç özeti

Toplam **41 uç**. Hackathon fazlarına dağılımı → [PLAN.md](PLAN.md).

| Grup | Uç sayısı | Faz |
|---|---|---|
| `/auth` | 7 | 1 |
| `/me`, `/talents` | 7 | 1 |
| `/skills` | 1 | 1 |
| `/organizations` | 4 | 1 |
| `/institutions` | 3 | 3 |
| `/engagements` | 7 | 2 |
| `/evidence` | 3 | 2 |
| Değerlendirme / tanıklık / itiraz | 4 | 2 |
| `/public` | 2 | 3 |
| `/discover` | 2 | 3 (R.1) |
| `/admin` | 2 | 3 |

**Definition of Done hatırlatması:** Yeni uç = **aynı commit'te yetkilendirme
testi**. Testsiz uç commit edilmez (CLAUDE.md). Her ucun test satırı →
[AUTHORIZATION.md](AUTHORIZATION.md).
