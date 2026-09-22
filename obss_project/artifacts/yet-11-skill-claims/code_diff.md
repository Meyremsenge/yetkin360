# Code Diff — yet-11-skill-claims
_Green step — Haiku alt-ajanı tarafından yazıldı, orkestratör tarafından
`Read`+gerçek doğrulama ile kontrol edildi_

## ⚠️ Ortam sorunu (kayıt için, alt-ajan kaynaklı değil)
Docker Desktop bu oturumda kapanmış/motoru durmuştu — ilk Haiku dispatch'i
bu yüzden migration'ı çalıştıramadığını/testleri doğrulayamadığını
raporladı ("PostgreSQL servisi çalışmıyor"). Orkestratör bunu bağımsız
`docker ps`/`docker info` ile doğruladı (gerçek bir ortam sorunuydu, alt-ajan
uydurmadı), kullanıcıdan Docker Desktop'ı yeniden başlatmasını istedi,
`docker compose up -d` ile konteynerleri kaldırıp devam etti.

## Kod incelemesinde bulunan gerçek hatalar (Definition of Done ihlali)
İlk implementasyon iki gerçek hata içeriyordu (pytest ile doğrulandı,
alt-ajanın "syntax doğru, DB olmadığı için çalıştıramadım" iddiası bu
hataları gizlemişti):

1. **`add_skill_claim()` `talent_id=None` kontrolü yapmıyordu** —
   talent profili olmayan bir kullanıcı `POST /talents/me/skills`
   çağırdığında, `SkillClaim(talent_id=None, ...)` INSERT denemesi DB'nin
   NOT NULL constraint'ini ihlal edip `IntegrityError` (500) fırlatıyordu
   — `404` dönmesi gerekirken (AC-S1).
2. **`get_skills()` aynı kontrolü yapmıyordu** — `scoped_skill_claims()`
   `talent_id=None` için boş sorgu döndürdüğünden, `GET` `200 {"items":[]}`
   dönüyordu — "hiç claim yok" ile "talent profili yok" ayırt edilemiyordu
   (boş-sonuç-hata-ayrımı ihlali, AC-S1).

Her iki endpoint'e (`post_skills`, `get_skills`) `me.py`'deki
`TALENT_PROFILE_NOT_FOUND` koduyla tutarlı bir `if principal.talent_id is
None: raise HTTPException(404, ...)` kontrolü eklendi. `delete_skills()`'e
dokunulmadı — o zaten `remove_skill_claim()`'in `SkillClaimNotFoundError`'ı
sayesinde doğru davranıyordu.

Ayrıca bir test hatası bulundu: `test_post_skills_happy_path`,
`claimed_level` gönderilmeden yapılan bir istekte `claimed_level is not
None` bekliyordu — DATABASE.md §2.2'ye göre bu alan nullable ve
gönderilmediyse `None` dönmesi doğru davranış; test assertion'ı düzeltildi.

## Oluşturulan dosyalar
- `backend/app/models/skill_claim.py` — `SkillClaim` ORM modeli
  (DATABASE.md §2.2 şemasına birebir).
- `backend/app/services/skill_claim.py` — `add_skill_claim`,
  `list_skill_claims`, `remove_skill_claim` + 4 exception sınıfı.
- `backend/app/api/talent_skills.py` — 3 endpoint (`POST`/`GET`
  `/talents/me/skills`, `DELETE /talents/me/skills/{skill_id}`).
- `backend/alembic/versions/f7e8g9h0i1j2_add_skill_claims_table.py` —
  migration (uygulandı ve doğrulandı, aşağı bakınız).

## Değiştirilen dosyalar
- `backend/app/models/__init__.py` — `SkillClaim` export'u eklendi.
- `backend/app/services/authorization.py` — yeni `scoped_skill_claims()`
  fonksiyonu eklendi (mevcut fonksiyonlara dokunulmadı — `Read` ile
  doğrulandı, `scoped_talent_profiles`/`scoped_organizations`/
  `scoped_institutions`/`can()` değişmemiş).
- `backend/app/main.py` — `talent_skills_router` eklendi (diğer router'larla
  aynı kalıp).

## Migration doğrulaması
`alembic upgrade head` (`045883d11996` → `f7e8g9h0i1j2`), `alembic
downgrade -1`, tekrar `alembic upgrade head` döngüsü orkestratör tarafından
bizzat çalıştırılıp doğrulandı (Docker Desktop yeniden başlatıldıktan
sonra). `alembic current` → `f7e8g9h0i1j2 (head)`.

## Acceptance Criteria doğrulaması (Read + pytest ile)
| AC | Durum | Not |
|---|---|---|
| AC-1 | ✅ | `add_skill_claim` → 201, `{skill_id, claimed_level, source:"MANUAL"}` |
| AC-2 | ✅ | `list_skill_claims` skill join'i ile `{items:[...]}` |
| AC-3 | ✅ | `session.delete(claim)` — hard-delete |
| AC-4 | ✅ | Skill bulunamazsa `SkillNotFoundError` → 404 |
| AC-5 | ✅ | Duplicate → `SkillAlreadyClaimedError` → 409 |
| AC-6 | ✅ | `skill.status != "ACTIVE"` → aynı `SkillNotFoundError` → 404 (ayrım sızdırılmıyor) |
| AC-7 | ✅ | Scoped sorgu boşsa `SkillClaimNotFoundError` → 404 |
| AC-8 | ✅ | Boş liste → `200 {"items":[]}` |
| AC-S1 | ✅ (düzeltme sonrası) | `talent_id is None` → 404, hem POST hem GET'te |
| AC-S2 | ✅ | `PostSkillClaimRequest` şemasında `talent_id`/`user_id` yok |
| AC-S3 | ✅ | `scoped_skill_claims()` kullanılıyor, çıplak `select(SkillClaim)` yok (`list_skill_claims` içinde `select(Skill)` var ama bu talent'a özel değil, genel skill lookup — CLAUDE.md'nin "kendi kaynağına erişim scoped olmalı" kuralı ihlal edilmiyor) |
| AC-S4 | ✅ | `scoped_skill_claims().where(skill_id==...)` — başka talent'ın claim'i bulunamaz |

## CAVEMAN self-review
- Yeni dosya sayısı: 3 (model + servis + router) — institutions/organizations/
  talent modüllerinin zorunlu eşleniği.
- Yeni soyutlama yok — `talent.py`/`me.py` kalıbı takip edildi.
- `scoped_skill_claims()` tek satırlık, mevcut `scoped_talent_profiles()`
  kalıbının birebir aynısı.

## Test dosyalarına dokunulmadı (implementasyon fazında)
`git diff` ile `tests/test_skill_claim*.py`'nin code-copilot dispatch'i
sırasında değişmediği doğrulandı — yalnız ayrı bir dispatch'te (test
assertion hatası düzeltmesi) tek satır değişti, bu `test-copilot`'un
sorumluluk alanına ait bir düzeltmeydi.

## Sonraki adım
`verify` — gerçek test çalıştırması zaten bu adımda yapıldı (298 test PASS,
authorization suite 71 PASS, ruff/mypy temiz) ama `verify` skill'i CI
komutlarıyla resmi olarak tekrar teyit edecek.
