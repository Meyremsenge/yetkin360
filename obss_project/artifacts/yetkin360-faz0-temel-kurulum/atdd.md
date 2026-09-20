---
task_slug: yetkin360-faz0-temel-kurulum
jira_id: null
saga_task_id: null
threat_model: not-applicable
priority: high
coverage_target: null
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 0
  e2e: 80
affected_modules:
  - .env.example
  - docker-compose.yml
  - backend/ (FastAPI iskeleti: app/main.py, app/core/config.py, alembic.ini, alembic/, requirements.txt)
  - frontend/ (Next.js + TS + shadcn/ui iskeleti, messages/tr.json)
  - .github/workflows/ci.yml
---

# ATDD — yetkin360-faz0-temel-kurulum

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga entegrasyonu bu ortamda mevcut değil (mcp__saga__* araçları bulunamadı) — task takibi PLAN.md üzerinden yapılıyor.

## Persona
Tek geliştirici (Yusuf), hackathon takım detayları henüz netleşmemiş (PLAN.md 0.13 "ekip isim eşlemesi" hâlâ yapılmamış madde). İskelet kurulumunu şu an fiilen tek kişi yürütüyor.

## Hedef (Neden)
Faz 1'de gerçek iş mantığına (endpoint, auth, veri modeli implementasyonu) başlayabilmek için çalışan bir geliştirme ortamı iskeleti kurmak. Dokümantasyon (DOMAIN/DATABASE/API/AUTHORIZATION/SECURITY/STATE_MACHINE) tamamlandı ama repo'da `backend/` ve `frontend/` klasörü hiç yok; kod yazmaya başlamadan önce "boş ama ayağa kalkan" bir temel şart. PLAN.md Faz 0'ın kalan maddeleri: 0.9 (.env.example), 0.10 (Docker Compose + backend iskeleti), 0.11 (Frontend iskeleti), 0.12 (CI).

## User Story
As a tek geliştirici (Yusuf)
I want çalışan bir Docker Compose + FastAPI backend + Next.js frontend iskeleti ve CI pipeline'ı
So that Faz 1'de gerçek iş mantığı (auth, yetkilendirme, domain modelleri) üzerine güvenle inşa edebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given repo kökünde `.env.example` doldurulmuş ve `.env` olarak kopyalanmış, When `docker compose up -d` çalıştırılır, Then PostgreSQL 16 ve MinIO container'ları `healthy` durumda ayağa kalkar (`docker compose ps` ile doğrulanır).
2. [Critical] Given container'lar healthy, When backend dizininde `alembic upgrade head` çalıştırılır, Then hatasız tamamlanır (ilk/boş revizyon dahi olsa).
3. [Critical] Given migration tamamlanmış, When `uvicorn app.main:app --reload` başlatılır, Then `GET /health` 200 döner ve `GET /docs` Swagger UI'ı açar.
4. [Critical] Given backend ayakta, When frontend dizininde `npm install && npm run dev` çalıştırılır, Then Next.js iskelet ana sayfası tarayıcıda açılır ve en az bir shadcn/ui bileşeni render olur.
5. [High] Given `.env` dosyası eksik veya bir zorunlu değişken hatalı, When backend başlatılmaya çalışılır, Then Pydantic Settings validation hatasıyla net bir mesajla crash olur — sessizce yanlış/default değerle ayağa kalkmaz.
6. [High] Given 5432/9000/8000/3000 portlarından biri zaten kullanımda, When ilgili servis başlatılır, Then "address already in use" tipi açık bir hata verir (otomatik port çözümü beklenmez).
7. [High] Given PostgreSQL veya MinIO container'ı ayağa kalkmıyor (yanlış env/disk/izin sorunu), When backend başlatılır, Then bağlantı hatasıyla net şekilde crash olur, sonsuz beklemeye girmez.
8. [Medium] Given CI pipeline tetiklenir, When backend job çalışır, Then `ruff check .`, `mypy app`, `pytest` (placeholder `test_health.py`: `GET /health` → 200) hatasız geçer.
9. [Medium] Given CI pipeline tetiklenir, When frontend job çalışır, Then `npm run lint`, `npm run typecheck`, `next build` hatasız geçer.
10. [Medium] Given `.gitignore` kontrol edilir, When repo'ya bakılır, Then `.env` dosyası asla commit edilmemiş olur, yalnızca `.env.example` placeholder değerlerle repoda bulunur.

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme, kullanıcı girdisi, dosya yükleme/indirme, ödeme, kişisel veri (KVKK), çok kiracılı sınır, dış API çağrısı, arka plan işi, yeni bir HTTP ucu. Bu görevde eklenen tek uç `GET /health` — herhangi bir kullanıcı girdisi almıyor, veri döndürmüyor, yetkilendirme gerektirmiyor, sadece servis canlılığını bildiriyor; gerçek iş mantığı/auth/veri modeli implementasyonu Faz 1'e ait ve o fazda `threat-model` yeniden değerlendirilecek.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (tüm servisler doğru kurulu) | `docker compose ps` → tüm servisler `healthy`; `GET /health` → `200 {"status":"ok"}`; frontend → `200` ana sayfa | Postgres/MinIO container'ları oluşur, alembic migration tablosu yazılır | Terminalde "healthy" durumları, tarayıcıda çalışan ana sayfa ve Swagger UI | AC-1..4 |
| 2 | Girdi geçersiz (`.env` eksik/hatalı) | Backend process crash, Pydantic validation hata mesajı (stderr) | Yok — process başlamadan durur | Net hata mesajı (hangi env değişkeninin eksik/hatalı olduğu) | AC-5 |
| 3 | Kaynak yok | N/A — bu aşamada "kaynak" (attestation, skill_signal vb.) kavramı yok, Faz 1'de gelecek | — | — | — |
| 4 | Yetkisiz erişim | N/A — `/health` ve `/docs` yetkilendirme gerektirmiyor, auth/can()/scoped_*() implementasyonu bu görevde yok | — | — | — |
| 5 | Dış bağımlılık hatası (Postgres/MinIO ayağa kalkmıyor) | Backend başlangıçta bağlantı hatasıyla crash, exit code ≠ 0 | Yok | stderr'de bağlantı hatası, `docker compose ps` içinde ilgili servis `unhealthy`/`exited` | AC-7 |
| 6 | Zaman aşımı (DB/MinIO bağlantı denemesi) | Makul bir timeout (birkaç saniye) sonrası bağlantı hatasıyla crash | Yok | Net timeout hata mesajı, sonsuz bekleme yok | AC-7 |
| 7 | Kısmi başarı (ör. Postgres kalkar, MinIO kalkmaz) | Backend'in kendisi hatasız başlayıp DB'ye bağlanabiliyorsa `/health` yine 200 dönebilir (MVP'de basit 200/500, "degraded" formatı Faz 1'e ertelenir) | Yok | `docker compose ps` MinIO'nun unhealthy olduğunu gösterir, backend health-check bunu henüz ayrıştırmaz (bilinen sınırlama, Assumptions'a not düşüldü) | AC-1 (kısmen) |
| 8 | Hiçbir şey yapılamadı ama hata yok (sessiz başarısızlık) | Kabul edilmez — `docker compose up -d`'nin exit code 0 dönmesi TEK BAŞINA yeterli kabul edilmez | — | Kabul kriteri: `docker compose ps` ile "healthy" durumu VE `/health` endpoint'inin gerçekten 200 dönmesi birlikte kontrol edilir | AC-1 |

Kısmi başarı: Bir servis (ör. MinIO) healthy olmazken diğerleri (Postgres, backend) çalışıyorsa, bu Faz 0'da "tamamlanmadı" sayılır — AC-1 tüm servislerin healthy olmasını şart koşuyor. Backend'in kendi health-check'i bağımlılık bazında ayrıştırma yapmıyor (bilinen sınırlama, bkz. Assumptions).
Hiçbir şey yapılamadı ama hata da yok: Kabul kriteri yalnızca komutun exit code'una değil, `docker compose ps`'in "healthy" durumuna VE `/health` endpoint'inin fiilen 200 dönmesine bağlanır — "crash-loop ama compose komutu başarılı görünüyor" durumu bu şekilde yakalanır.
Boş sonuç ↔ hata ayrımı: Bu aşamada veri döndüren bir uç olmadığı için (yalnızca `/health`) bu ayrım N/A — Faz 1'de gerçek endpoint'ler eklenince yeniden ele alınacak.

Silinen satır yok — tüm 8 satır yukarıda N/A gerekçesiyle veya uygulanmış haliyle işlendi.

## Test Strategy
Unit: 20% — backend config/settings validation (Pydantic Settings'in eksik env'de doğru hata verdiğinin testi)
Integration: 0% — bu aşamada gerçek servis entegrasyonu (auth, veri modeli) yok, Faz 1'e ertelendi
E2E/Smoke: 80% — CI'da: backend `pytest` ile placeholder `test_health.py` (`GET /health` → 200), `ruff check .`, `mypy app`; frontend `npm run lint`, `npm run typecheck`, `next build`. Yerelde: `docker compose up -d` → `alembic upgrade head` → `uvicorn` → `npm run dev` uçtan uca zincirinin hatasız çalışması.

## Benchmark / Başarı Ölçütü
Coverage Target: Yok (iskelet aşaması, nicel coverage hedefi anlamsız)
Performance Target: Yok
Memory: Yok
Görsel/UI kriteri: Frontend ana sayfası tarayıcıda hatasız açılmalı, en az bir shadcn/ui bileşeni görünür olmalı (layout bozulmamalı) — `verify` adımında gerekirse `vision-test` ile kontrol edilir.
Diğer ölçülebilir kriterler: "docker compose up -d + alembic upgrade head + uvicorn + npm run dev hatasız çalışır, GET /health 200 döner, frontend ana sayfa tarayıcıda açılır" — ikili (çalışıyor/çalışmıyor) kabul kriteri.

## Kapsam Dışı
- Gerçek endpoint'ler / iş mantığı (auth, talent, engagement, evidence, attestation vb.)
- `can()`/`scoped_*()` yetkilendirme çekirdeği implementasyonu (PLAN.md 1.2)
- Seed/fixture verisi (`scripts/seed`)
- Gerçek migration şeması (attestations/skill_signals/evaluations/vb. tabloları) — yalnızca ilk/boş migration
- Production Caddy/TLS/S3 konfigürasyonu
- Lisans teyidi (PLAN.md 0.1) — ayrı madde, bu görevin parçası değil
- Ekip isim eşlemesi (PLAN.md 0.13) — ayrı madde

## Etkilenen Dosyalar/Modüller (bilinen)
- `.env.example` (repo kökü)
- `docker-compose.yml` (PostgreSQL 16 + MinIO servisleri)
- `backend/` — `app/main.py`, `app/core/config.py`, `alembic.ini`, `alembic/`, `requirements.txt`, opsiyonel `Dockerfile`
- `frontend/` — Next.js App Router + TS + shadcn/ui iskeleti, `package.json`, TR metin dosyası (ör. `messages/tr.json`)
- `.github/workflows/ci.yml` — backend job (ruff+mypy+pytest) ve frontend job (npm lint+typecheck+build)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede `projelerim/yetkin360` klasörü kendi git reposu olarak klonlandı (`git clone` ile ayrı repo), `projelerim/obss` reposundan bağımsız. Sonraki adımlarda (plan/code-copilot/test-copilot/red-team) arama `projelerim/yetkin360` klasörüyle sınırlanmalı, `projelerim/obss`'nin devasa git geçmişi taranmamalı.

## Rollback Beklentisi
Otomatik rollback gerekmez. Bir adım (ör. migration veya container start) başarısız olursa süreç durur, hata mesajı net şekilde gösterilir; `docker compose down` ile container'lar temizlenip yeniden denenir. Bu bir prod deploy değil, veri kaybı riski taşımıyor.

## Risks
- Backend health-check'in bağımlılık bazında (Postgres vs MinIO ayrı ayrı) durum ayrıştırması yapmaması — kısmi arıza durumunda yanıltıcı "sağlıklı" görünüm riski taşıyor (Faz 1'de "degraded" health-check formatına genişletilmesi önerilir).
- Tek geliştirici + sıkı hackathon takvimi (teslim 9-11 Ekim 2026) — CI/iskelet kurulumuna ayrılan süre Faz 1-3'ün zamanını sıkıştırabilir.

## Assumptions
- Backend portu 8000, frontend portu 3000, PostgreSQL 5432, MinIO 9000/9001 varsayılıyor (PLAN.md/README'de birebir port numarası verilmemiş, README'deki örnek komutlardan çıkarım).
- Saga/Jira entegrasyonu bu görevde kullanılmıyor — mevcut ortamda `mcp__saga__*` araçları bulunamadı, ilerleme takibi PLAN.md üzerinden yapılacak varsayımıyla ilerlendi.
- Ekip büyüklüğü/rol dağılımı (PLAN.md 0.13) netleşmediği için persona "tek geliştirici" olarak varsayıldı; takım büyürse bu ATDD'nin persona bölümü güncellenmeli.

## Unknowns
- Backend health-check'in bağımlılıklara göre "degraded" durumu ne zaman/nasıl ekleneceği (Faz 1'e mi, bu iskelet aşamasına mı ait) netleşmedi.
- CI'ın hangi platformda (GitHub Actions varsayıldı — repo GitHub'da) çalışacağı doğrulanmadı.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Tek geliştirici (Yusuf), hackathon takım detayları belirsiz (Sonnet 5 low alt-ajanı tarafından yanıtlandı: gitStatus'ta tek yazar görünüyor, PLAN.md 0.13 henüz yapılmamış)
2. Ana hedef/"neden" → Faz 1'de gerçek iş mantığına başlayabilmek için çalışan bir geliştirme ortamı iskeleti kurmak (Sonnet 5 low alt-ajanı tarafından yanıtlandı: dokümantasyon tamam ama backend/frontend klasörü yok)
3. Happy path senaryosu → 5 adımlı zincir: .env kopyala → docker compose up -d → alembic upgrade head → uvicorn (GET /health, GET /docs) → npm run dev (Sonnet 5 low alt-ajanı tarafından yanıtlandı: PLAN.md 0.10/0.11'deki stack varsayımları)
4. Edge case'ler → .env eksik/hatalı (compose açık hata vermeli), port çakışması (README'de not yeterli) (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Davranış sözleşmesi — minimal doğrulama ucu → GET /health yeterli, GET /docs bonus (Sonnet 5 low alt-ajanı tarafından yanıtlandı: auth/CRUD Faz 1'e ait)
6. Başarı ölçütü/benchmark → İkili (çalışıyor/çalışmıyor) kriter kabul edilir, nicel metrik gereksiz (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Kapsam dışı → gerçek endpoint/iş mantığı, auth implementasyonu, seed verisi, gerçek migration şeması, prod config, lisans teyidi, ekip eşlemesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Bağımlılıklar/etkilenen dosyalar → .env.example, docker-compose.yml, backend/, frontend/, .github/workflows/ci.yml (Sonnet 5 low alt-ajanı tarafından yanıtlandı: PLAN.md 0.9-0.12'nin doğrudan karşılığı)
9. Güvenlik kısıtı → .env gitignore'da olmalı, sadece .env.example placeholder ile commit edilmeli (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
10. Rollback beklentisi → Otomatik rollback gerekmez, manuel durdur/düzelt/tekrar dene yeterli (Sonnet 5 low alt-ajanı tarafından yanıtlandı: veri kaybı riski taşımayan bir iskelet kurulumu)
11. Kabul kriteri sahibi → Kullanıcı (Yusuf) manuel kontrolü + CI yeşil (Sonnet 5 low alt-ajanı tarafından yanıtlandı: tek geliştiricili hackathon hazırlığında ayrı onaylayıcı yok)
12. Test stratejisi oranı → Klasik unit/integration/e2e yerine smoke test ağırlıklı (unit 20/integration 0/e2e-smoke 80) (Sonnet 5 low alt-ajanı tarafından yanıtlandı: iskelet aşamasında "ayakta kalma + tip/lint temizliği" doğrulanır)
