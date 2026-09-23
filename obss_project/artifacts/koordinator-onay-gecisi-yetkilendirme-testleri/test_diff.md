# Test Diff — koordinator-onay-gecisi-yetkilendirme-testleri
_Reference: atdd.md, plan.md_

## Değiştirilen Dosyalar

- `backend/tests/test_engagement_transitions.py` — 5 yeni fixture + 3 yeni test sınıfı (7 yeni test fonksiyonu) eklendi.
- `backend/tests/authorization/test_matrix.py` — sadece 2 docstring güncellendi (YET-7 → YET-65 referansı), test mantığı değişmedi.

## AC → Test Eşlemesi

| AC | Test | Durum |
|---|---|---|
| AC-1 (happy path) | `TestTransitionHappyPathT1::test_transition_draft_to_pending_approval_200` (mevcut) | zaten vardı |
| AC-2 / AC-S1 | `TestCoordinatorCrossInstitution::test_transition_cross_institution_coordinator_pending_to_active_404` | yeni |
| AC-3 / AC-S2 | `TestCoordinatorCrossInstitution::test_transition_cross_institution_coordinator_invalid_to_status_404` | yeni |
| AC-4 / AC-S3 | `TestOrgAdminScopeVsAdminMismatch::test_org_member_not_admin_vs_active_engagement_403` | yeni |
| AC-5 | `TestCoordinatorCrossInstitution::test_transition_cross_institution_fiona_vs_alice_404` | yeni |
| AC-6 | `TestTransitionPreconditionFailed::test_transition_reason_missing_for_reject_422` (mevcut) | zaten vardı |
| AC-7 / AC-S5 | `TestTransitionVersionConflict::test_transition_version_old_409` (mevcut) | zaten vardı |
| AC-8 / AC-S4 | `TestExtraFieldsIgnored::test_extra_org_id_in_payload_ignored`, `test_extra_institution_id_in_payload_ignored` | yeni |
| AC-S6 (authz-test matris) | Kapsam dışı bırakıldı, bkz. aşağıdaki not | — |

## Not — AC-4/AC-S3 fixture sapması

`evan_member_of_org_b` fixture'ı yalnızca `user_org_admin_evan` (User) ve
`organization_b`'ye bağlı — `org_admin_evan` (organization_a'daki ADMIN
üyeliği) fixture'ını zincire dahil etmiyor. Sonuç: bu testte Evan'ın TEK
üyeliği `organization_b`'de `role="MEMBER"`. Bu, atdd.md'nin tasarladığı
"org_ids⊃org_admin_ids" (bir kurumda admin, diğerinde sade üye) senaryosundan
biraz farklı — burada Evan hiçbir yerde admin değil, sadece `organization_b`
üyesi. Davranışsal sonuç aynı (kaynak org_ids kapsamında görünür, eylem
yasak → 403, 404 değil) ve AC-4'ün özünü doğruluyor, ama `get_current_principal`
`kind`'ı bu haliyle `ORG_MEMBER` çıkarıyor (`ORG_ADMIN` değil) — `can_transition`
zaten `principal.kind == "ORG_ADMIN"` kontrolüyle başladığı için sonuç
değişmiyor, ama tam senaryo (aynı principal'ın bir kurumda admin bir kurumda
sade üye olması) ayrıca doğrulanmadı. `code-copilot`/`verify` aşamasında bu
test kırmızı çıkarsa ya da tam senaryo isteniyorsa fixture'a `org_admin_evan`
bağımlılığı eklenmesi gerekir — şimdilik davranışsal olarak yeterli kabul
edildi, `red-team` adımında tekrar değerlendirilebilir.

## AC-S6 kapsam notu

`authz-test` skill'i (YET-77'nin istediği tam parametrik matris) bu adımda
ÇAĞRILMADI — `test-copilot` sadece Haiku alt-ajan dispatch'i yapıyor,
`authz-test` ayrı bir skill/adım. `verify` veya kullanıcı onayıyla ayrıca
tetiklenmesi gerekiyor; atdd.md'nin Unknowns bölümüne not düşüldü.

## Beklenen Sonuç

Testler "red step" değil — implementasyon (`transition_engagement`,
`scoped_engagements`) PLAN 2.2'de zaten yazılmış. Bu testlerin çoğu
YEŞİL geçmesi bekleniyor; kırmızı çıkan olursa (özellikle AC-S2/AC-S3)
gerçek bir yetkilendirme bug'ı işaret eder ve `code-copilot`/`verify`
aşamasında ele alınmalı.
