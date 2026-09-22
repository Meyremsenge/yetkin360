# Plan — skill-taksonomisi-seed-arama
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/app/services/authorization.py | `scoped_skills()` eklenecek — mevcut `scoped_organizations`/`scoped_institutions`/`scoped_talent_profiles` deseniyle tutarlı, çıplak `select(Skill)` yasak kuralı gereği (AC-1, AC-5, AC-9). Skill global veri olduğu için tüm authenticated principal'lar (kind != None) için filtresiz `select(Skill)` döner — tenant filtresi yok, sadece merkezi giriş noktası. | low |

## New Files
| File | Purpose |
|------|---------|
| backend/scripts/__init__.py | `scripts` paketini `python -m scripts.seed` olarak çalıştırılabilir yapar (boş dosya). |
| backend/scripts/seed.py | ~150 (100-200 aralığı) skill'lik taksonomi verisini idempotent şekilde (`ON CONFLICT (slug) DO NOTHING`) tek transaction içinde ekler. Konsola özet basar ("N yeni kayıt eklendi" / "0 yeni kayıt eklendi"). AC-6, AC-7, AC-8 (Davranış Sözleşmesi satır 7-8). |
| backend/app/schemas/skill.py | `SkillResponse` (id, slug, name_tr, name_en, category, status, merged_into_id) ve `SkillSearchResponse` (items, total) Pydantic DTO'ları — mevcut `organizations.py`/`institutions.py` deseniyle tutarlı (`from_attributes = True`). AC-1, AC-4. |
| backend/app/services/skill.py | Arama iş mantığı: `search_skills(session, principal, q, limit, offset)` — `scoped_skills()` üzerinden `ilike()` ile parametrize arama, DEPRECATED hariç, MERGED dahil + `merged_into_id` snapshot, `name_tr ASC` sıralama. Router'da iş mantığı yazılmaz kuralı gereği burada. AC-1, AC-3, AC-4, AC-9 (AC-S1). |
| backend/app/api/skills.py | `GET /skills/search?q=&limit=&offset=` router'ı. `q`: `Field(..., min_length=2, max_length=200)`, `limit`: `Field(20, le=100)`. `get_current_principal` dependency ile 401 zaten `get_current_user`'dan geliyor (AC-5). 500 durumunda generic mesaj (AC-10/AC-S2 — FastAPI'nin default exception handler'ı zaten stack trace'i response'a sızdırmıyor, ekstra kontrol gerekmez, sadece doğrulanacak). AC-1, AC-2, AC-3, AC-5, AC-9, AC-10, AC-11. |
| backend/tests/authorization/test_skill_authorization.py | Pozitif test (authenticated her principal kind için 200) + negatif test (token yok → 401) + AC-S1/S2/S3 threat-model testleri (wildcard arama, DB hata mesajı sızıntısı yok — mock edilebilir, çok uzun q → 400). Mevcut `conftest.py` fixture'ları (`session`, user/org fixture'ları) kullanılır, skill için yeni fixture eklenebilir. |
| backend/tests/test_seed_skills.py (veya backend/tests/scripts/test_seed.py) | Seed script'in unit/integration testleri: 100-200 aralığı kayıt sayısı, slug UNIQUE, category CHECK uyumu, idempotency (iki kez çalıştırma → aynı sonuç), transaction rollback (kısmi hata senaryosu). |

## Dependencies
- `app.services.authorization.Principal`, `get_scoped_or_404` — mevcut, değişmeyecek.
- `app.api.deps.get_current_principal`, `get_session` — mevcut, aynen kullanılacak (auth zaten 401 döndürüyor, bkz. `app/core/deps.py:get_current_user`).
- `app.models.Skill` — mevcut ORM modeli, değişmeyecek (id, slug, name_tr, name_en, category, parent_id, status, merged_into_id zaten var).
- Mevcut router deseni (`organizations.py`, `institutions.py`): `APIRouter(prefix=..., tags=...)`, Pydantic DTO'lar dosya başında, `HTTPException` ile durum kodları, docstring'de AC referansları.
- `scoped_organizations`/`scoped_institutions`/`scoped_talent_profiles` — `scoped_skills()` bu üçünün deseniyle tutarlı yazılacak (tek fark: global veri olduğu için kiracı ID listesine göre filtre yok, sadece "authenticated mi" kontrolü).

## Migration Required?
**Hayır.** `skills` tablosu zaten `alembic/versions/b82aa928fbd2_initial_schema_users_institutions_.py` (initial schema) migration'ında mevcut — tüm gerekli kolonlar (id, slug, name_tr, name_en, category, parent_id, status, merged_into_id) ve CHECK constraint'ler zaten uygulanmış. Bu görev sadece seed verisi (uygulama/script seviyesinde, migration değil) ve yeni bir okuma endpoint'i ekliyor.

## Risks
- (atdd.md'den taşındı) Rate limit bu endpoint'te yok — PLAN 1.6'daki ertelenmiş genel rate-limit kararına bağlı, kabul edilen risk.
- (atdd.md'den taşındı) 401 dönüşü CLAUDE.md'nin "403→404" kuralına küçük nüans taşıyor ama mevcut `get_current_user` davranışıyla tutarlı, yeni bir sapma değil.
- **Yeni bulgu:** `scoped_skills()` için `Principal.kind` kontrolü nasıl olacak netleşmeli — mevcut üç `scoped_*` fonksiyonu belirli `kind` değerlerine (`ORG_MEMBER`/`ORG_ADMIN`, `INST_ADMIN`/`COORDINATOR`, `TALENT`) göre filtreliyor. Skill için TÜM `kind` değerleri (TALENT, ORG_MEMBER, ORG_ADMIN, COORDINATOR, INST_ADMIN, USER) erişebilmeli — `principal.user_id is not None` kontrolü yeterli olabilir (kimliksiz principal zaten `get_current_principal`'a hiç ulaşamıyor, `get_current_user` 401 ile keser). Bu, `scoped_skills`'i diğer üçünden basit yapıyor: pratikte koşulsuz `select(Skill)` dönebilir çünkü fonksiyona ulaşan her principal zaten authenticated.
- **Yeni bulgu:** Seed script'teki ~150 skill'in gerçek içeriği (isim TR/EN, kategori, hiyerarşi) hâlâ Unknown (atdd.md'de de işaretli) — `test-copilot`/`code-copilot` bu veriyi bir yerden üretmek zorunda kalacak. Plan aşamasında bu çözülemez, aşağıda açık soru olarak taşınıyor.

## Open Questions (çözüldü)
1. ~150 skill'lik taksonomi verisinin kaynağı → **Elle küçük ama gerçekçi bir örnek küme (100-200 arası), ESCO/O*NET'ten uyarlama değil.** (Sonnet 5 low alt-ajanı tarafından yanıtlandı: MVP kapsamı seed script'i DB-only tutuyor, dış veri kaynağı entegrasyonu ne atdd.md'de ne plan.md'de işaret ediliyor; AI/eşleştirme zaten MVP dışı yasaklı.)
2. `scoped_skills()` filtre mantığı → **Koşulsuz `select(Skill)` yeterli, `is_suspended` kontrolü eklenmez.** (Sonnet 5 low alt-ajanı tarafından yanıtlandı: fonksiyona ulaşan her principal `get_current_user` seviyesinde zaten authenticated; diğer üç `scoped_*` fonksiyonu da suspension kontrolü yapmıyor, tutarlılık bozulmamalı.)
3. `merged_into_id` snapshot'ı → **Ayrı join yazılıp hedefin `slug`/`name_tr` bilgisi aynı response'a gömülür, frontend ikinci çağrı yapmaz.** (Sonnet 5 low alt-ajanı tarafından yanıtlandı: atdd.md AC-4 birebir "merged_into_id ve hedefin slug/name'i" diyor, bu response şeklinin parçası; ikinci round-trip <300ms performans hedefiyle çelişir.)
