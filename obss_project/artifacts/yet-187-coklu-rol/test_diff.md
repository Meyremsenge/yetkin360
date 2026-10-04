# test_diff — yet-187-coklu-rol (red adımı)

Yeni dosyalar (hepsi `backend/tests/authorization/`, 74 test toplandı, henüz çalıştırılmadı; mevcut test dosyalarına dokunulmadı):

| Dosya | Test | Hedeflenen AC / matris satırı |
|---|---|---|
| test_multi_role_authorization.py | 44 (gerçek DB + `X-Debug-User-Id` ile gerçek `get_current_principal`, mock yok) | AC-1,2,3,4,5,7,8; AC-S1 (satır 16-19,21-24), AC-S2 (9,27,28,29), AC-S3 (13-15), AC-S4 (10-12), AC-S5 (5,6); satır 8, 31 |
| test_principal_roles_unit.py | 21 | `coordinator_institution_ids`, `engagement_relation` maskeleme, `scoped_*`/`can()` kind'dan bağımsızlığı (AC-5,6,S1,S3,S4,S5) |
| test_no_kind_authz.py | 8 | AC-6 statik AST koruması (1 tarama testi kırmızı olmalı + 7 tarayıcı öz-testi) |

## Açık notlar
- **Gevşek assert (8 yer):** `>= 400` / "403 veya 404" kullanan testler kod sonrası gerçek davranışa göre sıkılaştırılacak (assert gevşetme yasağı; bunlar zaten gevşek yazıldı, sıkılaştırmak yasaklanan şey değil). Sıkılaştırma kod sonrası ayrı bir test-copilot dağıtımıyla yapılır.
- Matris satır 20 (talent-tarafı eylemler) ve 21, 25, 26 önceki dosyada/mevcut testlerde kapsandı (alt-ajan raporu); satır 20'nin deliverable ve TALENT_TO_ORG kısmı ayrıca doğrulanacak.
- İlk alt-ajan koşusu oturum limitine takılıp yarıda kesildi; dosyalar sözdizimi olarak geçerli, eksikler ikinci dağıtımla tamamlandı.
- Dashboard (K2 → 200, X → 404) senaryosu için alt-ajan raporunda satır yok; kod sonrası kontrol edilecek.
