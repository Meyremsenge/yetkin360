---
task_slug: yet-5-outbox-worker
jira_id: null
saga_task_id: null
priority: high
threat_model: done
coverage_target: 90
performance_target: "poll gecikmesi <= 5sn (worker boşta değilken)"
memory_target: null
test_strategy:
  unit: 60
  integration: 35
  e2e: 5
affected_modules:
  - backend/app/models/outbox.py (yeni)
  - backend/app/services/outbox.py (yeni)
  - backend/app/workers/outbox_worker.py (yeni)
  - backend/alembic/versions/ (yeni migration)
  - backend/app/services/auth.py (satır 108-154 — register_user TODO bağlanacak)
  - backend/app/models/__init__.py (yeni model export)
  - .env.example (OUTBOX_POLL_INTERVAL_SECONDS, OUTBOX_MAX_ATTEMPTS)
---

# ATDD — yet-5-outbox-worker

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (PLAN.md madde 1.5).

## Persona
Son kullanıcı için doğrudan görünür değil. İki iç "kullanıcı":
- **Servis katmanı geliştiricisi** (`app/services/*`): açık bir transaction
  içindeyken ağ çağrısı yapmadan bir yan etkiyi (e-posta gönderimi vb.)
  güvenle sıraya koymak ister.
- **Worker process** (systemd altında sürekli çalışan ayrı bir process):
  sıradaki işleri sırayla, çift işlemeden, DB'yi kilitlemeden tüketir.

## Hedef (Neden)
CLAUDE.md ve docs/DATABASE.md §5 değişmez kuralı: "Ağ çağrısı (e-posta, S3,
AI) asla açık transaction içinde yapılmaz." Bu görev o kuralı çalışan bir
altyapıya döker. Somut ilk kanıt: `app/services/auth.py` içindeki
`register_user()` fonksiyonu (satır 118-121) hâlihazırda bu altyapının
yokluğu yüzünden var olan bir hesaba tekrar kayıt denemesi bildirimini
atlıyor — bu görev outbox'ı hem genel altyapı olarak kurar hem de bu TODO'yu
kapatan ilk somut tüketiciyi (`email.duplicate_registration_attempt` topic'i)
bağlar.

## User Story
As a servis katmanı geliştiricisi
I want açık bir transaction içinde ağ çağrısı yapmadan bir yan etkiyi
sıraya koyabilmek
So that transaction hem atomik kalır hem de dış servis (SMTP) çökse bile
kullanıcı akışı bloklanmaz/etkilenmez

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given açık bir DB transaction'ı, When `outbox_service.enqueue(session, topic="email.duplicate_registration_attempt", payload={...})` çağrılır, Then aynı transaction içinde `outbox` tablosuna `processed_at=NULL, attempts=0` olan bir satır eklenir ve hiçbir ağ çağrısı yapılmaz (senkron, engellemeyen).
2. [Critical] Given `outbox`'ta `processed_at IS NULL` olan bir satır, When worker poll döngüsü çalışır, Then satır `SELECT ... FOR UPDATE SKIP LOCKED` ile seçilir, topic'e kayıtlı handler çağrılır, handler başarılı dönerse `processed_at = now()` UPDATE edilir.
3. [Critical] Given `register_user()` var olan bir e-postayla tekrar çağrılır, When kayıt denemesi reddedilir (mevcut davranış: sahte `user_id` ile `201`), Then aynı transaction içinde `outbox`'a `topic="email.duplicate_registration_attempt"` satırı eklenir (audit_events zaten eklendiği gibi).
4. [High] Given `outbox`'ta `processed_at IS NULL` olan bir satır, When handler çağrısı exception fırlatır (SMTP/ağ hatası dahil), Then `attempts += 1` UPDATE edilir, `processed_at` NULL kalır, hata log'lanır (payload içeriği değil, outbox id + hata tipi).
5. [High] Given bir satırın `attempts >= OUTBOX_MAX_ATTEMPTS`, When worker poll sorgusu çalışır, Then bu satır artık seçilmez (`WHERE processed_at IS NULL AND attempts < OUTBOX_MAX_ATTEMPTS`) — sessizce sonsuza kadar denenmeye devam etmez.
6. [High] Given aynı satırı aynı anda seçmeye çalışan 2 worker (çoklu instance simülasyonu), When her ikisi de aynı anda poll sorgusu çalıştırır, Then `SKIP LOCKED` sayesinde sadece biri satırı alır, diğeri boş döner — satır iki kez işlenmez.
7. [Critical] AC-S1 Given `outbox_service.enqueue()` çağıran kod, When payload içine `password`/`password_hash`/`token`/`private_note` anahtarlarından biri (case-insensitive, iç içe dict dahil) konursa, Then `enqueue()` `ValueError` fırlatır ve satır DB'ye hiç yazılmaz (audit.py'deki `_check_pii_in_metadata` ile aynı guard, outbox servisine de uygulanır).
8. [High] AC-S2 Given worker bir handler hatasını yakalar, When hatayı loglar, Then log satırında `outbox.id`, `topic`, hata tipi/mesajı bulunur ama `payload` içeriği (örn. e-posta adresi) **hiçbir zaman** log'a basılmaz.
9. [Medium] AC-S3 Given `outbox` tablosunda `attempts >= OUTBOX_MAX_ATTEMPTS` olan kalıcı-başarısız satırlar birikir, When bu durum gözlenir, Then bu satırlar fiziksel silinmez (denetlenebilirlik) ama Risks bölümünde açıkça "PII retention riski, MVP'de kabul edilen risk" olarak işaretlenir — sessizce göz ardı edilmez.

## Agentic Değerlendirme Kriterleri
(Tetikleyici yok — bu görev bir LLM agent/tool-calling davranışını değiştirmiyor. Bölüm silindi.)

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: satır var, handler başarılı | `enqueue()` → `None` (exception yoksa başarı); worker döngü fonksiyonu → işlenen satır sayısı (int) | `outbox.processed_at = now()` UPDATE edilir | Son kullanıcı hiçbir şey görmez (arka plan); `EMAIL_BACKEND=console` ise geliştirici konsolda e-posta içeriğini görür | AC-1, AC-2, AC-3 |
| 2 | Girdi geçersiz: payload'da PII anahtarı | `enqueue()` → `ValueError` fırlatır, çağıranın transaction'ı (caller sorumluluğunda) etkilenir | Satır hiç DB'ye yazılmaz | Son kullanıcı hiçbir şey görmez; geliştirici test/log'da hatayı görür | AC-S1 |
| 3 | Kaynak yok: işlenecek satır yok | Worker döngü fonksiyonu → `0` döner | Yok | Kullanıcı hiçbir şey görmez; worker bir sonraki poll'a kadar bekler | AC-8 (davranış sözleşmesi tablosu satırı) |
| 4 | Yetkisiz erişim | N/A — silindi | — | — | — |
| 5 | Dış bağımlılık hatası (SMTP/ağ) | Handler exception fırlatır, worker yakalar, fonksiyon exception'ı yutar (crash etmez) | `attempts += 1` UPDATE edilir, `processed_at` NULL kalır | Kullanıcı hiçbir şey görmez; log'da hata tipi + outbox id (payload yok) | AC-4, AC-S2 |
| 6 | Zaman aşımı (SMTP timeout) | AC-4 ile aynı yol (timeout da bir exception türüdür) | Aynı: `attempts += 1` | Aynı | AC-4 |
| 7 | Kısmi başarı: batch'te bazı satırlar başarılı bazıları değil | Her satır kendi bağımsız transaction'ında işlenir; worker döngü fonksiyonu toplam işlenen sayıyı döner (başarısızlar sayılmaz) | Başarılılar `processed_at` alır, başarısızlar `attempts += 1` alır — birbirini etkilemez | Kullanıcı hiçbir şey görmez | AC-2 (satır bazlı izolasyon) |
| 8 | Hiçbir şey yapılamadı ama hata yok: worker döngüsü boşta | Döngü fonksiyonu → `0` döner (satır 3 ile aynı) | Yok | Kullanıcı hiçbir şey görmez; debug-level log opsiyonel | AC-8 |

**Silinen satır:** "Yetkisiz erişim" — outbox tablosuna dışarıdan (HTTP) erişim yolu bu görevde yok; worker tek iç process olarak DB'ye doğrudan bağlanıyor, yeni bir endpoint açılmıyor. Bu yüzden CLAUDE.md'nin "yeni endpoint = yetkilendirme testi zorunlu" kuralı burada tetiklenmiyor.

Kısmi başarı: Her outbox satırı **kendi bağımsız transaction'ında** işlenir (satır 7). Bir satırın handler hatası diğer satırların işlenmesini durdurmaz veya geri almaz — outbox'ın tasarım amacı zaten bu izolasyondur.

Hiçbir şey yapılamadı ama hata da yok: Worker'ın "seçilecek satır yok" durumu (`processed_at IS NULL AND attempts < MAX_ATTEMPTS` boş sonuç döndüğünde) açıkça `0` işlenen satır olarak raporlanır — sessiz/belirsiz bir "başarı" değil, ölçülebilir bir "yapacak iş yok" sonucudur.

Boş sonuç ↔ hata ayrımı: `enqueue()` başarıyla dönerse satır kesin DB'dedir (aynı transaction, `session.flush()` ile doğrulanabilir) — "sanki eklendi ama eklenmedi" durumu yoktur, çünkü outbox INSERT'i çağıranın transaction'ının bir parçasıdır (aynı commit/rollback sınırında). Worker tarafında "0 satır işlendi" (iş yok) ile "satır vardı ama hepsi hata verdi" (attempts arttı) ayrımı loglanan sayılarla (seçilen satır sayısı vs. başarıyla işaretlenen sayısı) ayrılır — ikisi de aynı `0` dönüş değerini paylaşmaz.

## Test Strategy
Unit: 60% — `enqueue()` (PII guard, transaction içi INSERT), worker'ın satır
seçme/işaretleme/attempts artırma mantığı (DB mock'lanmış veya in-memory).
Integration: 35% — gerçek PostgreSQL test DB'sine karşı `FOR UPDATE SKIP
LOCKED` davranışı, partial index kullanımı, iki worker'ın aynı satırı
yarışması, migration upgrade/downgrade.
E2E: 5% — `register_user()` (duplicate email) → `outbox` satırı → worker →
`EMAIL_BACKEND=console` çıktısı ucu ucuna.

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: poll gecikmesi ≤ 5sn (worker boşta değilken, satır
işlenebilir hale geldikten sonraki bir sonraki poll'da alınmalı)
Memory: belirtilmedi (MVP ölçeğinde önemsiz — Unknowns'a not düşüldü)
Görsel/UI kriteri: yok (bu görev backend-only, UI yok)
Diğer ölçülebilir kriterler: worker crash-loop yapmamalı — tek satırın/
iterasyonun hatası process'i öldürmemeli (AC-4 ile doğrulanır).

## Kapsam Dışı
- Gerçek SMTP entegrasyonu (PLAN 1.6'da e-posta doğrulama/şifre sıfırlama
  ile birlikte gelecek). Bu görevde yalnız `EMAIL_BACKEND=console` yolu
  gerçek çalışır; `smtp` yolu için handler iskeleti bırakılabilir ama test
  edilmez.
- Exponential backoff / gelişmiş retry stratejisi — sabit `attempts` sayacı
  + sabit `OUTBOX_MAX_ATTEMPTS` eşiği yeterli.
- Ayrı bir `dead_letter` tablosu — `attempts >= MAX_ATTEMPTS` filtresi
  yeterli, satır `outbox`'ta kalır.
- Celery/Redis/RabbitMQ — CLAUDE.md kesin yasak, final analiz §39.
- Admin UI'dan outbox izleme/panel.
- Çoklu worker instance'ının gerçek yatay ölçekleme entegrasyon testi
  (`SKIP LOCKED` mekanizması hazırlanır ve AC-6 ile iki worker'ın yarışması
  test edilir, ama prod'da kaç instance çalışacağı bu görevin kapsamı değil).
- `outbox` için ayrı bir retention/temizlik job'ı (bkz. Risks).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/outbox.py` (yeni) — `app/models/audit.py` pattern'ine
  paralel (bigserial PK) ama immutability trigger YOK (mutable tablo).
- `backend/app/services/outbox.py` (yeni) — `enqueue(session, topic, payload)`.
- `backend/app/workers/outbox_worker.py` (yeni) — polling döngüsü, topic→handler
  dispatch tablosu.
- `backend/alembic/versions/` — yeni migration (tablo + partial index
  `(created_at) WHERE processed_at IS NULL`). Ham SQL yalnız burada.
- `backend/app/services/auth.py:108-154` — `register_user()`'daki TODO
  yorumunun yerine `outbox_service.enqueue(...)` çağrısı eklenir.
- `backend/app/models/__init__.py` — yeni `Outbox` model export.
- `.env.example` — `OUTBOX_POLL_INTERVAL_SECONDS` (öneri: 5), `OUTBOX_MAX_ATTEMPTS`
  (öneri: 5) placeholder'ları (docs/ENV.md §6'daki `EMAIL_BACKEND` zaten var,
  bu iki değişken docs/ENV.md'ye de eklenmeli — ayrı onay istenmeden, docs
  güncellemesi kapsam içi).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökü proje klasörüyle aynı mı
(`C:\Users\Meyrem\Desktop\P\yetkin360`) yoksa daha geniş bir dizin mi taşıyor,
kontrol edilmedi. Sonraki adımlarda (özellikle `plan`, `code-copilot`,
`test-copilot`) arama HER ZAMAN `backend/` altına sınırlanmalı; kök dizinden
sınırsız `grep -r` veya `git log -p --all` çalıştırılmamalı.

## Rollback Beklentisi
`alembic downgrade -1` tabloyu ve partial index'i tamamen kaldırır —
işlenmemiş satırlar varsa (nadir, MVP'de outbox henüz kritik veri taşımıyor)
kaybolur; bu kabul edilebilir çünkü henüz tek tüketici (duplicate-email
bildirimi) kritik bir iş akışını bloklamıyor. Worker process'in kendisi hata
verirse (örn. DB bağlantısı geçici kopması): crash-loop yapmaz, döngü
içindeki try/except tek bir iterasyonun hatasını yutar, hatayı loglar ve bir
sonraki poll'da devam eder — process'in tamamen durması yalnız beklenmeyen
(yakalanmamış) bir hata durumunda olur ve bu durumda systemd (final analiz
§39 mimari) supervisor olarak yeniden başlatır.

## Risks
- **PII retention riski (kabul edilen risk):** `attempts >= MAX_ATTEMPTS`
  olan satırlar fiziksel silinmediği için outbox'ta (örn. e-posta adresi
  içeren) payload süresiz kalabilir. MVP'de ayrı bir temizlik job'ı
  kapsam dışı bırakıldı (bkz. Kapsam Dışı) — bu bilinçli bir kabul, V2'de
  retention politikası eklenmeli.
- Çoklu worker instance'ının gerçek üretim ortamında birden fazla process
  olarak çalışıp çalışmayacağı henüz netleşmedi (tek VPS varsayımıyla
  muhtemelen tek instance) — `SKIP LOCKED` yine de güvenlik payı olarak
  eklendi, ek karmaşıklık getirmiyor.

## Assumptions
- `EMAIL_BACKEND=console` MVP'de tek gerçek çalışan yol; `smtp` dalı bu
  görevde tam test edilmeyecek (varsayım — kullanıcı onaylamadı).
- `OUTBOX_POLL_INTERVAL_SECONDS=5`, `OUTBOX_MAX_ATTEMPTS=5` makul varsayılan
  değerler olarak önerildi (Sonnet 5 low alt-ajanı önerisi) — kesin değer
  `plan` adımında veya kullanıcı onayıyla değişebilir.
- Worker'ın deploy şekli (systemd unit dosyası) final analiz §39'da
  belirtilen mimariyle tutarlı varsayıldı; bu görev kapsamında gerçek
  systemd unit dosyası yazılmayacak (sadece çalıştırılabilir script/entrypoint).

## Unknowns
- Worker process'in bellek/performans hedefi (memory_target) belirtilmedi —
  MVP ölçeğinde (hackathon, düşük trafik) şimdilik önemsiz kabul edildi.
- `outbox` retention politikası (başarısız satırların ne zaman/nasıl
  temizleneceği) V2'ye bırakıldı, henüz karar yok.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Sonnet 5 low alt-ajanı tarafından yanıtlandı:
   sadece worker process; bu görevde 1 topic (email.duplicate_registration_attempt).
2. Ana hedef/neden → Sonnet 5 low alt-ajanı tarafından yanıtlandı: genel
   altyapı asıl teslim, register_user TODO'su ilk somut kanıt/tüketici.
3. Happy path senaryosu → Sonnet 5 low alt-ajanı tarafından yanıtlandı:
   5sn poll aralığı, `FOR UPDATE SKIP LOCKED` ile batch seçim, handler
   dispatch, `processed_at`/`attempts` güncelleme.
4. Edge case — worker çökerse → Sonnet 5 low alt-ajanı tarafından
   yanıtlandı: `FOR UPDATE SKIP LOCKED` yeterli, advisory lock gereksiz.
5. Edge case — SMTP hatası → Sonnet 5 low alt-ajanı tarafından yanıtlandı:
   `attempts` artar, `MAX_ATTEMPTS` eşiği var, aşılınca sorgu filtresiyle
   dışlanır (ayrı dead-letter tablosu yok).
6. Davranış sözleşmesi tablosu → Sonnet 5 low alt-ajanı tarafından
   dolduruldu, "yetkisiz erişim" satırı N/A gerekçesiyle silindi.
7. Başarı ölçütü → Sonnet 5 low alt-ajanı tarafından yanıtlandı: poll
   gecikmesi ≤5sn, unit coverage ≥%90.
8. Kapsam dışı → Sonnet 5 low alt-ajanı tarafından yanıtlandı (bkz. Kapsam
   Dışı bölümü, birebir aktarıldı).
9. Bağımlılıklar/etkilenen dosyalar → Sonnet 5 low alt-ajanı tarafından
   yanıtlandı (bkz. Etkilenen Dosyalar bölümü).
10. Performans/güvenlik kısıtı → Sonnet 5 low alt-ajanı tarafından
    yanıtlandı: 5sn polling + partial index ihmal edilebilir yük; SMTP
    sırları .env'den, asla loglanmaz/payload'a yazılmaz.
11. Rollback beklentisi → Sonnet 5 low alt-ajanı tarafından yanıtlandı
    (bkz. Rollback Beklentisi bölümü).
12. Test stratejisi oranı → Sonnet 5 low alt-ajanı tarafından yanıtlandı:
    60/35/5 (unit/integration/e2e), genel 70/20/10'dan daha
    integration-ağırlıklı çünkü asıl risk (kilitlenme/çift-işleme) yalnız
    gerçek DB ile test edilebilir.
13. Task-slug onayı → **kullanıcıdan** alındı: `yet-5-outbox-worker`.
14. Threat-model tetikleyicisi (background job + dış SMTP çağrısı) →
    `threat-model` skill'i çağrıldı; STRIDE-lite uygulandı, AC-S1/AC-S2/AC-S3
    üretildi (PII guard payload'da, log'da payload sızmaması, retention
    riskinin açıkça kabul edilmesi). Spoofing/Repudiation/Elevation N/A
    (worker'ın dışarıdan erişilen bir HTTP yüzeyi yok).
