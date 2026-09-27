# HATA.md — Frontend↔Backend Entegrasyon Denetimi

**Tarih:** 2026-09-27
**Kapsam:** "Frontend ile backend'i tam olarak bağlıyor muyuz, çalıştırıyor muyuz?"
sorusuna cevap aramak için yapılan statik kod denetimi + risk analizi.
**Yöntem sınırı:** Docker Desktop bu makinede çalışmıyordu (`docker ps` →
`failed to connect to the docker API`), bu yüzden PostgreSQL/MinIO/backend/frontend
canlı ayağa kaldırılıp gerçek bir HTTP isteğiyle uçtan uca doğrulanamadı. Aşağıdaki
bulgular kod okuma + backend route envanteri + frontend istemci taraması ile
üretildi. **Canlı doğrulama yapılana kadar "kesin çalışıyor" denemez.**

**Önemli metodolojik not:** İlk tur analiz yanlışlıkla `feature/plan-2.7-degerlendirme-formu-semasi`
dalında yapıldı — bu dal `main`'in 29 commit gerisindeydi ve `admin.py`, `public.py`,
`verified_experiences.py` gibi dosyalar o dalda hiç yoktu. Bu rapor `main` dalına
geçildikten sonra tekrarlanan, doğru zeminde yapılan analizi yansıtıyor.

---

## Özet tablo

| # | Bulgu | Ciddiyet | Etki |
|---|---|---|---|
| 1 | Evidence upload akışı (3 adımın 3'ü de) mock, backend hazır | **KRİTİK** | Demo/duman testi kırılır |
| 2 | Değerlendirme formu tamamen mock, backend hazır | **KRİTİK** | Demo/duman testi kırılır |
| 3 | `.env.example`'daki `NEXT_PUBLIC_API_BASE_URL` yanlış (`/api/v1` yok) | **KRİTİK** | Sıfırdan kurulum kırık başlar |
| 4 | `private_note` ve evidence kayıtları localStorage'da düz metin | ORTA | Kural ihlali + XSS maruziyeti |
| 5 | Mock/gerçek hata kodu uyuşmazlığı (422 vs 409) | ORTA | Bağlarken sessiz davranış farkı |
| 6 | PLAN.md, tamamlanmış işleri `[ ]` gösteriyordu (3.1/3.2/3.3/3.11) | ORTA | Ekip yanlış "kalan iş" sanır (bu oturumun tetikleyicisi) |
| 7 | Docker Desktop çalışmıyor — canlı doğrulama yapılamadı | ORTA | Bu raporun kendisi doğrulanmamış varsayımlara dayanıyor |
| 8 | `require_email_verified()` hiç kullanılmıyor | DÜŞÜK-ORTA | E-posta doğrulama kısıtı fiilen yok |
| 9 | `tests/test_seed.py` rollback izolasyonunu bypass ediyor | DÜŞÜK | Yerel dev DB'de kalıcı test verisi birikir |
| 10 | `engagements.ts`/GET akışları gerçek backend'e bağlı (doğrulandı, sorun yok) | — | Referans: bu doğru çalışıyor |

---

## 1. Evidence upload akışı — mock'ta kalmış, backend hazır (KRİTİK)

**Dosya:** `frontend/lib/api/evidence.ts`

Üç adımlı akışın hepsi mock:

- **Adım 1** (`requestUploadUrl`, satır 96-118): `USE_MOCK_UPLOAD_URL = true`.
  Dosya başı yorumu bunun backend hazır olduğunu ama "bu oturumda backend+MinIO
  çalışmadığı için" mock'landığını söylüyor — backend'de `POST /evidence/upload-url`
  gerçekten var (`backend/app/api/evidence.py:43`).
- **Adım 2** (`uploadFileToStorage`, satır 123-148): `USE_MOCK_STORAGE_UPLOAD = true`,
  aynı gerekçeyle.
- **Adım 3** (`recordEvidence`, satır 151-229): **HER KOŞULDA** mock, hiçbir bayrağa
  bağlı değil. Dosya başı yorumu (satır 16-18): *"Adım 3 (POST /evidence, kanıt kaydı)
  backend'de HİÇ YOK (Evidence modeli/tablosu PLAN 2.6'da henüz oluşturulmadı)"*.
  **Bu artık yanlış**: `POST /evidence` backend'de gerçekten var
  (`backend/app/api/evidence.py:163`, PLAN 2.6 main'de tamamlanmış). Yorum, backend
  ilerlerken güncellenmemiş.

**Neden kritik:** `evidence-upload-form.tsx` gerçek bir sayfada
(`frontend/app/calismalar/[id]/page.tsx` üzerinden) aktif olarak kullanılıyor.
Kullanıcı dosya seçip "yükle" dediğinde arayüz başarı gösteriyor ama **hiçbir byte
backend'e/MinIO'ya gitmiyor** — kayıt sadece tarayıcı localStorage'ında. Demo
sırasında veya jüri kendi dosyasını yüklemeye çalışırsa fark edilmeyen bir sahte
akış çalışır.

**Düzeltme:** `USE_MOCK_UPLOAD_URL` ve `USE_MOCK_STORAGE_UPLOAD`'ı `false` yap,
`recordEvidence()`'ı gerçek `apiFetch("/evidence", {...})` çağrısına çevir, dosya
başı yorumunu güncel duruma göre yeniden yaz. Backend+MinIO ayakta olmadan bu
değişikliğin doğrulanması mümkün değil (bkz. bulgu 7). PLAN.md 3.17.

---

## 2. Değerlendirme formu — tamamen mock, backend hazır (KRİTİK)

**Dosya:** `frontend/lib/api/evaluation.ts`

`submitEvaluation()` (satır 77-117) tamamen `localStorage` tabanlı. Dosya başı
yorumu (satır 5-8): *"BACKEND DURUMU: bu uç backend'de HİÇ YOK (PLAN 2.7
'Değerlendirme formu şeması' henüz yazılmadı)"*. **Bu da artık yanlış**:
`POST /engagements/{engagement_id}/evaluation` backend'de tamamlanmış
(`backend/app/api/engagements.py:835`, PLAN 2.7 / YET-69, main'de merge edilmiş).

**Ek sözleşme uyuşmazlığı (bağlanırken düzeltilmesi gereken):**
- Mock, "durum PENDING_EVALUATION değilse" → **422 INVALID_STATUS**, "zaten
  gönderilmiş" → **409 ALREADY_SUBMITTED** olmak üzere iki ayrı HTTP kodu üretiyor.
- Backend'in kendi docstring'i (`engagements.py:598`) açıkça şunu söylüyor:
  *"409 CONFLICT: Engagement not in PENDING_EVALUATION, **or** duplicate evaluation"*
  — yani backend her iki durumda da **409** döndürüyor, 422 değil.
- Frontend hata işleme kodu (`ApiError` kod eşlemesi, form/sayfa seviyesinde) mock'un
  422/409 ayrımına göre yazılmışsa, gerçek backend'e bağlanınca "durum uygun değil"
  hatası "zaten gönderilmiş" gibi yanlış yorumlanabilir veya işlenmeyen bir kod
  (422) hiç görünmeyebilir.

**Neden kritik:** `calismalar/[id]/degerlendirme/page.tsx` üzerinden aktif kullanılan
bir form. Kurum tarafı değerlendirme gönderdiğini sanır, hiçbir attestation/skill
signal tetiklenmez çünkü backend hiç haberdar olmaz — **"beyan → kanıt → tanıklık →
doğrulanmış deneyim" zincirinin tam ortası sahte**.

**Düzeltme:** `getEngagement()` üzerinden durum kontrolünü koru (backend zaten aynı
kontrolü tekrar yapacak, savunma amaçlı UX için sorun değil), ama gerçek gönderim
için `apiFetch("/engagements/{id}/evaluation", {method:"POST", body:{direction, items, private_note}})`
kullan; 422 dalını kaldırıp backend'in gerçek 409 davranışına göre tek bir hata
mesajı göster (veya backend response body'sindeki `code` alanına göre ayrım yap —
backend zaten `code` döndürüyor mu kontrol edilmeli). PLAN.md 3.18.

---

## 3. `.env.example` içindeki base URL kurulumu kırıyor (KRİTİK)

`.env.example` (git'te takip edilen placeholder dosya):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Backend'de **`/api/v1` prefix'i hiçbir router'da yok** — tüm route'lar doğrudan
kökten: `/auth/login`, `/engagements`, `/evidence/upload-url` vb.
(`backend/app/api/*.py` içindeki `APIRouter(prefix=...)` tanımları doğrulandı,
hiçbirinde `/api/v1` geçmiyor).

`frontend/lib/api/client.ts:17`'deki kod-içi default zaten **doğru**:
```ts
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
```
(prefix'siz). Yani şu anki geliştirme ortamı muhtemelen `.env` dosyasında bu
değişkeni hiç set etmediği için kazara doğru çalışıyor — ama:

- **Açık kaynak paketi (PLAN 3.15) kapsamında** biri `.env.example`'ı kopyalayıp
  `.env.local` yaparsa (ki `.env.example`'ın amacı tam olarak bu), her istek
  `http://localhost:8000/api/v1/auth/login` gibi var olmayan bir path'e gider →
  **tüm frontend 404'e düşer**, hiçbir açıklama olmadan.
- Bu, "kurulum talimatı sıfırdan doğrulanır" maddesinin (3.15) tam olarak
  yakalaması gereken bir hata sınıfı — henüz o madde çalıştırılmadığı için
  yakalanmamış.

**Düzeltme:** `.env.example`'da `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
yap (prefix'siz), ya da tersine backend'e gerçekten `/api/v1` prefix'i eklenmesi
mimari bir karar gerektirir (CLAUDE.md "yeni mimari önerme" kuralı gereği bu ikinci
seçenek önerilmiyor, sadece not düşülüyor). PLAN.md 3.20.

---

## 4. localStorage'da PII/hassas veri — proje kuralı ihlali (ORTA)

`.claude/rules/frontend.md`: *"Auth: httpOnly cookie — token'a JS'ten erişilmez,
`localStorage` kullanılmaz."*

- `evaluation.ts:43,108`: `private_note` alanı (kurum içi gizli değerlendirme
  notu — CLAUDE.md'de "Loglara PII yazılmaz" listesinde açıkça sayılan bir alan)
  `StoredEvaluation` içinde **düz metin olarak `window.localStorage`'a yazılıyor**.
  Kod, API response'unda `private_note`'un hiç dönmediğini özenle sağlıyor (D9
  kuralı doğru uygulanmış, satır 32-33), ama aynı hassasiyet localStorage'a
  taşınmamış — tarayıcıda kalıcı, XSS ile okunabilir, DevTools'tan görülebilir.
- `evidence.ts:153-176`: kanıt kayıtları (`EvidenceRecord[]`) da localStorage'da.
  Bunlar PII sınıfında değil ama kuralın lafzını (`localStorage kullanılmaz`)
  ihlal ediyor.

**Neden önemli:** Kural sadece auth token'ı için yazılmış olsa da, "localStorage
kullanılmaz" ifadesi genel bir mimari karar (sunucu durumu = TanStack Query,
localStorage yok) — bu iki dosya o kararı bilerek çiğniyor (mock olduğu için haklı
gerekçeyle), ama gerçek koda geçerken localStorage'ın tamamen kaldırılması ve
varsa geçiş döneminde biriken verinin temizlenmesi gerekiyor.

**Düzeltme:** 3.17/3.18 (mock→gerçek geçişi) tamamlandığında bu dosyalardaki
`localStorage.getItem/setItem` çağrılarının tamamı kaldırılmalı. PLAN.md 3.19.

---

## 5. PLAN.md gerçek kod durumunu yansıtmıyordu (ORTA — bu oturumun kök nedeni)

Kullanıcı "Faz 3'te kalan iş yok sanıyordum" dedi — araştırma bunun **kısmen
tersi** olduğunu gösterdi: bazı işler bitmiş ama işaretlenmemiş, bazı işler de
(3.17-3.23) hiç madde olarak açılmamıştı:

- **3.1, 3.2, 3.3, 3.11** main'de kod+test+ATDD artifact olarak tam ama PLAN.md'de
  `[ ]` idi → bu oturumda `[x]` olarak düzeltildi (YET-105/106/107 ve seed script
  referanslarıyla).
- **3.17-3.23** (evidence/evaluation mock temizliği, env düzeltmesi,
  require_email_verified, test_seed.py izolasyonu, son doğrulama) önceki
  maddelerin (2.11, 3.12) metin içi notlarında *"ayrı bir madde olarak açılmalı"*
  diye işaretlenmiş ama hiçbiri gerçekten madde numarası almamıştı — bu yüzden
  PLAN.md'yi üstünkörü okuyan biri bunları göremiyordu.

**Düzeltme:** Bu oturumda PLAN.md'ye eklendi (bkz. aşağıdaki "PLAN.md'de yapılan
değişiklikler"). Bundan sonra bir madde notunda "ayrı madde açılmalı" yazıldığı an
o madde numarası da o commit'te açılmalı — yoksa borç metne gömülüp kaybolur.

---

## 6. Docker Desktop çalışmıyor — bu rapor canlı doğrulanmadı (ORTA)

`docker ps` / `docker compose ps` komutları
`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`
hatasıyla başarısız oldu. Sonuç: PostgreSQL, MinIO, backend (`uvicorn`), frontend
(`npm run dev`) hiçbiri bu oturumda ayağa kaldırılıp gerçek bir tarayıcı/HTTP
isteğiyle test edilemedi.

**Bunun anlamı:** Yukarıdaki bulgular (özellikle 1, 2, 3) kod okumaya dayanıyor —
son derece yüksek güvenle doğru (backend route'ları grep ile teyit edildi, frontend
mock bayrakları doğrudan okundu), ama örneğin CORS'un tarayıcıda gerçekten preflight
sorunu çıkarıp çıkarmadığı, cookie `SameSite`/`Secure` ayarlarının gerçek tarayıcı
davranışıyla uyumu, veya migration zincirinin baştan sona `alembic upgrade head` ile
sorunsuz uygulanıp uygulanmadığı **doğrulanamadı**.

**Öneri:** Docker Desktop açıldığında şu sıra minimum doğrulama olarak çalıştırılmalı:
```
docker compose up -d
cd backend && alembic upgrade head && uvicorn app.main:app --reload
cd frontend && npm run dev
```
sonra tarayıcıda gerçek bir kayıt→giriş→engagement→evidence→evaluation akışı
elle denenmeli. Bu, PLAN 2.14 (uçtan uca duman testi) maddesinin zaten talep
ettiği şey — henüz yapılmamış.

---

## 7. `require_email_verified()` hiç kullanılmıyor (DÜŞÜK-ORTA)

3.12'nin notunda zaten yazılıydı: fonksiyon tanımlı ama hiçbir router'da
`Depends()` olarak bağlanmamış. Yani e-posta doğrulaması olmayan bir kullanıcı da
yazma uçlarını (engagement açma, evidence yükleme, evaluation gönderme) sınırsız
kullanabiliyor. Bilinçli bir kapsam kararı mı yoksa unutulmuş mu netleşmemiş
— PLAN.md 3.21 olarak resmi madde açıldı.

---

## 8. `tests/test_seed.py` izolasyon hatası (DÜŞÜK)

3.12'nin notunda zaten yazılıydı: seed fonksiyonlarını test içinde çağırırken ayrı
bir DB session açılıyor, bu da pytest'in transaction-rollback izolasyonunu bypass
ediyor ve yerel geliştirme veritabanına kalıcı satır bırakıyor. Kod hatası değil,
test hijyeni hatası — PLAN.md 3.22 olarak resmi madde açıldı.

---

## Doğrulanan, SORUN OLMAYAN alanlar (referans için)

Aşağıdakiler bu denetimde kontrol edildi ve **doğru** bulundu — tekrar
sorgulanmasın:

- `frontend/lib/api/engagements.ts`: `GET /engagements`, `GET /engagements/{id}`,
  `POST /engagements/{id}/transitions` gerçek `apiFetch` ile bağlı, mock store
  main'de kaldırılmış (commit 3a791ff).
- `frontend/lib/api/admin.ts`, `institutions.ts`, `public.ts`, `client.ts`
  içindeki auth/skills/talent_skills/skill_signals/verified_experiences
  fonksiyonları: hepsi gerçek `apiFetch`, mock/localStorage yok.
- CSRF: cookie adı `csrf_token`, header adı `X-CSRF-Token` (backend
  `app/core/deps.py:69-70`) ile frontend'in gönderdiği `x-csrf-token`
  (`client.ts:133`, case-insensitive) birebir eşleşiyor.
- CORS: `allow_credentials=True`, `allow_origins` default `http://localhost:3000`
  (frontend portu ile tutarlı), `allow_headers=["*"]` CSRF header'ını kapsıyor.
- Evaluation rating enum'u (`BELOW/MEETS/EXCEEDS/NOT_OBSERVED`) frontend Zod
  şeması ile backend CHECK kısıtı birebir aynı.

---

## PLAN.md'de yapılan değişiklikler (bu oturum)

1. 3.1, 3.2, 3.3, 3.11 → `[ ]`'den `[x]`'e (kod zaten tamamdı, sadece belge senkronu).
2. Yeni maddeler eklendi: 3.17 (evidence mock temizliği), 3.18 (evaluation mock
   temizliği), 3.19 (localStorage/PII temizliği), 3.20 (.env.example düzeltmesi),
   3.21 (require_email_verified kararı), 3.22 (test_seed.py izolasyonu),
   3.23 (son doğrulama — grep ile mock/localStorage kalmadığını teyit).

**Sıradaki iş (kullanıcının belirttiği gibi ATDD ile başlanacak):** PLAN.md'deki
sırayla 3.17 → 3.18 → 3.19 → 3.20 → 3.21 → 3.22 → 3.23, sonra 2.14 (uçtan uca
duman testi). 3.17/3.18 `@fe` etiketli ama backend'de değişiklik gerektirmiyor —
sadece iki dosyadaki mock bayraklarının kaldırılması ve backend gerçek çalışırken
doğrulanması. 3.20/3.21/3.22 `@be` etiketli, bağımsız çalışılabilir.
