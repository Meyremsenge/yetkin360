---
task_slug: yet-72-attestation-revoke
jira_id: YET-72
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 50
  integration: 40
  e2e: 10
affected_modules:
  - backend/app/services/authorization.py (yeni scoped_attestations(), ownership-bazlı)
  - backend/app/services/attestation.py (yeni revoke_attestation())
  - backend/app/api/engagements.py veya yeni backend/app/api/attestations.py (POST /attestations/{id}/revoke)
  - backend/alembic/versions/ (yeni migration: skill_signals trigger'ına superseded_by_id istisnası)
---

# ATDD — yet-72-attestation-revoke

## Jira Kaynağı
[YET-72 — [PLAN 2.10] Attestation iptali (revoke) — append-only istisnası](https://kuyusuzyusuf123.atlassian.net/browse/YET-72)
Açıklama (Jira'dan birebir): "POST /attestations/{id}/revoke — revoked_at + zorunlu revoke_reason (append-only'nin tek istisnası). Sadece tanıklığı yapan kişi iptal edebilir."
Alt görevler: [YET-93](https://kuyusuzyusuf123.atlassian.net/browse/YET-93) (POST /attestations/{id}/revoke ucu), [YET-94](https://kuyusuzyusuf123.atlassian.net/browse/YET-94) (yetkilendirme testi — sadece tanıklığı yapan kişi iptal edebilir, başkası 403/404 alır).
Atanan: Meyrem (Jira görünen adı "Meyrsem").

AC kaynağı (STATE_MACHINE.md §6 + API.md §2.8 + DOMAIN.md D12, birebir):
- "Kurum tanıklığını geri çeker → `Attestation.revoked_at` + zorunlu gerekçe. Orijinal kayıt kalır."
- "SkillSignal: `superseded` olur, silinmez."
- "Revoke, bir durum geçişi değildir — `engagements.status` `VERIFIED` kalır, değişen `attestations` tablosudur."
- "Yalnız tanıklığı yapan kişi geri çekebilir."
- API.md: İstek `revoke_reason`, cevap `200`, hatalar `403, 404, 409 ALREADY_REVOKED`.

## Persona
Bir engagement için daha önce `POST /engagements/{id}/attestations` ile tanıklık göndermiş olan kişi (INST:COORD veya ORG_ADMIN — YET-70'te T8'i tetiklemeye yetkili roller) — kendi gönderdiği tanıklığı, bir hata/yanlış anlama nedeniyle geri çekmek istiyor.

## Hedef (Neden)
"Silinebilir doğrulama, doğrulama değildir" (STATE_MACHINE.md §6) — tanıklıklar asla fiziksel olarak silinmez, ama gerçek dünyada bir tanıklık hatalı/yanlış verilmiş olabilir. Revoke mekanizması, append-only'nin bütünlüğünü bozmadan (orijinal kayıt kalır, sadece `revoked_at`/`revoke_reason` eklenir) bu gerçek ihtiyacı karşılar.

## User Story
As a tanıklığı yapan kişi (attestor)
I want kendi gönderdiğim bir Attestation'ı geri çekmek
So that hatalı/yanlış bir tanıklık, öğrencinin profilinde "geri çekildi" notuyla işaretlenebilsin, silinmeden

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given bir `Attestation` mevcut ve henüz geri çekilmemiş (`revoked_at IS NULL`), When tanıklığı yapan kişi (`attestor_user_id == principal.user_id`) `POST /attestations/{id}/revoke` çağırır (`revoke_reason` dolu), Then `200` döner, aynı transaction içinde: `Attestation.revoked_at`/`revoke_reason` set edilir (append-only'nin belgelenmiş tek istisnası), ilgili `SkillSignal` kayıtları (`source_type=ATTESTATION`, `source_id=attestation.id`) için yeni bir "tombstone" `SkillSignal(strength=NONE, source_type=ATTESTATION, source_id=attestation.id, occurred_at=revoked_at)` eklenir ve eski sinyal(ler)in `superseded_by_id`'si bu yeni sinyale set edilir, `AuditEvent` yazılır.

2. [Critical] Given `Attestation` mevcut, When tanıklığı yapan kişi DIŞINDA biri (örn. aynı kurumun başka bir koordinatörü, veya `Attestation`'ın ait olduğu engagement'ın talent'ı) revoke dener, Then `403` döner (tanıklık zaten kendisine görünür/erişilebilir bir kaynak — S6 istisnası gibi, varlığı sızdırmak sorun değil çünkü kişi zaten Attestation'ın ilişkili olduğu engagement'a erişebiliyor olabilir; ama attestor değilse yetkisi yok).

3. [High] Given `Attestation` mevcut ama principal bu kaynağa (scoped_attestations üzerinden) hiç erişemiyor (örn. tamamen farklı bir kurum/organizasyondan), When revoke denenir, Then `404` döner (kaynağın varlığı sızdırılmaz).

4. [High] Given `attestation_id` geçersiz/yok, When revoke denenir, Then `404` döner.

5. [Critical] Given `Attestation` zaten geri çekilmiş (`revoked_at IS NOT NULL`), When aynı veya başka biri tekrar revoke dener, Then `409 ALREADY_REVOKED` döner, hiçbir yazma olmaz (mevcut `revoked_at` değişmez).

6. [High] Given `revoke_reason` boş/eksik, When revoke denenir, Then `422` döner, hiçbir yazma olmaz.

7. [Medium] Given revoke başarılı, When `Attestation` kaydı tekrar okunur (ör. `GET` ile, varsa), Then `claim_type`, `attestor_user_id`, `created_at` gibi orijinal alanlar **değişmemiştir** — sadece `revoked_at`/`revoke_reason` eklenmiştir (append-only'nin gerçek anlamda korunduğunun kanıtı).

8. [Medium] Given revoke başarılı, When `VerifiedExperience` kaydı (varsa, aynı engagement'a ait) okunur, Then kayıt **görünür kalır**, silinmez/değişmez — sadece "doğrulama geri çekildi" durumunun UI'da nasıl gösterileceği bu görevin kapsamı dışıdır (backend sadece `Attestation.revoked_at`'i expose eder, frontend ayrı).

9. [Critical] **AC-S1 (Repudiation/Info disclosure — revoke_reason PII riski)** Given revoke başarılı olur, When `AuditEvent` yazılır, Then `revoke_reason`'ın METNİ audit metadata'sına **yazılmaz** (sadece revoke olayının gerçekleştiği, kim tarafından, hangi attestation için loglanır — `revoke_reason`'ın kendisi CLAUDE.md'nin "loglara PII yazılmaz: ... private_note ..." kuralına tabi, serbest metin gerekçe kişisel/hassas bilgi içerebilir).

10. [Critical] **AC-S2 (Race condition — eşzamanlı çifte revoke)** Given aynı `Attestation` için iki eşzamanlı `POST /attestations/{id}/revoke` isteği (ikisi de `revoked_at IS NULL` durumunu görüyor), When ikisi de işlenmeye çalışılır, Then **sadece biri** `200` alır (`revoked_at`'i set eder), diğeri `409 ALREADY_REVOKED` alır — DB seviyesinde `UPDATE ... WHERE revoked_at IS NULL` koşuluyla korunur (rowcount==0 ise 409), asla iki kez set edilmez/üzerine yazılmaz.

11. [High] **AC-S3 (Tampering — trigger istisnasının kötüye kullanımı)** Given `attestations` tablosundaki trigger istisnası SADECE `revoked_at`/`revoke_reason` alanlarına, `skill_signals` tablosundaki istisna SADECE `superseded_by_id`'ye izin veriyor, When bir UPDATE denemesi bu izin verilen alanlar DIŞINDA başka bir alanı (ör. `attestations.claim_type`, `skill_signals.strength`) değiştirmeye çalışır, Then trigger YİNE hata fırlatır (istisna sadece belirtilen alan(lar) için, tüm satır için değil) — bu, `plan`/`code-copilot` adımında trigger SQL'i yazılırken doğrulanacak bir DB-seviyesi garanti, servis kodu bu alanların dışına asla UPDATE göndermez zaten ama DB'nin kendisi de ikinci savunma hattı olarak bunu reddetmeli.

## Threat Model
Çağrıldı — `AC-S1`, `AC-S2`, `AC-S3` yukarıdaki Acceptance Criteria'ya eklendi (threat-model skill'i, 2026-09-24).

STRIDE-lite değerlendirmesi:
- **S**poofing: Mevcut auth mekanizması değişmiyor — tetikleyici yok.
- **T**ampering: AC-S3 (trigger istisnasının sadece izin verilen alanlarla sınırlı kalması).
- **R**epudiation: AC-S1 (revoke_reason PII riski, ama olayın kendisi AuditEvent'te izleniyor — kim/ne zaman/hangi attestation kaydediliyor, sadece metin loglanmıyor).
- **I**nfo disclosure: AC-2/AC-3 (403 vs 404 ayrımı zaten atdd.md'de mevcut — attestor olmayan ama kaynağa erişimi olan biri 403, hiç erişimi olmayan biri 404 alır, kaynağın varlığı gereksiz sızdırılmaz).
- **D**oS: Bu uç tekil kaynak güncelleme, sınırsız çağrı riski minimal — MVP kapsamında rate-limit **kabul edilen risk** (bkz. Risks, önceki görevlerle tutarlı).
- **E**levation: AC-2 (attestor olmayan → 403), AC-S2 (race condition'da yetki bypass edilemez — her iki eşzamanlı istek de aynı yetki kontrolünden geçer, sadece ikinci DB seviyesinde 409 alır).

`authz-test` skill'i (AC-2/AC-3/AC-S2 yetkilendirme/ownership AC'leri ürettiği için) `plan`/`test-copilot` adımında IDOR testleri için ayrıca çağrılmalı.

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — attestor kendi tanıklığını geri çeker | `200` | Attestation.revoked_at/revoke_reason set edilir + tombstone SkillSignal + eski sinyal(ler) superseded_by_id set edilir + AuditEvent | `{"id":"...", "revoked_at":"2026-...", "revoke_reason":"Yanlış değerlendirilmiş"}` | AC-1 |
| 2 | Yetkisiz — attestor değil ama kaynağa erişimi var | `403` | Yok | `{"code":"FORBIDDEN","message":"Bu tanıklığı sadece yapan kişi geri çekebilir."}` | AC-2 |
| 3 | Kaynağa hiç erişimi yok (scope dışı) | `404` | Yok | `{"code":"NOT_FOUND","message":"Attestation bulunamadı."}` | AC-3 |
| 4 | attestation_id yok | `404` | Yok | `{"code":"NOT_FOUND",...}` | AC-4 |
| 5 | Zaten geri çekilmiş | `409` | Yok | `{"code":"ALREADY_REVOKED","message":"Bu tanıklık zaten geri çekilmiş."}` | AC-5 |
| 6 | revoke_reason boş | `422` | Yok | `{"detail":[{"loc":["body","revoke_reason"],"msg":"field required"}]}` | AC-6 |

Kısmi başarı: Bu uçta "kısmi başarı" oluşmaz — tüm yan etkiler (Attestation update + tombstone SkillSignal + superseded_by_id update + AuditEvent) TEK transaction içinde; biri başarısız olursa hepsi rollback olur, `200` yerine hata döner (500 değil — beklenmeyen bir DB hatası olursa mevcut `get_session` rollback deseni zaten devreye girer).
Hiçbir şey yapılamadı ama hata da yok: Oluşmaz — her istek ya `200` (gerçek değişiklik) ya da bir hata koduyla sonuçlanır.
Boş sonuç ↔ hata ayrımı: N/A (tekil kaynak güncelleme, liste dönmüyor).

## Test Strategy
Unit: 50% — yetki kontrolü (attestor mu değil mi), ALREADY_REVOKED kontrolü, tombstone SkillSignal üretim mantığı.
Integration: 40% — gerçek DB transaction'ı (revoked_at/revoke_reason update, append-only trigger'ın SADECE bu iki alana + skill_signals.superseded_by_id'ye izin verdiğinin doğrulanması — örn. `claim_type`'ı değiştirmeye çalışan bir test 403/trigger hatası almalı).
E2E: 10% — happy path (AC-1) + yetkisiz (AC-2) + zaten geri çekilmiş (AC-5) senaryoları.

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok
Diğer: `pytest tests/authorization -q` regresyonsuz kalmalı; append-only trigger'ın SADECE izin verilen alanlara (attestations: revoked_at/revoke_reason; skill_signals: superseded_by_id) izin verdiği ayrıca doğrulanmalı (mevcut alanlardan birini UPDATE etmeye çalışan bir test hâlâ trigger hatası almalı).

## Kapsam Dışı
- `VerifiedExperience`'ın UI'da "geri çekildi" notuyla nasıl gösterileceği — backend sadece veriyi expose eder, frontend ayrı bir görev.
- Revoke sonrası yeniden tanıklık gönderme (`POST /attestations` tekrar) — mevcut UNIQUE constraint (`engagement_id, attestor_user_id, subject_type`) zaten var, bu görev onu değiştirmiyor; revoke edilmiş bir Attestation'ın yerine yeni bir tanıklık gönderilip gönderilemeyeceği ayrı bir karar/görev (bu görevde UNIQUE constraint aynen kalır — yani revoke edilse bile aynı kişi aynı engagement'a ikinci kez tanıklık gönderemez, mevcut kısıt bunu zaten engelliyor).
- `DISPUTED` akışı (T9/T10) — ayrı, PLAN.md R.3.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/services/authorization.py` — yeni `scoped_attestations()` (ownership-bazlı: `attestor_user_id == principal.user_id`, mevcut `scoped_evidence()` deseniyle tutarlı).
- `backend/app/services/attestation.py` — yeni `revoke_attestation()` fonksiyonu.
- `backend/app/api/engagements.py` (veya yeni `attestations.py` — `plan` adımında proje deseni netleştirilecek) — `POST /attestations/{id}/revoke` route'u.
- `backend/alembic/versions/` — yeni migration: `skill_signals_before_update_delete()` trigger fonksiyonuna SADECE `superseded_by_id` değişikliğine izin veren bir istisna eklenir (mevcut `attestations` tablosundaki `revoked_at`/`revoke_reason` istisnasının aynısı — o trigger'ın SQL'i de incelenip aynı desen uygulanacak).
- `backend/app/models/audit.py` — mevcut `log_audit_event()` kullanımı (yeni alan gerekmez).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı — bu oturumda arama `backend/`, `docs/`, `obss_project/artifacts/` alt dizinleriyle sınırlı tutuldu.

## Rollback Beklentisi
Tüm yan etkiler (Attestation update + tombstone SkillSignal + superseded_by_id update + AuditEvent) tek transaction — biri başarısız olursa hepsi rollback, `Attestation.revoked_at` kısmi olarak set edilmiş kalmaz.

## Risks
- **Kabul edilen risk (DoS):** `POST /attestations/{id}/revoke` ucunda rate-limit yok — MVP/hackathon kapsamında tek VPS, threat-model STRIDE-lite değerlendirmesinde bilinçli olarak kapsam dışı bırakıldı.
- **Mimari çelişki (kullanıcıya soruldu, karar alındı):** `skill_signals` tablosundaki immutability trigger hiçbir istisna tanımıyordu — DOMAIN.md D12'nin "superseded olur" davranışı bu haliyle uygulanamazdı. Karar: yeni migration ile trigger'a `superseded_by_id` için istisna eklenecek (CLAUDE.md'nin "tek istisna" listesine bu alan da eklenmiş olacak — bu bilinçli bir genişletme, sessizce yapılmıyor, bu notla kayıt altına alınıyor).
- `attestations` tablosundaki mevcut trigger'ın (varsa) `revoked_at`/`revoke_reason` DIŞINDAKİ alanlara izin verip vermediği `plan` adımında doğrulanmalı — eğer trigger yoksa (sadece CHECK constraint varsa), append-only'nin uygulama katmanında (servis fonksiyonunda, sadece bu iki alanı UPDATE eden bir sorgu ile) korunması gerekir.

## Assumptions
- **Tombstone SkillSignal deseni (varsayım):** STATE_MACHINE.md/DOMAIN.md revoke'ta yeni bir SkillSignal oluşturulacağını AÇIKÇA söylemiyor, sadece "superseded olur" diyor. `superseded_by_id`'nin anlamlı olabilmesi için (bir satırın "hangi sinyalle değiştirildiğini" göstermesi gerektiği için) revoke'ta `strength=NONE` ile bir tombstone sinyal oluşturulacağı ve eski sinyal(ler)in bu tombstone'a `superseded_by_id` ile işaret edeceği varsayıldı. Bu, en tutarlı yorum ama **kullanıcı onayı gerektiren bir varsayım** — Hard Stop'ta gösterilecek.
- Revoke ucu, engagement'ın kendisini DEĞİL, `Attestation` kaydını hedefliyor (`/attestations/{id}/revoke`, `/engagements/{id}/...` değil) — API.md'nin URL şablonuyla birebir.

## Unknowns
- Birden fazla `SkillSignal` aynı `source_id=attestation.id`'ye sahip olabilir mi (ör. hem ana ATTESTATION sinyali hem opsiyonel skill_id'li bir tane)? YET-70/71'deki implementasyona göre bir Attestation başına en fazla 1 SkillSignal üretiliyor (skill_id verilmişse) — bu görevde "ilgili TÜM SkillSignal kayıtları" ifadesi bu tekil kaydı kapsıyor, `plan` adımında kod okunarak kesinleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Persona/hedef → attestor'un kendi tanıklığını geri çekmesi, append-only bütünlüğü korunarak (kullanıcı mesajından + STATE_MACHINE.md §6)
2. Happy path/edge case'ler → yukarıdaki AC-1..AC-8 (kullanıcı mesajından + API.md §2.8)
3. Yetkilendirme → sadece attestor (STATE_MACHINE.md'den birebir: "Yalnız tanıklığı yapan kişi geri çekebilir")
4. Mimari çelişki (skill_signals trigger) → kullanıcıya soruldu, "trigger'a istisna ekle" kararı alındı (bu oturumda, atdd öncesi)
5. Tombstone SkillSignal deseni → varsayım, Hard Stop'ta kullanıcı onayı bekleniyor
6. Test oranı → 50/40/10 (önceki görevlerle tutarlı varsayılan)
7. Benchmark → coverage 90% (yetkilendirme-ağırlıklı görev için standarttan yüksek, önceki attestation görevleriyle tutarlı)
