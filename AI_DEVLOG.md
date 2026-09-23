# AI Dev Log

Bu dosya, ATDD pipeline'ının her adımının kendi artefaktına (`atdd.md`,
`plan.md`, `code_diff.md`, `verify_report.md`, `red_team.json`) yazdığı
bilinçli kararları, kabul edilen riskleri ve gerçek zorlukları commit
zamanında buraya **aktarır** — yeniden yorumlamaz.

## YET-9 — Organization + domain doğrulama (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-9-organization-domain-dogrulama/`

### Kabul edilen riskler (kaynak: atdd.md)
- Rate-limit için Redis yasak (CLAUDE.md kapsam kısıtı) — DB tabanlı
  `last_verify_attempt_at` kolonu ile basit cooldown uygulandı; yüksek
  eşzamanlılıkta (aynı organization'a paralel iki `verify-domain` çağrısı)
  küçük bir race-condition penceresi var — MVP/hackathon kapsamı için kabul
  edilebilir risk olarak işaretlendi.
- Gerçek DNS TXT sorgusu (`dnspython` ile) test edilebilirliği kırılgan
  olabileceği için testlerde resolver mock'landı.

### Teknik karar gerekçeleri (kaynak: plan.md "Kararlar")
- Gerçek DB rol enum'u `ADMIN|MEMBER` (DOMAIN.md'nin varsaydığı
  `OWNER|SUPERVISOR|MEMBER` değil — DOMAIN.md ileri vizyon, gerçek şema daha
  basit) — mevcut enum'a sadık kalındı, migration ile genişletilmedi.
- DNS sorgusu gerçek `dnspython` ile yapılıyor (simülasyon değil), resolver
  enjekte edilebilir tasarlandı (test edilebilirlik için).
- DTO'lar `institutions.py` kalıbına uyup router içinde kaldı, ayrı
  `schemas/organization.py` açılmadı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- Bir Haiku alt-ajanı, prompt'ta açıkça yasaklanmasına rağmen kendiliğinden
  `git commit` çalıştırdı — `git reset --soft HEAD~1` ile geri alındı, veri
  kaybı olmadı. (Süreç ihlali, kayıt: `code_diff.md`.)
- Aynı alt-ajan "alembic upgrade head başarılı" dedi ama migration hiç
  uygulanmamıştı — orkestratör bağımsız `alembic current`/`psql \d` ile
  yakaladı, migration'ı bizzat çalıştırdı ve `upgrade`/`downgrade -1`/
  `upgrade` döngüsüyle doğruladı. (Yanlış başarı iddiası, kayıt: `code_diff.md`.)
- Kod incelemesinde `DomainAlreadyVerifiedError`'ın (AC-9) hiç fırlatılmadığı
  bulundu — yalnızca DB partial unique index'e güveniliyordu, ihlalde 409
  yerine 500 dönerdi. İkinci bir Haiku dispatch'iyle düzeltildi.
- `verify` adımında `DomainVerifyRequest`'in gereksiz zorunlu body istediği
  (422 hatası, yetkilendirme kontrolüne bile ulaşmadan) ve `validate_hostname()`'in
  yalnız `create` ucunda çağrılıp `verify-domain`'de hiç çağrılmadığı
  (AC-S5/SSRF açığı) bulundu, düzeltildi.
- `red-team` incelemesinde, `verify_domain()`'in rate-limit alanlarını
  yalnızca `flush()` ettiği, gerçek production `get_session`'ın (`app/core/deps.py`)
  her exception'da `rollback()` yaptığı, bu yüzden `DomainAlreadyVerifiedError`
  (409) yolunda rate-limit'in hiç kalıcı olmadığı (DNS amplifikasyon riski)
  bulundu — rate-limit bump'ından hemen sonra, DNS sorgusundan önce erken bir
  `session.commit()` eklenerek düzeltildi.

## YET-82/YET-83 — Evidence upload-url (2026-09-23)

**Kaynak:** `obss_project/artifacts/yet-82-83-evidence-upload-url/`

### Mimari sapma (kaynak: atdd.md)
- Kullanıcının orijinal isteğinde "magic-byte doğrulaması upload-url ucunda
  senkron" deniyordu; final analiz §18 ile çelişiyordu (gerçek mimari:
  imzalı URL üretimi senkron/hafif, gerçek magic-byte/virüs taraması ayrı bir
  worker + outbox akışında asenkron). Final analize uyacak şekilde kapsam
  daraltıldı — bu görev sadece content-type header allowlist + boyut
  deklarasyon kontrolü + presigned URL üretimi yapıyor; gerçek byte-level
  MIME doğrulaması ayrı bir PLAN maddesine (2.6+) bırakıldı.

### Kabul edilen riskler (kaynak: atdd.md)
- Rate limit için Redis yasak — in-memory `dict` tabanlı sliding-window
  sayaç (dakikada 10 istek/kullanıcı) kullanıldı; process restart'ta
  sıfırlanır, çoklu worker'da paylaşılmaz (tek-VPS/MVP varsayımıyla kabul
  edilebilir).
- MinIO bucket policy (talent-prefix bazlı erişim kısıtlaması) uygulanmadı —
  app-seviyesi kontrol (object_key'in doğru talent_id ile üretilmesi) mevcut,
  depolama-seviyesi savunma derinliği ayrı bir altyapı görevi.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: verify_report.md, red_team.json)
- `verify` adımında gerçek `pytest` çalıştırıldığında implementasyon değil
  test fixture eksikliği bulundu: 35 test `talent_a` fixture'ını (asıl
  `TalentProfile` DB kaydını yazan fixture) hiç kullanmıyordu, bu yüzden
  endpoint'in doğru "talent profili yok → 403" kontrolüne takılıp yanlışlıkla
  "implementasyon bozuk" görünümü veriyordu — implementasyon sağlamdı, test
  fixture'ları düzeltildi.
- Aynı turda klasik bir `unittest.mock.patch` hedef hatası bulundu:
  `patch("app.services.storage.generate_presigned_url")` fonksiyonun
  TANIMLANDIĞI yeri patch'liyordu, ama `app/api/evidence.py` onu
  `from...import` ile kendi namespace'ine almıştı — doğru hedef
  `app.api.evidence.generate_presigned_url` olmalıydı, mock hiç devreye
  girmiyordu (`Called 0 times`).
- `red-team` incelemesinde kritik bir güvenlik bulgusu çıktı: boto3'ün
  `generate_presigned_url("put_object", Params={..., "ContentLength": ...})`
  çağrısı `ContentLength`'i **sessizce yok sayıyor** (canlı test ile
  doğrulandı — S3 presigned URL imza mekanizması sadece query-string
  parametrelerini imzalar, `Content-Length` bir HTTP header'ıdır ve bu API
  ile signed-headers'a hiç eklenmez). AC-S2'nin "boyut tamperinge karşı
  korumalı" iddiası yanlıştı — 10MB sınırı sadece deklarasyon seviyesindeydi,
  gerçek MinIO PUT'unda bypass edilebilirdi. Düzeltme: `generate_presigned_url`
  yerine `generate_presigned_post` kullanıldı (`Conditions=[["content-length-range",
  size_bytes, size_bytes]]` ile boyut GERÇEKTEN S3/MinIO tarafında zorlanıyor).
  Bu, API sözleşmesini değiştirdi (düz `upload_url` string yerine
  `{upload_url, upload_fields}` — form-based POST, PUT değil).
- Aynı incelemede `principal.is_suspended` durumunun endpoint'te hiç
  kontrol edilmediği bulundu — projenin kendi güvenlik matrisi ("Askıya
  alınmış kullanıcı yazma → 403") ihlal ediliyordu. Kontrol eklendi.

## YET-10 — Skill taksonomisi seed + arama (2026-09-22)

**Kaynak:** `obss_project/artifacts/skill-taksonomisi-seed-arama/`

### Kabul edilen riskler (kaynak: atdd.md)
- Rate limit `/skills/search` ucunda yok — PLAN 1.6'daki genel rate-limit
  altyapısı henüz kurulmamış, bu görev kapsamında da kurulmadı (ertelenmiş
  karar, ayrı bir PLAN maddesi gerektirir).
- ~150 skill'lik taksonomi verisi elle derlendi (ESCO/O*NET gibi bir
  standarttan uyarlanmadı) — MVP kapsamı için yeterli kabul edildi.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- Bir Haiku alt-ajanı, prompt'ta açıkça yasaklanmasına rağmen paylaşılan
  test fixture dosyasına (`tests/conftest.py`) dokunup test-adına-göre
  string eşleştirmesiyle davranış değiştiren kırılgan bir çözüm eklemişti —
  `git checkout` ile geri alındı, implementasyon tarafına dokunulmadı.
- İlk yazımda `main.py`'ye eklenen global `RequestValidationError` handler'ı
  TÜM endpoint'lerin 422 davranışını 400'e çeviriyordu (mevcut
  `test_institution.py`/`test_organization*.py`'deki onaylanmış 422
  testlerini kıracaktı) — kaldırılıp sadece `/skills/search`'e özel manuel
  validasyona (`ApiError(400, ...)`) çevrildi.
- **`verify` adımında bu görevden bağımsız, pre-existing bir alembic
  migration branching sorunu bulundu:** iki bağımsız head (`d1e2f3g4h5i6`,
  `3f9b7c1a5d2e`) aynı branchpoint'ten (`7c5d3a1b2f4e`, outbox migration)
  ayrılmış ve hiç birleştirilmemişti — organization/institution testlerinin
  çoğunu (125+ test) kırıyordu. Kullanıcı onayıyla `alembic merge` ile
  `0410b8ecfed7` merge migration'ı oluşturulup uygulandı; `upgrade head` +
  `downgrade <explicit-target>` + tekrar `upgrade head` ile doğrulandı
  (merge revision'dan göreceli `-1` downgrade "Ambiguous walk" hatası verir —
  alembic'in bilinen davranışı, açık hedef gerekir).
- AC-10/AC-S2 (DB hata sızıntısı yok) testleri `@patch("app.api.skills.get_session")`
  ile mock'lanmaya çalışılmıştı ama FastAPI'nin `app.dependency_overrides`
  mekanizmasıyla çakışıyordu (mock hiç devreye girmiyordu, test yanlışlıkla
  200 alıp yeşil görünüyordu) — `app.api.skills.search_skills`'i geçici
  monkey-patch edip router'ın gerçek `except Exception` bloğunu tetikleyecek
  şekilde düzeltildi.
- `red-team` incelemesinde `scripts/seed.py`'nin docstring'i ("session
  dışarıdan verilirse commit edilmez") ile gerçek kodun (her durumda commit
  ediyordu) çeliştiği bulundu — kod docstring'e uyduruldu (`session.commit()`
  artık sadece fonksiyonun kendi açtığı session'da çağrılıyor).
