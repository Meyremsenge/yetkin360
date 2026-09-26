# test_diff.md — profil-sayfasi-kanit-dokumu

## Oluşturulan Dosyalar
- `frontend/app/profil/evidence-section.test.tsx` — YENİ, 13 test fonksiyonu
- `backend/tests/test_verified_experiences_authorization.py` — YENİ, 5 test fonksiyonu + fixture'lar

## AC → Test Eşleştirme

### Frontend (`evidence-section.test.tsx`)
| AC | Test(ler) |
|---|---|
| AC-1 | Mount → `getMySignals()` çağrılır; sinyaller skill'e göre gruplu, alanlarıyla render edilir; `occurred_at` azalan sırada |
| AC-2 | Sinyal yoksa boş durum mesajı (hata değil) |
| AC-3 | `getMySignals()` reddedilirse `role="alert"` + "Tekrar dene"; retry tekrar çağırır |
| AC-4 | `superseded:true` listede kalır, "Geçersiz kılındı" görünür |
| AC-5 | `attested_by:null` → "Kendi beyanı"; isimli ile görsel ayrışma |
| AC-6 | Metinler düz metin render edilir (dangerouslySetInnerHTML kontrolü) |
| AC-12 | Bir sorgu hata verirken diğeri etkilenmez (bağımsız useQuery, iki yönlü test) |

### Backend (`test_verified_experiences_authorization.py`)
| AC | Test |
|---|---|
| AC-7 | `test_ac7_authenticated_talent_gets_own_verified_experiences` — PRIVATE dahil tüm kayıtlar + tüm alanlar |
| AC-8 | `test_ac8_talent_with_no_verified_experiences_returns_empty_list` — 200 + `{items:[]}` |
| AC-9/AC-S1 | `test_ac9_ac_s1_talent_a_cannot_see_talent_b_records` — cross-talent sızıntı yok (tam substring kontrolü) |
| AC-10/AC-S2 | `test_ac10_ac_s2_unauthenticated_request_returns_401` |
| AC-11/AC-S3 | `test_ac11_ac_s3_talent_profile_required_returns_404_not_401` — talent'sız principal 404 (401 değil) |

## Durum
RED (beklenen) — component (`evidence-section.tsx`), `getMySignals`/`getMyVerifiedExperiences` client fonksiyonları, backend route/servis henüz yok.

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar (orkestratör tarafından, dispatch öncesi ikinci bir Haiku turuyla)
- **Yanlış endpoint path'i**: Backend testi `/api/v1/talents/me/verified-experiences` kullanıyordu — projede `/api/v1` öneki YOK (kardeş uç `skill_signals.py`'nin gerçek path'i `/talents/me/signals`, mevcut testlerle doğrulandı). 5 satır `/talents/me/verified-experiences`'a düzeltildi.
- **Yanlış sayım**: `test_ac9_ac_s1_...` testinde `talent_a`'ya sadece 1 fixture (`verified_exp_a1_private`) veriliyor ama `assert len(items) == 2` yazılmıştı — doğru implementasyon bu testte FAIL ederdi. `1`'e düzeltildi.

## Yan bulgu (ayrı görev olarak kaydedildi, bu görevin kapsamında değil)
`test_skill_claim_authorization.py:190`'da GÖRÜLDÜ Kİ `/talents/me/skills` ucu talent'sız principal için zaten **404** dönüyor — bu, `skill_signals.py`'nin 401-birleşik davranışının proje genelinde bir istisna değil, tutarsızlık olduğunu doğruluyor. Daha önce spawn edilen `task_4d23a5ea` (skill_signals.py'yi 404'e hizalama) görevi bu bulguyla daha da güçleniyor.
