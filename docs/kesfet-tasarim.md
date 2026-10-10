# Keşfet — kapsam ve mahremiyet tasarımı (AŞAMA 0)

**Durum: ONAYLANDI (10 Ekim 2026) ve uygulandı.** Onaylanan kararlar §8'de.
İlgili: `PLAN.md` R.1 · `docs/AUTHORIZATION.md` §4 · `docs/SECURITY.md` §3 · `docs/API.md` §1.6
Ön çalışma: `obss_project/artifacts/kurum-kesfet-aday-filtreleme/` (atdd.md, plan.md — bu belge onaylanınca ona göre güncellenecek).

## 1. Ne, ne değil

Keşfet bir **dizin ve arama** ekranıdır: kuruluş ve kurum üyeleri herkese açık öğrenci profillerini, öğrenciler kuruluşları listeler ve filtreler.

Eşleştirme **değildir**. Skor, uygunluk yüzdesi, öneri, "sana uygun" sıralaması, AI, Elasticsearch, pgvector yoktur (CLAUDE.md Kapsam, final analiz §9.1). Sıralama sabittir; iki kullanıcı aynı filtreyle aynı listeyi görür.

## 2. Kim kimi görür

### 2.1 Öğrenci dizini — `GET /discover/talents`

| Çağıran | Sonuç |
|---|---|
| Anonim | `401` |
| E-postası doğrulanmamış | `401 EMAIL_NOT_VERIFIED` |
| Oturum açmış, e-postası doğrulanmış her kullanıcı (öğrenci dahil) | `200` |

Listelenen profil koşulu (tek birleşik `WHERE`):

```
visibility = 'PUBLIC' AND public_slug IS NOT NULL AND deleted_at IS NULL
```

| `visibility` | Keşfet'te | Gerekçe |
|---|---|---|
| `PUBLIC` | Listelenir | Öğrenci profili zaten anonim `/p/{slug}` ile açmış |
| `ORGANIZATIONS` | **Listelenmez** (v1) | Detay sayfası yalnız `/p/{slug}`; bu seviyeye ayrı bir kimlikli detay ucu ve yeni yetki kuralı gerekir |
| `INSTITUTION` (varsayılan) | Listelenmez | Yalnız öğrencinin kendi kurumu görür; mevcut kural değişmez |
| `PRIVATE` | Listelenmez | — |

Kuruluşun doğrulama seviyesi (T1–T4) **aranmaz**: listelenen veri zaten anonim erişime açık, T2 şartı koruma eklemez.

Sonuç: Keşfet hiçbir öğrencinin bugün gizli olan verisini açmaz. Yeni olan tek şey **toplu listelenebilirlik**tir (§5).

### 2.2 Kuruluş dizini — `GET /discover/organizations`

| Çağıran | Sonuç |
|---|---|
| Anonim / e-postası doğrulanmamış | `401` |
| Oturumlu her kullanıcı | `200` |

Koşul: `status = 'ACTIVE' AND deleted_at IS NULL` — mevcut `scoped_organization_directory()` (PLAN 3.53) aynen kullanılır; yeni yetki kuralı açılmaz.

Kurumlar (üniversiteler) v1'de bu uçta **yoktur** — bkz. §8 karar 3.

## 3. Dönen alanlar (allowlist)

### Öğrenci kartı

| Alan | Kaynak | Not |
|---|---|---|
| `public_slug` | `talent_profiles` | Karttaki "Profili gör" → `/p/{slug}` |
| `full_name`, `headline`, `department`, `city` | `talent_profiles` | — |
| `institution_name` | `institutions.name` | Yoksa `null` |
| `sealed_skills[]` (`name_tr`) | Tanıklıkla doğrulanmış yetkinlikler | Yalnız **PUBLIC** doğrulanmış deneyimden gelenler |
| `verified_experience_count` | `verified_experiences` | Yalnız `visibility = 'PUBLIC'` olanlar sayılır |

**Asla dönmez:** e-posta, telefon, `user_id`, `talent_profiles.id`, `study_year`, CV, kanıt dosyası/URL'si, `private_note`, beyan edilmiş ama doğrulanmamış yetkinlikler, PUBLIC olmayan deneyimler.

Doğrulanmamış (self-claim) yetkinlikler kartta **gösterilmez**: bugünkü `/p/{slug}` yanıtı onları içermiyor; Keşfet public profilden fazlasını göstermemeli.

Avatar: modelde görsel alanı yok → kartta ad baş harfleri.

### Kuruluş kartı

| Alan | Not |
|---|---|
| `id`, `name`, `verification_level` | — |
| `domain` | **Yalnız T2+ ise**; aksi halde `null` (doğrulanmamış alan adı saldırganın seçtiği serbest metindir — `api/public.py` GUV-03 kuralı) |

`legal_id`, `status`, üye listesi, doğrulama notları dönmez. Kartta eylem: öğrenci için "Çalışma başlat" → mevcut `/calismalar/olustur?organization_id=…`. Ayrı kuruluş detay sayfası v1'de yok.

## 4. Arama, filtre, sayfalama

| Konu | Karar |
|---|---|
| Arama | PostgreSQL `ILIKE '%q%'`. Trigram **yok**: `pg_trgm` kurulu değil, kurmak migration ister; hackathon ölçeğinde (< 10 000 satır) sıralı tarama yeterli |
| `q` | 2–64 karakter; `%`, `_`, `\` kaçışlanır. Öğrencide `full_name` + `headline`; kuruluşta `name` |
| Öğrenci filtreleri | `skill_id` (çoklu, hepsi eşleşmeli; yalnız mühürlü yetkinlikler), `institution_id`, `department`, `city` (büyük/küçük harf duyarsız eşitlik) |
| Sıralama | Öğrenci: `created_at DESC, id`. Kuruluş: `name, id`. Puan alanı yok |
| Sayfalama | Cursor (`docs/API.md` §1.6): `{items, next_cursor, has_more}`; `limit` varsayılan 20, **maks. 50**; `total` dönmez |
| Bilinmeyen parametre | `422` (`extra=forbid`) — istemciden `visibility`, `organization_id`, `role` kabul edilmez |
| Yeni bağımlılık | Yok |
| Migration | Yok |

## 5. Mahremiyet ve kötüye kullanım

| Risk | Önlem |
|---|---|
| Toplu kazıma (bir üye tüm PUBLIC profilleri döker) | Kullanıcı başına **60/dk** (`SECURITY.md` §3 "Arama" satırı), mevcut `services/rate_limit.py` ile; aşımda `429 RATE_LIMITED`. `limit` maks. 50 |
| Öğrenci listelendiğini bilmiyor | Profil formundaki görünürlük seçiminin altında açık bilgilendirme metni (`profil.visibilityDiscoverHint`) |
| Görünürlük sonradan kapatıldı | Etki anında: sonraki istekte listede yok; `/p/{slug}` zaten `404` |
| Gizli deneyimden yetkinlik sızması | `sealed_skills` ve sayaç yalnız PUBLIC deneyimden türetilir; yetkilendirme testinde ayrı vaka |
| Filtreyle varlık sızdırma | Var olmayan `skill_id` / `institution_id` → `200 + []` (404 değil) |
| LIKE joker enjeksiyonu | `q` kaçışlanır. Not: mevcut `GET /organizations` kaçışlamıyor — ayrı küçük düzeltme önerisi |
| PII loglama | `q` loglanmaz (ad içerebilir) |

Audit: liste aramaları `audit_events`'e yazılmaz — veri zaten herkese açık, kayıt yalnız tabloyu şişirir.

## 6. Davranış sözleşmesi

| Durum | `/discover/talents` | `/discover/organizations` | Arayüz |
|---|---|---|---|
| Başarılı, sonuç var | `200 + items` | `200 + items` | Kart ızgarası |
| Başarılı, sonuç yok | `200 + []` | `200 + []` | Boş durum |
| Geçersiz girdi | `422` | `422` | "Filtre geçersiz" |
| Anonim / e-posta doğrulanmamış | `401` | `401` | Girişe yönlendirme |
| Hız sınırı | `429` + `Retry-After` | `429` + `Retry-After` | "Çok fazla istek" |
| Sunucu hatası / zaman aşımı | `5xx` | `5xx` | Hata durumu + yeniden dene |
| Özellik kapalı (`discover_enabled = false`) | `404` | `404` | Menüde Keşfet yok |

Kısmi başarı yoktur: yetkinlik ya da sayaç toplu yüklemesi hata verirse istek `5xx` olur, eksik kartlı `200` dönmez. Boş liste yalnız yetkili ve başarılı sorguda döner.

## 7. Frontend — `/kesfet`

- Üstte arama kutusu + filtre çipleri; sekmeler **Öğrenciler / Kuruluşlar**, ikisi de oturum açmış herkese görünür.
- Arayüzde yetkinlik, bölüm ve şehir filtreleri var. `institution_id` filtresi API'de mevcut ama arayüzde yok: kurumları listeleyen bir uç bulunmuyor.
- Kart ızgarası: baş harf avatarı, ad, başlık, mühürlü yetkinlik çipleri, doğrulanmış deneyim sayısı, "Profili gör".
- Boş, yükleme (iskelet), hata, hız sınırı durumları ayrı ayrı.
- Animasyon: kart girişinde `y360-step-in`; `prefers-reduced-motion` açıkken kapalı.
- Metinler `frontend/messages/tr.json` içinde.

**Keşifte görülen iki uyumsuzluk:**
1. Bu dalda üst gezinme çubuğu yok; `components/app-shell.tsx` yan gruplu menü kullanıyor ("3. prompt" uygulanmamış görünüyor). Keşfet girişi mevcut menüye eklenir.
2. `y360-step-in` animasyonu `frontend/app/globals.css` içinde tanımlı değil; bu işle birlikte tanımlanması gerekir.

## 8. Onaylanan kararlar (10 Ekim 2026)

1. **Yalnız `PUBLIC` profiller listelenir.** `ORGANIZATIONS` seviyesi v1'de açılmadı.
2. **Öğrenci dizinini oturum açmış herkes görür** (öğrenciler dahil). Anonim erişim yok.
3. **Kurumlar (üniversiteler) dizinde yok** — varsayılan; istenirse `GET /discover/institutions` ayrı iş olarak eklenir.
4. **Kartta yalnız mühürlü yetkinlikler** gösterilir.
5. **Yetkilendirme değişikliği onaylandı:** `services/authorization.py`'ye `scoped_discoverable_talent_profiles()`, `scoped_discoverable_verified_experiences()`, `scoped_discoverable_attestations()` eklendi; mevcut kapsam fonksiyonları değişmedi.
6. Backend ve frontend aynı işte yazıldı.

## 9. Kabul

Her uç için pozitif + negatif yetkilendirme testi aynı commit'te · ilgili testler + `pytest tests/authorization -q` tamamı · frontend `npm run lint && npm run typecheck` + bileşen testleri · ekran görüntüleri (masaüstü + mobil; dolu, boş, hata).
