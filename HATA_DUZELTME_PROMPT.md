# HATA_DUZELTME_PROMPT.md — İş Listesi ve Düzeltme Prompt'ları

**Kaynak:** [HATA.md](HATA.md) (2026-09-28 denetimi, `main` @ `82a690a`)
**Ekip:** 2 kişi — **Kişi A** ve **Kişi B**. Düzeltmeleri Claude **Sonnet** oturumları yapar;
her kişi kendi prompt'unu yeni bir Sonnet oturumuna yapıştırır.
**Son tarih:** Kod dondurma (PLAN 3.16) **7 Ekim akşamı**; 8 Ekim demo provası (PLAN 4.1).

> Bu dosya önceki tek-prompt'luk sürümün (PLAN 3.17–3.23) yerini alır. O maddeler aşağıdaki
> listeye dahil edildi; numaraları korundu.

---

## İçindekiler

0. [Hızlı başlangıç](#0-hızlı-başlangıç)
1. [Ortak kurallar (her prompt bunu okutur)](#1-ortak-kurallar)
2. [Karar tablosu — başlamadan önce ikiniz karar verin](#2-karar-tablosu)
3. [İş bölümü ve dosya sahipliği](#3-iş-bölümü-ve-dosya-sahipliği)
4. [Takvim, bağımlılıklar, senkron noktaları](#4-takvim)
5. [İş listesi (checklist)](#5-iş-listesi)
6. [Skill zincirleri](#6-skill-zincirleri)
7. [Prompt'lar — Ortak (O-00)](#7-promptlar--ortak)
8. [Prompt'lar — Kişi A (backend: güvenlik, yetki, altyapı)](#8-promptlar--kişi-a)
9. [Prompt'lar — Kişi B (zincir iş kuralları + frontend)](#9-promptlar--kişi-b)
10. [Prompt'lar — Kapanış (O-01, O-02)](#10-promptlar--kapanış)
11. [Kapsam haritası: her HATA ID'si hangi prompt'ta](#11-kapsam-haritası)

---

## 0. Hızlı başlangıç

1. **Bugün (28 Eylül):** §2'deki 10 kararı ikiniz birlikte verin, tabloya işaretleyin. Karar
   verilmezse prompt'lar "Öneri" sütunundaki varsayılanı uygular.
2. **Kişi A** `O-00`'ı çalıştırır (PLAN.md'ye maddeleri ekler — 15 dakikalık iş).
3. Kişilerden biri A, diğeri B listesini alır. A listesi `@be2` alanıyla (auth, yetki, dosya,
   deploy) örtüşüyor.
4. Her iş için: yeni Sonnet oturumu aç → proje kökünde → ilgili prompt'un ```text``` bloğunu
   **olduğu gibi** yapıştır. Prompt Sonnet'e önce §1'i okutur.
5. İş bitince: testler yeşil → Sonnet sana diff özetini gösterir → **sen onaylarsan** `/bitir`
   → dalı push et → `gh pr create` → diğer kişi review eder → merge.
6. Oturum iş bitmeden kapanacaksa Sonnet'e `handoff` skill'ini çalıştırt; sonraki oturum
   `HANDOFF.md`'den devam eder.

---

## 1. Ortak kurallar

> Her prompt "Önce HATA_DUZELTME_PROMPT.md §1'i oku" diye başlar. Sonnet bu bölümü
> kurallar listesi olarak uygular.

**1.1 Dil ve iletişim**
- Kullanıcıyla Türkçe konuş. Kod, tanımlayıcı, kod yorumu, API alan adı İngilizce.
- UI metni Türkçe ve **koda gömülmez** → `frontend/messages/tr.json`.

**1.2 Önce doğrula, sonra düzelt**
- HATA.md 28 Eylül'de `82a690a` üzerinde yazıldı. Satır numaraları kaymış olabilir.
  Kod yazmadan önce bulgunun **hâlâ geçerli** olduğunu kodu okuyarak teyit et.
- Bulgu geçersizse (biri düzeltmiş, yorum yanlış): düzeltme yapma, nedenini söyle, dur.
- HATA.md'deki öneriyi körü körüne uygulama; daha basit ve doğru bir yol görürsen söyle.

**1.3 Dal ve git**
- Başlamadan: `git switch main && git pull` → `git switch -c <prompt'taki dal adı>`.
- `git add -A` / `git add .` **yasak** — dosyaları adıyla ekle.
- Commit'i **sen atmazsın**; kullanıcı onaylayınca `/bitir` çalıştırılır.
- `main`'e doğrudan push yok; push + `gh pr create` kullanıcının onayıyla.
- Commit mesajı Türkçe, gövdede `PLAN <numara>` ve HATA ID'leri; son satır CLAUDE.md'deki
  `Co-Authored-By` satırı.

**1.4 Onay gerektirenler (CLAUDE.md) — bunlarda DUR ve sor**
- Migration oluşturma/uygulama · dosya silme · 3+ dosyalık refactor · bağımlılık ekleme/
  yükseltme · **yetkilendirme/kimlik doğrulama mantığı değişikliği** · `docker-compose.yml`,
  CI, `settings.json` değişikliği · push/deploy.
- Prompt'ta "ONAY NOKTASI" yazan yerde kod yazmadan önce planı özetle ve onay bekle.

**1.5 Değişmez kurallar (ihlal = değişiklik reddedilir)**
- Katman: `api/ → services/ → models/`. İş mantığı yalnız `services/`. Repository katmanı yok.
- Pydantic şeması ≠ ORM modeli; ORM modeli doğrudan response olmaz.
- Veri erişimi `can()` / `scoped_*()` üzerinden. Çıplak `select(Model)` ile kiracı verisi okunmaz.
- Yetkisiz erişim **404** (403 değil). İstisna: CSRF (403) ve belgelenmiş S6 durumları.
- **Yeni endpoint = aynı commit'te yetkilendirme testi** (`tests/authorization/`), pozitif +
  en az bir "başka kiracı erişemez" negatif test.
- Append-only: `attestations`, `skill_signals`, `evaluations`, `audit_events`,
  `verified_experiences` (istisnalar: `attestations.revoked_at/revoke_reason`,
  `skill_signals.superseded_by_id` set-once, `verified_experiences.visibility`).
- Ağ çağrısı (e-posta, S3, DNS) açık transaction içinde yapılmaz → outbox.
- Loglara/audit metadata'ya PII yok: şifre, token, `private_note`, tam e-posta, CV içeriği.
- Ham SQL yalnız migration'da. Zaman `timestamptz`/UTC, ID UUIDv7.
- **MVP dışı özellik yazma:** AI, matching, chat, gamification, Redis, Celery, Elasticsearch,
  pgvector, RLS, Kubernetes. Hız sınırı gerekiyorsa süreç içi (in-memory) çözüm.
- `.env` **okunmaz**, içeriği çıktıya yazılmaz. `.env.example` okunabilir (yalnız placeholder).

**1.6 Dosya sahipliği**
- §3'teki tabloya bak. Başka kişinin sahip olduğu dosyaya dokunman gerekiyorsa **dur ve
  kullanıcıya söyle** — iki kişinin aynı dosyada paralel çalışması merge çatışması demek.
- Küçük, kaçınılmaz dokunuşlar (ör. yeni router'a `Depends` eklemek) serbest; commit
  mesajında belirt.

**1.7 Test ve bilinen kırıklar**
- Doğrulama matrisi (CLAUDE.md): backend servis → ilgili unit+integration; yeni endpoint →
  + yetkilendirme testi; **auth/yetki değişikliği → `pytest tests/authorization -q` tamamı**;
  migration → `alembic upgrade head` + `alembic downgrade -1` + testler; frontend mantık →
  `npm run typecheck` + ilgili bileşen testi; bağımlılık → tüm paket.
- **Bilinen kırık testler (A-13 ve B-11 düzeltene kadar):** bunlar senin hatan değil; ama
  sayıları **artmamalı**. Kendi değişikliğinden önce ve sonra aynı listeyi karşılaştır.
  - Backend (13): `tests/test_evaluation.py::TestEvaluationInvalidSkillIdInItem::test_evaluation_invalid_skill_id_in_item_422`,
    `tests/test_outbox_worker.py` içinden 9 test, `tests/test_seed.py` içinden 3 test
    (`test_ac4_db_error_during_seeding_causes_full_rollback`,
    `test_ac5_production_environment_prevents_seeding`,
    `test_ac4_engagement_creation_error_propagates_not_swallowed`).
  - Frontend (9): `lib/api/evaluation.test.ts` (6), `app/calismalar/[id]/evidence-upload-form.test.tsx` (1),
    `app/calismalar/[id]/degerlendirme/evaluation-form.test.tsx` (1), `app/kurum/[id]/panel/page.test.tsx` (1).
- **Test fixture tuzağı (HATA.md TEST-02):** `tests/conftest.py`'deki `override_get_session`
  istisnada rollback yapmaz; üretim yapar. "Yaz, sonra hata fırlat" yolu test ediyorsan bu
  farkı göz önünde tut (A-13 düzeltene kadar ilgili testte gerçek davranışı taklit et ya da
  servisi doğrudan, rollback eden bir oturumla çağır).
- Testi atlamak yok. Test kırıldıysa çıktısıyla söyle.

**1.8 Ortam**
- `docker compose up -d` (Postgres + MinIO). Postgres yerelde `55433` portunda olabilir —
  bağlantı `.env`'den okunur, sen `.env`'i açma; `backend/.venv/Scripts/python.exe` ile çalıştır.
- Seed: `cd backend && .venv/Scripts/python.exe -m scripts.seed` (idempotent).
- Seed giriş bilgileri `baslat.bat` sonunda yazıyor.

**1.9 Bitiş**
1. Kabul kriterleri + doğrulama komutları yeşil.
2. `HATA.md`'de düzelttiğin her ID başlığının sonuna ` — ✅ DÜZELTİLDİ (PLAN x.y, dal <ad>)`
   ekle. Kısmen düzelttiysen ` — ◐ KISMEN (ne kaldı)`.
3. Bu dosyada §5 checklist'inde kendi satırını `[x]` yap.
4. CLAUDE.md kısa rapor formatıyla bitir (`Değişen / Doğrulanan / Kalan`), commit için onay iste.

---

## 2. Karar tablosu

Prompt'lar bu kararlara `K1…K10` diye atıf yapar. **"Seçilen" sütununu doldurun.** Boş
bırakılırsa Sonnet "Öneri"yi uygular ve bunu raporunda belirtir.

| # | Konu | Seçenekler | Öneri (varsayılan) | Seçilen |
|---|---|---|---|---|
| K1 | **Davet rızası** (GUV-02) | (a) Davet + kabul akışı (yeni durum kolonu, migration) · (b) Doğrudan ekleme kalsın; tek tip yanıt + 500 düzeltmesi + AUTHZ-01 | **(b)** — AUTHZ-01 düzelince hesap kilitleme etkisi kalkar; kabul akışı Faz 5 | ☐ |
| K2 | **Sybil / org rızası** (GUV-03, GUV-08) | (a) Org'un engagement'ı onaylaması (yeni geçiş) · (b) Onay yok; public sayfada kurum seviyesi + org alan adı gösterilir, bilgi-sızıntısı oracle'ı kapatılır | **(b)** — MVP'de yeni geçiş eklemek zinciri uzatır | ☐ |
| K3 | **Kurum ADMIN onay/tanıklık verebilir mi?** (AUTHZ-02) | (a) Hayır (doküman: yalnız `INST:COORD`); seed'e COORDINATOR hesapları eklenir · (b) Evet, INST_ADMIN de yapabilir | **(a)** — doküman böyle; kod değişmez, seed düzelir | ☐ |
| K4 | **Geri çekilen tanıklığın etkisi** (GUV-05) | (a) VE'ye yeni durum kolonu (migration + append-only istisnası) · (b) VE satırı değişmez; okuma katmanı "aktif tanıklığı kalmayan VE"yi geri çekilmiş sayar | **(b)** — migration yok, append-only korunur | ☐ |
| K5 | **T4 — kurumsuz engagement** (AUTHZ-03) | (a) T4'ü uygula (`DRAFT→ACTIVE`, org üyesi) · (b) MVP dışı: `institution_id` zorunlu | **(b)** — `INSTITUTION_REQUIRED` 422 | ☐ |
| K6 | **Üretim topolojisi** (ENT-07) | (a) Tek origin, reverse proxy `/api` → backend · (b) Alt alan adları + `Domain=` cookie | **(a)** — CSRF/middleware değişmeden çalışır. Kodlama deploy maddesine kalır; O-02 dokümante eder | ☐ |
| K7 | **E-posta doğrulama kapsamı** (IS-08) | (a) Tüm yazma uçları (`/auth/*` ve logout hariç) · (b) Yalnız kritik uçlar (engagement, evidence, evaluation, attestation) · (c) Hiç (kararı belgele) | **(a)** + seed kullanıcıları doğrulanmış + yeniden gönderme ucu | ☐ |
| K8 | **Engagement tarihleri** (IS-02) | (a) Yalnız oluştururken · (b) Oluştururken + `PATCH /engagements/{id}/dates` | **(b)** — ACTIVE'de bitiş tarihi sonradan girilir; DRAFT/PENDING_APPROVAL/ACTIVE'de, org üyesi veya talent sahibi, `version` kilidiyle | ☐ |
| K9 | **Kanıt taraması** (IS-07) | (a) Worker'da magic-byte + boyut kontrolü → CLEAN/INFECTED · (b) ClamAV | **(a)** — ClamAV PLAN 5.3'te | ☐ |
| K10 | **Skill sinyal kuralları** (GUV-04, IS-06) | TALENT_TO_ORG sinyal üretmesin (zorunlu) · teslim sinyali MODERATE→WEAK? · silinen claim için tombstone? | TALENT_TO_ORG **hiç sinyal üretmez**; teslim sinyali **WEAK**; silinen claim için **NONE tombstone** (supersede) | ☐ |

---

## 3. İş bölümü ve dosya sahipliği

**Kişi A — Backend: güvenlik, yetki, altyapı** (auth, oturum, yetkilendirme çekirdeği,
worker, MinIO, kanıt backend'i, seed, bağımlılıklar, test altyapısı)

**Kişi B — Zincir iş kuralları + frontend** (engagement tarihleri/durum makinesi, tanıklık,
değerlendirme, skill sinyalleri, public doğrulama, `/me`, tüm frontend ekranları)

| Dosya / alan | Sahip | Not |
|---|---|---|
| `backend/app/services/auth.py`, `app/api/auth.py`, `app/core/*` | **A** | |
| `backend/app/api/deps.py`, `app/services/authorization.py` | **A** | B-04 okuma sorgusu için `authorization.py`'ye fonksiyon ekleyebilir → A'ya haber ver |
| `backend/app/workers/*`, `app/services/outbox.py`, `app/services/storage.py` | **A** | |
| `backend/app/services/evidence.py`, `app/api/evidence.py`, `app/schemas/evidence.py` | **A** | |
| `backend/app/services/institution.py`, `organization.py`, `reminder.py`, `api/institutions.py`, `api/organizations.py` | **A** | İstisna: B-12 link-request uçları → A-09'dan **sonra** |
| `backend/scripts/seed.py` | **A** | B-04 public_token backfill'i için A-05'ten sonra küçük ekleme yapabilir |
| `backend/tests/conftest.py`, CI (`.github/workflows/ci.yml`) | **A** (backend), **B** (frontend job) | |
| `backend/requirements.txt`, `docker-compose.yml`, `baslat.bat`, `.env.example` | **A** | |
| `backend/app/services/engagement.py`, `app/api/engagements.py` | **B** | A-08 (AUTHZ-01) Senkron-1'den sonra dokunur |
| `backend/app/services/attestation.py`, `evaluation.py`, `skill_signal.py`, `skill_claim.py`, `verified_experience.py`, `talent.py` | **B** | A-08 Senkron-1'den sonra dokunur |
| `backend/app/api/public.py`, `me.py`, `verified_experiences.py`, `skill_signals.py`, `talent_skills.py` | **B** | |
| `backend/app/services/skill.py`, `api/admin.py` | **B** (B-12, B-13) | |
| `frontend/**` | **B** | |
| `backend/alembic/versions/*` (yeni migration) | Yazan kişi | **Aynı gün iki kişi migration açmaz** — `alembic heads` tek başlı kalmalı; açmadan önce diğerine haber ver |
| `HATA.md`, bu dosya, `PLAN.md` | Herkes | Yalnız kendi satırlarını işaretle; çatışma olursa ikisini de koru |

---

## 4. Takvim

Gün 1 = 29 Eylül Pzt · Gün 9 = 7 Ekim Salı (kod dondurma) · 8 Ekim demo provası.

| Gün | Tarih | Kişi A | Kişi B |
|---|---|---|---|
| 0 | 28 Eyl | O-00 (PLAN maddeleri) · kararlar K1–K10 | kararlar K1–K10 |
| 1 | 29 Eyl | **A-05** seed demo düzeltmesi · **A-01** giriş kilitleme · **A-02** logout | **B-01** CSRF retry · **B-02** `/me` rol + durum etiketleri + admin linkleri |
| 2 | 30 Eyl | **A-03** MinIO/bucket/.env.example · **A-04** outbox worker | **B-03** engagement tarihleri |
| 3 | 1 Eki | **A-06** kanıt backend (tarama + liste + sertleştirme) | **B-04** public token + görünürlük + revoke okuma |
| 4 | 2 Eki | **A-07** e-posta doğrulama zorunluluğu | **B-05** skill sinyal kuralları · **B-06** durum makinesi |
| — | 2 Eki akşam | **🔄 SENKRON-1 (O-01):** A-01…A-07 ve B-01…B-06 main'de; ikiniz de rebase; tam test | |
| 5 | 3 Eki | **A-08** çoklu rol (AUTHZ-01) — büyük iş | **B-07** değerlendirme FE bağlama · **B-08** engagement oluşturma + teslim ekranları |
| 6 | 4 Eki | **A-08** devam · **A-09** davet uçları | **B-09** kanıt FE bağlama · **B-10** tanıklık/geri çekme/paylaşım ekranları |
| 7 | 5 Eki | **A-10** kayıt zamanlama + hız sınırı · **A-11** bağımlılıklar · **A-12** DB kısıtları | **B-10** devam · **B-11** frontend testleri + CI |
| 8 | 6 Eki | **A-13** test izolasyonu · **A-14** hata biçimi · **A-15** alan adı/DNS/hatırlatma | **B-12** bağlanma talepleri + admin kuyruğu · **B-13** profil + küçükler |
| 9 | 7 Eki | **O-02** son doğrulama + uçtan uca duman testi (ikiniz birlikte) → PLAN 3.16 dondurma | |

**Bağımlılık grafiği (ok = "önce bitmeli")**

```
A-05 ──► B-04 (backfill seed'e eklenir)        A-03 ─┬─► A-06 ──► B-09
A-05 ──► A-07 (seed kullanıcıları doğrulanmış)  A-04 ─┘
B-03 ─┐                                         B-02 ──► B-10 (rol bilgisi)
B-04 ─┼─► SENKRON-1 ──► A-08 ──► A-09          B-03 ──► B-08
B-05 ─┤                                         B-04 ──► B-10, A-12 (trigger VE.visibility/public_token'a izin vermeli)
B-06 ─┘                                         A-09 ──► B-12
A-13, B-11 ──► O-02                             hepsi ──► O-02
```

**Öncelik kuralı:** Zaman yetmezse şu sırayla kes: A-15 → B-13 → A-14 → A-10 → B-12 → A-12.
**Kesilemez (demo zinciri):** A-05, A-01, A-03, A-04, A-06, B-01, B-02, B-03, B-04, B-07, B-08,
B-09, B-10, O-02.

---

## 5. İş listesi

| ✓ | ID | Başlık | HATA ID'leri | PLAN | Öncelik | Gün | Zincir |
|---|---|---|---|---|---|---|---|
| [ ] | O-00 | PLAN.md'ye maddeleri ekle, .mcp.json kontrolü | L-15 | — | — | 0 | Z-DOC |
| [ ] | A-01 | Giriş kilitleme sayacı gerçekten kalıcı olsun | GUV-01, L-03 | 3.24 | KRİTİK | 1 | Z-GÜV |
| [ ] | A-02 | Logout refresh token ailesini iptal etsin | GUV-06, L-04 | 3.25 | YÜKSEK | 1 | Z-GÜV |
| [ ] | A-03 | MinIO bucket, healthcheck, depolama hataları, .env.example | OPS-03, (eski 3.20) | 3.26, 3.20 | KRİTİK | 2 | Z-STD |
| [ ] | A-04 | Outbox worker: döngü, tıkanma, e-posta linkleri | OPS-01, OPS-02 | 3.27 | KRİTİK | 2 | Z-STD |
| [ ] | A-05 | Seed demo düzeltmesi: COORDINATOR, T2 org, doğrulanmış e-posta | AUTHZ-02, IS-02 (seed) | 3.28 | KRİTİK | 1 | Z-STD |
| [ ] | A-06 | Kanıt backend'i: tarama, liste ucu, kayıt sertleştirme | IS-07, GUV-12 | 3.29 | KRİTİK | 3 | Z-GÜV |
| [ ] | A-07 | E-posta doğrulama zorunluluğu + yeniden gönderme | IS-08 (eski 3.21) | 3.21 | YÜKSEK | 4 | Z-GÜV |
| [ ] | A-08 | Çoklu rol: kapsam sorguları `kind`'dan bağımsız | AUTHZ-01, GUV-02 (DoS), AUTHZ-02 (kod), L-08 | 3.30 | YÜKSEK | 5-6 | Z-GÜV |
| [ ] | A-09 | Davet uçları: 500, numaralandırma, rol doğrulama | GUV-07, GUV-02 (K1), L-01 | 3.31 | YÜKSEK | 6 | Z-GÜV |
| [ ] | A-10 | Kayıt zamanlama + kimlik uçlarına hız sınırı | GUV-10, GUV-11 | 3.32 | ORTA | 7 | Z-GÜV |
| [ ] | A-11 | Bağımlılık yükseltmeleri + secrets baseline | DEP-01, L-16 | 3.33 | YÜKSEK | 7 | Z-BAĞ |
| [ ] | A-12 | DB kısıtları: append-only trigger, claimed_level, timestamptz | VER-01, VER-02, VER-03 | 3.34 | ORTA | 7 | Z-STD |
| [ ] | A-13 | Backend test izolasyonu + fixture rollback semantiği | TEST-01 (backend), TEST-02 (eski 3.22) | 3.22 | YÜKSEK | 8 | Z-TEST |
| [ ] | A-14 | Hata yanıt biçimi, 307'ler, prod ayarları | OPS-04, ENT-06 (inst/org), L-07, L-11, L-12, L-14 | 3.35 | ORTA | 8 | Z-STD |
| [ ] | A-15 | Alan adı gaspı, DNS transaction, hatırlatma sınırları | GUV-09, AUTHZ-04, GUV-13 | 3.36 | ORTA | 8 | Z-GÜV |
| [ ] | B-01 | Refresh sonrası CSRF başlığı yeniden okunsun | ENT-03, L-13 | 3.37 | KRİTİK | 1 | Z-GÜV |
| [ ] | B-02 | `/me` rol bilgisi, admin linkleri, durum etiketleri, 307 | ENT-04, ENT-05, IS-04 (UI), ENT-06 (signals/VE) | 3.38 | KRİTİK | 1 | Z-UI |
| [ ] | B-03 | Engagement tarihleri (oluşturma + PATCH) | IS-02 | 3.39 | KRİTİK | 2 | Z-GÜV |
| [ ] | B-04 | Public token, VE görünürlüğü, geri çekme okuma filtresi | IS-01, GUV-05, GUV-03 (gösterim), L-05 | 3.40 | KRİTİK | 3 | Z-GÜV |
| [ ] | B-05 | Skill sinyal ve tanıklık kuralları | GUV-04, IS-05, IS-06 | 3.41 | YÜKSEK | 4 | Z-GÜV |
| [ ] | B-06 | Durum makinesi dokümana uysun | AUTHZ-03, IS-03, GUV-08 | 3.42 | YÜKSEK | 4 | Z-GÜV |
| [ ] | B-07 | Değerlendirme formu gerçek backend'e | ENT-02 (eval), eski 3.18, 3.19 (kısmi) | 3.18 | KRİTİK | 5 | Z-UI |
| [ ] | B-08 | Engagement oluşturma + teslim ekranları | ENT-01 (a) | 3.43 | KRİTİK | 5 | Z-UI |
| [ ] | B-09 | Kanıt yükleme gerçek backend'e | ENT-02 (evidence), eski 3.17, 3.19 | 3.17 | KRİTİK | 6 | Z-UI |
| [ ] | B-10 | Tanıklık, geri çekme, deneyim paylaşımı ekranları | ENT-01 (b), IS-01 (UI) | 3.44 | KRİTİK | 6-7 | Z-UI |
| [ ] | B-11 | Frontend testleri + CI'da vitest | TEST-01 (frontend) | 3.45 | YÜKSEK | 7 | Z-TEST |
| [ ] | B-12 | Kurum bağlanma talepleri + admin kuyruğu reddi | IS-10, IS-11 | 3.46 | ORTA | 8 | Z-GÜV |
| [ ] | B-13 | Profil düzeltmeleri, skill yönetimi, frontend bağımlılığı | IS-09, DEP-02, L-06, L-10 | 3.47 | ORTA | 8 | Z-STD |
| [ ] | O-01 | Senkron-1 entegrasyon kontrolü | — | — | — | 4 | — |
| [ ] | O-02 | Son doğrulama + uçtan uca duman testi + HATA.md kapanışı | eski 3.23, 2.14, ENT-07 (K6 dokümanı) | 3.23 | KRİTİK | 9 | Z-SON |

---

## 6. Skill zincirleri

Prompt'lardaki "Zincir" alanı bunlardan birini gösterir. Skill'ler `Skill` aracıyla ya da
`/ad` yazarak çağrılır.

| Kod | Ne zaman | Zincir |
|---|---|---|
| **Z-GÜV** | Auth, yetki, yeni endpoint, dosya yükleme, kişisel veri, kiracı sınırı | `/atdd` → `threat-model` → `plan` → (`authz-test` — threat-model yetki AC-S'si ürettiyse **zorunlu**) → `test-copilot` → `code-copilot` → `verify` (içinde `security-scan` gate'i) → `red-team` → kullanıcı onayı → `/bitir` |
| **Z-STD** | Backend iş kuralı / altyapı, yeni endpoint yok | `/atdd` → `plan` → `test-copilot` → `code-copilot` → `verify` → `red-team` → onay → `/bitir` |
| **Z-UI** | Frontend ekran/akış | `/atdd` → `plan` → `test-copilot` → `code-copilot` → `verify` (UI gate'leri: `vision-test`, `frontend-audit` araçları) → `red-team` → onay → `/bitir` |
| **Z-BAĞ** | Bağımlılık yükseltme | ONAY → yükselt → `security-scan` → `verify` (tüm backend + frontend paketi) → onay → `/bitir` |
| **Z-TEST** | Yalnız test/CI düzeltmesi | Kırmızıları tek tek teşhis et (kök neden yazılı) → düzelt → `verify` → onay → `/bitir` |
| **Z-DOC** | Yalnız doküman | Doğrudan düzenle → onay → commit |
| **Z-SON** | Kapanış | `verify` (tam) → `security-scan` → `frontend-audit` → uçtan uca senaryo → `postmortem` |

Notlar:
- `test-copilot` ve `code-copilot` kodu bir alt-ajana yazdırır; Sonnet orkestre eder ve
  sonucu **okuyup doğrular**. Z-STD işlerde zaman darsa bu iki adım atlanıp Sonnet testi
  ve kodu kendisi yazabilir (**hafif yol**) — ama **Z-GÜV işlerde atlanmaz**.
- `fast-track` yalnız tek dosyalık, auth/yetki dışı, test gerektirmeyen değişikliklerde
  (ör. bir metin/etiket). Auth'a dokunan hiçbir kod fast-track ile yazılmaz.
- Artifact'lar `obss_project/artifacts/<task-slug>/` altına yazılır; slug prompt'ta verildi.
- Oturum kapanacaksa `handoff`; iş bittiğinde `/bitir`.

---

## 7. Prompt'lar — Ortak

### O-00 · PLAN.md'ye maddeleri ekle

| Sahip | PLAN | Öncelik | Gün | Zincir | Dal |
|---|---|---|---|---|---|
| Kişi A | — | — | 0 | Z-DOC | `docs/3.24-hata-duzeltme-maddeleri` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: O-00 — HATA_DUZELTME_PROMPT.md §5 iş listesindeki maddeleri PLAN.md'ye ekle.

YAPILACAKLAR:
1. PLAN.md'yi oku. "Plan bakım kuralları" bölümünü uygula: madde silinmez, yeni madde ilgili
   fazın sonuna eklenir, her madde TEK SATIR, detay docs/'a (burada HATA.md'ye) referansla.
2. Faz 3'te 3.23'ten sonra, 3.16'dan (kod dondurma) ÖNCE şu yeni maddeleri ekle — numara ve
   başlık §5 tablosundaki gibi, sahip etiketi: Kişi A işleri için @be2, Kişi B işleri için
   @fe (backend ağırlıklı B işleri için @be1 — B-03, B-04, B-05, B-06). Format örneği:
   - [ ] 3.24 Giriş kilitleme sayacı kalıcı olsun (HATA GUV-01) @be2
   Eklenecekler: 3.24–3.47 (§5'teki PLAN sütunu). 3.17, 3.18, 3.20, 3.21, 3.22, 3.23
   zaten var — onlara dokunma, yalnız satır sonuna "(HATA_DUZELTME_PROMPT <ID>)" ekle.
3. Mevcut 3.17–3.23'ün altındaki uzun ">" not bloklarını SİLME (kural 1).
4. `.mcp.json` repoda izlenmiyor ve .gitignore'da yok (HATA.md L-15). İçeriğini oku: erişim
   anahtarı/token/parola içeriyorsa .gitignore'a `.mcp.json` ekle ve içeriğini çıktıya YAZMA,
   sadece "sır içeriyor/içermiyor" de. Sır yoksa kullanıcıya commit'lenip commit'lenmeyeceğini sor.

KABUL: PLAN.md'de 3.24–3.47 var, her biri tek satır; `git diff PLAN.md` yalnız ekleme gösteriyor.
Commit mesajı: "PLAN: HATA.md düzeltme maddeleri eklendi (3.24–3.47)". Commit için onay iste.
```

---

## 8. Prompt'lar — Kişi A

### A-01 · Giriş kilitleme sayacı gerçekten kalıcı olsun

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.24 | GUV-01, L-03 | KRİTİK | 1 | — | Z-GÜV | `fix/3.24-giris-kilitleme` | `a01-giris-kilitleme` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-01 — HATA.md GUV-01 ve L-03. PLAN 3.24.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → authz-test → test-copilot → code-copilot →
verify → red-team. Artifact slug: a01-giris-kilitleme. Commit yalnız ben onaylayınca /bitir.
Bu bir KİMLİK DOĞRULAMA değişikliği: plan.md hazır olunca kod yazmadan ÖNCE bana özetle,
onay bekle (ONAY NOKTASI).

BAĞLAM (HATA.md GUV-01'i de oku):
- backend/app/services/auth.py `authenticate()` yanlış parolada `user.failed_login_count += 1`
  yapıp gerekirse `locked_until` set ediyor, DENIED audit yazıyor, sonra `InvalidCredentials`
  fırlatıyor.
- backend/app/api/auth.py bunu ApiError(401)'e çeviriyor. backend/app/core/deps.py
  `get_session` istisnayı görünce `session.rollback()` yapıyor → sayaç ve audit HİÇ
  kaydedilmiyor. Canlı kanıt: seed kullanıcısıyla 3 yanlış giriş → failed_login_count 0,
  DENIED audit 0.
- Aynı tuzak `refresh_tokens()` içinde fark edilmiş ve istisnadan önce `session.commit()`
  yapılarak çözülmüş (auth.py'de "Commit it now, before raising" yorumu). Aynı deseni kullan.
- Testler neden yeşil: tests/conftest.py `override_get_session` istisnada rollback yapmıyor
  (HATA.md TEST-02). Bu yüzden mevcut `test_login_locks_account_after_repeated_failures`
  yanıltıcı biçimde geçiyor.

DOĞRULA (kod yazmadan):
1. authenticate() ve get_session'ı oku; hatanın hâlâ var olduğunu teyit et.
2. İstersen canlı teyit: backend/.venv ile TestClient(app) (override'sız) + seed kullanıcısı
   `ogrenci1@seed.local` ile 3 yanlış giriş, sonra users.failed_login_count'u oku. (Sonunda
   doğru parolayla bir giriş yapıp sayacı sıfırla.)

YAPILACAKLAR:
1. Başarısız giriş yolunda (kullanıcı var + parola yanlış) sayaç artışı, gerekirse
   locked_until ve DENIED audit kaydı istisna fırlatılmadan önce KALICI olsun
   (`session.commit()`; refresh_tokens'taki yorum tarzıyla neden orada olduğunu açıkla).
   Kullanıcı yoksa da DENIED audit kalıcı olsun.
2. Kilitli hesap yolu (`AccountLocked`): DENIED audit yaz (metadata'ya {"reason": "locked"};
   e-posta YAZMA) ve kalıcı yap.
3. Kilit süresi dolmuşsa (locked_until <= now) sayacı sıfırla ki süresi dolan hesap tek bir
   yanlış denemede yeniden kilitlenmesin; locked_until'i None yap.
4. L-03: `user.status` 'SUSPENDED' veya 'DELETED' ise authenticate() InvalidCredentials
   fırlatsın (parola doğru olsa bile; ayırt edici mesaj YOK — numaralandırma koruması).
   refresh_tokens() de token'ın kullanıcısı ACTIVE/PENDING değilse InvalidRefreshToken.
5. Sabitler (10 deneme, 15 dk) değişmesin.

KABUL KRİTERLERİ (atdd.md'ye AC olarak yaz):
- AC-1: Var olan kullanıcıya yanlış parola → 401 ve DB'de failed_login_count +1 (gerçek
  get_session semantiğiyle doğrulanmış).
- AC-2: 10. yanlış denemede locked_until ≈ now+15dk; 11. denemede doğru parolayla bile 423.
- AC-3: Her başarısız deneme için audit_events'te USER_LOGIN/DENIED satırı kalıcı.
- AC-4: Kilit süresi dolduktan sonra doğru parola → 200, sayaç 0.
- AC-5: SUSPENDED kullanıcı doğru parolayla → 401 INVALID_CREDENTIALS (aynı mesaj).
- AC-6: Başarılı giriş davranışı değişmedi (cookie'ler, yanıt gövdesi).
DAVRANIŞ SÖZLEŞMESİ tablosu: yanlış parola → 401 INVALID_CREDENTIALS; kilitli → 423
ACCOUNT_LOCKED; askıdaki → 401 INVALID_CREDENTIALS; olmayan e-posta → 401 INVALID_CREDENTIALS.

TEST NOTU: Rollback'i gerçekten sınayan en az bir test yaz. Seçenek: testte
app.dependency_overrides[get_session] yerine, üretimdeki gibi `yield` + istisnada savepoint
rollback yapan bir generator override kullan (sadece bu test dosyasında). A-13 bu override'ı
genelleştirecek; burada yerel tut.

KAPSAM DIŞI: IP bazlı hız sınırı (A-10), kayıt zamanlaması (A-10).

DOĞRULAMA: pytest tests/authorization -q (tamamı) + pytest tests -q -k "auth or login" ;
bilinen kırık listesi (§1.7) dışında yeni kırık olmamalı.
BİTİŞ: §1.9.
```

### A-02 · Logout refresh token ailesini iptal etsin

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.25 | GUV-06, L-04 | YÜKSEK | 1 | — | Z-GÜV | `fix/3.25-logout-refresh-iptal` | `a02-logout-refresh` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-02 — HATA.md GUV-06 ve L-04. PLAN 3.25.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → test-copilot → code-copilot → verify → red-team.
Slug: a02-logout-refresh. ONAY NOKTASI: auth değişikliği — plan.md sonrası kod öncesi onay.

BAĞLAM:
- backend/app/api/auth.py `_set_auth_cookies`: refresh_token cookie'si `path="/auth/refresh"`.
  Tarayıcı bu cookie'yi `/auth/logout`'a GÖNDERMEZ. `logout()` içinde
  `request.cookies.get("refresh_token")` her zaman None → aile iptali hiç çalışmıyor.
  Çalınmış refresh token logout sonrası 30 gün geçerli kalıyor.
- L-04: `_ACCESS_TOKEN_MAX_AGE = 15*60` ve `_REFRESH_TOKEN_MAX_AGE` sabit; settings'teki
  `access_token_ttl_minutes` / `refresh_token_ttl_days` değişirse cookie ile JWT ayrışır.

DOĞRULA: auth.py cookie path'ini ve logout akışını oku; frontend/lib/session/use-session.ts
logout çağrısını (`POST /auth/logout`) teyit et.

YAPILACAKLAR (öneri — daha iyisini görürsen söyle):
1. Refresh cookie path'ini `/auth` yap: hem /auth/refresh hem /auth/logout alır.
   `_clear_auth_cookies` hem YENİ path'i (`/auth`) hem ESKİ path'i (`/auth/refresh`) silsin —
   eski oturumlardaki cookie'ler temizlensin.
2. Savunma katmanı: logout, cookie gelmese bile kullanıcının TÜM aktif (revoked_at IS NULL)
   refresh token'larını iptal etsin mi? → Bu "tüm cihazlardan çıkış" demek. KULLANICIYA SOR;
   varsayılan: yalnız sunulan token'ın ailesi + cookie yoksa kullanıcının tüm aileleri.
3. Cookie max_age'leri settings'ten türet (dakika*60, gün*86400).
4. frontend/lib/api/client.ts refresh çağrısı değişmeyecek (path aynı: /auth/refresh) — teyit et.

KABUL:
- AC-1: Giriş → logout → eski refresh cookie ile /auth/refresh → 401 INVALID_REFRESH_TOKEN.
- AC-2: Logout yanıtı eski ve yeni path'teki refresh cookie'lerini siler (Set-Cookie başlıkları).
- AC-3: Refresh akışı (rotasyon, reuse tespiti) değişmedi — mevcut testler yeşil.
- AC-4: Cookie max_age = settings TTL.
TEST: tests/authorization/test_auth_refresh_real_session.py deseniyle gerçek cookie akışı
(override'sız get_current_user) kullanan bir test ekle; tarayıcının path kuralını taklit etmek
için TestClient cookie jar'ının path'e göre cookie gönderdiğini doğrula (göndermiyorsa testte
path eşleşmesini açıkça sına: Set-Cookie başlığındaki Path=/auth).

DOĞRULAMA: pytest tests/authorization -q (tamamı) + frontend: npm run typecheck.
BİTİŞ: §1.9.
```

### A-03 · MinIO bucket, healthcheck, depolama hataları, .env.example

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.26 + 3.20 | OPS-03, eski 3.20 | KRİTİK | 2 | — | Z-STD | `chore/3.26-minio-bucket` | `a03-minio-bucket` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-03 — HATA.md OPS-03 + PLAN 3.20 (.env.example). PLAN 3.26.
ZİNCİR (Z-STD, hafif yol serbest): /atdd → plan → (test+kod) → verify → red-team. Slug: a03-minio-bucket.
ONAY NOKTALARI: docker-compose.yml değişikliği ve baslat.bat değişikliği onay gerektirir.

BAĞLAM:
- `yetkin360-evidence` bucket'ını oluşturan hiçbir kod/betik yok. Taze kurulumda presigned
  POST `NoSuchBucket` ile düşer.
- `docker compose ps` → minio `unhealthy`. Healthcheck `curl` kullanıyor; imaj
  `cgr.dev/chainguard/minio:latest` — muhtemelen curl yok. İmaj etiketi sabitlenmemiş.
- backend/app/api/evidence.py upload-url yalnız EndpointConnectionError/ConnectTimeoutError
  yakalıyor; bucket yok/yetki hatası gibi botocore ClientError'lar 500'e düşüyor.
  storage.generate_presigned_get_url aynı.
- Tarayıcıdan MinIO'ya presigned POST için CORS (localhost:3000 origin) gerekebilir.
- PLAN 3.20: `.env.example`'da `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` olduğu
  raporlanmıştı; backend'de /api/v1 öneki yok. (.env.example placeholder dosyası, okuyabilirsin;
  .env'i OKUMA.)

DOĞRULA:
1. `docker compose ps` ve `docker inspect --format '{{json .State.Health}}' yetkin360-minio-1`
   ile unhealthy nedenini gör (log'u oku, sır içeren env'i yazdırma).
2. `grep -rn create_bucket backend/app backend/scripts` → yok olduğunu teyit et.
3. .env.example'da NEXT_PUBLIC_API_BASE_URL satırını kontrol et.

YAPILACAKLAR:
1. Bucket'ı idempotent oluşturan tek bir fonksiyon: `app/services/storage.py` içinde
   `ensure_bucket()` (head_bucket → yoksa create_bucket). Çağrı yeri: `scripts/seed.py`
   başlangıcı VE ayrı bir komut `python -m scripts.init_storage` (baslat.bat'ta migration'dan
   sonra çağrılır). Uygulama açılışında (lifespan) ÇAĞIRMA — ağ çağrısı açılışı kilitlemesin.
   Bucket public OLMAYACAK (anonim okuma yok).
2. MinIO CORS: Presigned POST'un tarayıcıdan çalışması için gerekiyorsa bucket CORS'unu
   `ensure_bucket()` içinde `frontend_origin` için ayarla (put_bucket_cors). MinIO sürümü
   bucket-CORS desteklemiyorsa (bazı sürümler yalnız global `MINIO_API_CORS_ALLOW_ORIGIN`
   destekler) docker-compose env'ine ekle — ONAY NOKTASI.
3. Healthcheck: imajda curl yoksa `mc ready local` ya da imajda bulunan başka bir araçla
   değiştir; imaj etiketini sabit bir sürüme çek (latest yerine). ONAY NOKTASI.
4. evidence.py upload-url ve storage.generate_presigned_get_url: botocore `ClientError`'ı da
   yakala → 503 STORAGE_UNAVAILABLE (mesajda bucket/endpoint sızdırma yok; log'a hata kodu yaz,
   PII yok).
5. .env.example: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 (önek yok). docs/ENV.md'de
   aynı değişken varsa uyumla.
6. baslat.bat: migration'dan sonra `python -m scripts.init_storage` adımı (CRLF satır sonlarını
   KORU — dosyanın başındaki not). ONAY NOKTASI.

KABUL:
- AC-1: Boş MinIO'da `python -m scripts.init_storage` → bucket var; ikinci çalıştırma hata vermez.
- AC-2: `docker compose ps` → minio healthy.
- AC-3: Bucket silinmişken POST /evidence/upload-url → 503 STORAGE_UNAVAILABLE (500 değil).
- AC-4: Gerçek MinIO'ya presigned POST ile küçük bir PNG yüklenebiliyor (manuel/entegrasyon
  testi; `requests.post(url, data=fields, files=...)`).
- AC-5: .env.example'da /api/v1 yok.

DOĞRULAMA: pytest tests/test_storage.py tests/test_evidence_upload_url.py
tests/authorization/test_evidence_upload_url.py -q ; docker compose ps.
BİTİŞ: §1.9 (PLAN 3.20'yi de [x] yap).
```

### A-04 · Outbox worker: döngü, tıkanma, e-posta linkleri

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.27 | OPS-01, OPS-02 | KRİTİK | 2 | — | Z-STD | `fix/3.27-outbox-worker` | `a04-outbox-worker` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-04 — HATA.md OPS-01 ve OPS-02. PLAN 3.27.
ZİNCİR (Z-STD): /atdd → plan → test-copilot → code-copilot → verify → red-team. Slug: a04-outbox-worker.
ONAY NOKTASI: baslat.bat değişikliği.

BAĞLAM (HATA.md OPS-01'deki 7 maddeyi oku):
- backend/app/workers/outbox_worker.py `__main__` tek batch işleyip çıkıyor;
  settings.outbox_poll_interval_seconds hiç kullanılmıyor; baslat.bat worker'ı başlatmıyor.
- process_batch handler'ı olmayan topic'leri SEÇİYOR ama işlemiyor, attempts artırmıyor.
  Sorgu ORDER BY created_at LIMIT 10 → kuyruğun başında 10 handler'sız satır birikince worker
  sonsuza dek aynı 10 satırı seçer. Canlı: DB'de 60 işlenmemiş satır (30 email.verify_email,
  15 engagement.pending_approval, 15 attestation.created).
- Handler'sız topic'ler: evidence.scan_requested (A-06 yazacak), engagement.pending_approval,
  attestation.created, email.organization_member_invited, reminder.<template>.
- email.duplicate_registration_attempt SMTP modunda TODO → e-posta gitmeden processed.
- İlk satırın commit'i batch'in tüm FOR UPDATE kilitlerini bırakıyor.
- _resolve_user_email her çağrıda yeni engine açıyor.
- Hata logunda str(e) — SMTP istisnası alıcı adresini içerebilir (PII).
- OPS-02: verify_url = f"{frontend_origin}/verify-email?token=..." ve reset_url
  "/reset-password?token=..." — frontend sayfaları /e-posta-dogrula ve /sifre-sifirla
  (frontend/app/e-posta-dogrula/page.tsx ve sifre-sifirla/page.tsx `token` query param okuyor).

YAPILACAKLAR:
1. Sorguyu handler'ı olan topic'lerle sınırla: `.where(Outbox.topic.in_(handlers.keys()))`.
   reminder.* için prefix eşleşmesi gerekiyorsa açık bir eşleme kur (ör. handler anahtarı
   "reminder.*" → sorguda `topic.like('reminder.%')`), ya da reminder topic'ini tek bir
   "reminder.send" olarak standartlaştır (bu, A-15/reminder.py'yi etkiler — tek topic + template
   payload'da; A-15'e not düş).
2. Eksik handler'lar (MVP: gerçek e-posta göndermeden console/SMTP bildirimi):
   - engagement.pending_approval → kurumun koordinatörlerine e-posta (SMTP modunda; console'da
     print, PII yok).
   - attestation.created → talent'a "deneyimin doğrulandı" e-postası.
   - email.organization_member_invited → davet edilen kullanıcıya bilgi e-postası.
   - reminder → ilgili engagement'ın tarafına hatırlatma.
   - email.duplicate_registration_attempt SMTP dalı: gerçek _send_smtp_email.
   evidence.scan_requested'ı YAZMA (A-06'nın işi) — ama A-06 gelene kadar kuyruğu tıkamaması
   için 1. madde yeterli.
   Her handler kullanıcı e-postasını DB'den kendisi çözer (payload'a e-posta koyma).
3. `run_forever(poll_interval)` döngüsü: her turda yeni Session, process_batch, boşsa uyku.
   SIGINT/SIGTERM'de temiz çıkış. `python -m app.workers.outbox_worker` bunu çağırsın;
   `--once` bayrağı eski tek-batch davranışı için.
4. Kilit semantiği: her satırı kendi transaction'ında işle (satır başına
   SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1 ya da batch'i seçip her satırı ayrı kilitle).
   Handler (ağ çağrısı) açık transaction İÇİNDE çalışmasın: satırı kilitle → payload'ı kopyala →
   ... CLAUDE.md "ağ çağrısı açık transaction içinde yapılmaz" kuralını dikkate al. Pragmatik
   çözüm: satırı `attempts+1` ve `locked_at` ile "claim" edip commit et, handler'ı çalıştır,
   sonra processed_at yaz. (Yeni kolon gerekiyorsa migration → ONAY; gerekmiyorsa attempts
   üzerinden çöz.) Seçimini plan.md'de gerekçelendir.
5. Engine'i modül seviyesinde bir kez oluştur (_resolve_user_email).
6. Hata logu: yalnız `type(e).__name__` ve outbox_id/topic; `str(e)` YAZMA.
7. OPS-02: URL'leri `/e-posta-dogrula?token=` ve `/sifre-sifirla?token=` yap. Frontend
   sayfalarının query param adını (token) tekrar teyit et.
8. baslat.bat: backend'den sonra ayrı pencerede
   `.venv\Scripts\python.exe -m app.workers.outbox_worker` (CRLF koru). ONAY NOKTASI.
9. max_attempts'e ulaşan satırlar için log'a WARNING (outbox_id, topic).

KABUL:
- AC-1: Kuyruğun başında 20 handler'sız satır varken yeni email.verify_email satırı ilk turda işlenir.
- AC-2: Worker `--once` olmadan sürekli çalışır, SIGINT ile temiz çıkar.
- AC-3: Doğrulama/sıfırlama e-postasındaki link frontend'de ilgili sayfayı açar (URL testi).
- AC-4: Handler istisnasında log satırında e-posta adresi yok.
- AC-5: Mevcut outbox testleri (§1.7'deki 9 kırık dahil — onlar seed'li DB'deki birikmiş
  satırlar yüzünden kırık; 1. madde sonrası birçoğu yeşile dönebilir) yeşil ya da kalan
  kırığın nedeni yazılı.
- AC-6: Payload PII guard'ı (outbox.py) gevşemedi.

DOĞRULAMA: pytest tests/test_outbox_worker.py tests/test_outbox_service.py -q ;
elle: worker'ı başlat → yeni bir kullanıcı kaydet → console'da doğru /e-posta-dogrula linki.
BİTİŞ: §1.9.
```

### A-05 · Seed demo düzeltmesi: COORDINATOR, T2 organizasyon, doğrulanmış e-posta

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.28 | AUTHZ-02 (seed), IS-02 (seed), IS-08 (seed) | KRİTİK | 1 | K3 | Z-STD | `fix/3.28-seed-demo` | `a05-seed-demo` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-05 — Seed verisini demo zincirini API/arayüz üzerinden oynatılabilir hale getir.
HATA.md AUTHZ-02 (canlı kanıt), IS-02 (seed notu), IS-08. PLAN 3.28.
ZİNCİR (Z-STD, hafif yol serbest): /atdd → plan → (test+kod) → verify → red-team. Slug: a05-seed-demo.
KARAR: K3 (HATA_DUZELTME_PROMPT.md §2). Seçilmemişse öneri (a): kod değişmez, seed düzelir.

BAĞLAM (canlı DB sayımları, 28 Eylül):
- institution_members: 5 satırın 5'i ADMIN, COORDINATOR yok. Onay (PENDING_APPROVAL→ACTIVE),
  red, iptal, PENDING_EVALUATION geçişi ve tanıklık yalnız principal.kind == "COORDINATOR"
  kabul ediyor (backend/app/services/engagement.py transition_table,
  backend/app/services/attestation.py create_attestation). Seed'in "kurum admin" hesaplarıyla
  bu adımlar API'den yapılamıyor.
- organizations: 5'in 5'i T1 → tüm tanıklıklar ATTESTOR_NOT_VERIFIED_SUPERVISOR ile
  PARTICIPATION'a düşüyor; seed demosunda COMPETENCE hiç görünmüyor (15/15 PARTICIPATION).
- users: 31'in 30'u email_verified_at NULL (yalnız seed admin doğrulanmış). A-07 e-posta
  doğrulamasını zorunlu yapınca seed kullanıcıları hiçbir şey yapamaz.
- Seed idempotent olmalı (baslat.bat her açılışta çalıştırıyor).

DOĞRULA: backend/scripts/seed.py'yi oku; kurum üyesi rollerini, org verification_level'ını,
email_verified_at set edilen yeri bul. tests/test_seed.py'nin neleri doğruladığını oku.

YAPILACAKLAR:
1. Her kurum için ayrı bir COORDINATOR hesabı: `kurumN-koordinator@seed.local`, rol
   COORDINATOR. Bu kullanıcı başka hiçbir kurum/organizasyonda üye OLMAMALI (tek rol — A-08
   gelene kadar `kind` hesaplaması bozulmasın). Mevcut `kurumN-admin` hesapları ADMIN kalsın.
2. En az 2 organizasyonu T2 yap (verification_level='T2', verified_at dolu, domain dolu).
   Demo için en az bir engagement'ın tüm COMPETENCE ön koşullarını sağladığından emin ol:
   süre ≥ 28 gün, ≥1 deliverable, org ≥ T2, tanıklığı kurumun COORDINATOR'ı vermiş.
   Mevcut 15 tanıklık append-only; onlara dokunma. Yeni bir "demo engagement" seti ekle ya da
   seed'in "mevcut değilse oluştur" mantığıyla yeni kayıtlar üret — mevcutları güncelleme.
3. Ayrıca zincirin CANLI oynatılabilmesi için tanıklığı YAPILMAMIŞ engagement'lar ekle:
   en az 1 × PENDING_APPROVAL (koordinatör onaylayacak), 1 × ACTIVE + deliverable'lı
   (org değerlendirmeye gönderecek), 1 × PENDING_EVALUATION (org değerlendirecek),
   1 × EVALUATED (koordinatör tanıklık verecek). Hepsi T2 org + koordinatörlü kurum ile.
4. Tüm seed kullanıcılarında email_verified_at = now (idempotent: yalnız NULL ise).
5. baslat.bat'ın sonundaki giriş bilgileri bloğuna koordinatör hesaplarını ekle
   (CRLF koru). ONAY NOKTASI (baslat.bat).
6. Seed'in prod koruması (ENVIRONMENT=production'da çalışmaz) korunmalı.
7. B-04 bu seed'e public_token backfill'i ekleyecek — ona yer bırak (ayrı fonksiyon).

KABUL:
- AC-1: `python -m scripts.seed` iki kez üst üste hatasız; ikinci çalıştırma yeni satır üretmez.
- AC-2: kurum1-koordinator ile giriş → PENDING_APPROVAL engagement'ı API ile ACTIVE yapabilir (200).
- AC-3: EVALUATED demo engagement'ına koordinatör tanıklığı → claim_type COMPETENCE, downgrade_reasons [].
- AC-4: Seed kullanıcılarının hepsi email_verified_at dolu.
- AC-5: tests/test_seed.py yeşil (§1.7'deki 3 bilinen kırık hariç — onlar A-13'te).
DOĞRULAMA: pytest tests/test_seed.py -q ; seed'i iki kez çalıştır ; TestClient ile AC-2/AC-3.
BİTİŞ: §1.9. HATA.md AUTHZ-02'yi "◐ KISMEN — seed düzeldi, INST_ADMIN kod kararı K3/A-08" işaretle.
```

### A-06 · Kanıt backend'i: tarama, liste ucu, kayıt sertleştirme

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.29 | IS-07, GUV-12 | KRİTİK | 3 | A-03, A-04, K9 | Z-GÜV | `fix/3.29-kanit-tarama-liste` | `a06-kanit-backend` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-06 — HATA.md IS-07 ve GUV-12. PLAN 3.29.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → authz-test → test-copilot → code-copilot →
verify (security-scan gate'i dahil) → red-team. Slug: a06-kanit-backend.
KARAR: K9 (öneri: worker'da magic-byte + boyut). ONAY NOKTALARI: yeni endpoint + olası migration.
ÖN KOŞUL: A-03 (bucket) ve A-04 (worker döngüsü) main'de olmalı. Değilse dur ve söyle.

BAĞLAM:
- POST /evidence `evidence.scan_requested` outbox satırı yazıyor; handler yok → scan_status
  hep PENDING → GET /evidence/{id}/download-url hep 409 SCAN_NOT_CLEAN.
- Talent'ın kendi kanıtlarını listeleyeceği uç yok (frontend bu yüzden localStorage kullanıyor —
  B-09 bu uca bağlanacak).
- POST /evidence: nesnenin MinIO'da varlığı/boyutu/tipi kontrol edilmiyor; mime_type
  allowlist'e göre doğrulanmıyor; size_bytes üst sınırı yok; aynı storage_key tekrar tekrar
  kaydedilebiliyor. Magic-byte kontrolü hiçbir yerde yok (CLAUDE.md: "uzantıya güvenilmez").
- Hız sınırı süreç içi (storage.py _rate_limit_counters): anahtarlar hiç temizlenmiyor;
  POST /evidence talent_id None iken "None" anahtarını paylaşıyor.

YAPILACAKLAR:
1. Worker handler `evidence.scan_requested` (A-04'ün handler kayıt yapısına):
   - Satırı DB'den oku; nesneyi MinIO'dan ilk ~8 KB + head_object (ContentLength,
     ContentType) ile al. Ağ çağrıları açık DB transaction'ı DIŞINDA.
   - Magic-byte eşleşmesi: PDF `%PDF-`, PNG `\x89PNG\r\n\x1a\n`, JPEG `\xFF\xD8\xFF`,
     DOCX `PK\x03\x04` (+ zip içinde `word/` — ilk KB'lerde central directory olmayabilir; MVP
     için PK imzası + boyut yeterli, bunu atdd Risks'e yaz). Beyan edilen mime_type ile eşleşmeli.
   - Boyut: head_object ContentLength == evidence.size_bytes ve ≤ settings.evidence_max_size_bytes.
   - Sonuç: hepsi tamam → CLEAN; imza/tip uyuşmazlığı → INFECTED; nesne yok/okunamadı → FAILED.
     content_hash (sha256) hesaplanabiliyorsa yaz (tam dosyayı akış halinde oku; 10 MB sınırı var).
   - Evidence güncellemesi (scan_status, content_hash) — modelde mutable alanlar olarak
     belgelenmiş; audit event yaz (evidence.scanned, result).
2. POST /evidence sertleştirme (service katmanında):
   - mime_type ALLOWED_CONTENT_TYPES içinde olmalı → değilse 422 UNSUPPORTED_CONTENT_TYPE.
   - size_bytes ≤ evidence_max_size_bytes → değilse 422 FILE_TOO_LARGE.
   - storage_key biçimi: tam olarak `evidence/{talent_id}/{uuid}.{ext}` regex'i; `..` ve ek
     segment reddi; ext mime_type ile uyumlu.
   - Aynı storage_key ikinci kez → 409 EVIDENCE_ALREADY_REGISTERED. DB'de UNIQUE kısıt ekle
     (migration → ONAY; mevcut veride çakışma olmadığını önce SELECT ile doğrula). A-12 ile
     aynı gün migration açmayın (§3).
   - Nesne varlığı: POST /evidence sırasında head_object ÇAĞIRMA (ağ çağrısı transaction içinde
     olur) — varlık ve boyut kontrolünü worker yapar (1. madde). Bunu atdd'de açıkça yaz.
3. Yeni uç: GET /evidence (talent'ın kendi kanıtları, deleted_at IS NULL, created_at DESC,
   limit/offset ≤ 100). scoped_evidence() üzerinden. Yanıt EvidenceResponse listesi
   ({items: [...]}), storage_key DAHİL etme mi? → frontend ihtiyacı yok; iç bilgi — çıkar
   ve EvidenceResponse'tan da çıkarılabilir mi değerlendir (B-09 ile konuş, sözleşmeyi
   docs/API.md'ye yaz). Yetkilendirme testi ZORUNLU: talent B, talent A'nın kanıtını görmez;
   org üyesi/koordinatör boş liste alır.
4. Hız sınırlayıcı: eski zaman damgası listeleri boşalınca anahtarı sil (bellek sızıntısı);
   talent_id None iken 403'ü rate limit'ten ÖNCE dön.
5. docs/API.md'ye GET /evidence sözleşmesini ekle.

KABUL:
- AC-1: Geçerli PNG yükle → POST /evidence → worker turu → scan_status CLEAN → download-url 200.
- AC-2: PNG içeriği .pdf/mime application/pdf olarak beyan → INFECTED → download-url 409.
- AC-3: Nesne yüklenmeden kayıt → FAILED.
- AC-4: Aynı storage_key ikinci kez → 409.
- AC-5: GET /evidence yalnız kendi kanıtları; başka talent'ınki listede yok (authz testi).
- AC-6: mime_type allowlist dışı → 422; size_bytes > sınır → 422.
DOĞRULAMA: pytest tests/authorization -q (tamamı) + tests/test_evidence_service.py +
tests/authorization/test_evidence_record_download.py + yeni testler; migration varsa
alembic upgrade head && alembic downgrade -1 && alembic upgrade head.
BİTİŞ: §1.9. B-09'a (Kişi B) GET /evidence yanıt şemasını ilet (PR açıklamasına yaz).
```

### A-07 · E-posta doğrulama zorunluluğu + yeniden gönderme

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.21 | IS-08 | YÜKSEK | 4 | A-04, A-05, K7 | Z-GÜV | `fix/3.21-eposta-dogrulama-zorunlu` | `a07-eposta-dogrulama` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-07 — HATA.md IS-08, PLAN 3.21. ZİNCİR (Z-GÜV). Slug: a07-eposta-dogrulama.
KARAR: K7 (öneri (a): /auth/* ve logout hariç tüm yazma uçları).
ONAY NOKTASI: yetkilendirme/kimlik doğrulama değişikliği — plan sonrası onay.
ÖN KOŞUL: A-05 (seed kullanıcıları doğrulanmış) ve A-04 (e-postalar gerçekten gidiyor) main'de.
DOSYA NOTU: Bu iş B'nin router dosyalarına (engagements.py, me.py, talent_skills.py) yalnız
`Depends` ekler — commit mesajında belirt, B'ye haber ver.

BAĞLAM:
- backend/app/core/deps.py `require_email_verified()` tanımlı, hiçbir yerde kullanılmıyor.
  Docstring'i "no write succeeds until the account's email is verified" diyor (docs/API.md §2.1,
  docs/AUTHORIZATION.md G6).
- Doğrulama linkini yeniden gönderme ucu yok; 24 saatte tıklanmazsa kullanıcı kalıcı doğrulanmamış.
- frontend/lib/api/client.ts 401 EMAIL_NOT_VERIFIED'de refresh DENEMİYOR (doğru); ama arayüz
  bu hatayı kullanıcıya anlamlı gösteriyor mu? → B-02'ye not.

YAPILACAKLAR:
1. `get_current_principal`'ın doğrulanmış varyantı: `get_verified_principal` (api/deps.py) —
   require_email_verified üzerinden. K7'ye göre yazma uçlarında get_current_principal yerine
   bunu kullan. Liste (router'ları grep'le, eksik kalmasın): engagements (POST, transitions,
   tasks, deliverables, evaluation, attestations), attestations revoke, evidence (upload-url,
   POST), institutions (POST, members, link-requests, approve, reminders), organizations (POST,
   members, verify-domain), talents/me (PATCH), talents/me/skills (POST, DELETE), admin yazma uçları.
   Okuma uçları ve /auth/logout değişmez.
2. HTTP kodu: mevcut `401 EMAIL_NOT_VERIFIED`. 403 mü olmalı? docs/API.md'yi oku; dokümanda
   ne yazıyorsa o. (Frontend client.ts 401+EMAIL_NOT_VERIFIED'i özel ele alıyor — değiştirirsen
   B'ye haber ver.)
3. Yeni uç: POST /auth/resend-verification (kimliği doğrulanmış, doğrulanmamış kullanıcı;
   CSRF'li). Zaten doğrulanmışsa 204 (no-op). Önceki kullanılmamış token'ları used_at ile
   geçersiz kıl, yenisini outbox'a koy. Hız sınırı: kullanıcı başına 1/dakika, 5/saat
   (süreç içi, A-10 ile ortak yardımcıya taşınabilir). Yetkilendirme testi zorunlu.
4. GET /me yanıtına `email_verified: bool` ekleme işi B-02'nin — çakışmamak için sen ekleme;
   B-02 henüz eklemediyse B'ye söyle.
5. Test fixture'ları: tests/conftest.py'deki kullanıcı fixture'ları email_verified_at set
   etmiyorsa yüzlerce test 401 alır. Fixture'ları doğrulanmış yap (tek yerde); doğrulanmamış
   senaryolar için ayrı fixture ekle.

KABUL:
- AC-1: Doğrulanmamış kullanıcı POST /engagements → 401 (ya da dokümandaki kod) EMAIL_NOT_VERIFIED.
- AC-2: Doğrulanmamış kullanıcı GET /engagements, GET /me, POST /auth/logout → 200/204.
- AC-3: Doğrulanmış kullanıcıda hiçbir davranış değişmedi (tam test paketi).
- AC-4: resend-verification → outbox'ta yeni email.verify_email; eski token artık 400.
- AC-5: Listede sayılan her yazma ucu için parametrik bir test (tek tabloda uç × beklenen kod).
DOĞRULAMA: pytest tests/authorization -q (tamamı) + pytest -q tamamı (bilinen kırıklar hariç).
BİTİŞ: §1.9. HATA.md IS-08 ve önceki rapor #8.
```

### A-08 · Çoklu rol: kapsam sorguları `kind`'dan bağımsız

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.30 | AUTHZ-01, GUV-02 (DoS kısmı), AUTHZ-02 (kod), L-08 | YÜKSEK | 5-6 | **SENKRON-1**, K3 | Z-GÜV + `authz-test` | `fix/3.30-coklu-rol-yetki` | `a08-coklu-rol` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-08 — HATA.md AUTHZ-01 (+ GUV-02'nin hesap-kilitleme etkisi, AUTHZ-02'nin kod kısmı).
PLAN 3.30. Bu projenin EN RİSKLİ değişikliği: yetkilendirme çekirdeği.
ZİNCİR (Z-GÜV, eksiksiz): /atdd → threat-model → plan → authz-test (ZORUNLU, saldırgan matrisi
+ canlı sonda) → test-copilot → code-copilot → verify → red-team. Slug: a08-coklu-rol.
ONAY NOKTALARI: (1) atdd.md bitince, (2) plan.md bitince — kod yazmadan iki kez onay.
ÖN KOŞUL: SENKRON-1 tamam (B-03…B-06 main'de). `git log main --oneline | head -30` ile teyit;
değilse dur. Bu iş B'nin servis dosyalarına (engagement.py, attestation.py, evaluation.py)
dokunur — başlamadan Kişi B'ye "A-08 başladı, bu dosyalara 2 gün dokunma" de.

BAĞLAM (HATA.md AUTHZ-01, AUTHZ-02, GUV-02'yi oku):
- Kayıtta her kullanıcıya talent profili açılıyor → her koordinatör/org üyesi aynı zamanda talent.
- backend/app/api/deps.py get_current_principal tek `kind` seçiyor: INST_ADMIN > COORDINATOR >
  ORG_ADMIN > ORG_MEMBER > TALENT. Principal docstring'i "kind yalnız gösterim içindir, yetki
  kararı kind'a dayanmamalı" diyor; ama can(), scoped_organizations/institutions/engagements/
  evidence, transition_table, create_engagement, create_task/deliverable, create_evaluation,
  create_attestation hep kind'a bakıyor.
- Sonuç: kurum üyesi olan talent kendi engagement/kanıtını göremez; org admin'i + koordinatör
  olan kişi org uçlarında 404 alır; herhangi biri sahte kurum açıp kurbanı üye yaparak kurbanın
  talent işlevlerini kapatabilir (GUV-02).
- AUTHZ-02: T2/T3/T5/T6 ve tanıklık yalnız kind=="COORDINATOR". K3 kararına göre:
  (a) doküman gibi yalnız COORDINATOR rolü — ama kind değil, "bu kurumda COORDINATOR üyeliği"
  kontrol edilmeli (institution_coordinator_ids); (b) ADMIN rolü de dahil.

HEDEF TASARIM (öneri — plan.md'de netleştir):
1. Principal'a rol-bazlı listeler: talent_id (var), org_ids, org_admin_ids, institution_ids,
   institution_admin_ids, + institution_coordinator_ids (yeni). `kind` yalnız gösterim için kalsın
   (login yanıtıyla tutarlı öncelik sırası — AUTHZ-02'deki summarize_role/get_current_principal
   tutarsızlığını da gider).
2. scoped_engagements = BİRLEŞİM: (talent_id == principal.talent_id) OR
   (organization_id IN org_ids) OR (institution_id IN institution_ids). SQLAlchemy `or_`;
   boş liste terimlerini ekleme.
3. scoped_organizations → organization_id IN org_ids (kind'sız). scoped_institutions → IN
   institution_ids. scoped_evidence → owner_talent_id == talent_id (kind'sız; admin istisnası korunur).
4. İşlem yetkisi KAYNAĞA göre: "bu engagement'ta hangi sıfatla?" yardımcı fonksiyonu —
   ör. `engagement_roles(principal, engagement) -> set[str]` {"TALENT_OWNER", "ORG_MEMBER",
   "ORG_ADMIN", "INST_COORD", "INST_ADMIN"}. transition_table, create_task (ORG_*),
   create_deliverable (TALENT_OWNER), create_evaluation (yön ↔ sıfat: TALENT_TO_ORG yalnız
   TALENT_OWNER; ORG_TO_TALENT yalnız ORG_*), create_attestation (institution varsa INST_COORD,
   yoksa ORG_ADMIN) bunu kullansın.
   KRİTİK: Aynı kişi hem TALENT_OWNER hem ORG/INST sıfatına sahipse (kendi engagement'ında
   koordinatör/org üyesi) → kendi kendine onay/değerlendirme/tanıklık YASAK (self-attestation
   kuralının genellemesi). Bunu açık AC-S olarak yaz ve test et.
5. can() Organization/Institution dalları kind yerine *_admin_ids'e baksın.
6. L-08: talent_id yoksa signals ucu 401 değil 404 (verified-experiences ile tutarlı) — B'nin
   dosyası; küçük dokunuş, commit'te belirt.
7. Frontend etkisi: /me organizations/institutions artık doğru dolacak. B-02'nin /me rol alanları
   bu listelerden türetilmeli — B'ye haber ver.

AUTHZ-TEST: authz-test skill'i ile saldırgan matrisi: aktörler {talent A, talent B, org A üyesi,
org A admin, org B üyesi, kurum X koordinatör, kurum X admin, kurum Y koordinatör, hem talent
hem kurum X koordinatör olan kişi, hem org A admin hem kurum X koordinatör olan kişi,
platform admin} × uçlar {GET/POST engagements, transitions (her geçiş), tasks, deliverables,
evaluation (iki yön), attestations, revoke, evidence (liste/indir), GET organizations/{id},
dashboard}. Beklenen her hücre 200/201/404/403(S6)/409 olarak tabloya.

KABUL (asgari):
- AC-1: Kurum X koordinatörü olan talent kendi engagement'larını listeler, teslim yapar, kendi
  kanıtını indirir.
- AC-2: Aynı kişi kendi engagement'ını onaylayamaz/değerlendiremez/tanıklayamaz (404 ya da 409 —
  sözleşmede netleştir).
- AC-3: Org A admin + kurum X koordinatörü: GET /organizations/A 200; org A'ya üye davet eder.
- AC-4: Sahte kurum açıp kurbanı ADMIN yapmak kurbanın talent uçlarını ETKİLEMEZ (GUV-02 DoS kapandı).
- AC-5: Mevcut tests/authorization/* tamamı yeşil (davranış değişikliği gereken test varsa
  gerekçesiyle listele, onay al).
- AC-6: Tenant izolasyonu: hiçbir aktör başka kiracının kaydını görmüyor (matris).
DOĞRULAMA: pytest tests/authorization -q (TAMAMI) + pytest -q (tam paket) + authz-test canlı sonda.
BİTİŞ: §1.9. HATA.md AUTHZ-01 ✅, GUV-02 ◐ (rıza akışı K1/A-09), AUTHZ-02 ✅.
```

### A-09 · Davet uçları: 500, numaralandırma, rol doğrulama

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.31 | GUV-07, GUV-02 (K1), L-01 | YÜKSEK | 6 | A-08, K1 | Z-GÜV | `fix/3.31-davet-uclari` | `a09-davet-uclari` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-09 — HATA.md GUV-07, GUV-02 (K1 kararına göre), L-01. PLAN 3.31.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → authz-test → test-copilot → code-copilot →
verify → red-team. Slug: a09-davet-uclari. ONAY NOKTASI: yetki davranışı değişikliği.
KARAR: K1 (öneri (b): doğrudan ekleme kalır; tek tip yanıt + 500 fix). K1=(a) seçildiyse
davet+kabul akışı (organization_members.status zaten var: INVITED/ACTIVE; institution_members
için migration) — bu durumda iş büyür, önce süre tahmini ver ve onay al.

BAĞLAM:
- backend/app/services/organization.py invite_org_member bilinmeyen e-postada ValueError;
  backend/app/api/organizations.py yalnız AlreadyMemberError yakalıyor → 500. Numaralandırma
  oracle'ı: bilinmeyen 500, bilinen 201.
- backend/app/api/institutions.py invite_member_endpoint: bilinmeyen → 422 "User not found",
  bilinen → 201 (oracle). `role` Pydantic'te doğrulanmıyor → DB CHECK → 500.
  Mevcut üyenin rolü sessizce değişiyor (`member.role = role`), son ADMIN kendini düşürebilir.
- Herhangi bir kullanıcı POST /institutions/ ve /organizations/ ile ADMIN olabiliyor (GUV-02,
  GUV-03). A-08 hesap kilitleme etkisini kaldırdı; bu iş yanıt sızıntısını kapatır.

YAPILACAKLAR (K1=(b)):
1. Her iki davet ucunda rol `Literal` (kurum: ADMIN|COORDINATOR, org: ADMIN|MEMBER) → 422.
2. Bilinmeyen e-posta ve bilinen e-posta için AYNI yanıt: 202 Accepted + {"status": "queued"}
   (ya da dokümandaki sözleşme; docs/API.md'yi oku ve güncelle). Bilinen e-postada üyelik
   oluşturulur + bildirim outbox'a; bilinmeyende yalnız audit (INVITE_UNKNOWN_EMAIL, e-posta
   yazmadan — hash'i bile yazma). Yanıt süresi farkı minimal olsun (aynı sayıda DB sorgusu).
   Bu bir API sözleşmesi değişikliği (201→202) — frontend henüz bu uçları çağırmıyor; yine de
   docs/API.md'yi güncelle.
3. Zaten üyeyse: organizasyonda 409 ALREADY_MEMBER sızıntıdır mı? → yalnız org ADMIN'i
   görebildiği için kabul edilebilir; atdd'de karar yaz.
4. Kurum: mevcut üyenin rolünü değiştirmek ayrı ve açık bir işlem olmalı — davet ucunda
   mevcut üye → 409 ALREADY_MEMBER (org ile tutarlı). Son ADMIN korunur.
5. Hata yanıtlarını ApiError biçimine çevir (bu iki uç için; A-14 geri kalanını yapar).

KABUL:
- AC-1: Org davetinde bilinmeyen e-posta → 202 (500 değil); bilinen → 202; ikisi ayırt edilemez.
- AC-2: Geçersiz rol → 422 VALIDATION_ERROR.
- AC-3: Kurumda mevcut üyeye davet → 409; rol değişmez.
- AC-4: Yetkisiz (başka kurumun admin'i) → 404 (değişmedi).
DOĞRULAMA: pytest tests/authorization -q (tamamı) + tests/test_institution.py tests/test_organization.py.
BİTİŞ: §1.9.
```

### A-10 · Kayıt zamanlama + kimlik uçlarına hız sınırı

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.32 | GUV-10, GUV-11 | ORTA | 7 | A-01 | Z-GÜV | `fix/3.32-kimlik-hiz-siniri` | `a10-kimlik-hiz-siniri` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-10 — HATA.md GUV-10 ve GUV-11. PLAN 3.32. ZİNCİR (Z-GÜV). Slug: a10-kimlik-hiz-siniri.
ONAY NOKTASI: auth değişikliği. KISIT: Redis YASAK (CLAUDE.md MVP dışı) → süreç içi limiter.

BAĞLAM:
- register_user: yeni e-posta yolu Argon2 hash hesaplıyor (~50-100 ms), mevcut e-posta yolu
  hesaplamıyor → zamanlama ile numaralandırma.
- /auth/login, /auth/register, /auth/forgot-password, /auth/verify-email, /auth/reset-password,
  (A-07'nin) /auth/resend-verification: IP bazlı hız sınırı yok. forgot-password her çağrıda
  outbox'a e-posta satırı yazıyor (bombardıman).
- Mevcut süreç içi limiter: backend/app/services/storage.py check_rate_limit (yalnız evidence).

YAPILACAKLAR:
1. Ortak limiter: app/core/rate_limit.py — kayan pencere, anahtar+pencere+limit parametreli,
   thread-safe (Lock), boş anahtar temizliği. storage.py'deki evidence limiter'ı buna taşı
   (davranış aynı kalsın: 10/dk/talent).
2. IP'yi güvenli çıkar: request.client.host (proxy arkasında X-Forwarded-For'a GÜVENME —
   K6 tek origin reverse proxy ise uvicorn --proxy-headers ile çözülür; bunu docs/ENV.md'ye not et).
3. Limitler (öneri, atdd'de netleştir): login 10/dk/IP + 20/saat/e-posta; register 5/saat/IP;
   forgot-password 3/saat/e-posta + 10/saat/IP; verify/reset 20/saat/IP. Aşımda 429
   RATE_LIMITED + Retry-After başlığı. forgot-password'de e-posta limiti aşılınca yine 204 dön
   (numaralandırma koruması) ama outbox'a yazma.
4. GUV-10: mevcut e-posta yolunda da hash_password(password) çağır (sonucu at) — yanıt süresi eşitlensin.
5. A-01'deki hesap kilidi IP limiti olmadan DoS aracı: aynı e-postaya farklı IP'lerden
   deneme ile hesap kilitlenebilir — atdd Risks'e yaz; MVP'de kabul.

KABUL:
- AC-1: 11. login denemesi (aynı IP, 1 dk) → 429 + Retry-After.
- AC-2: forgot-password 4. çağrı (aynı e-posta, 1 saat) → 204 ama outbox'a yeni satır yok.
- AC-3: Kayıtta mevcut ve yeni e-posta yanıt süresi farkı < 20 ms (10 ölçüm ortalaması; testte
  Argon2 çağrısının iki yolda da yapıldığını mock ile doğrula — zamanlama testi kırılgan olmasın).
- AC-4: Evidence limiter davranışı değişmedi (mevcut testler yeşil).
DOĞRULAMA: pytest tests/authorization -q (tamamı) + evidence testleri.
BİTİŞ: §1.9.
```

### A-11 · Bağımlılık yükseltmeleri + secrets baseline

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.33 | DEP-01, L-16 | YÜKSEK | 7 | — | Z-BAĞ | `chore/3.33-bagimlilik-yukseltme` | `a11-bagimlilik` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-11 — HATA.md DEP-01 ve L-16. PLAN 3.33.
ZİNCİR (Z-BAĞ): ONAY → yükselt → security-scan → verify (TAM paket) → onay → /bitir.
Slug: a11-bagimlilik. ONAY NOKTASI: bağımlılık yükseltmesi — hiçbir şeyi kurmadan önce
yükseltme planını (paket, eski→yeni sürüm, kırıcı değişiklik notları) göster, onay bekle.

BAĞLAM (pip-audit, 28 Eylül):
- pyjwt 2.10.1: PYSEC-2026-120/-175/-176/-177/-178/-179 (düzeltme 2.13.0), PYSEC-2025-183 (düzeltme yok).
- starlette 0.41.3 (fastapi 0.115.6 üzerinden): PYSEC-2026-1941 (düzeltme 0.47.2) → fastapi
  yükseltmesi gerekir.
- pytest 8.3.4: PYSEC-2026-1845 (düzeltme 9.0.3, yalnız geliştirme).
- detect-secrets 589 bulgu: çoğu alembic revision hash'i ve test parolaları (yanlış pozitif);
  .secrets.baseline güncel değil.

YAPILACAKLAR:
1. Her advisory'yi oku (pip-audit --desc): pyjwt açıkları bizim kullanımımızı (HS256 encode/decode,
   algorithms=[HS256] sabit) etkiliyor mu? PYSEC-2025-183 düzeltmesizse etkisini değerlendir ve
   HATA.md'ye not düş.
2. backend/.venv içinde yükselt: pyjwt==2.13.0 (ya da en güncel güvenli), fastapi'yi starlette
   ≥0.47.2 çeken en düşük sürüme, pytest==9.0.3. requirements.txt'yi sabit sürümlerle güncelle.
   Global pip install YOK.
3. Kırıcı değişiklik taraması: fastapi yeni sürümünde `class Config` (Pydantic v1 stili) uyarıları,
   TestClient/httpx sürüm uyumu, exception handler davranışı. Tam test paketini koş.
4. Security-scan'i tekrar çalıştır (security-scan skill'i). Secrets bulgularını TEK TEK incele:
   gerçek sır yoksa `--accept-secrets` ile baseline güncelle (skill'in "Yanlış pozitif yönetimi"
   bölümüne uy). `.env` bulgusu çıkarsa: .env git'te izlenmiyor (.gitignore) — baseline'a
   yazma, tarama kapsamından çıkar.
5. CI (.github/workflows/ci.yml) pip install requirements.txt kullanıyorsa ek değişiklik yok; kontrol et.

KABUL:
- AC-1: pip-audit backend'de 0 bilinen düzeltilebilir zafiyet (düzeltmesizler gerekçeli listede).
- AC-2: pytest -q tam paket: bilinen kırıklar (§1.7) dışında yeni kırık yok.
- AC-3: security-scan secrets gate'i PASS (baseline incelenmiş).
DOĞRULAMA: security-scan + pytest -q + frontend npm run build (CI simülasyonu).
BİTİŞ: §1.9.
```

### A-12 · DB kısıtları: append-only trigger, claimed_level, timestamptz

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.34 | VER-01, VER-02, VER-03 | ORTA | 7 | **B-04** (VE güncellenebilir alanları), A-06 migration'ı | Z-STD | `fix/3.34-db-kisitlari` | `a12-db-kisitlari` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-12 — HATA.md VER-01, VER-02, VER-03. PLAN 3.34. ZİNCİR (Z-STD). Slug: a12-db-kisitlari.
ONAY NOKTASI: migration oluşturma ve uygulama. `alembic heads` tek başlı olmalı; Kişi B aynı
gün migration açmıyor olmalı (§3) — sor.
ÖN KOŞUL: B-04 main'de (verified_experiences'ta hangi alanların güncellendiğini o belirler:
visibility ve public_token).

BAĞLAM:
- VER-01: append-only trigger yalnız audit_events, skill_signals, attestations için var.
  evaluations ve verified_experiences DB'de UPDATE/DELETE'e açık. CLAUDE.md istisnası:
  verified_experiences.visibility (B-04 public_token'ı da set ediyor → istisna listesine
  public_token eklenmeli, "NULL → değer" set-once olarak).
- VER-02: POST /talents/me/skills geçersiz claimed_level → DB CHECK → servis IntegrityError'ı
  "zaten eklenmiş" sanıp 409 ALREADY_CLAIMED dönüyor (backend/app/services/skill_claim.py).
  create_engagement'ta geçersiz institution_id formatı INSTITUTION_MISMATCH(400), yetkisiz kind
  TALENT_NOT_FOUND(404) — bu ikincisi A-08'de değişmiş olabilir, kontrol et.
- VER-03: engagement_tasks.due_at, completed_at, deliverables.submitted_at modelde
  DateTime(timezone=True) olmadan tanımlı → migration'da gerçek tipi doğrula
  (`\d engagement_tasks` ya da information_schema).

YAPILACAKLAR:
1. Mevcut trigger migration'larındaki deseni (l3m4n5o6p7q8_...) örnek al. Yeni migration:
   - evaluations + evaluation_items: UPDATE/DELETE yasak.
   - verified_experiences: DELETE yasak; UPDATE yalnız visibility (serbest) ve public_token
     (yalnız NULL→değer) değişebilir.
   - downgrade trigger'ları kaldırır.
2. VER-03: tip `timestamp without time zone` ise `ALTER COLUMN ... TYPE timestamptz USING
   <col> AT TIME ZONE 'UTC'`; model tanımlarını DateTime(timezone=True) yap. Zaten timestamptz
   ise yalnız modeli düzelt (migration yok).
3. VER-02: talent_skills.py PostSkillClaimRequest.claimed_level → Literal["BEGINNER",
   "INTERMEDIATE","ADVANCED"] | None (dosya B'nin — küçük dokunuş, commit'te belirt);
   skill_claim.py IntegrityError dalında constraint adına bak: uq → 409, diğerleri → yeniden fırlat.
4. Test: trigger'ların UPDATE/DELETE'i engellediğini ve izinli güncellemeyi geçirdiğini sına
   (tests/test_attestation_revoke.py::TestAttestationRevokeDBTrigger deseni).

KABUL:
- AC-1: evaluations UPDATE → DB hatası; verified_experiences.visibility UPDATE → başarılı;
  public_token NULL→değer başarılı, değer→başka değer hata; claim_type UPDATE hata.
- AC-2: Geçersiz claimed_level → 422 VALIDATION_ERROR.
- AC-3: alembic upgrade head → downgrade -1 → upgrade head temiz.
- AC-4: B-04'ün public_token/visibility akışı testleri yeşil.
DOĞRULAMA: alembic upgrade/downgrade/upgrade + pytest -q tam paket.
BİTİŞ: §1.9.
```

### A-13 · Backend test izolasyonu + fixture rollback semantiği

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.22 | TEST-01 (backend), TEST-02 | YÜKSEK | 8 | A-04, A-05 | Z-TEST | `test/3.22-test-izolasyonu` | `a13-test-izolasyonu` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-13 — HATA.md TEST-01 (backend kısmı), TEST-02, PLAN 3.22. ZİNCİR (Z-TEST). Slug: a13-test-izolasyonu.
KURAL: Test düzeltirken ürün kodunu DEĞİŞTİRME. Bir test ürün hatasını yakalıyorsa (gerçek
kırık) testi "düzeltme" — raporla ve dur.

BAĞLAM:
- Yerelde `pytest -q` (seed'li DB) 28 Eylül: 13 kırık — §1.7'deki liste. Ortak kök: testler
  seed verisiyle dolu geliştirme DB'sine karşı koşuyor ve GLOBAL satır sayıyor ("30
  TalentProfile oluştu" = seed'in 30 kaydı; "15 SkillSignal" = seed'in sinyalleri) ya da outbox
  kuyruğunun boş olduğunu varsayıyor. CI temiz DB kullandığı için orada muhtemelen geçiyor.
- tests/test_seed.py seed fonksiyonlarını ayrı DB session ile çağırıyor → yerel DB'ye kalıcı satır.
- TEST-02: tests/conftest.py override_get_session generator değil → istisnada rollback yok;
  üretimde var. GUV-01 bu yüzden testte yeşildi.

YAPILACAKLAR:
1. Kırıkları tek tek çalıştır, her biri için kök nedeni bir satırla yaz (tablo). A-04/A-05
   sonrası bazıları kendiliğinden düzelmiş olabilir — önce güncel listeyi çıkar.
2. Global sayım yapan testleri kendi oluşturdukları kayıtlara göre filtrele (id IN (...),
   ya da test başı/sonu farkı). Outbox worker testleri: testin eklediği satırı işleyen bir
   handler seti ya da `topic` filtresiyle çalışsın.
3. test_seed.py: seed fonksiyonlarını test fixture'ının session'ıyla çağır (seed.py bir
   session parametresi alıyor mu? almıyorsa bu ürün kodu değişikliği → dur ve sor; öneri:
   seed fonksiyonlarına opsiyonel session parametresi — geriye uyumlu, küçük).
4. TEST-02: override_get_session'ı üretim semantiğine çek:
       def override_get_session():
           nested = test_session.begin_nested()  # savepoint
           try:
               yield test_session
               ... (commit davranışı: savepoint'i bırak)
           except Exception:
               nested.rollback(); raise
   Router'lar `session.commit()` çağırıyor — join_transaction_mode="create_savepoint" ile
   etkileşimini dikkatle test et. Bu değişiklik YÜZLERCE testi etkiler: önce ayrı bir dalda dene,
   kırılan testleri listele; kırılan her test ya gerçek bir "yaz-sonra-hata" ürün hatasını
   gösteriyordur (raporla, düzeltme) ya da test yanlış varsayım yapıyordur (düzelt).
   Eğer kapsam 1 günü aşıyorsa: override'ı yalnız opsiyonel bir fixture (`client_strict`) olarak
   ekle ve kritik yollar (login, refresh, evaluation çakışması, attestation çakışması) için kullan;
   geneli PLAN 5.x'e bırak — kullanıcıya sor.
5. Ayrı test veritabanı seçeneği: TEST_DATABASE_URL ortam değişkeni verilirse testler onu
   kullansın (config'de opsiyonel ayar; .env'e dokunma, .env.example'a placeholder ekle).

KABUL:
- AC-1: Seed'li yerel DB'de `pytest -q` → 0 kırık.
- AC-2: Temiz DB'de (CI) `pytest -q` → 0 kırık.
- AC-3: `pytest -q` iki kez üst üste çalıştırınca DB'de kalıcı satır sayısı değişmiyor
  (users, talent_profiles, outbox sayımları öncesi/sonrası).
- AC-4: GUV-01'in eski hali (A-01 öncesi kod) strict fixture ile KIRMIZI olurdu — bunu bir
  yorumda/atdd'de gösteren test mevcut.
DOĞRULAMA: pytest -q (iki kez) + sayım karşılaştırması.
BİTİŞ: §1.9. §1.7'deki bilinen kırık listesini bu dosyada "kapandı" diye güncelle.
```

### A-14 · Hata yanıt biçimi, 307'ler, prod ayarları

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.35 | OPS-04, ENT-06 (inst/org), L-07, L-11, L-12, L-14 | ORTA | 8 | A-09 | Z-STD | `fix/3.35-hata-bicimi` | `a14-hata-bicimi` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-14 — HATA.md OPS-04, ENT-06 (yalnız institutions/organizations), L-07, L-11, L-12, L-14.
PLAN 3.35. ZİNCİR (Z-STD). Slug: a14-hata-bicimi.

BAĞLAM:
- docs/API.md §1.4: her hata {code, message, request_id}. Sapmalar (canlı doğrulandı):
  tanımsız yol → {"detail": "Not Found"} (Starlette HTTPException handler'ı kayıtlı değil,
  main.py yalnız fastapi.HTTPException'ı yakalıyor); HTTPException(detail="string") kullanan
  uçlar (institutions, organizations, verified_experiences, skill_signals, me) code:"HTTP_ERROR"
  dönüyor; engagements.py request_id: None; ApiError her hata için UUID üretiyor ama loglamıyor;
  yakalanmayan istisnalar düz 500 metin.
- POST /institutions/ ve /organizations/ "/" ile tanımlı → sonda / olmadan çağrı 307
  (POST gövdesi tarayıcıya göre kaybolabilir).
- L-07: admin limit/offset sınırsız. L-11: CORS origin listesi doğrulanmıyor ("*" + credentials
  tehlikesi). L-12: engine pool_pre_ping yok. L-14: seed_admin_password tahmin edilebilir varsayılan.
- /docs ve /openapi.json üretimde açık; debug=True varsayılan.

YAPILACAKLAR:
1. main.py: starlette.exceptions.HTTPException handler'ı (404/405 → {code: NOT_FOUND /
   METHOD_NOT_ALLOWED, ...}); genel Exception handler → 500 {code: INTERNAL_ERROR, message
   generic, request_id}; logger'a request_id + istisna tipi (PII yok, str(e) yok).
2. request_id: middleware ile her isteğe UUID ata (X-Request-ID yanıt başlığı), ApiError ve
   handler'lar aynı id'yi kullansın. engagements.py'deki `"request_id": None` sözlüklerini
   ApiError'a çevirmek B'nin dosyası → yalnız handler seviyesinde çöz: api_error_handler
   request_id None ise request.state.request_id ile doldursun (dosyaya dokunmadan çözüm).
3. HTTPException(detail="string") kullanan A-dosyalarını (institutions.py, organizations.py)
   ApiError'a çevir; kod adlarını docs/API.md'deki hata kodu listesiyle eşle. B dosyalarındaki
   (verified_experiences.py, skill_signals.py, me.py) aynı dönüşümü B'ye bırak — PR'da not düş,
   ya da B onaylarsa sen yap.
4. ENT-06: institutions/organizations POST rotalarını "" yap (FastAPI'de "/" yerine ""), eski
   "/" yolunu da kabul etmek için ikinci dekoratör ekle (geriye uyum) ya da redirect_slashes'i
   bu router için değerlendirme — basit olan: iki path.
5. L-07: admin limit ≤ 200, offset ≥ 0 (Query(ge, le)).
6. L-11: settings.allowed_origins'te "*" varsa uygulama açılışında hata ver (credentials ile).
7. L-12: create_engine(..., pool_pre_ping=True).
8. L-14: ENVIRONMENT != development iken seed_admin_password varsayılan değerse seed çalışmasın
   (seed prod'da zaten çalışmıyor — staging için de koruma).
9. /docs, /redoc, /openapi.json: settings.environment == "production" ise kapalı.
   settings.debug varsayılanı False olsun mu? → docs/ENV.md'ye bak; değiştirirsen .env.example'ı
   güncelle, .env'e dokunma.

KABUL:
- AC-1: GET /yok-boyle → 404 {code:"NOT_FOUND", message, request_id} + X-Request-ID başlığı.
- AC-2: Kurum/org uçlarının tüm hata yanıtları {code, message, request_id} ve code != HTTP_ERROR.
- AC-3: POST /institutions ve /institutions/ ikisi de 201.
- AC-4: Zorla fırlatılan istisna → 500 INTERNAL_ERROR, gövdede iz yok.
- AC-5: ENVIRONMENT=production'da /docs 404.
DOĞRULAMA: pytest -q tam paket (hata gövdesini kontrol eden testler etkilenebilir; her değişikliği
gerekçelendir) + frontend/lib/api/errors.ts'nin yeni kodları işlediğini typecheck ile teyit.
BİTİŞ: §1.9.
```

### A-15 · Alan adı gaspı, DNS transaction, hatırlatma sınırları

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| A | 3.36 | GUV-09, AUTHZ-04, GUV-13 | ORTA | 8 | A-04, A-09 | Z-GÜV | `fix/3.36-alan-adi-hatirlatma` | `a15-alan-adi-hatirlatma` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: A-15 — HATA.md GUV-09, AUTHZ-04, GUV-13. PLAN 3.36. ZİNCİR (Z-GÜV). Slug: a15-alan-adi-hatirlatma.
(Zaman yetmezse kesilebilecek ilk iş — §4 öncelik kuralı.)

BAĞLAM:
- GUV-09: POST /institutions/ alan adını doğrulamadan UNIQUE ayırıyor (ilk gelen alır).
  Org domain doğrulamada çakışma kontrolü yalnız verification_level == "T2" arıyor
  (backend/app/services/organization.py) → T3/T4 org'un alanı başka org tarafından yeniden
  doğrulanabilir. FREE_EMAIL_DOMAINS yalnız 4 alan.
- AUTHZ-04: verify_domain DNS'ten önce commit ediyor ama sonra org.domain_verification_token
  okununca ORM yeni transaction açıyor → DNS (3 sn'ye kadar) açık transaction içinde.
- GUV-13: reminders: template serbest metin → topic reminder.<her şey>; engagement_ids listesi
  sınırsız, tekrar koruması yok.

YAPILACAKLAR:
1. Kurum alan adı: oluştururken domain "talep edilen" olarak saklanır ama UNIQUE ayrılmaz —
   ya kurum için de org'daki DNS doğrulama akışı (MVP'de fazla), ya da en basit: domain alanı
   yalnız platform admin'i tarafından set edilebilir (POST /institutions/ domain'i yok sayar
   veya 422). Karar ver + atdd'de gerekçele (öneri: admin set eder; kurumlar T1 başlar).
   Migration gerekirse ONAY.
2. Org çakışma kontrolü: verification_level IN ('T2','T3','T4').
3. FREE_EMAIL_DOMAINS: yandex.com, icloud.com, hotmail.com.tr, outlook.com.tr, gmail.com.tr?,
   protonmail.com, mail.ru, yahoo.com.tr ekle (kısa, belgeli liste).
4. AUTHZ-04: DNS'ten önce ihtiyaç duyulan değerleri yerel değişkenlere al (domain, token), commit,
   session'ı kullanmadan DNS; sonra yeni kısa transaction'da sonucu yaz.
5. GUV-13: template Literal (ör. "evaluation_pending", "approval_pending"); engagement_ids
   max_length=100; aynı engagement+template için son 24 saatte kuyruğa girmişse atla
   (outbox'ta payload sorgusu ya da audit üzerinden). A-04 reminder topic'ini standartlaştırdıysa uyumla.

KABUL:
- AC-1: T3 org'un alanını ikinci org doğrulamaya çalışınca 409 DOMAIN_ALREADY_VERIFIED.
- AC-2: DNS çağrısı sırasında açık transaction yok (testte resolver mock'u içinde
  session.in_transaction() False).
- AC-3: Geçersiz template → 422; 101 id → 422; 24 saat içinde tekrar → queued_count 0.
- AC-4: Kurum oluşturmada alan adı gaspı kapandı (seçilen yönteme göre).
DOĞRULAMA: pytest tests/authorization -q + tests/test_organization.py tests/test_reminders.py tests/test_institution.py.
BİTİŞ: §1.9.
```

---

## 9. Prompt'lar — Kişi B

### B-01 · Refresh sonrası CSRF başlığı yeniden okunsun

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.37 | ENT-03, L-13 | KRİTİK | 1 | — | Z-GÜV | `fix/3.37-csrf-refresh-retry` | `b01-csrf-refresh` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-01 — HATA.md ENT-03 ve L-13. PLAN 3.37.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → test-copilot → code-copilot → verify → red-team.
Slug: b01-csrf-refresh. ONAY NOKTASI: oturum/CSRF istemci mantığı (auth) değişikliği.

BAĞLAM:
- frontend/lib/api/client.ts apiFetch: CSRF başlığı istek başında bir kez `getCsrfToken()` ile
  okunup `options.headers`'a konuyor. 401 UNAUTHENTICATED → performRefresh() → backend
  /auth/refresh YENİ csrf_token cookie'si yazıyor (backend/app/api/auth.py _set_auth_cookies) →
  retry AYNI options ile (ESKİ x-csrf-token) gidiyor → 403 CSRF_FAILED.
- Access token 15 dk; sayfada 15 dakikadan uzun kalan her kullanıcının ilk POST/PATCH/DELETE'i
  başarısız olur (değerlendirme formu, profil kaydı, geçiş düğmesi).
- L-13: getCsrfToken regex'i /csrf_token=([^;]*)/ → "xcsrf_token=" gibi adlarla da eşleşir.

DOĞRULA: client.ts'yi oku; lib/api/client.test.ts'de refresh+retry testlerinin mutasyon
isteğinde CSRF başlığını kontrol edip etmediğine bak (muhtemelen etmiyor).

YAPILACAKLAR:
1. Başlıkları retry'dan hemen önce yeniden kur: header üretimini bir fonksiyona al
   (buildHeaders(method, extra)); retry'da çağır. Gövde (JSON string) aynı kalabilir.
2. performRefresh'in kendisi de CSRF gönderiyor — backend /auth/refresh CSRF istemiyor
   (require_csrf yok); gereksizse bırak, zararsız.
3. L-13: regex'i cookie sınırına bağla: /(?:^|;\s*)csrf_token=([^;]*)/ ve decodeURIComponent.
4. Test (vitest): fetch mock'u → ilk POST 401 UNAUTHENTICATED; refresh 204 ve document.cookie'yi
   yeni token'la güncelliyor; retry'ın x-csrf-token başlığı YENİ token olmalı. Ayrıca
   "xcsrf_token=a; csrf_token=b" → "b".

KABUL:
- AC-1: Süresi dolmuş access token ile POST → refresh → retry başarılı (200/201), 403 yok.
- AC-2: Retry isteğindeki x-csrf-token == refresh sonrası cookie değeri.
- AC-3: GET akışları değişmedi; single-flight refresh korunuyor (eşzamanlı 401'ler tek refresh).
- AC-4: npm run typecheck, npm run lint, ilgili vitest dosyaları yeşil.
Canlı teyit (opsiyonel): backend ACCESS_TOKEN_TTL_MINUTES=1 ile başlat (env değişkeni olarak,
.env'e dokunmadan), 1 dk bekle, profil kaydet.
BİTİŞ: §1.9.
```

### B-02 · `/me` rol bilgisi, admin linkleri, durum etiketleri, 307'ler

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.38 | ENT-04, ENT-05 (+ekip gözlemi), IS-04 (UI), ENT-06 (signals/VE) | KRİTİK | 1-2 | — | Z-UI (+backend `/me`) | `fix/3.38-me-rol-durum-etiketleri` | `b02-me-rol-etiketler` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-02 — HATA.md ENT-04, ENT-05 (ekip gözlemi dahil), IS-04 (arayüz kısmı), ENT-06
(signals ve verified-experiences). PLAN 3.38.
ZİNCİR (Z-UI): /atdd → plan → test-copilot → code-copilot → verify (vision-test ile alt
bilgi ve çalışmalar listesinin ekran görüntüsü) → red-team. Slug: b02-me-rol-etiketler.
ONAY NOKTASI: yetkiyle ilgili arayüz değişikliği (admin linkleri) — plan sonrası onay.

BAĞLAM:
- ENT-05 / ekip gözlemi: frontend/components/app-shell.tsx sayfa altındaki "Kurum Doğrulama"
  (/admin/dogrulama-kuyrugu) ve "Yetkinlik Yönetimi" (/admin/skiller) linkleri rol ayrımı
  yapılmadan HERKESE (öğrenciye de) gösteriliyor. Veri güvenliği sorunu YOK — backend her admin
  isteğinde is_platform_admin kontrolü yapıp 404 dönüyor. Sorun arayüzde: öğrenci tıklayınca
  boş/hata sayfası. Link metinleri koda gömülü (CLAUDE.md ihlali).
- GET /me (backend/app/api/me.py) is_platform_admin, rol ve email_verified dönmüyor →
  frontend rol bazlı UI yapamıyor (frontend/lib/api/engagements.ts başındaki "BACKEND GAP" notu).
- ENT-04: frontend/lib/api/engagements.ts EngagementStatus tipi ve messages/tr.json
  `calismalar.status` 6 durum içeriyor; EVALUATED, VERIFIED, DISPUTED, RESOLVED yok. Seed'deki
  15 engagement'ın 15'i VERIFIED → çalışmalar listesinde etiket boş. transitionAction sözlüğü aynı.
- IS-04: availableTransitions yalnız duruma bakıyor; her kullanıcıya her geçiş düğmesi görünüyor.
- ENT-06: backend/app/api/skill_signals.py ve verified_experiences.py route'ları "/" ile tanımlı;
  frontend sonda / olmadan çağırıyor → 307 (canlı doğrulandı). Proxy/HTTPS arkasında mixed-content riski.
- A-07 yazma uçlarına e-posta doğrulama zorunluluğu getirecek → arayüz 401 EMAIL_NOT_VERIFIED'i
  anlamlı göstermeli.

YAPILACAKLAR:
Backend (me.py, skill_signals.py, verified_experiences.py — senin dosyaların):
1. GET /me yanıtına ekle: user.is_platform_admin (bool), user.email_verified (bool),
   roles: {talent: bool, organization_admin_ids: [...], organization_member_ids: [...],
   institution_admin_ids: [...], institution_coordinator_ids: [...]} — Principal'dan türet
   (A-08 Principal'ı değiştirecek; alan adlarını A ile konuş, şimdilik mevcut Principal
   alanlarından + InstitutionMember.role sorgusundan üret). Yanıt şeması Pydantic, ORM değil.
   docs/API.md'yi güncelle. Mevcut yetkilendirme testlerini koş (yeni endpoint değil ama
   yanıt genişledi: başka kullanıcının üyelik bilgisi SIZMAMALI — test ekle).
2. ENT-06: iki router'da @router.get("") yap (ve geriye uyum için "/" ikinci dekoratör).
Frontend:
3. lib/session/types.ts MeResponse'u genişlet (isMeResponse doğrulaması dahil).
4. app-shell.tsx: admin linkleri yalnız `session.data.user.is_platform_admin` ise. Metinleri
   messages/tr.json'a taşı. Admin sayfaları (app/admin/*) admin olmayan kullanıcıda 404/"yetkiniz
   yok" yerine not-found göstersin (zaten backend 404 → mevcut davranışı doğrula).
5. EngagementStatus'a EVALUATED, VERIFIED, DISPUTED, RESOLVED; tr.json'a etiketler
   ("Değerlendirildi", "Doğrulandı", "İtiraz Edildi", "İtiraz Çözüldü"); NEXT_STATUSES'a
   backend tablosuyla birebir girişler (EVALUATED'ten geçiş transitions ucuyla yapılmaz —
   tanıklık ayrı uç; B-10 düğmesini ekleyecek). Bilinmeyen durum için güvenli fallback etiketi.
6. IS-04: availableTransitions(status, roles, engagement) — rol + engagement'ın
   organization_id/institution_id'si ile backend tablosundaki (backend/app/services/engagement.py
   transition_table) sıfat kurallarını yansıt. Sunucu yine son sözü söyler (403 ele alınıyor).
7. 401 EMAIL_NOT_VERIFIED için global bir bant: "E-postanı doğrula" + (A-07 resend ucu gelince)
   "Tekrar gönder" butonu. Metinler tr.json.
Testler: app-shell.test.tsx (öğrenci → admin linki yok; admin → var), engagements.test.ts
(tüm durum etiketleri), types.test.ts.

KABUL:
- AC-1: Öğrenci ile giriş → sayfa altında admin linkleri YOK; seed admin → VAR.
- AC-2: Çalışmalar listesinde VERIFIED engagement "Doğrulandı" etiketiyle görünür.
- AC-3: Koordinatör PENDING_APPROVAL engagement'ında yalnız Onayla/Reddet görür; talent görmez.
- AC-4: GET /talents/me/signals → 200 (307 değil).
- AC-5: /me başka kullanıcının üyeliklerini döndürmüyor (authz testi).
- AC-6: npm run lint, typecheck, ilgili vitest yeşil; kurum panel testi (§1.7) bu işle düzelirse işaretle.
BİTİŞ: §1.9. HATA.md ENT-04, ENT-05 ✅; IS-04 ✅ (UI); ENT-06 ◐ (inst/org POST A-14'te).
```

### B-03 · Engagement tarihleri (oluşturma + PATCH)

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.39 | IS-02 | KRİTİK | 2 | K8 | Z-GÜV | `feat/3.39-engagement-tarihleri` | `b03-engagement-tarihleri` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-03 — HATA.md IS-02. PLAN 3.39.
ZİNCİR (Z-GÜV — yeni endpoint): /atdd → threat-model → plan → authz-test → test-copilot →
code-copilot → verify → red-team. Slug: b03-engagement-tarihleri.
KARAR: K8 (öneri (b): oluşturmada opsiyonel + PATCH ucu).

BAĞLAM:
- backend/app/services/attestation.py _check_competence_preconditions: started_on/ended_on
  boşsa ENGAGEMENT_DURATION_BELOW_THRESHOLD → COMPETENCE hiç verilemez.
- Bu alanları set eden API yok: POST /engagements (backend/app/api/engagements.py
  PostEngagementRequest) almıyor, PATCH yok. Yalnız backend/scripts/seed.py doğrudan yazıyor.
- DB'de CHECK var: ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on.
- Tarih snapshot'ı tanıklık anında VerifiedExperience'a kopyalanıyor.

YAPILACAKLAR:
1. PostEngagementRequest: started_on: date | None, ended_on: date | None; Pydantic
   model_validator ile ended_on >= started_on (422). Makul aralık: 2000-01-01 ≤ tarih ≤ bugün+2 yıl.
   Yanıt şemalarına (PostEngagementResponse, EngagementDetailResponse) started_on/ended_on ekle.
2. Yeni uç: PATCH /engagements/{id}/dates — gövde {started_on?, ended_on?, version}.
   - Yetki: engagement scope'unda + (org üyesi/admin'i O ORGANİZASYONUN) veya (talent sahibi).
     Kararı atdd'de yaz; A-08 sonrası "sıfat" yardımcısına taşınacak — şimdilik mevcut desenle
     (principal.kind + org_ids/talent_id) yaz, kod yorumunda A-08'e atıf yap.
   - İzinli durumlar: DRAFT, PENDING_APPROVAL, ACTIVE. Diğerleri → 409 (snapshot sonrası değişmez).
   - Optimistic lock: version eşleşmezse 409; başarıda version+1 (transition ile aynı UPDATE deseni).
   - Audit: ENGAGEMENT_DATES_UPDATED (metadata: yalnız alan adları, eski/yeni tarih yazılabilir — PII değil).
   - Scope dışı → 404; scope içi ama yetkisiz sıfat → 403 (transition'daki gibi) ya da 404 —
     docs/AUTHORIZATION.md'ye bak, tutarlı ol.
3. docs/API.md'ye iki değişikliği yaz.
4. Frontend sözleşmesi: frontend/lib/api/engagements.ts EngagementDetail'e started_on/ended_on
   ekle (ekran işi B-08'de).

KABUL:
- AC-1: POST /engagements tarihlerle → 201, detayda tarihler görünüyor.
- AC-2: ended_on < started_on → 422.
- AC-3: ACTIVE engagement'ta org üyesi PATCH → 200, version+1; eski version ile → 409.
- AC-4: VERIFIED engagement'ta PATCH → 409.
- AC-5: Başka org'un üyesi → 404; talent B → 404 (authz testi, aynı commit).
- AC-6: Tarihleri ≥28 gün olan, diğer ön koşulları sağlanan engagement'ta tanıklık → COMPETENCE.
DOĞRULAMA: pytest tests/authorization -q (tamamı) + tests/test_engagement*.py + tests/test_attestation.py.
BİTİŞ: §1.9.
```

### B-04 · Public token, VE görünürlüğü, geri çekme okuma filtresi

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.40 | IS-01, GUV-05, GUV-03 (gösterim), L-05 | KRİTİK | 3 | A-05, K2, K4 | Z-GÜV | `feat/3.40-public-dogrulama-linki` | `b04-public-token` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-04 — HATA.md IS-01, GUV-05, GUV-03 (yalnız public gösterim), L-05. PLAN 3.40.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → authz-test → test-copilot → code-copilot →
verify → red-team. Slug: b04-public-token.
KARARLAR: K4 (öneri (b): VE satırı değişmez, okuma katmanı filtreler), K2 (öneri (b): public'te
kurum seviyesi + org alan adı gösterimi).
ONAY NOKTASI: yetkilendirme sorgusu değişikliği (authorization.py'ye fonksiyon ekleme — Kişi A'ya
haber ver) ve olası data migration.

BAĞLAM:
- backend/app/services/verified_experience.py generate_public_token() hiçbir yerden
  çağrılmıyor (kendi docstring'i "YERINDE kalmış" diyor). backend/app/services/attestation.py
  VerifiedExperience'ı visibility="PRIVATE", public_token=None ile oluşturuyor. Görünürlüğü
  değiştiren uç YOK. Canlı: 15 VE, 0 token, 0 PUBLIC → GET /public/v/{token} hep 404,
  GET /public/talents/{slug} deneyim listesi hep boş.
- GUV-05: revoke_attestation yalnız attestation + ATTESTATION kaynaklı sinyalleri işaretliyor;
  revoked_at hiçbir okumada filtrelenmiyor: backend/app/services/authorization.py
  scoped_attestations_for_engagement geri çekilenleri döndürüyor → public sayfada skill hâlâ
  COMPETENCE; VE ve profil geçerli görünüyor.
- GUV-03 (gösterim): public doğrulama sayfası organization_trust_level gösteriyor ama kurum
  seviyesini ve org alan adını göstermiyor; org adı serbest metin.
- L-05: GET /public/talents/{slug} iç talent_id (UUID) döndürüyor; /public/v/{token}
  deleted_at'li talent'ı filtrelemiyor.
- verified_experiences tablosu append-only; CLAUDE.md istisnası: visibility. public_token set
  etmek de bir UPDATE → A-12 trigger'ı "NULL→değer set-once" olarak izin verecek; sen A-12'den
  ÖNCE bitiriyorsun, trigger henüz yok.

YAPILACAKLAR:
1. Tanıklık anında (create_attestation) VE'ye public_token = generate_public_token() yaz
   (INSERT anında — UPDATE değil). UNIQUE kısıt migration'da var mı kontrol et (m4n5... migration).
2. Mevcut VE'ler için backfill: token'ı NULL olan VE'lere token üret. Seçenek: (a) data migration
   (ONAY), (b) seed'e idempotent backfill fonksiyonu (A-05'in bıraktığı yer). Öneri: (b) + ayrıca
   PATCH ucu token yoksa üretir (3. madde) → gerçek kullanıcıların eski kayıtları da çözülür.
3. Yeni uç: PATCH /talents/me/verified-experiences/{id} gövde {visibility} —
   Literal['PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC']. Yalnız sahibi (scoped_own_verified_experiences).
   public_token NULL ise burada üret. Başkasının VE'si → 404. Audit VE_VISIBILITY_CHANGED.
   Yetkilendirme testi aynı commit'te.
4. K4 okuma filtresi: "aktif tanıklık" = engagement'ın revoked_at IS NULL en az bir tanıklığı.
   - scoped_attestations_for_engagement: revoked_at IS NULL filtresi.
   - scoped_public_verified_experience_by_token ve public profil VE sorgusu: aktif tanıklığı
     olmayan VE'yi döndürme (EXISTS alt sorgusu) → /public/v/{token} 404.
   - GET /talents/me/verified-experiences: sahibi görmeye devam eder ama `revoked: true` alanıyla.
   Bu değişiklikler authorization.py'de (A'nın dosyası): yalnız sorgu fonksiyonu ekle/değiştir;
   Kişi A'ya haber ver.
5. Public doğrulama yanıtına: institution_trust_level (kurum verification_level) ve
   organization_domain (yalnız org T2+ ise; değilse null). talent_name kalır.
6. L-05: public profil yanıtından talent_id'yi çıkar (frontend frontend/app/p/[slug]/page.tsx ve
   lib/api/public.ts kullanıyor mu kontrol et; kullanıyorsa kaldır). /public/v/{token}'da
   talent_profile.deleted_at IS NULL şartı (tek WHERE — zamanlama farkı olmasın).
7. docs/API.md güncelle.

KABUL:
- AC-1: Yeni tanıklık → VE.public_token dolu (≥43 karakter), visibility PRIVATE → /public/v/{token} 404.
- AC-2: Sahibi PATCH visibility=PUBLIC → /public/v/{token} 200; /public/talents/{slug} (talent
  PUBLIC ise) deneyimi listeler.
- AC-3: Tanıklık geri çekilince /public/v/{token} 404; sahibi listesinde revoked:true.
- AC-4: Talent B, talent A'nın VE'sine PATCH → 404 (authz testi).
- AC-5: Public yanıtlarda talent_id/engagement_id/iç UUID yok.
- AC-6: Seed backfill sonrası DB'de token'ı NULL VE yok.
DOĞRULAMA: pytest tests/authorization -q (tamamı) + tests/test_public_*.py tests/test_attestation*.py.
BİTİŞ: §1.9. A-12'ye (Kişi A) "VE'de UPDATE edilen alanlar: visibility, public_token (set-once)" notunu ilet.
```

### B-05 · Skill sinyal ve tanıklık kuralları

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.41 | GUV-04, IS-05, IS-06 | YÜKSEK | 4 | K10 | Z-GÜV | `fix/3.41-skill-sinyal-kurallari` | `b05-sinyal-kurallari` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-05 — HATA.md GUV-04, IS-05, IS-06. PLAN 3.41.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → test-copilot → code-copilot → verify → red-team.
Slug: b05-sinyal-kurallari. KARAR: K10.

BAĞLAM:
- GUV-04: backend/app/services/evaluation.py sinyal üretimi yönden bağımsız. Talent
  TALENT_TO_ORG değerlendirmesinde maddeye skill_id + EXCEEDS yazarsa kendi talent_id'si için
  STRONG sinyal (attested_by_org_id=None) üretiliyor. Teslim (create_deliverable) her seferinde
  MODERATE; görev oluşturma WEAK (engagement.py).
- IS-05: create_attestation'da geçersiz skill_id sessizce yok sayılıyor (değerlendirmede 422);
  skill ACTIVE mi bakılmıyor. Koordinatör tanıklığında attestor_org_id = engagement.organization_id
  (koordinatör o organizasyondan değil). Değerlendirme yükünde criterion/comment/private_note/items
  için üst sınır yok.
- IS-06: claim silinince SELF_CLAIM sinyali kalıyor; yeniden eklenince ikinci sinyal. GET
  /talents/me/signals her sinyal için attested_by: None dönüyor. Skill MERGE edilince iddia/sinyaller
  hedefe yönlenmiyor; parent_id döngüsü engellenmiyor (bu son ikisi B-13'te).
- Mevcut YET-71 testleri eski davranışı sabitliyor olabilir — değişen her testi gerekçesiyle listele.

YAPILACAKLAR:
1. evaluation.py: yalnız direction == "ORG_TO_TALENT" iken sinyal üret. TALENT_TO_ORG maddelerinde
   skill_id kabul edilsin mi? → öneri: kabul et ama sinyal üretme (kayıt amaçlı); atdd'de yaz.
2. K10: DELIVERABLE_SIGNAL_STRENGTH → "WEAK" (karar değilse dokunma).
3. create_attestation skill_id: geçersiz format/olmayan/ACTIVE olmayan → 422 INVALID_REQUEST
   (değerlendirmeyle tutarlı; AttestationCreateRequest'te uuid.UUID tipine geç). API router'da
   yeni istisna eşlemesi.
4. attestor_org_id: institution_id doluysa (koordinatör tanıklığı) attestor_org_id = None mi,
   yoksa ayrı attestor_institution_id mi? Kolon yoksa migration gerekir → öneri: attestor_org_id=None
   ve public yanıtta "attestor_organization" yerine kurum adı (B-04'ün alanlarıyla uyumlu).
   CHECK kısıtları (ck_attestations_*) buna izin veriyor mu kontrol et; vermiyorsa DUR, sor.
5. Evaluation şeması: criterion max 200, comment max 2000, private_note max 4000, items max 30 (422).
6. skill_claim remove: silinen claim'in SELF_CLAIM sinyaline NONE tombstone ekle ve superseded_by_id
   ile bağla (attestation revoke'daki desen; trigger set-once izin veriyor).
7. skill_signal.py: attested_by = {organization_id, organization_name} (attested_by_org_id varsa),
   yoksa null. Superseded sinyaller listede "superseded": true ile kalır (mevcut).

KABUL:
- AC-1: Talent TALENT_TO_ORG'da EXCEEDS+skill_id → skill_signals'ta yeni satır YOK.
- AC-2: Org ORG_TO_TALENT'ta EXCEEDS+skill_id → STRONG, attested_by_org_id = org.
- AC-3: Tanıklıkta geçersiz skill_id → 422.
- AC-4: 31 maddelik değerlendirme → 422; 2001 karakter comment → 422.
- AC-5: Claim sil → SELF_CLAIM sinyali superseded; /talents/me/signals'ta superseded:true.
- AC-6: /talents/me/signals'ta ORG sinyalinin attested_by'ı dolu.
DOĞRULAMA: pytest tests/authorization -q + tests/test_evaluation.py tests/test_skill_signals.py
tests/test_skill_claim.py tests/test_attestation.py.
BİTİŞ: §1.9.
```

### B-06 · Durum makinesi dokümana uysun

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.42 | AUTHZ-03, IS-03, GUV-08 | YÜKSEK | 4 | K2, K5 | Z-GÜV | `fix/3.42-durum-makinesi` | `b06-durum-makinesi` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-06 — HATA.md AUTHZ-03, IS-03, GUV-08. PLAN 3.42.
ZİNCİR (Z-GÜV): /atdd → threat-model → plan → authz-test → test-copilot → code-copilot →
verify → red-team. Slug: b06-durum-makinesi. ONAY NOKTASI: yetki (geçiş sahipliği) değişikliği.
KARARLAR: K5 (öneri (b): T4 yok, institution_id zorunlu), K2 (öneri (b)).
NOT: A-08 (Senkron-1'den sonra) bu tabloyu "sıfat" modeline taşıyacak; sen bugünkü kind
modeliyle, kuralları dokümana uydur.

BAĞLAM (docs/STATE_MACHINE.md satır ~100-120 tablosunu oku):
- T5 ACTIVE→PENDING_EVALUATION: doküman TALENT veya ORG:SUPERVISOR; kod ORG üyesi/admin veya
  COORDINATOR, TALENT yapamıyor.
- T4 DRAFT→ACTIVE (kurumsuz) yok → institution_id NULL engagement DRAFT'ta kalıyor; tanıklıktaki
  "kurumsuz → ORG_ADMIN" dalı ölü.
- Tanıklık kriter 1 "karşılıklı onay" (iki yönlü değerlendirme) kontrol edilmiyor.
- DRAFT'ı iptal/silme yok; REJECTED'tan yeniden gönderme yok (doküman: REJECTED terminal — doğru).
- `reason` her geçişte üzerine yazılıyor, uzunluk sınırı yok.
- Görev durumu değiştirilemiyor (PLANNED→DONE ucu yok).
- GUV-08: create_engagement'ta TALENT herhangi bir organizasyon için, ORG_MEMBER herhangi bir
  talent için engagement açabiliyor; institution_id uyuşmazlığı 400, uyuşunca 201 → talent'ın
  kurumunu öğrenme oracle'ı.

YAPILACAKLAR:
1. T5: TALENT sahibi de yapabilsin (doküman); COORDINATOR'ın yetkisi dokümanda yok → kaldırılsın mı?
   Kullanıcıya sor (öneri: dokümana uy, kaldır; ama seed/test etkisine bak).
2. K5=(b): create_engagement'ta institution_id yoksa talent'ın institution_id'sini kullan;
   talent'ın kurumu yoksa 422 INSTITUTION_REQUIRED. Böylece "institution_id uyuşmazlığı" durumu
   ortadan kalkar → oracle kapanır (GUV-08). Gövdedeki institution_id alanı: kaldır ya da yok say
   (sözleşme değişikliği → docs/API.md). Tanıklıktaki kurumsuz dal: K5=(b) ise ölü kod yorumu ekle.
3. Kriter 1: tanıklık ön koşullarına "TALENT_TO_ORG değerlendirmesi var mı" ekle →
   yoksa downgrade reason ENGAGEMENT_NOT_MUTUALLY_CONFIRMED (kod zaten ayrılmış).
   DİKKAT: bu seed'deki demo COMPETENCE senaryosunu etkiler — A-05'in demo engagement'ında
   TALENT_TO_ORG değerlendirmesi var mı kontrol et; yoksa Kişi A'ya söyle.
4. DRAFT → CANCELLED (talent sahibi ya da oluşturan org üyesi, reason zorunlu) — doküman
   tablosunda yoksa önce docs/STATE_MACHINE.md'ye ekle (karar kaydı), sonra kod.
5. reason: yalnız reason gerektiren geçişlerde yazılsın; diğerlerinde gönderilen reason yok
   sayılsın; max 1000 karakter (422).
6. GUV-08 rıza kısmı (K2=(b)): yeni onay geçişi YOK. Ama talent'ın kendi adına başkasının açtığı
   engagement'ı görmesi normal. Bunu atdd Risks'e yaz.
7. Görev durumu (PLANNED→IN_PROGRESS→DONE): MVP'de gerekli mi? Zincir için gerekmiyor → kapsam
   dışı, HATA.md IS-03'e "◐ görev durumu ertelendi" notu.
8. frontend/lib/api/engagements.ts NEXT_STATUSES'ı yeni tabloya uydur (B-02'nin yapısını kullan).

KABUL:
- AC-1: Talent sahibi ACTIVE+deliverable → PENDING_EVALUATION 200.
- AC-2: Kurumu olmayan talent için POST /engagements → 422 INSTITUTION_REQUIRED.
- AC-3: Farklı institution_id gönderilse de sonuç talent'ın kurumuyla oluşur (oracle yok).
- AC-4: TALENT_TO_ORG değerlendirmesi olmadan tanıklık → downgrade ENGAGEMENT_NOT_MUTUALLY_CONFIRMED.
- AC-5: T1'de gönderilen reason, T3 gerekçesini ezmiyor; 1001 karakter reason → 422.
- AC-6: DRAFT→CANCELLED (karar verildiyse) çalışır, audit yazılır.
DOĞRULAMA: pytest tests/authorization -q (tamamı) + tests/test_engagement_transitions.py
tests/test_engagement.py tests/test_attestation.py + frontend typecheck/vitest.
BİTİŞ: §1.9. docs/STATE_MACHINE.md'deki tabloyu kodla eşitle.
```

### B-07 · Değerlendirme formu gerçek backend'e

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.18 (+3.19 kısmi) | ENT-02 (değerlendirme) | KRİTİK | 5 | B-02, B-05 | Z-UI | `fix/3.18-degerlendirme-gercek-backend` | `b07-degerlendirme-fe` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-07 — HATA.md ENT-02 (değerlendirme kısmı), PLAN 3.18 ve 3.19'un değerlendirme kısmı.
ZİNCİR (Z-UI): /atdd → plan → test-copilot → code-copilot → verify (vision-test: form + hata
durumları) → red-team. Slug: b07-degerlendirme-fe.

BAĞLAM:
- frontend/lib/api/evaluation.ts submitEvaluation() her koşulda localStorage; private_note düz
  metin localStorage'da (.claude/rules/frontend.md "localStorage kullanılmaz").
- Backend: POST /engagements/{id}/evaluation (backend/app/api/engagements.py). Yanıt kodları:
  201; 404 NOT_FOUND; 403 FORBIDDEN (yön/rol uyuşmazlığı); 409 CONFLICT — hem "bu durumda
  değerlendirilemez" hem "zaten gönderilmiş" (message farklı, code aynı); 422 INVALID_REQUEST
  (skill) / VALIDATION_ERROR (Pydantic). private_note yanıtta YOK. B-05 alan uzunluk sınırları ekledi.
- Mock 422 INVALID_STATUS ve 409 ALREADY_SUBMITTED üretiyor — gerçek backend'de 422 INVALID_STATUS yok.
- Bilinen kırık testler: lib/api/evaluation.test.ts (6) ve evaluation-form.test.tsx (1) — mock
  store'u varsayıyor; bu iş bunları gerçek sözleşmeye göre yeniden yazar (§1.7'den düş).
- "Gönderildi mi?" bilgisi için backend'de GET yok → hasSubmittedEvaluation mock'tan geliyor.

YAPILACAKLAR:
1. submitEvaluation → apiFetch POST, gövde {direction, items, private_note}. Yanıt tipi
   EvaluationResponse (private_note yok).
2. Hata eşleme: 409 → message'a göre değil, iki durumu ayırt etmek için önce engagement durumunu
   bil (sayfa zaten getEngagement çağırıyor): durum PENDING_EVALUATION değilse "Bu çalışma şu an
   değerlendirilemez"; ise "Bu yönde zaten değerlendirme gönderdiniz". 403 → "Bu yönde değerlendirme
   yapma yetkiniz yok". 422 → alan hatası. Metinler tr.json.
3. hasSubmittedEvaluation: backend GET ucu olmadan bilinemez. Seçenek: (a) kaldır; gönderim sonrası
   409'u "zaten gönderilmiş" olarak göster, başarılı gönderimden sonra TanStack Query cache'inde
   tut; (b) backend'e GET /engagements/{id}/evaluations/mine ucu (yeni endpoint + authz testi —
   iş büyür). Öneri (a); kullanıcıya sor.
4. Yön: /me roller (B-02) → talent TALENT_TO_ORG, org üyesi ORG_TO_TALENT formu; koordinatöre form gösterme.
5. localStorage kodunu ve EVALUATION_STORAGE_KEY'i tamamen kaldır. Uygulama açılışında eski anahtarı
   temizleyen tek seferlik kod (localStorage.removeItem('...')) — try/catch ile.
6. Başarılı ORG_TO_TALENT gönderimi engagement'ı EVALUATED yapar → engagement query'sini invalidate et.
7. Dosya başı yorumunu güncel duruma göre yeniden yaz.

KABUL:
- AC-1: Org üyesi PENDING_EVALUATION engagement'ında formu gönderir → backend'de evaluation satırı,
  engagement EVALUATED, arayüz "Değerlendirildi".
- AC-2: `grep -n "localStorage" frontend/lib/api/evaluation.ts` → yalnız eski anahtar temizliği (ya da hiç).
- AC-3: İkinci gönderim → "zaten gönderdiniz" mesajı.
- AC-4: private_note hiçbir tarayıcı deposunda/istek yanıtında görünmüyor.
- AC-5: evaluation.test.ts ve evaluation-form.test.tsx yeşil (gerçek sözleşmeye göre, fetch mock'lu).
DOĞRULAMA: npm run typecheck, npm run lint, npx vitest run lib/api/evaluation.test.ts
"app/calismalar/[id]/degerlendirme"; canlı: seed'in PENDING_EVALUATION demo engagement'ı (A-05) ile.
BİTİŞ: §1.9. PLAN 3.18 [x].
```

### B-08 · Engagement oluşturma + teslim ekranları

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.43 | ENT-01 (a) | KRİTİK | 5 | B-02, B-03, B-06 | Z-UI | `feat/3.43-engagement-olusturma-teslim` | `b08-olusturma-teslim` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-08 — HATA.md ENT-01'in (a) kısmı: engagement oluşturma, tarih düzenleme, teslim
(deliverable), görev ekranları. PLAN 3.43.
ZİNCİR (Z-UI): /atdd → plan → test-copilot → code-copilot → verify (vision-test + frontend-audit
araçlarıyla erişilebilirlik) → red-team. Slug: b08-olusturma-teslim.

BAĞLAM:
- Backend uçları var ama frontend hiç çağırmıyor: POST /engagements, POST /engagements/{id}/tasks,
  POST /engagements/{id}/deliverables, (B-03) PATCH /engagements/{id}/dates.
- ACTIVE→PENDING_EVALUATION en az bir deliverable gerektiriyor; teslim ekranı olmadığı için seed
  dışı hiçbir engagement arayüzden değerlendirmeye ulaşamıyor.
- Organizasyon seçimi: talent hangi org'u seçecek? Backend'de org listeleme/arama ucu YOK
  (GET /organizations/{id} yalnız üyeye). Seçenek: (a) organization_id metin alanı (kötü UX),
  (b) org üyesi engagement'ı talent için açar (ORG_MEMBER akışı; talent_id gerekir — talent
  arama ucu yok), (c) yeni uç: GET /organizations?q= (T2+ ya da tümü, yalnız {id, name,
  verification_level}) — yeni endpoint + authz testi. KULLANICIYA SOR; öneri (c) minimal:
  yalnız ad araması, sayfa başı 20, kimliği doğrulanmış herkes (org adları kamusal bilgi sayılır).
  (c) seçilirse backend kısmı organizations.py → Kişi A'nın dosyası: A'ya haber ver/ya da A yazsın.

YAPILACAKLAR:
1. /calismalar/yeni sayfası: tür (kind), başlık, organizasyon seçimi, başlangıç/bitiş tarihi.
   Kurumu olmayan talent'a "önce kurumuna bağlan" mesajı (B-06 422 INSTITUTION_REQUIRED).
   Zod şeması lib/engagements/schemas.ts; metinler tr.json.
2. Oluşturduktan sonra DRAFT detayında "Onaya gönder" (T1) düğmesi zaten transition-actions'ta var —
   akışı doğrula.
3. Detay sayfasında (app/calismalar/[id]/page.tsx):
   - Talent sahibi + ACTIVE → "Teslim ekle" formu (başlık, açıklama, opsiyonel skill seçimi —
     GET /skills araması; mevcut skills-section bileşenini yeniden kullan).
   - Org üyesi + ACTIVE → "Görev ekle" formu.
   - Tarih düzenleme (B-03 PATCH) — izinli durumlarda ve sıfatlarda.
   - Teslim listesi zaten detayda var; yeni teslim sonrası invalidate.
4. Hata durumları: 403/404/409/422 anlaşılır Türkçe; teknik detay sızmaz.
5. Klavye erişimi, focus görünürlüğü, boş durumlar (CONTRIBUTING frontend kontrol listesi).
6. lib/api/engagements.ts'ye createEngagement, createDeliverable, createTask, updateDates.

KABUL:
- AC-1: Seed talent yeni engagement açar → DRAFT → onaya gönderir → PENDING_APPROVAL.
- AC-2: ACTIVE engagement'ta talent teslim ekler → listede görünür → org üyesi "Değerlendirmeye
  gönder" yapabilir (ya da B-06 sonrası talent).
- AC-3: Tarih hatası (bitiş < başlangıç) formda gösterilir, istek atılmaz.
- AC-4: vitest: form doğrulama, başarılı gönderim, 422/403 mesajları.
- AC-5: vision-test/erişilebilirlik gate'leri PASS.
DOĞRULAMA: npm run typecheck, lint, vitest (ilgili), canlı akış seed kullanıcılarıyla.
BİTİŞ: §1.9.
```

### B-09 · Kanıt yükleme gerçek backend'e

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.17 (+3.19) | ENT-02 (kanıt) | KRİTİK | 6 | **A-03, A-04, A-06** | Z-UI | `fix/3.17-kanit-gercek-backend` | `b09-kanit-fe` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-09 — HATA.md ENT-02 (kanıt kısmı), PLAN 3.17 ve 3.19. ZİNCİR (Z-UI). Slug: b09-kanit-fe.
ÖN KOŞUL: A-03 (bucket + CORS), A-04 (worker döngüsü), A-06 (tarama + GET /evidence) main'de.
`git log main --oneline` ile teyit et; değilse dur ve Kişi A'ya sor.

BAĞLAM:
- frontend/lib/api/evidence.ts: USE_MOCK_UPLOAD_URL = true, USE_MOCK_STORAGE_UPLOAD = true;
  adım 3 (recordEvidence) koşulsuz localStorage. Dosya başı yorumu "POST /evidence backend'de HİÇ
  YOK" diyor — yanlış, var.
- Akış: (1) POST /evidence/upload-url {filename, content_type, size_bytes} → {upload_url,
  upload_fields, object_key, expires_in}; (2) tarayıcıdan presigned POST (multipart/form-data:
  önce upload_fields, EN SON "file" alanı — S3 kuralı); (3) POST /evidence {storage_key: object_key,
  kind, mime_type, size_bytes, deliverable_id?} → scan_status PENDING; worker taradıktan sonra CLEAN.
- A-06: GET /evidence liste ucu + download-url yalnız CLEAN'de. Yanıt şeması A-06 PR açıklamasında.
- Bilinen kırık: evidence-upload-form.test.tsx (1).

YAPILACAKLAR:
1. Mock bayraklarını ve localStorage kodunu tamamen kaldır; dosya başı yorumunu yeniden yaz.
2. Adım 2: FormData sırası (fields sonra file); Content-Type'ı elle SET ETME (boundary tarayıcıda).
   MinIO 204/201 → başarı. Ağ hatası/403 (policy ihlali: boyut/tip) → anlaşılır mesaj.
3. Adım 3 gerçek apiFetch. deliverable_id: B-08'deki teslim formundan ya da detay sayfasından bağla.
4. Liste: profildeki evidence-section ve engagement detayı GET /evidence'tan okusun; scan_status
   rozeti (Taranıyor / Hazır / Reddedildi / Başarısız) ve PENDING'de 5 sn'de bir yeniden çek
   (TanStack Query refetchInterval, CLEAN/INFECTED/FAILED'da dur).
5. İndirme: CLEAN kanıtta "İndir" → GET /evidence/{id}/download-url → yeni sekmede aç
   (rel="noopener noreferrer"); 409'da "dosya henüz hazır değil".
6. Eski localStorage anahtarını tek seferlik temizle.
7. 3.19 doğrulaması: `grep -rn "localStorage" frontend/lib frontend/app --include=*.ts --include=*.tsx
   | grep -v test` → yalnız temizlik kodu (B-07 ve bu iş).

KABUL:
- AC-1: Gerçek PNG yükle → MinIO'da nesne var → evidence satırı → birkaç sn içinde "Hazır" → indir çalışır.
- AC-2: 11 MB dosya → istemci tarafında reddedilir (upload-url 422'yi de ele al).
- AC-3: PDF uzantılı PNG (A-06 AC-2) → "Reddedildi" rozeti, indirme yok.
- AC-4: Mock bayrağı ve localStorage kodu yok (grep).
- AC-5: evidence-upload-form.test.tsx ve evidence-section.test.tsx fetch mock'larıyla yeşil.
DOĞRULAMA: npm run typecheck, lint, vitest (ilgili) + canlı uçtan uca yükleme (Docker + worker açık).
BİTİŞ: §1.9. PLAN 3.17 ve 3.19 [x].
```

### B-10 · Tanıklık, geri çekme, deneyim paylaşımı ekranları

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.44 | ENT-01 (b), IS-01 (UI) | KRİTİK | 6-7 | B-02, B-04, B-05 | Z-UI | `feat/3.44-taniklik-paylasim-ekranlari` | `b10-taniklik-paylasim` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-10 — HATA.md ENT-01'in (b) kısmı + IS-01'in arayüz kısmı. PLAN 3.44.
ZİNCİR (Z-UI): /atdd → plan → test-copilot → code-copilot → verify (vision-test: tanıklık
kartı, public doğrulama sayfası mobil genişlikte — jüri telefonundan açacak, PLAN 4.1) → red-team.
Slug: b10-taniklik-paylasim.

BAĞLAM:
- Backend: POST /engagements/{id}/attestations {claim_type, version, skill_id?} (EVALUATED
  engagement; kurumlu ise o kurumun COORDINATOR'ı — A-08 sonrası sıfat modeli), yanıt
  {id, claim_type, requested_claim_type, downgrade_reasons[]}; POST /attestations/{id}/revoke
  {revoke_reason} (yalnız tanıklığı yapan). B-04: PATCH /talents/me/verified-experiences/{id}
  {visibility}, liste yanıtında public_token ve revoked.
- Frontend'de bunların hiçbiri yok. Engagement detay yanıtında tanıklık bilgisi yok —
  geri çekme için attestation_id gerekir. Seçenek: detay yanıtına `attestations: [{id,
  claim_type, attestor_user_id == me?, revoked_at}]` ekle (backend engagements.py — senin
  dosyan; yetki: scope içindekiler görür, attestor kimliği yerine "bu tanıklığı sen yaptın" bool'u).
- Public sayfalar: frontend/app/v/[token]/page.tsx ve app/p/[slug]/page.tsx mevcut; B-04 yeni
  alanlar ekledi (institution_trust_level, organization_domain, talent_id kaldırıldı).

YAPILACAKLAR:
1. Engagement detayı (EVALUATED + koordinatör): "Tanıklık ver" paneli — claim_type seçimi
   (COMPETENCE varsayılan), opsiyonel skill, onay diyaloğu ("Bu işlem geri çekilebilir ama
   kayıt silinmez"). Yanıttaki downgrade_reasons'ı insan diline çevir (tr.json: her kod için
   açıklama — ENGAGEMENT_DURATION_BELOW_THRESHOLD, NO_DELIVERABLE, ATTESTOR_NOT_VERIFIED_SUPERVISOR,
   COORDINATOR_CONFIRMATION_MISSING, ENGAGEMENT_NOT_MUTUALLY_CONFIRMED).
2. VERIFIED + tanıklığı yapan → "Tanıklığı geri çek" (gerekçe zorunlu).
3. Profil (app/profil) doğrulanmış deneyimler bölümü: her VE için görünürlük seçici (PRIVATE /
   INSTITUTION / ORGANIZATIONS / PUBLIC) → PATCH; PUBLIC ise "Doğrulama linkini kopyala"
   (`${origin}/v/${public_token}`) + QR gerekmez (MVP). revoked:true ise "Geri çekildi" rozeti,
   paylaşım kapalı.
4. Public profil linki: talent visibility PUBLIC + public_slug varsa `/p/{slug}` kopyala.
5. /v/[token] sayfası: kurum seviyesi ve org alan adı göster; "Doğrulandı" rozetinin anlamını
   bir cümleyle açıkla (tr.json). Mobil genişlikte kırılmasın.
6. Yeni API fonksiyonları lib/api/engagements.ts / lib/api/verified-experiences.ts.

KABUL:
- AC-1: Koordinatör EVALUATED demo engagement'ında tanıklık verir → VERIFIED; claim_type ve
  varsa downgrade açıklamaları görünür.
- AC-2: Talent profilinde deneyimi PUBLIC yapar → linki kopyalar → gizli pencerede /v/{token} açılır.
- AC-3: Koordinatör tanıklığı geri çeker → /v/{token} artık "bulunamadı"; profilde "Geri çekildi".
- AC-4: Mobil (375px) public sayfa vision-test PASS.
- AC-5: vitest: panel görünürlük kuralları (rol × durum), hata mesajları.
DOĞRULAMA: npm run typecheck, lint, vitest + canlı uçtan uca (PLAN 4.1 senaryosunun provası).
BİTİŞ: §1.9. HATA.md ENT-01 ✅ (B-08 ile birlikte), IS-01 ✅.
```

### B-11 · Frontend testleri + CI'da vitest

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.45 | TEST-01 (frontend) | YÜKSEK | 7 | B-07, B-09 | Z-TEST | `test/3.45-frontend-testleri-ci` | `b11-frontend-test-ci` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-11 — HATA.md TEST-01 (frontend kısmı). PLAN 3.45. ZİNCİR (Z-TEST). Slug: b11-frontend-test-ci.
ONAY NOKTASI: CI yapılandırması (.github/workflows/ci.yml) değişikliği.
KURAL: Ürün kodunu değiştirme; test gerçek bir hatayı yakalıyorsa raporla ve dur.

BAĞLAM:
- 28 Eylül: `npx vitest run` → 9 kırık (§1.7). B-07/B-09 bir kısmını düzeltmiş olmalı.
  Kalanlar: kurum/[id]/panel/page.test.tsx (admin linki — B-02 ile düzelmiş olabilir) vb.
- CI frontend job'ı lint + typecheck + build koşuyor, vitest KOŞMUYOR → kırık testler görünmüyor.
- Lint 6 uyarı (kullanılmayan değişkenler: evidence-section.test.tsx 'rerender', v/[token]/page.test.tsx 'container' ...).

YAPILACAKLAR:
1. `npx vitest run` → güncel kırık listesi; her biri için kök neden (tablo).
2. Kırıkları düzelt: gerçek sözleşmeye göre fetch mock'ları; mock store varsayımlarını kaldır.
3. Lint uyarılarını gider (davranış değişmeden).
4. package.json'da "test": "vitest run" var mı? Yoksa ekle. CI'da frontend job'ına `npm test`
   adımı (typecheck'ten sonra). ONAY NOKTASI.
5. CI'da testlerin gerçek ağa çıkmadığını doğrula (fetch global mock'u vitest.setup.ts'de mi?);
   gerçek fetch çağrısı yakalanırsa test başarısız olsun (güvenlik ağı).

KABUL:
- AC-1: `npx vitest run` → 0 kırık. AC-2: `npm run lint` → 0 uyarı.
- AC-3: CI frontend job'ı vitest koşuyor (yeşil PR çalıştırmasıyla doğrula).
- AC-4: Testte gerçek ağ çağrısı → açık hata.
DOĞRULAMA: npm run lint && npm run typecheck && npx vitest run && npm run build.
BİTİŞ: §1.9. §1.7'deki frontend bilinen kırık listesini "kapandı" diye güncelle.
```

### B-12 · Kurum bağlanma talepleri + admin kuyruğu reddi

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.46 | IS-10, IS-11 | ORTA | 8 | **A-09** (institutions.py), A-08 | Z-GÜV | `feat/3.46-baglanma-talepleri` | `b12-baglanma-talepleri` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-12 — HATA.md IS-10 ve IS-11. PLAN 3.46. ZİNCİR (Z-GÜV — yeni endpoint'ler).
Slug: b12-baglanma-talepleri.
DOSYA NOTU: backend/app/api/institutions.py ve services/institution.py Kişi A'nın; A-09 main'de
olmadan başlama. Başlarken A'ya "institutions dosyalarına giriyorum" de.

BAĞLAM:
- IS-10: Koordinatörün bekleyen bağlanma taleplerini görmesini sağlayan liste ucu yok; onay ucu
  request_id istiyor; reddetme ucu yok; talent kendi taleplerini göremiyor; frontend ekranı yok.
  Pratikte talent'ı kuruma bağlamanın tek yolu seed. (Kurum listesi/araması da yok — talent hangi
  kuruma talep atacak? → GET /institutions?q= (id, name, verification_level) gerekebilir.)
- IS-11: Admin "reddet" = aynı seviyeyi göndermek; kuyruk kriteri (T2 + legal_id) değişmediği için
  reddedilen org kuyrukta kalır; her çağrıda verified_at güncelleniyor (düşürmede bile);
  note serbest metni audit metadata'sına yazılıyor.

YAPILACAKLAR:
1. GET /institutions/{id}/link-requests?status=PENDING — yalnız o kurumun üyeleri (A-08 sıfat
   modeli); yanıt: id, talent adı, bölüm, created_at (e-posta YOK).
2. POST /institutions/{id}/link-requests/{rid}/reject {reason?} — PENDING → REJECTED, decided_*.
   Model CHECK'i REJECTED'ı destekliyor mu kontrol et; desteklemiyorsa migration → ONAY.
3. GET /talents/me/link-requests — talent kendi talepleri.
4. GET /institutions?q= — ad araması, limit 20, kimliği doğrulanmış herkes (kurum adı kamusal).
5. Frontend: profilde "Kurumuna bağlan" (arama + talep + durum); koordinatör panelinde
   (app/kurum/[id]/panel) bekleyen talepler listesi + Onayla/Reddet.
6. IS-11: admin kuyruğu için "reddedildi" durumu. Seçenek: organizations'a
   verification_review_status/last_reviewed_at kolonu (migration → ONAY) ya da kuyruk kriterine
   "son ADMIN_SET_VERIFICATION_LEVEL audit'inden sonra değişmemiş olanları hariç tut" (migration'sız
   ama sorgu karmaşık). Öneri: migration'sız çözüm yoksa en basit kolon; A-12 ile aynı gün değil.
   verified_at yalnız seviye YÜKSELİNCE güncellensin. note audit'e yazılmasın (ya da uzunluk + PII
   uyarısı) — kullanıcıya sor.
7. Yetkilendirme testleri: başka kurumun koordinatörü listeyi göremez (404), talent başkasının
   talebini göremez.

KABUL:
- AC-1: Talent kurum arar → talep atar → koordinatör panelde görür → onaylar → talent.institution_id dolu.
- AC-2: Reddetme → talent "Reddedildi" görür; yeni talep atabilir.
- AC-3: Admin reddi → org kuyruktan düşer; verified_at değişmez.
- AC-4: Tüm yeni uçlar için authz testleri aynı commit'te.
DOĞRULAMA: pytest tests/authorization -q (tamamı) + ilgili testler + frontend typecheck/vitest.
BİTİŞ: §1.9.
```

### B-13 · Profil düzeltmeleri, skill yönetimi, frontend bağımlılığı

| Sahip | PLAN | HATA | Öncelik | Gün | Bağımlılık | Zincir | Dal | Slug |
|---|---|---|---|---|---|---|---|---|
| B | 3.47 | IS-09, DEP-02, L-06, L-10, IS-06 (merge/parent) | ORTA | 8 | B-11 | Z-STD | `fix/3.47-profil-skill-duzeltmeleri` | `b13-profil-skill` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: B-13 — HATA.md IS-09, DEP-02, L-06, L-10 ve IS-06'nın merge/parent kısmı. PLAN 3.47.
ZİNCİR (Z-STD; DEP-02 için Z-BAĞ adımları). Slug: b13-profil-skill.
ONAY NOKTASI: next sürüm yükseltmesi (bağımlılık) — kırıcı değişiklik.

BAĞLAM:
- IS-09 (backend/app/api/me.py PATCH /talents/me): public_slug biçim doğrulaması yok; eşzamanlı
  iki istekte UNIQUE ihlali 500; None gönderilen alan yok sayılıyor → kullanıcı başlık/şehir/slug
  SİLEMİYOR; full_name güncellenemiyor.
- L-06: updated_at elle set ediliyor (TimestampMixin ile çakışma riski).
- L-10 / IS-06: skill.py update_skill parent_id'yi kaldıramıyor; parent döngüsü (A→B→A)
  engellenmiyor; MERGED skill DEPRECATED yapılabiliyor; merge sonrası mevcut claim/sinyaller hedefe
  yönlenmiyor (docs/DOMAIN.md §3.5).
- DEP-02: npm audit → next içindeki postcss ≤8.5.22 (1 high, 1 moderate); öneri next@16.3.6 (kırıcı).

YAPILACAKLAR:
1. public_slug: ^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$ (3-40), rezerve kelimeler (admin, api, p, v,
   giris, kayit...). IntegrityError → 409 SLUG_TAKEN.
2. Alan silme: Pydantic `model_fields_set` ile "gönderildi mi" ayrımı; açıkça null gönderilen alan
   NULL yapılır (visibility hariç — zorunlu). full_name (1-200) eklenir.
3. L-06: updated_at'i ORM'e bırak (onupdate) — TimestampMixin'i kontrol et.
4. Skill: update_skill'de parent_id=null ile kaldırma (model_fields_set); döngü kontrolü (üst
   zinciri yürü); MERGED → DEPRECATED yasak (409); okuma tarafında merge yönlendirmesi:
   list_skill_claims / list_skill_signals merged skill'i hedef skill'in bilgisiyle gösterir
   (veri değişmez — append-only). Admin ekranı (app/admin/skiller) etkileniyorsa uyumla.
5. DEP-02: önce `npm ls postcss` ile hangi next sürümünün düzelttiğini bul; next'in aynı ana
   sürümünde yamalı bir sürüm varsa onu tercih et (kırıcı olmayan). Yoksa kullanıcıya kırıcı
   yükseltme riskini anlat ve onay al; kod dondurmaya 1 gün kala büyük sürüm yükseltmesi
   önerilmez → reddedilirse HATA.md'ye "kabul edilen risk: build zamanı bileşeni" notu.
6. Frontend profil formu (profile-form.tsx) slug kuralını istemcide de göstersin; alan temizleme
   destekli.

KABUL:
- AC-1: "Ali Veli" slug → 422; "ali-veli" → 200; "admin" → 422.
- AC-2: headline:null → alan temizlenir.
- AC-3: Skill döngüsü → 422; MERGED→DEPRECATED → 409.
- AC-4: npm audit high 0 ya da gerekçeli kabul notu.
DOĞRULAMA: pytest tests/authorization -q + tests/test_talent.py tests/test_skill_*.py +
npm run typecheck/lint/vitest/build.
BİTİŞ: §1.9.
```

---

## 10. Prompt'lar — Kapanış

### O-01 · Senkron-1 entegrasyon kontrolü (2 Ekim akşamı, ikiniz)

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: O-01 — Senkron-1. Kod yazma; yalnız doğrula ve raporla.
1. `git switch main && git pull`. §5'te A-01…A-07 ve B-01…B-06 main'de mi? (`git log --oneline`,
   PR'lar). Eksik olanı listele.
2. `cd backend && .venv/Scripts/python.exe -m alembic heads` → tek başlı mı? İki başlıysa DUR:
   merge migration gerekir (ONAY).
3. `alembic upgrade head` → `python -m scripts.init_storage` (varsa) → `python -m scripts.seed` (iki kez).
4. `pytest -q` ve `pytest tests/authorization -q` → kırık listesi, §1.7'deki bilinen listeyle karşılaştır.
5. `cd frontend && npm run lint && npm run typecheck && npx vitest run`.
6. Canlı kısa duman: seed koordinatörle PENDING_APPROVAL onayı; seed org üyesiyle değerlendirme
   (B-07 henüz yoksa API ile); koordinatörle tanıklık → COMPETENCE; VE'yi PUBLIC yap → /public/v/{token} 200.
7. Rapor: tablo (adım / sonuç / sorumlu). A-08'in başlayıp başlayamayacağına karar ver:
   B-03…B-06 main'deyse "A-08 başlayabilir".
```

### O-02 · Son doğrulama + uçtan uca duman testi + HATA.md kapanışı (7 Ekim, ikiniz)

| PLAN | Zincir | Dal |
|---|---|---|
| 3.23, 2.14, 3.16 öncesi | Z-SON | `docs/3.23-son-dogrulama` |

```text
Önce HATA_DUZELTME_PROMPT.md dosyasının §1 "Ortak kurallar" bölümünü oku ve uygula.

GÖREV: O-02 — PLAN 3.23 (mock/localStorage son doğrulaması), PLAN 2.14 (uçtan uca duman testi),
HATA.md kapanışı, K6 dağıtım kararının dokümantasyonu. ZİNCİR (Z-SON):
verify (tam) → security-scan → frontend-audit → uçtan uca senaryo → postmortem.
Kod yazma; kırık bulursan raporla, ilgili kişiye prompt öner.

ADIMLAR:
1. main güncel; alembic tek başlı; temiz bir DB'de (docker volume'u SİLME — `docker compose down -v`
   YASAK; ayrı bir veritabanı adı oluşturabilirsin) upgrade head + init_storage + seed.
2. 3.23: `grep -rn "USE_MOCK\|localStorage\." frontend/lib frontend/app --include=*.ts --include=*.tsx | grep -v "\.test\."`
   → yalnız eski anahtar temizliği kalmalı.
3. verify skill'i: backend pytest -q (0 kırık), pytest tests/authorization -q, ruff + mypy,
   frontend lint/typecheck/vitest/build.
4. security-scan skill'i: secrets/SAST/pip-audit/npm audit → PASS ya da gerekçeli kabul.
5. Uçtan uca senaryo (PLAN 4.1 demo akışı) — backend + worker + frontend açık, tarayıcıda:
   a. Yeni öğrenci kaydı → console'daki doğrulama linki → /e-posta-dogrula → doğrulandı.
   b. Kurumuna bağlanma talebi → koordinatör onayı (B-12 yoksa seed öğrencisiyle devam).
   c. Profil: yetkinlik beyanı (beyan).
   d. Engagement oluştur (tarihli, T2 org) → onaya gönder → koordinatör onaylar.
   e. Öğrenci teslim + kanıt yükler (PNG/PDF) → tarama "Hazır" → indirilebiliyor (kanıt).
   f. Değerlendirmeye gönder → org üyesi değerlendirir; öğrenci TALENT_TO_ORG değerlendirir.
   g. Koordinatör tanıklık verir → COMPETENCE (tanıklık).
   h. Öğrenci deneyimi PUBLIC yapar → linki telefondan (ya da 375px) açar (doğrulanmış deneyim).
   i. Koordinatör tanıklığı geri çeker → link "bulunamadı". (Demo sonrası temizle.)
   j. 15 dakika bekleyip (ya da TTL'i kısaltıp) bir form gönder → 403 CSRF yok (B-01).
   k. Öğrenci hesabında sayfa altında admin linkleri yok (B-02).
   Her adımı ekran görüntüsüyle (frontend-audit/Playwright) belgele.
6. frontend-audit: public doğrulama sayfası Lighthouse erişilebilirlik ≥ 90, konsol hatası yok.
7. K6: docs/'a (ör. docs/DEPLOY.md ya da SETUP.md bölümü) seçilen topolojiyi, cookie/CSRF
   gereksinimini ve uvicorn --proxy-headers notunu yaz.
8. HATA.md: her ID'nin durumu (✅/◐/açık) — açık kalanlar için "kabul edilen risk" gerekçesi.
   Başa kısa bir "Kapanış durumu (7 Ekim)" tablosu ekle.
9. postmortem skill'i: tekrarlayan hata kalıpları → bir sonraki atdd için kontrol maddeleri.
10. PLAN 3.23 ve 2.14 [x]; 3.16 (kod dondurma) için kullanıcı onayı iste.
```

---

## 11. Kapsam haritası

Her HATA.md ID'si en az bir prompt'a bağlı. Kapanış O-02'de doğrulanır.

| HATA ID | Prompt | | HATA ID | Prompt |
|---|---|---|---|---|
| GUV-01 | A-01 | | IS-06 | B-05 (+merge/parent B-13) |
| GUV-02 | A-08 (DoS), A-09 (yanıt/K1) | | IS-07 | A-06 |
| GUV-03 | K2 → B-04 (gösterim), B-06 (oracle) | | IS-08 | A-05 (seed), A-07 |
| GUV-04 | B-05 | | IS-09 | B-13 |
| GUV-05 | B-04 | | IS-10 | B-12 |
| GUV-06 | A-02 | | IS-11 | B-12 |
| GUV-07 | A-09 | | ENT-01 | B-08, B-10 |
| GUV-08 | B-06 | | ENT-02 | B-07, B-09 |
| GUV-09 | A-15 | | ENT-03 | B-01 |
| GUV-10 | A-10 | | ENT-04 | B-02 |
| GUV-11 | A-10 | | ENT-05 (+admin linkleri ekip gözlemi) | B-02 |
| GUV-12 | A-06 | | ENT-06 | B-02 (signals/VE), A-14 (inst/org) |
| GUV-13 | A-15 | | ENT-07 | K6 → O-02 (doküman) |
| AUTHZ-01 | A-08 | | OPS-01 | A-04 |
| AUTHZ-02 | A-05 (seed), A-08 (kod) | | OPS-02 | A-04 |
| AUTHZ-03 | B-06 | | OPS-03 | A-03 |
| AUTHZ-04 | A-15 | | OPS-04 | A-14 |
| IS-01 | B-04, B-10 | | VER-01…03 | A-12 |
| IS-02 | A-05 (seed), B-03 | | TEST-01 | A-13, B-11 |
| IS-03 | B-06 (görev durumu ertelendi) | | TEST-02 | A-13 (A-01'de yerel) |
| IS-04 | B-02, B-06 | | DEP-01 | A-11 |
| IS-05 | B-05 | | DEP-02 | B-13 |
| L-01 | A-09 | | L-09 (N+1) | **Ertelendi** → PLAN 5.6 |
| L-02 | **Ertelendi** (org alan adı PATCH) | | L-10 | B-13 |
| L-03 | A-01 | | L-11, L-12, L-14 | A-14 |
| L-04 | A-02 | | L-13 | B-01 |
| L-05 | B-04 | | L-15 | O-00 |
| L-06 | B-13 | | L-16 | A-11 |
| L-07 | A-14 | | L-08 | A-08 |
| Önceki rapor #3 (.env.example) | A-03 | | Önceki rapor #1, #2, #4 | B-07, B-09 |
