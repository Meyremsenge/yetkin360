# AUTHORIZATION.md — Yetkilendirme ve Test Matrisi

Kim, hangi kaynağa, hangi eylemi yapabilir ve yapamadığında **hangi HTTP kodunu**
alır.

**Kaynak:** `yetkin360-final-analiz.md` §15.1–15.4, §21.1–21.2.

> **Bu dosya doğrudan teste dönüşür.** §5'teki matrisin **her satırı bir
> pytest vakasıdır** (`tests/authorization/`). Satır eklemek = test eklemek.
> Yeni uç eklenip buraya satır yazılmazsa CI geçmez.

**İlgili dosyalar:**
- Uç listesi ve şemalar → [API.md](API.md)
- Kaynak alanları, `visibility` enum'ları → [DATABASE.md](DATABASE.md)
- Durum geçişi yetkileri → [STATE_MACHINE.md](STATE_MACHINE.md)
- Saldırı senaryoları, rate limit → [SECURITY.md](SECURITY.md)

---

## 1. Temel ayrım

| Soru | Ne zaman sorulur |
|---|---|
| **Authentication** — "Sen kimsin?" | Bir kez, oturum başında |
| **Authorization** — "Bunu yapabilir misin?" | **Her istekte, her nesne için** |

> **Kritik nokta: Yetkilendirme bir *rol* sorusu değil, bir *nesne* sorusudur.**
> "Bu kullanıcı koordinatör mü?" yetersizdir. Doğru soru: "Bu kullanıcı **bu**
> engagement'ın koordinatörü mü?"

Bu ayrımı kaçırmak BOLA'ya (Broken Object Level Authorization) yol açar —
OWASP API Security Top 10'da hem 2019 hem 2023'te **1 numara**, API
saldırılarının ~%40'ı. Otomatik tarayıcılar bunu **yakalayamaz**, çünkü
uygulama mantığı hatasıdır, girdi doğrulama hatası değil.
**Tek savunma sistematik testtir** — bu dosyanın var olma sebebi budur.

---

## 2. Aktörler (Principal)

Yetki, `User` üzerinde bir rol kolonundan değil, **bağlardan** çıkarılır.
Bir kullanıcı aynı anda birden fazla aktör olabilir (hem öğrenci hem kurum üyesi).

| Aktör | Nasıl belirlenir | Kapsam alanı |
|---|---|---|
| `ANONYMOUS` | Token yok | Yalnız `/public/*` |
| `TALENT` | `talent_profiles.user_id` | `talent_id` |
| `ORG_MEMBER` | `organization_members` (`role = MEMBER`) | `org_ids[]` |
| `ORG_ADMIN` | `organization_members` (`role = ADMIN`) | `org_ids[]` |
| `ORG_SUPERVISOR` | `engagements.supervisor_user_id` | Tek engagement |
| `COORDINATOR` | `institution_members` (`role = COORDINATOR`) | `institution_ids[]` |
| `INST_ADMIN` | `institution_members` (`role = ADMIN`) | `institution_ids[]` |
| `PLATFORM_ADMIN` | `users.is_platform_admin` | Global — **ama sınırsız değil** (§4) |
| `SUSPENDED` | `users.status = 'SUSPENDED'` | Hiçbir yazma |

`Principal` nesnesi her istekte bir kez kurulur ve isteğin tamamında taşınır:

```python
Principal(
    user_id, kind, talent_id=None,
    org_ids=[], org_admin_ids=[], institution_ids=[],
    is_platform_admin=False, is_suspended=False,
)
```

---

## 3. Multi-tenancy: uygulama seviyesinde zorunlu kapsamlama

**Karar: Uygulama seviyesinde zorunlu kapsamlama (scoping) + V2'de RLS'i
güvenlik ağı olarak ekle.**

| Yaklaşım | Değerlendirme |
|---|---|
| Ayrı veritabanı | ❌ Yüzlerce kurum için işletilemez; migration cehennemi |
| Ayrı şema | ❌ Aynı sorun; ayrıca **öğrenci birden fazla kuruma ait olabilir** — model uymuyor |
| `tenant_id` + uygulama filtresi | ✅ **Temel katman** |
| PostgreSQL RLS | ⚠️ İkinci katman — **MVP'de değil** |
| Sadece uygulama yetkilendirmesi | ⚠️ Tek başına yetersiz, MVP için kabul edilebilir |

**RLS neden MVP'de yok:** Erteleme gerekçesi performans değil (indekslenmiş
kolonda tipik %2-5), **operasyonel tuzaklardır:** RLS politikaları tablo
sahibine ve superuser'a uygulanmaz; PgBouncer kullanıldığında oturum
değişkenleri sızabilir; `current_setting()` politika içinde yanlış kullanılırsa
sorgu planı bozulur ve index kaybolur.

> **Yanlış kurulmuş RLS, olmayan RLS'ten daha tehlikelidir** — sahte güven yaratır.

**Doğru sıra:** Önce uygulama katmanını sağlam kur ve **test et**; sonra RLS'i
ikinci ağ olarak ekle.

### 3.1 Yapısal çözüm: `scoped_*()`

> **Güvenlik kuralı: Filtrelemeyi hatırlamak zorunda olmak, er ya da geç
> unutmak demektir. Varsayılanı güvenli yapın.**

Her sorgu bir `scoped_*()` fonksiyonundan geçer. **Çıplak `select(Model)`
kullanımı lint ile yasaklanır** (CLAUDE.md).

```python
def scoped_engagements(session, principal: Principal):
    q = select(Engagement)
    if principal.kind == "TALENT":
        return q.where(Engagement.talent_id == principal.talent_id)
    if principal.kind == "ORG_MEMBER":
        return q.where(Engagement.organization_id.in_(principal.org_ids))
    if principal.kind == "COORDINATOR":
        return q.where(Engagement.institution_id.in_(principal.institution_ids))
    raise Forbidden()
```

Bu desenin sonucu: **kapsam dışı kayıt sorgudan hiç dönmez** → doğal olarak
`404` üretir, `403` değil (§4.2).

### 3.2 Nesne seviyesi: `can()`

Liste kapsamlaması yetmez; tekil eylem için merkezî tek fonksiyon:

```python
def can(principal, action: str, resource) -> bool
```

`scoped_*()` **hangi kayıtları görebileceğini**, `can()` **o kayda ne
yapabileceğini** belirler. İkisi birden gerekir.

---

## 4. Karar matrisi

`RW` okuma+yazma · `R` okuma · `✗` erişim yok

| Kaynak | Talent (sahip) | Talent (diğer) | Org üyesi (ilgili) | Org üyesi (ilgisiz) | Koordinatör (kendi kurumu) | Admin |
|---|---|---|---|---|---|---|
| TalentProfile (public alanlar) | RW | R (`visibility`'ye göre) | R (eşleşmişse) | ✗ | R | R |
| TalentProfile (Keşfet dizini kartı — yalnız `PUBLIC` + `public_slug`) | R | R | R | R | R | R |
| TalentProfile (e-posta, tel) | RW | ✗ | R (**yalnız aktif engagement**) | ✗ | R | R |
| Evidence (`PRIVATE`) | RW | ✗ | ✗ | ✗ | ✗ | ✗ **(admin bile hayır)** |
| Evidence (engagement'a bağlı) | RW | ✗ | R | ✗ | R | R |
| Engagement | R + sınırlı W | ✗ | RW | ✗ | R + onay | R |
| Evaluation (yapılandırılmış) | R (gönderildikten sonra) | ✗ | RW (yazar) | ✗ | R | R |
| Evaluation (`private_note`) | **✗ asla** | ✗ | R (yalnız kendi kurumu) | ✗ | ✗ | R |
| Attestation | R | R (public ise) | RW (kendi yaptığı) | ✗ | R | R |

### 4.1 "Admin her şeyi görür" varsayımı yanlıştır

> Öğrencinin `PRIVATE` kanıtı (örneğin kişisel sağlık raporu içeren bir belge)
> platform admininin işi **değildir**. En az yetki ilkesi admin'e de uygulanır.

Admin erişimi gerçekten gerekiyorsa, **gerekçeli ve denetim kaydına yazılan bir
"break-glass" akışı** olmalıdır — sessiz erişim değil.

> ❓ AÇIK SORU: Break-glass akışının mekaniği final analizde tanımlanmamış
> (gerekçe zorunlu mu, ikinci onay gerekiyor mu, öğrenciye bildirim gidiyor mu).
> MVP'de admin için `PRIVATE` evidence erişimi **tamamen kapalıdır**; break-glass
> Faz 5'e bırakılır ([PLAN.md](../PLAN.md) 5.4).

### 4.2 404 mü 403 mü?

Ürünün en çok hata yapılan noktası. Kural:

| Durum | Kod | Sebep |
|---|---|---|
| Token yok / geçersiz | `401` | Henüz kimlik yok |
| Kaynak **kapsam dışı** (başka kiracının) | **`404`** | `403` "bu ID var ama senin değil" bilgisini sızdırır → enumeration |
| Kaynak yok | `404` | Ayırt edilemez olmalı |
| Kaynak **erişilebilir**, eylem yasak | `403` | Varlık zaten biliniyor, sızıntı yok |
| Kullanıcı askıya alınmış | `403` | Kimlik geçerli, yetki yok |

**Pratik ayrım:**
- `scoped_*()` sorgusundan kayıt dönmedi → **`404`**
- `scoped_*()` döndü ama `can()` `False` → **`403`**

Örnek: Öğrenci kendi engagement'ını görebilir (`scoped` döner) ama `VERIFIED`
yapamaz (`can()` `False`) → **`403`**. Başka kurumun engagement'ına dokunursa
`scoped` hiç döndürmez → **`404`**.

---

## 5. Test matrisi

> **Her satır bir testtir.** `tests/authorization/` altında yaşar.
> Matris **elle tek tek yazılmaz — parametrik üretilir**; her uç × her aktör
> kombinasyonu otomatik denenir.

Fixture'lar: iki kurum (Org A, Org B), iki öğrenci (Talent A, Talent B),
iki üniversite (Univ A, Univ B), her birinin kendi engagement'ı.

### 5.1 Kiracı izolasyonu — kurum

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| A1 | Org A üyesi | Org B engagement | Read | **404** |
| A2 | Org A üyesi | Org B engagement | Update | **404** |
| A3 | Org A üyesi | Org B evaluation | Read | **404** |
| A4 | Org A üyesi | Org B deliverable | Read | **404** |
| A5 | Org A üyesi | Org B üye listesi | Read | **404** |
| A6 | Org A üyesi | Org B attestation | Read | **404** |

### 5.2 Kiracı izolasyonu — öğrenci

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| B1 | Talent A | Kendi evidence | Update | **200** |
| B2 | Talent A | Talent B evidence (`PRIVATE`) | Read | **404** |
| B3 | Talent A | Talent B evidence | Update | **404** |
| B4 | Talent A | Talent B engagement | Read | **404** |
| B5 | Talent A | Talent B profili (`PRIVATE`) | Read | **404** |
| B6 | Talent A | Talent B profili (`PUBLIC`) | Read | **200** |
| B7 | Talent A | Kendi `skill_claims` | Delete | **204** |
| B8 | Talent A | Talent B `skill_claims` | Delete | **404** |

### 5.3 Alan seviyesi gizlilik

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| C1 | Talent A | Kendi evaluation'ı (`private_note`) | Read | **403 / alan cevapta yok** |
| C2 | Org üyesi (kendi kurumu) | `private_note` | Read | **200** |
| C3 | Koordinatör | `private_note` | Read | **alan cevapta yok** |
| C4 | Talent A | Kendi evaluation'ı (gönderilmemiş) | Read | **404** |
| C5 | Talent A | Kendi evaluation'ı (gönderilmiş) | Read | **200** |
| C6 | Org üyesi (ilgisiz) | Talent A e-posta alanı | Read | **alan cevapta yok** |
| C7 | Org üyesi (aktif engagement) | Talent A e-posta alanı | Read | **200** |

> **C1 özel bir durumdur:** `private_note` için ayrı bir uç yoktur — alan,
> response şemasından **hiç çıkmaz**. Test, cevap gövdesinde anahtarın
> **yokluğunu** doğrular ([DOMAIN.md](DOMAIN.md) D9).

### 5.4 Eylem yetkisi (kaynak görünür, eylem yasak)

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| D1 | Talent A | Kendi engagement | `status → VERIFIED` | **403** (yalnız kurum+koordinatör) |
| D2 | Talent A | Kendi engagement | `status → ACTIVE` | **403** |
| D3 | Org üyesi | Kendi kurum engagement | Evaluate | **200** |
| D4 | Org üyesi (`MEMBER`) | Kurum üyesi silme | Delete | **403** (yalnız `ADMIN`) |
| D5 | Org üyesi (`MEMBER`) | `verify-domain` | Post | **403** (yalnız `ADMIN`) |
| D6 | Org üyesi (ilgisiz, aynı kurum) | Engagement değerlendirme | Post | **403** (yalnız supervisor) |
| D7 | Talent A | Kendi attestation'ı oluşturma | Post | **403** (kendi kendine tanıklık yok) |
| D8 | Org üyesi | Başkasının attestation'ını revoke | Post | **403** (yalnız tanıklığı yapan) |

### 5.5 Koordinatör

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| E1 | Koordinatör A | Kendi kurumu engagement | Read | **200** |
| E2 | Koordinatör A | Başka üniversite engagement | Read | **404** |
| E3 | Koordinatör A | Öğrenci `PRIVATE` evidence | Read | **404** |
| E4 | Koordinatör A | Kendi kurumu engagement | Onay geçişi | **200** |
| E5 | Koordinatör A | Başka üniversite dashboard | Read | **404** |
| E6 | Koordinatör A | Kendi kurumu olmayan öğrenci profili | Read | **404** |

### 5.6 Anonim (public uçlar)

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| F1 | Anonim | Public profil (`visibility = PUBLIC`) | Read | **200** |
| F2 | Anonim | `PRIVATE` profil | Read | **404** |
| F3 | Anonim | `INSTITUTION` profil | Read | **404** |
| F4 | Anonim | Doğrulama linki (geçerli token) | Read | **200** |
| F5 | Anonim | Doğrulama linki (iptal edilmiş) | Read | **410** |
| F6 | Anonim | Doğrulama linki (`visibility != PUBLIC`) | Read | **404** |
| F7 | Anonim | Herhangi bir `/api/v1/engagements/*` | Read | **401** |
| F8 | Anonim | Herhangi bir yazma ucu | Write | **401** |

> **F5 `410` istisnası:** İptal edilmiş doğrulama linki `404` değil **`410 Gone`**
> döner. Gerekçe: link bir zamanlar geçerliydi ve **paylaşılmış** olabilir —
> "hiç yoktu" demek yanıltıcıdır. Burada varlık sızıntısı zaten yok, çünkü
> token'ı bilen kişi onu meşru biçimde almıştır.

### 5.7 Platform admin ve askıya alma

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| G1 | Platform admin | Talent `PRIVATE` evidence | Read | **403** (break-glass hariç) |
| G2 | Platform admin | Kurum doğrulama seviyesi | Update | **200** |
| G3 | Platform admin | Attestation | Delete | **405 / yol yok** (append-only) |
| G4 | Askıya alınmış kullanıcı | Herhangi bir yazma | Write | **403** |
| G5 | Askıya alınmış kullanıcı | Kendi profili | Read | **200** |
| G6 | E-postası doğrulanmamış kullanıcı | Herhangi bir yazma | Write | **401** `EMAIL_NOT_VERIFIED` |

### 5.8 Kendi kendine tanıklık (anti-abuse)

[DOMAIN.md](DOMAIN.md) D2 kuralının testleri:

| # | Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|---|
| H1 | Hem Talent A hem Org A yetkilisi olan kullanıcı | Talent A için attestation | Post | **403** |
| H2 | Org A üyesi | Kendisi supervisor olmadığı engagement için attestation | Post | **403** |
| H3 | T1 kurum üyesi | `COMPETENCE` attestation | Post | **201 ama `PARTICIPATION`'a düşürülmüş** |
| H4 | 30 günden yeni kurum | `COMPETENCE` attestation | Post | **201 ama düşürülmüş** (cooling period) |

> **H3 ve H4 yetki hatası değildir** — istek başarılı olur ama `claim_type`
> düşürülür. Test, dönen `claim_type` alanını **ve** `downgrade_reasons`
> içeriğini doğrular ([API.md](API.md) §2.8).

---

## 6. CI kuralı

> **Yeni bir uç eklendiğinde, yetkilendirme testi olmadan CI geçmez.**

Bu bir niyet beyanı değil, **otomatik kontroldür**: CI, kayıtlı uç sayısı ile
yetkilendirme testi kapsamını karşılaştırır; kapsanmamış uç varsa build kırılır.

| Kural | |
|---|---|
| Her uç için **en az bir pozitif** test | Yetkili aktör erişebiliyor mu |
| Her uç için **en az bir negatif** test | Başka kiracı erişemiyor mu (**zorunlu**) |
| Çalıştırma | `pytest tests/authorization -q` |
| Ne zaman | Yetkilendirme/kimlik değişikliğinde **tamamı** (CLAUDE.md doğrulama matrisi) |

### 6.1 E2E izolasyon senaryosu

Matristen bağımsız, tek bir bütünsel test (final analiz §21.3 Senaryo 2):

> İki kurum, iki öğrenci, iki üniversite oluştur → her aktör diğerinin **her**
> kaynağını denesin → **hepsi 404.**

Bu test yeni kaynak türü eklendiğinde otomatik büyür; matris satırı yazmayı
unutan geliştiriciyi yakalayan son ağdır.

---

## 7. Uç bazlı yetki özeti

[API.md](API.md)'deki her ucun yetki gereksinimi. Bu tablo, matris satırlarının
hangi uca karşılık geldiğini gösterir.

| Uç | Yetki | İlgili test |
|---|---|---|
| `POST /auth/*` | — (public) | F7, F8, G6 |
| `GET /me` | `AUTH` | — |
| `GET /talents/{id}` | `AUTH` + görünürlük filtresi | B5, B6, C6, C7, E6 |
| `PATCH /talents/me` | `TALENT` (kendi) | B1 |
| `*/talents/me/skills` | `TALENT` (kendi) | B7, B8 |
| `GET /talents/me/signals` | `TALENT` (kendi) | — |
| `GET /skills` | `AUTH` | — |
| `GET /discover/talents` | `AUTH` (e-posta doğrulanmış) — yalnız `PUBLIC` profiller | `tests/authorization/test_discover_authz.py` |
| `GET /discover/organizations` | `AUTH` (e-posta doğrulanmış) — yalnız `ACTIVE` kuruluşlar | `tests/authorization/test_discover_authz.py` |
| `POST /organizations` | `AUTH` | — |
| `GET /organizations/{id}` | `AUTH` | A5 |
| `POST /organizations/{id}/members` | `ORG:ADMIN` | D4 |
| `POST /organizations/{id}/verify-domain` | `ORG:ADMIN` | D5 |
| `GET /institutions/{id}/dashboard` | `INST:COORD` | E1, E5 |
| `GET /institutions/{id}/engagements` | `INST:COORD` | E2 |
| `POST /institutions/{id}/reminders` | `INST:COORD` | E2 |
| `POST /engagements` | `ORG:MEMBER` / `TALENT` | — |
| `GET /engagements/{id}` | taraflardan biri | A1, B4, E1, E2 |
| `POST /engagements/{id}/transitions` | duruma göre → [STATE_MACHINE.md](STATE_MACHINE.md) | D1, D2, E4 |
| `POST /engagements/{id}/tasks` | Kuruluş üyesi / koordinatör (doğrulanmış görev) · `TALENT` kendi çalışması (doğrulanmamış görev, sinyal yok) | A2, `tests/test_engagement_tasks.py` |
| `POST /engagements/{id}/tasks/{task_id}/verify` | Kuruluş üyesi / koordinatör; öğrenci (çoklu rolde dahi) `403`, kapsam dışı `404` | `tests/authorization/test_task_verification_authz.py` |
| `POST /engagements/{id}/deliverables` | `TALENT` (taraf) | A4 |
| `POST /evidence/upload-url` | `TALENT` | — |
| `POST /evidence` | `TALENT` | B3 |
| `GET /evidence/{id}/download-url` | erişim hakkı olan | B2, E3, G1 |
| `POST /engagements/{id}/evaluation` | `ORG:SUPERVISOR` / `TALENT` | A3, C1–C5, D3, D6 |
| `POST /engagements/{id}/attestations` | `ORG:SUPERVISOR` / `INST:COORD` | D7, H1–H4 |
| `POST /attestations/{id}/revoke` | tanıklığı yapan | A6, D8 |
| `POST /engagements/{id}/dispute` | `TALENT` / `ORG:MEMBER` | — |
| `GET /public/p/{slug}` | — | F1, F2, F3 |
| `GET /public/v/{token}` | — | F4, F5, F6 |
| `GET /admin/verification-queue` | `ADMIN` | — |
| `POST /admin/organizations/{id}/verification-level` | `ADMIN` | G2 |
| `POST /admin/organizations/{id}/verification-reject` | `ADMIN` | G2 |
| `GET /admin/fraud-queue` | `ADMIN` | — |
| `POST /admin/fraud-queue/{id}/resolve` | `ADMIN` | — |
| `GET /admin/fraud-flags/history` | `ADMIN` | — |
| `GET /admin/audit-events` | `ADMIN` | — |
| `GET /admin/skills` | `ADMIN` | — |
| `POST /admin/skills` | `ADMIN` | — |
| `PATCH /admin/skills/{id}` | `ADMIN` | — |
| `POST /admin/skills/{id}/deprecate` | `ADMIN` | — |
| `POST /admin/skills/{id}/merge` | `ADMIN` | — |
| `GET /admin/users` | `ADMIN` | — |
| `POST /admin/users/{id}/suspend` · `/reactivate` | `ADMIN` | G2 — kendi hesabı / son aktif admin → 409 |
| `GET /admin/organizations` | `ADMIN` | — |
| `POST /admin/organizations/{id}/suspend` · `/reactivate` | `ADMIN` | G2 |
| `GET /admin/institutions` | `ADMIN` | — |
| `POST /admin/institutions/{id}/verification-level` | `ADMIN` | G2 |
| `POST /admin/institutions/{id}/suspend` · `/reactivate` | `ADMIN` | G2 |
| `POST /complaints` | `TALENT` — özne kendisinin (değilse 404) | `tests/authorization/test_complaints_authz.py` |
| `GET /complaints` · `/complaints/assigned` | `AUTH` — yalnız kendi / kendisine atanmış | `test_complaints_authz.py` |
| `GET /complaints/{id}` | sahip; yetkili (gerekçe istendikten sonra); yükseltme sonrası hedefin COORDINATOR/ADMIN üyeleri — admin dahil diğerleri 404 | `test_complaints_authz.py` |
| `POST /complaints/{id}/explanation` | türetilmiş yetkili | `test_complaints_authz.py` |
| `POST /complaints/{id}/attachments*` · `GET …/attachments/{aid}` | yalnız sahip — yetkili eki **indiremez** (404) | `test_complaints_authz.py` |
| `GET /admin/complaints*` · `POST /admin/complaints/{id}/transitions` | `ADMIN` — ek indirmeleri audit'e yazılır; `PRIVATE` evidence erişimi değişmez (§4.1) | `test_complaints_authz.py` |

> ❓ AÇIK SORU: `POST /engagements` — engagement'ı kim başlatabilir? §34 hem
> kurumun hem öğrencinin oluşturabileceğini ima ediyor ama §10.2 durum makinesi
> okunduğunda netleşecek. Çelişki çıkarsa [STATE_MACHINE.md](STATE_MACHINE.md)
> esas alınır ve bu tablo güncellenir.
