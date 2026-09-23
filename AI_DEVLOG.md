# AI Dev Log

Bu dosya, ATDD pipeline'ının her adımının kendi artefaktına (`atdd.md`,
`plan.md`, `code_diff.md`, `verify_report.md`, `red_team.json`) yazdığı
bilinçli kararları, kabul edilen riskleri ve gerçek zorlukları commit
zamanında buraya **aktarır** — yeniden yorumlamaz.

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
