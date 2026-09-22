# Plan — yet-11-skill-claims
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Keşif özeti
- `Skill` modeli (`app/models/skill.py`) zaten var, DEĞİŞTİRİLMEYECEK.
- `SkillClaim` modeli, `app/api/talent_skills.py`, `app/services/skill_claim.py`
  hiçbiri yok — hepsi yeni.
- Migration head'i şu an tek (`045883d11996`, YET-9/YET-6 merge revizyonu
  sonrası) — yeni migration'ın `down_revision`'ı bu olacak, çatal riski yok.
- `app/models/__init__.py`'ye yeni `SkillClaim` export'u eklenmesi gerekiyor
  (mevcut kalıp: her yeni model burada import+`__all__`'a eklenmiş).
- `app/api/me.py` (206 satır) ve `app/services/talent.py` (102 satır) —
  YET-7'nin kurduğu `/me`, `/talents/me` uçlarıyla aynı router/prefix alanı.
  `GET/POST/DELETE /talents/me/skills` bu router'a mı eklensin yoksa ayrı
  `talent_skills.py`'ye mi — Open Questions'a bkz.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | Yeni `SkillClaim` export'u eklenir (mevcut kalıp). | low |
| `backend/app/services/authorization.py` | Yeni `scoped_skill_claims(session, principal)` fonksiyonu eklenir — mevcut fonksiyonlara (bu görevde `scoped_talent_profiles` dahil) dokunulmaz, sadece yeni bir fonksiyon eklenir. | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/models/skill_claim.py` | `SkillClaim` ORM modeli — DATABASE.md §2.2 şemasına birebir (`id`, `talent_id` FK→`talent_profiles.id`, `skill_id` FK→`skills.id`, `claimed_level` CHECK enum, `source` DEFAULT 'MANUAL' CHECK enum, `confirmed_by_user_at` nullable, UNIQUE(talent_id, skill_id)). |
| `backend/alembic/versions/<hash>_add_skill_claims_table.py` | Yeni migration — `skill_claims` tablosu (onay alındı, bkz. Migration Required?). |
| `backend/app/services/skill_claim.py` | İş mantığı: `add_skill_claim`, `list_skill_claims`, `remove_skill_claim` — `talent.py` kalıbı (validasyon DB'ye dokunmadan önce, exception sınıfları). |
| `backend/app/api/talent_skills.py` | Router: `POST /talents/me/skills`, `GET /talents/me/skills`, `DELETE /talents/me/skills/{skill_id}` — `me.py` kalıbı (DTO'lar router içinde, `{code,message,request_id}` hata sözleşmesi). Ayrı dosya (Open Questions'a bkz., öneri: ayrı dosya). |
| `backend/tests/test_skill_claim.py` | Fonksiyonel AC testleri (test-copilot yazacak). |
| `backend/tests/test_skill_claim_authorization.py` | AC-S1..AC-S4 izolasyon testleri (test-copilot yazacak). |

## Dependencies
- `app/api/deps.py` → `get_current_principal`, `get_session` (me.py/organizations.py ile aynı).
- `app/services/authorization.py` → `Principal`, yeni `scoped_skill_claims()`,
  `get_scoped_or_404()` (mevcut).
- `app/models/skill.py` → `Skill` (salt okunur — `status`, `id` alanları
  kullanılacak, AC-6'nın MERGED/DEPRECATED reddi için).
- `app/models/identity.py` → `TalentProfile` (salt okunur, `talent_id` FK
  hedefi).
- Hata sözleşmesi: YET-7'de kurulan `{code,message,request_id}` deseni
  (`app/main.py`'deki `api_error_handler`/`validation_exception_handler`)
  — DEĞİŞTİRİLMEYECEK, sadece kullanılacak.

## Migration Required?
**Evet** — `skill_claims` tablosu yeni, DATABASE.md §2.2 şemasına birebir:
```
id uuid PK
talent_id uuid NOT NULL REFERENCES talent_profiles(id)
skill_id uuid NOT NULL REFERENCES skills(id)
claimed_level text CHECK (claimed_level IN ('BEGINNER','INTERMEDIATE','ADVANCED'))
source text NOT NULL DEFAULT 'MANUAL' CHECK (source IN ('MANUAL','AI_EXTRACTED'))
confirmed_by_user_at timestamptz
UNIQUE (talent_id, skill_id)
CHECK (source <> 'AI_EXTRACTED' OR confirmed_by_user_at IS NOT NULL)
created_at, updated_at (TimestampMixin, proje kalıbı)
```
Geriye uyumlu (yeni tablo, mevcut veriyi etkilemez). `down_revision`:
`045883d11996` (tek head, çatal riski yok). `alembic upgrade head` +
`downgrade -1` + tekrar `upgrade head` `verify` adımında doğrulanacak.

## Risks
(atdd.md'den taşınan + keşifte bulunan)
- DOMAIN.md/DATABASE.md şema tutarsızlığı (atdd.md'de zaten not edildi,
  DATABASE.md esas alındı).
- YET-10'un iddia edilen kapsamının kod tabanında bulunamaması (atdd.md'de
  not edildi, bu görevi bloke etmiyor).
- Yeni `scoped_skill_claims()` fonksiyonu `authorization.py`'ye eklenirken
  mevcut fonksiyonlara (özellikle `scoped_talent_profiles`) yanlışlıkla
  dokunulmaması gerekiyor — `code-copilot`'a açıkça "SADECE yeni fonksiyon
  ekle, mevcutları değiştirme" talimatı verilecek.

## Open Questions
1. **Router dosyası:** `talent_skills.py` ayrı bir dosya mı (öneri —
   `me.py`'nin zaten 206 satır olması ve skill-claim mantığının kendi
   servis dosyasına sahip olması nedeniyle, tek dosyada büyümesindense
   ayrı router daha CAVEMAN-uyumlu: ilgili kod ilgili yerde), yoksa
   `me.py`'ye mi eklensin (YET-7 ile aynı dosyada tutmak, "/talents/me"
   önekini paylaşan uçları birleştirmek)? **Öneri: ayrı `talent_skills.py`**
   — `me.py` zaten kendi başına bir birim (GET /me + PATCH /talents/me),
   yeni 3 uç eklemek onu şişirir.
2. **MERGED/DEPRECATED skill claim reddi kodu:** atdd.md'nin Assumptions
   bölümünde önerilen `404 SKILL_NOT_FOUND` (ayrı kod yok, `merged_into_id`ye
   yönlendirme yok) onaylanıyor mu?

Kullanıcıdan yanıt/"sen karar ver" bekleniyor.

## Kararlar
(kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı)
1. **Router dosyası:** Ayrı `talent_skills.py` — onaylandı. `me.py` zaten
   kendi başına bir birim, 3 yeni uç eklemek onu şişirir.
2. **MERGED/DEPRECATED reddi:** `404 SKILL_NOT_FOUND` — onaylandı, ayrı kod
   icat edilmeyecek, `merged_into_id`'ye yönlendirme yapılmayacak.
