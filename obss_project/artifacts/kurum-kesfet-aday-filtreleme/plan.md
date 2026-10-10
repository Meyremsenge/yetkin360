# Plan — kurum-kesfet-aday-filtreleme

> **GEÇERSİZ (10 Ekim 2026):** Kapsam değişti — yalnız `PUBLIC` profiller, oturum açmış herkes, kimlikli detay ucu yok. Güncel tasarım: `docs/kesfet-tasarim.md`.

_Reference: atdd.md_

Git kökü proje klasörüyle aynı (`/Users/elifsarahan/Desktop/yetkin360`) — arama kapsamı sorunu yok.
Frontend'de `src/` yok; kök `frontend/app`, `frontend/lib`, `frontend/components`, `frontend/messages`.

## Keşifte atdd.md'yi düzelten bulgular

| atdd.md varsayımı | Kodda görülen | Sonuç |
|---|---|---|
| Unknown #1: "doğrulanmış" hangi seviye? | `organizations.verification_level IN ('T1'..'T4')`, varsayılan `T1`; `api/public.py` "verified (T2+)" diyor | Doğrulanmış = `T2+` ve `status='ACTIVE'`, `deleted_at IS NULL` |
| Unknown #2: hız sınırlayıcı var mı? | `services/rate_limit.py` — PostgreSQL tabanlı, `Rule(bucket, limit, window)`; `bucket` serbest `Text` | Var. Yeni `Rule` eklemek yeter, migration gerekmez |
| Unknown #4: görünürlük ayarı arayüzü var mı? | `frontend/app/profil/profile-form.tsx:163` — `visibility` seçimi mevcut | AC-10 yalnız yardım metni eklemektir |
| Unknown #5: feature flag altyapısı | Ayrı altyapı yok; `core/config.py:56` `rate_limit_enabled: bool` deseni var | Aynı desenle `discover_enabled` ayarı |
| AC-7: "mevcut `ORG_TO_TALENT` davet akışı" | `ORG_TO_TALENT` **değerlendirme yönüdür**, davet değil. `POST /engagements` org üyesine açık ama iç `talent_id` (UUID) ister; frontend `calismalar/olustur` yalnız öğrenci tarafını destekler | Kurum tarafı davet arayüzü **yok** — Open Question 1 |
| "public talent id" kartta | `talent_profiles.public_slug` nullable; `ORGANIZATIONS` görünürlüklü öğrencinin slug'ı olmayabilir | Detay ucu için kimlik seçimi — Open Question 2 |
| Görünen ad alanı | `full_name` (ayrı `display_name` yok); ek alanlar `headline`, `department`, `study_year`, `city` | Kart alanları bunlardan seçilir |

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/services/authorization.py` | Yeni `scoped_discoverable_talent_profiles()` (görünürlük `ORGANIZATIONS`/`PUBLIC`, `deleted_at IS NULL`) ve doğrulanmış-org üyeliği kontrolü — AC-1, AC-2, AC-S1, AC-S7 | **high** (yetkilendirme; açık onay + `pytest tests/authorization -q` tamamı) |
| `backend/app/services/rate_limit.py` | `DISCOVER_USER = Rule("discover_user", 30, 60)` + `_RULES`'a ekleme — AC-S6 | low |
| `backend/app/core/config.py` | `discover_enabled: bool` ayarı — Rollback | low |
| `backend/app/main.py` | `discover_router` kaydı | low |
| `.env.example` | `DISCOVER_ENABLED` placeholder (dosya bu oturumda okunamadı — izin reddedildi; elle eklenecek) | low |
| `docs/AUTHORIZATION.md` | §4 matrisi: "Org üyesi (ilgisiz)" hücresi → "R (doğrulanmış org + `visibility` ORGANIZATIONS/PUBLIC, yalnız keşfet alanları)"; uç tablosuna iki satır | medium |
| `docs/API.md` | İki yeni uç | low |
| `PLAN.md` | R.1 durumu | low |
| `frontend/components/app-shell.tsx` | Kuruluş bölümüne "Keşfet" menü girişi (`:298` civarı) — AC-8 | medium (kabuk; tüm sayfaları etkiler) |
| `frontend/messages/tr.json` | Yeni `kesfet` anahtar grubu + `profil.visibility` yardım metni — AC-10 | low |
| `frontend/app/profil/profile-form.tsx` | Görünürlük seçiminin altına bilgilendirme metni — AC-10 | low |
| `backend/scripts/seed.py` | (İsteğe bağlı) birkaç demo öğrencisini `ORGANIZATIONS` yapmak — boş vitrin riski | low |

## New Files

| File | Purpose |
|------|---------|
| `backend/app/api/discover.py` | `GET /discover/talents`, `GET /discover/talents/{id}`; Pydantic allowlist yanıt şemaları (`extra=forbid` sorgu modeli) — iş mantığı yok |
| `backend/app/services/discover.py` | Filtre (çoklu `skill_id` = hepsi, `institution_id`, `verified_only`), cursor sayfalama (20 / maks 50 / derinlik 200), toplu skill ve deneyim sayısı yükleme (≤ 3 sorgu), audit kaydı |
| `backend/tests/authorization/test_discover_authz.py` | Rol × görünürlük matrisi: AC-2, AC-S1, AC-S2, AC-S3, AC-S4, AC-S7 |
| `backend/tests/test_discover.py` | Filtre, sıralama, sayfalama, boş sonuç, 422, sorgu sayısı, hız sınırı, audit — AC-1, AC-3..AC-6, AC-S5, AC-S6, AC-S8, AC-9 |
| `frontend/lib/api/discover.ts` (+ `.test.ts`) | İstemci fonksiyonları; backend hazır olana kadar mock katmanı (versiyonlu, rastgele sonuç yok) |
| `frontend/app/kesfet/page.tsx` (+ `.test.tsx`) | Filtre + kart listesi + boş/hata durumları — AC-1, AC-5, AC-6, AC-9 |
| `frontend/app/kesfet/[id]/page.tsx` (+ `.test.tsx`) | Keşfet-görünümlü profil detayı — AC-7, AC-S3 |

**Rendered web UI dosyaları var** (`.tsx`, `app-shell.tsx`) → `verify` adımında gate 11 (`vision-test`) aktif çalışır.

## Dependencies

- `app.api.deps.get_verified_principal` / `get_current_principal` — `Principal.org_ids` oturumdan gelir; doğrulanmış-org kontrolü bunun üstüne `Organization` sorgusuyla yapılır (istemci `organization_id` almaz).
- `app.services.authorization.get_scoped_or_404` + `app.core.errors.ApiError` — 404 zarfı `scoped_public_talent_profile` ile aynı desen (tek birleşik `WHERE`, zamanlama yan kanalı yok).
- `app.services.rate_limit.enforce` — mevcut imza; sayaç ayrı commit edilir.
- `app.services.audit.log_audit_event` — PII koruması var; metadata'ya yalnız filtre türleri yazılır.
- `SkillSignal` (`strength`, `superseded_by_id`) + `Skill` — doğrulanmış / self-claim ayrımı; `scoped_public_verified_experiences` deseni deneyim sayısı için.
- Frontend: `components/skill-picker.tsx` (skill filtresi için yeniden kullanılır), `lib/api/client.ts` hata zarfı, `lib/session/use-session.ts` (menü görünürlüğü).

## Migration Required?

**Hayır.** `visibility`, `verification_level`, `skill_signals` mevcut; `auth_rate_limits.bucket` serbest metin. Yeni tablo/sütun/indeks yok. (1000+ öğrencide `visibility` kısmi indeksi gerekebilir — şimdi eklenmiyor.)

## Risks

- **Yetkilendirme çekirdeğine dokunuş** — `authorization.py` her uçta kullanılıyor. Yeni fonksiyon eklenir, mevcut `scoped_talent_profiles` **değiştirilmez**; böylece diğer uçların kapsamı genişlemez.
- **Doğrulanmış-org kontrolü Principal'da yok** — `Principal.org_ids` doğrulama seviyesinden bağımsız tüm üyelikleri içerir. Kontrol her istekte DB'den yapılmalı (AC-S7); `Principal`'a alan eklemek 3+ dosyayı etkiler, kaçınılır.
- **Mock ↔ backend sapması** — @fe yarısı mock ile ilerlerse yanıt şeması bu plandaki alan listesine sabitlenmeli.
- **Takvim** — bugün 10 Ekim 2026, teslim 11 Ekim. Backend yarısı (@be2) + tam yetkilendirme paketi gerekiyor.
- **`.env.example`** bu oturumda okunamadı; `DISCOVER_ENABLED` satırı eklenirken mevcut biçim elle kontrol edilmeli.
- atdd.md'den taşınanlar: boş vitrin (seed), kapsam kayması (skor eklenmez).

## Open Questions

1. **"Davet gönder" (AC-7):** Kurum tarafından engagement başlatan arayüz yok ve backend iç `talent_id` istiyor. (a) AC-7'yi "profil detayını göster"e indir, davet düğmesini kapsam dışı bırak; (b) Keşfet detayına kurum tarafı "çalışma başlat" formu ekle (yeni arayüz + `POST /engagements` org yolu).
2. **Detay ucu kimliği:** `public_slug` nullable. (a) Kimlik doğrulamalı keşfet uçlarında `talent_profiles.id` (UUIDv7) kullan — AC-S2'deki "iç `talent_id` yanıtta yok" maddesi yalnız `user_id` için geçerli olacak şekilde daraltılır; (b) yalnız slug'ı olan öğrencileri listele; (c) yeni opak kimlik sütunu (migration gerekir).
3. **Menü görünürlüğü (AC-8):** `/me` yanıtındaki `organizations` doğrulama seviyesini taşıyor mu bilinmiyor. (a) Keşfet girişini her kuruluş üyesine göster, doğrulanmamışsa sayfa "kuruluşun doğrulanınca açılır" bilgi durumu göstersin (API yine 404); (b) `/me`'ye `verification_level` ekle (backend değişikliği).
4. **Audit (AC-S8):** Arama ve profil görüntüleme `audit_events`'e yazılsın mı? (a) yalnız profil detayı görüntüleme; (b) ikisi de; (c) hiçbiri. "Kim baktı" ekranı kapsam dışı.
5. **Kart alanları:** `full_name`, `department`, `study_year`, `city`, `headline`, üniversite adı, skill'ler, doğrulanmış deneyim sayısı — hepsi mi, alt küme mi?
6. **Seed:** Demo için birkaç öğrenci `ORGANIZATIONS` yapılsın mı (bu işin içinde mi, ayrı commit mi)?

## Kararlar
Tümü *Sonnet alt-ajanı (low) tarafından yanıtlandı* — kullanıcı onayı değildir.

1. **Davet düğmesi kapsam dışı.** AC-7 "profil detayını göster"e indirildi. *Gerekçe: kurum tarafı davet arayüzü yok; yenisini yazmak yetkilendirme yüzeyini büyütür ve takvime sığmaz.*
2. **Detay ucu `talent_profiles.id` (UUIDv7) kullanır:** `GET /discover/talents/{id}`. AC-S2 yalnız `user_id`'yi yasaklayacak şekilde daraltıldı. *Gerekçe: migration gerekmez; slug şartı boş vitrin riskini artırır; UUIDv7 tahmin edilemez ve 404 zarfı varlığı sızdırmaz.*
3. **Menü girişi her kuruluş üyesine görünür;** kuruluş doğrulanmamışsa sayfa "kuruluşun doğrulanınca açılır" bilgi durumunu gösterir, API yine `404` döner. *Gerekçe: `/me`'ye alan eklemek @be2 bağımlılığı; asıl güvenlik sunucuda.*
4. **Yalnız profil detayı görüntüleme audit'e yazılır;** liste araması yazılmaz. *Gerekçe: tek öğrenciye erişimi izler; her aramayı yazmak `audit_events`'i şişirir.*
5. **Kart alanları:** `id`, `full_name`, üniversite adı, `department`, `study_year`, `headline`, skill'ler (doğrulanmış / self-claim), doğrulanmış deneyim sayısı. `city` yalnız detayda. *Gerekçe: veri minimizasyonu.*
6. **Seed bu işin dışında,** ayrı isteğe bağlı commit. *Gerekçe: yetkilendirme commit'i temiz kalır; demo için yine de yapılmalı.*

Bu kararların dosya listesine etkisi: `frontend/app/kesfet/[id]/page.tsx` davet düğmesi içermez; `backend/scripts/seed.py` bu işin "Files to Modify" listesinden çıkar; `services/discover.py` audit kaydını yalnız detay ucunda yazar.
