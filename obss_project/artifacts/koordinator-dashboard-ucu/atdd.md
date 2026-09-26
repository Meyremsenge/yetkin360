---
task_slug: koordinator-dashboard-ucu
jira_id: YET-107
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 85
performance_target: "<200ms"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/api/institutions.py
  - backend/app/services/engagement.py
  - backend/app/services/authorization.py (scoped_engagements — değişiklik gerekmeyebilir)
  - backend/tests/test_institution_authorization.py (veya yeni test dosyası)
  - backend/alembic/versions/ (yeni migration — index, kullanıcı onayı gerektirir)
---

# ATDD — koordinator-dashboard-ucu

## Jira Kaynağı
[YET-107 — [PLAN 3.3] Koordinatör dashboard ucu (durum takibi + bekleyen değerlendirme)](https://kuyusuzyusuf123.atlassian.net/browse/YET-107)
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.3.\nSahip: @be1"
Tip: Görev · Öncelik: Medium · Durum: Yapılacaklar
Not: Jira issue'sunda ayrı bir Acceptance Criteria alanı yok — kaynak PLAN.md 3.3 satırı ve final-analiz.md §14/§39 (bu ekran "ürünü satan ekran" olarak tanımlanmış).
Saga: bu oturumda Saga MCP sunucusuna bağlanılamadı (araç listesinde yok) — `saga_task_id` kaydedilemedi, ilerleyen bir oturumda `jira-sync`/`saga` skill'i ile senkronize edilmeli.

## Persona
Üniversite/MYO staj koordinatörü (COORDINATOR) veya kurum yöneticisi (INST_ADMIN) — kendi kurumunun tüm staj/engagement süreçlerini takip eden, genelde 1 akademisyen + 1 memurdan oluşan küçük ekip.

## Hedef (Neden)
Koordinatörün elle Excel'de takip ettiği iki soruyu ("hangi stajlar onayımı bekliyor?", "hangi bitmiş stajın değerlendirmesi hâlâ gelmedi?") tek istekte cevaplamak. final-analiz.md §14: "PENDING_EVALUATION... koordinatörün en çok kovaladığı durum... ürünün en kritik operasyonel ekranı bu listedir."

## User Story
As a kurum koordinatörü (COORDINATOR/INST_ADMIN)
I want kendi kurumumun onay bekleyen ve değerlendirme bekleyen engagement'larını tek bir uçtan görmek
So that her dönem harcadığım takip süresini (manuel Excel yerine) otomatikleştirebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir COORDINATOR/INST_ADMIN, kendi kurumunda 3 `PENDING_APPROVAL` ve 7 `PENDING_EVALUATION` durumunda engagement varken, When `GET /institutions/{kendi_institution_id}/dashboard` çağrılır, Then 200 döner ve `summary.pending_approval == 3`, `summary.pending_evaluation == 7`, iki liste de ilgili engagement kayıtlarını içerir.
2. [Critical] Given kimliği doğrulanmış bir COORDINATOR, When kendi `institution_ids` listesinde OLMAYAN bir `institution_id` ile bu uç çağrılır, Then **404** döner (403 değil) ve yanıt gövdesinde o kurumun hiçbir engagement verisi bulunmaz. (AC-S1)
3. [Critical] Given kimliği doğrulanmış bir TALENT veya ORG_MEMBER principal, When bu uç herhangi bir `institution_id` ile çağrılır, Then **404** döner (kurum var olsa bile). (AC-S2)
4. [High] Given kimliği doğrulanmamış (oturumsuz) bir istek, When bu uca çağrı yapılır, Then **401** döner. (AC-S4)
5. [High] Given COORDINATOR'ın kurumunda hiç engagement yoksa, When dashboard çekilir, Then 200 döner, `summary.pending_approval == 0`, `summary.pending_evaluation == 0`, iki liste de boş `[]` — hata değil.
6. [High] Given `institution_id` path parametresi geçerli bir UUID formatında değilse, When uç çağrılır, Then 422 döner (FastAPI path validasyonu).
7. [Critical] Given aynı kurumda hem `confidential=true` hem `confidential=false` engagement'lar varken, When COORDINATOR dashboard'unu çekiyor, Then response yalnızca `institution_id == principal.institution_ids` içindeki kayıtları döner — başka kurumun kaydı, `confidential` alanından bağımsız olarak asla sızmaz (institution_id filtresi sunucuda `principal.institution_ids`'ten kurulur, istemciden gelen hiçbir alandan değil). (AC-S3)
8. [Medium] Given kurumda `PENDING_APPROVAL`/`PENDING_EVALUATION` dışında durumlarda (ör. `ACTIVE`, `VERIFIED`, `DRAFT`) engagement'lar da varken, When dashboard çekilir, Then bu durumlar `summary`/listelere dahil edilmez — sadece iki hedef durum gösterilir (kapsam net).

## Threat Model
Çağrıldı — STRIDE-lite uygulandı, AC-S1–AC-S4 yukarıdaki Acceptance Criteria'ya eklendi.

- **Spoofing**: Mevcut oturum/JWT doğrulaması (`get_current_principal`) kullanılıyor, bu görevde yeni bir kimlik doğrulama mekanizması eklenmiyor — mevcut auth testleri kapsıyor, atlandı.
- **Tampering**: `institution_id` yalnız URL path'inden okunur ama yetki kararı **asla** bu path değerine güvenmez — `principal.institution_ids` (oturumdan türetilen) ile karşılaştırılır. → AC-S1, AC-S3.
- **Repudiation**: GET-only, state değişmiyor; audit event gerekmiyor — atlandı.
- **Info disclosure**: Cross-tenant sızıntı riski en yüksek risk — başka kurumun engagement'ı (özellikle `confidential=true` olanlar) asla listeye girmemeli. → AC-S3. Ayrıca yetkisiz principal (TALENT/ORG_MEMBER) veya yanlış kurum için 403 değil 404 dönülmeli (kaynak varlığı sızdırılmaz). → AC-S1, AC-S2.
- **DoS**: Sayfalama yok — kabul edilmiş risk, bkz. Risks bölümü (kurum başına engagement sayısı düşük, MVP'de YAGNI).
- **Elevation**: Yetki kontrolü sunucuda `scoped_engagements`/`principal.institution_ids` üzerinden yapılır, response şekillendirmesi (UI'da gizleme) değil. → AC-S1, AC-S2, AC-S4.

`authz-test` skill'i bu adımda ÇAĞRILMADI: uç henüz kodlanmadı, `authz-test`'in "gerçek çalışan sisteme karşı doğrulama" adımı canlı bir endpoint gerektiriyor. Bu, pipeline'ın `test-copilot`/`verify` adımında (uç yazıldıktan sonra) çağrılmalı — bkz. Unknowns.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (kendi kurumu, veri var) | `200 {"institution_id": "...", "summary": {"pending_approval": 3, "pending_evaluation": 7}, "pending_approval": [{"id","talent_id","organization_id","title","started_on"}...], "pending_evaluation": [{"id","talent_id","organization_id","title","ended_on"}...]}` | Yok (salt okunur) | Onay/değerlendirme bekleyen listeler + sayaçlar | AC-1 |
| 2 | Girdi geçersiz (institution_id UUID formatında değil) | `422 {"code":"VALIDATION_ERROR", ...}` (FastAPI otomatik) | Yok | Alan hatası | AC-6 |
| 3 | Kaynak yok / başka kurum (institution_id principal scope'unda değil veya DB'de yok) | `404 {"code":"NOT_FOUND","message":"Institution bulunamadı."}` | Yok | "Bulunamadı" | AC-2 |
| 4 | Yetkisiz rol (TALENT/ORG_MEMBER) | `404` (aynı NOT_FOUND — rol farkı sızdırılmaz) | Yok | "Bulunamadı" | AC-3 |
| 5 | Oturumsuz istek | `401 {"code":"UNAUTHORIZED","message":"Kimlik doğrulama gerekli."}` | Yok | Giriş gerekli mesajı | AC-4 |

Kısmi başarı: **Uygulanmaz** — GET-only, tek sorgu/tek response; DB'ye yazma yok, dolayısıyla "bir kısmı yazıldı kalanı yazılamadı" durumu oluşamaz.
Hiçbir şey yapılamadı ama hata da yok: Kurumun hiç engagement'ı yoksa `200` + boş listeler + sıfır sayaçlar döner (AC-5) — bu "veri yok" durumudur, sessiz bir "başarı" iddiası taşımaz çünkü zaten hiçbir yazma işlemi yoktu.
Boş sonuç ↔ hata ayrımı: "Veri yok" (kurumun engagement'ı yok) → `200` + boş liste. "Yetkin yok" (başka kurum veya yanlış rol) → `404`. İkisi asla aynı gövdeyi paylaşmaz; ayrım `principal.institution_ids` kontrolünün `scoped_engagements` çağrısından ÖNCE yapılmasıyla sağlanır.

Dış bağımlılık hatası / Zaman aşımı satırları silindi: bu uç DB dışında dış bağımlılığa (e-posta, S3, AI) dokunmuyor; özel bir timeout sözleşmesi tanımlı değil, DB sorgu süresi (institution_id, status) index'i ile kontrol altında (bkz. Benchmark).

## Test Strategy
Unit: 70% — `engagement.py`'de yeni `get_coordinator_dashboard(session, principal, institution_id)` servis fonksiyonu: scope filtreleme, sayaç doğruluğu, boş liste, durum filtresi (sadece PENDING_APPROVAL/PENDING_EVALUATION).
Integration: 20% — endpoint üzerinden 401/404/422/200 senaryoları, `pytest tests/authorization -q` içinde cross-tenant (başka kurum → 404) ve rol (TALENT/ORG_MEMBER → 404) testleri.
E2E: 10% — happy path: COORDINATOR olarak login → dashboard çek → beklenen sayaçları doğrula.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: <200ms (kurum başına engagement sayısı düşük; `(institution_id, status)` index'i ile karşılanır)
Memory: —
Görsel/UI kriteri: Yok — bu bir backend ucu, UI/frontend 3.9'da ayrı görev.
Diğer ölçülebilir kriterler: Yeni endpoint = aynı commit'te yetkilendirme testi zorunlu (CLAUDE.md).

## Kapsam Dışı
- Hatırlatma/bildirim gönderme (PLAN 3.4, ayrı görev, `POST /institutions/{id}/reminders`).
- Frontend gösterimi (PLAN 3.9, ayrı görev).
- Filtreleme/sıralama/sayfalama query parametreleri — MVP'de tamamen kapsam dışı (kurum başına engagement sayısı düşük, YAGNI).
- `PENDING_APPROVAL`/`PENDING_EVALUATION` dışındaki durumların (`ACTIVE`, `EVALUATED`, `VERIFIED`, `DISPUTED`, `RESOLVED`, `CANCELLED`, `REJECTED`, `DRAFT`) listelenmesi.
- Kurum dashboard'u (PLAN 3.5, ayrı görev — org tarafı, bu görev institution/coordinator tarafı).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/institutions.py` — yeni `GET /institutions/{institution_id}/dashboard` route
- `backend/app/services/engagement.py` — yeni `get_coordinator_dashboard()` servis fonksiyonu
- `backend/app/services/authorization.py` — mevcut `scoped_engagements()`/`scoped_institutions()` kullanılır, değişiklik beklenmiyor (doğrulanmadı, kod okuma anında teyit edildi: her ikisi de COORDINATOR/INST_ADMIN'i institution_ids ile zaten filtreliyor)
- Yeni migration: `(institution_id, status)` index + `WHERE status='PENDING_EVALUATION'` partial index — **kullanıcı onayı gerekiyor, CLAUDE.md "migration oluşturma" onay listesinde.**

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup olmadığı bu oturumda kontrol edilmedi. Sonraki adımlar (plan/code-copilot/test-copilot/red-team) arama kapsamını `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\yetkin360` ile sınırlı tutmalı, sınırsız arama yapmamalı.

## Rollback Beklentisi
Endpoint GET-only olduğu için state rollback'i yok — hata durumunda (404/422/401) DB'de hiçbir değişiklik oluşmaz. Eklenecek index migration'ı için `alembic upgrade head` **ve** `alembic downgrade -1` ikisi de test edilmeli (doğrulama matrisi kuralı, CLAUDE.md).

## Risks
- Sayfalama olmadan bırakılması kabul edilmiş bir risktir: kurum başına engagement sayısının (yüzlerle) MVP ölçeğinde küçük kalacağı varsayımına dayanır. Bu varsayım yanlış çıkarsa (ör. büyük bir üniversite binlerce engagement biriktirirse) dashboard yanıt boyutu büyür — V2'de sayfalama eklenmesi gerekir.
- `saga_task_id` bu oturumda oluşturulamadı (Saga MCP bağlı değildi) — ilerleyen adımlarda iş takibi Saga'dan kopuk kalabilir, bir sonraki oturumda senkronize edilmeli.

## Assumptions
- Dashboard yanıtının `pending_approval`/`pending_evaluation` liste öğelerinde `talent_id`/`organization_id` UUID string olarak döneceği varsayıldı (mevcut `PostEngagementResponse` şemasındaki örüntüyle tutarlı) — kullanıcı onayı almadı, varsayım olarak işaretli.
- Route'un `institutions.py` router'ına (ayrı bir `dashboard.py` yerine) eklenmesi varsayıldı çünkü path `/institutions/{id}/dashboard` altında ve mevcut kurum-ilişkili uçlarla (members, link-requests) aynı router'da.

## Unknowns
- `authz-test` skill'inin canlı doğrulama adımı (gerçek sisteme karşı IDOR/tenant-leak probe'ları) uç kodlandıktan sonra `test-copilot`/`verify` aşamasında çalıştırılmalı — bu ATDD adımında endpoint henüz yok, çalıştırılamadı.
- Response şemasındaki alan seti (`title`, `started_on`/`ended_on` dışında ek alan gerekip gerekmediği — ör. `organization_name` gibi denormalize bir alan koordinatör için faydalı olabilir mi) `plan` adımında netleştirilmeli; bu ATDD'de minimal alan seti varsayıldı.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → COORDINATOR ve INST_ADMIN, ikisi de (Sonnet 5 low alt-ajanı tarafından yanıtlandı: `scoped_engagements` her ikisini de aynı şekilde scope'luyor, final-analiz §14/15'te ayrım yok).
2. Ana hedef/neden → onay+değerlendirme takibini tek istekte cevaplamak (Sonnet 5 low alt-ajanı tarafından yanıtlandı: final-analiz §14 "en kritik operasyonel ekran" tanımı).
3. Happy path (endpoint, JSON şekli) → `GET /institutions/{id}/dashboard`, query param yok, `summary`+iki liste (Sonnet 5 low alt-ajanı tarafından yanıtlandı: final-analiz §14/15 iki durumu öne çıkarıyor).
4. Edge case'ler (boş liste, yanlış kurum) → 200+boş / 404 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi tablosu → dolduruldu, "dış bağımlılık/zaman aşımı/kısmi başarı" satırları silindi (Sonnet 5 low alt-ajanı tarafından yanıtlandı: GET-only, DB dışı bağımlılık yok).
6. Başarı ölçütü → <200ms + index (Sonnet 5 low alt-ajanı tarafından yanıtlandı: final-analiz §14 index önerisi).
7. Kapsam dışı → hatırlatma/frontend/filtreleme-sayfalama/diğer status'ler (Sonnet 5 low alt-ajanı tarafından yanıtlandı: YAGNI + PLAN.md'deki ayrı madde numaraları).
8. Bağımlılıklar → institutions.py + engagement.py servis fonksiyonu (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör tarafından kod okumasıyla teyit edildi).
9. Performans/güvenlik kısıtı → (institution_id, status) + partial index gerekli (Sonnet 5 low alt-ajanı tarafından yanıtlandı: final-analiz §14 doğrudan öneriyor; migration için kullanıcı onayı hatırlatıldı).
10. Rollback → GET-only, state rollback yok; migration'ın kendi rollback'i ayrı test edilir (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → otomatik test (pytest + zorunlu authorization paketi) (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLAUDE.md zorunluluğu).
12. Test stratejisi oranı → 70/20/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: proje varsayılanı, servis katmanı ağırlıklı).
13. Threat-model tetikleyici (yetkilendirme + çok-kiracılı sınır) → AC-S1–AC-S4 eklendi (orkestratör tarafından `threat-model` skill'i ile, STRIDE-lite: Tampering/Info disclosure/Elevation kategorileri geçerli bulundu, Spoofing/Repudiation atlandı, DoS kabul edilmiş risk olarak not edildi).
