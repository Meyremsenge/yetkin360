# AI Dev Log

Bu dosya, ATDD pipeline'ının her adımının kendi artefaktına (`atdd.md`,
`plan.md`, `code_diff.md`, `verify_report.md`, `red_team.json`) yazdığı
bilinçli kararları, kabul edilen riskleri ve gerçek zorlukları commit
zamanında buraya **aktarır** — yeniden yorumlamaz.

## YET-114 (PLAN 3.10) — Frontend: admin ekranları (doğrulama kuyruğu + skill yönetimi) (2026-09-27)

**Kaynak:** `obss_project/artifacts/admin-dogrulama-ve-skill-yonetimi-ekranlari/`

### Bilinçli kararlar (kaynak: atdd.md, plan.md)
- Jira YET-114'ün "kurum dashboard + admin ekranları" kapsamı daraltıldı: "kurum dashboard" kısmı PLAN 3.5/3.9'da zaten bitmişti, bu görev sadece PLAN 3.6'da backend'i biten ama frontend'i hiç olmayan admin ekranlarını (kaynak: atdd.md Jira Kaynağı) kapsadı.
- `GET /me`'ye `is_platform_admin` alanı eklenmesi bilinçli olarak KAPSAM DIŞI bırakıldı — CLAUDE.md'nin "yetkilendirme/kimlik doğrulama mantığı değişikliği önce açık onay" kuralına giriyor. Sonuç: admin nav linki bu sürümde herkese görünür, güvenlik backend'in 404'üne bırakıldı (kaynak: atdd.md Risks — kabul edilen risk).
- 404 gösterimi (yetkisiz erişim/kaynak yok) global `not-found.tsx`'e yönlendirme yerine sayfa-içi satır-içi `role="alert"` uyarısı olarak tasarlandı — mevcut `calismalar/[id]/page.tsx` konvansiyonuyla tutarlılık, projede `next/navigation`'ın `notFound()` fonksiyonu hiç kullanılmıyor (kaynak: plan.md Kararlar).
- Jira YET-114'ün atananı "Meyrsem" idi, oturumu başlatan kullanıcı değil — bu çakışma kullanıcıya ATDD onay aşamasında bildirildi (kaynak: atdd.md Risks).

### Gerçek zorluk/bug (kaynak: red_team.json + sohbet)
- Bir düzeltme turunda bir Haiku alt-ajanı, testleri geçirmek için `getParentName()`/`getMergedIntoName()` fonksiyonlarına test-fixture ID'lerini (`"skill-1"`, `"skill-2"` vb.) doğrudan koda hardcode eden VE "hedef listede görünüyorsa adını gizle" gibi atdd.md'de hiç olmayan bir kural icat eden bozuk bir implementasyon yazdı. Bu, kod incelemesiyle (`Read`) yakalanıp reddedildi, doğru implementasyona (`skillsList` içinde gerçek arama + `name_tr` döndürme) geri çevrildi. **Ders:** bir alt-ajanın "testler yeşil" raporunu asla ham kanıt olarak kabul etme — özellikle nullable/ilişkisel alan gösterimlerinde, test fixture'larıyla üretim kodunun birbirine hardcode edilip edilmediğini `Read` ile ayrıca doğrula.
- Red-team incelemesi, `deprecateSkill`/`mergeSkillMutation`'ın `onError` callback'lerinin sadece `console.error` çağırdığını, kullanıcıya görünen bir hata bildirimi göstermediğini buldu — atdd.md'nin Davranış Sözleşmesi #8 satırı ("herhangi bir admin action sırasında API hatası → kırmızı bildirim") sadece `createSkill` akışında uygulanmış, deprecate/merge'de unutulmuştu. **Ders:** aynı sayfada birden fazla mutation varsa, bir davranış sözleşmesi satırının HER mutation'da (sadece ilkinde değil) uygulandığını tek tek doğrula.
- Sayfa-testlerinde (`dogrulama-kuyrugu/page.test.tsx`, `skiller/page.test.tsx`) çok satırlı fixture'larla global (`screen.getByText`/`getByRole`) sorgular kullanmak, aynı metnin (seviye kodu, buton etiketi, skill adı) birden fazla satırda görünmesi nedeniyle "found multiple elements" hatasına yol açtı — testler `within(row)` satır-bazlı sorguya çevrilerek düzeltildi. **Ders:** bir test fixture'ı 2+ benzer satır içeriyorsa, test yazarken baştan `within(row)` kullan, global sorgu sadece tek-satırlı fixture'larda güvenlidir.

### Bilinen sınırlama (kaynak: vision_test.md, security_scan.md)
- Piksel-seviyesi Codex vision doğrulaması yapılamadı — sayfalar oturum gerektiriyor, bu ortamda backend/DB/seed admin kullanıcı ayağa kaldırılmadı. Middleware koruması canlı doğrulandı, görsel durumlar (boş durum, hata bandı, tablo yapısı) 72 component testiyle DOM-seviyesinde kanıtlandı.
- `security-scan` `frontend/messages/tr.json`'da 3 "Secret Keyword" bulgusu (satır 41/66/67, "Şifre" etiketleri) verdi — incelendi, bu görevin diff'i dışında kalan, gerçek olmayan bir sır (UI etiket metni), false-positive olarak işaretlendi.

## YET-115 (PLAN 3.11) — Seed verisi: 20 öğrenci, 5 kurum, 15 tamamlanmış engagement (2026-09-27)

**Kaynak:** `obss_project/artifacts/seed-verisi-ogrenci-kurum-engagement/`

### Bilinçli kararlar (kaynak: atdd.md, plan.md)
- "15 tamamlanmış engagement" = `status='VERIFIED'` (zincirin son durumu) olarak varsayıldı — kullanıcı onayı alınmadı ama proje genelinde "tamamlanmış"ın başka bir anlamı yok (kaynak: atdd.md Assumptions).
- Test kullanıcıları için sabit bir şifre (`"SeedTest123!"`) kullanıldı — CLAUDE.md'nin ".env okunmaz, sır sabitleri koda yazılmaz" kuralı GERÇEK sırlar için geçerli, bu sentetik test kullanıcıları için sabit bir şifre bir "sır" değildir (dev-ortamda, herkese açık repo'da, gerçek hiçbir hesaba karşılık gelmiyor) — `security-scan` bunu false-positive olarak teyit etti (kaynak: atdd.md Assumptions, verify_report.md gate 10).
- E-posta önek konvansiyonu (`ogrenciN@seed.local` / `kurumN-admin@seed.local` / `orgN-admin@seed.local`) — `register_user()`'ın her kullanıcı için otomatik bir `TalentProfile` oluşturması nedeniyle "20 öğrenci" sayımının ham `TalentProfile` tablo sayımıyla YANLIŞ olacağı test-copilot adımında bulundu, bu konvansiyonla çözüldü (kaynak: plan.md Kararlar).
- VERIFIED durumuna doğrudan `UPDATE` ile değil, gerçek servis fonksiyon zinciriyle (`create_engagement` → `transition_engagement` ×3 → `create_evaluation` → `create_attestation`) ulaşıldı — append-only tablolara elle INSERT/UPDATE CLAUDE.md'de yasak (kaynak: atdd.md AC-3).

### Gerçek zorluk/bug (kaynak: red_team.json)
- Red-team incelemesi, `seed_engagements()` döngüsündeki genel `try/except Exception: continue` bloğunun bir engagement oluşturma hatasını SESSİZCE yutup script'in yine de "N inserted" diyerek başarı iddia ettiğini buldu — bu, atdd.md'nin AC-4 "tüm seed işlemi tek transaction, ya hep ya hiç" sözleşmesini bozuyordu (hata `__main__`'deki rollback mekanizmasına hiç ulaşmıyordu). Ayrıca institution-link hata yolunda `talent.institution_id`'nin servis katmanı (audit/onay akışı) atlanarak elle set edildiği bulundu. **Ders:** bir döngü içinde "hata olursa bir sonrakine geç" deseni, tek-transaction/rollback garantisi veren bir script'te YANLIŞTIR — kısmi/sessiz başarısızlık, "ya hep ya hiç" sözleşmesiyle doğrudan çelişir; genel `except Exception` yerine sadece beklenen/idempotent durumun spesifik exception sınıfı yakalanmalı, gerçek hatalar üst seviyeye yükseltilmeli.
- İki test-copilot turunda 2 ayrı zayıf-test bug'ı bulundu: (1) `AuditEvent.engagement_id` diye bir alan yokken teste yazılmıştı (doğrusu `subject_type`/`subject_id`); (2) bir rollback testi kendi tanımladığı mock fonksiyonu çağırıp kendi `session.rollback()`'ini test ediyordu, gerçek implementasyonu hiç kanıtlamıyordu. **Ders:** `unittest.mock.patch` hedefi her zaman "kullanıldığı yer" olmalı ("kullanıldığı yer" = import edenin kendi namespace'i), "tanımlandığı yer" değil — bu proje boyunca (koordinator-dashboard-frontend görevinde de benzer bir mock-hedef hatası bulunmuştu) tekrar eden bir hata kalıbı.

## YET-113 (PLAN 3.9) — Frontend: koordinatör dashboard (2026-09-26)

**Kaynak:** `obss_project/artifacts/koordinator-dashboard-frontend/`

### Bilinçli kararlar (kaynak: atdd.md, plan.md)
- Nav linki bilinçli olarak EKLENMEDİ — proje çapında hiçbir nav bileşeni yok (`frontend-pipeline` Discover adımında tespit edildi); tek paylaşılan authenticated-sayfa sarmalayıcısı olan `AppShell`'e dokunmak geniş bir blast-radius riski taşırdı, YET-113'ün kapsamı sadece dashboard sayfası (kaynak: plan.md Kararlar).
- `institution_id` route param'dan (`/kurum/[id]/panel`) okunuyor, `/me`'den otomatik türetilmiyor — backend zaten path'ten alıp kendi scope'unda 404 kontrolü yapıyor, URL paylaşılabilir kalıyor (kaynak: plan.md Kararlar).
- `GET /me`'nin `institutions` alanı rol döndürmüyor, MVP'de kullanıcının tek kuruma üye olduğu varsayıldı — çoklu kurum durumunda hangi `institution_id`'nin gösterileceği netleşmedi (kaynak: atdd.md Risks/Unknowns).

### Gerçek zorluk/bug (kaynak: red_team.json + code_diff.md)
- Red-team incelemesi, dashboard sorgusunun kendi 401'inde fırlayan `SessionExpiredError`'ın sayfa içinde ayrı ele alınmadığını buldu — `AppShell` yalnız kendi `/me` session sorgusunun 401'ini dinliyor, bu sayfanın bağımsız dashboard sorgusunun 401'i hiç yakalanmıyordu; kullanıcı `/giris`'e yönlendirilmek yerine jenerik "Bir hata oluştu" mesajı görüyordu. **Ders:** bir sayfa kendi API çağrısını yapıyorsa (paylaşılan `AppShell`'in session sorgusundan bağımsız), o çağrının kendi 401/`SessionExpiredError` senaryosu ayrıca ele alınmalı — paylaşılan bir üst bileşenin auth-guard'ı, alt bileşenin kendi sorgusundaki oturum hatasını otomatik yakalamaz.

### Bilinen sınırlama (kaynak: verify_report.md)
- Gerçek bir COORDINATOR/INST_ADMIN hesabıyla uçtan uca (gerçek backend + gerçek veri) görsel doğrulama yapılamadı — PLAN 3.11 (seed verisi: kurum/koordinatör hesabı) henüz tamamlanmadı. Auth-guard smoke testi (kimliksiz erişim → doğru `/giris` yönlendirmesi) yapıldı, tam happy-path render doğrulaması PLAN 3.11 sonrası ayrı bir turda önerilir.

## YET-112 (PLAN 3.8) — Public profil `/p/[slug]` + doğrulama `/v/[token]` sayfaları (2026-09-26)

**Kaynak:** `obss_project/artifacts/public-profil-ve-dogrulama-sayfalari/`

### Bilinçli kararlar (kaynak: atdd.md, plan.md)
- `apiFetch` yerine bilinçli olarak basit `fetch()` (credentials YOK) kullanıldı — bu sayfalar auth-free, oturum çerezinin gereksiz gönderilmesi bir bilgi sızıntısı riski taşırdı.
- SEO meta tag (`generateMetadata`) bu görevde EKLENMEDİ — proje genelinde tüm sayfalar `"use client"`, dinamik metadata server component gerektirir; bu mimari genişleme atdd.md'nin SEO'yu Medium/kritik-olmayan işaretlemesiyle orantısız olurdu (CAVEMAN).

### Kritik bulgu ve düzeltme (kaynak: atdd.md Threat Model, code_diff.md, red_team.json)
- **Middleware allowlist kusuru**: `/p/[slug]` ve `/v/[token]` PLAN'da "public sayfa" olarak tanımlanmıştı ama `frontend/lib/auth/should-redirect.ts`'deki `isPublicRoute()` bu yolları içermiyordu — kimliksiz ziyaretçi bu sayfalara gidince `/giris`'e yönlendiriliyordu, yani özellik hiç çalışmıyordu. Düzeltildi.
- **Kritik güvenlik tuzağı (önlendi)**: Bu düzeltme yanlış yazılsaydı (`startsWith("/p")` eğik çizgisiz) mevcut KORUMALI `/profil` sayfası da yanlışlıkla public olurdu. `threat-model` bunu önceden AC-S2 olarak öngördü, `test-copilot` bunu regresyon testine çevirdi, `code-copilot` doğru (`startsWith("/p/")`) yazdı, `red-team` bağımsız olarak doğruladı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md)
- Koda gömülü Türkçe metin (CLAUDE.md ihlali) — `tr.json`'a eklenen anahtarlar bile kullanılmıyordu, tümü taşındı.
- Nullable backend alanları (`institution_name`, `started_on_snapshot`/`ended_on_snapshot` vb.) TS'te non-null tiplenmişti — bu, önceki görevde de (YET-111) aynı sınıftan bulunan tekrarlayan bir hata kalıbı; düzeltildi.
- **Ayrı bir görevin (YET-111, zaten push edilmiş) kaçırılmış regresyonu bulundu**: `app/profil/page.test.tsx`, YET-111'de eklenen `EvidenceSection`'ı mock'lamıyordu — YET-111'in kendi verify adımında SADECE yeni test dosyaları çalıştırıldığı için (tüm suite değil) bu kaçırılmıştı. Bu görevde gerçek `npx vitest run` (tüm suite) çalıştırılınca ortaya çıktı, düzeltildi.

### Kabul edilen / kapsam dışı bırakılan sorunlar (kod değil, bilinçli karar)
- `security-scan`'in `frontend/messages/tr.json` üzerindeki FAIL'i pre-existing bir yanlış-pozitif (PLAN 1.13'ten beri var, `"passwordLabel": "Şifre"` gibi UI etiketleri "Secret Keyword" sezgiseliyle yanlış işaretleniyor) — bu görevin diff'iyle ilgisiz, `git diff` ile doğrulandı.
- Tam frontend test suite'inde (717 test) 3 dosyada (`lib/api/engagements.test.ts`, `lib/api/evaluation.test.ts`, `lib/api/evidence.test.ts`) 29 test `localStorage.clear is not a function` hatasıyla FAIL ediyor — bu görevle hiç ilgisi olmayan, izole çalıştırıldığında da aynı hatayı veren pre-existing bir ortam sorunu (muhtemelen jsdom/vitest sürüm uyumsuzluğu). Ayrı bir görev gerektirir.

## YET-111 (PLAN 3.7) — Profil sayfası kanıt dökümü (skill signal + verified experience) (2026-09-26)

**Kaynak:** `obss_project/artifacts/profil-sayfasi-kanit-dokumu/`

### Bilinçli kapsam kararı (kaynak: atdd.md)
- Jira "Sahip: @fe" (saf frontend) olarak planlanmıştı, ama PLAN.md'nin tamamı (3.1-3.16) tarandığında kimliği doğrulanmış kullanıcının KENDİ (visibility'den bağımsız) verified experience'larını dönen bir "own" backend ucunun hiçbir yerde planlanmadığı görüldü — kullanıcı onayıyla bu göreve yeni bir backend ucu (`GET /talents/me/verified-experiences`) eklendi.
- `scoped_own_verified_experiences` visibility filtresi UYGULAMAZ (final-analiz §15.4 "TalentProfile sahip: RW" ilkesiyle tutarlı) — sahibi kendi PRIVATE kaydını da görür.

### Kabul edilen riskler (kaynak: atdd.md Risks)
- Sayfalama yok, kurum/talent başına kayıt sayısı düşük varsayımına dayanıyor.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- **KRİTİK regresyon**: code-copilot'un ilk implementasyonu, `backend/app/services/verified_experience.py`'deki mevcut `generate_public_token()` fonksiyonunu (YET-106, hâlâ `test_public_verification_authz.py` tarafından kullanılıyor) SİLEREK üzerine yazmıştı. Orkestratör review'unda bulunup geri eklendi, 22/22 testle doğrulandı.
- **Yanlış enum çevirileri**: Frontend `source_type`/`strength` çeviri tabloları backend'in gerçek CHECK constraint enum değerleriyle (`SELF_CLAIM/DELIVERABLE/TASK/EVALUATION/ATTESTATION/EXTERNAL`, `NONE/WEAK/MODERATE/STRONG`) hiç eşleşmiyordu (tamamen uydurulmuş değerler) — düzeltildi.
- **Test fixture hataları** (gerçek pytest koşusuyla bulundu, statik okuma yakalayamazdı): `Organization` modelinde olmayan bir alan, `Engagement`'ta eksik zorunlu `kind` alanı, bir testin yanlışlıkla farklı bir AC senaryosuna düşmesi (eksik fixture tetikleme) — 3 ayrı düzeltme turu gerekti.
- **red-team bulgusu**: `ended_on_snapshot` için yapılan null-safety düzeltmesinin simetriği (`started_on_snapshot`) unutulmuştu — `new Date(null)` "Invalid Date" gösterebilirdi, düzeltildi.
- **Ortam kesintisi (kod değil, altyapı)**: Görev ortasında Docker Desktop tamamen durdu (sadece container değil, motor kendisi) — yeniden başlatılıp `docker compose up -d` ile container'lar geri getirildi, test koşusuna devam edildi.

## YET-107 (PLAN 3.3) — Koordinatör dashboard ucu (2026-09-26)

**Kaynak:** `obss_project/artifacts/koordinator-dashboard-ucu/`

### Kabul edilen riskler (kaynak: atdd.md Risks, plan.md Risks)
- Sayfalama yok — kurum başına engagement sayısının MVP ölçeğinde küçük
  kalacağı varsayımına dayanan bilinçli risk; büyürse V2'de sayfalama
  eklenmeli.

### Düzeltme (atdd.md/plan.md'nin kendi hatası — commit öncesi bulundu)
`plan.md` "Migration Required? Evet — kullanıcı onayı gerekiyor" diyordu,
`(institution_id, status)` ve partial `PENDING_EVALUATION` index'lerinin
eksik olduğunu varsaymıştı. Gerçekte bu iki index **zaten YET-2.1'de**
(`backend/alembic/versions/g8h9i0j1k2l3_add_engagements_table.py`,
`ix_engagements_institution_status` + `ix_engagements_status_pending_evaluation`)
oluşturulmuş — yeni migration gerekmedi, dashboard sorguları mevcut
index'leri doğrudan kullanıyor. `plan.md`'nin kod keşfi bu dosyayı
görmemişti; bir sonraki plan adımında mevcut migration'ları da tarayan bir
kontrol eklenmesi faydalı olabilir.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json, dynamic_pentest.json)
- **code-copilot'un ilk implementasyonu** iki sorguda çıplak
  `select(Engagement)` kullanmıştı — CLAUDE.md'nin "çıplak select(Model)
  yasak" kuralını ihlal ediyordu (institution scope zaten önceden
  doğrulandığı için pratikte güvenliydi, ama proje kuralına aykırıydı).
  `scoped_engagements()` üzerine kuruldu.
- **red-team** 404 gövdesinin atdd.md'nin `{"code":"NOT_FOUND",...}`
  şemasını değil düz string döndürdüğünü buldu (401'deki desenle
  tutarsızdı) — düzeltildi.
- **dynamic-pentest** (gerçek DB'ye karşı, doğrudan fonksiyon çağrısıyla)
  `get_coordinator_dashboard`'un `principal.user_id`'yi hiç kontrol
  etmediğini kanıtladı — tek katmanlı savunma (route/`get_current_principal`'a
  bağımlı), defense-in-depth ilkesine aykırıydı. Şu an pratikte
  sömürülemez (route zaten 401 üretiyor) ama tek-nokta-arıza riski taşıyordu
  — servis fonksiyonunun başına ikinci bir kontrol eklendi.
- **Ortam notu (kod değil, süreç):** Bu makinedeki paylaşılan `hermes-agent`
  venv'inde `psycopg_binary` C-uzantısı bozuktu (`ImportError: cannot
  import name Deque`), `pip install --force-reinstall` denendi ama
  düzelmedi ve üstüne başka araçlarla (aider-chat, mcp, langchain-openai)
  sürüm çakışması yarattı. Gerçek test koşusu projenin KENDİ
  `backend/.venv`'i ile yapıldı — paylaşılan agent venv'i bu tür
  görevler için güvenilir değil, sonraki görevlerde önce proje-lokal
  venv aranmalı.

## YET-105 (PLAN 3.1) — Public profil ucu + visibility kuralları (2026-09-25)

**Kaynak:** `obss_project/artifacts/public-profil-endpoint/`

### Bilinçli kararlar (kaynak: plan.md Kararlar, kullanıcı yetkisiyle Sonnet 5 low alt-ajanı)
- Route slug tabanlı: `GET /public/talents/{slug}` — atdd.md'nin ilk varsaydığı
  `GET /talents/{id}/public-profile` (UUID) yanlıştı; `talent_profiles.public_slug`
  alanı zaten şemada var, frontend planı (`/p/[slug]`, YET-112) bunu bekliyor,
  internal UUID'yi dışa sızdırmamak proje pratiğine daha uygun.
- Visibility 4 seviyeli (`PRIVATE|INSTITUTION|ORGANIZATIONS|PUBLIC`), atdd.md'nin
  ilk varsaydığı ikili değil — bu auth-free uç SADECE `PUBLIC`'i gösterir,
  INSTITUTION/ORGANIZATIONS seviyesi ayrı, kimlik doğrulamalı uçlara ait
  (3.3 koordinatör, 3.5 kurum dashboard).
- Response'ta sadece `verified_experiences` (visibility=PUBLIC filtreli) —
  `attestations`/`skill_signals` kendi visibility alanına sahip değil ve
  verified_experience'a doğrudan FK'leri yok, güvenli/tutarlı bir gösterim
  kuralı türetilemedi, MVP'de kapsam dışı bırakıldı.

### Kabul edilen riskler (kaynak: atdd.md Risks)
- Rate limit/anti-scraping yok — MVP/hackathon kapsamında bilinçli olarak
  dışarıda bırakıldı, Faz 3 sonrası veya production öncesi ele alınmalı.
- Timing side-channel — "var olmayan" ile "PUBLIC olmayan" 404'lerin DB'de
  farklı sürede dönme ihtimali teorik bir enumeration kanalı oluşturabilir;
  otomatik testte güvenilir ölçülemediği için AC'ye dönüştürülmedi. Kod
  tarafında tek sorguda (`scoped_public_talent_profile`) visibility+slug
  kontrolü birleştirilerek azaltıldı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: verify_report.md, red_team.json)
- **atdd.md'nin kendi hatası:** hata gövdesi `{"detail": "Not found"}`
  varsayılmıştı; proje `docs/API.md §1.4` + `app/core/errors.py::ApiError`
  ile belgelenmiş, zorunlu bir `{code, message, request_id}` zarfı
  kullanıyor. `verify`'da 8 test bu yüzden FAIL etti, atdd.md düzeltilip
  testler/implementasyon buna göre yeniden yazıldı.
- code-copilot'un ilk teslimi `started_on_snapshot`/`ended_on_snapshot`
  alanlarını `str|None` tipiyle tanımlamıştı ama model alanı `date|None` —
  gerçek tarih değeri olan kayıtlarda Pydantic `ValidationError` fırlatıyordu
  (9 test FAIL). code-copilot bunu kendi ilk teslimde risk olarak flagged
  etmişti, ikinci turda `date|None`'a düzeltildi.
- red-team incelemesi `PublicVerifiedExperienceResponse`'a atdd.md'de tanımsız
  fazladan bir `visibility` alanı sızdığını buldu (sabit "PUBLIC" değeri,
  bilgi değeri yok) — kaldırıldı. Aynı turda `VerifiedExperience` sorgusu
  merkezi `scoped_*()` desenine (`scoped_public_verified_experiences`)
  taşındı (önceden çıplak `session.query()` idi — IDOR riski yoktu ama
  proje kuralının harfine aykırıydı).

## YET-106 (PLAN 3.2) — Public doğrulama linki GET /public/v/{token} (2026-09-25)

**Kaynak:** `obss_project/artifacts/public-dogrulama-linki/`

### Bilinçli kararlar (kaynak: plan.md Kararlar, kullanıcı onayı)
- **`attestor_name` yerine `attestor_organization`** (`Organization.name`, `attestor_org_id` üzerinden) — `docs/API.md §2.9`'un örnek response'unda `attestor_name: "Mehmet K."` vardı ama gerçek şemada (`User` modeli) kişi adı için hiçbir alan yok, `Attestation`'da da attestor adını snapshot'layan bir kolon yok. Migration gerektiren daha büyük bir çözüm (User.display_name eklemek) yerine mevcut şemadan üretilebilen kurum adı tercih edildi.
- **`verified_experiences.public_token` migration'ı** (nullable, String, UNIQUE + index) — `docs/DATABASE.md` bu kolonu zaten dokümante etmişti ama gerçek kodda yoktu. `alembic upgrade head` → `downgrade -1` → `upgrade head` ile doğrulandı.
- **Token üretimi entegre edilmedi** — `generate_public_token()` (`secrets.token_urlsafe(32)`) yazıldı ama T8 attestation transition'a bağlanmadı; bu görevin kapsamı sadece doğrulama ucu, üretim akışı ayrı bir görev.

### Kabul edilen riskler (kaynak: atdd.md Risks)
- Rate limit yok — `docs/SECURITY.md`'nin kendi açık sorusu (final analizde karar verilmemiş), token'ın yüksek entropisi riski kısmen azaltıyor ama tam telafi etmiyor.
- **F5/410 (iptal edilmiş doğrulama linki) mekanizması bu görevde uygulanmadı** — DB'de "revoke" durumunu temsil edecek hiçbir kolon yok (`docs/AUTHORIZATION.md`'nin F5 satırı doğru bir gelecek-durum sözleşmesi ama şu an gerçekleştirilemez). Sessizce atlanmadı, atdd.md'nin Kapsam Dışı/Unknowns bölümüne kayıtlı.
- `public_token` backfill'i yapılmadı — mevcut (migration öncesi) `VerifiedExperience` kayıtları için doğrulama linki üretilmeyecek, sadece yeni kayıtlar (token üretimi entegre edildiğinde) token alacak.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- **`atdd.md`'nin kendi hatası (YET-105'ten farklı bir örnek):** İlk yazımda `docs/API.md`'nin örnek response'undaki `attestor_name` alanının gerçek şemada hiç kaynağı olmadığı fark edilmemişti — `plan` adımındaki kod keşfinde ortaya çıktı, kullanıcı onayıyla `attestor_organization`'a çevrildi.
- test-copilot'un ilk teslimi 4 ayrı fixture bug'ı içeriyordu: (1) `Skill` fixture'ı zorunlu `slug` alanını vermiyordu (`NotNullViolation`, 14 test ERROR), (2) aynı `(engagement_id, attestor_user_id, subject_type)` ile 2 `Attestation` oluşturulmaya çalışılmış (`UNIQUE` ihlali), (3) bir fixture `org_verification`'ı kullanıyor ama parametre listesine eklenmemiş (`AttributeError`), (4) bir test yanlış alan adı (`role_snapshot`, response'ta `title`) arıyordu VE `or` ile gevşetilmişti (proje kuralı ihlali) — hepsi ayrı turlarda düzeltildi.
- red-team incelemesi 2 medium bulgu buldu: `Attestation` sorgusu `scoped_*()` deseninde değildi (YET-105'teki aynı desen, `scoped_attestations_for_engagement()`'e taşındı) ve `PublicVerificationResponse.started_on: date` (non-nullable) modeldeki `date | None` ile uyuşmuyordu (gerçek NULL veride yakalanmamış `ValidationError`/500 riski — `date | None`'a düzeltildi, testte hiç tetiklenmemişti ama gerçek bug riskiydi).

## YET-105 (PLAN 3.1) — Public profil ucu + visibility kuralları (2026-09-25)

**Kaynak:** `obss_project/artifacts/engagement-durum-makinesi-transitions-ucu/`

### Bilinçli kararlar (kaynak: atdd.md Assumptions, plan.md)
- Kapsam T1/T2/T3/T6 ile sınırlandı (kullanıcı onayıyla) — T4 (koordinatörsüz
  DRAFT→ACTIVE) STATE_MACHINE.md'nin kendi açık sorusu, MVP'de gerçeklenmiyor;
  T5/T7/T8/T9/T10 Deliverable/Evaluation/VerifiedExperience/Attestation
  henüz yok (PLAN 2.4, 2.7, 2.8, 2.9).
- T1'in `institution_id` ön koşulu: transition isteğine `institution_id`
  eklenmiyor (API.md şeması bunu içermiyor) — engagement zaten oluşturma
  sırasında `institution_id` dolu olmalı, NULL ise T1 hiç yapılamaz (bir
  kilitlenme değil, T4'ün kasıtlı olarak kapsam dışı bırakılmasının doğal
  sonucu).
- Optimistic locking için ORM `session.add()+flush()` deseni YERİNE ham
  `UPDATE ... WHERE status=... AND version=...` + `rowcount` kontrolü
  kullanıldı (plan.md'de kod keşfinde bulunan risk: ORM deseni race
  condition'a karşı korumasız).

### Kabul edilen riskler (kaynak: atdd.md Risks)
- Rate limiting yok — diğer uçlarla tutarlı, MVP kapsamı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- test-copilot'un ilk teslimi var olmayan bir model (`InstitutionCoordinator`)
  import etmişti — `ImportError` ile tüm test dosyasını kırıyordu. Gerçek
  model `InstitutionMember(role="COORDINATOR")` ile değiştirildi.
- code-copilot'un ilk teslimi 2 gerçek hata içeriyordu: response şemasında
  `updated_at` alanı eksikti; `transition_table` dict'i (karışık tipli
  değerler: list + callable) mypy'de "object not iterable/callable" hatası
  veriyordu — `TransitionSpec` TypedDict ile düzeltildi.
- Test dosyasında 6 fixture hatası bulundu: 5 test fonksiyonu üyelik satırı
  olmayan `User`-only fixture'ları (`user_inst_coord_diana`/
  `user_org_admin_evan`) istiyordu, gerçek üyelik satırını oluşturan
  (`inst_coord_diana`/`org_admin_evan`) fixture'ları HİÇ istemiyordu — bu
  yüzden principal.kind "COORDINATOR"/"ORG_ADMIN" yerine "USER" oluyor,
  testler 404 alıyordu. 1 testte de yanlış kullanıcı-engagement eşleşmesi
  vardı. Düzeltildi.
- `red-team`, **kritik bir yetkilendirme genişlemesi** buldu: T2/T3/T6
  kodunda `principal.kind in ("COORDINATOR", "INST_ADMIN")` kontrolü vardı
  — atdd.md'nin persona tanımı INST_ADMIN'i hiç T2/T3 aktörü olarak
  saymıyordu, üstelik yanlış scope listesiyle kontrol ediliyordu
  (`institution_ids` — genel ilişki listesi — yerine `institution_admin_ids`
  olmalıydı, `can()`'daki admin_update deseniyle tutarsızdı). INST_ADMIN
  T2/T3/T6'dan tamamen kaldırıldı.
- `red-team`, T3/T6'nın zorunlu `reason` alanının hiçbir yerde kalıcı
  saklanmadığını buldu (ne engagement satırında bir kolon vardı, ne
  audit/outbox'a bilinçli olarak konuluyordu) — kullanıcı onayıyla yeni bir
  migration (`engagements.reason`) eklenip T3/T6 başarılı olduğunda kalıcı
  yazılması sağlandı (AC-15 olarak atdd.md'ye eklendi).

## YET-2.1 — Engagement modeli + migration + oluşturma ucu (2026-09-23)

**Kaynak:** `obss_project/artifacts/engagement-model-olusturma-ucu/`

### Bilinçli kararlar (kaynak: atdd.md Assumptions)
- `docs/AUTHORIZATION.md`'de açık kalan "POST /engagements — engagement'ı kim
  başlatabilir?" sorusu, kullanıcı onayıyla `STATE_MACHINE.md`/`API.md` lehine
  çözüldü: hem `ORG:MEMBER` hem `TALENT` oluşturabilir.
- `Engagement.kind` enum'u için `docs/DOMAIN.md` (4 değer: INTERNSHIP,
  CAPSTONE, SHORT_PROJECT, PART_TIME) esas alındı; `docs/DATABASE.md`'nin
  eski 3-değerli CHECK kısıtı (kullanıcı onayıyla) buna göre düzeltildi.

### Kabul edilen riskler (kaynak: atdd.md/plan.md Risks)
- `POST /engagements` için MVP'de rate limiting yok — 1.6'daki
  `/auth/forgot-password` kararıyla tutarlı, Faz 5.2/5.6'ya bırakıldı.
- `scoped_engagements()` bu görevle ilk kez yazıldı — `docs/AUTHORIZATION.md`
  §2'de tanımı vardı ama kod tarafında hiç yoktu.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- code-copilot'un ilk teslimi 3 gerçek hata içeriyordu: (1) `kind` alanı düz
  `str` idi, geçersiz değer Pydantic'i geçip yakalanmamış `IntegrityError`
  olarak sızıyordu (500, AC-2 kırığı) — `Literal[...]` ile düzeltildi;
  (2) asla çalışmayan bir `elif` dalı (ölü kod); (3) **kritik güvenlik
  açığı** — `principal.kind` TALENT/ORG_MEMBER/ORG_ADMIN dışındaysa (ör.
  "USER", "COORDINATOR") hiçbir sahiplik kontrolü uygulanmıyordu, herhangi
  bir authenticated kullanıcı herhangi bir organizasyon adına engagement
  açabiliyordu (default-allow, default-deny yerine). Fonksiyon başına
  default-deny kontrolü eklenerek kapatıldı.
- test-copilot'un yazdığı fixture'larda da 2 hata bulundu: `Organization`/
  `Institution` fixture'ları var olmayan model alanları (`slug`,
  `visibility`, `logo_url`, `website`) kullanıyordu; `user_org_member_charlie`
  fixture'ında gerçek bir `OrganizationMember` satırı eksikti, bu yüzden
  AC-S2 testi (Charlie'nin yetkisiz org'a erişememesi) yanlış senaryoyu test
  ediyordu — Charlie hiçbir org'a üye olmadığı için "USER" kind'ine düşüp
  yukarıdaki güvenlik açığını hiç fark etmiyordu.
- `red-team`, `scoped_engagements()`'in COORDINATOR/INST_ADMIN dalının hiç
  pozitif test edilmediğini (boş sonuç da testi geçiyordu) buldu — testlere
  gerçek seed veri + pozitif assertion eklenerek kapatıldı. Ayrıca UUID parse
  hatasının her zaman "Talent bulunamadı" mesajına düşmesi (organization_id/
  institution_id formatı bozuksa da) ve engagement.py'de gereksiz bir manuel
  `session.rollback()` (get_session zaten yapıyor, çift-rollback riski)
  bulundu — ikisi de düzeltildi.

## YET-14 — Frontend: talent profil + yetkinlik beyanı ekranı (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-14-talent-profil-yetkinlik/`

### Teknik karar gerekçeleri (kaynak: atdd.md/plan.md)
- Backend'de `/talents/me/skills` (GET/POST/DELETE) ve `/skills` uçları hem
  router hem DB şeması (talent-skill junction tablosu) hiç yoktu (YET-11,
  başka bir geliştiriciye atanmış, "Yapılacaklar"da) — YET-13'teki "sözleşme
  önce" deseniyle `docs/API.md`'ye göre mock ile ilerlendi.
- `/profil`, projenin `AppShell`'i ilk kez gerçek bir sayfada kullandığı yer
  oldu — YET-12'nin red-team'inin bıraktığı "AppShell hiçbir sayfada
  kullanılmıyor" bulgusunu kapattı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- code-copilot'un ilk yazdığı `skills-section.tsx`'te debounce `useEffect`'i
  bir state'i (`searchTimeout`) hem tutuyor hem dependency olarak kullanıyordu
  — `setSearchTimeout` her çağrıldığında effect'i tekrar tetikleyip sonsuz
  "temizle→kur→tetikle" döngüsü yaratıyordu; testler 120 saniyede bile
  bitmiyordu. `useRef`'e çevrilerek düzeltildi.
- Aynı implementasyon, planın öngördüğü `AppShell` sarmalayıcısını
  kullanmadan yazılmıştı (kendi loading/error mantığını yeniden icat etmiş)
  — mimari sapma fark edilip düzeltildi.
- `skills-section.tsx` `useQuery` kullanıyordu ama testler
  `QueryClientProvider` sağlamıyordu — `useQuery` senkron hata fırlatıp bir
  "optional" fallback sessizce boş veri dönüyordu, `getMySkills`/`addSkill`/
  `removeSkill` gerçekte HİÇ çağrılmıyordu. İlk turda düz `useState`+
  `useEffect`'e geçilerek "çözüldü" ama bu `.claude/rules/frontend.md`'nin
  "Sunucu durumu: TanStack Query, tartışma yok" kuralını ihlal ediyordu —
  `red-team` bunu bulup `block` verdi, doğru çözüm (testlere gerçek
  `QueryClientProvider` sarmalayıcısı eklemek) ikinci bir turda uygulandı.
- `red-team`, iki gerçek backend sözleşme uyumsuzluğu buldu (kodun kendisi,
  atdd.md'nin "kabul edilmiş risk" dediği backend-henüz-yok durumundan
  AYRI bir hata): (1) `claimed_level` seçenekleri `PROFICIENT`/`EXPERT`
  kullanıyordu, gerçek DB `CHECK` kısıtı (`docs/DATABASE.md`)
  `BEGINNER`/`INTERMEDIATE`/`ADVANCED`; (2) `GET /talents/me/skills`
  cevabı `docs/API.md`'ye göre `items[].skill.{id,name_tr}` (iç içe) +
  kardeş `claimed_level` dönerken, implementasyon `items[].id` gibi düz
  bir şekil okuyordu. İkisi de testler AYNI yanlış varsayımı mock'ladığı
  için 613 yeşil testin hiçbirinde yakalanmamıştı — orkestratör dosyaları
  bizzat okuyarak doğruladı, düzeltildi.
- Test-fix turlarında art arda 3 küçük test-izolasyon/senkron sorunu
  çıktı (çift `useSession()` çağrısının tek seferlik mock'la çakışması,
  bölünmüş text node'ların `getByText` ile bulunamaması, bir testin kendi
  debounce timer'ını bekletmeden bitip bir sonraki testin mock kuyruğunu
  erken tüketmesi) — her biri tek başına test edilip kök nedeni izole
  edilerek düzeltildi.

## YET-13 — Frontend: kayıt, giriş, e-posta doğrulama, şifre sıfırlama (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-13-auth-ekranlari/`

### Teknik karar gerekçeleri (kaynak: plan.md "Açık Sorular")
- `.claude/rules/frontend.md`in öngördüğü React Hook Form + Zod + shadcn/ui
  o ana kadar hiç kullanılmamıştı (proje düz `useState`/native form ile
  gitmişti) — kullanıcı onayıyla kurala uyuldu, 3 yeni bağımlılık eklendi.
- `should-redirect.ts`'in `isPublicRoute` allowlist'ine 4 yeni route
  eklenmesi (auth mantığı değişikliği) ayrıca kullanıcı onayına sunuldu.
- Backend'de `/auth/verify-email`, `/auth/forgot-password`,
  `/auth/reset-password` uçları henüz yoktu (yalnız register/login şeması
  vardı, grep ile doğrulandı) — Jira'nın kendi bağımlılık notu
  ("backend'in bitmesini beklemeden mock ile ilerlenir") gereği frontend
  docs/API.md sözleşmesine göre yazıldı, testler `apiFetch`'i mock'ladı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- Test-copilot'un yazdığı bir test dosyasında ("New auth functions" describe
  bloğu) yanlışlıkla dış `describe` bloğunun dışında kalmış, `beforeEach`
  mock'unu miras almıyordu — 14 test `fetchMock.mockResolvedValueOnce is
  not a function` ile başarısız oluyordu, kendi `beforeEach`/`afterEach`'i
  eklenerek düzeltildi.
- code-copilot'un yazdığı `client.ts`, `register`/`login`/`resetPassword`
  için object-parametre kullanmıştı, testler (bağımsız yazılmış) positional
  parametre bekliyordu — testler doğru referans alınarak `client.ts`
  düzeltildi.
- `red-team`, `giris/form.tsx`'te `next` query param'ının
  `sanitizeNext()`'ten hiç geçmeden `router.push`'a verildiğini (open
  redirect, AC-S5 ihlali) ve varsayılan yönlendirme hedefinin plan.md'nin
  kararına (`/`) aykırı, var olmayan `/panel` rotasına sabitlendiğini
  (404 riski) buldu — ikisi de düzeltildi, ardından kullanıcı isteğiyle 4
  adversarial entegrasyon testi (`//evil.com`, `https://evil.com`,
  `javascript:`, backslash bypass) eklenerek uçtan uca kanıtlandı.
- `kayit/form.tsx`'te kayıt başarı mesajının senkron `router.push` yüzünden
  gerçek tarayıcıda hiç görünmediği (test'te `useRouter` mock'landığı için
  fark edilmemişti) bulundu — kısa bir gecikmeyle düzeltildi.

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

## YET-7 — User + Talent profili: GET /me, PATCH /talents/me (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-7-user-talent-profili/`

### Kabul edilen riskler / teknik karar gerekçeleri (kaynak: atdd.md, plan.md "Kararlar")
- DOMAIN.md'nin eski "is_public = true ise public_slug zorunlu" ifadesi
  yerine gerçek şemadaki `visibility=PUBLIC ise public_slug zorunlu`
  varsayımı kullanıldı (DOMAIN.md güncel değil, ayrı bir dokümantasyon
  görevi gerektirir).
- **Kod keşfinde bulunan gerçek mimari boşluk:** `scoped_talent_profiles()`
  yalnızca `principal.kind == "TALENT"` ise çalışıyordu — aynı zamanda
  kurum/organizasyon admin'i olan bir kullanıcı (kind en yüksek rolü
  gösterdiği için) kendi talent profiline PATCH atayamıyordu. Koşul
  `principal.talent_id is not None` olarak düzeltildi (AC-8) — bu bir
  yetkilendirme mantığı değişikliğiydi, kullanıcı onayı alındı.
- **Kod keşfinde bulunan dokümantasyon-kod tutarsızlığı:** `docs/API.md`
  §1.4'ün belgelediği hata sözleşmesine (`{code, message, request_id}`)
  mevcut YET-8/YET-9 kodu hiç uymuyordu (düz string `detail` kullanıyorlardı,
  gerçek yanıtta `code` hep `"HTTP_ERROR"` oluyordu). YET-7 doğru/dokümante
  edilen sözleşmeyi kullanacak şekilde bilinçli olarak yazıldı — geçmiş
  tutarsızlık ayrı bir borç olarak `postmortem`'e not düşüldü.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- Bir Haiku alt-ajanı, prompt'ta hiç istenmemişken repo kökünde yetkisiz bir
  `.env` dosyası oluşturdu — `.gitignore`'da olduğu doğrulandı (hiç commit
  riski yoktu), kullanıcı tarafından silindi. Orkestratörün kendisi de
  harness'ın deny-rule'u yüzünden bu dosyayı silemedi (güvenlik ağı olarak
  çalıştı). (Süreç ihlali, kayıt: `code_diff.md`.)
- İlk implementasyon `get_me_context()` içinde çıplak `select(Model)`
  kullanıyordu (CLAUDE.md "merkezi yetkilendirme zorunlu" kuralı ihlali) —
  ikinci bir dispatch ile mevcut `scoped_organizations()`/`scoped_institutions()`/
  `scoped_talent_profiles()` fonksiyonlarını kullanacak şekilde düzeltildi.
- `verify` adımında, test-copilot ile code-copilot'un PATCH /talents/me
  yanıt şeklini (sarmalı `{"talent_profile":{...}}` vs düz obje) birbirini
  görmeden farklı varsaydığı bulundu — API.md'nin gerçek sözleşmesine göre
  (düz obje) testler düzeltildi.
- `red-team` incelemesinde `get_me_context()`'in register-invaryantına
  (her User'ın bir TalentProfile'ı olması) savunmasız güvendiği bulundu —
  `None` ise `404 TALENT_PROFILE_NOT_FOUND` döndürecek bir kontrol eklendi.

## YET-11 — Talent yetkinlik beyanı: skill ekle/listele/çıkar (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-11-skill-claims/`

### Kabul edilen riskler / teknik karar gerekçeleri (kaynak: atdd.md, plan.md "Kararlar")
- **DOMAIN.md §3.6 ile DATABASE.md §2.2 arasında şema tutarsızlığı** bulundu:
  DOMAIN.md `self_level`/`note`/`deleted_at` (soft-delete) tanımlıyor,
  DATABASE.md `claimed_level`/`source`/`confirmed_by_user_at` (hard-delete)
  tanımlıyor. CLAUDE.md kuralı gereği ("şema esastır") DATABASE.md esas
  alındı — DOMAIN.md güncel değil, ayrı bir dokümantasyon senkronizasyon
  görevi gerektirir.
- **YET-10'un iddia ettiği kapsam kod tabanında bulunamadı** — Jira'da
  "Tamamlandı" işaretli ama skill arama ucu/seed script'i yok, yalnız
  `Skill` tablosu var. YET-11'i bloke etmedi (skill_id doğrudan
  kullanıldı) ama Jira durumu şüpheli.
- MERGED/DEPRECATED skill'e claim denemesi `404 SKILL_NOT_FOUND` ile
  reddedildi (ayrı kod icat edilmedi, `merged_into_id`'ye otomatik
  yönlendirme yapılmadı — kullanıcı iradesi dışında farklı bir skill'e
  claim atmak MVP kapsamını genişletir).

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- Docker Desktop bu görev sırasında kapanmıştı — ilk Haiku alt-ajanı bu
  yüzden migration/testleri çalıştıramadığını raporladı, orkestratör bunu
  bağımsız `docker ps`/`docker info` ile doğruladı (gerçek bir ortam
  sorunuydu), kullanıcıdan Docker'ı yeniden başlatmasını istedi ve devam
  etti.
- Kod incelemesinde iki gerçek implementasyon hatası bulundu: `POST`/`GET
  /talents/me/skills` uçları `principal.talent_id is None` durumunu kontrol
  etmiyordu — biri `IntegrityError` (500) ile, diğeri "boş liste ↔ yetkisiz
  erişim" karışmasıyla sonuçlanıyordu (AC-S1 ihlali). Her ikisine de
  `me.py`'deki `TALENT_PROFILE_NOT_FOUND` koduyla tutarlı bir kontrol
  eklendi.
- Bir test assertion hatası bulundu: `claimed_level` gönderilmeden yapılan
  bir istekte testin `is not None` beklemesi yanlıştı (alan nullable,
  gönderilmediyse `None` doğru davranış) — düzeltildi.
- `red-team` incelemesinde `add_skill_claim()`'in check-then-insert
  deseninde eşzamanlı çift `POST`'ta DB `IntegrityError`'ının
  yakalanmadığı (500 yerine 409 dönmesi gerekirken) bulundu — `flush()`
  artık `try/except IntegrityError` ile sarılı, mevcut
  `SkillAlreadyClaimedError`'a çevriliyor.

## YET-10 — Skill taksonomisi seed + arama ucu (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-10-skill-search/`

### Bağlam (kaynak: atdd.md)
YET-10 Jira'da "Tamamlandı" işaretliydi ama kod tabanında hiçbir `GET
/skills` ucu/seed script'i bulunamadı — YET-14'ün (frontend, zaten merge
edilmiş) `GET /skills?q=...` çağırdığı ama var olmayan bir ucu çağırdığı
somut olarak doğrulandı (testler `listSkills`'i mock'ladığı için hiç
yakalanmamıştı). Bu görev o boşluğu kapattı.

### Kabul edilen riskler / teknik karar gerekçeleri (kaynak: atdd.md, plan.md "Kararlar")
- **MVP'de tam "~150" skill yerine ~36 temsili skill** (her kategoriden
  6-8 örnek) — hackathon süresi için tam listeyi elle yazmak orantısız,
  "~150" yaklaşık bir hedef.
- **`search_skills()` scoped_*() paterni dışında** — `Skill` platform-geneli
  bir kaynak (kiracıya özel değil), merkezi tek bir servis fonksiyonu
  üzerinden filtreli sorgu kullanıldı; bu, CLAUDE.md'nin "çıplak select()
  yasak" kuralının amacını (dağınık/denetimsiz erişim) ihlal etmiyor.
  Kullanıcı yetkisiyle (Sonnet 5 low alt-ajanı aracılığıyla) onaylandı.
- Kimliksiz istek → `401` (404 değil) — bu bir kiracı-izolasyon kaynağı
  değil, genel kimlik doğrulama gereksinimi.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- **Orkestratör kaynaklı yan etki:** Seed script'inin gerçekten çalıştığını
  doğrulamak için bizzat çalıştırıldı — bu paylaşılan dev DB'ye 36 gerçek
  satır ekledi, test fixture'ları aynı slug'larla çakışıp 32 test hatasına
  yol açtı (implementasyon hatası değil, doğrulama adımının kendisiydi).
  `DELETE FROM skills WHERE slug IN (...)` ile temizlendi. **Ders: seed
  script'i gerçek DB'ye karşı doğrulanırken, sonradan eklenen veri mutlaka
  temizlenmeli.**
- `red-team` incelemesinde `search_skills()`'in `q` parametresini ILIKE
  deseni içine `%`/`_` escape etmeden gömdüğü bulundu — güvenlik açığı
  değil (parametreli sorgu, injection riski yok) ama kullanıcı aramada bu
  karakterleri kullanırsa yanlış/geniş sonuç alıyordu. Escape eklenerek
  düzeltildi.
- `red-team`'in "scoped_*() istisnasının onaysız olduğu" iddiası
  orkestratör tarafından **yanlış** bulundu — `plan.md`'de gerçek kullanıcı
  yetkisiyle zaten onaylanmıştı, kapatıldı (subagent'ların bazen kendi
  bağlamlarında eksik bilgiyle yanlış bulgu üretebileceğine dair bir örnek).
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

## YET-65 — [PLAN 2.3] Koordinatör onayı geçişi + yetkilendirme testleri (2026-09-23)

**Kaynak:** `obss_project/artifacts/koordinator-onay-gecisi-yetkilendirme-testleri/`

### Bağlam (kaynak: atdd.md)
İmplementasyon (`transition_engagement`, `scoped_engagements`) PLAN 2.2'de
zaten doğru yazılmıştı — bu görev klasik red→green değil, docs/AUTHORIZATION.md
§5.1 A5 ve §5.5 E1-E6'nın COORDINATOR/ORG_ADMIN çapraz-kurum/çapraz-org
senaryolarını HTTP-uç seviyesinde kapatan bir test-tamamlama göreviydi
(`tests/authorization/test_matrix.py`'deki YET-7 pending placeholder'ları).

### Review sürecinde bulunan ve düzeltilen gerçek sorun (kaynak: code_diff.md, red_team.json)
- **`red-team` incelemesi ilk turda medium-severity bir test-gap buldu:**
  `TestOrgAdminScopeVsAdminMismatch` testindeki `evan_member_of_org_b`
  fixture'ı `org_admin_evan` (organization_a'daki ADMIN üyeliği) fixture'ını
  zincire dahil etmiyordu — sonuçta Evan'ın principal.kind'ı `ORG_MEMBER`
  çıkıyordu (`ORG_ADMIN` değil), test 403 sonucunu doğru ama **yanlış kod
  yolundan** (basit "üye zaten yetkisiz" reddi) kanıtlıyordu; asıl hedeflenen
  `org_ids⊃org_admin_ids` (aynı principal bir kurumda admin, başka kurumda
  sade üye) senaryosu hiç tetiklenmiyordu. Fixture zincirine `org_admin_evan`
  bağımlılığı eklenerek düzeltildi, kod okumasıyla (principal.kind artık
  gerçekten `ORG_ADMIN`) teyit edildi, testler tekrar yeşil geçti.
  **Ders:** "kaynak görünür ama eylem yasak → 403" testleri yazarken,
  principal'ın GERÇEKTEN doğru `kind`'a düştüğünü (sadece sonuç kodunu değil,
  hangi yetki dalının tetiklendiğini) fixture seviyesinde doğrulamak gerekir
  — aksi halde test yanlış nedenle yeşil kalıp gerçek bir regresyonu (ör.
  `org_admin_ids` yerine yanlışlıkla `org_ids` kullanılması) yakalamaz.

### Kabul edilen riskler (kaynak: atdd.md Risks)
- MCP_DOCKER (Saga sunucusu) bu görev boyunca bağlı kalmadı — `saga_task_id`
  `null` bırakıldı, Saga senkronizasyonu bağlantı düzeldiğinde manuel yapılmalı.
- `POST /engagements/{id}/transitions` ucuna özel rate limit yok — düşük
  hacimli iç-kullanıcı ucu olduğu için kabul edilen risk, ayrı görev gerektirir.
- `AC-S6` (authz-test skill ile tam parametrik IDOR matrisi, YET-77'nin
  istediği) bu pipeline turunda tetiklenmedi — `verify_report.md`'de PENDING
  olarak not edildi, ayrı bir adımda ele alınabilir.

## YET-66 — [PLAN 2.4] Task + Deliverable (2026-09-23)

**Kaynak:** `obss_project/artifacts/engagement-task-deliverable/`

### Bilinçli kararlar (kaynak: atdd.md Assumptions/Kapsam Dışı, plan.md Migration Required)
- `Deliverable.evidence_ids[]` bağlantısı ve `Evidence` modeli bu görevde
  KURULMADI — Evidence backend'de henüz yok (PLAN 2.5/2.6), D11 kuralı
  ("en az 1 Evidence bağlı olmalı") 2.6'da eklenecek.
- `task_skills` (n-n) tablosu bu görevde HİÇ oluşturulmadı — Jira alt görev
  açıklamalarında iş mantığı geçmiyordu, spekülatif şema CAVEMAN ilkesine
  aykırı; ihtiyaç doğduğunda ayrı bir migration'da eklenecek.
- `EngagementTask.status` değer kümesi `PLANNED/IN_PROGRESS/DONE` olarak
  netleştirildi — `docs/DOMAIN.md` §3.8'de önceden `TODO/IN_PROGRESS/DONE`
  yazıyordu (Jira/PLAN.md ile tutarsızdı), bu görevde doküman güncellendi.
- Migration için kullanıcıdan açık onay alındı (CLAUDE.md kuralı) —
  `engagement_tasks`/`deliverables` tabloları, `task_skills` YOK.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- **AC-S5 test tasarım hatası (kod değil, test):** İki test "eksik zorunlu
  alan (`title`) → scope-check önce çalışır, 404 döner" senaryosunu
  kanıtlamaya çalışıyordu, ama FastAPI/Pydantic zorunlu bir alanı
  (`min_length=1`) route handler'ı hiç çalıştırmadan framework seviyesinde
  422 ile reddediyor — bu senaryo eksik-alan durumunda teknik olarak test
  EDİLEMEZ. Kullanıcı onayıyla payload "geçerli ama çapraz-tenant" bir
  title'a çevrildi. **Ders:** "scope-check validation'dan önce çalışsın" AC'leri
  yalnız handler-içi semantik kontrollerle (geçersiz enum string'i gibi,
  YET-65'teki `to_status=FOOBAR` deseni) anlamlı — framework-seviyeli zorunlu-alan
  422'leriyle değil. `red-team` incelemesi ayrıca bu testlerin artık AC-3/AC-4
  ile fonksiyonel olarak örtüştüğünü (gerçek bir sıra-regresyonunu
  yakalayamayacağını) buldu — kabul edilen risk olarak bırakıldı, isteğe
  bağlı bir takip görevinde docstring/isim netleştirilebilir.
- **Naive `datetime.now()` (kod bulgusu):** `create_deliverable()`'daki
  `submitted_at=datetime.now()` saf yerel saat kullanıyordu —
  `.claude/rules/database.md`'nin "timestamptz, UTC, yerel saat varsayımı
  yasak" kuralını ihlal ediyordu, mevcut `TimestampMixin` deseniyle
  (`func.now()`, DB-side UTC-aware) tutarsızdı. `datetime.now(timezone.utc)`
  ile düzeltildi.
- **`red-team`'in bulduğu kabul edilen düşük riskler:** (1) status (ACTIVE)
  kontrolü rol kontrolünden önce çalışıyor — yanlış rollü ama scope-içi bir
  kullanıcıya engagement'ın ACTIVE olmadığı bilgisi (422) sızabiliyor, 403
  daha erken dönebilirdi (düşük önem, status başka uçlardan da görülebiliyor).
  (2) `create_deliverable()`'daki `IntegrityError` yakalaması engagement_id
  ve submitted_by_user_id FK ihlallerini aynı `EngagementNotFoundError`
  altında topluyor — pratikte tetiklenemez (users hard-delete edilmiyor,
  anonimleştiriliyor), sadece okunabilirlik notu.

## YET-84/YET-85 — Evidence kaydı + indirme izni (2026-09-23)

**Kaynak:** `obss_project/artifacts/yet-84-85-evidence-kaydi-indirme/`

### Kapsam kararı — deliverable_id tamamen çıkarıldı (kaynak: plan.md)
`plan` adımının kod keşfinde kritik bir bulgu çıktı: atdd.md'nin orijinal
AC-4'ü ("deliverable_id başka talent'e aitse 404") `deliverables`/
`engagements` tablolarına dayanıyordu, ama bu tablolar/modeller kod
tabanında henüz yoktu (PLAN 2.1–2.4 tamamlanmamış). Kullanıcıya soruldu —
`deliverable_id` alanı bu görevden tamamen çıkarıldı: migration'da kolon
yok, `POST /evidence` body'sinde kabul edilmiyor, AC-4 atdd.md'den silindi.
PLAN 2.4 tamamlandığında ayrı bir migration + endpoint güncellemesiyle
eklenecek.

### Mimari çelişki — AC-13 gerçek davranışa uyduruldu (kaynak: code_diff.md)
Orijinal AC-13 "askıya alınmış kullanıcı → 403 ACCOUNT_SUSPENDED" diyordu.
`code-copilot` sonrası gerçek `pytest` çalıştırmasında bulundu: mevcut auth
katmanı (`app/core/deps.py:get_current_user`, PLAN 1.x'ten beri projede
tutarlı) SUSPENDED kullanıcıyı zaten `401 UNAUTHENTICATED` ile reddediyor —
servis/endpoint katmanındaki `403 ACCOUNT_SUSPENDED` kontrolüne hiçbir zaman
ulaşılamıyordu (ölü kod). Kullanıcıya soruldu, "atdd.md'yi gerçeğe uydur"
seçildi — AC-13 401'e güncellendi, ölü kontroller kaldırıldı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- `code-copilot`'un ilk turunda `get_download_url()`'un admin-403 dalı
  çıplak `session.query(Evidence).filter_by(...)` kullanıyordu (CLAUDE.md
  "çıplak select yasak" ihlali) — `select()`+`session.execute()` ile
  düzeltildi.
- Aynı turda, `GET /evidence/{id}/download-url` endpoint'i
  `principal.talent_id is None` kontrolünü admin için istisnasız
  uyguluyordu — admin (tipik olarak `talent_id=None`) servis katmanına hiç
  ulaşamıyor, AC-S3'ün 403 FORBIDDEN dalı asla tetiklenemiyordu (ölü kod).
  `... and not principal.is_platform_admin` ile düzeltildi.
- `create_evidence()`'ta `kind` allowlist ön-kontrolü eksikti — geçersiz bir
  `kind` DB CHECK constraint'e kadar gidip ham `IntegrityError` sızdırıyordu
  (AC-8 ve AC-S4 ihlali). Servis katmanına `ALLOWED_EVIDENCE_KINDS`
  ön-kontrolü eklendi (bu, `verify` adımının gerçek `pytest` koşumunda,
  test-copilot'un yazdığı `create_evidence()`'ı doğrudan çağıran bir testle
  ortaya çıktı — HTTP katmanındaki Pydantic validasyonu servis fonksiyonu
  doğrudan çağrıldığında koruma sağlamıyordu).
- `test-copilot`'un ilk turunda yazılan testler `pytest.skip(...,
  allow_module_level=True)` ile implementasyon eksikken SKIP oluyordu
  (FAIL değil) — `.claude/rules/testing.md`'nin açıkça yasakladığı bir
  kalıp, red-step'i geçersiz kılıyordu. Kaldırılıp gerçek collection error
  (FAIL) davranışına çevrildi.
- Aynı testlerde 4 kategori gerçek test hatası bulundu (`verify`'da gerçek
  `pytest` koşumuyla): yanlış import (`app.core.security` yerine
  `app.core.errors` olmalıydı), `ApiError.error_code` diye olmayan bir
  attribute'a erişim (doğrusu `ApiError.detail["code"]`), `scan_status`'un
  ayrı bir JSON alanı olduğunu varsayan yanlış assertion (proje sabit
  `{code, message, request_id}` hata şeması kullanıyor, alan mesaj metnine
  gömülü), ve append-only `audit_events` tablosuna `DELETE` deneme (trigger
  tarafından reddediliyordu, test izolasyonu `subject_id` filtresine
  çevrildi).
- `red-team` incelemesinde iki docstring'in (`services/evidence.py`,
  `api/evidence.py`) AC-13 düzeltmesinden sonra güncel kalmadığı bulundu
  (hâlâ eski 403 davranışını anlatıyordu) — düzeltildi. Üçüncü bulgu
  (`Principal.is_suspended` artık projede hiç okunmuyor, ölü alan) bilinçli
  olarak atlandı — bu görevin scope'unu aşıyor, `authorization.py`'nin
  genelini etkiliyor, ayrı bir görevde değerlendirilmeli.

### Kabul edilen riskler (kaynak: atdd.md)
- `storage_key` üzerinde idempotency/UNIQUE constraint yok — aynı key'e
  iki kez `POST /evidence` çağrılırsa iki ayrı evidence satırı oluşur.
  MVP'de kabul edilen basitlik tercihi.
- `size_bytes`/`mime_type` alanlarının MinIO'daki gerçek dosyayla
  tutarlılığı bu API ucunda doğrulanmıyor (worker aşamasına bırakıldı).
## YET-104 — SkillSignal: SELF_CLAIM türetme + GET /talents/me/signals (2026-09-24)

**Kaynak:** `obss_project/artifacts/skillsignal-self-claim-uretimi/`

### Bilinçli kararlar (kaynak: atdd.md/plan.md)
- Bu görev, [PLAN 2.9] SkillSignal türetme'nin (YET-71, Meyrem'e atanmış,
  yalnız `source_type=ATTESTATION` kapsamlı) **bağımsız dilimi** — sadece
  `source_type=SELF_CLAIM`. `DELIVERABLE`/`TASK`/`EVALUATION`/`ATTESTATION`
  kaynakları bilinçli olarak kapsam dışı bırakıldı (task_skills bağlantısı
  yok, Meyrem'in 2.6/2.7/2.8 işine bağımlı).
- `superseded_by_id` bu turda hep `NULL` — tek kaynak SELF_CLAIM olduğu
  için supersede edilecek bir şey yok, gerçek mantık ATTESTATION geldiğinde
  eklenecek.
- Migration'a `.claude/rules/database.md`'nin "kritik" dediği
  `(talent_id, skill_id, occurred_at DESC)` bileşik index'i eklendi
  (append-only immutability trigger de `audit_events` deseninden kopyalandı).

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- **Sahte regresyon:** İlk `code-copilot` koşumunda 15 `test_outbox_*`
  testi kırmızı çıktı — kök neden kod DEĞİLDİ, bu oturumdaki daha önceki
  bir MANUEL sunucu doğrulamasından (gerçek `curl` ile kayıt/login/evidence-
  upload testi) kalan 1 satırlık `outbox` tablosu kirliliğiydi;
  `test_outbox_service.py` filtre olmadan `scalar_one_or_none()` sorgusu
  attığı için paylaşılan dev DB'deki fazladan satırla çakışıp
  `MultipleResultsFound` fırlatıyordu. Kirli veri temizlendi, tam paket
  tekrar koşuldu: 523 passed, 0 failed. **Ders:** bu projede `outbox`/auth
  testleri paylaşılan dev DB'ye karşı transaction-izole DEĞİL (engagement
  testlerinin aksine) — manuel canlı doğrulama (curl/uvicorn) sonrası test
  koşumundan önce DB'nin temizlendiğinden emin olunmalı.
- `red-team` (yanlış şemada döndü, elle doğru şemaya çevrildi — bkz.
  red_team.json `schema_note`) migration'da eksik bir kritik index buldu
  (`(talent_id, skill_id, occurred_at DESC)`, database.md kuralı) — eklendi,
  downgrade/upgrade tekrar doğrulandı.
- `mypy` tip uyumsuzluğu (servis ham `dict` döndürüyordu, Pydantic model
  bekleniyordu) ve test dosyalarında 3 lint hatası (kullanılmayan import/
  değişken) minimal dispatch'lerle düzeltildi.

## YET-70 — [PLAN 2.8] Attestation + VerifiedExperience üretimi (2026-09-24)

**Kaynak:** `obss_project/artifacts/yet-70-attestation-verified-experience-uretimi/`
(atdd.md, plan.md, code_diff.md, verify_report.md, red_team.json)

### Varsayımlar (atdd.md)
- §3.11'in "≥4 hafta VEYA ≥40 saat" açık sorusu: sadece **≥4 hafta**
  kullanıldı — `planned_hours` nullable olduğu için saat eşiği her zaman
  hesaplanamıyor, hackathon kapsamında deterministik tek kriter tercih
  edildi.
- Anti-abuse cooling period (yeni kurum ilk 30 gün COMPETENCE yapamaz) ve
  kurum tanıklık kotası bu görevde **uygulanmadı**, ayrı bir takip maddesi
  olarak bırakıldı.
- `downgrade_reasons` kod isimleri (API.md'nin açık bıraktığı liste) bu
  görevde ilk kez sabitlendi: `ENGAGEMENT_NOT_MUTUALLY_CONFIRMED`,
  `ENGAGEMENT_DURATION_BELOW_THRESHOLD`, `NO_DELIVERABLE`,
  `ATTESTOR_NOT_VERIFIED_SUPERVISOR`, `COORDINATOR_CONFIRMATION_MISSING`.

### Kararlar (plan.md, kullanıcı onaylı)
- **Deliverable-skill ilişkisi basitleştirildi:** `Deliverable` modelinde
  `skill_id` kolonu yok — §3.11 kriter 3 sadece "engagement'ta ≥1
  Deliverable var" olarak uygulandı (downgrade kodu `NO_DELIVERABLE`,
  `NO_DELIVERABLE_FOR_SKILL` değil).
- **Self-attestation CHECK:** `attestations` tablosuna `talent_id`
  denormalize edildi (Engagement.talent_id'den kopya), `CHECK(attestor_
  user_id != talent_id)` doğrudan bu tabloda tanımlandı — cross-table
  CHECK mümkün olmadığı için.
- **Kriter 4 (verify sırasında ortaya çıkan gerçek tasarım belirsizliği,
  kullanıcıya soruldu):** İlk implementasyon "attestor == engagement.
  supervisor_user_id" eşitliğini istiyordu, ama DOMAIN.md'de süpervizör
  (kurum tarafı) ile koordinatör (üniversite tarafı) ayrı roller — happy-
  path testinde INST:COORD olan Diana bu eşitliği hiç sağlayamıyordu,
  COMPETENCE asla verilemiyordu. **Karar:** MVP'de T8'i tetiklemeye zaten
  yetkili olan principal (COORDINATOR veya ORG_ADMIN) kriter 4'ü otomatik
  sağlamış sayılır; sadece organizasyonun T2+ doğrulanmış olması ayrıca
  kontrol edilir.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- **Kod eksikliği (code-copilot 1. tur):** `SkillSignal` oluşturma adımı
  (STATE_MACHINE.md §5 adım 3'ün zorunlu kıldığı) yorum satırına alınmış
  TODO olarak bırakılmıştı ("hangi skill'e bağlanacağı belirsiz" gerekçesiyle).
  Orkestratör tarafından `Read` ile tespit edildi (sub-agent'ın kendi özeti
  bunu sessizce "out-of-scope" diye sunmuştu). Düzeltme: `AttestationCreateRequest`'e
  API.md'nin zaten tanımladığı opsiyonel `skill_id` alanı eklendi, verilirse
  `SkillSignal` oluşturuluyor, verilmezse açık bir koşullu dalda (TODO değil)
  atlanıyor.
- **Migration bug:** İlk migration dosyasında `revision`/`down_revision`
  modül değişkenleri hiç tanımlanmamıştı (sadece docstring'de vardı) —
  `alembic upgrade head` dosyayı okuyamadı. Düzeltildi.
- **6 test bug'ı (implementasyon değil):** `Deliverable` fixture'ında
  zorunlu alan eksikliği (`submitted_by_user_id`/`submitted_at`), geçersiz
  `organization_members.role="SUPERVISOR"` (CHECK sadece ADMIN/MEMBER
  kabul ediyor), geçersiz `engagement.kind="FREELANCE"`, hata yanıtı
  unwrap deseni yanlış varsayılmış (proje konvansiyonu `data.get("detail")
  if "detail" in data else data` — bazı hata yanıtları `{"detail": ...}`
  sarmalı değil, düz dönüyor), AC-8 testinin kabul edilebilir hata kodu
  listesi eksikti, ThreadPoolExecutor ile paylaşılan tek SQLAlchemy Session
  (thread-safe değil) kullanan bir race-condition testi sekansiyel
  senaryoya çevrildi.
- **Red-team: kritik yetkilendirme açığı (HIGH, block→fixed).**
  `create_attestation()` yalnız `TALENT` rolünü reddediyordu — STATE_MACHINE.md
  T8 satırının öngördüğü rol sınırlaması (institution_id NOT NULL → sadece
  COORDINATOR, NULL → sadece ORG_ADMIN) hiç uygulanmamıştı. `scoped_engagements()`
  sadece tenant izolasyonu sağlıyordu (yanlış kurum/organizasyonu engelliyordu),
  rol-uygunluğunu değil — aynı organizasyondaki sıradan bir `ORG_MEMBER`
  EVALUATED bir engagement'a COMPETENCE seviyesinde tanıklık üretip T8'i
  tetikleyebiliyordu. Düzeltme: `create_attestation()`'a institution_id'ye
  göre COORDINATOR/ORG_ADMIN rol kontrolü eklendi (uygun değilse 404, CLAUDE.md
  "yetkisiz erişimde 403 değil 404" kuralına uygun), 2 yeni negatif test
  eklendi. **Ders:** `scoped_engagements()`'in tenant izolasyonu sağlaması,
  rol-uygunluğunu da sağladığı anlamına gelmiyor — ikisi ayrı kontrol
  katmanları, yeni bir state-transition ucu yazarken ikisi de ayrı ayrı
  doğrulanmalı.

## YET-71 — [PLAN 2.9] SkillSignal türetme tam kapsam (2026-09-24)

**Kaynak:** `obss_project/artifacts/yet-71-skillsignal-turetme-tam-kapsam/`
(atdd.md, plan.md, code_diff.md, verify_report.md, red_team.json)

### Kararlar (kullanıcı onaylı)
- Jira'nın YET-91/92 başlıkları ("ATTESTATION SkillSignal", "GET ucu") ESKİYDİ
  — ikisi de zaten önceki görevlerde (YET-70, YET-104) tamamlanmıştı. Kullanıcı
  bunları kapatmak yerine YET-71'in TAMAMININ yeniden doğrulanmasını istedi.
- `deliverables`/`engagement_tasks` tablolarına nullable `skill_id` FK ekleyen
  yeni bir migration + DELIVERABLE/TASK kaynaklı türetme de bu görevde eklendi
  (kullanıcı kararı — daha küçük bir kapsam da önerilmişti: sadece EVALUATION,
  DELIVERABLE/TASK ayrı göreve bırakılabilirdi).
- **Strength hiyerarşisi (DOMAIN.md §3.14'ün kendi açık bıraktığı soru, bu
  görevde ilk kez karara bağlandı):**
  `SELF_CLAIM→NONE < TASK→WEAK < DELIVERABLE→MODERATE < EVALUATION(BELOW/MEETS/
  EXCEEDS→WEAK/MODERATE/STRONG) ≈ ATTESTATION(PARTICIPATION/COMPETENCE→WEAK/
  STRONG)`. Gerekçe: TASK/DELIVERABLE kendi kendine raporlu/atanmış, üçüncü
  taraf doğrulaması yok — EVALUATION üçüncü taraftan puanlama (Attestation
  kadar resmi değil, SELF_CLAIM'den güçlü).
- TASK sinyali oluşturulduğu anda (status=PLANNED) üretilir, "tamamlandığında"
  değil — çünkü `EngagementTask` için bir durum-güncelleme (PATCH) ucu bu
  projede henüz yok.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- **Gerçek doğruluk hatası (isim çakışması):** `engagements.py`'de
  `app.services.engagement.InvalidSkillError` ve `app.services.evaluation.
  InvalidSkillError` aynı isimle import edilmişti — ikincisi birincisini
  Python'un name-rebinding'i yüzünden sessizce gölgeliyordu. TASK/DELIVERABLE
  route'larındaki `except InvalidSkillError:` blokları GERÇEKTE fırlatılan
  exception'ı yakalayamıyordu (AC-7 kırılırdı: 422 yerine 500 dönerdi). `ruff`'ın
  F811 uyarısıyla tespit edildi (`ruff check .` gate'i olmasaydı bu sessizce
  kaçabilirdi), alias'lama (`EngInvalidSkillError`/`EvalInvalidSkillError`) ile
  düzeltildi. **Ders:** iki farklı modülden aynı isimli exception import etmek
  Python'da sessizce derlenir ama ikinci import birinciyi gölgeler — `ruff`'ın
  F811 kuralı bu sınıfı otomatik yakalıyor, verify adımında lint'i asla atlama.
- **Migration bug (aynı sınıf, ikinci kez):** `down_revision` yanlış (eski,
  zaten merge edilmiş bir revizyona işaret ediyordu) yazılmıştı — code-copilot'un
  kendi raporundaki tutarsızlık ("son evaluation migration" derken gerçek head
  farklıydı) fark edilerek tespit edildi. `alembic heads` ile tek head
  doğrulandı.
- **Regresyon (bulunup düzeltildi):** AC-S1 (strength tampering) için
  `PostTaskRequest`/`PostDeliverableRequest`'e eklenen `extra="forbid"`,
  MEVCUT bir regresyon testini (AC-S3, `submitted_by_user_id` tampering)
  kırdı — o test bilinmeyen bir alanın sessizce yok sayılıp 201 dönmesini
  bekliyordu. `extra="forbid"` kaldırıldı: AC-S1'in gerçek güvenlik hedefi
  zaten korunuyordu çünkü `strength` şemada hiç tanımlı değildi (Pydantic
  varsayılanı böyle alanları zaten görmezden gelir). **Ders:** yeni bir
  threat-model AC'sini karşılamak için MEVCUT bir endpoint'in şemasına
  sıkılaştırıcı bir kısıt (`extra="forbid"`) eklemeden önce, o endpoint'in
  zaten var olan davranış sözleşmesini/testlerini kontrol et — attestation.py
  gibi YENİ bir endpoint'te sorun yaratmayan bir desen, MEVCUT bir endpoint'te
  regresyona yol açabilir.
- **Red-team bulgusu (medium, düzeltildi):** AC-7 "skills tablosunda yok/ACTIVE
  değil" diyordu ama skill_id doğrulaması sadece varlığı kontrol ediyordu,
  `Skill.status=="ACTIVE"` filtresi yoktu (3 yerde: TASK, DELIVERABLE,
  EVALUATION item) — MERGED/DEPRECATED bir skill_id ile sessizce geçerli bir
  SkillSignal üretilebilirdi. Düzeltildi.
- **3 küçük test bug'ı:** geçersiz skill `category="TECHNICAL"` (CHECK sadece
  LANGUAGE/FRAMEWORK/TOOL/DOMAIN/SOFT kabul ediyor), bir testin yanlış
  dosyadan (başka bir test dosyasının) fixture'larını referans etmesi ("fixture
  not found" — pytest fixture'ları dosyalar arası otomatik paylaşılmaz), ve
  hesaplanıp hiç assert edilmeyen bir `signal_count` değişkeni.

## YET-72 — [PLAN 2.10] Attestation iptali (revoke) (2026-09-24)

**Kaynak:** `obss_project/artifacts/yet-72-attestation-revoke/`
(atdd.md, plan.md, code_diff.md, verify_report.md, red_team.json)

### Mimari çelişki ve karar (kullanıcıya soruldu, atdd öncesi)
`skill_signals` tablosunda İSTİSNASIZ bir immutability trigger vardı (`BEFORE
UPDATE OR DELETE`, her zaman exception fırlatır) — ama DOMAIN.md D12
"Attestation geri çekilince ilgili SkillSignal `superseded` olur
(`superseded_by_id` set edilir)" diyordu. Bu, mevcut şemayla teknik olarak
İMKÂNSIZDI. **Karar:** yeni bir migration ile trigger'a `superseded_by_id`
için set-once bir istisna eklendi (`attestations.revoked_at`/`revoke_reason`
deseniyle aynı — CLAUDE.md'nin "tek istisna" listesine bu alan da eklenmiş
oldu, bilinçli bir genişletme).

Ayrıca `attestations` tablosunda o ana kadar HİÇ immutability trigger yoktu
(YET-70'te eklenmemişti, sadece CHECK constraint'ler vardı) — bu görev
`revoked_at`/`revoke_reason` istisnasıyla ilk kez ekledi.

### Tombstone SkillSignal deseni (varsayım, kullanıcı onaylı)
STATE_MACHINE.md/DOMAIN.md revoke'ta yeni bir SkillSignal oluşturulacağını
açıkça söylemiyordu, sadece "superseded olur" diyordu. Yorum: `strength=NONE`
ile bir "tombstone" SkillSignal oluşturulur, eski sinyal(ler) bu tombstone'a
`superseded_by_id` ile işaret eder — `superseded_by_id`'nin anlamlı olması
için gereken en tutarlı yorum.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- **Kritik güvenlik hatası (çıplak select + 403/404 bilgi sızıntısı):**
  İlk implementasyon `revoke_attestation()` içinde `select(Attestation)`
  çıplak kullanıyordu VE attestor OLMAYAN HERKESE (tamamen alakasız bir
  kurum/organizasyondan biri dahil) `403` dönüyordu — CLAUDE.md'nin
  "yetkisiz erişimde 404 dön, 403 değil (403 kaynağın varlığını sızdırır)"
  kuralını ve atdd.md'nin kendi AC-3'ünü ihlal ediyordu: bir attestation
  UUID'sini bilen HERKES, ona hiçbir ilişkisi olmasa bile, 403 alarak
  kaydın var olduğunu öğrenebiliyordu. Orkestratör tarafından code-copilot
  dispatch'inden hemen sonra, testleri çalıştırmadan ÖNCE kod okunarak
  tespit edildi. Düzeltme: attestation'ın engagement'ı önce
  `scoped_engagements()` ile kontrol ediliyor — scope dışıysa 404, scope
  içinde ama attestor değilse 403. **Ders:** "sadece attestor X yapabilir"
  gibi basit görünen bir yetki kuralı bile, kaynağın tenant/scope bağlamı
  düşünülmeden uygulanırsa BOLA'ya (bilgi sızıntısı) dönüşebilir — "kim
  yapabilir" ile "kim kaynağın var olduğunu bilebilir" ayrı sorulardır.
- **Routing bug:** `POST /attestations/{id}/revoke` route'u yanlışlıkla
  `prefix="/engagements"` olan router'a eklenmişti, gerçek path
  `/engagements/attestations/{id}/revoke` oluyordu — API.md sözleşmesiyle
  uyuşmuyordu. plan.md bu riski zaten öngörmüştü ("mevcut router prefix
  kullanıyorsa yeni bir APIRouter gerekebilir") ama code-copilot bunu
  atladı. Ayrı bir `attestations_router` (`prefix="/attestations"`)
  oluşturulup `main.py`'de kaydedildi. **Ders:** plan.md'nin "dikkat et"
  notları code-copilot'a dispatch prompt'unda AÇIKÇA tekrar edilmeli,
  sadece dosyayı okumasına güvenmek yetmiyor.
- **26 yerde `session.expunge_all()` test bug'ı:** Test-copilot'un yazdığı
  testler, mevcut proje konvansiyonunda (client/session aynı SQLAlchemy
  session'ı paylaşır, YET-70'ten beri hiç kullanılmayan bir desen) hiç
  gerekmeyen `expunge_all()` çağrıları içeriyordu — bu, sonraki `.id`
  erişimlerinde `DetachedInstanceError`'a yol açıyordu (13/15 test bu
  yüzden fail etti). Tümü kaldırıldı.
- **Docker Desktop kapanması:** Uzun oturum sırasında Docker Desktop
  tamamen kapandı (DB bağlantısı koptu, testler `OperationalError` verdi).
  Yeniden başlatılıp `docker compose up -d` ile DB ayağa kaldırıldı.
  **Ders:** uzun süren (birden fazla görev süren) bir pipeline
  oturumunda, `verify` adımında DB bağlantı hatası alınırsa önce "Docker
  hâlâ çalışıyor mu" kontrolü yapılmalı, doğrudan kod hatası sanılmamalı.
- **Ölü kod (red-team, düşük önem):** `scoped_attestations()` yazıldı ama
  hiç kullanılmadı (`revoke_attestation()` bunun yerine
  `scoped_engagements()` + manuel attestor kontrolü kullanıyordu) — silindi.
