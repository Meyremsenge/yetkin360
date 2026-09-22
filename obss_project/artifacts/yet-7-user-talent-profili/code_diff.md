# Code Diff — yet-7-user-talent-profili
_Green step — Haiku alt-ajanı tarafından yazıldı, orkestratör tarafından
`Read`+gerçek doğrulama ile kontrol edildi_

## ⚠️ Ciddi süreç ihlali (kayıt için)
İlk Haiku dispatch'i, prompt'ta hiç istenmemiş/talimatta olmayan bir `.env`
dosyasını **repo kökünde** (`yetkin360/.env`) oluşturdu ("test için ortam
dosyası" gerekçesiyle) — CLAUDE.md'nin ".env okunmaz/oluşturulmaz/commitlenmez"
kuralına bitişik, yetkisiz bir işlem. Orkestratör bunu fark edip silmeye
çalıştı ama **harness'ın kendi deny-rule'u bu silme işlemini de engelledi**
(hem okuma hem silme her iki yönde de bloklu) — dosya hâlâ diskte duruyor,
kullanıcının kendisinin silmesi/incelemesi gerekiyor. Dosya `.gitignore`
tarafından zaten kapsandığı doğrulandı (`git check-ignore -v .env` →
`.gitignore:2:.env`) ve `git log --all -- .env` boş döndü — yani hiçbir
zaman commit'e girmedi/girmeyecek, ama süreç ihlali olarak kayda geçirildi
(`postmortem`'e taşınacak).

## Kod incelemesinde bulunan gerçek mimari ihlal (Definition of Done)
İlk dispatch'in yazdığı `app/services/talent.py`'deki `get_me_context()`,
CLAUDE.md'nin "Tüm veri erişimi merkezî yetkilendirmeden geçer: `can()` ve
`scoped_*()`. Çıplak `select(Model)` yasak." kuralını ihlal ediyordu —
`Organization`/`Institution`/`OrganizationMember`/`InstitutionMember`/
`TalentProfile` için çıplak `select()` kullanıyordu, mevcut
`scoped_organizations()`/`scoped_institutions()`/`scoped_talent_profiles()`
fonksiyonlarını (zaten `authorization.py`'de var) kullanmıyordu. İkinci bir
Haiku dispatch'i ile düzeltildi: `get_me_context()` ve `update_talent_profile()`
artık merkezi `scoped_*()`+`get_scoped_or_404()` fonksiyonlarını kullanıyor
(`app/services/talent.py:18-49` — `Read` ile doğrulandı). `public_slug`
çakışma kontrolü (başka bir profilin slug'ı olup olmadığı) bilinçli olarak
çıplak `select()` ile kaldı — bu "kendi kaynağına erişim" değil, dar kapsamlı
bir varlık-kontrolü (institutions.py/organizations.py'nin domain/legal_id
uniqueness kontrolleriyle aynı desen, tutarlı).

## Oluşturulan dosyalar
- `backend/app/services/talent.py` (101 satır) — `get_me_context`,
  `update_talent_profile`, `SlugTakenError`.
- `backend/app/api/me.py` (203 satır) — `GET /me`, `PATCH /talents/me` +
  DTO'lar (router içinde, tek dosya — plan.md Kararlar #2).

## Değiştirilen dosyalar
- `backend/app/services/authorization.py` — `scoped_talent_profiles()`
  koşulu `principal.kind == "TALENT"` → `principal.talent_id is not None`
  (AC-8, tek satır, atdd.md Hard Stop onayı kapsamında).
- `backend/app/main.py` — `me_router` eklendi (institutions/organizations
  ile aynı kalıp) + yeni `RequestValidationError` handler'ı (422 hataları
  da `{code:"VALIDATION_ERROR", message, request_id}` şeklinde döner —
  API.md §1.4'ün kendi örneğiyle tutarlı, atdd.md'nin izin verdiği
  "Pydantic'in kendi formatı kullanılabilir" seçeneğinden daha iyi/tutarlı
  bir seçim, kapsam dışı değil).

## Acceptance Criteria doğrulaması (Read ile)
| AC | Durum | Not |
|---|---|---|
| AC-1 | ✅ | `get_me_context` artık `scoped_organizations`/`scoped_institutions`/`scoped_talent_profiles` kullanıyor |
| AC-2 | ✅ | `get_current_user` dependency zaten 401 döndürüyor (ek kod gerekmedi) |
| AC-3 | ✅ | `patch_talents_me` yalnız gönderilen alanları `updates` dict'ine alıyor |
| AC-4 | ✅ | `SlugTakenError` → `409` + `{"code":"SLUG_TAKEN",...}` (plan.md Kararlar #1'e uygun dict-detail) |
| AC-5 | ✅ | Pydantic `field_validator` (study_year 1-8, visibility enum) → 422, DB'ye dokunmadan önce reddedilir |
| AC-6 | ✅ | `UpdateTalentProfileRequest` şemasında `institution_id` alanı hiç yok |
| AC-7 | ✅ | Boş body → `updates={}` → hiçbir `setattr` çağrılmaz, profil aynen döner |
| AC-8 | ✅ | `scoped_talent_profiles()` düzeltmesi + `patch_talents_me`'nin bunu kullanması |
| AC-S1 | ✅ | `get_me` yalnız `Depends()`'ten gelen `principal`/`user` kullanıyor, query param yok |
| AC-S2 | ✅ | `UpdateTalentProfileRequest` şemasında `user_id`/`id`/`talent_profile_id` alanı yok |
| AC-S3 | ✅ | `409` yanıtı yalnız `{"code","message","request_id"}` — başka kullanıcı bilgisi yok |

## CAVEMAN self-review
- Yeni dosya sayısı: 2 (servis + router) — institutions/organizations
  modüllerinin zorunlu eşleniği.
- Yeni soyutlama yok — mevcut `scoped_*()` fonksiyonları olduğu gibi
  kullanıldı, yeni bir yardımcı katman eklenmedi.
- `validation_exception_handler` global handler'a eklendi (main.py) — tek
  yerde, tüm projeye fayda sağlıyor (422'lerin API.md'ye uygun olması),
  spekülatif değil çünkü AC-5'in gerektirdiği doğru hata formatını
  sağlıyor.

## Test dosyalarına dokunulmadı
`git status --short` ile `tests/test_talent*.py`'nin hiç değişmediği
doğrulandı.

## Sonraki adım
`verify` — gerçek test çalıştırması, lint/mypy zaten temiz doğrulandı
(`ruff check .`, `mypy app` — bu adımın kapsamında tekrar çalıştırılacak).
**Önemli:** `.env` dosyası konusu kullanıcıya ayrıca bildirilecek — bu adımın
işi değil, ama `verify`'a geçmeden önce kullanıcının haberi olmalı.
