# Test Diff — calismalar-gercek-backend-baglama
_Red step (test-copilot, 2 ayrı Haiku alt-ajanı: backend + frontend)_

## Genişletilen Dosyalar
| Dosya | Yeni test | Amaç |
|---|---|---|
| `backend/tests/authorization/test_engagement_authorization.py` | 12 (+8 fixture) | `TestEngagementList` (AC-1,2,3,7,8), `TestEngagementDetail` (AC-4,5,6,AC-S1,AC-S2) |
| `frontend/lib/api/engagements.test.ts` | 8 | `listEngagements`/`getEngagement`'ın gerçek `apiFetch` çağrısı yaptığını doğrulayan testler (AC-1,4,5,6,7) |

Diskte doğrulandı (`git status --short`): her iki dosya `M`.

## AC → Test eşleşmesi
- AC-1 (TALENT kendi engagement'ları): `test_talent_lists_own_engagements_ac1`, `test_talent_sees_only_own_engagements_ac1_isolation` + frontend 2 test
- AC-2 (ORG_MEMBER/ORG_ADMIN izolasyonu): `test_org_member_lists_own_org_engagements_ac2`, `test_org_member_sees_only_own_org_engagements_ac2_isolation` (principal.kind="MEMBER" ayrıca doğrulanıyor)
- AC-3 (COORDINATOR/INST_ADMIN izolasyonu): `test_coordinator_lists_own_institution_engagements_ac3` + isolation testi
- AC-4 (detay: tasks+deliverables): `test_get_engagement_detail_returns_all_fields_ac4` + frontend 2 test
- AC-5/AC-S1 (kapsam dışı → 404, veri sızmaz): `test_get_engagement_out_of_scope_returns_404_ac5`, `test_talent_cannot_access_another_talent_engagement_ac_s1` + frontend 1 test
- AC-6/AC-S2 (var/yok ayırt edilemez): `test_get_nonexistent_engagement_returns_404_ac6`, `test_out_of_scope_and_nonexistent_return_same_status_and_body_ac6_s2`, `test_org_member_cannot_access_another_org_engagement_ac_s2` + frontend 2 test
- AC-7 (boş liste): `test_empty_list_returns_200_ac7` + frontend 1 test
- AC-8 (sayfalama): `test_list_with_pagination_limit_offset_ac8`
- AC-9 (mock temizliği): implementasyon aşamasında doğrulanacak (test dosyalarının kendisi mock kaldırıldığında GREEN olacak şekilde yazıldı)

## Dokunulmayan (bilinçli korunan) testler
`frontend/lib/api/engagements.test.ts`'teki `transitionEngagement` mock
durum-makinesi testleri (12 test: version conflict, illegal transition,
reason zorunluluğu vb.) DEĞİŞMEDİ — plan.md'nin riski: bu fonksiyon zaten
gerçek uca gidiyordu, bu görevin kapsamı dışı.

## Durum
Red (beklenen) — backend'de `GET /engagements`/`GET /engagements/{id}` yok,
frontend'de `USE_MOCK_LIST`/`USE_MOCK_DETAIL` hâlâ `true`. Sonraki adım:
`code-copilot`.
