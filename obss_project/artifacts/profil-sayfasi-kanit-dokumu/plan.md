# Plan — profil-sayfasi-kanit-dokumu
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (.tsx dosyaları + Görsel/UI kriteri dolu).
Discover/Design Direction bilinçli olarak atlandı — bu görev mevcut
`skills-section.tsx` deseninin BİREBİR tekrarı (yeni bir tasarım yönü yok),
UI henüz kodda yok (screenshot alınacak bir şey yok). Gerçek ekran görüntüsü
`code-copilot` sonrası, `verify`/Validate adımında Playwright ile alınacak.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/profil/page.tsx | Yeni `EvidenceSection` bölümünü `SkillsSection`'ın altına render edecek şekilde güncellenir | low |
| frontend/lib/api/client.ts | Yeni `getMySignals()` ve `getMyVerifiedExperiences()` fonksiyonları eklenir (mevcut `getMySkills` deseniyle, satır 333-335) | low |
| frontend/messages/tr.json | `profil` nesnesine yeni anahtarlar eklenir (`evidenceSection`, `emptySignalsMessage`, `emptyVerifiedExperiencesMessage`, `signalsLoadError`, `retryButton`, `selfClaimLabel`, `supersededLabel` vb.) | low |
| backend/app/services/authorization.py | Yeni `scoped_own_verified_experiences(session, principal)` fonksiyonu eklenir (satır ~296'daki `scoped_public_verified_experiences`'ın yanına) | low |

## New Files
| File | Purpose |
|------|---------|
| frontend/app/profil/evidence-section.tsx | Kanıt dökümü bölümü: skill signal grupları + verified experience kartları, `skills-section.tsx` (satır 1-30 fetch/render deseni) ile aynı yapı |
| frontend/app/profil/evidence-section.test.tsx | `skills-section.test.tsx` deseniyle (vi.mock + QueryClientProvider + waitFor) |
| backend/app/services/verified_experience.py | `list_own_verified_experiences(session, principal)` — `skill_signal.py::list_skill_signals`'ın aynı yapısı, `scoped_own_verified_experiences` kullanır |
| backend/app/api/verified_experiences.py | `GET /talents/me/verified-experiences` route — `backend/app/api/skill_signals.py`'nin birebir aynı yapısı (router, Pydantic response şeması, 401 kontrolü) |
| backend/tests/test_verified_experiences_authorization.py | AC-7-AC-12/AC-S1-S3 testleri — `test_institution_authorization.py`'deki tenant-izolasyon fixture desenine benzer, ama tek-talent-scope (cross-talent, unauthenticated, non-talent principal senaryoları) |

## Dependencies
- `app.services.authorization.scoped_skill_signals` / `scoped_own_verified_experiences` (yeni) — her ikisi de `principal.talent_id` ile filtreler, istemciden gelen hiçbir alana güvenmez.
- `backend/app/api/skill_signals.py` — response şeması ve 401 kontrol deseni (`principal.user_id is None or principal.talent_id is None → 401`) birebir örnek alınacak.
- `frontend/lib/api/client.ts::apiFetch()` — mevcut fetch wrapper, yeni fonksiyonlar bunun üzerine kurulur.
- `frontend/app/profil/skills-section.tsx` — TanStack Query (`useQuery`), boş durum, `role="alert"`/`aria-live` hata gösterimi deseni birebir örnek alınacak.

## Migration Required?
**Hayır.** `VerifiedExperience` modelinde zaten `ix_verified_experiences_talent_id` index'i var (`backend/app/models/verified_experience.py` satır 55) — yeni sorgu bu index'i doğrudan kullanır, ek index gerekmez. Yeni kolon/tablo yok.

## Risks
- atdd.md'den taşınan: sayfalama yok, tek talent'ın kayıt sayısı düşük varsayımına dayanıyor.
- `attested_by` alanı backend'de (`skill_signal.py` satır 71) HER ZAMAN `None` dönüyor — "SELF_CLAIM always has null attested_by" yorumu var ama kod ORG_ATTESTATION kaynaklı sinyaller için de her zaman `None` döndürüyor (henüz doldurulmamış). AC-1/AC-5'teki "attested_by varsa isim gösterilir" dalı pratikte bugün hiç tetiklenmeyecek — frontend'de yine de savunmacı şekilde koşullu render edilecek (gelecekte backend doldurursa otomatik çalışsın diye), ama bu bir mevcut backend sınırlaması, bu görevin kapsamında düzeltilmeyecek.

## Open Questions
1. ~~401 vs 404 tutarsızlığı~~ — **ÇÖZÜLDÜ (kullanıcı kararı):** Yeni `GET /talents/me/verified-experiences` ucunda atdd.md'nin öngördüğü **404** ayrımı (oturumsuz=401, oturumlu-ama-talent-değil=404) KORUNUR. `skill_signals.py`'deki mevcut 401-birleşik davranış BU GÖREVDE değiştirilmez — kardeş uçlar arasındaki tutarsızlık bilinçli olarak kabul edildi, ayrı bir görevle (tutarlılık temizliği) ele alınacak (bkz. spawn edilen görev).

Açık soru kalmadı.
