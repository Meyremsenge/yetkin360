# Test Diff — guvenlik-bulgulari-duzeltme
_Reference: atdd.md, plan.md_

4 Haiku alt-ajanı (paralel, arka plan) ile yazıldı. `git status --short backend/tests/authorization` ile doğrulandı: 8 dosya değiştirildi, 1 yeni dosya oluşturuldu.

## Değiştirilen/Oluşturulan Dosyalar → AC Eşlemesi

| Dosya | AC | Beklenen durum |
|---|---|---|
| `test_engagement_authorization.py` | AC-3 (IS-03, T4 geçişi, reason append/limit) | RED (endpoint yok) |
| `test_engagement_authorization.py` | AC-7 (AUTHZ-03, T8 SUPERVISOR vs ORG_ADMIN) | RED (endpoint yok) |
| `test_engagement_authorization.py` | AC-6 + AC-S1/AC-S2 (GUV-08, oracle kapatma) | GREEN (regresyon, kod zaten doğru) |
| `test_public_verification_authz.py` | AC-1 (IS-01, generate_public_token çağrılmıyor) | RED (implementasyon yok) |
| `test_attestation_revoke_authorization.py` | AC-4 + AC-S3 (GUV-05, revoke sonrası filtre) | GREEN (regresyon) |
| `test_verified_experiences_authorization.py` | AC-4 + AC-S3 (GUV-05, liste tutarlılığı) | GREEN (regresyon) |
| `test_evaluation_authorization.py` | AC-5 + AC-S4 (GUV-04, kendine sinyal engeli) | RED |
| `test_evaluation_authorization.py` | AC-8 (IS-05, geçersiz skill_id → 422) | RED |
| `test_skill_claim_authorization.py` | AC-9 (IS-06, silinen iddiada sinyal filtresi) | RED |
| `test_skill_signals.py` | AC-11 + AC-S6 (L-08, 401→404) | RED |
| `test_talent_authorization.py` | AC-10 (VER-02, claimed_level → 400) | RED |
| `test_talent_authorization.py` | AC-14 (L-06, updated_at) | GREEN (regresyon) |
| `test_skill_update_authorization.py` (yeni) | AC-13 (L-10, parent_id/MERGED→DEPRECATED) | RED |

## 5. dispatch (boşluk kapatma)
İlk 4 dispatch'te AC-2 (IS-02) ve AC-12 (L-09) atlanmış bulundu (kapsam kontrolünde yakalandı). 5. bir Haiku alt-ajanı dispatch edildi:

| Dosya | AC | Beklenen durum |
|---|---|---|
| `test_engagement_authorization.py` (`TestStartedOnEndedOnTransition`, 3 test) | AC-2 (IS-02, started_on/ended_on API alanı, tarih sırası 400) | RED |
| `test_skill_claim_authorization.py` (`TestSkillClaimListingPerformance`, `TestSkillSignalListingPerformance`, 2 test + `query_counter` fixture) | AC-12 (L-09, N+1 sorgu sayacı) | RED |

**Düzeltme notu:** Alt-ajan raporunda `query_counter` fixture'ının `conftest.py`'ye eklendiğini iddia etti; `git status --short backend/tests/authorization/conftest.py` boş döndü — fixture aslında `test_skill_claim_authorization.py`'nin içine yazılmış (grep ile doğrulandı). Raporla gerçek diff'in örtüşmediği bir örnek — bu yüzden her dosya `git status`/`grep` ile tek tek doğrulandı, salt alt-ajan raporuna güvenilmedi.

## Tüm 14 Jira bulgusu + 6 AC-S için kapsam tam
Artık AC-1..AC-14 ve AC-S1..AC-S6'nın tamamı en az bir test fonksiyonuna bağlı. `code-copilot`'a geçiş için engel yok.

## Not
Her alt-ajan "GREEN beklenen" regresyon testlerini de yazdı (AC-6, AC-4, AC-14) — bunlar implementasyon değişmeden şu an çalıştırılabilir, gerçek pytest koşusu `verify` adımında yapılacak (bu adımda koşulmadı, sadece dosya varlığı/kapsam doğrulandı).
