---
name: Güvenlik kuralları
paths:
  - "**/auth/**"
  - "**/authorization/**"
  - "**/services/*auth*"
  - "**/services/*evidence*"
  - "**/services/*attestation*"
  - "**/api/**/auth*"
  - "**/core/security*"
  - "**/core/deps*"
  - "**/*upload*"
  - "**/*permission*"
---

# Güvenlik-kritik kod

Bu dosyalarda **token tasarrufu için context kısma.** Gerekiyorsa `yetkin360-final-analiz.md` §15 ve §16'yı oku.

## Yetkilendirme (en kritik risk: BOLA)

- Her veri erişimi merkezî `can()` veya `scoped_*()` üzerinden. Çıplak `select(Model)` yasak.
- Kaynak sahipliği **URL'den değil, oturumdan** çıkarılır. İstemciden gelen `org_id`/`talent_id` filtresine güvenilmez.
- Yetkisiz erişimde **404** dön, 403 değil (403 kaynağın varlığını sızdırır).
- Frontend'de butonu gizlemek yetkilendirme değildir — karar her zaman sunucuda **tekrar** verilir.
- Admin her şeyi göremez. `PRIVATE` kanıt admin'e de kapalıdır.

## Her yeni endpoint için zorunlu

Aynı commit'te, yoksa endpoint bitmemiştir:

1. Pozitif test (yetkili aktör erişebiliyor)
2. **Negatif test** (başka kiracı erişemiyor → 404)
3. Response şeması ayrı Pydantic modeli — ORM modeli doğrudan dönülmez

## Kimlik doğrulama

- Şifre: Argon2id
- Token: httpOnly + Secure + SameSite=Lax cookie. `localStorage` yasak
- Refresh token DB'de saklanır (iptal edilebilmesi için), rotasyonlu
- Rate limit: login, kayıt, şifre sıfırlama, dosya yükleme uçlarında

## Dosya yükleme

- Uzantıya güvenme → magic-byte ile MIME tespiti
- Allowlist kullan, blacklist değil
- Dosya adı korunmaz → `{uuid}.{ext}`
- Tarama bitmeden (`scan_status != CLEAN`) indirilemez
- Kullanıcı içeriği **ana domainden servis edilmez**
- İndirme: kısa ömürlü imzalı URL + her indirmede yetki kontrolü + audit

## Sır ve log

- `.env` okunmaz, içeriği çıktıya taşınmaz
- Loglanmaz: şifre, token, CV içeriği, `private_note`, tam e-posta
- Ham SQL yalnız migration dosyalarında

## Doğrulama

Bu dizinlerde değişiklik yaptıysan **yetkilendirme test paketinin tamamını** çalıştır:
`pytest tests/authorization -q`

Bunu atlama. Repo açık kaynak — bir yetkilendirme açığı herkes tarafından okunabilir.
