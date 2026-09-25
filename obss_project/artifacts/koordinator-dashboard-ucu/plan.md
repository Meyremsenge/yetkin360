# Plan — koordinator-dashboard-ucu
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev — atdd.md'nin
Etkilenen Dosyalar/Benchmark bölümlerinde .tsx/.jsx/.css veya Görsel/UI
kriteri yok).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/app/services/engagement.py | Yeni `get_coordinator_dashboard(session, principal, institution_id)` servis fonksiyonu — mevcut `scoped_engagements`, `EngagementNotFoundError`/`TransitionForbiddenError` desenini izler (bkz. `transition_engagement` satır 205+) | low |
| backend/app/api/institutions.py | Yeni `GET /institutions/{institution_id}/dashboard` route + `DashboardResponse`/`DashboardEngagementItem` Pydantic şemaları (mevcut `InstitutionResponse` desenini izler) | low |
| backend/tests/test_institution_authorization.py | AC-S1–AC-S4 negatif testleri (cross-tenant 404, TALENT/ORG_MEMBER 404, oturumsuz 401) — mevcut dosyanın deseni izlenir | low |
| backend/tests/test_institution.py (veya yeni `test_coordinator_dashboard.py`) | AC-1, AC-5, AC-6, AC-8 pozitif/happy-path testleri | low |

## New Files
Yok — mevcut `institutions.py`/`engagement.py` dosyalarına eklenecek (ayrı bir `dashboard.py` gerekmiyor; path zaten `/institutions/{id}/...` altında ve mevcut kurum uçlarıyla aynı router).

## Dependencies
- `app.services.authorization.scoped_engagements(session, principal)` — COORDINATOR/INST_ADMIN için zaten `institution_id in principal.institution_ids` filtresi uyguluyor (backend/app/services/authorization.py:183-208). Yeni fonksiyon bunun üzerine `status.in_(["PENDING_APPROVAL","PENDING_EVALUATION"])` filtresi ekleyecek — **AC-S3 gereği institution_id filtresi asla URL'den değil bu fonksiyon üzerinden principal'dan gelmeli.**
- `app.services.authorization.scoped_institutions(session, principal)` + `get_scoped_or_404` — institution_id'nin principal scope'unda olup olmadığını AC-S1/AC-S2 için doğrulamak üzere `institutions.py`'deki `invite_member_endpoint`/`approve_link_request_endpoint` ile aynı desen (404, `institution_id not in principal.institution_ids` kontrolü önce).
- `app.api.deps.get_current_principal` — 401 kontrolü mevcut route'lardaki `if principal.user_id is None: raise HTTPException(401, ...)` deseniyle aynı.
- Response şeması: `PostEngagementResponse`'daki gibi ayrı Pydantic modeli (`from_attributes = True`), ORM `Engagement` nesnesi doğrudan dönülmez (CLAUDE.md kuralı).

## Migration Required?
**Evet — ama bu adımda OLUŞTURULMAYACAK, önce kullanıcı onayı gerekiyor** (CLAUDE.md: "Migration oluşturma veya uygulama" açık onay listesinde). Gereken: `ix_engagements_institution_id_status` (institution_id, status) index + `ix_engagements_pending_evaluation` partial index (`WHERE status='PENDING_EVALUATION'`). MVP performans hedefi (<200ms) bu index'lere dayanıyor (final-analiz §14, atdd.md Benchmark). Endpoint index olmadan da doğru çalışır (sadece daha yavaş sorgu) — bu yüzden migration'ı ayrı bir onay adımı olarak kullanıcıya sorulacak, code-copilot onsuz da doğru davranışı üretebilir.

## Risks
- atdd.md'den taşınan: sayfalama yok — kurum başına engagement sayısı düşük varsayımı kabul edilmiş risk.
- Migration onayı gecikirse endpoint index'siz devreye girip küçük ölçekte sorun çıkarmaz, ama büyüdükçe (V2) yeniden ele alınmalı.
- Yeni bulunan risk yok — mevcut `scoped_engagements`/`scoped_institutions` deseni doğrudan yeniden kullanılabiliyor, ek bir yetkilendirme yüzeyi açılmıyor.

## Open Questions
Yok — atdd.md ve kod keşfi arasında çelişki veya belirsizlik çıkmadı; response şeması (Assumptions'ta işaretliydi) `PostEngagementResponse` deseniyle tutarlı şekilde netleşti.
