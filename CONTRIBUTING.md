# Katkı Rehberi

Yetkin360'a katkı vermek için gereken her şey. Proje hackathon takvimiyle
çalışıyor — kurallar kısa ve bağlayıcı.

**Önce okuyun:** [README.md](README.md) (kurulum) · [PLAN.md](PLAN.md) (iş sırası)
· `CLAUDE.md` (değişmez kurallar)

---

## Ekip ve sahiplik

[PLAN.md](PLAN.md)'deki her madde bir sahip etiketi taşır. Etiket sabittir —
isim değişse bile plan satırı kısa kalır.

| Etiket | Alan | Kişi |
|---|---|---|
| `@be1` | Backend — alan modeli, engagement, institution, seed | Yusuf Çinar (`yutronax`) |
| `@be2` | Backend — yetkilendirme, auth, dosya, attestation, deploy | Meyrem Şenge (`Meyremsenge`) |
| `@fe` | Frontend — tüm ekranlar, erişilebilirlik | Elif Sara |
| `@all` | Ortak — faz kapanışları, dokümantasyon, sunum | Tümü |

**Sahiplik ne demek:** Maddeyi bitirmek o kişinin sorumluluğudur — tek başına
yazması gerekmez. Başkasının maddesine dokunmadan önce ona haber verin.

---

## Çalışma akışı

### 1. Maddeyi seçin

İş her zaman [PLAN.md](PLAN.md)'den gelir. Planda olmayan iş yapılmaz —
gerekliyse önce plana eklenir.

```bash
git checkout main && git pull
git checkout -b feat/2.5-dosya-yukleme
```

### 2. Sözleşmeyi yazın (backend ↔ frontend arası iş)

> **Sözleşme önce kuralı:** Bir maddenin API sözleşmesi
> ([docs/API.md](docs/API.md)) yazılmadan `@fe` o ekranı bekleyemez.

Sözleşme yazılır → `@fe` mock ile ilerler → backend gerçeğini bağlar.
**Backend'in bitmesini beklemek 3 kişilik ekipte en büyük israftır.**

### 3. Yazın

- Katman: `api/ → services/ → models/`. İş mantığı **yalnız** `services/` içinde.
- Tüm veri erişimi `can()` ve `scoped_*()` üzerinden. Çıplak `select(Model)` **yasak**.
- Pydantic şeması ile ORM modeli **asla aynı sınıf değildir**.
- UI metni Türkçe, koda gömülmez (sabit metin dosyasından).

### 4. Test edin

| Değişiklik | Çalıştırılacak |
|---|---|
| Sadece doküman | Hiçbiri |
| Frontend stil | `npm run lint` |
| Frontend mantık | `npm run typecheck` + ilgili bileşen testi |
| Backend servis | İlgili unit + integration testi |
| **Yeni endpoint** | İlgili test + **yetkilendirme testi (zorunlu)** |
| **Yetkilendirme / auth** | **`pytest tests/authorization -q` tamamı** |
| Migration | `alembic upgrade head` + `alembic downgrade -1` + testler |
| Bağımlılık değişikliği | Tüm test paketi |

> **Testi atlamak tasarruf değil, gizlenmiş hatadır.**

### Test veritabanı

Backend testleri geliştirme veritabanına **dokunmaz**. Testler başladığında:

1. **Otomatik oluşturma** — conftest.py boş test veritabanını sıfırdan oluşturur.
2. **Şema kurulumu** — `alembic upgrade head` ile tüm migration'lar uygulanır.
3. **Temizlik** — her test kendi verisini kurar; test sonunda rollback ile silinir.

Koşmak için:
```bash
docker compose up -d  # PostgreSQL + MinIO başlatır
cd backend
pytest -q
```

Testler dev veritabanını **değiştirmez**. CI'da test DB adı zaten `test` olarak ayarlanmıştır
(GitHub Actions üzerine PostgreSQL servisi sağlar).

Ortam değişkeni `TEST_DATABASE_URL` ile test DB'si geçersiz kılınabilir — ancak **adı `test` ile
bitmelidir** (güvenlik kuralı: dev DB'ye yanlışlıkla dokunmaya karşı koruma):

```bash
# Yerel olarak farklı test DB'si kullanma (adı "test" ile bitmeli)
TEST_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/custom_test" pytest -q
```

Paralel oturumlarda (ör. ayrı worktree'ler) her oturum kendi DB'sini kullanır: `TEST_DB_SUFFIX=s0 pytest -q` → `yetkin360_s0_test` (yalnız `[a-z0-9]`, en fazla 16 karakter).

Frontend testleri:
```bash
cd frontend
npm run test
```

### 5. PR açın

```bash
git push -u origin feat/2.5-dosya-yukleme
gh pr create
```

---

## Dal adlandırma

```
<tip>/<plan-maddesi>-<kısa-açıklama>
```

| Tip | Ne zaman |
|---|---|
| `feat/` | Yeni özellik |
| `fix/` | Hata düzeltme |
| `docs/` | Yalnız dokümantasyon |
| `test/` | Yalnız test |
| `chore/` | Yapılandırma, bağımlılık, altyapı |

**Örnekler:**
```
feat/1.2-yetkilendirme-cekirdegi
feat/2.8-attestation-uretimi
fix/2.5-magic-byte-kontrolu
docs/0.4-yetki-matrisi
```

**`main`'e doğrudan push yapılmaz.** İstisna: Faz 0 dokümantasyonu.

---

## Commit kuralları

- Mesaj **Türkçe**, tek satır özet + gerekirse gövde.
- Her mantıklı birim ayrı commit. **Bomba commit atmayın** — jüri repoya bakabilir.
- [PLAN.md](PLAN.md) maddesiyle ilgiliyse gövdeye madde numarasını yazın.
- `git add -A` / `git add .` **yasak** — dosyaları adıyla ekleyin.

```
Dosya yükleme için imzalı URL ucu eklendi

Üç adımlı akış: upload-url → PUT → POST /evidence.
Magic-byte kontrolü adım 3'te, dosya storage'a indikten sonra yapılıyor.

PLAN 2.5

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

**Yasak:** `git push --force` (açık onay olmadan), uygulanmış migration'ı
düzenleme (düzeltme = **yeni** migration), `.env` commit'leme.

---

## Kod inceleme akışı

Her PR bir ekip arkadaşından onay ister. Tek istisna: yalnız dokümantasyon.

### İnceleyen kontrol listesi

**Zorunlu — biri eksikse PR onaylanmaz:**

- [ ] Yetkilendirme testi var mı? (pozitif **ve** negatif — en az bir "başka kiracı erişemez")
- [ ] Response şeması ayrı tanımlı mı? ORM modeli doğrudan dönülmüyor mu?
- [ ] Veritabanı kısıtları eklendi mi? (sadece uygulama kontrolü yetmez)
- [ ] Durum değişikliği `AuditEvent` üretiyor mu?
- [ ] Ağ çağrısı transaction dışında mı? (`outbox`)
- [ ] Yetkisiz erişimde `404` dönüyor mu? (`403` değil)
- [ ] Loglara PII sızıyor mu? (şifre, token, `private_note`, tam e-posta)
- [ ] Migration geriye uyumlu mu?

**Frontend ek:**

- [ ] Klavye ile kullanılabiliyor mu? Focus görünür mü?
- [ ] Boş durum (empty state) tasarlandı mı?
- [ ] Hata durumu kullanıcıya anlaşılır mı? Teknik detay sızmıyor mu?
- [ ] UI metni Türkçe ve koda gömülü değil mi?

**Kapsam:**

- [ ] Bu değişiklik `beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirine hizmet ediyor mu?

> Son madde en önemlisidir. **MVP dışı özellik yazılmaz.** Yasaklılar: AI,
> matching motoru, chat, gamification, blockchain, trust score, assessment,
> Redis, Elasticsearch, Celery, pgvector, Kubernetes, RLS.

### İncelenen için

- İnceleme yorumu kişiye değil koda yöneliktir.
- Katılmıyorsanız tartışın — sessizce uygulamak da, sessizce yok saymak da yanlıştır.
- Bir kararı değiştirmek gerekiyorsa `yetkin360-final-analiz.md`'deki gerekçeye
  bakın; hâlâ katılmıyorsanız ekibe açın.

---

## Definition of Done

Bir özellik şunların **hepsi** sağlanmadan bitmiş sayılmaz:

1. Yetkilendirme testi yazıldı (pozitif **ve** negatif)
2. Girdi doğrulama Pydantic şemasıyla; response şeması **ayrı** tanımlı
3. Veritabanı kısıtları eklendi
4. Durum değişikliği `AuditEvent` üretiyor
5. Transaction sınırı bilinçli seçildi; ağ çağrısı transaction dışında
6. Hata durumları ele alındı; kullanıcıya teknik detay sızmıyor
7. Erişilebilirlik: klavye + label + kontrast
8. Boş durum tasarlandı
9. KVKK: bu veri neden toplanıyor, kim görüyor, ne zaman siliniyor — cevaplanmış
10. Migration geriye uyumlu

---

## Plan bakımı

1. **Madde eklemek serbest, madde silmek değil.** İptal edilen madde `[-]` ile
   kalır — jüri ve katkıcı için karar geçmişidir.
2. Yeni iş ilgili fazın sonuna eklenir, numara devam eder (`2.15`).
   **Numara yeniden kullanılmaz** — commit mesajları ona atıf yapar.
3. Her madde **tek satır**. Detay `docs/` içine yazılır.
4. Faz kapanış maddesi atlanmaz.

---

## Açık kaynak sorumluluğu

Repo herkese açıktır. Sonucu: **bir yetkilendirme açığı herkes tarafından
okunabilir.** Güvenlik kuralları gevşetilmez, sıkılaştırılır.

- Sır repoda olmaz. Commit öncesi kontrol edin — `gitleaks` CI'da çalışır.
- Bir sır kazara commit edilirse geçmişten silmek **yetmez**, sır **döndürülmelidir**.
- `LICENSE`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.env.example`
  her zaman güncel tutulur.

---

## Soru ve tartışma

| Konu | Nereye |
|---|---|
| Hata, özellik önerisi | GitHub Issues |
| **Güvenlik açığı** | **[SECURITY.md](SECURITY.md) — issue AÇMAYIN** |
| Mimari karar tartışması | `yetkin360-final-analiz.md`'deki ilgili bölüme atıfla Issue |
| Plan sırası | Ekip içi, sonra [PLAN.md](PLAN.md) güncellenir |
