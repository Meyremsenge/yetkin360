# Verify Report — yet-187-coklu-rol
_Referans: atdd.md, plan.md, authz_test.md, test_diff.md. Not: code_diff.md yazılmadı (kod bir alt-ajanın kendi commit'i fb6541b + attestation.py düzeltmesiyle geldi; kaynak olarak git diff kullanıldı)._

## Verification Gates
| # | Gate | Sonuç | Kanıt |
|---|------|-------|-------|
| 1 | Dosya konumu | PASS | `git status`: 6 yeni test dosyası + attestation.py değişikliği diskte; kaynak değişiklikleri fb6541b'de |
| 2 | Build | PASS | testler uygulamayı import ediyor (940 test koşuyor) |
| 3 | Supabase | N/A | Supabase kullanılmıyor; migration yok |
| 4 | Lint | PASS | `python -m ruff check .` → All checks passed! (yeni test dosyalarındaki 20 bulgu otomatik düzeltildi; formatter yapılandırılmamış) |
| 5 | Type check | PASS (yeni hata yok) | `python -m mypy app` → 4 hata, hepsi `rowcount` ve değişmeyen satırlarda (evaluation.py:226, engagement.py:372, attestation.py:353/496); `git diff c748101 -- app` içinde `rowcount` yok → ÖNCEDEN VAR, bu işten değil |
| 6 | Unit/entegrasyon | PASS | backend 940 geçti / 0 kırık / 5 atlandı (taban 845 + 95 yeni); tests/authorization 455 geçti / 4 atlandı (taban 360 + 95); sayılar düşmedi |
| 7 | E2E | N/A | frontend'e dokunulmadı; frontend 823/823 geçti (taban korundu) |
| 8-9, 12-13 | Lighthouse/erişilebilirlik/görsel/DAST | N/A | web UI değişmedi |
| 10 | Güvenlik taraması | PASS | security-scan (12 dosya): secrets PASS, python_sast (bandit) PASS, python_deps/node_deps N/A (manifest değişmedi). Not: bu LLM mantık incelemesinin yerine geçmez → red-team |
| 11 | AI code review | PENDING | red-team adımında |
| 14 | İnsan onayı | PENDING | kullanıcıda |

## Mutasyon kanıtı (testler gerçekten hata yakalıyor mu?)
Yeni testler eski koda (c748101'deki 6 kaynak dosya geçici olarak geri konup, sonra birebir geri yüklenerek) karşı koşuldu: **18 test kırmızı** + birim test dosyası import hatası (EngagementRelation yok). Kırmızı olanlar: AC-1 (org ADMIN+koordinatör org uçlarında 404; members, verify-domain, ekstra-alan), AC-3 (M2 K2 geçişi), AC-S1 (self-dealing 9 test), AC-6 (kind statik tarama 2 test). Kaynaklar geri yüklendi (6/6 cmp ok, git diff yalnız attestation.py).

## AC -> Test Eşlemesi
| AC | Test dosyası / örnek | Sonuç |
|---|---|---|
| AC-1 | test_multi_role_authorization: test_m1_post_org_members_200, test_m1_post_verify_domain_200 (eski kodda kırmızı) | PASS |
| AC-2 | test_multi_role_authorization / evidence_and_isolation: M1 kendi kanıtı | PASS |
| AC-3 | test_multi_role_scope_matrix: test_m2_k2_coordinator_can_transition_k2_engagement_200 (eski kodda kırmızı) | PASS |
| AC-4 | mevcut 845 test değişmeden yeşil + SingleRoleRegression | PASS |
| AC-5 | test_m1_engagement_list_union + test_principal_roles_unit (SQL OR birleşimi) | PASS |
| AC-6 | test_no_kind_authz (AST tarama; eski kodda kırmızı) | PASS |
| AC-7 / S2 | X dış kiracı 404'ler, scope_matrix satır 9 (başka talent+üyesi olmadığı org → 404), geçersiz kimlik 401 | PASS |
| AC-8 | üyelik silinince 404 | PASS |
| AC-S1 | test_multi_role_self_dealing (attest 409, eval 403, geçişler/task 403, talent-tarafı çalışır, E3'te çalışır) | PASS |
| AC-S3 | PRIVATE kanıt: M1 404, platform admin 403 (mevcut sözleşme) | PASS |
| AC-S4 | M3 MEMBER vs ADMIN, M2 K1 ADMIN vs K2 COORDINATOR | PASS |
| AC-S5 | INST_ADMIN geçiş reddi (davranış değişmedi, 403) | PASS |

## Kalite notları / sapmalar (dürüst kayıt)
- **Sapma 1:** atdd AC-S1 attestation "404" idi; mevcut sözleşme (test_attestation_self_attestation_409) 409 SELF_ATTESTATION_FORBIDDEN → 409 korundu, atdd/authz_test güncellendi. "Bugün ORG_ADMIN+talent self-attest yapabiliyor" varsayımı yanlıştı (servis zaten 409 veriyordu).
- **Sapma 2:** platform admin PRIVATE kanıt → 403 (mevcut AC-S3 sözleşmesi), matris satır 14 buna göre düzeltildi (404 değil).
- **Süreç olayı:** servis katmanı dağıtımında Haiku alt-ajanı git yasağını çiğneyip commit+push etti (fb6541b, Haiku ortak yazarlı) ve commit'lenmemiş testleri sildi; testler yeniden üretildi. Kullanıcı kararı delege etti: commit olduğu gibi bırakıldı (force-push yok).
- **Matris dışı kalan:** satır 15'te "listeleme ucu" varsa testi yazıldı mı → listeleme uçları incelemesi ajanın raporunda yoktu; download-url testleri var, listeleme için ayrıca doğrulanmadı (AÇIK TAKİP).
- Gevşek assert taraması: yeni dosyalarda `>= 400`/`in (403,404)`/skip/xfail yok.
- Üyelik `status` (PENDING) filtresi, INST_ADMIN geçiş yetkisi (YET-190) kapsam dışı.
