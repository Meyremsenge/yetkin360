# PLAN.md — Yetkin360

Yapılacak işlerin **sırası** ve ilerleme durumu. Tek doğruluk kaynağı: bu dosya.
Kararların gerekçesi burada değil → `yetkin360-final-analiz.md`, detay → `docs/`.

**Durum işaretleri:** `[ ]` yapılacak · `[~]` devam ediyor · `[x]` bitti · `[-]` iptal/ertelendi

**Sahip etiketleri:** `@be1` `@be2` backend · `@fe` frontend · `@all` ortak
*(İsim eşlemesi CONTRIBUTING.md'de; etiket sabit kalır ki plan satırı kısa olsun.)*

**Altın kural (final analiz §35.2):** Tek uçtan uca senaryo kusursuz çalışsın —
`beyan → kanıt → tanıklık → doğrulanmış deneyim`. Bu zincir çalışmıyorsa
hiçbir ek ekran kurtarmaz.

**Sözleşme önce kuralı:** Bir maddenin API sözleşmesi (`docs/API.md`) yazılmadan
`@fe` o ekranı bekleyemez. Sözleşme yazılır → `@fe` mock ile ilerler → backend
gerçeğini bağlar. Backend'in bitmesini beklemek 3 kişilik ekipte en büyük israftır.

---

## Faz 0 — Karar kilitleme (15-18 Eylül)

Ürün kodu yok. Çıktı: yazıya dökülmüş kararlar + çalışan iskelet.

- [ ] 0.1 **Lisans teyidi:** şartname izin verici lisans şart koşuyor mu? Lisans
      seçilir, `LICENSE` tam metinle doldurulur, bağımlılık uyumu kontrol edilir @all
- [x] 0.2 `docs/DOMAIN.md` — entity, alan, ilişki, iş kuralları @be1
- [x] 0.3 `docs/DATABASE.md` — DDL, kısıt, index, append-only, silme politikası @be1
- [x] 0.4 `docs/API.md` — uç listesi, yetki, şema özeti, hata kodları @all
- [x] 0.5 `docs/AUTHORIZATION.md` — aktör × kaynak × eylem × HTTP kodu matrisi @be2
- [x] 0.6 `docs/SECURITY.md` — OWASP tablosu, dosya akışı, rate limit, senaryolar @be2
- [x] 0.7 `docs/STATE_MACHINE.md` — Engagement durumları, geçiş ön koşulları @be1
- [x] 0.8 Repo kökü: README, CONTRIBUTING, SECURITY.md, .gitignore, `docs/ENV.md` @all
- [x] 0.9 `.env.example` — `docs/ENV.md` §8 şablonundan repo köküne kopyalanır @all
- [x] 0.10 Docker Compose (PostgreSQL + MinIO) + backend iskeleti (FastAPI, alembic) @be2
- [x] 0.11 Frontend iskeleti (Next.js + TS + shadcn/ui) + TR metin dosyası @fe
- [x] 0.12 CI: ruff + mypy + pytest · npm lint + typecheck @be2
- [x] 0.13 Ekip isim eşlemesi: `@be1`/`@be2`/`@fe` → kim (CONTRIBUTING'e yazılır) @all

> **0.1 neden ilk madde:** Lisans seçimi geri alınamaz — bir kez yayımlanan kod
> o lisans altında alınmış olur. Şartname teyit edilmeden repo herkese açık
> hâle getirilemez. Ayrıntı: `LICENSE`, final analiz §22.3 ve §37 madde 0b.

---

## Faz 1 — Omurga (18-25 Eylül)

Hedef: kimlik + kiracılık + yetkilendirme çekirdeği ayakta, profil ve skill beyanı çalışır.

**Bu fazın kilit maddesi 1.2'dir.** Yetkilendirme sonradan eklenirse delikli olur.

- [x] 1.1 İlk migration: user, talent, institution, organization, membership, skill @be1
- [x] 1.2 Yetkilendirme çekirdeği: `can()` + `scoped_*()` + `audit_events` @be2
- [x] 1.3 Yetkilendirme test iskeleti + fixture'lar (aktör matrisi) @be2
- [x] 1.4 Auth: kayıt, giriş, token yenileme, çıkış @be2
- [x] 1.5 `outbox` tablosu + worker (ağ çağrısı transaction dışına) @be2
- [x] 1.6 Auth: e-posta doğrulama + şifre sıfırlama (outbox üzerinden) @be2
      > PR #5 Copilot incelemesi: 2 ertelenen bulgu — (a) `/auth/forgot-password`
      > rate limit yok, genel rate-limit altyapısı kararı gerektiriyor;
      > (b) outbox worker `process_batch` batch'i tek `FOR UPDATE` ile baştan
      > kilitliyor, SMTP süresince sıradaki satırların kilidi de tutuluyor.
      > Faz 5.2/5.6 kapsamına alınabilir.
- [x] 1.7 User + Talent profili: `GET /me`, `PATCH /talents/me` @be1
- [x] 1.8 Institution + koordinatör rolü + öğrenci bağı @be1
- [x] 1.9 Organization + üyelik + domain doğrulama (T2) @be1
- [x] 1.10 Skill taksonomisi (~150 skill) seed + arama ucu @be1
- [x] 1.11 Talent yetkinlik beyanı: skill ekle/listele/çıkar @be1
- [x] 1.12 Frontend kabuk: layout, oturum yönetimi, korumalı rota, hata sınırı @fe
- [x] 1.13 Frontend: kayıt, giriş, e-posta doğrulama, şifre sıfırlama ekranları @fe
- [x] 1.14 Frontend: talent profil + yetkinlik beyanı ekranı @fe
- [x] 1.15 Faz 1 kapanış: `pytest tests/authorization` tamamı yeşil @all

---

## Faz 2 — Ana döngü (25 Eylül - 2 Ekim)

Hedef: zincirin kendisi. Engagement açılır, çıktı yüklenir, değerlendirilir,
attestation + verified experience + skill signal üretilir.

- [x] 2.1 Engagement modeli + migration + oluşturma ucu @be1
- [x] 2.2 Durum makinesi: tek `POST /engagements/{id}/transitions` ucu @be1
- [x] 2.3 Koordinatör onayı geçişi + yetkilendirme testleri @be1
- [x] 2.4 Task + Deliverable @be1
- [x] 2.5 Dosya yükleme altyapısı: imzalı URL, magic-byte, `{uuid}.{ext}` @be2
      > Kapsam daraltıldı (final analiz §18): gerçek magic-byte/byte-level MIME
      > doğrulama ve virüs taraması bu maddede YAPILMADI — worker + outbox
      > akışına (asenkron) bırakıldı, madde 2.6 kapsamına dahil edilmeli veya
      > yeni bir madde (2.6b) açılmalı. Bu maddede yapılan: presigned URL/POST
      > üretimi, content-type header allowlist, boyut sınırı (10MB,
      > content-length-range ile gerçekten zorlanıyor), `{uuid}.{ext}` object_key.
      > Detay: `obss_project/artifacts/yet-82-83-evidence-upload-url/`.
- [x] 2.6 Evidence kaydı + indirme izni (sahiplik URL'den çıkar) @be2
      > `POST /evidence` (kayıt oluşturma, scan_status=PENDING, outbox+audit
      > tek transaction) ve `GET /evidence/{id}/download-url` (sahiplik
      > kontrollü, 300sn TTL, scan_status=CLEAN zorunlu) eklendi. `evidence`
      > tablosu migration'ı uygulandı. `deliverable_id` bu maddeden tamamen
      > çıkarıldı (deliverables/engagements tabloları henüz yok — 2.4
      > tamamlanınca ayrı migration+endpoint güncellemesiyle eklenecek).
      > Detay: `obss_project/artifacts/yet-84-85-evidence-kaydi-indirme/`.
- [x] 2.7 Değerlendirme formu şeması (yetkinlik + davranış + `NOT_OBSERVED`) @be2
      > YET-69 tamamlandı. Evaluation modeli + POST /engagements/{id}/evaluation,
      > TALENT_TO_ORG/ORG_TO_TALENT yön bazlı durum kontrolü, race-safe transaction.
      > Detay: `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/`.
- [x] 2.8 Attestation + VerifiedExperience üretimi (tek transaction) @be2
      > YET-70 tamamlandı. Attestation + VerifiedExperience modelleri, §3.11 COMPETENCE
      > ön koşulları (6 kriter, basitleştirilmiş Deliverable kontrolü), tek transaction
      > (Attestation+VerifiedExperience+SkillSignal+AuditEvent+Outbox), T8 rol kontrolü
      > (institution_id'ye göre COORDINATOR/ORG_ADMIN).
      > Detay: `obss_project/artifacts/yet-70-attestation-verified-experience-uretimi/`.
- [x] 2.9 SkillSignal türetme + `GET /talents/me/signals` @be2
      > YET-71 tamamlandı. SELF_CLAIM (YET-104) + ATTESTATION (YET-70) sonrası
      > kalan DELIVERABLE/TASK/EVALUATION kaynakları eklendi — yeni migration
      > (deliverables.skill_id, engagement_tasks.skill_id), strength hiyerarşisi
      > karara bağlandı (SELF_CLAIM<TASK<DELIVERABLE<EVALUATION/ATTESTATION).
      > Detay: `obss_project/artifacts/yet-71-skillsignal-turetme-tam-kapsam/`.
- [x] 2.10 Attestation iptali (`revoke`) — append-only istisnası @be2
      > YET-72 tamamlandı. POST /attestations/{id}/revoke — revoked_at/revoke_reason
      > (append-only'nin tek istisnası, yeni DB trigger'ı ile), tombstone SkillSignal
      > + superseded_by_id, sadece attestor iptal edebilir (engagement-scope üzerinden
      > 403/404 ayrımı), race-safe (WHERE revoked_at IS NULL).
      > Detay: `obss_project/artifacts/yet-72-attestation-revoke/`.
- [x] 2.11 Frontend: engagement listesi + detay + durum geçiş aksiyonları @fe
      > main'den (#18). NOT: bu ekran, 2.9 hâlâ [~] iken ve
      > POST /engagements/{id}/evaluation backend'de yokken yazıldı — mock
      > (localStorage) tabanlı bir evaluation submission içeriyor
      > (bkz. dosya başındaki "KAPSAM DIŞI" notları). Backend artık (YET-69/70)
      > gerçek uçla hazır — bu ekranın mock'tan gerçek apiFetch'e bağlanması
      > AYRI bir takip maddesi (2.11'in kendisi "bitti" sayılmamalı, mock→gerçek
      > geçişi doğrulanmadan).
- [ ] 2.12 Frontend: çıktı yükleme (imzalı URL akışı, ilerleme, hata) @fe
- [ ] 2.13 Frontend: değerlendirme formu (kurum tarafı) @fe
- [ ] 2.14 Faz 2 kapanış: uçtan uca duman testi (kayıt → attestation → signal) @all

---

## Faz 3 — Görünür yüz (2-9 Ekim)

Hedef: jürinin göreceği yüz. Bu fazın sonunda canlı URL + gerçekçi veri olmalı.

- [x] 3.1 Public profil ucu + `visibility` kuralları @be1
      > YET-105 tamamlandı (PR #24, commit a65e670). `app/api/public.py` +
      > `visibility_service.py`. PLAN.md'de işaretlenmemişti — kod/test main'de
      > tam, sadece belge senkronu eksikti (2026-09-27 entegrasyon denetiminde bulundu).
- [x] 3.2 Public doğrulama linki `GET /public/v/{token}` @be1
      > YET-106 tamamlandı (PR #25, commit f2279a0). `verified_experiences.public_token`
      > migration'ı dahil. PLAN.md'de işaretlenmemişti (2026-09-27 entegrasyon denetiminde bulundu).
- [x] 3.3 Koordinatör dashboard ucu (durum takibi + bekleyen değerlendirme) @be1
      > YET-107 tamamlandı (commit 35a494c). `GET /institutions/{id}/dashboard`.
      > PLAN.md'de işaretlenmemişti (2026-09-27 entegrasyon denetiminde bulundu).
- [x] 3.4 Toplu hatırlatma ucu (`POST /institutions/{id}/reminders`) @be2
      > YET-108/130/131/132 tamamlandı. `services/reminder.py` +
      > `POST /institutions/{id}/reminders`; `scoped_institutions()`/
      > `scoped_engagements()` olduğu gibi tüketildi (yeni yetkilendirme dalı
      > yok), `log_audit_event()` (PII-guard'lı) kullanıldı. Institution-level
      > throttle (429), engagement-level dedup ve `engagement_ids[]` üst
      > sınırı hiçbir kaynakta tanımlı olmadığı için bilinçli olarak
      > UYGULANMADI — keyfi hardcode edilmedi, açık soru olarak bırakıldı
      > (Faz 5.2/5.6'ya aday). Detay: `obss_project/artifacts/yet-108-toplu-hatirlatma-ucu/`.
- [x] 3.5 Kurum dashboard ucu (bekleyen değerlendirmeler, üyeler) @be2
      > YET-109/133/134/135 tamamlandı. **Kapsam notu:** bu uç ("bekleyen
      > değerlendirmeler" kısmı) YET-107/PLAN 3.3'te zaten yapılmıştı — iki
      > ayrı Jira görevi yanlışlıkla aynı backend ucuna işaret ediyordu
      > (YET-109'a yorum olarak da düşüldü). Gerçek kalan iş: mevcut
      > `GET /institutions/{id}/dashboard` ucuna/servisine `members` (üye)
      > listesi eklendi — `InstitutionMember`+`User` join, `institution_id`
      > ve `User.status == "ACTIVE"` filtreleriyle (çapraz-kurum sızıntısı ve
      > askıya alınmış kullanıcı sızıntısı engellendi). Sayfalama/üye
      > yönetimi/öğrenci listesi bilinçli olarak kapsam dışı bırakıldı.
      > Detay: `obss_project/artifacts/kurum-dashboard-uyeler/`.
- [x] 3.6 Admin: kurum doğrulama kuyruğu + skill yönetimi @be2
      > YET-110/136/137/138/139 tamamlandı. Ön koşul olarak `users.is_platform_admin`
      > eklendi (DOMAIN.md'de tanımlıydı, migration'a hiç işlenmemişti — DATABASE.md
      > senkronu da düzeltildi). `list_verification_queue()`: T2 + `legal_id` dolu
      > kurumlar (T3 başvurusu sayılır — şemada ayrı başvuru alanı yok).
      > `set_verification_level()` approve/reject'i tek fonksiyonla kapsıyor.
      > Skill yönetimi bilinçli olarak sadece admin CRUD (create/update/deprecate/
      > merge) — kullanıcı öneri akışı (docs/API.md §2.10 açık sorusu) kapsam dışı
      > bırakıldı. Tüm `/admin/*` uçlarında yetkisiz erişim 404 (403 değil,
      > organizations.py'deki ORG:ADMIN deseniyle aynı). İlk admin self-servis
      > değil — `scripts/seed.py`'ye eklendi. `tests/authorization/test_admin_authz.py`
      > (15 test) + `pytest tests/authorization -q` tam paket (196 geçti).
      > Ayrı bulgu (bu maddenin kapsamı dışı): `require_email_verified()` hiçbir
      > router'da kullanılmıyor — e-posta doğrulama yazma kısıtı hiçbir uçta
      > uygulanmıyor, ayrı bir madde olarak açılmalı.
- [x] 3.7 Frontend: profil sayfası — kanıt dökümü (signal + verified experience) @fe
      > `app/profil/evidence-section.tsx` + testi mevcut. Jira YET-111 Tamamlandı.
- [x] 3.8 Frontend: public profil `/p/[slug]` + doğrulama `/v/[token]` @fe
      > PR #27 birleştirildi; `app/p/[slug]`, `app/v/[token]` + testleri mevcut.
- [x] 3.9 Frontend: koordinatör dashboard @fe
      > commit 2818115; `app/kurum/[id]/panel` + `lib/api/institutions.ts` + testleri.
      > `panel/page.test.tsx` "404 gösterilir (403 değil)" testi kırmızıydı;
      > aralıklı değil, regex kaynaklıydı — YET-217'de (7bdfdc8) düzeltildi.
- [x] 3.10 Frontend: kurum dashboard + admin ekranları @fe
      > PR #31 birleştirildi; `app/admin/dogrulama-kuyrugu`, `app/admin/skiller`,
      > `app/kurum/[id]/panel` + testleri mevcut.
- [x] 3.11 Seed verisi: 20 öğrenci, 5 kurum, 15 tamamlanmış engagement @be1
      > commit ad183f6 tamamlandı. `backend/scripts/seed.py` — 20 öğrenci
      > (ogrenci1-20@seed.local), 5 kurum + 5 organizasyon, 15 tam VERIFIED
      > engagement (Attestation/VerifiedExperience zinciriyle), idempotent.
      > PLAN.md'de işaretlenmemişti (2026-09-27 entegrasyon denetiminde bulundu).
- [x] 3.12 Güvenlik geçişi: BOLA taraması, 404-yerine-403 doğrulaması @be2
      > YET-116/154/155 tamamlandı (PR #32). Tüm `api/*.py` ve `services/*.py`
      > `scoped_*()`/`can()` kullanımı için tarandı — `institutions.py`'de router
      > içinde çıplak `select(Model)` vardı, merkezi katmana taşındı
      > (`get_institution()`, `institution_id`-scoped `approve_institution_link()`).
      > 404-vs-403 ayrımı final-analiz §21.2 matrisine göre doğrulandı, tutarlı.
      > Ek bulgu (kapsam genişletildi): `require_csrf` sadece `auth.py`/`evidence.py`'de
      > uygulanıyordu; `institutions`/`organizations`/`engagements`/`admin`/`me`/
      > `talent_skills`'teki 23 yazma ucuna eklendi. Yetkilendirme test paketi
      > birleştirildi (`tests/` kökündeki 10 dosya `tests/authorization/`'a
      > taşındı — `pytest tests/authorization -q` artık gerçekten tam paket).
      > Outbox PII-guard + birkaç skill testindeki dev-DB seed verisiyle (gerçek
      > skill taksonomisi) çakışan test fixture'ları düzeltildi (kod hatası
      > değildi, test izolasyon hatasıydı).
      > Ayrı bulgu (bu maddenin kapsamı dışı): `tests/test_seed.py`, seed
      > fonksiyonlarını çağırırken kendi ayrı DB session'ını açıyor ve test
      > rollback izolasyonunu bypass ediyor — yerel dev DB'ye kalıcı satır
      > bırakıyor, ayrı bir madde olarak açılmalı.
- [x] 3.13 Erişilebilirlik geçişi: klavye, focus, kontrast, `aria-live` @fe
      > PR #34 birleştirildi (commit fac4449).
- [ ] 3.14 Deploy: VPS, HTTPS, canlı URL, yedekleme, log @be2
- [ ] 3.15 Açık kaynak paketi: kurulum talimatı sıfırdan doğrulanır, sır taraması @all
  > YET-119 `verify` adımında (2026-09-28) `security-scan` ile bulundu: backend
  > `pyjwt` 2.10.1 (birden fazla advisory, PYSEC-2026-120/175/176/177/178/179 —
  > 2.12.0/2.13.0'a yükselt) ve `starlette` 0.41.3 (PYSEC-2026-161/248/249/
  > 1941/1942/2280/2281 — 1.3.1'e yükselt); frontend `postcss` (high severity
  > XSS advisory). `pytest` 8.3.4 için de bir advisory var (9.0.3, dev-only,
  > düşük öncelik). Bağımlılık sürüm yükseltmesi CLAUDE.md gereği açık onay
  > istediği ve bu görevin kapsamı dışında kaldığı için ayrı madde olarak
  > açıldı (bkz. 3.15b). Not: 3.33 de "bağımlılık yükseltmeleri" içeriyor —
  > 3.15b bu spesifik CVE'lerin kaynağı, 3.33 kapsadığında bu madde kapatılabilir.
- [ ] 3.15b Bağımlılık güvenlik yükseltmesi: `pyjwt`→2.13.0, `starlette`→1.3.1,
  `postcss` (frontend, high severity), `pytest`→9.0.3 (dev-only, düşük
  öncelik) — kaynak: YET-119 verify_report.md @be2
  > Backend kısmı YET-219 ile yapıldı (commit c748101): `pyjwt` 2.15.1,
  > `fastapi` 0.141.1 (`starlette` 1.6.0 transitif), `pytest` 9.0.3.
  > Açık kalan: yalnız frontend `postcss`.

**Aşağıdaki 5 madde 2026-09-27 frontend↔backend entegrasyon denetiminde bulundu
— önceki maddelerin "kapsam dışı" notlarında iz bırakılmış ama hiçbiri resmi
PLAN maddesi olarak açılmamıştı. Detay: `HATA.md`.**

- [ ] 3.17 Evidence upload akışının mock'tan gerçek backend'e bağlanması @fe
      > `frontend/lib/api/evidence.ts`: `USE_MOCK_UPLOAD_URL`/`USE_MOCK_STORAGE_UPLOAD`
      > hâlâ `true`, `recordEvidence()` her koşulda localStorage. Backend'de
      > `POST /evidence/upload-url` VE `POST /evidence` ikisi de tamamlanmış (2.5/2.6) —
      > dosya başındaki "Adım 3 backend'de HİÇ YOK" yorumu artık YANLIŞ/güncel değil.
      > Aktif kullanılan bir bileşende (`calismalar/[id]/evidence-upload-form.tsx`)
      > kullanıcı dosya yüklediğini sanıp hiçbir şey backend'e gitmiyor. bkz. HATA.md §1.
- [ ] 3.18 Değerlendirme formunun mock'tan gerçek backend'e bağlanması @fe
      > `frontend/lib/api/evaluation.ts`: `submitEvaluation()` tamamen localStorage,
      > dosya başı yorumu "backend'de HİÇ YOK" diyor ama `POST /engagements/{id}/evaluation`
      > 2.7'de (YET-69) tamamlandı. Ayrıca mock 422/409 hata kodu ayrımı yapıyor,
      > gerçek backend ikisini de 409 CONFLICT döndürüyor — bağlarken hata kodu
      > eşlemesi düzeltilmeli. `private_note` localStorage'a düz metin yazılıyor,
      > bu da ayrıca bkz. 3.19. bkz. HATA.md §2.
- [ ] 3.19 localStorage'a PII/hassas veri yazılmaması + auth kuralına uyum @fe
      > `.claude/rules/frontend.md`: "Auth: httpOnly cookie — `localStorage` kullanılmaz."
      > `evidence.ts` ve `evaluation.ts` (private_note dahil) kalıcı state için
      > localStorage kullanıyor — 3.17/3.18 ile birlikte çözülecek, ayrı doğrulama
      > gerektirir (localStorage temizliği + XSS maruziyeti kontrolü). bkz. HATA.md §2, §5.
- [ ] 3.20 `.env.example` NEXT_PUBLIC_API_BASE_URL düzeltmesi @be1
      > `.env.example`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` yazıyor
      > ama backend'de `/api/v1` prefix'i YOK (router'lar doğrudan `/auth`, `/engagements`
      > vb.) — `frontend/lib/api/client.ts` default'u da zaten prefix'siz
      > (`http://localhost:8000`) ve doğru. `.env.example`'dan kopyalayan biri kırık
      > bir base URL alır. Açık kaynak paketi (3.15) öncesi düzeltilmeli. bkz. HATA.md §3.
- [ ] 3.21 `require_email_verified()` hiçbir router'da uygulanmıyor @be2
      > 3.12'nin notu: e-posta doğrulama yazma kısıtı hiçbir uçta zorlanmıyor.
      > Güvenlik/kapsam kararı gerektirir (hangi uçlarda zorunlu olacağı netleşmeli).
- [ ] 3.22 `tests/test_seed.py` rollback izolasyonunu bypass ediyor @be1
      > 3.12'nin notu: seed fonksiyonlarını çağırırken ayrı DB session açıyor,
      > yerel dev DB'ye kalıcı satır bırakıyor. Test izolasyon hatası, veri hatası değil.
- [ ] 3.23 Faz 2/3 backend↔frontend GET/mock eşleşmesi son doğrulama @all
      > 3.17-3.19 kapandıktan sonra: `grep -rn "USE_MOCK\|localStorage\." frontend/lib/api/`
      > sıfır sonuç dönmeli (test dosyaları hariç). Bu madde kapanmadan 2.14
      > (uçtan uca duman testi) güvenilir sayılmaz.
- [x] 3.24 Giriş kilitleme sayacı kalıcı olsun (HATA_DUZELTME_PROMPT A-01, GUV-01, L-03) @be2
- [ ] 3.25 Logout refresh token ailesini iptal etsin (HATA_DUZELTME_PROMPT A-02, GUV-06, L-04) @be2
- [ ] 3.26 MinIO bucket, healthcheck, depolama hataları, .env.example (HATA_DUZELTME_PROMPT A-03, OPS-03) @be2
- [ ] 3.27 Outbox worker: döngü, tıkanma, e-posta linkleri (HATA_DUZELTME_PROMPT A-04, OPS-01, OPS-02) @be2
- [x] 3.28 Seed demo düzeltmesi: COORDINATOR, T2 organizasyon, doğrulanmış e-posta (HATA_DUZELTME_PROMPT A-05, AUTHZ-02, IS-02) @be2
      > Ek bulgu (2026-10-07, frontend incelemesi): seed adları İngilizce ve yer
      > tutucu ("Organization 1", "Institution 1", "Student 1"). Jüriye gösterilen
      > her ekranda (panel başlıkları, `/v/[token]` sertifikası, `/p/[slug]`)
      > görünüyor. Gerçekçi Türkçe ad, kurum/kuruluş adı, bölüm ve başlık verilmeli;
      > en az bir `VERIFIED` çalışma + `public_slug`'lı profil demo için hazır olmalı
      > (`planfrontend.md` FE-02). Seed idempotent olduğu için mevcut DB'de adlar
      > kendiliğinden değişmez — güncelleme yolu ayrıca düşünülmeli.
      > Ek bulgu 2: `GET /me` talent profili olmayan kullanıcıda 404 dönüyor
      > (`services/talent.py` `get_me_context` ValueError → `api/me.py` 404). Seed'in
      > platform admini (`seed_admin`) talent profilsiz → admin girişte tüm uygulama
      > hata ekranı. Testler `platform_admin_talent` fixture'ıyla admine profil verdiği
      > için yakalamamış. Düzeltme: `talent_profile` opsiyonel (`null`) döner; frontend
      > tipi zaten `null` kabul ediyor. **Düzeltildi (2026-10-07)** — profilsiz admin
      > testi `tests/test_talent.py` içinde.
      > **Tamamlandı (2026-10-07):** seed adları Türkçe ve kurgusal (öğrenci, kurum,
      > kuruluş, çalışma başlıkları, değerlendirme yorumları); 20 öğrencinin hepsi
      > kuruma bağlı ve `PUBLIC` + `public_slug`'lı (ör. `/p/ayse-yilmaz`). COORDINATOR
      > ve doğrulanmış e-posta önceden çözülmüştü (YET-190, YET-196). Mevcut DB için
      > güncelleme yolu: `python -m scripts.reset_demo --yes --reseed`.
      > Kapsam dışı kalan: IS-02'nin API tarafı (engagement tarihleri hâlâ yalnız seed'de set ediliyor).
- [ ] 3.29 Kanıt backend'i: tarama, liste ucu, kayıt sertleştirme (HATA_DUZELTME_PROMPT A-06, IS-07, GUV-12) @be2
- [ ] 3.30 Çoklu rol: kapsam sorguları `kind`'dan bağımsız (HATA_DUZELTME_PROMPT A-08, AUTHZ-01, GUV-02, AUTHZ-02, L-08) @be2
- [ ] 3.31 Davet uçları: 500, numaralandırma, rol doğrulama (HATA_DUZELTME_PROMPT A-09, GUV-07, GUV-02, L-01) @be2
- [ ] 3.32 Kayıt zamanlama + kimlik uçlarına hız sınırı (HATA_DUZELTME_PROMPT A-10, GUV-10, GUV-11) @be2
- [ ] 3.33 Bağımlılık yükseltmeleri + secrets baseline (HATA_DUZELTME_PROMPT A-11, DEP-01, L-16) @be2
- [ ] 3.34 DB kısıtları: append-only trigger, claimed_level, timestamptz (HATA_DUZELTME_PROMPT A-12, VER-01, VER-02, VER-03) @be2
- [ ] 3.35 Backend test izolasyonu + fixture rollback semantiği (HATA_DUZELTME_PROMPT A-13, TEST-01, TEST-02) @be2
- [ ] 3.36 Hata yanıt biçimi, 307'ler, prod ayarları (HATA_DUZELTME_PROMPT A-14, OPS-04, ENT-06, L-07, L-11, L-12, L-14) @be2
- [ ] 3.37 Alan adı gaspı, DNS transaction, hatırlatma sınırları (HATA_DUZELTME_PROMPT A-15, GUV-09, AUTHZ-04, GUV-13) @be2
- [ ] 3.38 Refresh sonrası CSRF başlığı yeniden okunsun (HATA_DUZELTME_PROMPT B-01, ENT-03, L-13) @fe
- [ ] 3.39 `/me` rol bilgisi, admin linkleri, durum etiketleri, 307 (HATA_DUZELTME_PROMPT B-02, ENT-04, ENT-05, IS-04, ENT-06) @fe
- [ ] 3.40 Engagement tarihleri (oluşturma + PATCH) (HATA_DUZELTME_PROMPT B-03, IS-02) @be1
- [ ] 3.41 Public token, VE görünürlüğü, geri çekme okuma filtresi (HATA_DUZELTME_PROMPT B-04, IS-01, GUV-05, GUV-03, L-05) @be1
- [ ] 3.42 Skill sinyal ve tanıklık kuralları (HATA_DUZELTME_PROMPT B-05, GUV-04, IS-05, IS-06) @be1
- [ ] 3.43 Durum makinesi dokümana uysun (HATA_DUZELTME_PROMPT B-06, AUTHZ-03, IS-03, GUV-08) @be1
- [ ] 3.44 Değerlendirme formunun mock'tan gerçek backend'e bağlanması (HATA_DUZELTME_PROMPT B-07, ENT-02) @fe
- [ ] 3.45 Engagement oluşturma + teslim ekranları (HATA_DUZELTME_PROMPT B-08, ENT-01) @fe
- [ ] 3.46 Kanıt yükleme gerçek backend'e (HATA_DUZELTME_PROMPT B-09, ENT-02) @fe
- [ ] 3.47 Tanıklık, geri çekme, deneyim paylaşımı ekranları (HATA_DUZELTME_PROMPT B-10, ENT-01, IS-01) @fe
- [ ] 3.48 Frontend testleri + CI'da vitest (HATA_DUZELTME_PROMPT B-11, TEST-01) @fe
- [ ] 3.49 Kurum bağlanma talepleri + admin kuyruğu reddi (HATA_DUZELTME_PROMPT B-12, IS-10, IS-11) @fe
- [ ] 3.50 Profil düzeltmeleri, skill yönetimi, frontend bağımlılığı (HATA_DUZELTME_PROMPT B-13, IS-09, DEP-02, L-06, L-10) @fe
- [x] 3.52 Kayıt ekranına hesap türü seçimi: `register` isteğine opsiyonel
      `account_kind` (TALENT/ORGANIZATION/INSTITUTION) + `entity_name` eklendi
      — docs/API.md §2.1 revize edildi, §"Kayıta hesap türü" (kullanıcı
      kayda derken kuruluş/kurum adı girip kayıt anında o kuruluşun/kurumun
      ADMIN'i olabiliyor; yeni bir güven sınırı açmıyor çünkü
      POST /organizations ve POST /institutions zaten davetsiz serbestti).
      Backend + frontend (segment seçici + koşullu kuruluş/kurum adı alanı)
      ve yetkilendirme testleri tamamlandı. @be2 @fe
- [x] 3.53 /calismalar'da "Yeni Çalışma" giriş noktası yok — öğrenci kendi
      başına kuruluş seçip çalışma başlatamıyor, yalnız kuruluşun gönderdiği
      özel linkle (?organization_id=...) gidilebiliyor. Karar: öğrenci tüm
      kuruluşlardan serbestçe arayıp seçebilsin — GET /organizations
      (liste/arama, authenticated) ucu + /calismalar'da "Yeni Çalışma"
      butonu + /calismalar/kurulus-sec seçici ekran eklendi. @be1 @fe
- [x] 3.51 Outbox worker'a eksik bildirim handler'ları eklendi: `attestation.created`
      (öğrenciye tanıklık/doğrulama bildirimi) ve `engagement.pending_approval`
      (koordinatöre onay bekleyen çalışma bildirimi) — DEFAULT_HANDLERS'a
      kaydedildi, canlı doğrulandı (worker yeniden başlatılınca gerçek 36
      satırlık birikmiş kuyruk hatasız boşaldı). Kalan: outbox worker'ın
      Docker/systemd gibi kalıcı bir servis olarak tanımlanması — deploy
      kapsamına (3.14) bırakıldı, launch.json'da "worker" config zaten var.
      bkz. 3.27. @be2
- [x] 3.54 AI fraud-flag — faz 1 (tanıklık metni): CLAUDE.md'nin MVP'de "AI
      yasak" kuralı final-analiz §11.4.6 gerekçesiyle bilinçli olarak
      daraltıldı — AI hiçbir zaman karar vermez, yalnız `attestation.statement`
      metnini OpenRouter'a (outbox worker, açık transaction dışında) gönderip
      şüpheli paternleri `fraud_flags` tablosuna işaretler; nihai karar
      (`CONFIRMED`/`DISMISSED`) `GET`/`POST /admin/fraud-queue` ile admin'e
      aittir. `attestation.statement` önceden API'den hiç girilemiyordu
      (hardcoded `None`) — bu iş onu gerçek bir request alanı yaptı. Faz 2
      (evidence dosya içeriği — PDF/OCR metin çıkarımı gerektirir) ayrı onay
      bekliyor. @be2
- [x] 3.55 AI sertifika çıkarımı — faz 2 (Udemy/Coursera, `evidence.kind=CERTIFICATE`):
      öğrencinin açık rızasıyla (upload anında otomatik DEĞİL, KVKK) tetiklenir.
      Literal Tesseract/zbar yerine (bu makinede sistem binary'si yok, kurulumu
      kırılgan) OpenRouter görsel modeli (metin/isim/kimlik no çıkarımı,
      final-analiz §11.2'nin sandıkladığı desen) + OpenCV QR dedektörü
      (deterministik, pip-only) kombinasyonu kullanıldı. AI hiçbir zaman
      "doğrulandı" kararı vermez (final-analiz §11.4.2/§39) — isim eşleşmesi
      kod tarafında düz string karşılaştırmasıyla hesaplanır, nihai
      CONFIRMED/REJECTED kararı `POST /certificate-checks/{id}/resolve` ile
      engagement'ın koordinatörüne/supervisor'una aittir. `scoped_evidence()`'ın
      "sadece sahibi görür" kuralına (final-analiz §21.2) kasıtlı ve dar bir
      istisna açıldı — yalnız CertificateCheck özeti, ham dosya değil. Canlı
      doğrulandı: gerçek sertifika görseli + gerçek OpenRouter çağrısıyla
      provider/kimlik no/isim doğru çıkarıldı. Yeni bağımlılık:
      opencv-python-headless, pymupdf (ikisi de pip-only, sistem binary yok). @be2
- [x] 3.56 Şüpheli kuruluş/kurum ve danışıklı tanıklık işaretleme: 3.54'ün
      `fraud_flags` kuyruğu `ORGANIZATION` ve `INSTITUTION` öznelerine genişletildi.
      İşaretlerin çoğu DETERMİNİSTİK kuraldır (`app/services/fraud_signals.py`,
      AI yok, `OPENROUTER_API_KEY` olmadan çalışır): kendi kendine tanıklık, tanık
      ile öğrencinin aynı e-posta alan adı, kopya tanıklık metni, dakikalar içinde
      doğrulama; doğrulanmamış kuruluşta yoğun tanıklık, yeni kuruluşta ani artış,
      tüm tanıklıkların tek öğrenciye gitmesi; onaylayan koordinatörün kuruluş
      üyesi olması, toplu ve hızlı onay. Tek AI çağrısı kuruluş kimliği
      (ad/alan adı tutarlılığı) kontrolüdür ve yalnız kuruluş düzeyinde veri
      gönderir (kişi adı/e-posta yok). Hiçbir işaret karar değildir — nihai
      `CONFIRMED`/`DISMISSED` kararı admin'e aittir (final-analiz §11.4.6). @be2 @fe
- [x] 3.57 Kuruluş kaydında kurumsal kimlik: `POST /auth/register`,
      `account_kind=ORGANIZATION` iken ücretsiz e-posta adreslerini sunucuda
      reddeder (doğrulama e-postası her zaman kurumsal adrese gider) ve 16 haneli
      MERSİS numarasını (`legal_id`) kuruluşa yazar. Kayıt formuna MERSİS alanı ve
      sicil/faaliyet belgesi adımı eklendi. **Belge adımı MOCK'tur** (backend ucu
      yok): belge sunucuya gitmez, karekod okunmaz, sonuç yalnız formdaki beyana
      bağlıdır ve hiçbir doğrulama seviyesini etkilemez — bkz.
      `obss_project/artifacts/kurulus-kayit-dogrulama/ENTEGRASYON_NOTU.md`. @fe @be2
- [ ] 3.16 Kod dondurma — Faz 4'e yeni özellik girmez @all

---

## Faz 4 — Sunum (9-11 Ekim, İstanbul)

Yeni özellik yok. Yalnız prova ve kırık olanın düzeltilmesi.

- [ ] 4.1 Demo provası: uçtan uca senaryo, jüri telefonundan public link @all
- [ ] 4.2 Sunum içeriği + ekran akışı @all
- [ ] 4.3 Son hata düzeltme (yalnız kırık olan) @all
- [ ] 4.4 Sunum @all

---

## Vakit kalırsa (Faz 3 içinde, zorunlu değil)

Yapılmazsa sunumda yol haritası olarak anlatılır.

- [x] R.1 Basit aday filtreleme ekranı (skill + kurum filtresi — matching motoru değil)
      > "Keşfet" olarak yapıldı: `GET /discover/talents` + `GET /discover/organizations`
      > ve `/kesfet` sayfası. Yalnız `PUBLIC` profiller listelenir, oturum açmış herkes
      > görür; puan/öneri yok. Arayüzde yetkinlik, bölüm ve şehir filtresi var; kurum
      > (üniversite) filtresi API'de mevcut, arayüzde yok. Tasarım: docs/kesfet-tasarim.md.
- [ ] R.2 Excel/PDF rapor dışa aktarma (akreditasyon argümanı)
- [ ] R.3 İtiraz (`DISPUTED`) akışı

---

## Faz 5+ — Hackathon sonrası (kabul alınırsa)

Bu bölüm 11 Ekim'de **başlar.** Sıra final analiz §35.4 (Plan B) üzerinedir:
hackathon çıktısını pilot uygulanabilir ürüne taşır. Numaralar Faz 5'ten devam
eder; önceki fazlar geçmiş kaydı olarak silinmeden durur.

### Faz 5 — Sertleştirme
- [ ] 5.1 Gerçek kullanıcı görüşmeleri: 5 koordinatör + 5 kurum + 10 öğrenci
- [ ] 5.2 BOLA test matrisi tamamlama (her uç × her aktör)
- [ ] 5.3 Dosya güvenliği derinleştirme (ClamAV, kullanıcı içeriği ayrı domain)
- [ ] 5.4 Audit log sorgulanabilirliği + saklama politikası
- [ ] 5.5 Hata izleme + uptime izleme
- [ ] 5.6 Yük testi ve N+1 sorgu temizliği

### Faz 6 — Kurum derinliği
- [ ] 6.1 Koordinatör dashboard derinleştirme (kohort, dönem, filtre)
- [ ] 6.2 Raporlama / dışa aktarma (akreditasyon formatı)
- [ ] 6.3 İtiraz akışı tam (`DISPUTED` → çözüm → kayıt)
- [ ] 6.4 Kurum doğrulama T3 (belge tabanlı)
- [ ] 6.5 Kurum için çıktı yorumlama

### Faz 7 — Pilot hazırlığı
- [ ] 7.1 Pilot kurulumu (tek üniversite, tek bölüm)
- [ ] 7.2 KVKK dokümantasyonu + aydınlatma metinleri + veri haritası
- [ ] 7.3 Yedekleme ve geri yükleme tatbikatı
- [ ] 7.4 Kullanıcı eğitim materyali
- [ ] 7.5 Basit yetenek arama (kurum, kendi üniversitesi içinde)

### Faz 8 — Pilot yürütme
- [ ] 8.1 Pilot yürütme + haftalık geri bildirim
- [ ] 8.2 Geri bildirimle düzeltme
- [ ] 8.3 Deterministik eşleştirme katmanı (AI değil — final analiz §9.2)
- [ ] 8.4 Pilot sonuç raporu

> ❓ AÇIK SORU: Faz 5-8 "kabul alınırsa 4 ay" varsayımına dayanıyor. Sözleşme
> koşulları (süre, ekip büyüklüğü, bütçe) belli olduğunda bu bölüm yeniden
> bölümlenir. Kabul gelmezse Faz 5 açık kaynak bakım moduna küçülür.

---

## Plan bakım kuralları

1. **Madde eklemek serbest, madde silmek değil.** İptal edilen madde `[-]` ile
   kalır — jüri ve katkıcı için karar geçmişidir.
2. Yeni iş çıkarsa ilgili fazın sonuna eklenir, numara devam eder (`2.15`).
   Numara yeniden kullanılmaz; geçmiş commit mesajları ona atıf yapar.
3. **Her madde tek satır.** Detay `docs/` içine yazılır, buraya değil.
   Plan uzarsa her ilerleme kontrolü pahalılaşır.
4. Bir madde başkasının maddesini bekliyorsa, bekleyen taraf sözleşmeye göre
   mock ile ilerler — bloke beklemez.
5. Faz kapanış maddesi (`1.15`, `2.14`, `3.16`) atlanmaz: bir sonraki faz kırık
   omurga üzerine kurulmaz.
6. Bir madde `[x]` olurken ilgili commit `PLAN <numara>` referansı taşır.
