---
task_slug: yet-217-test-izolasyonu
jira_id: YET-217
saga_task_id: null
priority: high
threat_model: not-applicable  # Test altyapısı: yeni endpoint, kimlik/yetki, kullanıcı girdisi, dosya, PII, çok kiracı sınırı yok. Yalnız test DB'si ve CI adımı; sır yok (URL settings'ten türetilir).
coverage_target: 0  # Yeni üretim kodu yok; hedef "kırmızı test sayısı = 0"
performance_target: "backend tam paket < 120 sn (şu an ~56 sn)"
memory_target: null
test_strategy:
  unit: 0
  integration: 70
  e2e: 30
affected_modules:
  - backend/tests/conftest.py
  - backend/tests/test_outbox_worker.py
  - backend/tests/test_seed.py
  - backend/tests/test_evaluation.py
  - frontend/lib/api/evaluation.test.ts
  - frontend/app/calismalar/[id]/evidence-upload-form.test.tsx
  - frontend/app/calismalar/[id]/degerlendirme/evaluation-form.test.tsx
  - frontend/app/kurum/[id]/panel/page.test.tsx
  - .github/workflows/ci.yml
---

# ATDD — yet-217-test-izolasyonu

## Jira Kaynağı
[YET-217 — TEST-01: Test paketleri kırmızı (seed-data izolasyon sorunu)](https://kuyusuzyusuf123.atlassian.net/browse/YET-217) · Öncelik: High · Durum: Yapılacaklar
Açıklama (Jira'dan, özet birebir): Backend 13 başarısız (`test_outbox_worker.py` 9, `test_seed.py` 3, `test_evaluation.py` 1) — testler seed'li dev DB'ye karşı koşup global satır sayıyor ya da kuyruğun boş olduğunu varsayıyor. Frontend 9 başarısız (`lib/api/evaluation.test.ts` 6 — engagements.ts gerçek backend'e bağlandı ama testler mock varsayıyor; `evidence-upload-form`, `evaluation-form`, `kurum/[id]/panel` testleri). CI frontend'de vitest hiç koşmuyor — bu 9 kırık test CI'da görünmüyor. Sahip: Meyrem Şenge (backend), Elif Sara (frontend + CI vitest). Detay: HATA.md §7 TEST-01.

**Doğrulama (2026-10-01, bu oturum):** backend `pytest tests` → 13 failed / 812 passed / 5 skipped; frontend `vitest run` → 9 failed / 814 passed (4 dosya). Jira ile birebir.

## Persona
Takım geliştiricisi (backend + frontend) ve jüri/katkıcı: repoyu klonlayıp testi koşan kişi.

## Hedef (Neden)
Test paketi, dev DB'nin seed durumundan bağımsız ve her koşuda aynı sonucu vermeli. Şu an kırmızı paket gerçek regresyonları gizliyor ve CI frontend testlerini hiç görmüyor.

## User Story
As a geliştirici
I want testlerin seed'li dev DB'den ve gerçek backend'den bağımsız, deterministik koşması
So that kırmızı bir test gerçekten bir regresyon anlamına gelsin.

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given seed'li dev DB (20 talent, 36 skill, kuyrukta satır), When `pytest tests -q` koşar, Then 0 failed (13 kırığın hepsi yeşil; test silinmez, skip/xfail yok, assert gevşetilmez).
2. [Critical] Given boş/seed'siz bir DB ve seed'li bir DB, When aynı paket koşar, Then iki durumda da aynı sonuç (izolasyon: sonuç dev DB içeriğine bağlı değil).
3. [Critical] Given testler koşar, When bitince dev DB'ye bakılır, Then dev DB'de hiçbir satır eklenmemiş/silinmemiş/değişmemiş (özellikle outbox, talent_profiles, skill_signals). Commit eden testler (`skip_locked` testleri) dev DB'ye yazmaz.
4. [Critical] Given frontend, When `npm run test` (vitest run) koşar, Then 0 failed ve çalışan backend gerekmez (`evaluation.test.ts` 6 test ağ mock'u/izole).
5. [High] Given `evidence-upload-form`, `evaluation-form` testlerindeki "genel hata mesajı" beklentisi, When koşar, Then ya kodun ya testin yanlış olduğu kanıtla belirlenip doğru taraf düzeltilir (kural: test kırıldıysa önce kimin yanlış olduğunu anla; kullanıcıya bildir).
6. [High] Given `kurum/[id]/panel` "404 gösterilir (403 değil)" testi (aralıklı kırmızı), When 20 kez art arda koşar, Then 20/20 yeşil (flaky kök neden giderilir, retry ile maskelenmez).
7. [High] Given CI (`.github/workflows/ci.yml`), When PR açılır, Then frontend job'ı `vitest run` koşar ve kırık test CI'yı kırmızı yapar. (CI değişikliği = ÖNCEDEN ONAY gerekir.)
8. [Medium] Given yeni geliştirici, When README/CONTRIBUTING'e bakar, Then test DB'sinin nasıl kurulduğu/kullanıldığı yazılıdır (tek komut).
9. [Medium] Given `pytest tests/authorization -q`, When koşar, Then izolasyon değişikliğinden sonra aynı sayıda test toplanır ve hepsi geçer (yetki testleri bozulmadı).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Test DB hazır, paket koşar | pytest exit 0 | yalnız test DB'sinde geçici satır; her test sonunda rollback/temizlik | "N passed" | AC-1,2,3 |
| 2 | Test DB yok / bağlanılamıyor | pytest exit != 0, ilk fixture'da açık hata ("test DB'ye bağlanılamadı: ... nasıl kurulur: ...") | yok | anlaşılır hata, 13 gizemli assert değil | AC-8 |
| 3 | Test DB şeması eski (migration geride) | fixture açıkça hata verir veya `alembic upgrade head` ister; sessiz geçmez | yok | açık mesaj | AC-2 |
| 4 | Test, dev DB URL'ine işaret ediyor (yanlış yapılandırma) | fixture reddeder: DB adı `_test` ile bitmiyorsa RuntimeError (dev DB'yi yanlışlıkla silmeye/yazmaya karşı koruma) | yok | açık hata | AC-3 |
| 5 | Frontend test, backend kapalı | test yine yeşil (ağ mock'u) | yok | geçer | AC-4 |
| 6 | CI'da kırık frontend testi | job fail | yok | kırmızı CI | AC-7 |
| 7 | Kısmi başarı: bir test dosyası izole, diğeri değil | kabul edilmez; AC-2 (boş/seed'li DB karşılaştırması) bunu yakalar | — | — | AC-2 |
| 8 | Hiçbir şey yapılamadı ama hata yok: fixture sessizce dev DB'ye düşer | YASAK; satır 4 korumasıyla RuntimeError | — | — | AC-3 |

Boş sonuç ↔ hata ayrımı: "kuyruk boş" varsayan testler kendi verisini kurup kendi satırlarını filtreler ya da boş test DB'si kullanır; global `count(*)` yasak.
Satır 7-8 uygulanır (yok sayılmadı); sabit "uygulanmayan satır" yok.

## Test Strategy
Unit: 0% — yeni üretim mantığı yok.
Integration: 70% — gerçek PostgreSQL (rules/testing.md: SQLite yasak), conftest/DB izolasyonu, outbox/seed/evaluation.
E2E: 30% — vitest bileşen/API testleri + CI'da koşması (yeni E2E senaryosu yok).

## Benchmark / Başarı Ölçütü
Coverage Target: değişmemeli (düşmemeli).
Performance Target: backend tam paket < 120 sn.
Görsel/UI kriteri: yok.
Diğer: `pytest tests -q` ve `vitest run` ikisi de 0 failed; seed'li ve boş DB'de eşit; dev DB'de iz bırakmıyor.

## Kapsam Dışı
- Yeni üretim özelliği, endpoint, migration oluşturma (mevcut migration'lar yalnız test DB'sine uygulanır).
- `evaluation.ts`/`engagements.ts` üretim davranışını değiştirmek (yalnız testin izolasyonu).
- YET-218 (test fixture rollback davranışı) — ayrı görev, bu bittikten sonra.
- Testleri silmek, skip/xfail, assert gevşetmek.

## Etkilenen Dosyalar/Modüller (bilinen)
Frontmatter listesi. Kırıkların yerleri: `test_outbox_worker.py` (9), `test_seed.py` (3: AC4 rollback, AC5 production guard, AC4 engagement error), `test_evaluation.py::TestEvaluationInvalidSkillIdInItem` (15 SkillSignal), vitest 4 dosya.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Git kökü proje klasörü (`yetkin360`); doğrulanmadı ama arama yine `backend/` ve `frontend/` ile sınırlanır, geniş `grep -r`/`git log --all` yok.

## Rollback Beklentisi
Değişiklik yalnız test kodu, test DB'si ve CI adımı. Geri alma = `git revert`; test DB'si silinebilir, dev DB'ye dokunulmaz.

## Risks
- Test DB'si için `CREATE DATABASE` + `alembic upgrade head` gerekir (migration UYGULAMA = onay şartı, CLAUDE.md).
- `docker-compose`/CI değişikliği gerekirse onay şartı.
- Mevcut yetki testleri (`tests/authorization`) fixture değişikliğinden etkilenebilir; AC-9 ile korunur.
- `evidence-upload-form`/`evaluation-form` kırığı test değil kod hatası olabilir (AC-5).

## Assumptions (kullanıcı onaylamadı; onay bekliyor)
- Yaklaşım: ayrı `yetkin360_test` veritabanı (URL `settings.database_url`'den DB adı değiştirilerek türetilir, sır yazılmaz); conftest oturum başı DB'yi yoksa oluşturur ve şemayı kurar, adı `_test` ile bitmiyorsa reddeder. Alternatif (dev DB'de satır silip rollback) reddedildi: commit eden testleri ve seed testlerini çözmez, dev veriyi riske atar.
- Seed testleri boş test DB'sinde "0 mevcut" varsayımıyla zaten doğru çalışır.
- Frontend `evaluation.test.ts` için çözüm: fetch/ağ katmanı mock'u (gerçek backend bağımlılığı kaldırılır).
- Kapsam: backend (benim) + frontend + CI hepsi bu görevde; Jira'da frontend/CI sahibi Elif Sara.

## Unknowns
- Frontend + CI işini bu görevde mi yapacağım, Elif'e mi bırakacağım? (Jira sahipliği Elif.)
- CI'da backend testleri için Postgres service var mı? (ci.yml okunacak, plan adımı.)
- `panel/page.test.tsx` aralıklı hatanın kök nedeni.

## Sorular ve Cevaplar (ham kayıt)
Not: skill'in 4z adımındaki Sonnet 5 alt-ajanı DISPATCH EDİLMEDİ; görev Jira açıklaması + yerel ölçümle zaten somut. Cevaplar aşağıda kaynakla belirtildi, onaylanmamış olanlar Assumptions'ta.
1. Persona → geliştirici/katkıcı (Jira + repo bağlamı).
2. Hedef → deterministik test paketi (Jira).
3. Happy path → `pytest tests -q`, `vitest run` yeşil (Jira + ölçüm).
4. Edge → test DB yok, yanlış DB, backend kapalı (sözleşme satır 2-5).
5. Davranış sözleşmesi → yukarıdaki tablo.
6. Ölçüt → 0 failed, <120 sn (ölçülen ~56 sn).
7. Kapsam dışı → yeni özellik, migration üretimi, YET-218.
8. Bağımlılıklar → conftest, ci.yml (onay), docker-compose (gerekirse onay).
9. Güvenlik → sır yok, dev DB koruması (satır 4).
10. Rollback → git revert.
11. Onay sahibi → kullanıcı + otomatik test.
12. Test oranı → 0/70/30 (varsayım, onay bekliyor).
