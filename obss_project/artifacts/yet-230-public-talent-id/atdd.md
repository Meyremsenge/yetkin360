---
task_slug: yet-230-public-talent-id
jira_id: YET-230
saga_task_id: null
priority: low
threat_model: done
coverage_target: 100 (değişen satırlar)
test_strategy:
  unit: 0
  integration: 100
  e2e: 0
affected_modules:
  - backend/app/api/public.py
  - backend/app/services/authorization.py
  - frontend/lib/api/public.ts
---

# ATDD — YET-230 (L-05)

## Jira Kaynağı
YET-230 — "L-05: Public profil talent_id sızdırıyor, /v/{token} silinmiş talent'ı filtrelemiyor".
Açıklama (birebir): "Konum: api/public.py. talent_id (iç UUID) döndürülüyor, ORG üyesi bunu POST /engagements'ta kullanabilir (GUV-08 ile ilişkili)."

## Sonda bulgusu (kod okuma)
- `GET /public/talents/{slug}` yanıtı `talent_id` (iç UUID) döndürüyor = sızıntı bu uçta.
- `GET /public/v/{token}` zaten `talent_id` döndürmüyor (mevcut AC-S4 testleri); asıl sorun: `scoped_public_verified_experience_by_token` talent profilinin `deleted_at`'ine bakmıyor → silinmiş talent'ın deneyimi doğrulama linkiyle görünür kalıyor. `/talents/{slug}` ucu `deleted_at IS NULL` filtreler; iki public uç tutarsız.

## Persona / Hedef
Anonim ziyaretçi (ve kötü niyetli ORG üyesi). İç kimlikler public yüzeyden çıkmalı; silinmiş kişinin public izi kalmamalı.

## Acceptance Criteria
1. [Critical] Given PUBLIC profil, When GET /public/talents/{slug}, Then 200 ve anahtarlar yalnız {display_name, verified_experiences}; yanıtta `talent_id` (ve talent/user UUID'si) yok.
2. [Critical] Given talent profili soft-deleted (deleted_at set) ve VE PUBLIC token'lı, When GET /public/v/{token}, Then 404 VERIFICATION_NOT_FOUND, olmayan token'la birebir aynı gövde (request_id hariç).
3. [High] Given silinmemiş talent + PUBLIC VE, When GET /public/v/{token}, Then 200 (regresyon; mevcut alanlar değişmez).
4. [High] Given silinmiş talent'ın PUBLIC profili, When GET /public/talents/{slug}, Then 404 TALENT_NOT_FOUND (mevcut davranış sabitlenir).
5. [Medium] Frontend `getPublicProfile` tipi ve `/p/[slug]` fixture'ı `talent_id` içermez; typecheck/test yeşil.

## Davranış Sözleşmesi
| # | Durum | Dönen | Yan etki | Kullanıcı görür | AC |
|---|---|---|---|---|---|
| 1 | PUBLIC profil | 200, talent_id yok | yok | profil | AC-1 |
| 2 | slug yok / PRIVATE / silinmiş | 404 TALENT_NOT_FOUND | yok | bulunamadı | AC-4 |
| 3 | token yok / PRIVATE / **talent silinmiş** | 404 VERIFICATION_NOT_FOUND (aynı gövde) | yok | bulunamadı | AC-2 |
| 4 | geçerli token | 200 | yok | doğrulama sayfası | AC-3 |
| 5 | DB hatası | 500 (mevcut) | yok | genel hata | kapsam dışı |
Satır sildim: 4xx girdi doğrulama (path string, her değer 404), zaman aşımı/kısmi başarı (salt-okuma, tek sorgu). "Hiçbir şey yapılamadı ama hata yok" yok: sonuç ya 200 ya 404. Boş sonuç↔hata: silinmiş/yok/PRIVATE kasıtlı ayırt edilmez (numaralandırma koruması).

## Tehdit modeli (özet, AC-S)
- AC-S1 [Critical] Silinmiş talent ile olmayan token yanıtı birebir aynı (varlık/silinme oracle'ı yok); tek sorgu (join), ek dal yok.
- AC-S2 [High] İç talent UUID'si hiçbir public yanıtta yok (iki uç da, response şeması + JSON anahtarı taraması).
- AC-S3 [Medium] POST /engagements, public sayfadan elde edilebilecek tanımlayıcıyla hedef talent seçemez: talent_id artık public'ten elde edilemez; ayrıca engagement açma yetkisi GUV-08 (ayrı görev).

## Kapsam dışı
GUV-08 (yabancı talent'a engagement spam), PublicVerifiedExperienceResponse.id (VE UUID'si, engagement ucunda kullanılamaz), users.deleted_at/status=DELETED sahibinin public gizlenmesi (şu an hiçbir kod yolu set etmiyor; takip), migration yok.

## Etkilenen yerler
public.py (şema + ), authorization.py `scoped_public_verified_experience_by_token` (talent profile join + deleted_at IS NULL), frontend public.ts + p/[slug] testi; sözleşme değişikliği: test_public_profile.py, test_public_profile_authz.py'deki "talent_id var" iddiaları sızıntıyı kodluyordu, güncellenecek.

## Rollback
Salt-okuma değişiklik; geri alma = commit revert.

## Assumptions
- "Silinmiş talent" = `talent_profiles.deleted_at IS NOT NULL` (profil modelinin tek soft-delete işareti; /talents/{slug} ile aynı).
- Frontend `talent_id` kullanmıyor (grep: yalnız tip + test fixture).

## Sorular ve Cevaplar
Sonnet alt-ajanı kullanılmadı (kullanıcı talimatı: alt-ajan yok); sorular kod okumasıyla cevaplandı, kullanıcıya soru kalmadı.
