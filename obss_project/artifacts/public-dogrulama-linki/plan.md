# Plan — public-dogrulama-linki
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/models/verified_experience.py` | `public_token` kolonu eklenecek (nullable, unique, String) | medium |
| `backend/app/api/public.py` | Mevcut router'a `GET /public/v/{token}` ucu eklenecek | low |
| `backend/app/services/authorization.py` | Yeni `scoped_public_verified_experience_by_token()` fonksiyonu — tek WHERE'de `public_token=... AND visibility='PUBLIC'` (timing side-channel'a karşı, YET-105'teki desenin aynısı) | medium |

## New Files
| File | Purpose |
|------|---------|
| `backend/alembic/versions/<yeni>_add_public_token_to_verified_experiences.py` | `verified_experiences.public_token` kolonu — **kullanıcı onayı gerekiyor, aşağıya bakın** |
| `backend/tests/test_public_verification.py` | AC-1, AC-2, AC-6, AC-7 |
| `backend/tests/authorization/test_public_verification_authz.py` | AC-3/AC-4/AC-5 (AC-S1/S2/S4), enumeration testleri |

## Dependencies
- `app.services.authorization.get_scoped_or_404` — mevcut helper aynen kullanılabilir.
- `app.models.VerifiedExperience`, `Engagement`, `Organization`, `Institution` — mevcut modeller.
- `Skill.name_tr` (doğrulandı: `backend/app/models/skill.py`) — `attested_skills[].name_tr` alanı buradan gelecek.
- `Organization.verification_level` (doğrulandı: `T1`-`T4` CHECK constraint) — `organization_trust_level` alanı buradan gelecek, atdd.md'nin varsayımı DOĞRU çıktı.

## Migration Required?
**Evet — kullanıcı onayı gerekiyor (CLAUDE.md kuralı).**
`verified_experiences.public_token` kolonu (nullable, `String`, `UNIQUE` constraint, index) eklenmeli. `docs/DATABASE.md` bu kolonu zaten dokümante etmiş ama gerçek şemada yok. Mevcut migration deseni (`backend/alembic/versions/`) incelendi — proje "önce ekle → sonra kullan" ilkesine uygun tek bir `alembic revision` ile eklenebilir (backward-compatible: nullable kolon, mevcut kayıtlar etkilenmez).

## Risks
- (atdd.md'den taşındı) Rate limit yok — kabul edilen risk.
- (atdd.md'den taşındı) Timing side-channel — tek sorguda visibility+token kontrolü.
- (atdd.md'den taşındı) Migration sonrası mevcut kayıtlarda `public_token` NULL kalacak — backfill bu görevin kapsamı dışı.

## Open Questions

Kod keşfinde atdd.md'nin göremediği **gerçek bir şema boşluğu** bulundu — bu, tahmin edilemeyecek kadar önemli bir üründeki karar:

1. **`attestor_name` için hiçbir kaynak yok.** `docs/API.md §2.9`'un örnek response'unda `attested_skills[].attestor_name: "Mehmet K."` var. Ama gerçek şemada:
   - `User` modelinde (`backend/app/models/identity.py`) **isim alanı YOK** — sadece `email`, `password_hash`, `status` var.
   - `Attestation` modelinde (`backend/app/models/attestation.py`) attestor'un adını snapshot'layan bir alan YOK — sadece `attestor_user_id` (FK) ve `attestor_org_id` (FK) var.
   - `TalentProfile.full_name` var ama bu SADECE talent'lar için — bir attestor (org/institution üyesi) tanıklık ederken kendi `TalentProfile`'ı olmayabilir (aslında CHECK constraint `attestor_user_id != talent_id` bunun ayrı kişiler olduğunu zorluyor, ama attestor'un talent olması mümkün — ama genelde attestor bir işveren/kurum temsilcisi).

   Bu alan olmadan AC-1'in happy-path response'u (`docs/API.md`'nin kendi örneği) **üretilemez**. Üç seçenek:
   - (a) `attestor_org_id` üzerinden `Organization.name`'i kullan, kişi adı yerine kurum adı göster (`attestor_name` yerine `attestor_organization`) — **atdd.md'nin varsaydığı response şeklini değiştirir**.
   - (b) `VerifiedExperience`'a (veya `Attestation`'a) migration ile bir `attestor_name_snapshot` kolonu ekle, T8 attestation sırasında doldur — ama bu alan HANGİ veriden dolacak, çünkü `User`'da da isim yok; muhtemelen `User`'a da bir `display_name`/`full_name` alanı eklenmesi gerekir (ayrı, daha büyük bir migration + PLAN dışı bir değişiklik).
   - (c) `attested_skills`'ten `attestor_name`'i tamamen çıkar, sadece `claim_type` + `skill.name_tr` göster — `docs/API.md`'nin örneğinden sapma, dokümanı da güncellemek gerekir.

2. **`public_token` migration'ı onaylanıyor mu?** Yukarıdaki "Migration Required?" bölümü — nullable/unique/`String` kolon, mevcut kayıtlar NULL kalır. Onaylıyor musunuz?

**Proje ortamı kısıtı:** Doğrulandı — repo kökü proje klasörüyle aynı, sınırsız arama riski yok.

## Kararlar (kullanıcı onayı)

1. **`attestor_name` yerine `attestor_organization` gösterilecek** (`Organization.name`, `attestor_org_id` üzerinden). Migration gerekmiyor, response şekli atdd.md'nin varsaydığından farklı: `attested_skills[].attestor_name` → `attested_skills[].attestor_organization`. `docs/API.md §2.9`'un örneği bu görevin kapsamında güncellenmeyecek (dokümantasyon güncellemesi ayrı bir görev — burada sadece kod/atdd.md düzeltiliyor).
2. **`public_token` migration'ı onaylandı.** `verified_experiences.public_token` (nullable, `String`, `UNIQUE`, index) eklenecek.

Bu kararlar atdd.md'ye (AC-1 response şeması) yansıtıldı.
