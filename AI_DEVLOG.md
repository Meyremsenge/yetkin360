# AI Dev Log

Bu dosya, ATDD pipeline'ının her adımının kendi artefaktına (`atdd.md`,
`plan.md`, `code_diff.md`, `verify_report.md`, `red_team.json`) yazdığı
bilinçli kararları, kabul edilen riskleri ve gerçek zorlukları commit
zamanında buraya **aktarır** — yeniden yorumlamaz.

## YET-2.2 — Durum makinesi: POST /engagements/{id}/transitions (2026-09-23)

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
