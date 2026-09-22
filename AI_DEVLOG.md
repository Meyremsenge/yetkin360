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
