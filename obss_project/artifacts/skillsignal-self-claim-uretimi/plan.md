# Plan — skillsignal-self-claim-uretimi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, `.tsx`/`.css`/UI kriteri yok).

## Keşif Özeti

`backend/app/api/talent_skills.py`'nin router prefix'i `/talents/me/skills` —
`GET /talents/me/signals` FARKLI bir path (`/talents/me/signals`), bu yüzden
aynı router'a eklenemez. Yeni bir `backend/app/api/skill_signals.py` dosyası
(kendi `APIRouter(prefix="/talents/me/signals")`) açılacak, `main.py`'ye
`include_router` ile eklenecek — mevcut `evidence.py`/`engagements.py`
deseniyle birebir aynı (her domain kendi router dosyasında).

`backend/app/services/authorization.py::scoped_skill_claims()` (satır 135)
tam olarak atdd.md'nin beklediği deseni gösteriyor: `principal.talent_id is
not None` kontrolü + `select(Model).where(Model.talent_id ==
principal.talent_id)`, aksi halde boş sonuç. `scoped_skill_signals()` bunun
birebir kopyası olacak (SkillSignal modeline uyarlanmış).

`backend/app/services/skill_claim.py::add_skill_claim()` (satır 31-106)
zaten `session.flush()` ile TEK bir INSERT yapıyor — SkillSignal INSERT'i bu
flush'tan ÖNCE (aynı transaction, `session.add()` ile) eklenip birlikte
flush edilecek. `POST /talents/me/skills` route'unun (`api/talent_skills.py`
satır 83-141) davranışı/response şeması DEĞİŞMİYOR — sadece servis
fonksiyonunun içi genişliyor.

`backend/app/models/skill_claim.py` taban deseni (Base+TimestampMixin,
uuid7_default, CheckConstraint) `SkillSignal` modeli için birebir
kopyalanacak. Mevcut alembic tek head: `i0j1k2l3m4n5`.

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | `SkillSignal`'i export listesine ekle | low |
| `backend/app/services/skill_claim.py` | `add_skill_claim()` içine SkillSignal INSERT'i (aynı transaction) | medium (mevcut fonksiyona dokunuyor, ama sadece ekleme) |
| `backend/app/main.py` | Yeni `skill_signals_router`'ı import+include et | low |

## New Files

| File | Purpose |
|------|---------|
| `backend/app/models/skill_signal.py` | `SkillSignal` SQLAlchemy modeli (append-only, DOMAIN.md §3.14 şeması) |
| `backend/app/services/skill_signal.py` | `list_skill_signals()` servis fonksiyonu — `scoped_skill_signals()` ile talent'ın sinyallerini skill bazlı gruplar |
| `backend/app/api/skill_signals.py` | `GET /talents/me/signals` route'u + Pydantic response şemaları |
| `backend/alembic/versions/<yeni_rev>_add_skill_signals_table.py` | Migration: `skill_signals` tablosu (down_revision=`i0j1k2l3m4n5`, mevcut tek head) |
| `backend/tests/test_skill_signals.py` | Happy path + boş liste + filtre + claim-silinince-sinyal-kalır testleri |
| `backend/tests/authorization/test_skill_signals.py` (veya mevcut `test_matrix.py`'ye ekleme) | Çapraz-talent izolasyon testleri (AC-S1/AC-S2) |

`backend/app/services/authorization.py`'ye `scoped_skill_signals()` eklenecek
— bu dosya zaten "Files to Modify" listesine girmeli, atdd.md'nin
`affected_modules`'ında vardı, burada teyit edildi:

| File | Why | Risk |
|------|-----|------|
| `backend/app/services/authorization.py` | Yeni `scoped_skill_signals()` (scoped_skill_claims() deseninde) | low |

## Dependencies
- `app.services.authorization.Principal`, `scoped_skill_claims()` (referans desen)
- `app.services.skill_claim.add_skill_claim()` — SkillSignal INSERT'i buraya eklenecek
- `app.models.base.Base`, `TimestampMixin`, `uuid7_default`
- `app.api.deps.get_current_principal`, `get_session` (mevcut route şablonu)

## Migration Required?
**Evet** — tek yeni tablo: `skill_signals` (id, talent_id FK→talent_profiles,
skill_id FK→skills, source_type CHECK IN (...), source_id UUID nullable,
strength CHECK IN ('NONE','WEAK','MODERATE','STRONG'), attested_by_org_id
FK→organizations nullable, occurred_at timestamptz, created_at timestamptz,
superseded_by_id FK→skill_signals nullable — self-referencing, append-only).
**UPDATE/DELETE immutability trigger'ı DA eklenecek** — kod keşfinde
`backend/alembic/versions/a1b2c3d4e5f6_add_audit_events_table_and_immutability_trigger.py`
bulundu: `audit_events` tablosu için gerçek bir Postgres `BEFORE UPDATE OR
DELETE` trigger'ı (append-only'yi DB seviyesinde zorluyor) zaten var — proje
emsali net. `skill_signals` migration'ı aynı deseni (`skill_signals_immutable`
trigger + fonksiyon) birebir kopyalayacak. Bu, `.claude/rules/database.md`
kuralıyla ("Kısıt veritabanında olur... sadece uygulama kontrolü yetmez")
tam uyumlu.

**CLAUDE.md kuralı gereği bu migration'ı oluşturmadan/uygulamadan önce
kullanıcıdan açık onay alınacak** — bu plan.md'nin sunumunda ayrıca sorulacak.

## Risks
- (atdd.md'den taşındı) Migration onayı zorunlu.
- (atdd.md'den taşındı) `scoped_skill_signals()` kod tekrarı — kabul edilen risk.
- Immutability trigger deseni `audit_events`'ten kopyalanacak (kod keşfinde
  doğrulandı, aşağıya bkz.) — migration biraz daha büyük olacak ama karar
  net, ek onay gerektirmiyor.

## Open Questions

Yok — kod keşfi (`scoped_skill_claims()` deseni, router prefix ayrımı,
`add_skill_claim()`'in flush noktası, `audit_events`'teki immutability
trigger emsali) atdd.md'nin bıraktığı tek belirsizliği kapattı.
