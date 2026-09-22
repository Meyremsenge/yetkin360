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
