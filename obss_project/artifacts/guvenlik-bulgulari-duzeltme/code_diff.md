# Code Diff — guvenlik-bulgulari-duzeltme
_Reference: atdd.md, plan.md, test_diff.md_

4 paralel Haiku alt-ajanı ile implementasyon yazıldı, inceleme sırasında 2 kapsam aşımı bulunup 2 düzeltme turuyla giderildi.

## Değiştirilen Dosyalar → AC Eşlemesi

| Dosya | AC | Özet |
|---|---|---|
| `services/engagement.py`, `api/engagements.py` | AC-2 (IS-02), AC-3 (IS-03), AC-7 (AUTHZ-03) | T4 (kurumsuz DRAFT→ACTIVE) ve T8 (EVALUATED→VERIFIED, SUPERVISOR-only) geçişleri eklendi; `started_on`/`ended_on` transition payload'a eklendi; `reason` append-only + 1000 karakter sınırı |
| `services/verified_experience.py`, `models/verified_experience.py`, `services/attestation.py` | AC-1 (IS-01) | `generate_public_token()` artık VerifiedExperience oluşturulduğunda çağrılıyor (model-level default + attestation.py'de explicit çağrı) |
| `services/evaluation.py` | AC-5 (GUV-04), AC-8 (IS-05) | Sinyal üretimi SADECE ORG_TO_TALENT yönünde; TALENT_TO_ORG isteği **kabul edilir (201)** ama sinyal üretmez (düzeltme sonrası — ilk versiyon isteği tamamen 403 ile engelliyordu, kullanıcı kararıyla düzeltildi); geçersiz `skill_id` → 422 VALIDATION_ERROR |
| `services/skill_claim.py`, `services/skill_signal.py` | AC-9 (IS-06), AC-12 (L-09) | Silinen iddianın sinyali okuma yolunda filtreleniyor, `attested_by` doğru hesaplanıyor; `selectinload` ile N+1 giderildi |
| `api/skill_signals.py` | AC-11 (L-08) | 401 → 404 |
| `api/talent_skills.py` | AC-10 (VER-02) | `claimed_level` route içinde manuel validasyon → 400 (DB CHECK'e düşmeden, **sadece bu endpoint**) |
| `services/skill.py`, `api/admin.py` | AC-13 (L-10) | `parent_id` null'lanabilir; MERGED→DEPRECATED → 409 CONFLICT |
| `main.py` | — | (Geri alındı — bkz. Düzeltmeler) |

## Dokunulmayan (kasıtlı) AC'ler
AC-6/AC-S1/AC-S2 (GUV-08), AC-4/AC-S3 (GUV-05), AC-14 (L-06): plan.md kararına göre kod zaten doğruydu, implementasyon değişikliği yapılmadı — sadece regresyon testleri bunları kilitliyor.

## İnceleme Sırasında Bulunan ve Düzeltilen Kapsam Aşımları

1. **`main.py` global validation handler (KRİTİK):** Bir alt-ajan `RequestValidationError` handler'ını TÜM endpoint'ler için 422→400'e çevirmişti — `grep -r "== 422" backend/tests` ile 66 mevcut assertion'ın kırılma riski tespit edildi. **Düzeltme:** Global handler tamamen geri alındı (FastAPI default 422'ye döndü); AC-10'un gereksinimi `api/talent_skills.py` içinde SADECE `claimed_level` alanına özel manuel kontrolle çözüldü.
2. **`services/evaluation.py` TALENT'ın TALENT_TO_ORG gönderme hakkının tamamen kapatılması:** İlk implementasyon TALENT'ın hiçbir TALENT_TO_ORG değerlendirmesi gönderememesini (403) sağlıyordu — bu, AC-5'in gerçek kapsamını (sadece sinyal üretimini engellemek) aşıyordu ve mevcut `test_talent_can_post_talent_to_org_201` testini kırıyordu. **Kullanıcı kararı (B seçeneği):** istek kabul edilir (201), sadece sinyal üretilmez. `atdd.md` AC-5 ve Davranış Sözleşmesi buna göre güncellendi, çelişen test (`test_talent_talent_to_org_evaluation_returns_403_forbidden`) `test_talent_talent_to_org_evaluation_accepted_but_no_signal_generated` olarak yeniden yazıldı (2 düzeltme turu: önce mantık, sonra `SkillSignal.evaluation_id` diye var olmayan bir alana referans veren hatalı query düzeltildi — gerçek alanlar `source_type='EVALUATION'`/`source_id`).

## Diğer notlar
- Bir alt-ajan "circular import" sorunu bulup `generate_public_token()`'ı `models/verified_experience.py`'ye taşıdı — bu, başka bir alt-ajanın (IS-01) aynı fonksiyona yaptığı değişiklikle aynı dosyalarda çakışma riski taşıyordu; `git status` ile her iki dosyanın da tutarlı son hale geldiği doğrulandı.
- Hiçbir migration eklenmedi (plan.md'nin öngördüğü gibi).
- Hiçbir test dosyası alt-ajanlar tarafından değiştirilmedi (sadece orkestratörün dispatch ettiği düzeltme turları test dosyalarına dokundu, bu da test-copilot kapsamında kabul edilebilir çünkü gerçek bir AC çelişkisini çözüyordu).

## Sıradaki adım
`verify` — gerçek `pytest tests/authorization -q` + tam paket koşusu henüz yapılmadı. Bu rapor sadece statik inceleme + kapsam doğrulamasıdır.
