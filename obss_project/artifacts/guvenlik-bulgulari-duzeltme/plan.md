# Plan — guvenlik-bulgulari-duzeltme
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## ÖNEMLİ BULGU — kod keşfi sırasında çıktı
Jira açıklamaları bazı bulgular için **güncel değil görünüyor** — kod tabanında
ilgili düzeltmeler zaten var gibi duruyor. Ayrıntı "Open Questions"ta.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/verified_experience.py` | `generate_public_token()` tanımlı (satır 15) ama hiçbir çağrı noktası bulunamadı — çağırma noktası eklenmeli (IS-01, AC-1) | medium |
| `backend/app/api/engagements.py` | T4/T5/T8 geçiş tablosu (satır ~286-351) — kurumsuz DRAFT→ACTIVE (T4) geçişi yok, `reason` üzerine yazma ve uzunluk sınırı (IS-03, AC-3), T8 rolü (AUTHZ-03, AC-7) | high |
| `backend/app/services/evaluation.py` | Skill sinyali üretim yönü — TALENT_TO_ORG değerlendirmesinin STRONG sinyal üretip üretmediği kontrol edilecek (GUV-04, AC-5) | medium |
| `backend/app/services/attestation.py` | Tanıklıkta geçersiz `skill_id` davranışı (IS-05, AC-8); skill MERGE sonrası iddia/sinyal yönlendirme (IS-06, AC-9) ile ilişkili okuma yolları | medium |
| `backend/app/api/skill_signals.py` | Satır 85: `raise HTTPException(status_code=401, ...)` → 404'e çevrilecek (L-08, AC-11) | low |
| `backend/app/api/talent_skills.py` | `POST /talents/me/skills` geçersiz `claimed_level` → 400 validasyonu (VER-02, AC-10); muhtemelen `GET`/`DELETE` N+1 sorguları (L-09, AC-12) | medium |
| `backend/app/services/skill_claim.py`, `skill_signal.py` | N+1 sorgu düzeltmesi — JOIN/eager-load (L-09, AC-12); silinen iddiada sinyal filtreleme, `attested_by` hesaplama (IS-06, AC-9) | medium |
| `backend/app/services/skill.py` | `update_skill`: `parent_id` kaldırma, MERGED→DEPRECATED engeli (L-10, AC-13) | low |
| `backend/app/api/me.py` | `PATCH /talents/me`: `updated_at` elle set ediliyorsa kaldırılacak (L-06, AC-14) — **doğrulanmadı, dosyada `updated_at` string'i bulunamadı, tekrar kontrol gerekiyor** | low |
| `backend/app/api/public.py` | GUV-05 (AC-4, AC-S3) için revoke sonrası okuma filtresi — **mevcut `scoped_public_verified_experience_by_token()` zaten `visibility=='PUBLIC'` filtreliyor, ek değişiklik gerekip gerekmediği belirsiz (bkz. Open Questions)** | medium |

## New Files
Yok — tüm düzeltmeler var olan dosyalara.

## Dependencies
- `services/authorization.py`: `scoped_public_verified_experience_by_token()`, `scoped_attestations_for_engagement()`, `scoped_own_verified_experiences()` — mevcut desenle tutarlı yeni scoped sorgular bunlara eklenecek, çıplak `select(Model)` yazılmayacak.
- `tests/authorization/` altındaki mevcut dosyalar (`test_engagement_authorization.py`, `test_public_verification_authz.py`, `test_attestation_revoke_authorization.py`, `test_skill_signals.py` vb.) — yeni testler bu dosyalara eklenecek, pattern'leri takip edilecek.
- `can()`/`scoped_*()` merkezi yetkilendirme kuralı (CLAUDE.md + `.claude/rules/security.md`) — hiçbir yeni sorgu bunun dışına çıkmayacak.

## Migration Required?
Hayır — hiçbir AC yeni kolon/tablo gerektirmiyor. Tüm kolonlar (`public_token`, `revoked_at`, `parent_id`, `merged_into_id`, `updated_at`) zaten mevcut.

## Risks
- atdd.md'den taşınan: T4/T8 nihai rol kararı (K4/K5/K8/K10), IS-01/IS-02 üretim verisinde backfill belirsizliği.
- **Yeni:** Jira açıklamaları ile mevcut kod arasında tutarsızlık riski — bazı "bulgular" zaten düzeltilmiş olabilir; `code-copilot`'un zaten doğru olan kodu "düzeltmeye" çalışıp regresyon sokması riski var.

## Open Questions

Kod keşfi sırasında atdd.md'nin varsaymadığı 3 somut çelişki bulundu — `test-copilot`/`code-copilot` başlamadan önce netleşmeli:

1. **GUV-08 (AC-6, AC-S1/AC-S2) zaten düzeltilmiş görünüyor.** `services/engagement.py:179-184` zaten şunu yapıyor: `institution_id` uyuşmazlığında "Generic error message that doesn't reveal whether institution exists" yorumuyla tek tip `InstitutionMismatchError` fırlatıyor; kodda docstring zaten `AC-5, AC-S3` referansı veriyor (farklı bir AC numaralandırma şeması — muhtemelen önceki bir ATDD turundan kalma). Bu bulgu güncel mi, yoksa Jira bu düzeltmeden SONRA mı açıldı (ör. 400→201 farkı HTTP response seviyesinde hâlâ var mı, sadece exception mesajı mı düzeltildi)? Cevaba göre AC-6 ya kapsam dışı kalır ya da sadece HTTP response kod/gövde seviyesinde ek doğrulama gerekir.
2. **GUV-05 (AC-4, AC-S3)'ün "okuma filtrelenmiyor" iddiası şüpheli.** `services/authorization.py:325-349` (`scoped_public_verified_experience_by_token`) zaten `visibility == "PUBLIC"` filtreliyor ve docstring'i "Implements AC-1, AC-2, AC-3 (AC-S2), AC-6" diyor; `services/attestation.py:478-484`'teki `revoke_attestation` de `UPDATE ... WHERE revoked_at IS NULL` ile race-condition'a karşı korumalı ve kendi docstring'inde "AC-S2: Race condition handled" yazıyor. Soru: VerifiedExperience.visibility, bağlı Attestation revoke edildiğinde otomatik PRIVATE'e mi dönüyor, yoksa visibility PUBLIC kalıp sadece Attestation mı revoke ediliyor? İkincisiyse gerçek açık hâlâ var (VerifiedExperience kendi başına PUBLIC kalır) — ama konum (GUV-05'in işaret ettiği `attestation.py:408+`/`authorization.py:352-372`) ile gerçek kod satırları tam örtüşmüyor, `code-copilot`'un doğru yeri bulması için netleştirme lazım.
3. **`backend/app/api/me.py`'de `updated_at` elle set edildiğine dair kod bulunamadı** (L-06, AC-14) — grep sonucu boş döndü. `PATCH /talents/me` başka bir dosyada mı (ör. `talent_skills.py` veya farklı bir route), yoksa bu bulgu zaten düzeltilmiş mi?

Mevcut kodda zaten var olan `AC-S1`/`AC-S2`/`AC-S3` etiketleri, atdd.md'de threat-model'in ürettiği YENİ `AC-S1..AC-S6` ile **çakışıyor** (aynı etiket, farklı anlam). `test-copilot`/`code-copilot`'un karışmaması için atdd.md'deki güvenlik kriterlerini referanslarken Jira koduyla (ör. "AC-S4/GUV-04") birlikte anmak gerekecek — bu plan.md'de zaten öyle yapıldı.

## Kararlar (kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı)

1. **GUV-08 (AC-6):** Kapsam dışı — kod zaten tek tip `InstitutionMismatchError` fırlatıyor (oracle mesaj seviyesinde kapalı). Yeni davranış eklenmeyecek; sadece router'ın bu exception'ı 404'e çevirdiğini ve 400/201 ayrımının HTTP katmanında olmadığını doğrulayan bir regresyon testi eklenecek.
2. **GUV-05 (AC-4/AC-S3):** Davranış değişikliği YOK — `scoped_public_verified_experience_by_token()` zaten `visibility=='PUBLIC'` filtreliyor, `revoke_attestation` zaten race-condition korumalı. VerifiedExperience.visibility'yi Attestation revoke'unda otomatik PRIVATE'e çevirmek yeni bir mimari karar gerektirir ve atdd.md bunu talep etmiyor — sadece mevcut filtrenin çalıştığını kanıtlayan regresyon testi eklenecek.
3. **L-06 (AC-14):** Kapsam dışı — `me.py`'de `updated_at` elle set grep'i boş döndü, zaten düzeltilmiş kabul ediliyor. `code-copilot`'a tekrar arattırmak token israfı olur; `TimestampMixin` davranışını sabitleyen bir regresyon testi yeterli.

**Sonuç:** AC-6, AC-4/AC-S3 ve AC-14 "kod düzeltmesi" değil "regresyon testi" kategorisine taşındı — `test-copilot` bunları zaten-doğru-davranışı kilitleyen testler olarak yazacak, `code-copilot` bu üç madde için servis/API kodunu değiştirmeyecek.
