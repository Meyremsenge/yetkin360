# Test Diff — skillsignal-self-claim-uretimi
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar (yeni, red step)

- `backend/tests/test_skill_signals.py` — 7 sınıf, 10 test fonksiyonu.
- `backend/tests/authorization/test_skill_signals.py` — 3 sınıf, 7 test fonksiyonu.

İmplementasyon (SkillSignal modeli, migration, servis fonksiyonları,
`GET /talents/me/signals` route'u) hiçbiri yok — testler `SkillSignal`
import hatası ve/veya 404 ile kırmızı geçmesi beklenen klasik red step.

## AC → Test Eşlemesi

| AC | Test(ler) |
|---|---|
| AC-1 | `TestSkillClaimCreatesSignal::test_post_skills_creates_skill_signal` |
| AC-2 | `TestGetSkillSignalsHappyPath::test_get_signals_happy_path` |
| AC-3 | `TestGetSkillSignalsWithFilter::test_get_signals_with_skill_id_filter` |
| AC-4 | `TestGetSkillSignalsEmpty::test_get_signals_empty_200` |
| AC-5 | `TestSkillClaimDeleteLeavesSignalIntact::test_delete_claim_signal_remains` |
| AC-6 | `TestGetSkillSignalsFilterNonExistent::test_get_signals_filter_nonexistent_skill_200` |
| Append-only (Davranış Sözleşmesi + `.claude/rules/database.md`) | `TestSkillSignalAppendOnly::test_skill_signal_cannot_be_updated`, `test_skill_signal_cannot_be_deleted` |
| AC-S1 | `TestCrossTalentSignalIsolation::test_talent_a_queries_skill_only_b_claimed_gets_empty_list`, `test_talent_a_cannot_see_talent_b_signals_in_full_list` |
| AC-S2 | `TestPrincipalTalentIdFromSessionNotRequest::test_scoped_signals_uses_principal_talent_id_not_query_param`, `test_scope_respects_principal_talent_id_across_requests` |
| (ek) | `TestSignalAuthorizationEdgeCases` — 401 senaryoları |

Hata kodları (`SKILL_NOT_FOUND` vb.) ve response alanları tam eşleşmeyle
(`==`) doğrulanıyor, substring/`.lower()`/`or` kullanılmamış.

## Varsayımlar (sub-agent'ın kendi notu)
1. Principal enjeksiyonu: `X-Debug-User-Id` header (mevcut `test_skill_claim.py` deseniyle aynı).
2. `GET /talents/me/signals` route'u `backend/app/api/skill_signals.py`'de olacak (plan.md ile uyumlu).
3. `scoped_skill_signals()` `scoped_skill_claims()` deseninin birebir kopyası.
4. Append-only trigger `audit_events` migration emsali (`skill_signals_immutable`).
5. Response şeması atdd.md'deki `{"items":[{"skill":{...},"signals":[{...}]}]}` birebir.

## Beklenen Sonuç
Kırmızı (red) — `code-copilot` adımına kadar. Testler kendi bağımsız
fixture setlerini kuruyor (mevcut `test_skill_claim.py` fixture'larını
paylaşmıyor).
