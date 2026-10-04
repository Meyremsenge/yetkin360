---
task_slug: yet-187-coklu-rol
jira_id: YET-187
saga_task_id: null
priority: critical
threat_model: done
coverage_target: 90
performance_target: "scoped_* sorguları tek SQL (OR/IN birleşimi), ek round-trip yok"
memory_target: null
test_strategy:
  unit: 25
  integration: 75
  e2e: 0
affected_modules:
  - backend/app/api/deps.py
  - backend/app/api/organizations.py
  - backend/app/services/authorization.py
  - backend/app/services/engagement.py
  - backend/app/services/attestation.py
  - backend/app/services/evaluation.py
  - backend/tests/authorization/
---

# ATDD — yet-187-coklu-rol

## Jira Kaynağı
[YET-187 — AUTHZ-01: Tek kind modeli çoklu rollü kullanıcıyı bozuyor](https://kuyusuzyusuf123.atlassian.net/browse/YET-187) (Highest, Yapılacaklar)

Açıklama (birebir, özet): Her kullanıcıya kayıtta talent profili açılıyor; `Principal.kind` docstring'i "yalnız gösterim içindir" diyor ama `can()`/`scoped_*`/tüm geçiş tablosu kind'a dayanıyor. Org ADMIN'i aynı zamanda koordinatörse org uçlarında 404 alıyor; kurum üyesi talent kendi kanıtlarını göremiyor (GUV-02'nin kökü).
Konum: `api/deps.py:43-54`, `services/authorization.py:52-235`.
Öneri: Kapsam sorgularını kind yerine üyelik listelerinin BİRLEŞİMİ ile kur (talent_id OR organization_id IN(...) OR institution_id IN(...)); işlem yetkisi kaynak bazlı.
Zincir: atdd → threat-model → plan → authz-test (zorunlu) → test-copilot → code-copilot → verify → red-team. İki onay noktası: atdd.md ve plan.md.

Kod keşfi (kind'a dayanan yerler): `authorization.py` (can, scoped_organizations/institutions/engagements/evidence), `engagement.py` (create, transition tablosu, task, deliverable, dashboard), `attestation.py` (2 yer), `evaluation.py`, `api/organizations.py:247,341`. `Principal` ve testlerde 149 `kind=` kullanımı var.

## Persona
Birden çok rolü olan kullanıcı: aynı hesap hem talent (kayıtta otomatik profil), hem bir organizasyonun ADMIN/MEMBER'ı, hem bir kurumun COORDINATOR/ADMIN'i olabilir. Tek rollü kullanıcılar da etkilenmemeli.

## Hedef (Neden)
`get_current_principal` çoklu üyeliği tek bir "en yüksek" `kind`'a indirgiyor; kind'a bakan her yetki kararı bu kullanıcıyı diğer rollerinde 404/403'e düşürüyor. Yetki, kind yerine üyelik kimlik listelerine (talent_id, org_ids, org_admin_ids, institution_ids, institution_admin_ids) ve kaynakla ilişkiye dayanmalı.

## User Story
As a çoklu rollü kullanıcı
I want rollerimin hepsinin yetkisini aynı anda kullanabilmek
So that bir rolüm yüzünden diğer rolümdeki işlevleri (kendi kanıtlarım, kurum onayı, org yönetimi) kaybetmeyeyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] AC-1 Given kullanıcı X org O'nun ADMIN'i ve kurum K'nın COORDINATOR'ı, When O'nun org uçlarına (admin_update, üye ekleme, verify-domain) ve K'nın PENDING_APPROVAL engagement'ına onay/red isteği atar, Then iki rol de çalışır (404 yok).
2. [Critical] AC-2 Given X bir org/kurum üyesi ve kayıtta talent profili var, When kendi kanıt/skill claim/signal/verified-experience uçlarını çağırır, Then kendi kayıtlarını görür (kind org/kurum olsa da).
3. [Critical] AC-3 Given X kurum A'da ADMIN, kurum B'de COORDINATOR, When B'nin PENDING_APPROVAL engagement'ını onaylar, Then başarılı (bugün INST_ADMIN'e indirgenip koordinatörlüğü kayboluyor). A'daki ADMIN davranışı değişmez (YET-190 kapsamı).
4. [Critical] AC-4 Given tek rollü kullanıcılar (TALENT, ORG_MEMBER, ORG_ADMIN, COORDINATOR, INST_ADMIN, USER), When mevcut tüm uçlar çağrılır, Then davranış birebir aynı (mevcut 845 backend / 360 authz testi değişmeden yeşil).
5. [High] AC-5 Given X engagement listesini çağırır, When X hem engagement'ın talent'ı hem org üyesi/koordinatör, Then liste kapsam birleşimidir (talent_id OR organization_id IN org_ids OR institution_id IN institution_ids), tek sorgu, tekrar kayıt yok.
6. [High] AC-6 Given yetki kararları, When kod incelenir, Then `principal.kind` hiçbir yetki kararında okunmaz (statik koruma testi); kind yalnız gösterim alanıdır.
7. [High] AC-7 Given X bir org/kurumun üyesi değil, When o kaynağa erişir, Then 404 (403 değil); çoklu rol sınırları genişletmez (birleşim = tam olarak üyelikleri).
8. [Medium] AC-8 Given X'in üyeliği silinir, When sonraki istekte kaynağa erişir, Then 404 (Principal her istekte DB'den kurulur; JWT'de rol taşınmaz).

Güvenlik AC'leri (threat-model, STRIDE-lite; atlanan: R — yeni audit kaynağı yok, D — sorgu şekli değişmiyor, S — kimlik doğrulama değişmiyor):
- AC-S1 [Critical] (E, kendi kendine işlem) Given X engagement E'nin talent'ı ve aynı zamanda E'nin org'unun üyesi/ADMIN'i veya E'nin kurumunun COORDINATOR'ı, When X org/koordinatör tarafı eylemini (attestation, ORG_TO_TALENT evaluation, PENDING_APPROVAL→ACTIVE/REJECTED, ACTIVE→CANCELLED/PENDING_EVALUATION org-tarafı, task oluşturma) kendi engagement'ında yapar, Then reddedilir (mevcut eylemin yetkisiz-hata türüyle: attestation 409 SELF_ATTESTATION_FORBIDDEN (mevcut sözleşme, test_attestation_self_attestation_409), diğerleri mevcut TransitionForbidden); talent-tarafı eylemleri (DRAFT→PENDING, deliverable, TALENT_TO_ORG) çalışmaya devam eder. Kurulan birleşim self-dealing'i yeni açmamalı. Not: kendi engagement'ını attest etme zaten servis katmanında 409 ile engelliydi; bu AC o sözleşmeyi koruyup diğer org/koordinatör eylemlerine genişletir. Güncelleme (kullanıcı kararı delegasyonu, 2026-10-01): ilk taslak 404 diyordu, mevcut 409 sözleşmesi korundu.
- AC-S2 [Critical] (T, E) Given X org O'ya üye ama O2'ye değil, When body/path'te O2 veya başka talent_id verir, Then 404; kaynak sahipliği oturumdan çıkar, istemci kimliğine güvenilmez. Çoklu rolde bir rolün üyeliği diğer rolün kaynağına yetki vermez (ör. talent olarak kurum K'ya bağlı olmak K'nın koordinatörlük kapsamını açmaz).
- AC-S3 [Critical] (I) Given PRIVATE kanıt, When platform admin veya aynı kullanıcının org/kurum rolü kanıt uçlarını çağırır, Then yalnız owner_talent_id == talent_id olan kayıtlar döner; org/kurum üyeliği başkasının kanıtını açmaz, admin hâlâ göremez.
- AC-S4 [High] (E) Given X yalnız org MEMBER (ADMIN değil) ve ayrıca başka org'un ADMIN'i, When MEMBER olduğu org'da ADMIN-only uç çağırır, Then 404; ADMIN yetkisi org bazlı (`org_id in org_admin_ids`), roller arası sızmaz. Aynısı kurum ADMIN vs COORDINATOR için.
- AC-S5 [High] (E) Given kullanıcı yalnız INST_ADMIN, When engagement geçişi dener, Then bugünkü gibi reddedilir (koordinatör yetkisi yalnız role=COORDINATOR üyelikten türer; INST_ADMIN'e geçiş yetkisi YET-190'a bırakılır, sessizce genişletilmez).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Çoklu rollü kullanıcı, her rolünün kaynağına erişir | mevcut uçların 2xx'i | mevcut eylem | rollerinin hepsi çalışır | AC-1,2,3 |
| 2 | Girdi geçersiz (bozuk UUID) | mevcut davranış (404/422) değişmez | yok | aynı | AC-4 |
| 3 | Kaynak yok | 404 | yok | aynı | AC-7 |
| 4 | Üyeliği olmayan kaynak | 404 (403 değil) | yok | "bulunamadı" | AC-7,S2 |
| 4b | Kendi engagement'ında org/koordinatör eylemi | attestation: 409 SELF_ATTESTATION_FORBIDDEN; diğerleri mevcut TransitionForbiddenError (403, mevcut S6 istisnası) | yok | işlem reddedilir | AC-S1 |
| 5 | DB hatası | 500, açık transaction rollback | yok | aynı | — |
| 6 | Zaman aşımı | satır silindi: yeni ağ çağrısı yok | — | — | — |
| 7 | Kısmi başarı | satır silindi: bu iş salt okuma/karar mantığı, yazma adımı eklenmiyor; mevcut servislerin transaction davranışı aynı | — | — | — |
| 8 | Hiçbir şey yapılamadı ama hata yok | Kapsam boş ise liste uçları 200 + [] (mevcut sözleşme); tekil kaynak uçları 404. Boş liste "üyelik yok" ile "veri yok"u ayırmaz: bilinçli (varlık sızıntısı olmasın) | yok | boş liste | AC-5,7 |

Kısmi başarı: bu görevde yazma yolu eklenmiyor; bir istekte yetki kararı ya tam geçer ya tam reddedilir.
Hiçbir şey yapılamadı ama hata da yok: yetki reddi her zaman açık hata (404/403) döner, sessiz başarı yok.
Boş sonuç ↔ hata ayrımı: liste uçlarında boş = kapsam dışı/veri yok (ayrım kasıtlı yapılmaz); tekil uçlarda 404.

## Test Strategy
Unit: 25% — `Principal` türetilmiş koordinatör kümesi, scoped_* sorgu derlemesi, statik "kind okunmaz" koruma testi.
Integration: 75% — çoklu rol matrisi (authz-test saldırgan matrisi), gerçek DB, mevcut authorization paketi regresyon olarak.
E2E: 0% — frontend dokunulmuyor (823 test aynı kalmalı).

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (değişen authz satırlarında dal kapsamı).
Regresyon tabanı: backend 845 geçti/0 kırık/5 atlandı; tests/authorization 360 geçti/4 atlandı; frontend 823/823. Sayılar düşmemeli.
Lint/tip: `python -m ruff check .`, `python -m mypy app` temiz.
Migration: gerekmiyor (yalnız kod; şema değişmez).

## Bilinçli davranış değişiklikleri (uygulama sonrası kayıt)
- `create_engagement`: her kullanıcının talent profili olduğundan, org üyesi/koordinatör/INST_ADMIN olan kullanıcı kendi talent_id'siyle herhangi bir org adına engagement açabilir (eskiden yalnız kind=TALENT yapabiliyordu). Org üyesi başka talent için yalnız kendi org'larında açabilir (değişmedi). Gerekçe: AC-2 (rol edinmek talent işlevini kaybettirmemeli). Red-team: kasıtlı kabul.
- Self-attestation: kendi engagement'ında attest → 409 SELF_ATTESTATION_FORBIDDEN (mevcut sözleşme korundu; ilk taslak 404'tü). Saf talent → 403 (değişmedi).
- Platform admin PRIVATE kanıt → 403 (mevcut AC-S3 sözleşmesi; authz_test satır 14 buna göre).
- Koordinatör+org üyesi aynı engagement'ta: evaluation'da org üyesi dalı öncelikli (ORG_TO_TALENT serbest); eskiden kind=COORDINATOR olduğu için reddedilirdi.

## Kapsam Dışı
- INST_ADMIN'e engagement geçiş yetkisi ve seed'e COORDINATOR (YET-190).
- Rızasız üyelik ataması (YET-176), Sybil/sahte deneyim üretimi (YET-177; AC-S1 yalnız yeni birleşimin açığı genişletmemesi için).
- Üyelik `status` (davet bekleyen) filtrelemesi, son-admin koruması (YET-236).
- Frontend (AppShell vb.), şema/migration, yeni endpoint.

## Etkilenen Dosyalar/Modüller (bilinen)
Bkz. frontmatter; ayrıca testlerde `Principal(kind=...)` kuran 5 dosya ve 149 `kind=` kullanımı (alanlar tutarlıysa geçerli kalır).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı. Tüm arama/komutlar `c:\Users\Meyrem\Desktop\P\yetkin360` altında (backend/ ve obss_project/) sınırlı tutulur; `git log -p --all` ve kök dizinden `grep -r` yok.

## Rollback Beklentisi
Yalnız kod değişikliği, migration yok: geri alma = commit revert. Yetki mantığı hatalıysa default-deny korunur (belirsizlikte reddet).

## Risks
- En riskli değişiklik: yetki çekirdeği. Hafif bir birleşim hatası tenant sızıntısı olur → AC-S2/AC-7 saldırgan matrisi zorunlu.
- AC-S1 mevcut davranışı sıkılaştırır (ORG_ADMIN+talent self-attest kapanır); ilgili eski test varsa kırılır, kod mu test mi yanlış anlaşılıp sorulur.
- Testlerin `Principal(kind=..., listeler tutarsız)` kurduğu yerler birleşimle farklı davranabilir; kırık görülürse test gevşetilmez, önce sorulur.
- Org üyeliği `status` (PENDING davet) Principal'da filtrelenmiyor; bu iş değiştirmiyor (kabul edilen risk, ayrı görev).
- Kabul edilen: rate limit/audit değişmiyor.

## Assumptions
- `kind` alanı Principal'da kalır (gösterim/geriye uyum), yetki kararlarında okunmaz; hesaplanışı değişmeyebilir.
- Koordinatör yetkisi = `institution_ids` içinde olup `institution_admin_ids` içinde olmayan kurumlar (tablo tek satır/kullanıcı-kurum: UNIQUE, rol tek). Yeni alan eklenmez, türetilmiş özellik olur; böylece mevcut testler geçerli kalır.
- Migration gerekmez.
- Platform admin kapsamı değişmez (kind ile ilgisi yok).

## Unknowns
- AC-S1'in org MEMBER (ADMIN olmayan) için de uygulanması (önerilen: evet, org-tarafı eylemin hepsinde).
- Mevcut testlerden hangileri kind-tutarsız Principal kuruyor (plan adımında sayılacak).

## Sorular ve Cevaplar (ham kayıt)
Kullanıcı "yalnız şart olan sorular" dedi; Jira açıklaması kabul kriteri sayıldı, 4z alt-ajan çağrısı yapılmadı. Onay noktasında kullanıcıya sorulacak kararlar: (1) AC-S1 kendi-engagement'ı reddi kapsamı (YET-177 ile örtüşme), (2) INST_ADMIN geçiş yetkisinin YET-190'a bırakılması, (3) `kind` alanının Principal'da kalması.
