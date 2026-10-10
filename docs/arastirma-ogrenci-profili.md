# Araştırma — Öğrenci profili: "Hakkımda" ve sertifika/çalışma vitrini

Tarih: 2026-10-10 · Kapsam: `/profil` (sahibi) ve `/p/[slug]` (herkese açık) · İlgili: PLAN 3.55 (`certificate_checks`)

## 1. Kritik ilke

**Kendi beyanı ile doğrulanmış kayıt görsel olarak asla karışmaz.** (final analiz §7.1: Claim ≠ Evidence ≠ Attestation; §7.6: `SELF_UPLOADED` kayıt platform kaydıyla aynı güven seviyesinde gösterilmez.)

| Katman | Örnek | Görsel dil |
|---|---|---|
| Doğrulanmış | Doğrulanmış deneyim, tanıklı yetkinlik | Çam yeşili + mühür (`VerifiedSeal`) |
| Koordinatör onaylı | Çalışma içinde yüklenen, `certificate_checks.decision = CONFIRMED` sertifika | Çam yeşili çerçeve, "Koordinatör onaylı" rozeti, mühür **yok** (mühür = tanıklık) |
| Kendi beyanı | "Hakkımda", çalışma dışı sertifika/çalışma | Nötr kâğıt/kum zemin, kesik çizgi kenar, "Kendi beyanı" etiketi, mühür **yok** |

## 2. İncelenen ürünler ve çıkarılan desenler

| Ürün | Gözlem | Alınan desen | Alınmayan |
|---|---|---|---|
| **LinkedIn** — About | Serbest metin, ~2.600 karakter; ilk ~3-4 satır görünür, kalanı "daha fazla gör" | Kısa önizleme + genişlet; karakter sayacı | Uzun sınır (öğrenci için gereksiz, KVKK yüzeyi büyür) |
| **LinkedIn** — Licenses & certifications | Ad, veren kuruluş, veriliş/bitiş tarihi, Credential ID, Credential URL; sertifika no ve URL isteğe bağlı | Alan seti birebir; "sertifika no" Mono yazı | Bitiş tarihi (MVP'de gereksiz), "skills" bağlama (beyanı yetkinlik sinyaline dönüştürür — yasak) |
| **LinkedIn** — Featured | Öne çıkan bağlantı/medya şeridi, yatay kaydırma | Yatay kaydırmalı şerit (scroll-snap) | Medya önizleme (dosya PRIVATE kalır) |
| **Credly / Accredible** | Rozet sayfası: veren kurum, tarih, "Verify" düğmesi, doğrulama kaynağı belirgin | "Resmi doğrulama ↗" bağlantısı; doğrulamayı **kimin** yaptığı kartta yazar | Rozet koleksiyonu/sayısı (gamification — yasak) |
| **Europass** | Profilde lisans/sertifika kaydı; dosyalar ayrı "Library"de, yalnız sahibine | Kayıt (meta) ile dosya ayrı; dosya asla vitrine çıkmaz | Ayrıntılı CV editörü |
| **Handshake** | Öğrenci profili: kısa tanıtım, bölüm/sınıf, iş deneyimi; işverene görünürlük ayarı | Görünürlük ayarına bağlı gösterim | İş eşleştirme/öneri (matching — yasak) |
| **Read.cv** | Sade tipografi, tek sütun "About" + kronolojik liste (Ocak 2025'te Perplexity'ye satıldı, kapandı) | Sakin tipografi; "Hakkımda" hero'nun hemen altında, düz metin | — |

Polywork da incelendi; hizmetin güncel durumu doğrulanamadı, desen alınmadı.

## 3. MVP alanları

**Gerekli**
- `about` — düz metin, en fazla **1.000 karakter**, satır sonları korunur; Markdown/HTML yok (XSS yüzeyi yok, `dangerouslySetInnerHTML` zaten yasak). Karakter sayacı. Alanın altında KVKK uyarısı: *"Sağlık, din, siyasi görüş gibi özel nitelikli bilgileri yazmayın."* (§17.2 sert kural.)
- Sertifika/çalışma kaydı — tür (Sertifika / Çalışma), başlık, veren kuruluş, tarih (ay-yıl), sertifika no, bağlantı (yalnız `https://`), isteğe bağlı dosya (mevcut güvenli yükleme akışı), "Profilde göster" anahtarı (**varsayılan kapalı**).

**MVP dışı (bilinçli olarak yok)**
- AI ile "Hakkımda" yazdırma / CV'den doldurma (AI — yasak), sertifikadan otomatik yetkinlik çıkarma (beyanı sinyale çevirir), rozet sayısı/ilerleme çubuğu/"profil %80 tamam" (gamification), güven puanı (trust score), işverene öneri (matching), sertifika bitiş tarihi ve hatırlatma, zengin metin editörü.

## 4. Veri modeli önerisi (ONAY BEKLİYOR)

### 4.1 `talent_profiles.about`
`about TEXT NULL`, `CHECK (about IS NULL OR char_length(about) <= 1000)`. Mevcut `PATCH /talents/me` ile güncellenir (yeni uç yok). Public profilde yalnız profil zaten `PUBLIC` iken çıkar.

### 4.2 Yeni tablo `portfolio_items` (önerilen — Seçenek A)

```
portfolio_items
  id              uuid PK (UUIDv7)
  talent_id       uuid NOT NULL → talent_profiles(id)
  kind            text NOT NULL CHECK (kind IN ('CERTIFICATE','WORK'))
  title           text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 120)
  issuer          text NULL     CHECK (≤ 120)
  issued_on       date NULL
  credential_id   text NULL     CHECK (≤ 100)
  external_url    text NULL     CHECK (external_url ~ '^https://' AND ≤ 500)
  evidence_id     uuid NULL UNIQUE → evidence(id)   -- dosya PRIVATE kalır
  show_on_profile boolean NOT NULL DEFAULT false   -- açık rıza
  deleted_at      timestamptz NULL                 -- soft delete
  created_at, updated_at timestamptz
  INDEX (talent_id) WHERE deleted_at IS NULL
```

- **Çalışma dışı kayıt:** öğrenci formu doldurur; dosya eklerse mevcut `POST /evidence/upload-url` → `POST /evidence` akışı (`deliverable_id` olmadan — model bunu zaten destekliyor) kullanılır, `evidence_id` bağlanır. Etiket: **Kendi beyanı**.
- **Çalışma içi onaylı sertifika:** öğrenci profilde "Çalışmalardan gelen sertifikalar" listesinden birini vitrine ekler → `evidence_id` o kanıta bağlı bir satır oluşur. Rozet sunucuda türetilir: kanıtın `certificate_checks.decision = CONFIRMED` ise **Koordinatör onaylı**, değilse **Kendi beyanı**. Öğrenci rozeti seçemez.
- **Neden ayrı tablo:** (1) `evidence` üzerindeki `visibility = 'PRIVATE'` CHECK'i olduğu gibi kalır — dosya hiçbir koşulda public olmaz; (2) beyan meta verisi (başlık, kurum, tarih) yapıttan ayrı durur (§7.1); (3) rıza tek yerde, geri alınabilir; (4) iki kaynak (çalışma içi/dışı) tek vitrin sorgusuyla gelir.

Reddedilen seçenekler:
- **B — `evidence`'a kolon eklemek** (title, issuer, show_on_profile): `PRIVATE` CHECK'ini gevşetmek ya da "görünür ama PRIVATE" çelişkisi gerekir; evidence'ı beyan meta verisiyle kirletir.
- **C — `certificate_checks.show_on_profile` + çalışma dışı için ayrı tablo:** rıza iki yerde, vitrin iki sorgu, iki farklı silme davranışı.

### 4.3 Uçlar (hepsi oturumdan sahiplik; başkasının kaydı → **404**)

| Uç | Ne yapar |
|---|---|
| `PATCH /talents/me` | `about` alanı eklenir |
| `GET /me/portfolio-items` | Kendi kayıtları + her biri için türetilmiş rozet |
| `POST /me/portfolio-items` | Yeni kayıt; `evidence_id` verilirse sahibine ait ve silinmemiş olmalı, yoksa 404 |
| `PATCH /me/portfolio-items/{id}` | Alanlar ve `show_on_profile` |
| `DELETE /me/portfolio-items/{id}` | Soft delete (`deleted_at`); bağlı kanıt dosyası etkilenmez |
| `GET /public/talents/{slug}` | Yanıta `about` ve `certificates[]` eklenir (ayrı Pydantic modeli) |

Yetkilendirme: `authorization.py`'a `scoped_portfolio_items(principal)` (sahibi) ve `scoped_public_portfolio_items(talent_id)` (yalnız `show_on_profile AND deleted_at IS NULL`, profil `PUBLIC`) eklenir. Her uç için pozitif + negatif test `tests/authorization`'a aynı commit'te.

### 4.4 Public'e çıkan / çıkmayan

| Çıkar | Çıkmaz |
|---|---|
| tür, başlık, veren kuruluş, tarih, sertifika no, rozet (`CONFIRMED` / `SELF_DECLARED`), sağlayıcı (Coursera/Udemy) | dosya, `storage_key`, `extracted_name`, `qr_raw_data`, `page_name`, `name_match`, `model`, karar veren kişi, iç id'ler, e-posta |

**Bağlantılar:**
- Onaylı sertifikada `verify_url` yalnız `https` **ve** sağlayıcı alan adı allowlist'indeyse (`coursera.org`, `www.coursera.org`, `udemy.com`, `www.udemy.com`, `ude.my`) "Resmi doğrulama ↗" olur; değilse hiç gösterilmez. Kontrol sunucuda.
- Kendi beyanı kayıtta `external_url` link olur ama **alan adı görünür yazılır** (ör. "credential.net ↗"), `rel="nofollow ugc noopener noreferrer"`; "kurum tarafından doğrulanmadı" ipucu taşır.

## 5. Yerleşim

- `/profil`: sağ sütunda "Hakkımda" kartı (sayaç, KVKK notu, kaydet) ve "Sertifikalar ve çalışmalar" kartı (sürükle-bırak — `app/calismalar/[id]/evidence-upload-form.tsx` deseni; her kayıtta "Profilde göster" anahtarı; çalışmalardan gelen sertifikalar ayrı alt başlık).
- `/p/[slug]`: "Hakkımda" hero'nun altında ana sütunda; "Sertifikalar" şeridi yetkinlik haritası ile zaman çizelgesi arasında (scroll-snap, klavye ok tuşları, masaüstünde ok düğmeleri); onaylılar önce, kendi beyanları ayrı alt başlıkla ve mühürsüz. Sicil kartına yalnız "Koordinatör onaylı sertifika: N" satırı (kendi beyanları sayılmaz).

## Kaynaklar
- LinkedIn sertifika alanları: [Wooster](https://apex.wooster.edu/blog/2023/02/10/how-to-add-a-certificate-on-linkedin/), [Syracuse IVMF](https://ivmf.syracuse.edu/how-to-manually-add-licenses-certification-to-your-linkedin-profile/)
- LinkedIn About sınırı (üçüncü taraf): [Unilink](https://www.unilink.us/blog/linkedin-character-limits-2026), [AuthoredUp](https://authoredup.com/blog/linkedin-character-limit)
- Read.cv: [TechCrunch](https://techcrunch.com/2025/01/17/perplexity-acquires-read-cv-a-social-media-platform-for-professionals/)
- Europass: [Europass digital tools](https://europass.europa.eu/no/europass-verktoy), [Europass FAQ](https://europass.europa.eu/me/faq?page=2)
