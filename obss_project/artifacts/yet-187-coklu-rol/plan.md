# Plan — yet-187-coklu-rol
_Reference: atdd.md (aynı klasör). Salt okuma keşfi; kod/test henüz yazılmadı._

## Tasarım özeti
1. `Principal` (authorization.py): `kind` kalır (gösterim), yeni türetilmiş özellik `coordinator_institution_ids` = `institution_ids` eksi `institution_admin_ids`. Yeni dataclass alanı yok, mevcut `Principal(...)` çağrıları ve testler geçerli kalır.
2. Tek merkezî yardımcı `engagement_relation(principal, engagement)` (authorization.py): kaynak bazlı ilişkiyi döner (`is_subject`, `is_org_member`, `is_org_admin`, `is_coordinator`, `has_org_side_link`). AC-S1 kuralı yalnız burada: principal engagement'ın talent'ı (`talent_id == engagement.talent_id`) ise org/koordinatör bayrakları False'a maskelenir, ham üyelik `has_org_side_link` ile ayrıca görülebilir.
3. `can()` ve `scoped_*`: `kind` yerine id listeleri. `scoped_engagements` = `or_(talent_id == ..., organization_id IN org_ids, institution_id IN institution_ids)` (boş küme → false), `scoped_evidence` yalnız `talent_id`'ye bağlı.
4. Servislerdeki `principal.kind` kararları `engagement_relation` ile değişir; mevcut hata türleri/kodları (404 / TransitionForbiddenError) aynen korunur.
5. Statik koruma: services/ ve api/ altında `principal.kind` yetki kararında okunmaz.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/app/services/authorization.py | Principal docstring + `coordinator_institution_ids`; `can()` (Organization/Institution kind kontrolü kalkar, yalnız `*_admin_ids`); `scoped_organizations/institutions/engagements/evidence` birleşim; yeni `engagement_relation` (AC-1,2,3,5,S1,S2,S3,S4) | high |
| backend/app/services/engagement.py | create (satır ~145-170: kendi talent'ı veya üye olunan org), geçiş tablosu (~290-335), create_task (~479-484), submit_deliverable (~601), dashboard (~709) (AC-1,3,S1,S5) | high |
| backend/app/services/attestation.py | satır 140 (koordinatör kriteri), 197-215 (TALENT/koordinatör/org admin rol kontrolü) (AC-S1: self-attest 404) | high |
| backend/app/services/evaluation.py | satır 114-130 direction/rol tutarlılığı, satır 199 `attested_by_org_id` (AC-S1) | high |
| backend/app/api/organizations.py | satır 247, 341: `kind != "ORG_ADMIN"` koşulu kalkar, yalnız `organization_id in org_admin_ids` (AC-1,S4) | medium |
| backend/app/api/deps.py | Davranış aynı; yalnız docstring/yorum ("kind gösterim içindir; yetki listelerden") (AC-6) | low |

## New Files
| File | Purpose |
|------|---------|
| backend/tests/authorization/test_multi_role_authorization.py | Çoklu rol saldırgan matrisi (gerçek DB + gerçek get_current_principal): AC-1,2,3,5,7,8, AC-S1..S5 |
| backend/tests/authorization/test_principal_roles_unit.py | `coordinator_institution_ids`, `engagement_relation` (maskeleme), `scoped_*` birleşim derlemesi |
| backend/tests/authorization/test_no_kind_authz.py | Statik koruma (AC-6): `app/services` + `app/api` içinde `principal.kind` geçmez (deps.py'deki kind hesabı ve Principal tanımı hariç) |

## Dependencies
- `get_current_principal` (api/deps.py) her istekte üyelikleri DB'den kurar → AC-8 için ek kod yok, yalnız test.
- `scoped_engagements` tüm engagement servislerinin ortak girişi (engagement, attestation, evaluation, reminders, dashboard, verified-experience yolları); birleşim değişikliği hepsini etkiler.
- `scoped_evidence`: api/evidence.py ve services/evidence.py çağırır.
- Test altyapısı: tests/authorization/conftest.py fixture'ları (org_a/org_b, talent_a/b, org_a_member...), `tests/_testdb.py session_override`. Dashboard API'sinde `ValueError` eşlemesi code aşamasında okunacak (hata mesajı ayrımı korunacak).
- Frontend'e dokunulmaz.

## Migration Required?
Hayır. Şema değişmez; yeni alan ORM'de değil, `Principal` dataclass'ında türetilmiş özellik. Geri alma = commit revert.

## Risks
- `scoped_engagements` birleşimi tüm engagement akışlarını etkiler: tenant sızıntısı için AC-7/AC-S2 matrisi zorunlu (authz-test adımında canlı probe).
- Davranış değişimi (bilinçli): (a) org/koordinatör+talent kendi engagement'ında org-tarafı eylemini yapamaz (AC-S1; bugün org ADMIN+talent self-attest yapabiliyor); (b) üye+talent kullanıcı artık kendi talent kayıtlarını da görür. Bu ikisini kapsayan eski bir test kırılırsa test gevşetilmez; kod mu test mi yanlış anlaşılıp sorulur.
- Principal'ı kind-tutarsız kuran testler (kind="TALENT" ama org_ids dolu gibi) birleşimde farklı davranabilir; kırılanlar tek tek incelenir.
- INST_ADMIN geçiş yetkisi bilinçli olarak eklenmiyor (YET-190); `coordinator_institution_ids` bu yüzden admin kurumlarını dışlar. INST_ADMIN'in engagement görünürlüğü (institution_ids kapsamı) aynen kalır.
- Dashboard: yetkisiz principal'a dönen `ValueError` mesajları ("Not authorized" / "Institution not found") API'de nasıl eşleniyorsa aynı kalmalı (404 kuralı).
- Org üyeliği `status` (PENDING) filtresi yok; kapsam dışı, kabul edilen risk.

## Open Questions
Yok. atdd.md'deki üç karar (AC-S1 kapsamı, INST_ADMIN'in YET-190'a bırakılması, `kind`'ın Principal'da kalması) kullanıcı onayıyla "devam" denerek kabul edildi. Alt-ajan çağrısı gerekmedi.

## UI notu
Render edilen web UI dosyası yok → verify'da gate 11 (`vision-test`) N/A.

## Doğrulama planı
`pytest tests/authorization -q` tamamı + tüm backend paketi, `python -m ruff check .`, `python -m mypy app`; security-scan kapısı; frontend testleri değişmediği için yalnız son kontrol (823/823).
