---
task_slug: yet-2-yetkilendirme-cekirdegi
jira_id: YET-2
saga_task_id: null
threat_model: done
priority: critical
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 40
  integration: 50
  e2e: 10
affected_modules:
  - backend/app/services/authorization.py (yeni)
  - backend/app/models/audit.py (yeni)
  - backend/alembic/versions/ (yeni migration: audit_events + trigger)
  - backend/tests/test_authorization.py (yeni)
  - backend/tests/test_audit_events.py (yeni)
---

# ATDD — yet-2-yetkilendirme-cekirdegi

## Jira Kaynağı
[YET-2 — Yetkilendirme çekirdeği: can() + scoped_*() + audit_events](https://kuyusuzyusuf123.atlassian.net/browse/YET-2)

User Story (Jira'dan birebir): "As any actor calling the API, I want every data access to pass through a central can()/scoped_*() layer, so that unauthorized access always returns 404 instead of leaking resource existence, and no endpoint can bypass authorization."

PLAN.md Faz 1, madde 1.2 — **fazın kilit maddesi**, `docs/AUTHORIZATION.md`'ye dayanır. `YET-1` (migration) tamamlandığı için artık bloke değil.

**Kapsam sınırlama kararı (önemli):** `docs/AUTHORIZATION.md` §5'teki devasa test matrisi (A1-H4) `Engagement`/`Evidence`/`Attestation`/`Evaluation` gibi Faz 2 tabloları üzerine kurulu — bu tablolar henüz yok (sadece `YET-1`'in 7 tablosu var: users, institutions, institution_members, talent_profiles, organizations, organization_members, skills). Bu görev **can()/scoped_*() çekirdek mekanizmasını** ve **audit_events**'i inşa eder, mevcut 7 tablo üzerinde örneklendirir (`scoped_talent_profiles`, `scoped_organizations`). Tam test matrisi (Engagement vb.) `YET-7/8/9`'da genişleyecek.

## Persona
Backend geliştiriciler (`YET-7/8/9/10/11`'i yazacak kişiler) — doğrudan son kullanıcıya görünmez. Bu bir iç kütüphane/servis katmanı, HTTP dış yüzeyi bu görevde yok.

## Hedef (Neden)
`docs/AUTHORIZATION.md`'nin kesinleşmiş tasarımını (`Principal` + `can()` + `scoped_*()` + 404/403 ayrımı) gerçek koda dönüştürmek — bu madde Faz 1'in temelidir, `YET-7/8/9/10/11`'deki tüm uçlar buna bağımlı. Yetkilendirme sonradan eklenirse delikli olur (CLAUDE.md kuralı).

## User Story
As a backend developer (YET-7/8/9/10/11'i yazacak kişi)
I want merkezi bir can()/scoped_*() yetkilendirme çekirdeği ve audit_events altyapısı
So that her yeni uç aynı güvenli varsayılanı kullanabilsin, kapsam dışı erişim otomatik olarak 404 üretsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `Principal` dataclass'ı (`user_id, kind, talent_id, org_ids, org_admin_ids, institution_ids, is_platform_admin, is_suspended`), When bir principal oluşturulur, Then tüm `kind` değerleri (`ANONYMOUS, TALENT, ORG_MEMBER, ORG_ADMIN, ORG_SUPERVISOR, COORDINATOR, INST_ADMIN, PLATFORM_ADMIN, SUSPENDED`) geçerli enum değeri olarak kabul edilir.
2. [Critical] Given `scoped_talent_profiles(session, principal)` ve `scoped_organizations(session, principal)` fonksiyonları, When farklı `principal.kind` değerleriyle çağrılır, Then her biri kendi kapsamına göre filtrelenmiş bir SQLAlchemy `Select` nesnesi döner (çıplak `select(Model)` hiçbir yerde kullanılmaz).
3. [Critical] Given `can(principal, action, resource) -> bool`, When principal'ın kendi kaynağı için tanımlı bir action ile çağrılır, Then `True` döner; başka bir principal'ın kaynağı için çağrılırsa `False` döner.
4. [Critical] Given `audit_events` tablosu (bigserial PK, `actor_user_id`, `actor_ip`, `action`, `subject_type`, `subject_id`, `result` CHECK IN ('SUCCESS','DENIED','ERROR'), `metadata` jsonb, `created_at`), When `log_audit_event()` çağrılır, Then tabloya doğru alanlarla bir satır INSERT edilir.
5. [High] Given `get_scoped_or_404(scoped_fn, session, principal, resource_id)` yardımcı fonksiyonu, When `scoped_fn` sonucu boşsa, Then `None` döner (çağıran kod bunu HTTP 404'e çevirir — bu görevde HTTP entegrasyonu yok, sadece helper'ın kendisi).
6. [Critical/AC-S1] Given `can()`'a `principal.kind`/`action` için tanımlı OLMAYAN bir kombinasyon verilir, When `can()` çağrılır, Then `False` döner (exception fırlatmaz, asla `True` varsaymaz — default-deny).
7. [Critical/AC-S2] Given Org A ve Org B'ye ait ayrı `Organization`/`TalentProfile` kayıtları gerçek Postgres'te, When Org A principal'ıyla `scoped_organizations()`/`scoped_talent_profiles()` çağrılır, Then sorgu SONUCUNDA Org B'ye ait HİÇBİR kayıt dönmez — filtreleme SQL WHERE'de olur (üretilen SQL incelenerek doğrulanır), Python tarafında post-filter değil.
8. [Critical/AC-S3] Given `audit_events`'e bir satır INSERT edilmiş, When bu satıra UPDATE veya DELETE denenir (hem ORM hem raw SQL yoluyla), Then veritabanı `BEFORE UPDATE OR DELETE` trigger'ı `RAISE EXCEPTION` ile engeller — uygulama kodu bunu bypass edemez.
9. [High/AC-S4] Given `scoped_*()` principal'ın kapsamı dışında kalan bir kayıt için hiç satır döndürmez, When `get_scoped_or_404()` bu boş sonucu işler, Then "kayıt gerçekten yok" durumuyla AYNI sonucu (`None`) üretir — bu bilinçli bir tasarım kararıdır (404 kaynağın varlığını sızdırmaz).
10. [High/AC-S5] Given bir çağıran `scoped_*()`'i atlayıp `can()`'ı principal'a ait OLMAYAN bir resource ile doğrudan çağırır, When `can()` çalışır, Then resource'un principal'a ait olup olmadığını kendi içinde de kontrol eder ve `False` döner (defense-in-depth — `scoped_*()`'e güvenmeyen ikinci savunma katmanı).
11. [Medium/AC-S6] Given `log_audit_event()` çağrılırken `metadata` alanına bilinen hassas anahtarlar (`password`, `password_hash`, `email`, `tc_kimlik_no`) geçirilir, When kayıt INSERT edilir, Then bu anahtarlar reddedilir (`ValueError`) — ham PII `audit_events`'e asla yazılmaz.

## Threat Model
Çağrıldı — AC-S1 ile AC-S6 arası (yukarıdaki Acceptance Criteria'nın 6, 7, 8, 9, 10, 11. maddeleri) STRIDE-lite analizinden üretildi:
- **Elevation of Privilege** → AC-S1 (`can()` default-deny), AC-S5 (`can()` kendi içinde sahiplik kontrolü, `scoped_*()` bypass edilse bile)
- **Information Disclosure** → AC-S2 (tenant izolasyonu / BOLA), AC-S4 (boş sonuç ↔ "yok" ayrımı, kasıtlı olarak ayrılamaz), AC-S6 (audit log'da PII sızıntısı)
- **Repudiation** → AC-S3 (audit_events immutability, veritabanı seviyesinde)

`authz-test` skill'i çağrıldı — BOLA/tenant-izolasyon test kalıbı (`test-copilot`'a extra_instructions olarak verilecek): en az iki farklı principal (Org A / Org B) ile karşılaştırmalı test, "boş liste güvenli değildir" prensibi (AC-S4'te bilinçli olarak ele alındı), mock'lu authz testi kabul edilmez (gerçek Postgres'e karşı).

**Kabul edilen riskler (bilinçli kapsam dışı):**
- **Spoofing** (kimlik doğrulama/token doğrulama) — bu görevde yok, `Principal`'ın dışarıdan doğru kurulduğu varsayılır; gerçek token/session doğrulaması `YET-4`'e ait.
- **Tampering** (client girdisi doğrulama, body'den `role`/`user_id` okuma) — bu görevde HTTP/request parsing yok.
- **Denial of Service** (rate limit) — bu görevde HTTP yüzeyi yok; `docs/SECURITY.md` §3'e ve `YET-4`'e ait.

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — bu görev bir LLM agent/sub-agent davranışını değiştirmiyor, klasik backend servis kodu.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu bir servis katmanı/kütüphane kodu (HTTP endpoint değil) — "dönen değer" fonksiyon dönüş değeri/exception davranışıdır.

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | `can()` bool döner, `scoped_*()` filtrelenmiş `Select` döner, `log_audit_event()` satır INSERT eder | `audit_events`'e 1 satır yazılır | (Çağıran kod — henüz HTTP yok) | AC-1..4 |
| 2 | Girdi geçersiz | `can()`'a tanımsız `action` verilirse → `False` (AC-S1); `log_audit_event()`'e CHECK dışı `result` değeri verilirse DB `IntegrityError` | Yok (transaction rollback) | Exception (çağıran kod yakalar) | AC-6 |
| 3 | Kaynak yok | `scoped_*()` kapsam dışı kayıt için boş sonuç döner (satır yok, exception yok); `get_scoped_or_404()` bunu `None`'a çevirir | Yok | (Çağıran kod 404'e çevirir, bu görevde değil) | AC-5, AC-9 |
| 4 | Yetkisiz erişim | `can()` `False` döner (exception fırlatmaz) | Yok | (Çağıran kod 403'e çevirir, bu görevde değil) | AC-3, AC-10 |
| 5 | Dış bağımlılık hatası | Postgres bağlantısı koparsa SQLAlchemy exception'ı yukarı fırlatılır, yutulmaz | Yok | Exception | — |
| 6 | Zaman aşımı | N/A | — | — | Bu bir DB sorgu katmanı, ağ çağrısı/timeout mantığı barındırmaz; connection pool seviyesinde zaten yönetiliyor |
| 7 | **Kısmi başarı** | N/A | — | — | `can()`/`scoped_*()` atomik okuma operasyonları; `log_audit_event()` tek bir INSERT — ya commit olur ya olmaz, ara durum yok |
| 8 | **Hiçbir şey yapılamadı ama hata yok** | `scoped_*()` kapsam dışı/hiç kayıt yoksa boş sonuç döner — bu GEÇERLİ ve BEKLENEN bir durumdur (hata değil); `audit_events`'e bu olay için log YAZILMAZ (can() gürültüsü kararı) | Yok | — | AC-9 |

Kısmi başarı: N/A — yukarıda gerekçelendirildi, bu katmanda atomik operasyonlar dışında bir şey yok.
Hiçbir şey yapılamadı ama hata da yok: `scoped_*()`'in boş dönmesi sessiz başarı DEĞİLDİR — bu, "kapsam dışı" ile "gerçekten yok" durumlarının BİLİNÇLİ olarak ayırt edilemez tutulmasıdır (AC-S4, 404 sızıntı önleme tasarımı). `can()` çağrıları audit_events'e YAZILMAZ (gürültü) — sadece gerçek yazma/hassas okuma eylemleri loglanır, ama bu görev sadece `log_audit_event()` helper'ını kurar, gerçek çağrı noktaları `YET-4/7/8/9`'a kalır.
Boş sonuç ↔ hata ayrımı: Bilinçli olarak AYRILMAZ (AC-S4) — kapsam dışı kayıt da, gerçekten var olmayan kayıt da aynı `None`/404 sonucunu üretir; bu 404'ün "bu kaynak var ama senin değil" bilgisini sızdırmamasının nedenidir.

## Test Strategy
Unit: 40% — `can()` karar mantığı (her `Principal.kind` × action kombinasyonu, default-deny testleri AC-S1), `Principal` oluşturma, `log_audit_event()`'in PII-guard mantığı (AC-S6)
Integration: 50% — `scoped_*()` gerçek Postgres'e karşı (Org A/Org B fixture'larıyla tenant izolasyonu, AC-S2), `audit_events` immutability trigger testi (AC-S3, hem ORM hem raw SQL UPDATE/DELETE denemesi), `log_audit_event()` gerçek INSERT testi
E2E: 10% — `Principal` oluştur → `scoped_*()` sorgusu → `can()` kontrolü zinciri, HTTP olmadan uçtan uca (AC-3, AC-5)

`test-copilot`'a verilecek extra_instructions (authz-test kalıbı): en az iki farklı principal (Org A / Org B, Talent A / Talent B) ile karşılaştırmalı test yaz; "scoped_*() boş liste dönerse bunu PASS'e çevirme, gerçekten filtrelenip filtrelenmediğini SQL'i inceleyerek doğrula" prensibini uygula; mock'lu authz testi KABUL EDİLMEZ.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (`can()`/`scoped_*()`/`log_audit_event()` için)
Performance Target: Yok
Memory: Yok
Diğer ölçülebilir kriterler:
- Her `Principal.kind` için en az bir pozitif + bir negatif test
- `audit_events` immutability testi (trigger tetikleniyor mu) geçer
- Çıplak `select(Model)` kullanımı yok (code-review checklist maddesi; tam AST-tabanlı ruff custom rule bu görevin kapsamı dışında, backlog notu)

## Kapsam Dışı
- Gerçek HTTP endpoint'leri/middleware entegrasyonu — `YET-4/7/8/9`'a ait
- `docs/AUTHORIZATION.md` §5'teki TAM test matrisi (Engagement/Evidence/Attestation/Evaluation) — bu tablolar henüz yok
- Break-glass admin akışı — Faz 5
- PostgreSQL RLS — MVP'de yok (docs/AUTHORIZATION.md §3 kararı)
- `audit_events` partition stratejisi — Faz 5
- `log_audit_event()`'in gerçek çağrı noktalarının servislere serpiştirilmesi — `YET-4/7/8/9`'a kalır, bu görev sadece helper'ı kurar
- Çıplak `select(Model)` kullanımını otomatik tespit eden tam bir AST-tabanlı ruff custom linter — backlog notu, bu görevde sadece code-review checklist maddesi

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/services/authorization.py` — `Principal`, `can()`, `scoped_talent_profiles()`, `scoped_organizations()`, `get_scoped_or_404()`
- `backend/app/services/audit.py` — `log_audit_event()`
- `backend/app/models/audit.py` — `AuditEvent` SQLAlchemy modeli
- `backend/alembic/versions/` — yeni migration: `audit_events` tablosu + `BEFORE UPDATE OR DELETE` trigger
- `backend/tests/test_authorization.py`, `backend/tests/test_audit_events.py` — yeni test dosyaları

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki görevlerde teyit edildi): `projelerim/yetkin360` kendi git reposu, `projelerim/obss`'den bağımsız. Arama bu klasörle sınırlı kalmalı.

## Rollback Beklentisi
1 migration (`audit_events` + trigger) + servis katmanı kodu. Henüz production/staging'e deploy edilmedi — geliştirme ortamında migration serbestçe düzenlenip yeniden denenebilir. Prod'a gittikten sonra CLAUDE.md kuralı geçerli olur: uygulanmış migration elle değiştirilemez, düzeltme yeni migration ile yapılır.

## Risks
- `can()`'ın hem action-bazlı yetki tablosunu HEM DE resource sahiplik kontrolünü (AC-S5) kendi içinde yapması, fonksiyonun karmaşıklığını artırabilir — CAVEMAN ilkesiyle dengelenmeli, gereksiz soyutlama eklenmemeli.
- Çıplak `select(Model)` kullanımını engelleyen otomatik bir CI kontrolü bu görevde YOK (sadece code-review checklist) — bu, ileride birinin yanlışlıkla çıplak `select` yazıp fark edilmemesi riski taşır (kabul edilen risk, backlog'a not düşüldü).

## Assumptions
- `Principal` nesnesinin doğru kurulduğu (doğru `user_id`/`org_ids`/`institution_ids` ile) varsayılır — bu görev `Principal`'ı OLUŞTURMAZ, sadece tanımlar ve tüketir; gerçek kimlik doğrulamadan `Principal` üretimi `YET-4`'e ait.
- `actor_ip` parametresi bu görevde `None`/nullable kabul edilir — HTTP layer entegre olunca (`YET-4`) gerçek IP geçirilecek.

## Unknowns
- Çıplak `select(Model)` kullanımını tespit eden otomatik bir lint/CI kuralının ne zaman yazılacağı netleşmedi — backlog'a not düşüldü, ayrı bir görev olabilir.
- `docs/AUTHORIZATION.md`'deki açık soru (`POST /engagements`'i kimin başlatabileceği) bu görevi etkilemiyor (Engagement henüz yok), ama `YET-2`'nin `can()` tasarımı gelecekte bu karara uyum sağlayabilmeli — şimdilik varsayım gerektirmiyor.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Backend geliştiriciler (YET-7/8/9/10/11'i yazacaklar) (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
2. Happy path → Principal + can() + 2 örnek scoped_*() fonksiyonu, gerçek Postgres'e karşı test, HTTP yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. scoped_*() boş sonuç → 404 çevrimi → get_scoped_or_404() helper'ı bu görevde yazılmalı (Sonnet 5 low alt-ajanı tarafından yanıtlandı: 3 kez farklı implement edilme riski)
4. can() tanımsız action → default DENY (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. audit_events'e ne yazılır → can() çağrıları değil, sadece log_audit_event() helper'ı ve tablo kurulur (Sonnet 5 low alt-ajanı tarafından yanıtlandı: gürültü riski)
6. audit_events UPDATE/DELETE → BEFORE trigger + RAISE EXCEPTION (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Başarı ölçütü → ≥90% dal kapsamı + her kind için pozitif/negatif test + immutability testi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı → HTTP entegrasyonu, tam test matrisi, break-glass, RLS, partition (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Test stratejisi → unit 40/integration 50/e2e 10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: DB-ağırlıklı katman)
10. Rollback → henüz prod'a deploy edilmedi, serbest (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Lint kuralı bu görevde mi → hayır, code-review checklist yeterli, tam linter backlog (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. actor_ip → nullable, None kabul edilir (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
13. Threat-model AC-S1..S6 → STRIDE-lite analizinden (threat-model skill tarafından üretildi, bu oturumda)
14. authz-test kalıbı → BOLA/tenant izolasyon test prensibi, test-copilot'a extra_instructions olarak verilecek (authz-test skill tarafından üretildi, bu oturumda)
