# DOMAIN.md — Alan Modeli

Yetkin360'ın kavramsal modeli: hangi entity'ler var, alanları ne, birbirleriyle
nasıl ilişkililer, hangi iş kuralları geçerli.

**Kaynak:** `yetkin360-final-analiz.md` §7 (alan modeli), §8.2–8.4 (doğrulama eksenleri).
Bu dosya kararların **gerekçesini** tekrar etmez — gerekçe için final analize bakın.

**İlgili dosyalar:**
- Fiziksel şema, DDL, index, kısıt → [DATABASE.md](DATABASE.md)
- Engagement durum geçişleri → [STATE_MACHINE.md](STATE_MACHINE.md)
- Kim neye erişebilir → [AUTHORIZATION.md](AUTHORIZATION.md)
- Uç noktalar → [API.md](API.md)

---

## 1. Temel tasarım kararı: Claim / Evidence / Attestation

Ürünün tüm iddiası bu üç kavramın **ayrı** tutulmasına dayanır. Karıştırılırsa
kullanıcının yüklediği ekran görüntüsü ile kurumun imzası aynı statüde durur ve
güven hesabı kirlenir.

| Kavram | Tanım | Güven değeri |
|---|---|---|
| **Claim** | Özne kendi hakkında iddia ortaya atar ("Python biliyorum") | **Sıfır.** Yalnız profil UX'i için var |
| **Evidence** | İddiaya bağlanan yapıt: depo, doküman, çıktı, kayıt. **İçeriği** vardır | Kendi başına doğrulama **değildir** |
| **Attestation** | Kimliği doğrulanmış **üçüncü taraf**, belirli kapsam için, belirli tarihte, **adıyla** tanıklık eder | **Güvenin tek gerçek kaynağı** |

> **Değişmez kural:** Güven, Evidence'tan değil Attestation'dan gelir.
> Kurum doğrulaması bir "kanıt türü" değil, **kanıt üzerine bir tanıklıktır.**

> **Ürün dili kuralı (§8.3):** Sistem tanıklığın "doğru" olduğunu **iddia etmez.**
> Yalnız kimin, neyi, hangi dayanakla söylediğini değişmez biçimde kaydeder.
> UI metninde asla "bu kişi Python biliyor" denmez → "Acme A.Ş. bu kişinin Python'ı
> yeterli düzeyde kullandığını beyan etti" denir.

Zincir: `beyan → kanıt → tanıklık → doğrulanmış deneyim`
(`SkillClaim → Evidence → Attestation → VerifiedExperience`)

---

## 2. Entity listesi

### 2.1 MVP çekirdeği

| Entity | Rolü |
|---|---|
| `User` | Kimlik. Giriş yapan her aktör |
| `TalentProfile` | Öğrenci profili |
| `Institution` | Üniversite/bölüm — hem hakem hem ödeyen müşteri |
| `InstitutionMember` | Koordinatörler (`ADMIN` \| `COORDINATOR`) |
| `Organization` | Staj/proje veren kurum |
| `OrganizationMember` | Kurumda çok kullanıcı, rolle |
| `Skill` | Kontrollü sözlük (taksonomi). Platforma ait, kullanıcıya değil |
| `SkillClaim` | Kullanıcının beyanı |
| `Engagement` | Platformda takip edilen çalışma (staj, bitirme projesi) |
| `EngagementTask` | Hafif görev kaydı |
| `Deliverable` | Çıktı |
| `Evidence` | Yapıt |
| `Attestation` | Tanıklık — **en kritik entity** |
| `Evaluation` | Yapılandırılmış değerlendirme |
| `VerifiedExperience` | Döngünün değişmez çıktısı |
| `SkillSignal` | Türetilmiş yetkinlik kanıtı |
| `AuditEvent` | Denetim kaydı |

### 2.2 MVP'de OLMAYAN

Bunlar bilinçli olarak dışarıda. Eklemeden önce final analiz §39'a bakın.

| Entity | Karar | Neden |
|---|---|---|
| `Need` | ❌ Çıkar | Marketplace parçası. Staj zaten eşleşmiş geliyor → V2 |
| `Match` / `MatchReason` | ❌ Çıkar | Matching MVP'de yok → V2 |
| `Project` | ❌ Birleştir | `Engagement` ile aynı şey → §4 |
| `Experience` (ayrı) | ❌ Birleştir | `VerifiedExperience` yeterli |
| `Notification` | ⚠️ Minimal | Tek tablo; MVP'de in-app yeterli |
| `Message` / chat | ❌ Çıkar | Kapsam dışı |
| `Badge` / gamification | ❌ Çıkar | Kapsam dışı |
| `Assessment` | ❌ Çıkar | LinkedIn denedi, kapattı |
| `TrustScore` | ❌ **Asla** | Tek sayıya indirgemek manipülasyona davetiye (§8.6) |

---

## 3. Entity tanımları

Alan adları İngilizce; tipler kavramsaldır. Kesin DDL → [DATABASE.md](DATABASE.md).

### 3.1 User

Kimlik katmanı. Yetki taşımaz — yetki `TalentProfile` / `OrganizationMember` /
`Institution` bağlarından gelir.

```
User
  id, email (unique, citext), password_hash
  full_name
  email_verified_at (nullable)
  is_platform_admin (bool, default false)
  created_at, updated_at, deleted_at
```

**İş kuralları**
- E-posta doğrulanmadan hiçbir yazma işlemi yapılamaz.
- Bir `User` aynı anda hem öğrenci hem kurum üyesi olabilir — ama kendi kendini
  doğrulayamaz (§3.11 anti-abuse).

### 3.2 TalentProfile

```
TalentProfile
  id, user_id (unique)
  institution_id (nullable — platform dışı öğrenci için)
  student_no (nullable), department, enrollment_year
  headline, bio
  public_slug (unique, nullable)
  is_public (bool, default false)
  created_at, updated_at, deleted_at
```

**İş kuralları**
- `is_public = true` ise `public_slug` zorunlu.
- `institution_id` bağı **koordinatör tarafından onaylanmadan** kuruma ait sayılmaz
  (öğrenci kendi kendine üniversiteye bağlanamaz).

### 3.3 Institution

Ön araştırma dokümanında hiç yoktu; final analizin eklediği kritik entity.
Üniversite/bölüm hem **hakem** (engagement'ın gerçekliğini onaylar) hem
**ödeyen müşteri**.

```
Institution
  id, name, slug (unique)
  domain (nullable — ör. "example.edu.tr")
  type (UNIVERSITY | DEPARTMENT | VOCATIONAL_SCHOOL)
  parent_id (nullable — bölüm, üniversiteye bağlı)
  is_verified (bool)
  created_at, updated_at
```

**İş kuralları**
- Institution, `Engagement` üzerinde **onaylayan** taraftır — T4 güven seviyesi
  ancak koordinatör onayıyla oluşur (§3.11 madde 6).
- Institution kendi öğrencisi olmayan bir talent'ın engagement'ını onaylayamaz.

**Koordinatör rolü `InstitutionMember` üzerinden verilir** — `OrganizationMember`
ile simetrik bir tablo:

```
InstitutionMember
  id, institution_id, user_id
  role (ADMIN | COORDINATOR)
  UNIQUE (institution_id, user_id)
```

Bu entity §7.2 listesinde yer almıyordu ama §12.2 şemasında tanımlıdır —
şema esastır ([DATABASE.md](DATABASE.md) §2.1).

### 3.4 Organization ve OrganizationMember

```
Organization
  id, name, slug (unique)
  domain (nullable), tax_no (nullable), mersis_no (nullable)
  trust_tier (T1 | T2 | T3 | T4)
  verified_at (nullable), verified_by_user_id (nullable)
  created_at, updated_at, deleted_at

OrganizationMember
  id, organization_id, user_id
  role (OWNER | SUPERVISOR | MEMBER)
  invited_at, accepted_at (nullable)
  UNIQUE (organization_id, user_id)
```

**Güven kademeleri (§8.4)**

| Seviye | Kontrol | Otomasyon | Verdiği hak |
|---|---|---|---|
| `T1` | E-posta teyidi | Tam otomatik | Kurum oluştur, üye davet et |
| `T2` | Kurumsal domain (ücretsiz posta sağlayıcı reddedilir) + DNS TXT | Otomatik | `PARTICIPATION` tanıklığı |
| `T3` | MERSİS/vergi no + ticaret sicil + yetkili beyanı | Yarı-otomatik (admin onayı) | `COMPETENCE` tanıklığı |
| `T4` | Üniversitece "tanınan staj yeri" işareti | Koordinatör onayı | Tam güven, akreditasyon geçerli |

**MVP kapsamı:** T1 ve T2 otomatik çalışır ([PLAN.md](PLAN.md) 1.9).
T3 admin kuyruğu üzerinden (3.6). T4 koordinatör onayıyla (2.3).

### 3.5 Skill

> **Tanım: Skill, yetkinlik taksonomisindeki kontrollü bir kavramdır.
> Kullanıcıya ait değildir, platforma aittir.**

```
Skill
  id, slug (unique), name_tr, name_en
  category (LANGUAGE | FRAMEWORK | TOOL | DOMAIN | SOFT)
  parent_id (nullable — tek seviyeli hiyerarşi: FastAPI → Python)
  status (ACTIVE | MERGED | DEPRECATED), merged_into_id (nullable)
  is_curated (bool)
  created_at, updated_at
```

**İş kuralları**
- **Serbest metin skill'e MVP'de bile izin verilmez.** "Python", "python3",
  "Phyton" ayrı kayıt olursa hiçbir arama/agregasyon çalışmaz; sonradan
  temizlemek çok pahalıdır.
- Kullanıcı öneri gönderebilir; admin onaylar → `is_curated`.
- Hiyerarşi tek seviyeli. Tam skill grafı V3.
- `status = MERGED` ise `merged_into_id` zorunlu; sorgular merge hedefine yönlendirilir.

> ❓ AÇIK SORU: Seed skill sayısı — final analiz §7.3 "~300 küratörlü skill" diyor,
> [PLAN.md](PLAN.md) 1.10 "~150 skill" diyor. Hackathon süresi için 150 makul
> görünüyor ama bu final analizden bir sapma. Karar verilip iki dosya hizalanmalı.

### 3.6 SkillClaim

Kullanıcının kendi beyanı. Güven değeri sıfır ama profil UX'i için gerekli.

```
SkillClaim
  id, talent_id, skill_id
  self_level (nullable: BEGINNER | INTERMEDIATE | ADVANCED)
  note (nullable)
  created_at, updated_at, deleted_at
  UNIQUE (talent_id, skill_id) WHERE deleted_at IS NULL
```

**İş kuralları**
- Tek **mutable** kanıt entity'si. Geçmişi `skill_claim_history` ile tutulur (§6).
- Beyan silinse bile ondan türemiş `SkillSignal` kayıtları silinmez.

### 3.7 Engagement

> **Engagement = *olan şey*.** Belirli zaman aralığında, belirli taraflar
> arasında, platformda takip edilen çalışma. Staj, bitirme projesi, kısa proje —
> hepsi **tek entity**.

```
Engagement
  id, talent_id, organization_id
  institution_id (nullable — platform dışı işbirliği için)
  title, description
  kind (INTERNSHIP | CAPSTONE | SHORT_PROJECT | PART_TIME)
  status (bkz. STATE_MACHINE.md)
  started_at, ended_at (nullable)
  planned_hours (nullable)
  supervisor_user_id (nullable — kurum tarafı süpervizör)
  created_by_user_id
  created_at, updated_at
```

Durumlar, geçişler ve her geçişin ön koşulu → [STATE_MACHINE.md](STATE_MACHINE.md).

### 3.8 EngagementTask ve Deliverable

```
EngagementTask
  id, engagement_id
  title, description (nullable)
  status (PLANNED | IN_PROGRESS | DONE)
  due_at (nullable), completed_at (nullable)
  created_at, updated_at
  -- skill bağı: task_skills (n──n)

Deliverable
  id, engagement_id
  title, description
  submitted_by_user_id, submitted_at
  created_at, updated_at
```

**İş kuralları**
- `Deliverable` çıktının **kaydıdır**; dosyanın kendisi `Evidence` olarak bağlanır.
- Bir `Deliverable`'a en az bir `Evidence` bağlı olmalıdır (aksi halde tanıklık
  dayanaksız kalır).

### 3.9 Evidence

> **Tanım: Evidence, bir iddiaya bağlanan, doğrulanabilir bir kaynağı olan yapıttır.**

```
Evidence
  id, owner_talent_id
  kind (REPOSITORY | DOCUMENT | IMAGE | LINK | DELIVERABLE_REF | CERTIFICATE)
  uri (nullable) / storage_key (nullable)
  title, description
  engagement_id (nullable — platform içi mi dışı mı)
  visibility (PRIVATE | INSTITUTION | ORGANIZATION | PUBLIC)
  provenance (SELF_UPLOADED | PLATFORM_GENERATED | EXTERNAL_VERIFIED)
  content_hash              -- bütünlük
  created_at, deleted_at
```

**Kritik alan: `provenance`**

| Değer | Anlamı | Gösterim |
|---|---|---|
| `SELF_UPLOADED` | Kullanıcının yüklediği | En düşük güven; "beyan" olarak işaretlenir |
| `PLATFORM_GENERATED` | Platformda üretilmiş deliverable | Orta; zincire bağlı |
| `EXTERNAL_VERIFIED` | Kriptografik dış kanıt (GitHub OAuth vb.) | En yüksek (T5) |

> Kullanıcının yüklediği PDF ile platformda üretilmiş deliverable **asla aynı
> güven seviyesinde gösterilmez.**

**İş kuralları**
- `uri` veya `storage_key`'den **en az biri** dolu olmalı.
- Öğrencinin platform dışı kişisel projeleri buraya `SELF_UPLOADED` olarak girer —
  ayrı `Project` entity'si **yoktur** (§4).
- Dosya yükleme akışı → [SECURITY.md](SECURITY.md).

### 3.10 Attestation

Kimliği doğrulanmış üçüncü tarafın, belirli kapsam için, adıyla yaptığı tanıklık.
**Append-only.**

```
Attestation
  id
  subject_type (EVIDENCE | DELIVERABLE | ENGAGEMENT | SKILL_CLAIM)
  subject_id
  claim_type (PARTICIPATION | CONTRIBUTION | COMPETENCE | CONDUCT)
  attestor_user_id                     -- adıyla tanıklık; anonim yok
  attestor_org_id (nullable)
  attestor_institution_id (nullable)
  attestor_trust_tier (T1..T5)         -- tanıklık anında dondurulur
  statement (nullable)
  attested_at
  revoked_at (nullable), revoke_reason (nullable)
  created_at
```

**İki eksenli doğrulama (§8.2)** — tek merdiven yerine iki bağımsız eksen.

**Eksen 1 — Ne doğrulanıyor? (`claim_type`)**

| Tip | İfade | Doğrulanabilirlik |
|---|---|---|
| `PARTICIPATION` | "Bu kişi bu çalışmada yer aldı" | **Yüksek** — nesnel, kolay |
| `CONTRIBUTION` | "Bu çıktıyı bu kişi üretti" | **Orta** — ekip işinde zor |
| `COMPETENCE` | "Bu yetkinliği yeterli düzeyde kullandı" | **Düşük** — en değerli, en kırılgan |
| `CONDUCT` | "Zamanında/güvenilir çalıştı" | Orta — öznel ama tutarlı |

**Eksen 2 — Kim doğruluyor? (`attestor_trust_tier`)**

| Seviye | Attestor | Nasıl doğrulandı |
|---|---|---|
| `T0` | Kişinin kendisi | — (tanıklık sayılmaz) |
| `T1` | Doğrulanmamış kurum | Sadece e-posta |
| `T2` | Domain doğrulamalı kurum | Kurumsal e-posta domain kontrolü |
| `T3` | Kimlik doğrulamalı kurum | MERSİS/vergi no + yetkili teyidi |
| `T4` | T3 kurum + üniversite ortak onayı | İki bağımsız taraf |
| `T5` | Kriptografik dış kanıt | GitHub OAuth commit, imzalı credential |

Bir doğrulama ifadesi her zaman şu üçlüdür: **(Ne, Kim, Ne zaman)**

Örnek gösterim:
> **Python** — "Yeterli düzeyde kullandı" (COMPETENCE), *Acme Yazılım A.Ş.*
> (T3, MERSİS doğrulamalı) ve *XYZ Üniv. Bilg. Müh.* (T4 ortak onay) tarafından,
> **Ağu 2026**'da doğrulandı. Dayanak: 3 çıktı, 12 görev kaydı.

Bu, tek bir "Level 3" etiketinden kıyaslanamayacak kadar bilgilendiricidir ve
manipülasyona daha dayanıklıdır: kullanıcı seviyeyi değil, **kim olduğunu** görür.

### 3.11 COMPETENCE tanıklığının ön koşulları (§8.3)

`claim_type = COMPETENCE` geçerli sayılması için **hepsi** gerekli:

1. Bir `Engagement` var ve **tarafların ikisi de** onaylamış (öğrenci + kurum).
2. Engagement'ın süresi var (başlangıç/bitiş) ve minimum eşik üstünde
   (≥4 hafta **veya** ≥40 saat).
3. En az bir `Deliverable` var ve o yetkinliğe bağlanmış.
4. Attestor, **≥T2 doğrulanmış kurumda doğrulanmış üye** ve öğrencinin
   süpervizörü olarak Engagement'a bağlı.
5. Attestor tanıklığı **adıyla** yapıyor (anonim tanıklık yok); kayıt değişmez.
6. (Üniversite bağlamında) Koordinatör engagement'ın gerçekliğini onaylamış → T4.

**Herhangi biri eksikse tanıklık kaydedilir ama `COMPETENCE` olarak değil,
`PARTICIPATION` olarak gösterilir.** Reddedilmez — düşürülür.

> ❓ AÇIK SORU: §8.3 eşiği "≥4 hafta **veya** ≥40 saat" diyor. MVP'de hangisi
> zorunlu? `planned_hours` nullable olduğu için saat eşiği her engagement'ta
> hesaplanamayabilir. Hackathon için "≥4 hafta" tek kriter olarak alınabilir mi?

**Anti-abuse kuralları (§8.4)**
- Yeni kurum ilk **30 gün** içinde `COMPETENCE` tanıklığı yapamaz (cooling period).
- Kurumun tanıklık kotası doğrulanmış üye sayısına bağlı (üye başına ayda ~5).
- **Aynı kişi hem kurum yetkilisi hem öğrenci olarak kendi kendini doğrulayamaz**
  → `attestor_user_id != talent.user_id` **veritabanı seviyesinde CHECK** + üyelik
  grafiği kontrolü.
- Bir kurumun tüm tanıklıkları tek üniversiteye/tek öğrenci kümesine yoğunlaşıyorsa
  admin incelemesi için işaretlenir.

### 3.12 Evaluation

Kurumun yapılandırılmış değerlendirmesi. **Append-only.**

```
Evaluation
  id, engagement_id
  evaluator_user_id
  competence_ratings          -- skill_id → rating | NOT_OBSERVED
  conduct_ratings             -- davranış boyutu → rating | NOT_OBSERVED
  narrative (nullable)
  private_note (nullable)     -- öğrenciye gösterilmez, loglanmaz
  submitted_at
  created_at
```

**İş kuralları**
- `NOT_OBSERVED` **birinci sınıf değerdir** — değerlendiren, gözlemlemediği
  yetkinlik için puan vermeye zorlanmaz. Zorlanırsa uydurur ve veri kirlenir.
- `private_note` asla öğrenciye, public profile veya loglara çıkmaz.

### 3.13 VerifiedExperience

> **VerifiedExperience = Engagement'ın değişmez kaydı.** Engagement tamamlanıp
> değerlendirildiğinde **kopyalanarak** üretilir ve bir daha değişmez.

```
VerifiedExperience
  id, talent_id, engagement_id (unique)
  organization_name_snapshot          -- kopyalanmış, canlı FK değil
  institution_name_snapshot (nullable)
  title_snapshot, description_snapshot
  started_at, ended_at
  attestor_name_snapshot, attestor_role_snapshot
  attestor_trust_tier_snapshot
  public_token (unique)               -- public doğrulama linki
  visibility (PRIVATE | INSTITUTION | PUBLIC)
  created_at
```

**Neden kopyalanır (kasıtlı denormalizasyon):** Kurum hesabını silerse, adını
değiştirirse veya platformdan ayrılırsa öğrencinin doğrulanmış deneyimi
bozulmamalıdır. **Deneyim, tanıklık anındaki gerçeği dondurur.**

**Tek mutable alan:** `visibility` (öğrenci gizliliğini değiştirebilir).
Diğer her alan değişmezdir.

Üretimi tek transaction'da olur → [STATE_MACHINE.md](STATE_MACHINE.md).

### 3.14 SkillSignal

Sorun: "Bu kişinin Python yetkinliği ne kadar güçlü?" sorusunu her seferinde
6 tablo join'leyerek hesaplamak hem yavaş hem tutarsız.

Çözüm: Her kanıt olayı, o kişi–yetkinlik çifti için **değişmez bir sinyal kaydı**
üretir. **Append-only.**

```
SkillSignal
  id, talent_id, skill_id
  source_type (SELF_CLAIM | DELIVERABLE | TASK | EVALUATION | ATTESTATION | EXTERNAL)
  source_id
  strength (NONE | WEAK | MODERATE | STRONG)
  attested_by_org_id (nullable)
  occurred_at            -- yetkinliğin kullanıldığı tarih (recency için)
  created_at
  superseded_by_id (nullable)
```

> **Bir yetkinliğin "seviyesi" bir kolon değildir** — bu sinyallerin bir
> fonksiyonudur.

Üç faydası:
1. **Zaman içindeki geçmiş bedavaya gelir.**
2. **Açıklanabilirlik bedavaya gelir:** "Neden STRONG?" → sinyalleri listele.
3. **Geri alınabilirlik:** kurum tanıklığını geri çekerse sinyal `superseded` olur,
   geçmiş silinmez.

> ❓ AÇIK SORU: Hangi `source_type` hangi `strength` değerini üretir — final
> analizde tablolanmamış (ör. `SELF_CLAIM` her zaman `NONE` mı?). Sinyal üretim
> kuralları [PLAN.md](PLAN.md) 2.9 yazılırken netleşmeli ve buraya eklenmeli.

### 3.15 AuditEvent

Her durum değişikliği bir denetim kaydı üretir. **Append-only.**

```
AuditEvent
  id, actor_user_id (nullable — sistem olayları için)
  action                      -- ör. "engagement.transition"
  subject_type, subject_id
  payload (jsonb — PII içermez)
  ip_address (nullable), user_agent (nullable)
  occurred_at
```

Definition of Done (§36) madde 4 gereği: **durum değişikliği `AuditEvent`
üretmiyorsa özellik bitmemiştir.**

---

## 4. Experience / Project / Collaboration karışıklığının çözümü

Ön araştırma dokümanı `Project`, `Collaboration` ve `Experience`'ı ayrı entity
olarak tutuyordu. Bu üçü büyük ölçüde aynı şeydir; ayırmak gereksiz karmaşıklık
üretir.

| Ön araştırmadaki terim | Karar |
|---|---|
| `Collaboration` | → **`Engagement`** olarak adlandırıldı (§10.1) |
| `Project` (ayrı entity) | ❌ **MVP'den çıkarıldı.** Öğrencinin platform dışı kişisel projeleri `Evidence` olarak, düşük güven seviyesiyle (`SELF_UPLOADED`) eklenir |
| `Experience` (ayrı entity) | ❌ **Çıkarıldı.** `VerifiedExperience` yeterli |

Özet formül:

> **Engagement = olan şey.**
> **VerifiedExperience = olanın dondurulmuş, değişmez kaydı.**

---

## 5. İlişki haritası

```
Institution 1──n TalentProfile        (öğrenci hangi kuruma bağlı)
Institution 1──n Engagement           (hakem)
User        1──1 TalentProfile
User        n──n Organization         (OrganizationMember, role ile)

Engagement  n──1 TalentProfile
Engagement  n──1 Organization
Engagement  n──1 Institution          (nullable — platform dışı işbirliği için)
Engagement  1──n EngagementTask
Engagement  1──n Deliverable
Engagement  1──n Evaluation
Engagement  1──0..1 VerifiedExperience

Deliverable 1──n Evidence
Evidence    n──n Skill                (evidence_skills)
Attestation n──1 (polymorphic subject: Evidence | Deliverable | Engagement | SkillClaim)
Attestation n──1 Organization/Institution (attestor)

SkillSignal n──1 TalentProfile
SkillSignal n──1 Skill
SkillSignal n──1 (source: Deliverable | Evaluation | Attestation | SkillClaim)
```

---

## 6. Değişmezlik (append-only) ve geçmiş

**Prensip: Değişmez olması gereken veriyi mutable tasarlayıp sonra geçmiş
tablosu eklemek yerine, baştan append-only tasarlayın.**

Ayrı "history" tabloları (skill history, evaluation history, verification history,
profile changes) **reddedildi** — 4 ayrı geçmiş tablosu gereksiz yüktür.
`Attestation`, `Evaluation` ve `SkillSignal` doğaları gereği değişmez olduğu için
geçmiş zaten yapının içindedir.

| Tablo | Değişebilirlik | Geçmiş nasıl tutulur |
|---|---|---|
| `attestations` | Append-only (tek istisna: `revoked_at`) | Yapının içinde |
| `skill_signals` | Append-only (tek istisna: `superseded_by_id`) | Yapının içinde |
| `evaluations` | Append-only | Yapının içinde |
| `verified_experiences` | Append-only (tek istisna: `visibility`) | Yapının içinde |
| `audit_events` | Append-only | Yapının içinde |
| `skill_claims` | **Mutable** | `skill_claim_history` tablosu |
| Diğerleri | Mutable | Geçmiş tutulmaz |

Fiziksel uygulama (kısıt, trigger, silme politikası) → [DATABASE.md](DATABASE.md).

---

## 7. İş kuralları özeti

Alan modelinden doğan, kod yazarken doğrulanması gereken kurallar.
Bu tablo kod incelemesinde kontrol listesi olarak kullanılır.

| # | Kural | Nerede uygulanır |
|---|---|---|
| D1 | Güven yalnız `Attestation`'dan gelir; `Evidence` tek başına doğrulama değildir | Servis + UI |
| D2 | `attestor_user_id != talent.user_id` — kendi kendini doğrulama yok | **DB CHECK** + servis |
| D3 | `COMPETENCE` tanıklığı 6 ön koşulun hepsini gerektirir (§3.11) | Servis |
| D4 | Ön koşul eksikse tanıklık `PARTICIPATION`'a düşürülür, reddedilmez | Servis |
| D5 | Serbest metin skill yasak — yalnız taksonomiden seçim | DB FK + API şeması |
| D6 | `VerifiedExperience` alanları snapshot'tır; canlı FK ile bağlanmaz | Şema |
| D7 | Yeni kurum 30 gün `COMPETENCE` yapamaz (cooling period) | Servis |
| D8 | `NOT_OBSERVED` geçerli bir değerlendirme cevabıdır, boş değil | Şema + UI |
| D9 | `private_note` öğrenciye, public'e ve loglara çıkmaz | Servis + response şeması |
| D10 | Öğrenci kendi kendine `Institution`'a bağlanamaz — koordinatör onayı | Servis |
| D11 | `Deliverable`'a en az bir `Evidence` bağlı olmalı | Servis |
| D12 | Attestation geri çekilince ilgili `SkillSignal` `superseded` olur, silinmez | Servis (tek transaction) |
| D13 | `is_public = true` ise `public_slug` zorunlu | DB CHECK |
| D14 | `Evidence`'ta `uri` veya `storage_key`'den en az biri dolu | DB CHECK |
