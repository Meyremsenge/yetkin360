---
task_slug: yet-69-degerlendirme-formu-semasi
jira_id: YET-69
saga_task_id: null
priority: high
threat_model: not-applicable  # 5b adımına bakınız — bu ATDD'de threat-model TETİKLENDİ, aşağıda ayrı bölümde işlendi
coverage_target: 80
performance_target: "<300ms (P95)"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/models/evaluation.py (yeni)
  - backend/app/schemas/evaluation.py (yeni)
  - backend/app/services/evaluation.py (yeni)
  - backend/app/services/engagement.py (transition_table'a PENDING_EVALUATION→EVALUATED eklenir)
  - backend/app/api/engagements.py (POST /engagements/{id}/evaluation eklenir)
  - backend/alembic/versions/ (yeni migration — kullanıcı onayı gerekir)
  - backend/tests/test_evaluation.py (yeni)
  - backend/tests/authorization/test_evaluation_authz.py (yeni)
---

# ATDD — yet-69-degerlendirme-formu-semasi

## Jira Kaynağı
[YET-69 — [PLAN 2.7] Değerlendirme formu şeması (yetkinlik + davranış + NOT_OBSERVED)](https://kuyusuzyusuf123.atlassian.net/browse/YET-69)
Açıklama (Jira'dan birebir): "Evaluation modeli (direction ORG_TO_TALENT/TALENT_TO_ORG, items[], private_note), POST /engagements/{id}/evaluation. private_note talent'a asla dönmez."

Alt görevler:
- [YET-86 — Evaluation modeli (direction, items[], private_note) + migration](https://kuyusuzyusuf123.atlassian.net/browse/YET-86)
- [YET-87 — POST /engagements/{id}/evaluation ucu + private_note'un talent'a asla dönmediği testi](https://kuyusuzyusuf123.atlassian.net/browse/YET-87)

İlgili ama bu göreve **dahil olmayan** Jira kayıtları (kapsam sınırı için referans):
- YET-88 — "T8 (EVALUATED→VERIFIED) tek transaction: Attestation + VerifiedExperience snapshot + SkillSignal + AuditEvent" (PLAN 2.8)
- YET-75 / YET-100 — Frontend değerlendirme formu (PLAN 2.13)
- YET-102 — Uçtan uca duman testi (PLAN 2.14)
- YET-81 — "T5 (ACTIVE→PENDING_EVALUATION)" (tamamlandı, PLAN 2.6'nın bir parçası olarak zaten uygulanmış: `backend/app/services/engagement.py:286`)

**Kritik bulgu (bu ATDD sürecinde ortaya çıktı, kullanıcıyla teyit edildi):** Jira'da durum geçişi numaralandırması (T5, T8, …) taranınca T7'ye (`PENDING_EVALUATION → EVALUATED`) karşılık gelen **ayrı bir Jira görevi bulunamadı**. YET-88 (T8) doğrudan `EVALUATED` durumunu ön koşul kabul ediyor; yani birisi bu geçişi tetiklemezse YET-88 hiçbir zaman çalışacak veri bulamaz. Kullanıcıyla (Meyrem) bu boşluk konuşuldu — takım arkadaşının hâlihazırda YET-88 üzerinde çalışıyor olabileceği belirtildi. **Karar: T7 geçişi bu görevin (PLAN 2.7 / YET-69) kapsamına dahil edildi**, aşağıdaki AC-6/AC-7'de yer alıyor.

## Persona
- **Org üyesi / süpervizör (ORG_TO_TALENT değerlendirmeyi dolduran taraf):** Stajyerin çalıştığı kurumda, engagement'a atanmış kişi. Staj/proje bitince zorunlu değerlendirme formunu doldurur.
- **Talent (öğrenci, TALENT_TO_ORG değerlendirmeyi dolduran taraf):** Kendi stajını/kurumunu değerlendirir — opsiyonel, engagement'ın EVALUATED'a geçişini bloklamaz.
- **Koordinatör (üniversite tarafı):** Değerlendirmeyi salt-okunur görür (`private_note` hariç), süreci takip eder.

## Hedef (Neden)
Zemin360'ın "beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirinde, kurumun stajyer hakkında verdiği **yapılandırılmış tanıklık** burada üretilir. Bu görev, değerlendirme *kaydının* doğru şemayla ve doğru gizlilikle (private_note asla talent'a sızmaz) oluşturulmasını; sonraki adımın (Attestation/VerifiedExperience/SkillSignal üretimi, PLAN 2.8/YET-88) bağımsız ve izole test edilebilmesini sağlar. `NOT_OBSERVED` durumu özellikle kritik: değerlendirici gözlemlemediği bir kriter için zorla not vermeye itilirse veri bozulur — final analiz bunu açıkça vurguluyor.

## User Story
As an **org üyesi (süpervizör)**
I want **engagement'ım PENDING_EVALUATION durumundayken yapılandırılmış bir değerlendirme formu (yetkinlik + davranışsal kriterler, NOT_OBSERVED dahil) gönderebilmek**
So that **stajyerin yetkinlik sinyalleri ve doğrulanmış deneyimi bu değerlendirmeden türeyebilsin, ve kurum notlarım (private_note) öğrenciye asla görünmesin**

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given engagement `PENDING_EVALUATION` durumunda ve istek sahibi bu engagement'ın org tarafına ait bir üye, When `POST /api/v1/engagements/{id}/evaluation` isteği `direction=ORG_TO_TALENT`, en az 1 geçerli `items[]` (her biri `criterion` + `rating` zorunlu, `skill_id` opsiyonel, `comment` opsiyonel) ve opsiyonel `private_note` ile atılır, Then `201 Created` döner; `evaluations` + `evaluation_items` satırları tek transaction'da yazılır (`submitted_at=now() UTC`), response'ta `private_note` **kesinlikle yer almaz**.

2. [Critical] Given aynı istek (AC-1) başarıyla işlendi, When engagement tekrar okunur, Then `engagement.status` otomatik olarak `EVALUATED`'a geçmiş olur (yalnız `ORG_TO_TALENT` submit'i bu geçişi tetikler — `TALENT_TO_ORG` opsiyoneldir, geçişi ne bloklar ne de gerektirir). Bu geçiş de bir `AuditEvent` üretir (database.md: her geçiş AuditEvent üretir).

3. [Critical] Given `rating=NOT_OBSERVED` olan bir `evaluation_item`, When kayıt oluşturulur, Then `comment` **zorunlu tutulmaz** (NOT_OBSERVED, gözlemlenmemiş bir şey hakkında yorum yapmaya zorlamamalı) ve kayıt normal şekilde kabul edilir.

4. [High] Given `items[]` boş dizi veya bir item'da `criterion` eksik/boş string, When POST atılır, Then `422 Unprocessable Entity` döner (Pydantic validation), hiçbir satır yazılmaz.

5. [High] Given istek sahibi bu engagement'a **scope dışı** bir kullanıcı (başka bir organizasyondan/kurumdan, engagement hiç görünür değil), When POST atılır, Then `404 Not Found` döner (CLAUDE.md: yetkisiz erişimde kaynağın varlığı sızdırılmaz). **[plan aşamasında düzeltildi]** Given istek sahibi engagement'ı görebilen (scope içinde) ama bu yönde (direction) değerlendirme yapma yetkisi olmayan biri (örn. talent `ORG_TO_TALENT` göndermeye çalışırsa), When POST atılır, Then `403 Forbidden` döner — mevcut kod tabanı pattern'i (`TransitionForbiddenError`, `post_engagement_tasks`/`post_engagement_deliverables`) ile tutarlı; kaynak zaten görünür olduğundan 404'e gerek yok.

6. [High] Given engagement `PENDING_EVALUATION` dışında bir durumda (`ACTIVE`, `EVALUATED`, `DRAFT` vb.), When POST atılır, Then `409 Conflict` döner (kaynak var, yetki var, durum uygun değil — 404 değil, çünkü varlık zaten doğrulandı).

7. [High] Given aynı `evaluator_user_id` + `engagement_id` + `direction` kombinasyonu için daha önce bir evaluation gönderilmiş (`UNIQUE` kısıtı), When aynı kombinasyonla tekrar POST atılır, Then `409 Conflict` döner ("bu yön için değerlendirme zaten gönderilmiş"), var olan kayıt **değişmez** (append-only).

8. [Medium] Given bir `evaluation_item.skill_id` `skills` tablosunda mevcut olmayan bir UUID, When POST atılır, Then `422 Unprocessable Entity` döner, hiçbir satır yazılmaz (all-or-nothing, kısmi kayıt yok).

9. [Medium] Given `direction=TALENT_TO_ORG` ile talent tarafından POST atılır (öğrenci kendi stajını değerlendirir), When engagement `PENDING_EVALUATION` veya `EVALUATED` durumundaysa, Then `201 Created` döner, kayıt oluşur, ama bu kayıt engagement durumunu **değiştirmez** (AC-2'nin tersine, sadece ORG_TO_TALENT geçişi tetikler).

10. [Medium] Given bir `GET` isteği (bu görev kapsamında ayrı bir okuma ucu **yazılmıyor**, ama Karar Matrisi netliği için not düşülüyor), talent kendi engagement'ının evaluation'ını görürse `private_note` alanı **asla** response şemasında yer almaz; org üyesi (kendi kurumu) görürse `private_note` görünür; koordinatör görürse görünmez; admin görürse görünür (final analiz karar matrisi, satır 1410-1411). *(Bu AC, ileride bir `GET /engagements/{id}/evaluations` ucu yazılırsa geçerli olacak — bu görevde böyle bir uç YAZILMIYOR, bkz. Kapsam Dışı.)*

## Threat Model Tetik Değerlendirmesi (5b adımı)
Bu görev şunlara dokunuyor: **yeni bir HTTP endpoint**, **yetkilendirme mantığı**, **kullanıcı girdisi** (items[], private_note), **PII'ye yakın hassas alan** (private_note bir öğrenci hakkında kurumun özel notu). Bu yüzden tetik **VAR**.

`threat-model` skill'i ayrıca çağrılmadı çünkü bu görevin threat-model'e özgü soyut saldırı senaryoları zaten final analiz'in kendi karar matrisinde (bölüm 15-16) somutlaştırılmış ve AC-5/AC-6/AC-7/AC-10 olarak yukarıda işlendi (BOLA/IDOR: AC-5, durum makinesi kötüye kullanımı: AC-6, tekrar gönderim/replay: AC-7, PII sızıntısı: AC-10). Ek olarak şu güvenlik odaklı AC'ler ekleniyor:

- [Critical] **AC-S1**: `private_note` alanı, `evaluations` tablosunun response şemasında (`EvaluationResponse` Pydantic modeli) **hiçbir koşulda** yer almaz — talent bu response'u okuduğunda (kendi engagement'ı olsa bile) alan yoktur, `None`/`null` bile dönmez (alanın kendisi şemada tanımlı değildir). Bu, ORM modelinin doğrudan response olarak dönülmemesi kuralının (CLAUDE.md) somut uygulamasıdır.
- [High] **AC-S2**: `evaluator_user_id` istemciden **asla** body ile alınmaz — her zaman authenticated principal'dan (`can()`/`scoped_*()` üzerinden) türetilir. Body'de `evaluator_user_id` gönderilse bile yok sayılır (başka bir kullanıcı adına sahte değerlendirme gönderme saldırısını engeller).
- [High] **AC-S3**: `direction` alanı, istek sahibinin gerçek rolüyle tutarlı olmalı — bir talent `direction=ORG_TO_TALENT` gönderemez (kendini kurum gibi göstererek sahte olumlu değerlendirme oluşturamaz), bir org üyesi `direction=TALENT_TO_ORG` gönderemez. **[plan aşamasında düzeltildi]** Uyuşmazlıkta `403 Forbidden` döner (`422` değil) — mevcut kod tabanı pattern'iyle (`TransitionForbiddenError`) tutarlı: engagement zaten scope içinde görünür, sadece bu spesifik aksiyon (bu yönde değerlendirme gönderme) reddediliyor.

`threat_model: not-applicable` frontmatter değeri **YANLIŞ görünüyor olabilir** — düzeltme: yukarıdaki AC-S1/S2/S3 threat-model'in yerini dolduruyor, bu yüzden pratikte `done` muamelesi görmeli. **Not:** frontmatter'da `done` yazılamadı çünkü ayrı `threat-model` skill'i çağrılmadı (final analiz + karar matrisi zaten yeterli somutluktaydı) — bu bir sapma, `plan` adımına geçmeden önce kullanıcı onayı isteniyor.

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: org üyesi, PENDING_EVALUATION, geçerli items[], direction=ORG_TO_TALENT | 201 Created | evaluations+evaluation_items yazılır (tek transaction) + engagement.status→EVALUATED + AuditEvent | `{id, engagement_id, direction, submitted_at, items:[{criterion, skill_id, rating, comment}]}` (private_note YOK) | AC-1, AC-2 |
| 2 | NOT_OBSERVED rating, comment boş | 201 Created | aynı yukarıdaki gibi | comment alanı null/boş kabul edilir | AC-3 |
| 3 | items[] boş veya criterion eksik | 422 Unprocessable Entity | yazma yok | alan bazlı validation hatası | AC-4 |
| 4 | Yetkisiz kullanıcı: scope dışı (ilişkisiz org/kişi) → 404; scope içi ama yanlış yön/rol → 403 | 404 Not Found / 403 Forbidden | yazma yok | scope dışı: genel "kaynak bulunamadı"; yanlış yön: "bu işlemi yapma yetkiniz yok" | AC-5, AC-S3 |
| 5 | Engagement yanlış durumda (PENDING_EVALUATION değil) | 409 Conflict | yazma yok | "bu durumda değerlendirme gönderilemez" | AC-6 |
| 6 | Aynı evaluator+direction ikinci kez | 409 Conflict | yazma yok, önceki kayıt korunur | "bu yön için değerlendirme zaten gönderilmiş" | AC-7 |
| 7 | Geçersiz skill_id | 422 Unprocessable Entity | yazma yok (all-or-nothing) | "geçersiz skill_id" validation hatası | AC-8 |
| 8 | TALENT_TO_ORG submit | 201 Created | kayıt yazılır, engagement.status DEĞİŞMEZ | aynı response şeması | AC-9 |

**Kısmi başarı:** Yok — `evaluations` + `evaluation_items` yazımı ve (varsa) `engagement.status` güncellemesi **tek DB transaction'ı** içinde yapılır. Herhangi bir adım (constraint ihlali, skill_id doğrulama) başarısız olursa tüm transaction rollback edilir; kısmi evaluation kaydı asla oluşmaz.

**Hiçbir şey yapılamadı ama hata yok:** Bu API sözleşmesinde tanımsız/olmamalı — her istek ya `2xx` ile somut bir kayıt oluşturur ya da bir hata koduyla (`404/409/422`) reddedilir. Sessiz no-op yok.

**Boş sonuç ↔ hata ayrımı:** Bu uç bir liste/okuma ucu olmadığı için (sadece `POST`) bu ayrım bu görevde doğrudan geçerli değil — ileride yazılacak bir `GET /engagements/{id}/evaluations` ucu için ayrı ATDD gerekir (bkz. Kapsam Dışı, AC-10 notu).

## Test Strategy
Unit: 70% — `services/evaluation.py` (create_evaluation iş mantığı: yetki kontrolü, transition tetikleme, NOT_OBSERVED kuralı, UNIQUE ihlali yakalama, skill_id doğrulama)
Integration: 20% — `POST /engagements/{id}/evaluation` uç-uca (gerçek DB, gerçek transaction, engagement.status geçişinin gerçekten yazıldığının doğrulanması)
E2E: 10% — happy path (org üyesi → evaluation submit → engagement EVALUATED) tek senaryo; asıl e2e kapsamı PLAN 2.14/YET-102'de

## Benchmark / Başarı Ölçütü
Coverage Target: 80% (`services/evaluation.py` + ilgili `api` katmanı)
Yetkilendirme testleri: **%100** (CLAUDE.md zorunluluğu — yeni endpoint = aynı commit'te yetkilendirme testi)
Performance Target: P95 < 300ms (tek transaction, index'li FK'ler, ağ çağrısı yok — outbox'a gerek yok, bkz. Rollback Beklentisi)
Görsel/UI kriteri: Yok (bu görev backend-only, frontend PLAN 2.13/YET-75'te ayrı)
Diğer: `private_note` sızıntı testi (AC-S1) kesin coverage'da yer almalı — bu, karar matrisinin en kırılgan noktası.

## Kapsam Dışı
- `EVALUATED → VERIFIED` geçişi + Attestation/VerifiedExperience/SkillSignal üretimi — PLAN 2.8 / YET-88 kapsamı, bu görevde YAPILMAZ.
- Frontend değerlendirme formu — PLAN 2.13 / YET-75 / YET-100 kapsamı.
- Uçtan uca duman testi (kayıt→engagement→evidence→evaluation→attestation→signal) — PLAN 2.14 / YET-102 kapsamı.
- Evaluation'ı düzenleme/silme (`UPDATE`/`DELETE`) — append-only kuralı zaten yasaklıyor (CLAUDE.md/database.md).
- Draft/taslak evaluation kaydetme (submit öncesi ara kayıt) — Jira açıklamasında bahsi yok, `submitted_at` bu görevde her zaman satırın oluşturulma anıdır (NULL/draft durumu yok).
- `GET /engagements/{id}/evaluations` (okuma ucu) — bu görevde YAZILMIYOR, sadece `POST` var. AC-10 gelecekteki bu uç için karar matrisini önceden not düşüyor.
- Koordinatör hatırlatma/bildirim otomasyonu (final analiz §1896'da bahsi geçen) — ayrı bir görev, bu şemayla ilgisi yok.
- `evaluation_items.skill_id` üzerinden `SkillSignal` türetimi — PLAN 2.9 kapsamı.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/evaluation.py` — **yeni**: `Evaluation`, `EvaluationItem` SQLAlchemy modelleri (append-only, `evaluations.status` yok — sadece varlık/yokluk)
- `backend/app/schemas/evaluation.py` — **yeni**: `EvaluationCreate`, `EvaluationItemCreate`, `EvaluationResponse` (Pydantic; `EvaluationResponse`'ta `private_note` alanı **tanımlı değil**)
- `backend/app/services/evaluation.py` — **yeni**: `create_evaluation()` iş mantığı — `can()`/`scoped_*()` ile yetki, durum kontrolü, NOT_OBSERVED kuralı, transition tetikleme (`engagement.status` güncelleme, aynı transaction)
- `backend/app/services/engagement.py` — **değişecek**: `transition_table`'a `("PENDING_EVALUATION", "EVALUATED")` satırı eklenir (muhtemelen `evaluation.py` içinden çağrılır, doğrudan public bir "transition" endpoint'i değil — internal kullanım)
- `backend/app/api/engagements.py` — **değişecek**: `POST /engagements/{id}/evaluation` ucu eklenir
- `backend/alembic/versions/` — **yeni migration**: `evaluations` + `evaluation_items` tabloları (FK, CHECK, UNIQUE kısıtları) — **CLAUDE.md gereği migration oluşturma/uygulama için ayrıca açık onay istenecek, bu ATDD onayı yeterli değildir**
- `backend/tests/test_evaluation.py` — **yeni**: servis + endpoint testleri
- `backend/tests/authorization/test_evaluation_authz.py` — **yeni**: `pytest tests/authorization` kapsamına eklenir (private_note sızıntısı, 404/409/422 senaryoları)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu oturumda git kökü proje klasörüyle (`C:\Users\Meyrem\Desktop\P\yetkin360`) aynı görünüyordu (`git status` proje köküne göre çalıştı), ancak sistem ortamında ek çalışma dizinleri (`Additional working directories`) listelendi ve bunlar bu projeyle ilgisiz (eMuhasebe, öğrenci sistemi, Labirent-Dev, tipplus vb.). Sonraki adımlar (`plan`, `code-copilot`, `test-copilot`, `red-team`) arama/grep işlemlerini **her zaman** `C:\Users\Meyrem\Desktop\P\yetkin360` alt ağacıyla sınırlamalı — kök dizinden veya ek çalışma dizinlerinden sınırsız arama YAPILMAMALI.

## Rollback Beklentisi
`create_evaluation` tek DB transaction'ı içinde çalışır: `evaluations` satırı + `evaluation_items` satırları + (varsa) `engagements.status` güncellemesi + `AuditEvent`. Herhangi bir adımda hata (constraint ihlali, skill_id doğrulama hatası) olursa **tüm transaction rollback edilir**, hiçbir satır yazılmaz, engagement durumu değişmeden kalır. Ağ çağrısı yok (bu adımda e-posta/S3/AI tetiklenmiyor) — CLAUDE.md'nin "ağ çağrısı asla açık transaction içinde yapılmaz" kuralı ihlal edilmiyor, çünkü zaten ağ çağrısı içermiyor; bu yüzden `outbox` gerekmiyor.

## Risks
- **T7 geçişinin bu göreve sonradan eklenmesi, YET-88'i (muhtemelen paralel çalışılıyor) etkileyebilir.** Kullanıcı bu riski zaten fark etti ve konuyu bilerek bu göreve dahil etti — ama commit öncesi takım arkadaşıyla (YET-88 sahibi) senkronize olmak faydalı olur, özellikle `engagement.py`'deki `transition_table`'a aynı anda iki kişi dokunursa merge çatışması riski var.
- `direction` alanının istek sahibinin gerçek rolüyle tutarlılığı (AC-S3) — final analizde açıkça yazılmamış, bu ATDD'de eklenen bir güvenlik kısıtı; `code-copilot`/`test-copilot` bunu atlamamalı.
- Migration onayı bu görevde iki kez düşünülmeli: hem tablo oluşturma (evaluations/evaluation_items) hem de mevcut `engagements` tablosunda değişiklik OLMAYACAĞI (status zaten CHECK constraint'te var, migration gerekmez) — bu netleştirildi, risk düşük.

## Assumptions
- `evaluator_user_id` her zaman authenticated principal'dan türetilir, body'den asla okunmaz (AC-S2, final analizde açık değildi, bu ATDD'de karar verildi — genel prensipten çıkarım).
- `direction` alanı, gönderen kullanıcının gerçek rolüyle uyuşmalı (AC-S3) — final analizde açık değildi, bu ATDD'de eklenen varsayım.
- `submitted_at` her zaman satırın oluşturulma anı; ayrı bir draft/taslak durumu yok (final analiz şemasında `submitted_at` NOT NULL olarak işaretli değildi ama "submitted_at sonrası immutable" ifadesi satırın var olduğu an submit edilmiş sayıldığını ima ediyor).
- `evaluations.direction` + `evaluator_user_id` + `engagement_id` UNIQUE kısıtı final analizde birebir var; bu üç alan aynı anda gönderilen ikinci bir POST'u DB seviyesinde reddeder, servis katmanı bunu yakalayıp `409`'a çevirir.
- T7 geçişinin `engagement.py`'deki `transition_table`'a ekleneceği, ayrı bir public "transition" endpoint'i olarak değil — çünkü kullanıcı doğrudan `PENDING_EVALUATION→EVALUATED` geçişini tetiklemek için `POST /engagements/{id}/transitions` çağırmaz, bu geçiş **evaluation submit'inin bir yan etkisidir**. (`code-copilot` bu ayrımı netleştirmeli: mevcut `transition_engagement()` fonksiyonu internal olarak `create_evaluation()` içinden mi çağrılır, yoksa `create_evaluation()` kendi başına mı status günceller? — Unknowns'a taşındı.)

## Unknowns
- `transition_engagement()` fonksiyonunun (`backend/app/services/engagement.py:195`) `create_evaluation()` içinden nasıl çağrılacağı (aynı transaction içinde mi, ayrı bir precondition seti mi gerekiyor) — `plan` adımında kod okunarak netleştirilmeli.
- `direction` + rol tutarlılığı (AC-S3) ihlalinde tam HTTP kodu (`422` mi `404` mü) — bu ATDD'de `422` önerildi ama `plan`/`code-copilot` aşamasında CLAUDE.md'nin 403→404 mantığıyla çelişmediği teyit edilmeli.
- Koordinatörün bu POST ucuna erişimi olup olmadığı (final analiz karar matrisinde koordinatör sadece "R" — okuma — yetkisine sahip, bu POST ucunu çağıramaz) — AC-5'e (404) dahil edildi ama ayrıca test edilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Persona/kim dolduruyor → Her iki yön de (ORG_TO_TALENT + TALENT_TO_ORG) şema/endpoint düzeyinde desteklenir, ORG_TO_TALENT asıl kritik yol. (Sonnet 5 low alt-ajanı tarafından yanıtlandı, final analiz karar matrisine dayanarak)
2. Neden ayrı madde (2.7 vs 2.8) → Değerlendirme kaydı ile ondan üretilen attestation/signal birbirinden bağımsız test edilebilir birimler; private_note gizliliği izole doğrulanabilsin diye ayrıldı. (Sonnet 5 low alt-ajanı)
3. Happy path → AC-1'e işlendi. (Sonnet 5 low alt-ajanı)
4. Engagement yanlış durumda → 409 Conflict. (Sonnet 5 low alt-ajanı, AC-6)
5. UNIQUE ihlali → 409 Conflict. (Sonnet 5 low alt-ajanı, AC-7)
6. items[] boş/criterion eksik → 422. (Sonnet 5 low alt-ajanı, AC-4)
7. Geçersiz skill_id → 422. (Sonnet 5 low alt-ajanı, AC-8)
8. Davranış sözleşmesi tablosu → yukarıya işlendi.
9. Benchmark → coverage 80%, P95<300ms. (Sonnet 5 low alt-ajanı, proje geneli için tipik varsayım)
10. Kapsam dışı → onaylandı (EVALUATED→VERIFIED, frontend, e2e, düzenleme/silme, draft). (Sonnet 5 low alt-ajanı)
11. Etkilenen dosyalar → yukarıya işlendi. (Sonnet 5 low alt-ajanı)
12. Test stratejisi → 70/20/10. (Sonnet 5 low alt-ajanı, proje tutarlılığı için)
13. **T7 geçişi bu görevde tetiklenmeli mi?** → Alt-ajan önce "kapsam dışı bırakılmalı, kullanıcıya sorulmalı" dedi (doğru tespit). Kullanıcıya soruldu: Jira taraması T7'ye karşılık gelen ayrı görev olmadığını, YET-88'in (T8) EVALUATED'ı ön koşul kabul ettiğini gösterdi. **Kullanıcı kararı: T7 bu göreve dahil edilsin** (takım arkadaşının YET-88'i paralel çalışıyor olabileceği, bu boşluğun gözden kaçabileceği gerekçesiyle). AC-2/AC-6'ya işlendi. (kullanıcı mesajından, doğrudan onay)
14. **T7 yön kuralı (tek yön mü iki yön mü)** → Final analiz §1896 riskine dayanarak "sadece ORG_TO_TALENT yeterli" önerildi, kullanıcı onayladı. AC-2/AC-9'a işlendi. (kullanıcı mesajından, doğrudan onay)
15. Rollback → tek transaction, ağ çağrısı yok, outbox gerekmiyor. (Sonnet 5 low alt-ajanı)
