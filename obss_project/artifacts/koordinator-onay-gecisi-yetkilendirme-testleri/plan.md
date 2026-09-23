# Plan — koordinator-onay-gecisi-yetkilendirme-testleri
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, `.tsx`/`.css`/UI kriteri yok).

## Keşif Özeti

`backend/tests/test_engagement_transitions.py` zaten HTTP-uç seviyesinde
(`client` = FastAPI TestClient, `X-Debug-User-Id` header ile principal enjekte
ediliyor) geniş bir pozitif-yol testi içeriyor: T2 (Diana/COORDINATOR,
institution_a → ACTIVE), T3 (REJECTED), T6 (Evan/ORG_ADMIN ve Diana/COORDINATOR
→ CANCELLED), ve **tek bir** çapraz-tenant testi zaten var
(`TestTransitionNoAccess::test_transition_org_member_unauthorized_org_404` —
Charlie/org_a üyesi, Bob'un org_b engagement'ına erişmeye çalışıyor → 404).

Eksik olan tam olarak atdd.md'nin hedeflediği şey: **COORDINATOR'ün
çapraz-KURUM (institution) senaryosu** (Diana institution_a, Bob'un
institution_b'deki PENDING_APPROVAL/ACTIVE engagement'ını onaylamaya/iptal
etmeye çalışması) ve **ORG_ADMIN'in org_ids⊃org_admin_ids farkı senaryosu**
(bir kullanıcı organization_b'nin MEMBER'ı ama ADMIN'i değilken CANCELLED
denemesi → 403 bekleniyor, 404 değil — mevcut testlerde hiç yok).

Mevcut fixture'lar (`institution_b`, `organization_b`,
`engagement_draft_bob_isolated`, `talent_bob`) zaten var ama:
- `institution_b` için bir COORDINATOR fixture'ı (Diana'nın institution_b
  eşdeğeri) yok.
- `engagement_draft_bob_isolated` DRAFT durumunda — PENDING_APPROVAL/ACTIVE
  durumunda bob-isolated engagement fixture'ı yok (T2/T6 çapraz-kurum testi
  için gerekli).
- `organization_b`'de MEMBER (ADMIN değil) bir kullanıcı fixture'ı yok
  (AC-4/AC-S3 — org_ids⊃org_admin_ids senaryosu için gerekli: bu kullanıcının
  `org_ids=[organization_a, organization_b]` ama `org_admin_ids=[organization_a]`
  olması gerekiyor, yani **organization_b'ye MEMBER olarak eklenen ama
  organization_a'da ADMIN olan Evan** gibi bir kurulum — mevcut `org_admin_evan`
  fixture'ı sadece organization_a'ya bağlı, ikinci bir üyelik eklenmeli).

`tests/authorization/test_matrix.py`'deki `TestFutureResourcesPlaceholders`
sınıfında engagement'a özgü iki test (`test_engagement_access_org_member_read_own_org`,
`test_coordinator_scope_filtering`) zaten **skip değil, gerçek query-layer
testi** — bunlar HTTP-uç testleriyle çakışmıyor, ayrı katman (SQLAlchemy
`scoped_engagements()` doğrudan). Bu görevde bunlara DOKUNULMAYACAK; sadece
docstring'lerindeki "Status: YET-7 ... pending" notu güncellenecek (artık
pending değil, tamamlandı) çünkü YET-65 bu görevi kapatıyor.

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/tests/test_engagement_transitions.py` | Yeni fixture'lar (institution_b coordinator, PENDING_APPROVAL/ACTIVE bob-isolated engagement, org_b member-not-admin) + AC-2/AC-3/AC-4/AC-5/AC-S1/AC-S2/AC-S3 test sınıfları eklenecek | low |
| `backend/tests/authorization/test_matrix.py` | `test_engagement_access_org_member_read_own_org` ve `test_coordinator_scope_filtering` docstring'lerindeki "YET-7 ... pending" notu "YET-65 ile HTTP-uç seviyesinde tamamlandı, bkz. test_engagement_transitions.py" olarak güncellenir | low |
| `backend/app/services/engagement.py` | **Sadece** AC-S2/AC-S3 testleri kırmızı çıkarsa (kontrol sırası ya da org_ids/org_admin_ids karışıklığı gerçek bir bug ise) — mevcut kodun okunmasında sıra zaten doğru görünüyor (`get_scoped_or_404` önce, `transition_spec["can_transition"]` sonra), bu satır **tedbiren** listelendi | low (muhtemelen değişmeyecek) |
| `backend/app/services/authorization.py` | Aynı gerekçeyle tedbiren listelendi — `scoped_engagements()`/`can()` değişmesi beklenmiyor | low (muhtemelen değişmeyecek) |

## New Files

Yok — mevcut test dosyalarına ekleme yapılacak (fixture deseni zaten
`test_engagement_transitions.py` içinde kurulu, yeni dosya açmak gereksiz
parçalanma yaratır).

## Dependencies

- `app.services.authorization.Principal`, `scoped_engagements`, `get_scoped_or_404`, `can`
- `app.services.engagement.transition_engagement` (transition_table, precondition/authorization sırası)
- `app.models.Engagement`, `Institution`, `InstitutionMember`, `Organization`, `OrganizationMember`
- Test altyapısı: `client` fixture (TestClient, `X-Debug-User-Id` header ile auth bypass — `test_engagement_transitions.py` tepesinde tanımlı, `conftest.py`'de değil, dosyaya özel)

## Migration Required?
Hayır — hiçbir model/şema değişikliği yok, sadece test fixture'ları ve test senaryoları ekleniyor.

## Risks
- (atdd.md'den taşındı) Kontrol sırası (scope-check → illegal-transition) testte
  doğrulanmadan varsayılmamalı — kod okumasında doğru görünüyor ama AC-S2 testi
  bunu somut olarak kanıtlayacak.
- (atdd.md'den taşındı) org_ids/org_admin_ids farkının gerçek DB fixture'ında
  doğru kurulması kritik: `org_admin_evan`'a organization_b'de sadece
  `role="MEMBER"` (ADMIN değil) ikinci bir `OrganizationMember` satırı eklemek
  gerekiyor — yanlış kurulursa test yanlış senaryoyu doğrular (false negative).
- MCP_DOCKER (Saga) hâlâ bağlı değil — `authz-test` skill'inin kendi MCP
  bağımlılığı varsa (henüz kontrol edilmedi) bu adımda tekrar karşılaşılabilir;
  `test-copilot`/`code-copilot` aşamasında teyit edilecek.

## Open Questions

Yok — mevcut kod deseni (fixture stili, `X-Debug-User-Id` auth bypass, hata
şeması) yeterince net; yeni fixture'ların nasıl kurulacağı yukarıda kararlaştırıldı.
