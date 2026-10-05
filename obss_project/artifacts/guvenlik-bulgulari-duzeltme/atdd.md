---
task_slug: guvenlik-bulgulari-duzeltme
jira_id: YET-181, YET-179, YET-178, YET-191, YET-192, YET-193, YET-199, YET-200, YET-188, YET-215, YET-223, YET-224, YET-232, YET-238
saga_task_id: null
threat_model: done
priority: critical
coverage_target: 85
performance_target: "N+1 sorgu sayısı sabite iner (L-09) — somut sayı test ile ölçülür"
memory_target: null
test_strategy:
  unit: 50
  integration: 40
  e2e: 10
affected_modules:
  - services/engagement.py (145-184, 643-655)
  - services/attestation.py (408+)
  - services/authorization.py (352-372)
  - api/public.py (138-229)
  - services/evaluation.py (173-203)
  - services/skill_claim.py
  - services/skill_signal.py
  - services/skill.py (update_skill, merge)
  - api/talents.py (PATCH /talents/me, POST/GET/DELETE /talents/me/skills)
  - api/skill_signals.py (:84)
---

# ATDD — guvenlik-bulgulari-duzeltme

## Jira Kaynağı
14 ayrı Jira görevi, tek ATDD turunda birleştirildi (`YET` projesi, Cloud ID `1c97069a-da45-4ac5-916e-0d51b8cc6ab4`):

| Jira ID | Kod | Öncelik | Özet |
|---|---|---|---|
| [YET-191](https://kuyusuzyusuf123.atlassian.net/browse/YET-191) | IS-01 | Highest/Kritik, CANLI | `generate_public_token()` hiç çağrılmıyor; public doğrulama/profil hiç çalışmıyor |
| [YET-192](https://kuyusuzyusuf123.atlassian.net/browse/YET-192) | IS-02 | Highest/Kritik, CANLI | `started_on/ended_on` set eden API yok; COMPETENCE tanıklığı hiç verilemez |
| [YET-193](https://kuyusuzyusuf123.atlassian.net/browse/YET-193) | IS-03 | High | T4 geçişi yok; `completed_at` dolmuyor; `reason` üzerine yazılıyor |
| [YET-179](https://kuyusuzyusuf123.atlassian.net/browse/YET-179) | GUV-05 | High | Geri çekilen (`revoked_at`) tanıklık okuma yollarında filtrelenmiyor |
| [YET-178](https://kuyusuzyusuf123.atlassian.net/browse/YET-178) | GUV-04 | High | Talent kendi değerlendirmesiyle kendine STRONG sinyal üretebiliyor |
| [YET-181](https://kuyusuzyusuf123.atlassian.net/browse/YET-181) | GUV-08 | Medium | Çapraz-kiracı engagement açma + 400/201 bilgi sızıntısı oracle'ı |
| [YET-188](https://kuyusuzyusuf123.atlassian.net/browse/YET-188) | AUTHZ-03 | Medium | Durum makinesi dokümandan sapmış (T4/T5/T8 rol uyuşmazlığı) |
| [YET-199](https://kuyusuzyusuf123.atlassian.net/browse/YET-199) | IS-05 | Medium | Geçersiz `skill_id` sessizce yok sayılıyor; `attestor_org_id` yanlış yazılıyor |
| [YET-200](https://kuyusuzyusuf123.atlassian.net/browse/YET-200) | IS-06 | Medium | Silinen iddiada sinyal kalıyor; `attested_by` hep `None`; MERGE yönlendirmiyor |
| [YET-215](https://kuyusuzyusuf123.atlassian.net/browse/YET-215) | VER-02 | Medium | Geçersiz `claimed_level` → yanlışlıkla 409 (olması gereken 400) |
| [YET-223](https://kuyusuzyusuf123.atlassian.net/browse/YET-223) | L-09 | Low | N+1 sorgular (skill_claim/skill_signal/public) |
| [YET-224](https://kuyusuzyusuf123.atlassian.net/browse/YET-224) | L-10 | Low | `parent_id` kaldırılamıyor; MERGED→DEPRECATED tutarsızlığı |
| [YET-232](https://kuyusuzyusuf123.atlassian.net/browse/YET-232) | L-08 | Low | Profil yoksa 401 dönüyor (olması gereken 404) |
| [YET-238](https://kuyusuzyusuf123.atlassian.net/browse/YET-238) | L-06 | Low | `PATCH /talents/me` `updated_at`'i elle set ediyor |

Jira açıklamaları (description alanları) birebir yukarıdaki satırlara ve Davranış Sözleşmesi tablosuna yansıtıldı; sonraki adımlar (`plan`, `test-copilot`, `code-copilot`) bu tablodan okumalı, Jira'ya tekrar sorgu atmamalı.

**Not (araç bildirimi):** Jira MCP çağrılarının sonucunda Atlassian'dan gelen otomatik bir bildirim yakalandı — v1/sse ucu 30 Haziran 2026'dan sonra desteklenmeyecek, v2/mcp'ye geçiş isteniyor. Bu bir kullanıcı/sistem talimatı değil, salt bilgilendirme; herhangi bir bağlantı değişikliği yapılmadı.

**Not (Saga):** Bu oturumda Saga MCP sunucusuna bağlanılamadı (bağlı değil/zaman aşımı) — `saga_task_id` bu yüzden `null`. Saga kaydı daha sonra manuel veya bağlantı sağlandığında açılmalı.

## Persona
Backend geliştirici (Yusuf Çinar) — düzeltmelerin dolaylı faydalanıcısı: talent'lar (kendi verisi sızmasın, başkası adına sahte sinyal/tanıklık üretilmesin), kurumlar/koordinatörler (yetkisiz engagement açılmasın) ve platformun "kanıta dayalı yetkinlik" vaadine güvenen üçüncü taraf doğrulayıcılar (public profil linkini tıklayanlar).

## Hedef (Neden)
14 bulgu aynı kök nedenden besleniyor: yetkilendirme/append-only/durum-geçiş katmanındaki tutarsızlıklar, ve çoğu aynı dosyalarda (`engagement.py`, `evaluation.py`, `authorization.py`) üst üste biniyor. Tek ATDD turunda ele almak gereksiz tekrar eden review/test yükünü önler. İki bulgu (IS-01, IS-02) demo zincirini doğrudan kırıyor — bunlar olmadan `beyan → kanıt → tanıklık → doğrulanmış deneyim` zinciri uçtan uca çalışmıyor.

## User Story
As a platformu kullanan talent/kurum/doğrulayıcı
I want yetkilendirme kurallarının (kim-ne-görebilir) ve append-only garantilerinin (geri çekilen tanıklık geçersiz kalır) gerçekten uygulanmasını ve public doğrulama zincirinin çalışmasını
So that platforma ve üzerindeki "doğrulanmış deneyim" iddialarına güvenebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given bir VerifiedExperience oluşturulduğunda, When tanıklık COMPETENCE/PARTICIPATION türünde kaydedilirse, Then `generate_public_token()` çağrılır ve `visibility=PUBLIC` olduğunda `GET /public/v/{token}` 200 ile gerçek veri döner (IS-01).
2. [Critical] Given bir koordinatör engagement'ı tamamlarken `started_on`/`ended_on` alanlarını API üzerinden set ederse, When kriterler sağlanırsa, Then tanıklık türü COMPETENCE olabilir — sadece seed script değil, gerçek API akışı bunu üretebilir (IS-02).
3. [High] Given kurumsuz (institution'sız) bir engagement DRAFT durumundaysa, When T4 geçişi tetiklenirse, Then ACTIVE'e geçer; `completed_at` T5/T8'de dolar; `reason` alanı önceki değerlerin üzerine yazılmaz (append/log) ve bir üst uzunluk sınırını aşarsa 400 döner (IS-03).
4. [High] Given bir attestation `revoked_at` ile geri çekilmişse, When `GET /public/v/{token}` veya VerifiedExperience listesi okunursa, Then bu kayıt artık görünmez/404 döner — **AC-S3** (GUV-05).
5. [High] Given bir TALENT kendi TALENT_TO_ORG değerlendirmesini gönderirse, When istek işlenirse, Then istek 201 ile kabul edilir (TALENT_TO_ORG göndermek meşru bir eylem, bu tur kapsamında kısıtlanmıyor) AMA `skill_signal` ÜRETİLMEZ — sinyal üretimi SADECE ORG_TO_TALENT yönünde olur, TALENT kendine STRONG sinyal üretemez — **AC-S4** (GUV-04). **[Karar: 2026, kullanıcı onayı — "B seçeneği": istek engellenmez, sadece sinyal üretimi engellenir; eski `test_talent_can_post_talent_to_org_201` davranışı korunur.]**
6. [Medium] Given bir TALENT başka bir organizasyon için ya da bir ORG_MEMBER başka bir talent için engagement açmaya çalışırsa, When `institution_id` uyuşmazlığı varsa, Then her durumda aynı hata kodu (404) döner — var/yok farkı sızdırılmaz — **AC-S1, AC-S2** (GUV-08).
7. [Medium] Given dokümanda (`docs/STATE_MACHINE.md`) T8 geçişinin SUPERVISOR'a ait olduğu belirtilmişse, When ORG_ADMIN bu geçişi çağırırsa, Then 404 döner (yetkisiz) — **AC-S5** (AUTHZ-03).
8. [Medium] Given tanıklıkta geçersiz bir `skill_id` verilirse, When istek işlenirse, Then 422 VALIDATION_ERROR döner (sessizce yok sayılmaz) — değerlendirme ucuyla tutarlı (IS-05).
9. [Medium] Given bir skill iddiası silinip yeniden eklenirse, When SELF_CLAIM sinyali sorgulanırsa, Then eski sinyal okuma yolunda geçersiz sayılır (çakışan ikinci sinyal görünmez) ve `attested_by` doğru değeri döner (IS-06).
10. [Medium] Given `POST /talents/me/skills`'e geçersiz `claimed_level` gönderilirse, When Pydantic/servis validasyonu çalışırsa, Then 400 VALIDATION_ERROR döner (409 ALREADY_CLAIMED değil) (VER-02).
11. [Low] Given talent profili olmayan kimliği doğrulanmış bir kullanıcı `GET /talents/me/skill-signals` çağırırsa, When istek işlenirse, Then 401 değil 404 döner — verified-experiences ile tutarlı, kaynağın var/yok olduğu sızdırılmaz — **AC-S6** (L-08).
12. [Low] Given `skill_claim`/`skill_signal`/`public` listeleme uçları çağrıldığında, When N kayıt varsa, Then sorgu sayısı N'e bağlı artmaz (JOIN/eager-load ile sabit) (L-09).
13. [Low] Given `update_skill` çağrısında `parent_id` kaldırılmak istenirse, When istek işlenirse, Then `parent_id` null'lanabilir; MERGED bir skill DEPRECATED yapılmaya çalışılırsa 409 CONFLICT döner (L-10).
14. [Low] Given `PATCH /talents/me` çağrılırsa, When güncelleme yapılırsa, Then `updated_at` yalnız `TimestampMixin` tarafından set edilir, servis kodu elle set etmez (L-06).

## Threat Model
Çağrıldı — tetikleyiciler: yetkilendirme/kimlik doğrulama, çok-kiracılı (multi-tenant) sınır (talent/kurum/org), public (kimliksiz) uç. STRIDE-lite'tan özellikle **Elevation** (yetki sadece UI'da değil sunucuda kontrol ediliyor mu) ve **Information Disclosure** (400 vs 201/404 vs 401 oracle'ları) kategorilerinde somut açık bulundu. Üretilen güvenlik kriterleri yukarıdaki Acceptance Criteria'ya `AC-S1..AC-S6` olarak gömüldü:

- **AC-S1** (GUV-08/Elevation): TALENT'ın kendi olmayan `institution_id` ile `POST /engagements` göndermesi → 404, kayıt oluşmaz.
- **AC-S2** (GUV-08/Info disclosure): `institution_id` uyuşmazlığı ile var olmayan `institution_id` aynı hata kodunu döner — oracle kapanır.
- **AC-S3** (GUV-05/Tampering+Info disclosure): revoke edilmiş attestation `GET /public/v/{token}`'da 404, VerifiedExperience listesinde görünmez.
- **AC-S4** (GUV-04/Elevation): TALENT kendi TALENT_TO_ORG değerlendirmesiyle kendine sinyal üretemez (403/404, satır eklenmez).
- **AC-S5** (AUTHZ-03/Elevation): T8'i SUPERVISOR değil ORG_ADMIN çağırırsa 404.
- **AC-S6** (L-08/Info disclosure): Profili olmayan kullanıcıya 401 değil 404 — kaynak varlığı sızdırılmaz.

`authz-test` skill'i çağrıldı: AC-S1..AC-S6 için IDOR/yetkilendirme test matrisi `test-copilot` adımına `extra_instructions` olarak aktarılacak (en az iki farklı aktör: sahibi/başkası/anon/rol-yükseltme denemesi — bkz. authz-test SKILL.md matrisi). Mock'lu yetkilendirme testi kabul edilmeyecek.

**Kabul edilen risk:** T4 (kurumsuz DRAFT→ACTIVE) ve T8 (SUPERVISOR vs ORG_ADMIN) geçişlerinin **nihai rol ataması** mimari karar gerektiriyor (Jira'da K4/K5/K8/K10 olarak işaretli). Bu ATDD turu sadece *dokümanla kodun tutarlı olmasını* (AC-7/AC-S5) garanti eder; hangi rolün "doğru" olduğu kararı bu turun kapsamı dışıdır ve Unknowns'a yazıldı.

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışını veya prompt'unu değiştirmiyor, salt backend servis/endpoint düzeltmesi. Bölüm silindi.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Jira/Kod | Durum (girdi/koşul) | Dönen değer / durum kodu (düzeltme sonrası) | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|---|
| 1 | GUV-08 | TALENT başka org için / ORG_MEMBER başka talent için engagement açmaya çalışır | 404 (institution_id uyuşmazlığında da 404 — tutarlı) | Kayıt oluşturulmaz | "Kaynak bulunamadı" — var/yok bilgisi sızmaz | AC-6, AC-S1, AC-S2 |
| 2 | GUV-05 | Attestation revoke edilmiş (`revoked_at` dolu) | Public/VerifiedExperience okumalarında filtrelenir → 404 / listede yok | `revoked_at` değişmez (append-only); yalnız okuma sorgusuna `WHERE revoked_at IS NULL` eklenir | Geri çekilmiş tanıklık artık görünmez | AC-4, AC-S3 |
| 3 | GUV-04 | Talent kendi TALENT_TO_ORG değerlendirmesini gönderir | 201 (istek kabul edilir), ama sinyal üretilmez | `skill_signals`'a satır eklenmez (sadece ORG_TO_TALENT yönünde üretilir) | Değerlendirme kaydedilir, ama talent kendine STRONG sinyal kazandıramaz | AC-5, AC-S4 |
| 4 | IS-01 | VerifiedExperience oluşturulur, visibility=PUBLIC | `generate_public_token()` çağrılır; `GET /public/v/{token}` 200 + gerçek veri | `public_token` kolonu dolar | Public profil linki artık çalışır | AC-1 |
| 5 | IS-02 | Koordinatör `started_on`/`ended_on`'u API üzerinden set eder | 200; kriterler sağlanırsa tanıklık türü COMPETENCE olabilir | Engagement/tanıklık kaydına tarih yazılır | COMPETENCE tanıklığı artık API'den üretilebilir | AC-2 |
| 6 | IS-03 | Kurumsuz görev DRAFT, T4 geçişi istenir | 200 → ACTIVE; `reason` önceki değerin üzerine yazılmaz, sınır aşımında 400 | `completed_at` T5/T8'de dolar | Durum değişir, geçmiş `reason` kaybolmaz | AC-3 |
| 7 | IS-05 | Tanıklıkta geçersiz `skill_id` | 422 VALIDATION_ERROR (sessiz yok sayma yok) | Tanıklık oluşturulmaz | Net hata mesajı | AC-8 |
| 8 | IS-06 | Skill iddiası silinip yeniden eklenir | Eski SELF_CLAIM sinyali okuma yolunda geçersiz sayılır; `attested_by` doğru değeri döner | Yeni sinyal append edilir, eski satır silinmez (append-only) ama filtrelenir | Çakışan sinyal görünmez | AC-9 |
| 9 | AUTHZ-03 | T8 geçişi SUPERVISOR yerine ORG_ADMIN tarafından çağrılır | 404 (yetkisiz) | Durum değişmez | Kaynak bulunamadı | AC-7, AC-S5 |
| 10 | VER-02 | `POST /talents/me/skills`'te geçersiz `claimed_level` | 400 VALIDATION_ERROR (409 değil) | DB'ye yazılmadan reddedilir | Anlamlı "geçersiz seviye" hatası | AC-10 |
| 11 | L-09 | skill_claim/skill_signal/public listeleme | Aynı 200 sonucu, tek sorguda (JOIN/eager-load) | Sorgu sayısı sabitlenir | Davranış aynı, yanıt süresi iyileşir | AC-12 |
| 12 | L-10 | `update_skill` ile `parent_id` kaldırılır / MERGED→DEPRECATED denenir | `parent_id` null'lanabilir → 200; MERGED→DEPRECATED → 409 CONFLICT | `merged_into_id` tutarlılığı korunur | Tutarsız istek reddedilir | AC-13 |
| 13 | L-08 | Talent profili yok, skill-signals çağrılır | 401 yerine 404 | — | "Bulunamadı", profil varlığı sızmaz | AC-11, AC-S6 |
| 14 | L-06 | `PATCH /talents/me` çağrılır | `updated_at` yalnız `TimestampMixin` set eder | — | Davranış aynı, iç tutarlılık düzelir | AC-14 |

**Kısmi başarı:** Bu turdaki her düzeltme bağımsız bir commit/PR birimidir (CLAUDE.md: her mantıklı birim ayrı commit) — bir bulgunun düzeltmesi başarısız olsa bile diğerleri bağımsız olarak commit edilebilir/edilmeyebilir; append-only tablo kuralı gereği hiçbir düzeltme var olan satırı UPDATE/DELETE etmez, sadece izinli kolonları (`revoked_at`, `visibility`, `merged_into_id`) değiştirir veya yeni satır/migration ekler.

**Hiçbir şey yapılamadı ama hata da yok:** Uygulanmaz — bu görevler zaten var olan hatalı davranışları düzeltiyor; her AC açıkça "önce X oluyordu, düzeltme sonrası Y olmalı" şeklinde test edilebilir, sessiz "hiçbir şey değişmedi" kabul edilmez (test kırmızı kalır).

**Boş sonuç ↔ hata ayrımı:** `GET /public/v/{token}` için: token hiç yoksa/geçersizse 404; token var ama ilişkili VerifiedExperience revoke edilmişse de 404 (AC-S3) — ikisi ayırt edilmez (kasıtlı: doğrulama amaçlı uçta "var ama geçersiz" ile "hiç yok" bilgisinin ayrışması zaten bir bilgi sızıntısı olurdu). `GET /talents/me/skills` boş liste dönebilir (gerçekten hiç skill eklenmemiş) — bu 404 değil 200+`[]` olmalı, çünkü kullanıcı kendi kaynağına erişiyor (authz hatası değil, veri yok).

## Test Strategy
Unit: 50% — servis fonksiyonları (revoke filtreleme, sinyal üretim yönü kontrolü, claimed_level validasyonu, parent_id/MERGE tutarlılığı, updated_at davranışı)
Integration: 40% — endpoint + yetkilendirme (403→404 dönüşümleri, institution mismatch oracle kapatma, public token akışı, N+1 sorgu sayısı ölçümü)
E2E: 10% — happy path: DRAFT→T4→ACTIVE→COMPETENCE tanıklık→public profilde görünür olma zinciri

`pytest tests/authorization -q` tüm paket zorunlu (CLAUDE.md doğrulama matrisi: yetkilendirme değişikliği → tam paket).

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: N+1 sorgu sayısı sabite iner (L-09) — test ile sorgu sayısı ölçülüp sabitlenmeli (ör. `assert query_count <= k`)
Görsel/UI kriteri: Yok — bu tur yalnız backend
Diğer: `pytest tests/authorization -q` tam yeşil + her 14 bulgu için en az bir regresyon testi; AC-S1..AC-S6 için `authz-test` matrisi mock'suz geçmeli

## Kapsam Dışı
- T4/T8'in **nihai rol ataması** kararı (K4, K5, K8, K10 — Jira'da "Karar gerektirir" notlu maddeler): bu tur sadece dokümanla kodun tutarlı hale getirilmesini kapsar, hangi rolün doğru olduğuna dair yeni bir mimari karar vermez.
- AI, matching motoru, trust score, Redis/cache katmanı (N+1 düzeltmesi sadece JOIN/eager-load ile yapılır, yeni bağımlılık eklenmez) — MVP dışı liste.
- Üretim verisinde geriye dönük backfill/migration (IS-01/IS-02 canlı etkisi) — bu kapsamın dışında, ayrı karar gerektirir (bkz. Unknowns).

## Etkilenen Dosyalar/Modüller (bilinen)
`services/engagement.py` (145-184, 643-655), `services/attestation.py` (408+), `services/authorization.py` (352-372), `api/public.py` (138-229), `services/evaluation.py` (173-203), `services/skill_claim.py`, `services/skill_signal.py`, `services/skill.py` (update_skill/merge), `api/talents.py` (PATCH /talents/me, POST/GET/DELETE /talents/me/skills), `api/skill_signals.py` (:84). `scripts/seed.py` referans olarak okunur, değiştirilmez.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökü proje klasörü (`yetkin360`) ile aynı mı, yoksa daha geniş bir dizin mi, bu ATDD turunda kontrol edilmedi. Sonraki adımlar (`plan`, `code-copilot`/`test-copilot`, `red-team`) arama/grep'i `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\yetkin360` ile sınırlı tutmalı, kök dizinden sınırsız arama yapmamalı.

## Rollback Beklentisi
Hiçbir düzeltme append-only tabloya (`attestations`, `skill_signals`, `evaluations`, `audit_events`, `verified_experiences`) UPDATE/DELETE uygulamaz — yalnızca izinli kolonlar (`revoked_at`, `visibility`) veya yeni satır eklenir. Uygulanmış migration asla elle değiştirilmez, düzeltme gerekirse yeni migration açılır. Her bulgu ayrı commit olduğu için `git revert` ile bağımsız geri alınabilir.

## Risks
- IS-01/IS-02 "CANLI" etkili olarak işaretli — düzeltme sonrası mevcut (seed/demo) veride geriye dönük backfill gerekip gerekmediği belirsiz, kullanıcıya ayrıca sorulmalı.
- 14 bulgunun aynı dosyalarda (örn. `engagement.py`) üst üste binmesi, düzeltmelerin birbirini etkileme riski taşıyor — `plan` adımında dosya bazlı çakışma kontrolü yapılmalı.
- T4/T8 rol kararı netleşmeden AC-7/AC-S5 "doğru rol" dokümana göre sabitleniyor; karar değişirse bu AC'ler güncellenmeli.

## Assumptions
- `generate_public_token()` fonksiyonu kod tabanında zaten mevcut ama hiç çağrılmıyor (IS-01) — düzeltme "çağırma noktası ekleme" kapsamında, yeni token mantığı yazmak değil.
- N+1 düzeltmesi (L-09) yalnızca JOIN/eager-load ile yapılacak, yeni cache katmanı eklenmeyecek (MVP kapsamı yasaklı listesi: Redis).
- Kabul kriteri sahibi: `pytest tests/authorization -q` + ilgili bulgu testlerinin tamamının yeşil olması + kullanıcının (Yusuf Çinar) nihai onayı.

## Unknowns
- T4 (kurumsuz DRAFT→ACTIVE) ve T8 (SUPERVISOR vs ORG_ADMIN) geçişlerinde hangi rolün nihai olarak yetkili olacağı (K4, K5, K8, K10) — ayrı karar turu gerektirir.
- Üretim/demo verisinde IS-01/IS-02 için geriye dönük backfill gerekip gerekmediği.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Backend geliştirici Yusuf Çinar talep ediyor; dolaylı yararlanıcı talent/kurum kullanıcıları (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef/neden → Aynı kök neden + dosya çakışması, tek turda ele alma gereksiz tekrarı önler (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path → DRAFT→T4→ACTIVE→COMPETENCE tanıklık→public profilde görünürlük zinciri (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → GUV-05 revoke sonrası görünürlük, GUV-08 oracle kapatma, GUV-04 kendine sinyal engeli (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → Yukarıdaki 14 satırlık tabloya işlendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
6. Başarı ölçütü → `pytest tests/authorization -q` tam yeşil + N+1 somut azalma (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → K4/K5/K8/K10 rol kararları, MVP-dışı özellikler (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. Bağımlılıklar → Yukarıdaki dosya listesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
9. Performans/güvenlik kısıtı → 403→404 kuralı, append-only, yeni bağımlılık yasak (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → append-only + ayrı commit + yeni migration (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → pytest tam paket + kullanıcı onayı (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → Unit 50/Integration 40/E2E 10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. Riskler/varsayımlar/bilinmeyenler → Yukarıdaki Risks/Assumptions/Unknowns bölümlerine işlendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
14. Hangi görevler kapsama girsin? → GUV-*, AUTHZ-*, IS-*, L-*/VER-* tümü (14 görev) (kullanıcı mesajından).
15. Tek mi ayrı mı atdd.md? → Tek birleşik atdd.md (kullanıcı mesajından).
16. Görev slug'ı → `guvenlik-bulgulari-duzeltme` (kullanıcı onayından).
