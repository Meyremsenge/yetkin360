---
task_slug: yet-9-organization-domain-dogrulama
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: "DNS TXT sorgusu <3s (sabit timeout)"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/api/organizations.py (yeni)
  - backend/app/services/organization.py (yeni)
  - backend/app/models/identity.py (mevcut — Organization/OrganizationMember zaten burada tanımlı, DEĞİŞTİRİLMEZ)
  - backend/app/services/authorization.py (mevcut — can()/scoped_organizations() zaten var, DEĞİŞTİRİLMEZ, sadece kullanılır)
  - backend/app/services/outbox.py (mevcut — davet event'i eklenir, email anahtarı payload'da yasak)
  - backend/app/services/audit.py (mevcut — AC-S7 için kullanılır)
  - backend/alembic/versions/ (yeni migration — plan.md "Migration Required?")
  - docs/API.md §2.4 (referans, değiştirilmeyecek — sözleşme zaten sabit)
---

# ATDD — yet-9-organization-domain-dogrulama

Detaylı dosya listesi ve "Kritik keşif" notları için bkz. [plan.md](plan.md).

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. PLAN.md madde 1.9 ile eşleşiyor: "Organization
+ üyelik + domain doğrulama (T2)". Commit geçmişindeki YET-N numaralandırması
(YET-1..YET-8) PLAN madde numarasıyla birebir örtüşüyor (bkz. `git log`:
YET-1→1.1, YET-2→1.2, YET-4→1.4, YET-8→1.8) — bu eşleşme kullanıcıya
doğrulatılmadan (dosya üzerine yazma riski taşımadığı için) varsayım olarak
kullanıldı, yanlışsa 7. adımda (Hard Stop) düzeltilebilir.

## Persona
Bir organizasyon/şirket temsilcisi (ör. İK yetkilisi, staj sorumlusu) —
platformda kurumunu kaydedip ekibini davet eden ve kurumun gerçekliğini
kanıtlamak için domain doğrulaması yapan kişi.

## Hedef (Neden)
T1 (e-posta teyidi, tam otomatik) sürtünmesiz kayıt sağlar; T2 (kurumsal
domain + DNS TXT doğrulama) ise kurumun iddia ettiği tüzel kişiliğe gerçekten
ait olduğunu kanıtlayarak `PARTICIPATION` tanıklığı verme yetkisini gerçek
kurumlara sınırlar — sahte/kişisel domain ile itibarlı tanıklık üretimini
engeller.

## User Story
As a organizasyon temsilcisi
I want kurumumu oluşturup ekip üyelerimi davet edebilmek ve kurumsal domain'imi
doğrulayabilmek
So that platformda T2 güven seviyesiyle `PARTICIPATION` tanıklığı verebilirim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir kullanıcı, When `POST /organizations`
   ile `{name, domain?, legal_id?}` gönderir, Then `201` + kurum kaydı
   (`verification_level: "T1"`) döner ve kullanıcı otomatik `ADMIN` olur
   (gerçek DB rol enum'u `ADMIN|MEMBER` — bkz. plan.md "Kritik keşif").
2. [Critical] Given aynı `legal_id` ile ikinci bir organization oluşturma
   isteği, When `POST /organizations` çağrılır, Then `409 LEGAL_ID_TAKEN`
   döner.
3. [Critical] Given `ADMIN` rolüne sahip kullanıcı (Principal.kind
   `ORG_ADMIN`),
   When `POST /organizations/{id}/members` ile `{email, role}` gönderir,
   Then `201` + davet kaydı döner ve outbox'a e-posta event'i **aynı
   transaction içinde** eklenir.
4. [High] Given zaten üye olan bir e-posta, When tekrar davet edilir, Then
   `409 ALREADY_MEMBER` döner.
5. [Critical] Given `ORG:ADMIN` kullanıcı, When `POST /organizations/{id}/verify-domain`
   çağrılır ve organization'ın domain'i ücretsiz e-posta sağlayıcı (gmail.com,
   hotmail.com, outlook.com, yahoo.com vb. sabit liste) değilse, Then `200` +
   `{dns_txt_record, status:"pending"}` döner.
6. [Critical] Given domain ücretsiz e-posta sağlayıcı, When `verify-domain`
   çağrılır, Then `400 FREE_EMAIL_DOMAIN` döner ve `verification_level`
   değişmez.
7. [Critical] Given DNS'e TXT kaydı eklenmiş, When `verify-domain` tekrar
   çağrılır ve resolver TXT'yi bulursa, Then `200 {status:"verified"}` +
   `organization.verification_level="T2"`, `verified_at=now()`,
   `verified_by_user_id=çağıran kullanıcı` güncellenir.
8. [High] Given TXT kaydı DNS'te henüz yok veya sorgu timeout (>3sn), When
   `verify-domain` çağrılır, Then `200 {status:"pending"}` döner (hata değil),
   `verification_level` T1'de kalır.
9. [High] Given bir domain başka bir organization'da zaten T2 olarak
   doğrulanmış, When farklı bir organization aynı domain için `verify-domain`
   çağırır, Then doğrulama reddedilir (aşağıdaki Davranış Sözleşmesi #9).
10. [Medium] Given `ORG:ADMIN` olmayan bir kullanıcı, When `members` veya
    `verify-domain` uçlarını çağırır, Then `404` döner (403 değil).
11. [Medium] Given aynı organization için 1 dakika içinde ikinci
    `verify-domain` çağrısı, When istek yapılır, Then rate-limit devreye
    girer (Davranış Sözleşmesi #10).
12. [Critical] AC-S1: `GET /organizations/{id}` çağrısı, A organization'ına ait
    olmayan bir kullanıcının token'ıyla yapıldığında `404` döner ve yanıtta
    o organization'a ait hiçbir alan (name, domain, member listesi vb.)
    bulunmaz.
13. [Critical] AC-S2: `POST /organizations/{id}/members` isteğinde body'de
    `role: "ADMIN"` gönderilse bile, çağıran kullanıcı `ADMIN` değilse
    (yani bu organization için `ORG:ADMIN` yetkisi yoksa) istek zaten
    AC-10 ile `404` alır; `ORG:ADMIN` olan bir çağıran davet ettiği üyeye
    `ADMIN` veya `MEMBER` rolünü verebilir — gerçek DB kısıtı yalnızca iki
    rol tanımladığı için (`ck_organization_members_role`: `ADMIN|MEMBER`)
    ayrı bir "kendinden yüksek rol verme" senaryosu yoktur (rol seti zaten
    en yüksek `ADMIN` ile sınırlı). Girdi bu iki değer dışında bir rol
    içerirse `422` döner.
14. [Critical] AC-S3: `POST /organizations` isteğinde body'de
    `verification_level: "T2"` veya `verified_at`/`verified_by_user_id`
    gönderilse bile, sunucu bu alanları **yok sayar** — yeni kurum her zaman
    `verification_level: "T1"` ile oluşur (istemciden gelen güven seviyesine
    güvenilmez — Tampering).
15. [High] AC-S4: `POST /organizations/{id}/verify-domain` art arda aynı
    organization için 60 saniye içinde 2. kez çağrıldığında `429
    TOO_MANY_REQUESTS` döner; DNS sorgusu tekrar tetiklenmez (DoS/amplifikasyon
    koruması).
16. [High] AC-S5: Domain doğrulama sırasında DNS resolver'a verilen adres
    kullanıcı girdisindeki `domain` alanından türetilir; resolver çağrısı
    yalnızca standart DNS TXT sorgusu yapar (HTTP/TCP bağlantı kurmaz), bu
    yüzden dahili ağ adreslerine (`169.254.169.254`, `localhost`, RFC1918)
    HTTP isteği tetiklenemez (SSRF yüzeyi yok) — `domain` alanı ayrıca bir
    hostname formatı regex'iyle doğrulanır, IP adresi/port/path içeremez.
17. [Medium] AC-S6: `organization_members` tablosuna erişim `scoped_*()` ile
    daima çağıranın üyesi olduğu organization'larla filtrelenir; çıplak
    `select(OrganizationMember)` ile başka bir kiracının üye listesi asla
    dönmez (multi-tenant sızıntı — Info Disclosure).
18. [Medium] AC-S7: Kurum oluşturma, üye davet etme ve domain doğrulama
    (başarılı/başarısız) olayları `audit_events` tablosuna `actor_user_id`,
    `action`, `target_id`, zaman damgasıyla append-only olarak yazılır
    (Repudiation — kim ne zaman yaptı izlenebilir olmalı).

## Threat Model
Çağrıldı — STRIDE-lite uygulandı, AC-S1..AC-S7 kriterleri yukarıdaki
Acceptance Criteria listesine eklendi.

**Varlıklar ve sınırlar:** Organization kaydı (kiracı sınırı), OrganizationMember
üyelik/rol bilgisi, domain doğrulama durumu (T1↔T2 güven seviyesi — bu geçiş
tanıklık verme yetkisi kazandırdığı için yüksek değerli), DNS TXT sorgusu
(servis→dış DNS sınırı).

**STRIDE-lite:**
- **Spoofing** — mevcut `AUTH` middleware'i kapsıyor, bu görevde yeni bir
  kimlik doğrulama mekanizması yok → atlandı.
- **Tampering** — İstemciden gelen `role`, `verification_level`, `verified_at`
  gibi alanlara güvenilmemesi gerekiyor → AC-S2, AC-S3.
- **Repudiation** — Kurum/üyelik/doğrulama olaylarının izi olmalı → AC-S7.
- **Info disclosure** — Başka kiracının kurum/üye verisinin sızması,
  yetkisiz erişimde 404 yerine veri dönmesi → AC-S1, AC-S6.
- **DoS** — `verify-domain`'in sınırsız çağrılması DNS amplifikasyonuna/kaynak
  tüketimine yol açabilir → AC-S4.
- **Elevation** — Rol atamada kendinden yüksek rol verme, domain doğrulama
  SSRF'e dönüşme riski → AC-S2, AC-S5.

**Kabul edilen risk:** Rate-limit için Redis yasak olduğundan DB tabanlı
`last_verify_attempt_at` kolonuyla basit cooldown uygulanacak; çok yüksek
eşzamanlı istekte (aynı organization'a aynı anda iki paralel `verify-domain`
çağrısı) küçük bir race-condition penceresi olabilir — MVP/hackathon kapsamı
için kabul edilebilir risk olarak işaretlendi (Risks bölümüne de eklendi).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — yeni organization oluşturma | `201` + `{id, name, domain, verification_level:"T1"}` (model'de `slug` alanı yok) | `organizations` + `organization_members(ADMIN)` insert (tek transaction) | "Kurum oluşturuldu" | AC-1 |
| 2 | Girdi geçersiz/eksik (`name` boş, `domain` formatı bozuk) | `422` (Pydantic validation) | Yok | Alan bazlı hata mesajı | AC-2 |
| 3 | Kaynak yok (var olmayan `organization_id`) | `404` | Yok | "Bulunamadı" | AC-10 |
| 4 | Yetkisiz erişim (`ORG:ADMIN` değil) | `404` (403 değil — CLAUDE.md kuralı) | Yok | "Bulunamadı" | AC-10 |
| 5 | Dış bağımlılık hatası (DNS sorgusu NXDOMAIN/hata) | `200 {status:"pending"}` (hata değil, doğrulanamadı) | Yok, `verification_level` T1'de kalır | "Henüz doğrulanamadı, TXT kaydını kontrol edin" | AC-8 |
| 6 | Zaman aşımı (DNS sorgusu >3sn) | `200 {status:"pending"}` (madde 5 ile aynı) | Yok | Aynı — "pending" | AC-8 |
| 8 | Hiçbir şey yapılamadı ama hata yok (TXT kaydı DNS'te henüz görünmüyor) | `200 {status:"pending"}` — beklenen ara durum, hata değil | Yok | "TXT kaydı henüz görülemedi, birkaç dakika sonra tekrar deneyin" | AC-8 |
| 9 | Aynı `legal_id` ikinci kez | `409 LEGAL_ID_TAKEN` | Yok | "Bu tüzel kişilik zaten kayıtlı" | AC-2 |
| 9b | Domain başka organization'da zaten T2 | `409 DOMAIN_ALREADY_VERIFIED` (yeni hata kodu — DB'de doğrulanmış domain üzerinde partial unique index) | Yok | "Bu domain başka bir kurum tarafından doğrulanmış" | AC-9 |
| 10 | Rate limit (1 dk içinde 2. `verify-domain` çağrısı) | `429 TOO_MANY_REQUESTS` | Yok | "Lütfen biraz bekleyip tekrar deneyin" | AC-11 |

Kısmi başarı: Mimari olarak imkansız kılınmış — CLAUDE.md kuralı gereği
`organization_members` insert'i ile outbox event insert'i **aynı DB
transaction'ı içinde** yapılır (ağ çağrısı yok, sadece satır ekleme); ya
ikisi birlikte commit olur ya ikisi birlikte rollback olur.

Hiçbir şey yapılamadı ama hata da yok: Satır 8'de ele alındı — "pending"
durumu sessiz başarı değildir, `status` alanı açıkça "henüz doğrulanmadı"
bilgisini taşır, `verification_level` değişmediği için çağıran yanlışlıkla
T2 sanmaz.

Boş sonuç ↔ hata ayrımı: `GET /organizations/{id}` için organization
bulunamazsa `404`; kullanıcının erişim yetkisi yoksa da `404` (aynı kod,
kaynağın var olup olmadığı sızdırılmaz — CLAUDE.md "403 değil 404" kuralı).
`verify-domain` "pending" durumu (satır 8) `404`/hata ile karıştırılmaz:
her zaman `200` döner, sadece `status` alanı farklıdır.

## Test Strategy
Unit: 70% — ücretsiz-domain-reddi kontrolü, TXT doğrulama
mantığı (DNS resolver mock'lanır), rate-limit cooldown hesaplama.
Integration: 20% — endpoint + DB + outbox (aynı transaction'da insert
edildiğinin doğrulanması), yetkilendirme (`can()`/`scoped_*()`) kontrolleri.
E2E: 10% — tam happy-path akışı (organization oluştur → davet et →
verify-domain → DNS mock ile T2'ye geçiş).

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: DNS TXT sorgusu için sabit 3sn timeout — bu süre aşılırsa
`pending` dönülür, istek bloklanmaz.
Memory: Belirtilmedi (varsayım gerektirmiyor, standart FastAPI istek boyutu).
Görsel/UI kriteri: Yok — bu görev yalnız backend API, frontend kapsamı dışı.
Diğer ölçülebilir kriterler: Rate limit — aynı organization için `verify-domain`
dakikada en fazla 1 çağrı.

## Kapsam Dışı
- T3 (MERSİS/vergi no admin onayı) ve T4 (koordinatör onayı) — ayrı PLAN
  maddeleri (3.6, 2.3).
- Davetin e-posta gönderimi worker'ının kendisi — YET-5'te zaten kurulan
  outbox worker kullanılır, burada yalnız outbox'a event eklenir.
- Davet edilen üyenin daveti kabul etme akışı (`accepted_at` set edilmesi) —
  ayrı bir uç/görev olmalı, bu görevde yalnız davet oluşturma var.
- Ücretsiz e-posta sağlayıcı listesinin dinamik/dış servisten güncellenmesi —
  MVP'de kod içinde sabit liste.
- Frontend ekranları (PLAN 1.12-1.14 kapsamında, ayrı görev).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/organizations.py` (yeni router)
- `backend/app/services/organizations.py` (yeni servis — iş mantığı burada)
- `backend/app/models/organization.py` (yeni ORM modelleri: Organization,
  OrganizationMember)
- `backend/app/services/outbox.py` (mevcut — davet e-postası için event
  eklenir, değiştirilmez sadece kullanılır)
- `backend/app/services/authorization.py` (mevcut `can()`/`scoped_*()` —
  `ORG:ADMIN`/`ORG:MEMBER` kontrolleri buradan geçer)
- Institutions modülünün (YET-8) benzer yapısı **kod şablonu** olarak referans
  alınır, import edilmez (CLAUDE.md: "modüller birbirinin iç dosyalarını
  import etmez").

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle birebir
aynı olup olmadığı teyit edilmedi. Sonraki adımlarda (`plan`, `code-copilot`,
`test-copilot`, `red-team`) arama `yetkin360` proje klasörüyle sınırlı
tutulmalı, kök dizinden sınırsız `grep -r`/`git log -p --all` çalıştırılmamalı.

## Rollback Beklentisi
Domain doğrulama başarısız/pending kalırsa organization `T1`'de kalmaya
devam eder, T1 hakları (kurum oluşturma, üye davet etme) kaybedilmez.
Rate limit dahilinde sınırsız tekrar denenebilir. `verify-domain` çağrısı
hiçbir zaman organization kaydını veya mevcut üyelikleri geri almaz/silmez.

## Risks
- Gerçek DNS TXT sorgusu (`dnspython` ile) test edilebilirliği hackathon
  ortamında kırılgan olabilir — testlerde resolver mock'lanmalı, yalnız
  1 e2e/manuel testte gerçek sorgu denenebilir.
- Rate-limit için Redis yasak (CLAUDE.md kapsam kısıtı) — DB tabanlı
  `last_verify_attempt_at` kolonu ile basit cooldown uygulanacak; yüksek
  eşzamanlılıkta race condition riski düşük ama sıfır değil (MVP için kabul
  edilebilir — bkz. Threat Model "Kabul edilen risk").
- AC-S1/AC-S6 (multi-tenant izolasyon) `plan`/`test-copilot` adımında
  `authz-test` skill'i çağrılarak IDOR/kiracı-sızıntı test matrisiyle ayrıca
  doğrulanmalı — bu ATDD adımında sadece gereksinim olarak yazıldı, henüz
  kod/canlı sistem olmadığı için `authz-test`'in kendisi burada çalıştırılmadı.

## Assumptions
- YET-9 = PLAN.md madde 1.9 eşleşmesi (bkz. Jira Kaynağı bölümü) — kullanıcı
  onayı 7. adımda (Hard Stop) alınacak, yanlışsa düzeltilecek.
- Ücretsiz e-posta sağlayıcı listesi: gmail.com, hotmail.com, outlook.com,
  yahoo.com (genişletilebilir, bu görevde sabit kod listesi olarak kabul
  edildi — Sonnet 5 alt-ajanı tarafından önerildi).
- DNS sorgusu senkron yapılır, outbox'a gerekmiyor — salt-okunur, yan etkisiz,
  idempotent bir kontrol olduğu için (CLAUDE.md'deki outbox kuralı yan etkili
  dış çağrılar için, DNS lookup dışa veri göndermiyor).

## Unknowns
- Aynı domain'in birden fazla organization tarafından "T1" halinde
  (henüz doğrulanmamış) paylaşılıp paylaşılamayacağı — bu görevde izin
  verildi, yalnız T2 doğrulama anında çakışma engellendi (partial unique
  index varsayımı, migration detayı `plan` adımında netleşecek).
- Rate-limit eşiğinin (dakikada 1) kesin değeri kullanıcı tarafından
  onaylanmadı — makul varsayım olarak işaretlendi.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Organizasyon temsilcisi (İK/staj sorumlusu).
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı: DOMAIN.md §3.4 ve API.md
   §2.4'teki OWNER/SUPERVISOR/MEMBER rolleri bu personayı işaret ediyor.)
2. Ana hedef/neden → T1 sürtünmesiz kayıt, T2 sahte kurum engelleme.
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı: DOMAIN.md §3.4 güven
   kademeleri tablosundan çıkarım.)
3. Happy path → POST /organizations → members → verify-domain → DNS TXT →
   tekrar verify-domain → T2. (Sonnet 5 low alt-ajanı tarafından yanıtlandı:
   API.md §2.4 sözleşmesinden birebir.)
4. Edge case'ler → 409 LEGAL_ID_TAKEN, 409 ALREADY_MEMBER, 400
   FREE_EMAIL_DOMAIN, aynı domain çakışması, TXT henüz yok. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı.)
5. Davranış sözleşmesi → yukarıdaki tablo. (Sonnet 5 low alt-ajanı
   tarafından dolduruldu, madde 8/9b/10 ATDD yazarı tarafından netleştirildi.)
6. Başarı ölçütü → coverage %85, DNS sorgusu senkron+outbox gereksiz.
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLAUDE.md outbox kuralının
   kapsamı yan etkili çağrılarla sınırlı olduğu gerekçesiyle.)
7. Kapsam dışı → T3/T4, davet kabul akışı, frontend. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı: PLAN.md madde numaralarına göre ayrıştırıldı.)
8. Bağımlılıklar → auth, outbox, institutions kod şablonu. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı.)
9. Güvenlik kısıtı → DNS rebinding/rate-limit riski, SSRF riski yok.
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı — bu bölüm ayrıca
   `threat-model` skill'i tarafından derinleştirilecek.)
10. Rollback → T1'de kalır, sınırsız tekrar deneme (rate limit dahilinde).
    (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
11. Kabul kriteri sahibi → otomatik test. (Sonnet 5 low alt-ajanı tarafından
    yanıtlandı: backend API görevi, ATDD şablonu varsayılanı.)
12. Test stratejisi → 70/20/10. (Sonnet 5 low alt-ajanı tarafından
    yanıtlandı, proje varsayılanına uygun.)
13. Riskler/varsayımlar → DNS mock gerekliliği, sabit e-posta listesi.
    (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
