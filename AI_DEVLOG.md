# AI Dev Log

Bu dosya, ATDD pipeline'ının her adımının kendi artefaktına (`atdd.md`,
`plan.md`, `code_diff.md`, `verify_report.md`, `red_team.json`) yazdığı
bilinçli kararları, kabul edilen riskleri ve gerçek zorlukları commit
zamanında buraya **aktarır** — yeniden yorumlamaz.

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
