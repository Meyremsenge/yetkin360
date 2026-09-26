# DATABASE.md — Veritabanı Şeması

PostgreSQL 16 fiziksel şeması: tablolar, kolonlar, kısıtlar, index'ler,
append-only kuralları, silme politikası, transaction sınırları.

**Kaynak:** `yetkin360-final-analiz.md` §12.1–12.6.
Kavramsal model ve iş kuralları → [DOMAIN.md](DOMAIN.md).
Bu dosya *nasıl saklandığını* anlatır, *neden öyle olduğunu* değil.

**İlgili dosyalar:**
- Entity tanımları, iş kuralları → [DOMAIN.md](DOMAIN.md)
- `engagements.status` değerleri ve geçişleri → [STATE_MACHINE.md](STATE_MACHINE.md)
- Erişim kuralları (`scoped_*` sorguları) → [AUTHORIZATION.md](AUTHORIZATION.md)

---

## 1. Ortak kurallar

Bu kurallar **istisnasız** tüm tablolara uygulanır. İhlal = migration reddedilir.

| Kural | Değer | Gerekçe |
|---|---|---|
| Birincil anahtar | `uuid PRIMARY KEY`, **UUIDv7** | Zaman sıralı → index locality. Artan integer ID enumeration saldırısına ve iş verisi sızıntısına ("kaç öğrenciniz var?") açıktır — ID'ler URL'de görünecek |
| Zaman damgası | `timestamptz`, **her zaman UTC** | `timestamp` (tz'siz) kullanılmaz |
| Ortak kolonlar | `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()` | — |
| E-posta / slug | `citext` | Büyük-küçük harf duyarsız benzersizlik |
| Kısıtlar | FK, CHECK, UNIQUE **veritabanında** | Sadece uygulama kontrolü yetmez |
| Ham SQL | Yalnız migration dosyalarında | — |

**İstisna:** `audit_events` ve `outbox` `bigserial` PK kullanır — bu tablolar
URL'de görünmez, sıralı okuma önemlidir.

**UUIDv7 üretimi:** PostgreSQL 16'da yerleşik `uuidv7()` yoktur.

> ❓ AÇIK SORU: UUIDv7 nerede üretilecek — uygulama katmanında (Python `uuid6`
> paketi) mı, yoksa `pg_uuidv7` eklentisiyle veritabanında mı? Eklenti kurulumu
> Docker imajını değiştirir. Hackathon için uygulama katmanı daha az sürtünmeli
> görünüyor ama karar verilmemiş.

---

## 2. Şema

Aşağıdaki DDL taslağı kesinleşmiş hâldir. Alembic migration'ları buradan üretilir.
Her blokta ortak kolonlar (`id`, `created_at`, `updated_at`) tekrar yazılmamıştır.

### 2.1 Kimlik

```sql
users
  id uuid PK
  email citext UNIQUE NOT NULL
  password_hash text NOT NULL                    -- Argon2id
  email_verified_at timestamptz
  status text NOT NULL DEFAULT 'ACTIVE'
      CHECK (status IN ('PENDING','ACTIVE','SUSPENDED','DELETED'))
  is_platform_admin boolean NOT NULL DEFAULT false  -- yalnız seed/manuel atama, self-servis uç yok
  failed_login_count int NOT NULL DEFAULT 0
  locked_until timestamptz
  deleted_at timestamptz
  -- INDEX: (email) UNIQUE
  --        (status) PARTIAL WHERE deleted_at IS NULL

institutions                                     -- üniversite / bölüm
  id uuid PK
  name text NOT NULL
  domain citext UNIQUE                           -- ör. 'xyz.edu.tr'
  verification_level text NOT NULL DEFAULT 'T1'
      CHECK (verification_level IN ('T1','T2','T3','T4'))
  status text NOT NULL DEFAULT 'ACTIVE'

institution_members                              -- koordinatörler
  id uuid PK
  institution_id uuid NOT NULL REFERENCES institutions(id)
  user_id uuid NOT NULL REFERENCES users(id)
  role text NOT NULL CHECK (role IN ('ADMIN','COORDINATOR'))
  UNIQUE (institution_id, user_id)
  -- INDEX: (user_id)

talent_profiles
  id uuid PK
  user_id uuid UNIQUE NOT NULL REFERENCES users(id)
  institution_id uuid REFERENCES institutions(id)
  full_name text NOT NULL
  headline text
  department text
  study_year smallint CHECK (study_year BETWEEN 1 AND 8)
  city text
  visibility text NOT NULL DEFAULT 'INSTITUTION'
      CHECK (visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC'))
  public_slug citext UNIQUE                      -- paylaşılabilir profil linki
  deleted_at timestamptz
  -- INDEX: (institution_id) PARTIAL WHERE deleted_at IS NULL
  --        (public_slug) UNIQUE PARTIAL WHERE public_slug IS NOT NULL

organizations
  id uuid PK
  name text NOT NULL
  legal_id text                                  -- MERSİS / vergi no
  domain citext
  verification_level text NOT NULL DEFAULT 'T1'
      CHECK (verification_level IN ('T1','T2','T3','T4'))
  verified_at timestamptz
  verified_by_user_id uuid REFERENCES users(id)
  status text NOT NULL DEFAULT 'ACTIVE'
  deleted_at timestamptz
  -- UNIQUE (legal_id) PARTIAL WHERE legal_id IS NOT NULL
  --   → aynı şirket iki kez kurulamaz

organization_members
  id uuid PK
  organization_id uuid NOT NULL REFERENCES organizations(id)
  user_id uuid NOT NULL REFERENCES users(id)
  role text NOT NULL CHECK (role IN ('ADMIN','MEMBER'))
  status text NOT NULL DEFAULT 'ACTIVE'
  UNIQUE (organization_id, user_id)
  -- INDEX: (user_id)
  --   → "bu kullanıcı hangi kurumlarda" sorgusu HER istekte çalışır
```

### 2.2 Yetkinlik

```sql
skills
  id uuid PK
  slug citext UNIQUE NOT NULL
  name_tr text NOT NULL
  name_en text
  category text NOT NULL
      CHECK (category IN ('LANGUAGE','FRAMEWORK','TOOL','DOMAIN','SOFT'))
  parent_id uuid REFERENCES skills(id)           -- tek seviyeli hiyerarşi
  status text NOT NULL DEFAULT 'ACTIVE'
      CHECK (status IN ('ACTIVE','MERGED','DEPRECATED'))
  merged_into_id uuid REFERENCES skills(id)
  CHECK (status <> 'MERGED' OR merged_into_id IS NOT NULL)

skill_claims
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  skill_id uuid NOT NULL REFERENCES skills(id)
  claimed_level text
      CHECK (claimed_level IN ('BEGINNER','INTERMEDIATE','ADVANCED'))
  source text NOT NULL DEFAULT 'MANUAL'
      CHECK (source IN ('MANUAL','AI_EXTRACTED'))
  confirmed_by_user_at timestamptz               -- AI çıktısı için ZORUNLU
  UNIQUE (talent_id, skill_id)                   -- aynı skill iki kez eklenemez
  CHECK (source <> 'AI_EXTRACTED' OR confirmed_by_user_at IS NOT NULL)
```

> **Not:** `source = 'AI_EXTRACTED'` kolonu şemada duruyor ama **MVP'de AI yok**
> (CLAUDE.md kapsam kuralı). Kolon ileriye dönük bırakılmıştır; MVP'de her kayıt
> `MANUAL` gelir. Kolonu kaldırmak yerine bırakmak, sonradan migration gerektirmez.

### 2.3 Çalışma

```sql
engagements
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  organization_id uuid NOT NULL REFERENCES organizations(id)
  institution_id uuid REFERENCES institutions(id)
  supervisor_user_id uuid REFERENCES users(id)   -- kurumdaki sorumlu
  kind text NOT NULL CHECK (kind IN ('INTERNSHIP','CAPSTONE','SHORT_PROJECT','PART_TIME'))
  title text NOT NULL
  status text NOT NULL DEFAULT 'DRAFT'
      CHECK (status IN ('DRAFT','PENDING_APPROVAL','REJECTED','ACTIVE',
                        'CANCELLED','PENDING_EVALUATION','EVALUATED',
                        'VERIFIED','DISPUTED','RESOLVED'))
  started_on date
  ended_on date
  confidential boolean NOT NULL DEFAULT false
  version int NOT NULL DEFAULT 1                 -- optimistic locking
  CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on)
  -- INDEX: (organization_id, status)
  --        (talent_id, status)
  --        (institution_id, status)   ← koordinatör dashboard'unun ANA sorgusu
  --        (status) PARTIAL WHERE status = 'PENDING_EVALUATION'  ← takip ekranı

engagement_tasks
  id uuid PK
  engagement_id uuid NOT NULL REFERENCES engagements(id) ON DELETE CASCADE
  title text NOT NULL
  status text NOT NULL DEFAULT 'PLANNED'
      CHECK (status IN ('PLANNED','IN_PROGRESS','DONE'))
  completed_at timestamptz
  -- INDEX: (engagement_id)

deliverables
  id uuid PK
  engagement_id uuid NOT NULL REFERENCES engagements(id)
  task_id uuid REFERENCES engagement_tasks(id)
  title text NOT NULL
  description text
  submitted_at timestamptz
  accepted_at timestamptz
  accepted_by_user_id uuid REFERENCES users(id)
  -- INDEX: (engagement_id)
```

`status` değerlerinin anlamı ve geçiş kuralları → [STATE_MACHINE.md](STATE_MACHINE.md).

### 2.4 Kanıt

```sql
evidence
  id uuid PK
  owner_talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  deliverable_id uuid REFERENCES deliverables(id)
  kind text NOT NULL
      CHECK (kind IN ('REPOSITORY','DOCUMENT','IMAGE','LINK','CERTIFICATE'))
  provenance text NOT NULL
      CHECK (provenance IN ('SELF_UPLOADED','PLATFORM_GENERATED','EXTERNAL_VERIFIED'))
  storage_key text
  external_uri text
  content_hash text
  mime_type text
  size_bytes bigint
  scan_status text NOT NULL DEFAULT 'PENDING'
      CHECK (scan_status IN ('PENDING','CLEAN','INFECTED','FAILED'))
  visibility text NOT NULL DEFAULT 'PRIVATE'
  deleted_at timestamptz
  CHECK (storage_key IS NOT NULL OR external_uri IS NOT NULL)   -- DOMAIN D14
  -- INDEX: (owner_talent_id) PARTIAL WHERE deleted_at IS NULL
  --        (deliverable_id)

evidence_skills
  evidence_id uuid REFERENCES evidence(id) ON DELETE CASCADE
  skill_id uuid REFERENCES skills(id)
  PRIMARY KEY (evidence_id, skill_id)
```

**`scan_status` MVP notu:** Hackathon kapsamında ClamAV **yoktur** (final analiz
§35.3). MVP'de MIME + boyut + magic-byte kontrolü geçen dosya doğrudan `CLEAN`
işaretlenir. Kolon ileriye dönük durur. Akış → [SECURITY.md](SECURITY.md).

### 2.5 Tanıklık ve sinyal

```sql
attestations                                     -- APPEND-ONLY
  id uuid PK
  subject_type text NOT NULL
      CHECK (subject_type IN ('ENGAGEMENT','DELIVERABLE','SKILL_IN_ENGAGEMENT'))
  subject_id uuid NOT NULL
  skill_id uuid REFERENCES skills(id)            -- COMPETENCE ise dolu
  claim_type text NOT NULL
      CHECK (claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT'))
  attestor_user_id uuid NOT NULL REFERENCES users(id)
  attestor_org_id uuid REFERENCES organizations(id)
  attestor_institution_id uuid REFERENCES institutions(id)
  trust_level text NOT NULL CHECK (trust_level IN ('T1','T2','T3','T4','T5'))
  statement text
  revoked_at timestamptz
  revoke_reason text
  created_at timestamptz NOT NULL DEFAULT now()
  CHECK (claim_type <> 'COMPETENCE' OR skill_id IS NOT NULL)
  CHECK (attestor_org_id IS NOT NULL OR attestor_institution_id IS NOT NULL)
  -- INDEX: (subject_type, subject_id)
  --        (attestor_org_id, created_at)

skill_signals                                    -- APPEND-ONLY
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  skill_id uuid NOT NULL REFERENCES skills(id)
  source_type text NOT NULL
      CHECK (source_type IN ('SELF_CLAIM','DELIVERABLE','EVALUATION',
                             'ATTESTATION','EXTERNAL'))
  source_id uuid
  strength text NOT NULL CHECK (strength IN ('NONE','WEAK','MODERATE','STRONG'))
  attested_by_org_id uuid REFERENCES organizations(id)
  occurred_at timestamptz NOT NULL
  superseded_by_id uuid REFERENCES skill_signals(id)
  -- INDEX: (talent_id, skill_id, occurred_at DESC)   ← profil sayfasının ANA sorgusu
  --        (skill_id, strength) PARTIAL WHERE superseded_by_id IS NULL
  --          ← yetenek arama
```

> **`attestor_user_id != talent.user_id` kuralı (DOMAIN D2):** `attestations`
> tablosunda `talent_id` kolonu **yoktur** — talent, `subject_id` üzerinden
> dolaylı bulunur. Bu yüzden kural **tek tablolu CHECK ile ifade edilemez.**
>
> ❓ AÇIK SORU: Bu kısıt nasıl veritabanı seviyesinde zorlanacak?
> Seçenekler: (a) `attestations`'a denormalize `subject_talent_id` kolonu eklemek
> ve `CHECK`'i mümkün kılmak, (b) `BEFORE INSERT` trigger'ı. Final analiz "DB
> seviyesinde CHECK" diyor ama kolonu tanımlamamış. (a) tercih edilirse şema
> değişir — karar [PLAN.md](../PLAN.md) 2.8 öncesinde verilmeli.

### 2.6 Değerlendirme

```sql
evaluations                                      -- APPEND-ONLY (submitted_at sonrası)
  id uuid PK
  engagement_id uuid NOT NULL REFERENCES engagements(id)
  evaluator_user_id uuid NOT NULL REFERENCES users(id)
  direction text NOT NULL
      CHECK (direction IN ('ORG_TO_TALENT','TALENT_TO_ORG'))
  submitted_at timestamptz
  private_note text                              -- öğrenciye GÖSTERİLMEZ
  UNIQUE (engagement_id, evaluator_user_id, direction)

evaluation_items
  id uuid PK
  evaluation_id uuid NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE
  skill_id uuid REFERENCES skills(id)
  criterion text NOT NULL                        -- yetkinlik veya davranışsal kriter
  rating text NOT NULL
      CHECK (rating IN ('BELOW','MEETS','EXCEEDS','NOT_OBSERVED'))
  comment text
```

> `NOT_OBSERVED` kritiktir: gözlemlenmemiş şeye not vermeye zorlamak veriyi bozar.
> UI'da bu seçenek her zaman görünür olmalıdır (DOMAIN D8).

### 2.7 Doğrulanmış deneyim

```sql
verified_experiences                             -- SNAPSHOT, APPEND-ONLY
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  engagement_id uuid UNIQUE NOT NULL REFERENCES engagements(id)
  org_name_snapshot text NOT NULL                -- kasıtlı denormalizasyon
  org_verification_level_snapshot text NOT NULL
  institution_name_snapshot text
  title text NOT NULL
  started_on date NOT NULL
  ended_on date NOT NULL
  verified_at timestamptz NOT NULL
  visibility text NOT NULL DEFAULT 'PUBLIC'
  public_token text UNIQUE                       -- paylaşılabilir doğrulama linki
  -- Sadece `visibility` değişebilir. Diğer her alan değişmez.
```

Snapshot kolonları **bilinçli olarak FK değildir** — gerekçe [DOMAIN.md](DOMAIN.md) §3.13.

### 2.8 Altyapı

```sql
audit_events                                     -- APPEND-ONLY
  id bigserial PK                                -- burada UUID gereksiz, sıralı daha iyi
  actor_user_id uuid
  actor_ip inet
  action text NOT NULL
  subject_type text NOT NULL
  subject_id uuid
  result text NOT NULL CHECK (result IN ('SUCCESS','DENIED','ERROR'))
  metadata jsonb                                 -- PII İÇERMEZ
  occurred_at timestamptz NOT NULL DEFAULT now()
  -- INDEX: (subject_type, subject_id, occurred_at DESC)
  --        (actor_user_id, occurred_at DESC)
  -- Aylık partition (pg_partman) — büyüyecek TEK tablo budur

outbox                                           -- transaction güvenli yan etki
  id bigserial PK
  topic text NOT NULL
  payload jsonb NOT NULL
  created_at timestamptz NOT NULL DEFAULT now()
  processed_at timestamptz
  attempts int NOT NULL DEFAULT 0
  -- INDEX: (created_at) PARTIAL WHERE processed_at IS NULL

skill_claim_history                              -- tek mutable kanıt tablosunun geçmişi
  -- Bkz. DOMAIN.md §6
```

> ❓ AÇIK SORU: `skill_claim_history` [DOMAIN.md](DOMAIN.md) §6'da gerekli
> deniyor ama §12.2 DDL'inde tanımlanmamış. Kolonları (muhtemelen
> `skill_claim_id`, eski `claimed_level`, `changed_at`, `changed_by_user_id`)
> kesinleştirilmeli. Hackathon MVP'sinde atlanabilir mi?

> **`audit_events` partition notu:** Aylık partition (`pg_partman`) uzun vadeli
> çözümdür. Hackathon 3 haftalık veri üretecek — MVP'de düz tablo yeterli,
> partition Faz 5'e (PLAN 5.4) bırakılır.

---

## 3. Append-only tablolar

Bu tablolarda `UPDATE` ve `DELETE` **yasaktır.** Kural hem uygulama katmanında
(CLAUDE.md) hem veritabanı trigger'ıyla zorlanır — uygulama katmanı tek başına
yeterli değildir.

| Tablo | Yasak | İzin verilen tek istisna |
|---|---|---|
| `attestations` | UPDATE, DELETE | `revoked_at`, `revoke_reason` |
| `skill_signals` | UPDATE, DELETE | `superseded_by_id` |
| `evaluations` | UPDATE, DELETE | — (`submitted_at` dolduktan sonra) |
| `verified_experiences` | UPDATE, DELETE | `visibility` |
| `audit_events` | UPDATE, DELETE | — |

**Uygulama:** Her tablo için bir `BEFORE UPDATE OR DELETE` trigger'ı; istisna
kolonları dışında bir değişiklik varsa `RAISE EXCEPTION`.

> ❓ AÇIK SORU: Trigger'lar migration'da mı yazılacak yoksa `evaluations` için
> `submitted_at IS NULL` iken güncellemeye izin veren daha esnek bir kural mı
> gerekiyor (taslak kaydetme senaryosu)? Değerlendirme formu taslak olarak
> kaydedilebilecek mi, yoksa tek seferde mi gönderilecek — bu UX kararı şemayı
> etkiler.

---

## 4. Silme politikası

> **Tek politika uygulanamaz — tabloya göre değişir.**

| Tablo | Politika | Gerekçe |
|---|---|---|
| `users` | **Anonimleştirme** | KVKK silme hakkı. Satır kalır, PII temizlenir: `email = 'deleted-<uuid>@invalid'`, `password_hash = ''`. FK bütünlüğü korunur |
| `talent_profiles` | Soft delete + PII anonimleştirme | Aynı |
| `evidence` | Soft delete → **30 gün sonra dosya hard delete** | Yanlışlıkla silmeye karşı koruma |
| `attestations` | **Asla silinmez** — sadece revoke | Doğrulamanın anlamı bu |
| `verified_experiences` | **Asla silinmez** — `visibility` değişir | Aynı |
| `audit_events` | **Asla silinmez** — retention sonunda arşiv | Denetim |
| `engagement_tasks` | **Hard delete OK** | Değeri yok |

### KVKK ile değişmezliğin çelişkisi

KVKK silme hakkı ile doğrulamanın değişmezliği çelişir **gibi görünür**.

> **Çözüm: Kişisel veri silinir, olgu kalır.**
> "Ahmet Yılmaz" → "Silinmiş Kullanıcı" olur, ama
> "Acme A.Ş. 2026'da bir stajyeri doğruladı" kaydı kalır.

Bu hem KVKK'ya hem denetlenebilirliğe uyar. **Kayıt sırasında aydınlatma
metninde açıkça belirtilmesi zorunludur.**

---

## 5. Transaction sınırları

> **Değişmez kural: Ağ çağrısı (e-posta, S3, AI) asla açık transaction içinde
> yapılmaz.** Çözüm: `outbox` tablosu + ayrı worker.

| İşlem | Transaction İÇİNDE | Transaction DIŞINDA |
|---|---|---|
| Engagement → `VERIFIED` | `status`, `verified_experiences`, `skill_signals`, `attestations`, `audit_events`, `outbox` satırı | E-posta, bildirim |
| Evidence yükleme | DB kaydı (`scan_status = PENDING`) | Dosya yükleme, virüs taraması |
| Kullanıcı kaydı | `users` + `talent_profiles` | Doğrulama e-postası |
| Değerlendirme gönderimi | `evaluations` + `evaluation_items` + `audit_events` | Bildirim |

En kritik olanı birinci satırdır: doğrulanmış deneyimin üretimi **tek
transaction'dır** — yarım kalırsa tutarsız kanıt zinciri oluşur.
Detay → [STATE_MACHINE.md](STATE_MACHINE.md).

---

## 6. Eşzamanlılık (concurrency)

Optimistic locking **yalnız gereken yerde** kullanılır; her tabloya eklemek
gereksiz karmaşıklıktır.

| Tablo | Optimistic locking | Gerekçe |
|---|---|---|
| `engagements` | ✅ `version int` | Durum çakışması gerçek bir risk |
| Diğerleri | ❌ | Gereksiz karmaşıklık |

**Durum geçişi deseni:**

```sql
UPDATE engagements
   SET status = :new_status, version = version + 1
 WHERE id = :id AND status = :expected_status AND version = :expected_version;
```

0 satır dönerse → **`409 Conflict`** (bkz. [API.md](API.md)).

---

## 7. Ölçekleme ve kritik sorgular

| Sorgu | Ölçek | Risk | Çözüm |
|---|---|---|---|
| Profil sayfası (skill + sinyaller) | Kişi başı ~200 satır | Düşük | `(talent_id, skill_id, occurred_at DESC)` index |
| Koordinatör dashboard (400 engagement) | Kurum başı düşük | Düşük | `(institution_id, status)` index |
| "Değerlendirme bekleyenler" | Tüm tablo taraması riski | **Orta** | **Partial index** `WHERE status = 'PENDING_EVALUATION'` |
| Yetenek arama (skill filtreli) | Tablolar arası join | **Yüksek — asıl risk** | Aşağı bkz. |
| Audit log sorgusu | En hızlı büyüyen tablo | **Yüksek** | Aylık partition + retention |

**Yetenek arama:** `skill_signals × talent_profiles` join'i gerektirir ve
`skill_signals` en büyük tablodur. Çözüm sırası:

1. **MVP'de doğrudan join yeterli** (<10K öğrenci).
2. 10K+ için materialized view (`talent_skill_summary`, saatlik yenilenir).
3. Yalnız 100K+ **ve gerçek darboğaz kanıtlanırsa** arama motoru.

> **Elasticsearch MVP'de kesinlikle gereksizdir.** 10M dokümanın ve birkaç yüz
> sorgu/sn'nin altında PostgreSQL FTS + GIN daha hızlı, daha ucuz, bakımı daha
> basittir.

---

## 8. Migration kuralları

| Kural | |
|---|---|
| Araç | Alembic. `alembic revision --autogenerate -m "..."` |
| **Uygulanmış migration düzenlenmez/silinmez** | Düzeltme = **yeni** migration |
| Geriye uyumluluk | Definition of Done madde 10 — her migration geri alınabilir olmalı |
| Doğrulama | `alembic upgrade head` **ve** `alembic downgrade -1` çalıştırılır |
| Onay | Migration oluşturmak/uygulamak **açık onay gerektirir** (CLAUDE.md) |

---

## 9. DOMAIN.md ile şema arasındaki farklar

[DOMAIN.md](DOMAIN.md) kavramsal modeli, bu dosya fiziksel şemayı anlatır.
Final analizin §7'si ile §12.2'si birebir örtüşmüyor. **Çelişki hâlinde §12.2
(bu dosya) esastır** — fiziksel şema kararı burada verilmiştir.

Bilinen farklar:

| Konu | DOMAIN.md (§7) | Bu dosya (§12.2) | Geçerli olan |
|---|---|---|---|
| Talent görünürlüğü | `is_public` bool + `public_slug` | `visibility` 4 değerli enum | **`visibility` enum** |
| Evidence → Engagement | Doğrudan `engagement_id` | `deliverable_id` üzerinden dolaylı | **`deliverable_id`** |
| Evidence `kind` | `DELIVERABLE_REF` dahil 6 değer | 5 değer (`DELIVERABLE_REF` yok) | **5 değer** |
| SkillSignal `source_type` | `TASK` dahil 6 değer | 5 değer (`TASK` yok) | **5 değer** |
| Engagement `kind` | 4 değer (`CAPSTONE` ayrı) | 3 değer (`PROJECT`) | **3 değer** |
| Institution `is_verified` | bool | `verification_level` T1–T4 | **`verification_level`** |
| Evaluation puanları | Serbest `competence_ratings` | `evaluation_items` alt tablosu | **Alt tablo** |
| Attestation `subject_type` | 4 değer (`SKILL_CLAIM` dahil) | 3 değer (`SKILL_IN_ENGAGEMENT`) | **3 değer** |
| Tarih alanları | `started_at timestamptz` | `started_on date` | **`date`** |

> Bu tablo, [DOMAIN.md](DOMAIN.md) okuyup koda geçen ekip üyesinin yanlış alan
> adı kullanmasını engellemek içindir. Kod yazarken **her zaman bu dosyaya** bakın.
