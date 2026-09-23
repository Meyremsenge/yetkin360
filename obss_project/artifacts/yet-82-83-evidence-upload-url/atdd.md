---
task_slug: yet-82-83-evidence-upload-url
jira_id: YET-82, YET-83
saga_task_id: null
priority: critical
threat_model: done
coverage_target: 90
performance_target: "p95 < 300ms"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - api/evidence.py
  - services/storage.py
  - schemas/evidence.py
  - core/config.py
  - tests/test_storage.py
  - tests/authorization/test_evidence_upload_url.py
---

# ATDD — yet-82-83-evidence-upload-url

## Jira Kaynağı
YET-82 — `POST /evidence/upload-url`: MinIO imzalı URL üretimi
YET-83 — magic-byte MIME doğrulama + allowlist + `{uuid}.{ext}` + boyut sınırı
Jira'ya canlı bağlı değil — kullanıcı tarafından yerel olarak tanımlandı, Jira ID'leri referans amaçlı verildi.

## Persona
Öğrenci/talent (beyan sahibi). Kendi profiline (`owner_talent_id`, kimlik doğrulama bağlamından — JWT/session — çıkarılır, body'de taşınmaz) kanıt dosyası yüklemek için imzalı URL talep eder.

## Hedef (Neden)
`beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirinde kanıt (evidence) olmadan hiçbir tanıklık/doğrulama mümkün değil — bu uç, dosya yükleme altyapısının ilk (ve kritik) parçasıdır. Büyük dosyaların API sunucusundan geçmemesi (final analiz §18) için istemci MinIO'ya doğrudan yükler; API sadece imzalı URL üretir.

## User Story
As a öğrenci/talent (beyan sahibi)
I want dosyamı doğrudan storage'a yükleyebileceğim güvenli, süreli bir imzalı URL almak
So that kanıtımı platforma ekleyip beyanımı destekleyebileyim

## MİMARİ SAPMA NOTU (önemli — kullanıcı ile netleşti)

Kullanıcının orijinal isteğinde "magic-byte doğrulaması senkron, upload-url ucunda" deniyordu. Final analiz §18 incelendiğinde gerçek mimari şu:

```
Yükleme:  İstemci → API (yetki + kota kontrolü) → imzalı PUT URL üret
          İstemci → Object Storage (doğrudan — API'den geçmez)
          İstemci → API (yükleme tamamlandı bildirimi)
          API     → evidence kaydı (scan_status=PENDING) → outbox: tarama işi
          Worker  → indir, ClamAV tara, hash hesapla, MIME doğrula (magic-byte)
                  → scan_status=CLEAN | INFECTED
```

**Karar (kullanıcı onayladı):** Bu görevin (YET-82/YET-83) kapsamı, final analize uyacak şekilde **daraltıldı**:
- Bu uçta yapılan: `{uuid}.{ext}` object_key üretimi, `content_type` **header allowlist** ön-kontrolü (gerçek magic-byte değil — istemcinin deklare ettiği content_type'a bakılır), `size_bytes` deklarasyon kontrolü, MinIO presigned PUT URL üretimi.
- Bu uçta YAPILMAYAN: gerçek magic-byte/byte-level MIME doğrulama, virüs taraması, evidence DB kaydı (`scan_status` alanı). Bunlar ayrı bir PLAN maddesinde (worker + outbox, muhtemelen PLAN 2.6+) ele alınacak.
- Bu, orijinal YET-83 başlığındaki "magic-byte" ifadesiyle tam örtüşmüyor — Jira'da bu görevin kapsamının worker aşamasına bölündüğü not edilmeli.

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given kimlik doğrulanmış bir talent kullanıcı, When `POST /evidence/upload-url` isteğini geçerli `{filename, content_type, size_bytes}` ile gönderir, Then `200 OK` + `{upload_url, object_key, expires_in}` döner ve `object_key` formatı `evidence/{owner_talent_id}/{uuid}.{ext}` şeklindedir.
2. [Critical] Given kimlik doğrulanmamış istek, When `POST /evidence/upload-url` çağrılır, Then `401 Unauthorized` döner.
3. [Critical] Given `content_type` allowlist dışında (allowlist: `application/pdf`, `image/jpeg`, `image/png`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`), When istek gönderilir, Then `422 Unprocessable Entity` + `{error_code: "UNSUPPORTED_CONTENT_TYPE"}` döner.
4. [Critical] Given `size_bytes > 10MB` (10485760 byte), When istek gönderilir, Then `422 Unprocessable Entity` + `{error_code: "FILE_TOO_LARGE"}` döner.
5. [High] Given `filename` boş, eksik veya 255 karakterden uzun, When istek gönderilir, Then `422 Unprocessable Entity` (Pydantic `min_length=1, max_length=255` validasyonu) döner.
6. [High] Given MinIO'ya bağlanılamıyor (bağlantı hatası/timeout), When istek gönderilir, Then `503 Service Unavailable` + `{error_code: "STORAGE_UNAVAILABLE"}` döner.
7. [High] Given geçerli istek, When presigned URL üretilir, Then imzaya `Content-Type` ve `Content-Length` (max sınır) koşulu dahil edilir — istemci bildirdiğinden farklı bir `Content-Type`/boyutla MinIO'ya PUT yapmaya çalışırsa MinIO `SignatureDoesNotMatch`/reddetme ile engeller (bkz. Threat Model bölümü).
8. [Medium] Given geçerli istek, When `expires_in` üretilir, Then değer saniye cinsinden integer olur ve TTL 15 dakika (900 saniye) olarak ayarlanır.
9. [High] Given kimlik doğrulanmış ama talent profili olmayan bir kullanıcı (örn. sadece ORG_MEMBER/COORDINATOR rolünde, `principal.talent_id` None), When `POST /evidence/upload-url` çağrılır, Then `403 Forbidden` + `{error_code: "TALENT_PROFILE_REQUIRED"}` döner (bu uç yalnızca öğrenci/talent persona'sı için tasarlanmıştır — bkz. Persona). *(code-copilot'un implementasyon turunda bulunan bir persona-kısıtı ihlali sonrası eklendi, red-team incelemesiyle test kapsamına alındı.)*
AC-S1. [Critical] Given kimlik doğrulanmış talent A, When istek body'sinde (varsa herhangi bir alanda) başka bir talent'in kimliğini taşımaya çalışır, Then `object_key` yine de auth bağlamından çıkarılan A'nın `owner_talent_id`'siyle üretilir — body'deki hiçbir kimlik alanı dikkate alınmaz (Elevation testi: A'nın token'ıyla `evidence/{B_id}/...` formatında bir object_key asla üretilemez).
AC-S2. [High] Given kimlik doğrulanmış kullanıcı, When geçerli bir upload-url isteği gönderir, Then presigned URL'nin imzası MinIO'da `Content-Type` ve `Content-Length` (üst sınır) koşuluna bağlıdır — istemci imzalanan `content_type`/boyuttan farklı bir dosyayı MinIO'ya PUT etmeye çalıştığında MinIO isteği reddeder (Tampering testi: yalnızca backend'in allowlist kontrolüne güvenmek yeterli değildir, presigned URL'nin kendisi de kısıtlayıcı olmalıdır).
AC-S3. [High] Given aynı kullanıcı dakikada 10'dan fazla `upload-url` isteği gönderir, When eşik aşılır, Then `429 Too Many Requests` döner (bkz. `.claude/rules/security.md`: "Rate limit: login, kayıt, şifre sıfırlama, dosya yükleme uçlarında"). Eşik ve altyapı `plan.md`'de netleşti: dakikada 10 istek/kullanıcı, in-memory sayaç (Redis yasaklı, tek-VPS/MVP varsayımıyla — process restart'ta sıfırlanma ve çoklu worker'da tutarsızlık kabul edilen risk, bkz. Risks).
AC-S4. [Medium] Given MinIO veya API hata döndürür (503, 422 vb.), When hata yanıtı istemciye iletilir, Then yanıt gövdesinde MinIO'nun ham hata mesajı/stack trace'i veya iç bucket/endpoint bilgisi yer almaz — yalnızca tanımlı `error_code` + genel mesaj döner (Info Disclosure testi).

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | `200` + `{upload_url, object_key, expires_in: 900}` | Yok (DB kaydı yok, sadece imzalı URL üretimi) | Yükleme başlar (istemci MinIO'ya PUT eder) | AC-1 |
| 2 | Kimliksiz istek | `401 Unauthorized` | Yok | "Giriş yapmalısınız" | AC-2 |
| 3 | Allowlist dışı content_type | `422` + `{error_code: "UNSUPPORTED_CONTENT_TYPE", allowed: [...]}` | Yok | "Desteklenmeyen dosya türü" | AC-3 |
| 4 | Boyut aşımı (>10MB) | `422` + `{error_code: "FILE_TOO_LARGE"}` | Yok | "Dosya çok büyük" | AC-4 |
| 5 | Geçersiz filename | `422` (FastAPI/Pydantic standart validation error) | Yok | Alan altı hata | AC-5 |
| 6 | MinIO erişilemez | `503` + `{error_code: "STORAGE_UNAVAILABLE"}` | Yok (transaction yok, DB yazılmıyor) | "Şu an kullanılamıyor, tekrar deneyin" | AC-6 |

**Kaynak yok satırı:** Uygulanmaz — bu uç bir kaynağı okumuyor, tekil üretim yapıyor (idempotent olmayan bir POST ile yeni bir imzalı URL üretiliyor). Silindi.

**Kısmi başarı:** Uygulanmaz — işlem atomik tek adımdır (imza üretimi ya başarılı ya değil, ara durum yok). Silindi.

**Hiçbir şey yapılamadı ama hata da yok:** Uygulanmaz — her çağrı ya `200` + geçerli URL ya da açık bir hata koduyla sonuçlanır; sessiz no-op senaryosu bu senkron tekil-üretim ucunda mümkün değil. Silindi.

**Boş sonuç ↔ hata ayrımı:** Uygulanmaz — bu uç liste/koleksiyon dönmüyor, tekil obje üretiyor; "boş sonuç" kavramı yok.

## Test Strategy
Unit: 70% — `services/storage.py` içindeki `content_type` allowlist kontrolü, `size_bytes` sınır kontrolü, `object_key` üretimi (`{uuid}.{ext}` formatı + `evidence/{talent_id}/` prefix), filename validasyonu (Pydantic schema testleri dahil).
Integration: 20% — gerçek/mock MinIO istemcisiyle presigned URL üretimi, MinIO bağlantı hatası simülasyonu → 503 döngüsü, endpoint'in auth middleware ile entegrasyonu.
E2E: 10% — kimlik doğrulanmış kullanıcı tam happy-path akışını (upload-url iste → dönen URL'ye gerçek/test MinIO'ya PUT et) tamamlar.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (allowlist/content_type/boyut/filename doğrulama mantığı için — orijinal "magic-byte coverage" hedefi kapsam daralması nedeniyle bu doğrulama mantığına devredildi)
Performance Target: p95 < 300ms (imzalı URL üretimi, MinIO'ya ağ çağrısı dahil)
Memory: Belirtilmedi
Görsel/UI kriteri: Yok (bu görev saf backend API ucu, frontend entegrasyonu kapsam dışı)
Diğer ölçülebilir kriterler: —

## Kapsam Dışı
- Evidence DB kaydı (PLAN 2.6) — `evidence` tablosuna satır eklenmesi bu görevde yapılmaz.
- Gerçek magic-byte/byte-level MIME doğrulama ve virüs (ClamAV) taraması — final analiz §18'e göre ayrı bir worker + outbox akışında yapılacak (muhtemelen PLAN 2.6+).
- Download endpoint (`GET /evidence/{id}/download-url`).
- Çoklu dosya yükleme, dosya silme/versiyonlama.
- Thumbnail üretimi.
- Rate limiting'in **somut eşik değeri ve altyapısı** (`plan` adımında netleşecek — Redis yasaklı olduğu için basit in-memory/DB sayaç değerlendirilmeli). Rate limitin **kendisi** kapsam dışı değildir — bkz. AC-S3, `.claude/rules/security.md` bu uç için rate limiti değişmez kural olarak zorunlu kılıyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `api/evidence.py` — yeni endpoint (`POST /evidence/upload-url`)
- `services/storage.py` — MinIO presigned URL üretimi, allowlist/boyut/object_key mantığı
- `schemas/evidence.py` — request/response Pydantic şemaları
- `core/config.py` — MinIO/S3 bağlantı ayarları (bucket adı, endpoint, TTL sabiti)
- `tests/test_storage.py` — unit testler
- `tests/authorization/test_evidence_upload_url.py` — yetkilendirme testi (401/kendi adına üretim doğrulaması)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle (`C:\Users\Meyrem\Desktop\P\yetkin360`) aynı olup olmadığı bu görev kapsamında ayrıca kontrol edilmedi. Sonraki adımlar (plan/code-copilot/test-copilot) arama kapsamını proje klasörüyle sınırlı tutmalı.

## Rollback Beklentisi
S3/MinIO PUT işlemi atomiktir. Kullanılmayan imzalı URL, TTL (900 saniye) dolduğunda kendiliğinden geçersiz olur — ekstra cleanup job gerekmez. Bu uçta DB yazma işlemi olmadığı için transaction/rollback senaryosu yoktur.

## Risks
- **Content-Type/Content-Length spoofing riski (Tampering):** İstemcinin backend'e bildirdiği `content_type`/`size_bytes` ile gerçekte MinIO'ya PUT ettiği byte'lar farklı olabilir. Azaltma: presigned URL imzasına `Content-Type` ve max `Content-Length` koşulu dahil edilmeli (bkz. AC-S2) — aksi halde allowlist kontrolü yalnızca "security theater" olur. Bu, gerçek magic-byte doğrulamasının (worker aşaması) yerini tutmaz, onu tamamlar.
- **In-memory rate-limit sayacının sınırları (kabul edilen risk):** `plan.md`'de dakikada 10 istek/kullanıcı, in-memory `dict` sayaç olarak kararlaştırıldı. Process restart'ta sayaç sıfırlanır, birden fazla uvicorn worker process'i varsa (tek-VPS'te tipik olarak tek process ama ölçekte artabilir) sayaç paylaşılmaz — bu MVP'de kabul edilen bir risktir, DB/Redis tabanlı kalıcı çözüm daha büyük ölçekte (V2) değerlendirilmeli.
- **MinIO bucket policy detayı doğrulanmadı:** Talent-prefix bazlı erişim kısıtlamasının (`evidence/{talent_id}/` altında yalnızca ilgili kullanıcının yazabilmesi) MinIO IAM/policy seviyesinde nasıl uygulanacağı bu görevde netleştirilmedi — `services/storage.py` implementasyonunda ayrıca değerlendirilmeli.
- **Repudiation kapsam dışı bırakıldı (kabul edilen risk):** Bu uç DB'ye yazmıyor (evidence kaydı PLAN 2.6'da), dolayısıyla "kim, ne zaman upload-url istedi" audit log'u bu görevde tutulmuyor. Gerekçe: audit_events tablosuna yazım, evidence kaydının kendisiyle birlikte (PLAN 2.6) ele alınacak; bu ucun tek başına (DB'siz) audit'lenmesi ayrı bir altyapı gerektirir ve MVP'de orantısız olur.

## Assumptions
- **Dosya boyutu sınırı 10MB olarak varsayıldı** — final analizde resmi bir MB rakamı yok, kullanıcı bu varsayımı onayladı ama ürün kararı olarak değişebilir.
- Presigned URL TTL 15 dakika (900 saniye) olarak belirlendi (10 dakikaya kıyasla yavaş bağlantılı kullanıcılar için daha güvenli marj).
- `object_key` formatı `evidence/{owner_talent_id}/{uuid}.{ext}` olarak belirlendi (düz `{uuid}.{ext}` değil) — bucket içi erişim/audit ayrımı için.
- `owner_talent_id` istek body'sinde taşınmaz, kimlik doğrulama bağlamından (JWT/session) çıkarılır — spoofing önlenir.
- `evidence` tablosu **append-only DEĞİLDİR** (CLAUDE.md'nin append-only listesinde yok; final analiz §12.3: soft delete + 30 gün sonra dosya hard delete, `scan_status` alanı UPDATE edilir). Bu görevde evidence tablosuna hiç dokunulmuyor, ancak ileride (PLAN 2.6) o tabloya yazılacak kayıtlar bu soft-delete politikasına tabi olacak — bilgi notu olarak kaydedildi.

## Unknowns
- MinIO bucket policy'sinin talent-prefix bazlı erişim kısıtlamasını destekleyip desteklemediği ayrıca doğrulanmalı (implementasyon aşamasında).
- Presigned URL'nin TTL içinde birden fazla kez kullanılıp kullanılamayacağı (tekrar PUT/üzerine yazma) MinIO'nun davranışına bağlı — evidence DB kaydı aşamasında (PLAN 2.6) object_key tekilliği/immutability ayrıca ele alınmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → öğrenci/talent (beyan sahibi) (kullanıcı mesajından)
2. Kritiklik → kritik, kanıt olmadan zincir kırılır (kullanıcı mesajından)
3. Happy path akışı → bkz. AC-1 ve Davranış Sözleşmesi (Sonnet 5 low alt-ajanı tarafından detaylandırıldı: kimlik doğrulama bağlamından `owner_talent_id` çıkarımı, `object_key` örneği)
4-5. Edge case'ler ve davranış sözleşmesi → kullanıcı mesajından + Sonnet 5 low alt-ajanı tarafından yanıtlandı (422 vs 413 ayrımı: "size_bytes henüz byte akmadan deklare ediliyor, bu yüzden diğer alan doğrulama hatalarıyla tutarlı 422 ailesinde kalmalı" gerekçesiyle)
6. Benchmark → kullanıcı mesajından, kapsam daralması nedeniyle "magic-byte coverage" → "allowlist/doğrulama coverage" olarak güncellendi
7. Kapsam dışı → kullanıcı mesajından + final analiz teyidiyle genişletildi (gerçek magic-byte doğrulama da kapsam dışına eklendi)
8. Muhtemel dosyalar → kullanıcı mesajından
9. TTL/boyut/allowlist → kullanıcı önerisi + Sonnet 5 low alt-ajanı tarafından netleştirildi (TTL: 15dk, gerekçe: yavaş ağ marjı)
10. Rollback → kullanıcı mesajından
11. Onay sahibi → otomatik test yeterli (kullanıcı mesajından)
12. Test stratejisi → 70/20/10 (kullanıcı mesajından)
13. Evidence append-only mu? → final analiz §12.3 grep ile teyit edildi: HAYIR, soft delete + scan_status update var (kullanıcıya soruldu, "bilgi notu olarak yaz" onaylandı)
14. Upload-url rol kısıtı → final analiz/PLAN'da özel rol kısıtı yok, sadece "yetki + kota kontrolü" (§18) — ownership check (kendi adına üretim) yeterli kabul edildi
15. Magic-byte senkron mu asenkron mu? → final analiz §18 ile ÇELİŞKİ tespit edildi, kullanıcıya soruldu → "final analize uy" seçildi, kapsam daraltıldı (bkz. Mimari Sapma Notu)
16. Boyut sınırı resmi rakam var mı? → final analizde yok, kullanıcıya soruldu → 10MB varsayımıyla devam onaylandı
17. object_key formatı, Content-Type/Length spoofing riski, rate limiting, expires_in birimi → Sonnet 5 low alt-ajanı tarafından yanıtlandı (gerekçeler yukarıda ilgili bölümlerde)
18. Threat model (STRIDE-lite) → `threat-model` skill'i çağrıldı: Tampering (AC-S2), Elevation (AC-S1), DoS/rate-limit (AC-S3, `.claude/rules/security.md` ile teyitli), Info Disclosure (AC-S4) somut AC'lere çevrildi; Spoofing zaten AC-2 ile karşılanıyor; Repudiation kabul edilen risk olarak işaretlendi (gerekçe: Risks bölümünde). AC-S1 yetkilendirme kriteri ürettiği için `authz-test` skill'i `plan`/`test-copilot` aşamasında ayrıca çağrılmalı.
