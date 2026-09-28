# HATA.md — Yetkin360 Kapsamlı Hata ve Risk Denetimi

**Tarih:** 2026-09-28 (teslime 11 gün)
**Dal:** `main` (`82a690a`)
**Kapsam:** Backend'deki **47 endpoint'in tamamı** (13 router), bunların servis katmanı,
yetkilendirme çekirdeği, outbox worker, migration'lar, frontend API/oturum katmanı ve
sayfalar.
**Önceki sürüm:** 2026-09-27 tarihli entegrasyon denetimi (9 bulgu). O bulgular
§9'da güncel durumlarıyla bu rapora taşındı.

---

## 0. Yöntem ve kanıt düzeyi

Bu rapor önceki sürümden farklı olarak **canlı ortamda** doğrulandı (Docker ayaktaydı).

| Yöntem | Ne yapıldı | Sonuç |
|---|---|---|
| Statik okuma | 13 router, 17 servis, worker, yetkilendirme çekirdeği, ilgili modeller, trigger migration'ları, frontend `lib/api/*`, `lib/session/*`, middleware, ilgili sayfalar | Aşağıdaki bulgular |
| Backend testleri | `pytest -q` (seed'li yerel DB'ye karşı) | **13 başarısız**, 798 geçti, 5 atlandı |
| Frontend testleri | `npx vitest run` | **9 başarısız**, 814 geçti |
| Frontend lint / tip | `npm run lint`, `npm run typecheck` | 0 hata (6 uyarı) / temiz |
| Güvenlik taraması | `security-scan` skill'i (bandit, detect-secrets, pip-audit) + `npm audit` | Bandit PASS; **pip-audit FAIL** (pyjwt, starlette, pytest); **npm audit 1 high** |
| Canlı sonda | `TestClient` ile gerçek DB'ye karşı istekler + DB sayımları | Kilitleme hatası, outbox birikmesi, public token yokluğu **doğrulandı** |

Kanıt düzeyleri: **[CANLI]** = çalışan sistemde gözlendi · **[KOD]** = kod okumasıyla
kesin, çalıştırılmadı · **[ŞÜPHE]** = güçlü işaret var, doğrulanması gerekiyor.

---

## 1. Yönetici özeti

Güvenlik temeli (404-not-403, CSRF double-submit, httpOnly cookie, scoped sorgular,
append-only trigger'lar) büyük ölçüde doğru kurulmuş. Ancak **ürünün ana zinciri
(`beyan → kanıt → tanıklık → doğrulanmış deneyim`) arayüzden uçtan uca tamamlanamıyor**
ve birkaç güvenlik mekanizması **kodda var ama fiilen çalışmıyor**.

### Demoyu doğrudan kıran 11 madde (9 Ekim'den önce kapanmalı)

| # | ID | Sorun | Kanıt |
|---|---|---|---|
| 1 | IS-01 | Public doğrulama linki hiçbir zaman çalışmaz: `public_token` hiçbir yerde üretilmiyor, VerifiedExperience görünürlüğünü değiştiren uç yok | [CANLI] DB: 15 VE, 0 token, 0 PUBLIC |
| 2 | IS-02 | COMPETENCE tanıklığı ulaşılamaz: `started_on/ended_on` hiçbir uçtan set edilmiyor → her tanıklık PARTICIPATION'a düşer | [KOD] yalnız `seed.py` set ediyor |
| 3 | ENT-01 | Zincirin yarısı için arayüz yok: engagement oluşturma, görev, teslim (deliverable), tanıklık, geri çekme, kurum/organizasyon yönetimi ekranı yok | [KOD] frontend çağrı envanteri §3 |
| 4 | ENT-02 | Değerlendirme ve kanıt yükleme hâlâ mock (localStorage) | [KOD] önceki rapor #1-#2, hâlâ açık |
| 5 | OPS-01 | Outbox worker hiç çalışmıyor; çalışsa bile handler'sız topic'ler kuyruğu kalıcı tıkıyor | [CANLI] 60 işlenmemiş satır |
| 6 | OPS-02 | E-posta linkleri yanlış sayfaya gidiyor (`/verify-email`, `/reset-password` yok; sayfalar `/e-posta-dogrula`, `/sifre-sifirla`) | [KOD] |
| 7 | OPS-03 | MinIO bucket'ı hiçbir yerde oluşturulmuyor; MinIO container'ı `unhealthy` | [CANLI] `docker compose ps` |
| 8 | ENT-03 | Access token süresi dolduktan (15 dk) sonraki ilk yazma isteği **her zaman 403 CSRF** alır | [KOD] `client.ts:170` |
| 9 | ENT-04 | Frontend `EVALUATED` / `VERIFIED` durumlarını tanımıyor; seed'deki 15 engagement'ın **hepsi** VERIFIED | [CANLI] DB + `messages/tr.json` |
| 10 | TEST-01 | Test paketleri kırmızı: backend 13, frontend 9 başarısız; CI frontend testlerini hiç koşmuyor | [CANLI] |
| 11 | AUTHZ-02 | Seed'de **hiç COORDINATOR yok** (5 kurum üyesinin 5'i ADMIN); onay (T2) ve tanıklık yalnız COORDINATOR'a açık → seed kullanıcılarıyla koordinatör adımı API'den **yapılamaz** | [CANLI] DB |

### Güvenlikte en ciddi 5 madde

| ID | Sorun | Ciddiyet |
|---|---|---|
| GUV-01 | Giriş kilitleme **hiç çalışmıyor** (sayaç rollback ile kayboluyor) → sınırsız parola denemesi | **KRİTİK** [CANLI] |
| GUV-02 | Herhangi bir kullanıcı kurum/organizasyon açıp **rızası olmadan** başka bir kullanıcıyı üye yapabiliyor → kurbanın hesabı işlevsiz kalıyor + e-posta numaralandırma | **YÜKSEK** [KOD] |
| GUV-03 | Tek kullanıcı birkaç hesapla uçtan uca **sahte doğrulanmış deneyim** üretebilir (Sybil) | **YÜKSEK** [KOD] |
| GUV-04 | Talent, kendi TALENT_TO_ORG değerlendirmesiyle **kendine STRONG skill sinyali** yazabiliyor | **YÜKSEK** [KOD] |
| GUV-05 | Geri çekilen (revoked) tanıklık public sayfada ve doğrulanmış deneyimde **geçerli görünmeye devam ediyor** | **YÜKSEK** [KOD] |

---

## 2. Risk matrisi

Ciddiyet = etki × olasılık. Etki: güvenlik/veri bütünlüğü > demo/teslim > UX > hijyen.

| Ciddiyet | Adet | ID'ler |
|---|---|---|
| **KRİTİK** | 11 | GUV-01, AUTHZ-02, IS-01, IS-02, IS-07, ENT-01, ENT-02, ENT-03, OPS-01, OPS-02, OPS-03 |
| **YÜKSEK** | 15 | GUV-02, GUV-03, GUV-04, GUV-05, GUV-06, GUV-07, AUTHZ-01, IS-03, IS-04, IS-08, ENT-04, ENT-05, DEP-01, TEST-01, TEST-02 |
| **ORTA** | 19 | GUV-08…GUV-13, AUTHZ-03, AUTHZ-04, IS-05, IS-06, IS-09, IS-10, IS-11, VER-01, VER-02, ENT-06, ENT-07, OPS-04, DEP-02 |
| **DÜŞÜK** | 17 | VER-03, L-01…L-16 (§8) |

---

## 3. Endpoint envanteri (47 uç)

Sütunlar: **Auth** = kimlik gerekli mi · **CSRF** = yazma korumalı mı · **FE** = frontend
gerçekten çağırıyor mu (M = mock, — = hiç kullanılmıyor) · **Bulgular**.

| # | Metot + Yol | Auth | CSRF | FE | Bulgular |
|---|---|---|---|---|---|
| 1 | `POST /auth/register` | — | — | ✅ | GUV-10 (zamanlama) |
| 2 | `POST /auth/login` | — | — | ✅ | **GUV-01**, GUV-11, L-03 |
| 3 | `POST /auth/refresh` | cookie | — | ✅ | ENT-03, L-04 |
| 4 | `POST /auth/logout` | ✅ | ✅ | ✅ | **GUV-06** |
| 5 | `POST /auth/verify-email` | — | — | ✅ | OPS-02, IS-08 |
| 6 | `POST /auth/forgot-password` | — | — | ✅ | OPS-02, GUV-11 |
| 7 | `POST /auth/reset-password` | — | — | ✅ | OPS-02 |
| 8 | `GET /me` | ✅ | — | ✅ | AUTHZ-01, ENT-05 |
| 9 | `PATCH /talents/me` | ✅ | ✅ | ✅ | IS-09, L-06 |
| 10 | `GET /talents/me/skills` | ✅ | — | ✅ | L-09 (N+1) |
| 11 | `POST /talents/me/skills` | ✅ | ✅ | ✅ | ORTA: VER-02 (yanlış 409) |
| 12 | `DELETE /talents/me/skills/{skill_id}` | ✅ | ✅ | ✅ | VER-03 |
| 13 | `GET /talents/me/signals/` | ✅ | — | ✅ | ENT-06 (307), L-08 |
| 14 | `GET /talents/me/verified-experiences/` | ✅ | — | ✅ | ENT-06 (307), GUV-05 |
| 15 | `GET /skills` | ✅ | — | ✅ | — |
| 16 | `POST /engagements` | ✅ | ✅ | — | **GUV-03**, GUV-08, IS-02 |
| 17 | `GET /engagements` | ✅ | — | ✅ | AUTHZ-01 |
| 18 | `GET /engagements/{id}` | ✅ | — | ✅ | AUTHZ-01 |
| 19 | `POST /engagements/{id}/transitions` | ✅ | ✅ | ✅ | AUTHZ-02, IS-03, IS-04 |
| 20 | `POST /engagements/{id}/tasks` | ✅ | ✅ | — | IS-06 |
| 21 | `POST /engagements/{id}/deliverables` | ✅ | ✅ | — | IS-06, ENT-01 |
| 22 | `POST /engagements/{id}/evaluation` | ✅ | ✅ | M | **GUV-04**, ENT-02, IS-05 |
| 23 | `POST /engagements/{id}/attestations` | ✅ | ✅ | — | IS-01, IS-02, IS-05, GUV-03 |
| 24 | `POST /attestations/{id}/revoke` | ✅ | ✅ | — | **GUV-05** |
| 25 | `POST /evidence/upload-url` | ✅ | ✅ | M | OPS-03, GUV-12 |
| 26 | `POST /evidence` | ✅ | ✅ | M | IS-07, GUV-12 |
| 27 | `GET /evidence/{id}/download-url` | ✅ | — | — | IS-07 (hep 409) |
| 28 | `POST /institutions/` | ✅ | ✅ | — | **GUV-02**, GUV-03, GUV-09 |
| 29 | `POST /institutions/{id}/members` | ✅ | ✅ | — | **GUV-02**, GUV-07, L-01 |
| 30 | `POST /institutions/{id}/link-requests` | ✅ | ✅ | — | IS-10 |
| 31 | `POST /institutions/{id}/link-requests/{rid}/approve` | ✅ | ✅ | — | IS-10 |
| 32 | `GET /institutions/{id}/dashboard` | ✅ | — | ✅ | AUTHZ-01 |
| 33 | `POST /institutions/{id}/reminders` | ✅ | ✅ | — | OPS-01, GUV-13 |
| 34 | `POST /organizations/` | ✅ | ✅ | — | **GUV-02**, GUV-03 |
| 35 | `POST /organizations/{id}/members` | ✅ | ✅ | — | **GUV-02**, GUV-07 (500) |
| 36 | `POST /organizations/{id}/verify-domain` | ✅ | ✅ | — | AUTHZ-04, L-02 |
| 37 | `GET /organizations/{id}` | ✅ | — | — | AUTHZ-01 |
| 38 | `GET /public/talents/{slug}` | — | — | ✅ | IS-01, L-05 |
| 39 | `GET /public/v/{token}` | — | — | ✅ | **IS-01**, **GUV-05** |
| 40 | `GET /admin/verification-queue` | admin | — | ✅ | IS-11, L-07 |
| 41 | `POST /admin/organizations/{id}/verification-level` | admin | ✅ | ✅ | IS-11 |
| 42 | `GET /admin/skills` | admin | — | ✅ | L-07 |
| 43 | `POST /admin/skills` | admin | ✅ | ✅ | — |
| 44 | `PATCH /admin/skills/{id}` | admin | ✅ | ✅ | L-10 |
| 45 | `POST /admin/skills/{id}/deprecate` | admin | ✅ | ✅ | — |
| 46 | `POST /admin/skills/{id}/merge` | admin | ✅ | ✅ | L-10 |
| 47 | `GET /health` | — | — | — | — |

**Özet:** 47 ucun **17'si** frontend'den hiç çağrılmıyor, **3'ü** mock arkasında. Kalan
uçlar bağlı.

**Hiç olmayan ama zincirin ihtiyaç duyduğu uçlar:** kanıt listesi (`GET /evidence`),
kurumun bekleyen bağlanma taleplerini listeleme, talep reddetme, VerifiedExperience
görünürlüğü değiştirme/token üretme, engagement tarihlerini girme, e-posta doğrulama
linkini yeniden gönderme, T4 ve T9/T10 geçişleri (bkz. IS-03, IS-10).

---

## 4. Güvenlik bulguları

### GUV-01 — Giriş kilitleme hiç çalışmıyor · KRİTİK · [CANLI]

**Konum:** [backend/app/services/auth.py:363-389](backend/app/services/auth.py#L363-L389),
[backend/app/core/deps.py:20-29](backend/app/core/deps.py#L20-L29)

**Sorun:** Yanlış parolada `failed_login_count` artırılıp `InvalidCredentials`
fırlatılıyor. Router bunu `ApiError`'a çeviriyor; `get_session` istisnayı görünce
**tüm transaction'ı rollback ediyor**. Sayaç artışı ve `USER_LOGIN/DENIED` audit
kaydı hiçbir zaman DB'ye yazılmıyor. Aynı tuzak `refresh_tokens()` için fark edilip
açık `session.commit()` ile çözülmüş ([auth.py:457](backend/app/services/auth.py#L457)),
login için unutulmuş.

**Kanıt:** Seed kullanıcısıyla 3 yanlış giriş → `failed_login_count` 0'da kaldı,
`audit_events` içinde DENIED kaydı **0**.

**Etki:** 10 denemede kilitleme kuralı yok hükmünde; sınırsız çevrimiçi parola
denemesi. Başarısız giriş denemeleri denetim kaydına hiç düşmüyor (olay sonrası
inceleme imkânsız). Repo açık kaynak olduğu için bu herkes tarafından okunabilir.

**Öneri:** Başarısız yolda sayaç + audit'i istisnadan önce commit et (refresh'teki
desen) veya servisten istisna yerine sonuç nesnesi dön, router 401'i commit'ten sonra
üretsin. Regresyon testi: gerçek `get_session` ile 10 yanlış giriş → 423.

### GUV-02 — Rızasız üyelik ataması: hesap kilitleme + e-posta numaralandırma · YÜKSEK · [KOD]

**Konum:** [backend/app/api/institutions.py:128](backend/app/api/institutions.py#L128),
[backend/app/services/institution.py:80-120](backend/app/services/institution.py#L80-L120),
[backend/app/api/organizations.py:136-204](backend/app/api/organizations.py#L136-L204),
[backend/app/api/deps.py:43-54](backend/app/api/deps.py#L43-L54)

**Sorun (zincir):**
1. Kimliği doğrulanmış **her kullanıcı** `POST /institutions/` veya `POST /organizations/`
   ile kurum açıp ADMIN olabiliyor (onay/doğrulama yok).
2. ADMIN, yalnızca e-posta adresiyle **herhangi bir kullanıcıyı** anında üye yapabiliyor
   (davet/kabul akışı yok). Kurum tarafında mevcut üyenin rolü de sessizce değiştiriliyor
   (`member.role = role`).
3. `get_current_principal` tek bir `kind` seçiyor ve kurum üyeliği TALENT'ın önüne
   geçiyor. `scoped_engagements`, `scoped_evidence`, `create_deliverable` ise `kind`'a
   bakıyor.

**Senaryo:** Saldırgan sahte kurum açar, kurbanın e-postasını ADMIN olarak ekler →
kurbanın `kind`'ı `INST_ADMIN` olur → kurban **kendi engagement'larını göremez, teslim
yapamaz, kendi kanıtını indiremez**, değerlendirme yapamaz. Kurbanın bunu geri alma
yolu yok (üyelikten çıkma ucu yok).

**Ek sızıntı:** Kurumda bilinmeyen e-posta → `422 "User not found"`, bilinen → `201`.
Organizasyonda bilinmeyen e-posta → **500** (bkz. GUV-07). Kayıt ucunun (#1) numaralandırma
koruması bu yolla tamamen boşa çıkıyor.

**Öneri:** Üyelik için davet + kabul (bekleyen davet tablosu ya da outbox e-postası);
bilinmeyen/bilinen e-postaya aynı yanıt; AUTHZ-01'in çözümü (çoklu rol) ile birlikte
ele alınmalı.

### GUV-03 — Tek kişiyle sahte "doğrulanmış deneyim" üretimi (Sybil) · YÜKSEK · [KOD]

**Konum:** engagement oluşturma [engagement.py:90-222](backend/app/services/engagement.py#L90-L222),
kurum/organizasyon oluşturma (GUV-02), tanıklık [attestation.py](backend/app/services/attestation.py)

**Senaryo (3 hesap, hepsi self-servis):** A hesabı organizasyon "X A.Ş." açar; B hesabı
kurum açıp kendini koordinatör yapar (ya da C'yi davet eder); C talent B'nin kurumuna
bağlanma talebi atar, B onaylar. C engagement oluşturur (TALENT **herhangi bir**
`organization_id` seçebiliyor — organizasyonun rızası yok), B onaylar, A değerlendirir,
B tanıklık verir → **VerifiedExperience oluşur**.

**Hafifletici:** Organizasyon T1 kaldığı için claim PARTICIPATION'a düşer ve public
sayfada `organization_trust_level: T1` görünür. **Ama:** kurumun doğrulama seviyesi
(`institutions.verification_level`) hiçbir yerde kontrol edilmiyor ve public sayfada
gösterilmiyor; ayrıca organizasyon adı serbest metin ve alan adı public sayfada yok
(GUV-09).

**Öneri (MVP ölçeğinde):** (a) Organizasyonun engagement'ı onaylaması (T1 öncesi org
onayı ya da T2'de org tarafı onayı); (b) tanıklıkta kurum seviyesini de downgrade
kriterine kat; (c) public sayfada kurum seviyesini ve org alan adını göster.

### GUV-04 — Talent kendi değerlendirmesiyle kendine STRONG skill sinyali yazabiliyor · YÜKSEK · [KOD]

**Konum:** [backend/app/services/evaluation.py:173-203](backend/app/services/evaluation.py#L173-L203)

**Sorun:** Skill sinyali üretimi yönden bağımsız. Talent `TALENT_TO_ORG` yönünde
(organizasyonu değerlendirirken) maddelere `skill_id` + `EXCEEDS` yazarsa
`talent_id=engagement.talent_id` için **STRONG** sinyal üretiliyor
(`attested_by_org_id=None`).

**İlgili:** Talent her teslimde (`POST /deliverables`) `skill_id` vererek sınırsız
**MODERATE** sinyal üretebiliyor ([engagement.py:643-655](backend/app/services/engagement.py#L643-L655));
organizasyon görev açtığı anda **WEAK** sinyal üretiliyor (görev tamamlanmadan).

**Etki:** Platformun ana vaadi olan "kanıta dayalı yetkinlik sinyali" talent tarafından
şişirilebilir.

**Öneri:** Sinyal yalnız `ORG_TO_TALENT` yönünde; teslim sinyalleri ya organizasyon
onayından sonra ya da strength'i NONE/WEAK sınırlı olacak şekilde.

### GUV-05 — Geri çekilen tanıklık geçerli görünmeye devam ediyor · YÜKSEK · [KOD]

**Konum:** [backend/app/services/attestation.py:408+](backend/app/services/attestation.py#L408),
[backend/app/services/authorization.py:352-372](backend/app/services/authorization.py#L352-L372),
[backend/app/api/public.py:138-229](backend/app/api/public.py#L138-L229)

**Sorun:** `revoke_attestation` yalnız attestation'ı ve ATTESTATION kaynaklı skill
sinyallerini işaretliyor. `revoked_at` **hiçbir okuma yolunda filtrelenmiyor**:
- `scoped_attestations_for_engagement` geri çekilenleri de döndürüyor → public
  doğrulama sayfasında skill hâlâ "COMPETENCE" olarak listeleniyor.
- VerifiedExperience ve engagement `VERIFIED` kalıyor; talent profilinde ve public
  profilde deneyim geçerli görünüyor.

**Etki:** Bir doğrulama platformunun en kritik garantisi ("geri çekilen tanıklık artık
geçerli değildir") sağlanmıyor. Jüri/işveren sahte-geçerli kayıt görür.

**Öneri:** Okuma sorgularına `revoked_at IS NULL`; VerifiedExperience'ta "geri çekildi"
göstergesi (append-only kuralı nedeniyle ayrı tablo ya da istisna alanı — mimari karar,
sorulmalı).

### GUV-06 — Logout refresh token'ı iptal edemiyor · YÜKSEK · [KOD]

**Konum:** [backend/app/api/auth.py:58-66](backend/app/api/auth.py#L58-L66) ve
[auth.py:126-143](backend/app/api/auth.py#L126-L143)

**Sorun:** `refresh_token` cookie'si `path="/auth/refresh"` ile yazılıyor; tarayıcı bu
cookie'yi `/auth/logout` isteğine **göndermez**. Logout'ta `refresh_token_value` her zaman
`None` → aile iptali hiç çalışmaz. Yalnız istemci tarafındaki cookie silinir.

**Etki:** Çalınmış bir refresh token logout'tan sonra da 30 gün geçerli kalır. Test
paketinde bu yol muhtemelen cookie'yi elle ekleyerek geçiyor.

**Öneri:** Refresh cookie path'ini `/auth` yap (refresh + logout ikisini de kapsar) ya da
logout'ta kullanıcının tüm aktif ailelerini iptal et.

### GUV-07 — Organizasyona bilinmeyen e-posta davet edilince 500 · YÜKSEK · [KOD]

**Konum:** [backend/app/services/organization.py:159](backend/app/services/organization.py#L159),
[backend/app/api/organizations.py:288](backend/app/api/organizations.py#L288)

`invite_org_member` `ValueError` fırlatıyor, router yalnız `AlreadyMemberError`'ı
yakalıyor → **500 Internal Server Error**. Hem hata, hem numaralandırma oracle'ı (500 vs
201). Kurum tarafında aynı durum 422 dönüyor (tutarsız). Kurumda `role` Pydantic'te
doğrulanmıyor → geçersiz rol DB CHECK'e çarpar → yine 500.

### GUV-08 — Talent ve organizasyon, karşı tarafın rızası olmadan engagement açabiliyor · ORTA · [KOD]

**Konum:** [backend/app/services/engagement.py:145-184](backend/app/services/engagement.py#L145-L184)

- TALENT herhangi bir organizasyon için engagement açabiliyor (org sadece var mı diye
  bakılıyor). Açılan kayıt o organizasyonun listesine düşer → organizasyon listesine spam.
- ORG_MEMBER **platformdaki herhangi bir talent** için engagement açabiliyor; talent'ın
  listesine düşer.
- `institution_id` uyuşmazlığında 400, uyuşunca 201 → organizasyon, talent'ın hangi
  kuruma bağlı olduğunu deneyerek öğrenebilir (bilgi sızıntısı oracle'ı).

### GUV-09 — Alan adı ve kurum adı gaspı / sahte güven görüntüsü · ORTA · [KOD]

- `POST /institutions/` alan adını doğrulamadan unique olarak ayırıyor: ilk gelen
  `bilgi.edu.tr`'yi alır, gerçek kurum `409 DOMAIN_TAKEN` alır.
- Domain doğrulanmış (T2) bir organizasyonun **adı serbest metin**; public sayfada alan
  adı gösterilmediğinden "Google (T2)" gibi yanıltıcı görüntü mümkün.
- `DomainAlreadyVerifiedError` kontrolü yalnız `verification_level == "T2"` arıyor
  ([organization.py:278](backend/app/services/organization.py#L278)); T3/T4'e yükseltilmiş
  bir organizasyonun alanı başka org tarafından yeniden doğrulanabilir.
- Ücretsiz e-posta listesi yalnız 4 alan (gmail/hotmail/outlook/yahoo).

### GUV-10 — Kayıtta zamanlama ile e-posta numaralandırma · ORTA · [KOD]

[auth.py:128-160](backend/app/services/auth.py#L128-L160): yeni kullanıcı yolu Argon2
hash hesaplıyor (~50-100 ms), mevcut e-posta yolu hesaplamıyor. Yanıt süresi farkı
e-postanın kayıtlı olduğunu sızdırır. Çözüm: mevcut e-posta yolunda da sahte hash hesapla.

### GUV-11 — Kimlik uçlarında hız sınırı yok · ORTA · [KOD]

`/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/verify-email` için
IP/hesap bazlı hız sınırı yok. `forgot-password` her çağrıda outbox'a e-posta satırı
yazar → e-posta bombardımanı + outbox şişmesi (OPS-01 ile birleşince kuyruk tıkanması).
GUV-01 düzeltilse bile IP bazlı sınır olmadan hesap kilitleme DoS'a dönüşür.

### GUV-12 — Kanıt kaydı depodaki dosyayla bağlanmıyor · ORTA · [KOD]

[backend/app/services/evidence.py](backend/app/services/evidence.py) `POST /evidence`:
- Nesnenin MinIO'da gerçekten var olduğu, boyutunun/tipinin eşleştiği kontrol edilmiyor.
- `mime_type` allowlist'e göre doğrulanmıyor (upload-url'de doğrulanıyor, kayıtta değil);
  `size_bytes` üst sınırı yok.
- Aynı `storage_key` sınırsız kez kaydedilebilir (unique yok).
- Magic-byte kontrolü (CLAUDE.md kuralı) hiçbir yerde yok — tarama worker'ı yok (IS-07).
- Hız sınırı süreç içi bellekte ([storage.py:33](backend/app/services/storage.py#L33)):
  çoklu worker'da etkisiz, anahtarlar hiç temizlenmiyor (yavaş bellek sızıntısı).

### GUV-13 — Toplu hatırlatma ile outbox şişirme · ORTA · [KOD]

[backend/app/services/reminder.py](backend/app/services/reminder.py): `template` serbest
metin → `reminder.<her şey>` topic'i; `engagement_ids` listesinin üst sınırı yok, tekrar
koruması yok. Handler yok → her satır kuyruğu kalıcı tıkar (OPS-01).

---

## 5. Yetkilendirme modeli bulguları

### AUTHZ-01 — Tek `kind` modeli çoklu rollü kullanıcıyı bozuyor · YÜKSEK · [KOD]

**Konum:** [backend/app/api/deps.py:43-54](backend/app/api/deps.py#L43-L54),
[backend/app/services/authorization.py:52-235](backend/app/services/authorization.py#L52-L235)

Kayıtta **her kullanıcıya talent profili açılıyor**; yani her koordinatör ve
organizasyon üyesi aynı zamanda talent. `Principal.kind` docstring'i "yalnız gösterim
içindir, yetki kararı `kind`'a dayanmamalı" diyor; oysa `can()`, `scoped_organizations`,
`scoped_institutions`, `scoped_engagements`, `scoped_evidence`, tüm geçiş tablosu ve
tanıklık kontrolü `kind`'a dayanıyor. Sonuçlar:

- Organizasyon ADMIN'i aynı zamanda bir kurumda koordinatörse `kind=COORDINATOR` →
  `GET /organizations/{id}` 404, `/me` içinde organizasyon listesi boş, org davet/doğrulama
  yapamaz.
- Kurum üyesi olan talent kendi engagement/kanıtlarını göremez (GUV-02'nin kökü).
- Talent, kendi organizasyonunu açarsa (serbest) talent işlevlerini kaybeder.

**Öneri:** Kapsam sorgularını `kind` yerine üyelik listelerinin **birleşimi** ile kur
(`talent_id == X OR organization_id IN (...) OR institution_id IN (...)`); işlem
yetkisini kaynak bazlı kontrol et. Bu, yetkilendirme mantığı değişikliği olduğundan
onay + `pytest tests/authorization -q` tamamı gerektirir.

### AUTHZ-02 — `INST_ADMIN` hiçbir geçişi yapamıyor · KRİTİK · [CANLI]

**Canlı kanıt:** Seed'de `institution_members` tablosunda 5 satır var, **5'i de `ADMIN`**,
`COORDINATOR` hiç yok (`baslat.bat`'ın ekrana yazdığı "Kurum admin: kurum1-admin@seed.local"
hesapları). Bu hesaplarla `PENDING_APPROVAL → ACTIVE` onayı ve tanıklık **403/404 döner**.
Seed'deki 15 VERIFIED engagement API ile değil, seed betiğinin doğrudan yazmasıyla oluştu;
yani demo senaryosunun koordinatör adımı bugünkü haliyle canlı gösterilemez.


[engagement.py:297-335](backend/app/services/engagement.py#L297-L335): T2/T3/T6/T5
yalnız `principal.kind == "COORDINATOR"` kabul ediyor. Endpoint docstring'i
"COORDINATOR/INST_ADMIN" diyor. Kurum admin'i onay veremiyor, tanıklık veremiyor
(attestation da yalnız COORDINATOR). Bir kurumda admin, diğerinde koordinatör olan
kişi `kind=INST_ADMIN` olduğu için hiçbirinde onay veremez.

Ek tutarsızlık: login yanıtındaki `role` ([auth.py summarize_role](backend/app/services/auth.py))
COORDINATOR'ı INST_ADMIN'in önüne koyuyor; `get_current_principal` tersini yapıyor.
Frontend'in gördüğü rol ile backend'in uyguladığı rol farklı olabilir.

### AUTHZ-03 — Durum makinesi dokümandan sapmış · ORTA · [KOD]

`docs/STATE_MACHINE.md` ile kod karşılaştırması:

| Geçiş | Doküman | Kod |
|---|---|---|
| T4 `DRAFT→ACTIVE` (kurumsuz) | Org üyesi | **Yok** → `institution_id` NULL engagement DRAFT'ta sonsuza dek kalır; tanıklıktaki "kurumsuz → ORG_ADMIN" dalı ölü kod |
| T5 `ACTIVE→PENDING_EVALUATION` | TALENT veya ORG:SUPERVISOR | ORG üyesi/admin **veya COORDINATOR**; **TALENT yapamıyor** |
| T8 kurumsuz | ORG:SUPERVISOR | ORG_ADMIN |
| T9/T10 DISPUTED | "vakit kalırsa" | Yok (bilinçli) |
| Tanıklık kriter 1 "karşılıklı onay" | İki yönlü değerlendirme | Kontrol edilmiyor; yalnız ORG_TO_TALENT yeterli ([attestation.py:102](backend/app/services/attestation.py#L102)) |

Ayrıca DRAFT'taki bir engagement'ı iptal/silme yolu yok; REJECTED'tan yeniden gönderme yok.

### AUTHZ-04 — Ağ çağrısı açık transaction içinde · ORTA · [KOD]

[organization.py verify_domain](backend/app/services/organization.py): DNS sorgusundan
önce `session.commit()` yapılmış (iyi niyet), ama hemen ardından
`org.domain_verification_token` okunurken ORM yeni transaction açıyor → DNS (3 sn'ye kadar)
açık transaction içinde. CLAUDE.md "ağ çağrısı asla açık transaction içinde" kuralı.

---

## 6. İş kuralı / fonksiyonel bulgular

### IS-01 — Public doğrulama linki ve public profil deneyimleri hiç çalışmaz · KRİTİK · [CANLI]

- `generate_public_token()` ([verified_experience.py:15](backend/app/services/verified_experience.py#L15))
  tanımlı ama **hiçbir yerden çağrılmıyor**; kendi docstring'i "YERINDE kalmış" diyor.
- VerifiedExperience her zaman `visibility="PRIVATE"` oluşuyor
  ([attestation.py:315](backend/app/services/attestation.py#L315)) ve görünürlüğü
  değiştiren **uç yok**.
- Sonuç: `GET /public/v/{token}` gerçek veride **her zaman 404**; `GET /public/talents/{slug}`
  deneyim listesini **her zaman boş** döner.
- DB kanıtı: 15 VerifiedExperience, `public_token` dolu **0**, `PUBLIC` **0**.

Bu, jüriye gösterilecek son halkanın ("doğrulanmış deneyim paylaşılabilir") tamamen
kopuk olduğu anlamına geliyor.

### IS-02 — COMPETENCE hiçbir zaman verilemez · KRİTİK · [KOD]

[attestation.py:107-114](backend/app/services/attestation.py#L107-L114): süre kriteri
`started_on`/`ended_on` boşsa downgrade ediyor. Bu alanları set eden **hiçbir API yok**
(`POST /engagements` almıyor, PATCH ucu yok); yalnız `scripts/seed.py:608` doğrudan
yazıyor. Seed dışındaki her tanıklık `PARTICIPATION` + `ENGAGEMENT_DURATION_BELOW_THRESHOLD`
olur; public sayfada tarih alanları hep boş görünür.

**Seed de COMPETENCE göstermiyor [CANLI]:** DB'deki 15 tanıklığın **15'i `PARTICIPATION`**,
hepsinde `ATTESTOR_NOT_VERIFIED_SUPERVISOR` — seed'deki 5 organizasyonun 5'i de `T1`.
Demo'da "COMPETENCE" rozetini göstermek için seed organizasyonlarından en az biri `T2+`
olmalı.

### IS-03 — Engagement yaşam döngüsünde kör noktalar · YÜKSEK · [KOD]

- T4 yok (AUTHZ-03) → kurumu olmayan talent hiçbir zaman ilerleyemez.
- Görev (`engagement_tasks`) durumu değiştirilemiyor (PLANNED→DONE ucu yok), `completed_at`
  hiç dolmuyor.
- Talent T5'i yapamıyor; teslim yaptıktan sonra organizasyonun harekete geçmesini beklemek
  zorunda.
- `reason` alanı her geçişte üzerine yazılıyor (T1'de verilen reason, T3 reddetme gerekçesini
  silebilir); uzunluk sınırı yok.

### IS-04 — Frontend geçiş listesi backend'le uyuşmuyor · YÜKSEK · [KOD]

[frontend/lib/api/engagements.ts:69-76](frontend/lib/api/engagements.ts#L69-L76):
`PENDING_EVALUATION: []` — değerlendirme sonrası durumlar (`EVALUATED`, `VERIFIED`,
`DISPUTED`, `RESOLVED`) tipte ve etiket sözlüğünde yok. Rol bilgisi `/me`'de olmadığı için
her kullanıcıya her aday geçiş düğmesi gösteriliyor; yanlış rol 403 ile öğreniliyor.

### IS-05 — Tanıklık ve değerlendirmede tutarsızlıklar · ORTA · [KOD]

- Tanıklıkta `skill_id` geçersizse **sessizce yok sayılıyor** (değerlendirmede 422 dönüyor);
  ayrıca skill'in `ACTIVE` olup olmadığına bakılmıyor.
- Tanıklıkta kurum varsa tanıklığı **koordinatör** veriyor ama kayda
  `attestor_org_id = engagement.organization_id` yazılıyor → public sayfada "tanıklık eden
  organizasyon" gerçekte o organizasyon olmayan birinin eylemi olarak görünüyor.
- Değerlendirme yükünde `criterion`, `comment`, `private_note`, `items` için üst sınır yok
  (büyük gövde ile DB şişirme).

### IS-06 — Skill sinyali ve iddia (claim) tutarsızlıkları · ORTA · [KOD]

- Skill iddiası silinince (`DELETE /talents/me/skills/...`) SELF_CLAIM sinyali kalıyor
  (append-only); yeniden eklenince ikinci sinyal oluşuyor. Silinen iddia sinyallerde yaşamaya
  devam ediyor.
- `GET /talents/me/signals/` her sinyal için `attested_by: None` dönüyor
  ([skill_signal.py](backend/app/services/skill_signal.py)) — organizasyon tanıklı sinyaller
  bile "kimse tanıklık etmedi" gibi görünüyor.
- Skill MERGE edilince mevcut iddia/sinyaller hedefe yönlenmiyor (DOMAIN.md §3.5 "sorgular
  hedefe yönlenir" diyor); `parent_id` döngüsü (A→B→A) engellenmiyor.

### IS-07 — Kanıt yaşam döngüsü yarım: tarama yok, indirme hep 409 · KRİTİK (demo) · [KOD]

- `POST /evidence` `evidence.scan_requested` outbox satırı yazıyor; bu topic için **handler
  yok** → `scan_status` sonsuza dek `PENDING` → `GET /evidence/{id}/download-url` **her zaman
  409 SCAN_NOT_CLEAN**. Yüklenen hiçbir kanıt hiçbir zaman indirilemez.
- Talent'ın kendi kanıtlarını listeleyeceği `GET /evidence` ucu yok; frontend bu yüzden
  localStorage kullanıyor (ENT-02'nin kök nedeni).
- Kanıt silme ucu yok (30 gün soft delete modelde var, uçta yok).

### IS-08 — E-posta doğrulama akışı fiilen kapalı · YÜKSEK · [CANLI]

- 31 kullanıcının **30'u doğrulanmamış** (seed kullanıcıları).
- `require_email_verified()` hiçbir uçta kullanılmıyor (önceki rapor #8) — doğrulanmamış
  kullanıcı her şeyi yapabiliyor.
- Doğrulama linkini yeniden gönderme ucu yok; 24 saat içinde tıklanmazsa kullanıcı kalıcı
  doğrulanmamış kalır.
- OPS-01/OPS-02 yüzünden link zaten hiç ulaşmıyor.

### IS-09 — Profil güncellemede eksikler · ORTA · [KOD]

[backend/app/api/me.py:155-208](backend/app/api/me.py#L155-L208):
- `public_slug` biçim doğrulaması yok (boşluk, `/`, Unicode, tek karakter kabul);
  eşzamanlı iki istekte unique ihlali 500'e düşer.
- `None` gönderilen alan yok sayılıyor → kullanıcı başlık/şehir/slug'ı **silemiyor**.
- `full_name` güncellenemiyor.

### IS-10 — Kurum bağlanma talebi arayüzden kullanılamaz · ORTA · [KOD]

Koordinatörün bekleyen talepleri görmesini sağlayan liste ucu yok; onay ucu `request_id`
istiyor. Reddetme ucu yok. Talent kendi taleplerini göremiyor. Frontend'de ekran yok.
Pratikte talent'ı kuruma bağlamanın tek yolu seed.

### IS-11 — Admin doğrulama kuyruğu hiç boşalmaz · ORTA · [KOD]

"Reddet" = seviyeyi değiştirmeden aynı değeri göndermek; kuyruk kriteri (T2 + `legal_id`)
değişmediği için reddedilen organizasyon kuyrukta kalmaya devam eder. Ayrıca her çağrıda
`verified_at` güncelleniyor (düşürmede bile). `note` serbest metni audit metadata'sına
yazılıyor (PII kontrolü yalnız anahtar adına bakıyor).

---

## 7. Entegrasyon, operasyon, veri, test ve bağımlılık bulguları

### ENT-01 — Zincirin yarısı için arayüz yok · KRİTİK · [KOD]

Frontend'in çağırmadığı uçlar (§3): engagement oluşturma, görev, teslim, tanıklık, geri
çekme, kanıt kaydı/indirme, kurum/organizasyon oluşturma, üye davet, bağlanma talebi/onay,
hatırlatma, alan adı doğrulama. `ACTIVE → PENDING_EVALUATION` en az bir teslim gerektiriyor
ama teslim ekranı yok → **seed dışı hiçbir engagement arayüzden değerlendirmeye ulaşamaz**.
Demo, ya seed verisiyle ya da Swagger (`/docs`) üzerinden yapılabilir durumda.

### ENT-02 — Değerlendirme ve kanıt yükleme mock'ta (önceki rapor #1, #2 — hâlâ açık) · KRİTİK

`frontend/lib/api/evaluation.ts` her koşulda localStorage; `evidence.ts`'de
`USE_MOCK_UPLOAD_URL = true`, `USE_MOCK_STORAGE_UPLOAD = true`, adım 3 koşulsuz mock.
Kullanıcı "gönderildi" görür, backend'e hiçbir şey ulaşmaz. `private_note` localStorage'da
düz metin (önceki rapor #4).

### ENT-03 — Oturum yenilemeden sonraki ilk yazma isteği 403 · KRİTİK · [KOD]

**Konum:** [frontend/lib/api/client.ts:116-188](frontend/lib/api/client.ts#L116-L188)

`apiFetch` CSRF başlığını istek başında bir kez okuyup `options`'a koyuyor. 401 →
`/auth/refresh` → backend **yeni** `csrf_token` cookie'si yazıyor → retry aynı `options`
ile (**eski** CSRF başlığı) gidiyor → `403 CSRF_FAILED`. Access token 15 dakikada dolduğundan,
sayfada 15 dakikadan uzun kalan her kullanıcının ilk POST/PATCH/DELETE'i başarısız olur
(değerlendirme formu, profil kaydı, geçiş düğmesi). Retry sırasında başlık yeniden
okunmalı.

### ENT-04 — `EVALUATED`/`VERIFIED` durumları arayüzde tanımsız · YÜKSEK · [CANLI]

`EngagementStatus` tipi ve `messages/tr.json` `calismalar.status` sözlüğü 6 durum içeriyor.
Seed'deki 15 engagement'ın tamamı `VERIFIED` → çalışmalar listesinde durum etiketi boş/
`undefined` görünür. Demoda ilk açılan ekran.

### ENT-05 — `/me` rol bilgisi dönmüyor; admin linkleri herkese görünüyor · YÜKSEK · [KOD]

- `GET /me` `is_platform_admin`, rol, `email_verified` dönmüyor. Frontend rol bazlı UI
  yapamıyor (engagements.ts dosya başında da "BACKEND GAP" olarak not düşülmüş).
- [frontend/components/app-shell.tsx:137-142](frontend/components/app-shell.tsx#L137-L142):
  "Kurum Doğrulama" ve "Yetkinlik Yönetimi" linkleri **her oturum açmış kullanıcıya**
  gösteriliyor; tıklayınca 404. Link metinleri koda gömülü (CLAUDE.md "UI metni koda
  gömülmez" kuralı ihlali).
- *Ekip gözlemi (2026-09-28):* sayfanın altındaki bu iki bağlantı rol ayrımı yapılmadan
  öğrenciye de görünüyor. **Veri güvenliği açısından sorun yok** — backend her istekte
  `is_platform_admin` kontrolünü ayrıca yapıyor ve yetkisiz isteğe 404 dönüyor. Sorun
  arayüzde: öğrenci tıklarsa boş/hata veren sayfaya düşer. Yetkiyle ilgili bir arayüz
  değişikliği olduğu için sorulmadan dokunulmadı. Düzeltme: `/me` yanıtına
  `is_platform_admin` eklenmeli, linkler yalnız admin'e gösterilmeli, metinler
  `messages/tr.json`'a taşınmalı (bkz. `HATA_DUZELTME_PROMPT.md` B-02).

### ENT-06 — Sondaki `/` yüzünden 307 yönlendirmesi · ORTA · [CANLI]

`GET /talents/me/signals` ve `/talents/me/verified-experiences` backend'de `"/"` ile
tanımlı → frontend'in çağırdığı yol **307** alıyor (canlı doğrulandı). Yerelde tarayıcı
takip ediyor; reverse proxy/HTTPS arkasında `Location` http şemasıyla dönerse mixed-content
hatasına düşer. Aynı durum `POST /institutions/` ve `POST /organizations/` için tersine
geçerli (sonda `/` olmadan çağrılırsa 307 → POST gövdesi tarayıcıya göre kaybolabilir).

### ENT-07 — Üretim dağıtımında cookie/CSRF modeli kırılır · ORTA (dağıtım riski) · [ŞÜPHE]

Cookie'ler `Domain` belirtilmeden yazılıyor. Frontend ve API farklı alt alan adlarında
(`app.x` / `api.x`) yayınlanırsa: (a) `document.cookie` `csrf_token`'ı okuyamaz → tüm
yazma istekleri 403; (b) Next middleware `access_token`'ı göremez → her korumalı sayfa
girişe yönlenir. Yerelde `localhost` ortak olduğu için görünmüyor. Dağıtım ya tek origin
(reverse proxy ile `/api`) ya da `Domain=.x` gerektirir — deploy planında karar verilmeli.

### OPS-01 — Outbox worker: hiç çalışmıyor + kalıcı tıkanma · KRİTİK · [CANLI]

**Konum:** [backend/app/workers/outbox_worker.py](backend/app/workers/outbox_worker.py)

1. `__main__` **tek batch** işleyip çıkıyor; `outbox_poll_interval_seconds` hiç
   kullanılmıyor. `baslat.bat` worker'ı hiç başlatmıyor.
2. Handler'ı olmayan topic'ler (`evidence.scan_requested`, `engagement.pending_approval`,
   `attestation.created`, `email.organization_member_invited`, `reminder.*`) seçiliyor ama
   işlenmiyor ve `attempts` artmıyor ([satır 74](backend/app/workers/outbox_worker.py#L74)).
   Sorgu `ORDER BY created_at LIMIT 10` olduğundan, kuyruğun başında 10 handler'sız satır
   biriktiği an **worker kalıcı olarak aynı 10 satırı seçer; hiçbir e-posta bir daha
   gönderilmez.**
3. DB'de şu an: `email.verify_email` 30, `engagement.pending_approval` 15,
   `attestation.created` 15 işlenmemiş satır. Yeni bir satır ekleyen worker testleri tam
   bu yüzden başarısız (TEST-01).
4. `email.duplicate_registration_attempt` SMTP modunda `TODO` → e-posta gitmeden "işlendi"
   işaretleniyor.
5. İlk satırın commit'i batch'in tüm `FOR UPDATE` kilitlerini bırakıyor → çoklu worker'da
   `SKIP LOCKED` garantisi ilk satırdan sonra geçersiz.
6. Her e-posta için yeni `create_engine` açılıyor (`_resolve_user_email`).
7. Hata logunda `str(e)` yazılıyor — SMTP istisnaları alıcı adresini içerebilir (PII).

**Öneri:** Döngülü worker (poll interval), handler'sız topic'leri sorgu dışında bırakmak
(`topic IN handlers`), eksik handler'ları yazmak ya da o topic'leri üretmemek, `baslat.bat`'a
worker penceresi.

### OPS-02 — E-posta linkleri 404 sayfasına gidiyor · KRİTİK · [KOD]

[outbox_worker.py:187](backend/app/workers/outbox_worker.py#L187) `/verify-email?token=`,
[satır 215](backend/app/workers/outbox_worker.py#L215) `/reset-password?token=` üretiyor.
Frontend sayfaları `/e-posta-dogrula` ve `/sifre-sifirla`; `next.config.ts`'de yönlendirme
yok. Şifre sıfırlama ve e-posta doğrulama linkleri **not-found** sayfasına düşer.

### OPS-03 — MinIO bucket'ı yok, MinIO sağlıksız · KRİTİK · [CANLI]

- `yetkin360-evidence` bucket'ını oluşturan kod/betik yok (`create_bucket` aranınca yalnız
  botocore iç kodu çıkıyor). Taze kurulumda presigned POST `NoSuchBucket` ile düşer.
- `docker compose ps`: `yetkin360-minio-1 ... (unhealthy)`. Healthcheck `curl` kullanıyor;
  `cgr.dev/chainguard/minio` imajında `curl` olmaması muhtemel [ŞÜPHE]. İmaj `:latest`
  ile sabitlenmemiş.
- `upload-url` yalnız `EndpointConnectionError/ConnectTimeoutError` yakalıyor; bucket yok,
  yetki hatası gibi `ClientError`'lar 500'e düşer.
- MinIO'da tarayıcıdan presigned POST için CORS ayarı yapılmamış [ŞÜPHE].

### OPS-04 — Hata yanıt biçimi tutarsız · ORTA · [CANLI]

docs/API.md §1.4 `{code, message, request_id}` diyor. Sapmalar:
- Tanımsız yol: `{"detail": "Not Found"}` (Starlette `HTTPException` handler'ı kayıtlı
  değil, canlı doğrulandı); 405 de aynı.
- `HTTPException(detail="...")` kullanan uçlar (kurum, organizasyon, verified-experiences,
  signals) `code: "HTTP_ERROR"` dönüyor; frontend hata koduna göre dallanamıyor.
- Engagement uçlarında `request_id: None`; `ApiError`'da her hata için yeni UUID üretiliyor
  ama loga yazılmıyor → destek için korelasyon yok.
- Yakalanmayan istisnalar (IntegrityError yarışları, GUV-07) düz 500.
- `/docs` ve `/openapi.json` üretimde de açık; `debug=True` varsayılan.

### VER-01 — Append-only kuralı DB'de eksik · ORTA · [KOD]

CLAUDE.md `evaluations` ve `verified_experiences`'ı append-only sayıyor; trigger yalnız
`audit_events`, `skill_signals`, `attestations` için var. Bu iki tablo DB seviyesinde
UPDATE/DELETE'e açık ("kısıtlar veritabanında olur" kuralı).

### VER-02 — Yanlış hata kodları · ORTA · [KOD]

- `POST /talents/me/skills`'te geçersiz `claimed_level` → DB CHECK ihlali → servis bunu
  "zaten eklenmiş" sanıp **409 ALREADY_CLAIMED** dönüyor. Pydantic'te `Literal` yok.
- `create_engagement`'ta geçersiz `institution_id` formatı `INSTITUTION_MISMATCH` (400);
  yetkisiz `kind` `TALENT_NOT_FOUND` (404) — hata ayıklamayı zorlaştırıyor.

### VER-03 — Zaman tipi kuralı ihlali · DÜŞÜK-ORTA · [KOD]

`engagement_tasks.due_at`, `completed_at`, `deliverables.submitted_at`
`mapped_column(nullable=...)` ile `DateTime(timezone=True)` olmadan tanımlı →
`timestamp without time zone` olma ihtimali yüksek (CLAUDE.md: `timestamptz`/UTC).
Migration'da doğrulanmalı [ŞÜPHE].

### TEST-01 — Test paketleri kırmızı · YÜKSEK · [CANLI]

**Backend (13 başarısız):** `test_outbox_worker.py` (9), `test_seed.py` (3),
`test_evaluation.py::...invalid_skill_id_in_item_422` (1). Ortak kök: testler seed'li
geliştirme DB'sine karşı koşuyor ve **global satır sayıyor** (ör. "30 TalentProfile
oluştu" — bunlar seed'in 30 kaydı; "15 SkillSignal" — seed'in sinyalleri) ya da outbox
kuyruğunun boş olduğunu varsayıyor. CI temiz DB kullandığı için muhtemelen geçiyor;
yerelde `baslat.bat` sonrası `pytest` kırmızı. Testler kendi oluşturdukları kayıtlara göre
filtrelemeli ya da ayrı test veritabanı kullanılmalı.

**Frontend (9 başarısız):** `lib/api/evaluation.test.ts` (6) — `engagements.ts` gerçek
backend'e bağlandı (3a791ff) ama bu testler hâlâ mock store'u varsayıyor, gerçek
`fetch` → `SessionExpiredError`. Ayrıca `evidence-upload-form.test.tsx`,
`evaluation-form.test.tsx`, `kurum/[id]/panel/page.test.tsx` (panelde beklenmeyen `<a>` —
ENT-05'teki koşulsuz admin linkleri).

**CI boşluğu:** `.github/workflows/ci.yml` frontend için `lint`, `typecheck`, `build`
koşuyor ama **`vitest` koşmuyor** — bu 9 kırık test CI'da görünmez.

### TEST-02 — Test fixture'ı üretimdeki rollback davranışını gizliyor · YÜKSEK · [KOD]

[backend/tests/conftest.py:43-48](backend/tests/conftest.py#L43-L48): `override_get_session`
oturumu **generator olmadan** döndürüyor. Üretimdeki `get_session` istisnada `rollback()`
yapıyor; test override'ı yapmıyor. Sonuç: "önce yaz, sonra hata fırlat" deseni (GUV-01'deki
kilitleme sayacı, DENIED audit kayıtları) testte **yeşil**, üretimde **kayıp**.
`test_login_locks_account_after_repeated_failures` bu yüzden geçiyor. Ayrıca
`get_current_user` da `X-Debug-User-Id` başlığıyla override ediliyor; gerçek cookie/JWT
yolu yalnız `test_auth_refresh_real_session.py`'de sınanıyor. Düzeltme: override'ı
üretimle aynı semantikte generator yap (istisnada savepoint'e rollback) ve kritik yazma-
sonra-hata yolları için gerçek bağımlılıkla en az bir test ekle.

### DEP-01 — Zafiyetli Python bağımlılıkları · YÜKSEK · [CANLI]

`pip-audit` (backend/requirements.txt):

| Paket | Sürüm | Bulgu | Düzeltme |
|---|---|---|---|
| `pyjwt` | 2.10.1 | PYSEC-2026-120, -175, -176, -177, -178, -179, PYSEC-2025-183 | 2.13.0 (biri için düzeltme yok) |
| `starlette` (fastapi 0.115.6 üzerinden) | 0.41.3 | PYSEC-2026-1941 | 0.47.2 → fastapi yükseltmesi gerekir |
| `pytest` | 8.3.4 | PYSEC-2026-1845 | 9.0.3 (yalnız geliştirme) |

`pyjwt` doğrudan kimlik doğrulama yolunda. Bağımlılık yükseltmesi onay gerektirir
(CLAUDE.md) ve tüm test paketiyle doğrulanmalı.

### DEP-02 — Frontend bağımlılık zafiyeti · ORTA · [CANLI]

`npm audit`: `next` içindeki `postcss <= 8.5.22` — 1 **high** (XSS/path traversal
advisory'leri), 1 moderate. Önerilen düzeltme `next@16.3.6` (kırıcı değişiklik). Build
zamanı bileşeni olduğu için çalışma zamanı etkisi sınırlı, ama açık kaynak repoda Dependabot
uyarısı olarak görünecek.

---

## 8. Düşük öncelikli bulgular

| ID | Konum | Bulgu |
|---|---|---|
| L-01 | `institution.py:120` | Kurum ADMIN'i başka admin'lerin (ve kendi) rolünü düşürebilir; son admin'i kaldırma koruması yok; üyelikten çıkarma ucu yok |
| L-02 | `organizations.py` | Organizasyon alan adı oluşturulduktan sonra değiştirilemez (PATCH yok); alan adı yoksa `verify-domain` 400 |
| L-03 | `auth.py` login/refresh | `SUSPENDED/DELETED` kullanıcıya login ve refresh yine token üretiyor (sonraki istekte 401 alsa da) |
| L-04 | `api/auth.py:33` | Cookie `max_age` sabit 15 dk / 30 gün; `settings` TTL'i değişirse JWT ile cookie ayrışır |
| L-05 | `public.py` | Public profil `talent_id` (iç UUID) döndürüyor; ORG üyesi bunu `POST /engagements`'ta kullanabilir (GUV-08). `/v/{token}` silinmiş (`deleted_at`) talent'ı filtrelemiyor |
| L-06 | `me.py` | `PATCH /talents/me` `updated_at`'i elle set ediyor; `TimestampMixin` ile çakışma riski |
| L-07 | `admin.py` | `limit`/`offset` sınırsız (`limit=1000000` kabul) |
| L-08 | `skill_signals.py:84` | Talent profili yoksa `401 "Unauthorized"` — kimliği doğrulanmış kullanıcıya 401 yanlış; verified-experiences aynı durumda 404 dönüyor |
| L-09 | `skill_claim.py`, `skill_signal.py`, `public.py` | N+1 sorgular (her claim/sinyal/attestation için ayrı `SELECT`) |
| L-10 | `skill.py` | `update_skill` `parent_id`'yi kaldıramıyor; MERGED skill DEPRECATED yapılabiliyor, `merged_into_id` kalıyor |
| L-11 | `main.py:22-28` | CORS `allow_methods=["*"]`, `allow_headers=["*"]` + credentials; origin listesi dar olduğu sürece sorun değil, ama `.env`'de `*` yazılırsa tehlikeli |
| L-12 | `core/deps.py:16` | Engine `pool_pre_ping` olmadan; DB yeniden başlarsa ilk istekler 500 |
| L-13 | `client.ts:28` | `csrf_token=` regex'i `xcsrf_token=` gibi adlarla da eşleşir; sınır eklenmeli |
| L-14 | `config.py:55` | `seed_admin_password` varsayılanı tahmin edilebilir (`DEGISTIR_admin_parola`); üretimde seed engeli dışında koruma yok |
| L-15 | repo kökü | `.mcp.json` izlenmiyor ve `.gitignore`'da da yok — içinde erişim anahtarı varsa yanlışlıkla commit edilebilir (içerik okunmadı) |
| L-16 | `security-scan` | detect-secrets 589 bulgu: büyük çoğunluğu migration revision hash'leri ve test parolaları (yanlış pozitif). Baseline güncellenmeli ki gerçek sızıntı gürültüde kaybolmasın |

---

## 9. Önceki rapordaki (2026-09-27) bulguların durumu

| Eski # | Bulgu | Durum |
|---|---|---|
| 1 | Evidence upload akışı mock | **Açık** → ENT-02; ayrıca backend tarafında IS-07 ve OPS-03 eklendi (mock kaldırılsa da akış çalışmaz) |
| 2 | Değerlendirme formu mock | **Açık** → ENT-02; bağlanınca GUV-04 devreye girer |
| 3 | `.env.example` `NEXT_PUBLIC_API_BASE_URL` `/api/v1` | **Doğrulanamadı** — bu denetimde `.env.example` okuma izni verilmedi; önceki tespite göre açık kabul edilmeli |
| 4 | localStorage'da `private_note` | **Açık** (ENT-02 ile birlikte kapanır) |
| 5 | PLAN.md senkronu | Önceki oturumda düzeltildi |
| 6 | Docker çalışmıyor | **Kapandı** — bu denetim canlı ortamda yapıldı. Yeni: MinIO `unhealthy` (OPS-03) |
| 7 | `require_email_verified()` kullanılmıyor | **Açık** → IS-08 |
| 8 | `test_seed.py` izolasyonu | **Açık ve genişledi** → TEST-01 (worker ve evaluation testleri de aynı kökten) |

---

## 10. Önerilen düzeltme sırası (teslim: 9 Ekim)

Her adım, önceki adım olmadan anlamsız olan işleri sona bırakacak şekilde sıralandı.

> **Uygulanabilir iş listesi, 2 kişilik iş bölümü, gün gün takvim ve her iş için hazır
> prompt'lar:** [HATA_DUZELTME_PROMPT.md](HATA_DUZELTME_PROMPT.md). Aşağıdaki sıra özet
> niteliğindedir; bağlayıcı olan o dosyadaki takvimdir.

**Faz A — Demo zinciri (öncelik 1, ~4-5 gün)**
1. OPS-03: bucket oluşturma (seed veya başlangıç betiği) + MinIO healthcheck.
2. OPS-01 + OPS-02: döngülü worker, handler'sız topic'lerin dışlanması, doğru frontend
   yolları, `baslat.bat`'a worker.
3. IS-07: tarama handler'ı (MVP: magic-byte kontrolü + `CLEAN`) ve `GET /evidence`.
4. ENT-02: mock'ları kaldır, gerçek uçlara bağla.
5. IS-02: engagement'a tarih girişi (oluşturma gövdesine `started_on/ended_on` ya da ayrı uç).
6. IS-01: tanıklıkta `public_token` üret + VerifiedExperience görünürlüğü ucu + profil
   ekranında paylaşım.
7. ENT-01: en az teslim (deliverable) ve tanıklık ekranları; engagement oluşturma formu.
8. ENT-03, ENT-04, ENT-05: CSRF retry, durum etiketleri, `/me`'ye rol + koşullu admin linki.

**Faz B — Güvenlik (öncelik 2, ~2-3 gün, onay gerektirir)**
9. GUV-01 (tek satırlık etki, en yüksek risk), GUV-06, GUV-07.
10. GUV-05 (revoke okuma filtreleri), GUV-04 (sinyal yönü).
11. AUTHZ-01 + GUV-02 (çoklu rol + davet/kabul) — **yetkilendirme değişikliği**:
    `pytest tests/authorization -q` tamamı zorunlu.
12. DEP-01 (pyjwt/fastapi yükseltmesi — bağımlılık onayı + tüm test paketi).

**Faz C — Hijyen (öncelik 3)**
13. TEST-01 (test izolasyonu + CI'ya `vitest`), OPS-04, VER-01, AUTHZ-02, AUTHZ-03,
    kalan ORTA/DÜŞÜK maddeler.

**Karar gerektiren maddeler (kullanıcıya/ekibe soru):**
- GUV-03: Organizasyon onayı zincire eklenecek mi, yoksa T1 downgrade + public'te seviye
  gösterimi MVP için yeterli mi?
- GUV-05: Geri çekilen tanıklık VerifiedExperience'ı nasıl etkilemeli (append-only istisnası
  mı, ayrı durum tablosu mu)?
- AUTHZ-03: T4 (kurumsuz işbirliği) MVP'ye girecek mi? Girmezse `institution_id` zorunlu
  yapılmalı.
- ENT-07: Üretimde tek origin mi, alt alan adı mı?

---

## 11. Doğrulanan, sorun olmayan alanlar

Tekrar sorgulanmasın:

- **404-not-403** tutarlı uygulanmış: engagement, evidence, attestation revoke, kurum,
  organizasyon, public uçlar; public sorgular tek `WHERE` ile (zamanlama farkı yok).
- **CSRF double-submit** tüm yazma uçlarında var (canlı: CSRF'siz transition → önce 401,
  sonra CSRF kontrolü; sıralama doğru).
- **Refresh token rotasyonu + aile iptali** doğru; reuse tespitinde iptal commit ediliyor.
- **Şifre sıfırlamada** tüm refresh token'lar `FOR UPDATE` ile iptal ediliyor.
- **Evidence `storage_key`** sunucuda `evidence/{talent_id}/{uuid}.{ext}` olarak üretiliyor;
  dosya adı anahtara girmiyor; kayıtta önek kontrolü var; presigned POST Content-Type ve
  boyuta bağlı.
- **`private_note`** hiçbir API yanıtında yok; audit/outbox PII guard'ı çalışıyor.
- **Append-only trigger'ları** `audit_events`, `skill_signals` (yalnız `superseded_by_id`
  set-once), `attestations` (yalnız `revoked_at`/`revoke_reason`) için doğru.
- **Ham SQL** yalnız migration'larda; ILIKE araması escape'li; bandit MEDIUM+ bulgu yok.
- **Optimistic locking** (`version`) transition ve tanıklıkta atomik `UPDATE ... WHERE
  version = ?` ile.
- Frontend `lint` 0 hata, `typecheck` temiz; `next` parametresi sanitize ediliyor.
