# Plan — public-profil-endpoint
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/authorization.py` | Yeni `scoped_public_talent_profile()` fonksiyonu eklenecek — mevcut `scoped_talent_profiles()` yalnız kendi profiline izin veriyor, public erişim için ayrı, açık şekilde `visibility` filtreli bir fonksiyon gerekir (çıplak `select()` yasağına uymak için) | medium |
| `backend/app/api/deps.py` | Bu uç kimlik doğrulaması gerektirmiyor (auth-free) — `get_current_principal`'a `Depends` **verilmeyecek**, mevcut dosyada değişiklik gerekmeyebilir ama doğrulanmalı | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/services/visibility_service.py` | Visibility kuralı hesaplama (YET-121) — hangi talent/verified_experience/attestation/skill_signal public görünür |
| `backend/app/api/public.py` | GET public-profile ucu (YET-122) — router, auth-free |
| `backend/tests/test_public_profile.py` | AC-1, AC-2, AC-6, AC-7 |
| `backend/tests/authorization/test_public_profile_authz.py` | AC-3/AC-4/AC-5 (AC-S1/S2/S3), enumeration + PII sızıntısı testleri |

## Dependencies
- `app.services.authorization.get_scoped_or_404` — mevcut helper aynen kullanılabilir (scoped query + None dönüşü, route'ta 404'e çevrilir).
- `app.models.TalentProfile`, `VerifiedExperience`, `Attestation`, `SkillSignal` — mevcut modeller, değişiklik gerekmiyor.
- `app.api.me.TalentProfileResponse` gibi ayrı Pydantic response modelleri — ORM asla doğrudan dönülmüyor (proje kuralı), `public.py` kendi response şemalarını tanımlayacak (PII alanları — `email` zaten TalentProfile'da yok, ama `institution_id` gibi dahili alanlar public response'a **sızmamalı**).

## Migration Required?
Hayır — `talent_profiles.visibility` ve `verified_experiences.visibility` alanları zaten var (migration'da mevcut). Yeni kolon/tablo gerekmiyor.

## Risks
- (atdd.md'den taşındı) Rate limit/anti-scraping yok — kabul edilen risk, MVP kapsamı.
- (atdd.md'den taşındı) Timing side-channel — tek sorgu ile visibility kontrolü yapılmalı, implementasyon notu.
- **(yeni)** `get_current_principal` bu uçta **kullanılmamalı** — anonim erişim gerektiği için mevcut auth zincirinden tamamen bağımsız bir route olmalı. Yanlışlıkla `Depends(get_current_principal)` eklenirse endpoint kimlik doğrulaması zorunlu hale gelir ve AC-1/AC-2/AC-3 kırılır.

## Open Questions

Kod keşfi sırasında atdd.md'nin varsaydığından **farklı** bir şema bulundu — aşağıdaki 3 soru netleşmeden `test-copilot`/`code-copilot` yanlış sözleşme üzerine inşa eder:

1. **Visibility 4 değerli, ikili değil.** `talent_profiles.visibility` ve `verified_experiences.visibility` gerçek şemada `PRIVATE | INSTITUTION | ORGANIZATIONS | PUBLIC` (4 seviyeli enum) — atdd.md'nin varsaydığı `public`/`private` ikilisi yanlıştı. Bu public-profil ucu **sadece** `visibility == 'PUBLIC'` olanları mı gösterecek (INSTITUTION/ORGANIZATIONS seviyesindekiler görünmez), yoksa bu uç yalnızca "genel internet" katmanı olup INSTITUTION/ORGANIZATIONS seviyesi **ayrı, kimlik doğrulamalı** bir uca mı ait (örn. koordinatör/kurum dashboard'u — 3.3/3.5)?
   - Öneri: Bu uç auth-free olduğu için sadece `PUBLIC` gösterebilir; INSTITUTION/ORGANIZATIONS zaten ayrı görevlerde (3.3 koordinatör, 3.5 kurum dashboard) ele alınıyor. Ama bu bir varsayım, onay gerekiyor.

2. **`public_slug` alanı var — route UUID mi, slug mı olmalı?** `TalentProfile.public_slug` (unique, nullable) alanı zaten şemada mevcut. Frontend planı (YET-112, PLAN 3.8) `/p/[slug]` rotası kullanıyor. atdd.md ise `GET /talents/{id}/public-profile` (raw UUID) varsaydı. UUID ile public rota açmak (internal ID'yi dışarı sızdırmak) proje pratiğine aykırı olabilir — slug tabanlı olması daha tutarlı (`GET /public/talents/{slug}` gibi).
   - Bu, AC-1/AC-2/AC-3'ün path parametresini ve "malformed input" (AC-6) tanımını değiştirir (UUID validasyonu yerine slug-not-found / slug-null durumu).

3. **`attestations` ve `skill_signals` kendi visibility alanına sahip değil.** Model incelemesinde `SkillSignal` ve `Attestation`'da bir `visibility` kolonu **yok** — sadece `VerifiedExperience.visibility` var. Public response'ta hangi attestation/skill_signal'lerin gösterileceği belirsiz: (a) sadece `visibility=PUBLIC` olan `VerifiedExperience`'lara **bağlı** olanlar mı (ama attestation/skill_signal ile verified_experience arasında doğrudan FK yok — ikisi de `engagement_id` üzerinden kardeş), (b) talent PUBLIC ise TÜM attestation/skill_signal'ler mi gösterilir, (c) bu MVP'de hiç gösterilmez, sadece `verified_experiences` listelenir mi?
   - Öneri: MVP kapsamında sadece `verified_experiences` (visibility=PUBLIC filtreli) gösterilsin; attestation/skill_signal public response'tan çıkarılsın (Kapsam Dışı'na eklenir). Bu, atdd.md'nin Davranış Sözleşmesi tablosunu (AC-1) küçültür.

**Proje ortamı kısıtı:** Doğrulandı — repo kökü proje klasörüyle aynı (`git rev-parse --show-toplevel` = `yetkin360`), sınırsız arama riski yok.

## Kararlar (kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı)

1. **Sadece `visibility == 'PUBLIC'` gösterilecek.** INSTITUTION/ORGANIZATIONS seviyesi ayrı, kimlik doğrulamalı uçlarda (3.3 koordinatör, 3.5 kurum dashboard) ele alınacak — karıştırmak yetki sızıntısına yol açar.
2. **Route slug tabanlı: `GET /public/talents/{slug}`.** `public_slug` alanı zaten şemada var, frontend planı (`/p/[slug]`) bunu bekliyor, internal UUID'yi dışa sızdırmamak proje pratiğine daha uygun. atdd.md'nin `GET /talents/{id}/public-profile` (UUID) varsayımı **yanlıştı, düzeltildi**.
3. **Response'ta sadece `verified_experiences` (visibility=PUBLIC filtreli).** `attestations`/`skill_signals` kendi visibility alanına sahip değil ve verified_experience'a doğrudan FK'leri yok (ikisi de engagement_id üzerinden kardeş) — güvenli/tutarlı bir gösterim kuralı türetilemiyor, MVP'de kapsam dışı bırakıldı.

Bu kararlar atdd.md'ye (AC'ler, Davranış Sözleşmesi, Kapsam Dışı) yansıtıldı.
