# Sunum öncesi frontend planı (9 Ekim gece → 11 Ekim sunum)

> Kopyala-yapıştır prompt'lar: [`gece-promptlari.md`](gece-promptlari.md) · Ekran prosedürü: `.claude/skills/ekran/SKILL.md` (`/ekran <no>`)
> Tasarım kaynağı: [`sayfa-tasarim-brifi.md`](../sayfa-tasarim-brifi.md) (çelişirse `planfrontend.md`'nin önüne geçer) + `tasarimlar/stitch/` mockup'ları.

## Neredeyiz (9 Ekim 23:00)

| Durum | Ne |
|---|---|
| Bitti | Renk/yazı token'ları, kontrast testi (FE-03/04) · landing `/` · 5 auth sayfası (FE-15) · `ChainProgress`, `VerifiedSeal`, `Card/Badge/Alert/Button` |
| Tasarımı hazır, kodu eski | Kalan ~18 ekran. Stitch mockup'ları `tasarimlar/stitch/` içinde (20 + 8 ekran). Koddaki sabit renk sayısı ~654. |
| CI | 9 Ekim akşamı kırmızıydı (mypy `skill_signal.py:84` + `institution-link-section.test.tsx`). Düzeltildi. Yerelde backend 1561 test, frontend 1229 test geçti; mypy, ruff, lint ve typecheck temiz. |
| Deploy | Yok. Render belirsiz → aşağıda "Deploy" bölümü. |

**"Tasarım arşivlendi"** = Stitch çıktıları referans olarak repoya indirildi. Ekranlar henüz koda geçmedi.

## Altın kural

Sürenin tamamı **demo zincirinde görünen ekranlara** gider. Yeni özellik, backend değişikliği ve refactor yok. Gün sonunda geride kalınırsa P1 ekranlar kesilir, P0 ekranlar kesilmez. Eski görünümlü ama **çalışan** bir ekran, yarım bırakılmış yeni bir ekrandan iyidir.

---

## Bu gece (≈2 saat, Sonnet ile)

| # | Süre | İş | Nasıl | Çıktı |
|---|---|---|---|---|
| 0 | 10 dk | Hazırlık: güncel kod, ortam, CI | Prompt **P0** | Uygulama ayakta, CI yeşil |
| 1 | 15 dk | **FE-01/02 demo verisi kontrolü:** her rol giriş yapabiliyor mu, `VERIFIED` çalışma + `/v/{token}` + `/p/{slug}` var mı | Prompt **P1** | `planfrontend.md` §5 tablosu dolu, demo linkleri not edildi |
| 2 | 35 dk | **`/v/[token]` sertifika** (FE-13, en kritik) | `/clear` → `/ekran` | 1 commit |
| 3 | 35 dk | **AppShell sol navbar** (FE-09): içerideki tüm sayfaları tek seferde "yeni" gösterir | `/clear` → **`/model opus`** → `/ekran` | 1 commit |
| 4 | 15 dk | **`/p/[slug]`** (FE-14, küçük dosya) | `/clear` → `/ekran` | 1 commit |
| 5 | 10 dk | Kapanış: tam frontend testi, push, ekibe devir notu | Prompt **P5** | Push, `HANDOFF.md` güncel |

`/ekran` argümansız yazılınca sıradaki ekranı kendisi seçer. Kuyruk skill'in içinde; `planfrontend.md`'de `[ ]` olan ilk satırı alır. Her ekranın özel notları da skill'de. Yani 2–4. adımlar aynı iki komuttan ibaret: `/clear`, sonra `/ekran`.

### Model seçimi ve toplam süre

**Kuyruk tarihe bağlı değil.** `/ekran` kuyruğu `planfrontend.md`'deki `[x]` işaretlerine göre okur. Bu gece, yarın ya da arkadaşının makinesinde (`git pull` sonrası) hep kalınan yerden devam eder. Kuyruk bitince bunu söyler ve cila işlerini (FE-26/27/28/31/32) önerir.

**Opus önerilen ekranlar:** `shell`, `10`, `10b`, `10c`. Bunlar çok testli ya da durum makinesine ve dosya yüklemeye bağlı. Sonnet'le bu ekranlardan birine gelinirse skill durup uyarır: `/model opus` yazıp `/ekran <kod>`, ya da "devam" de. Diğer 11 ekran Sonnet'e uygun.

**Tahmini oturum sayısı** (1 oturum ≈ 25–45 dk):

| Kapsam | Ekran oturumu | + düzeltme / cila | Toplam | Tek kişi süre |
|---|---|---|---|---|
| **Demo için şart** (`2`, `shell`, `3`, `10`, `10b`, `10c`, `13`, `11`) | 8 | +2–3 | ~10–11 | ~6 saat |
| **Tüm kuyruk** (15 kod) | 15 | +4–5 | ~19–20 | ~11 saat |
| + Faz 4 (P0, P1, P5, responsive/a11y turu, prova) | — | +4–5 | **~24** | ~13 saat |

3 kişi paralel çalışırsa tüm iş kişi başı ~4–5 saate iner. **Gerçekçi hedef:** bu gece + yarın öğlene kadar "demo için şart" satırı bitsin. Gerisi kod dondurmaya (10 Ekim 18:00) kadar ne yetişirse.

### 2 saatten sonra devam etmek istersen

Aynı döngü devam eder. Kuyruğun devamı demo önemine göre sıralı:

`10` → `10b` → `10c` (çalışma detayı, 3 oturum) → `13` profil → `11` değerlendirme → `9` liste → `14` kuruluş paneli → `21` 404 → `16` kurum paneli → `12` → `18` → `19`

Her ekran için döngü:
1. `/clear`
2. `/ekran`. Sonnet seçtiği ekranı söyler; işini bitirip commit atar ve sıradakini yazar.
3. Tarayıcıda 375px ve 1280px genişlikte bir bak. Kötüyse "şu kısmı brife göre düzelt" de.
4. Her 2 ekranda bir `git push origin main` iste. Böylece yarın ekip nerede kaldığını görür, iş de kaybolmaz.

Ne zaman bırakırsan bırak, **son iş P5** (kapanış). Yarım ekranla yatma: ya commit et ya PX ile geri al. Çalışma ağacı temiz kalsın.

Yorgunluk kuralı: aynı hatayla ikinci kez 10 dakika uğraşıyorsan PX'i çalıştır, bir sonrakine geç.

### Paralel oturumlar (daha hızlı, ama kurallı)

**Aynı klasörde iki oturum açma.** Ortak git index'i kullanırlar, ikisi de `tr.json`'a yazar ve aynı ekranı seçebilirler. Her paralel oturum **kendi worktree'sinde** (ayrı klasör, aynı repo) çalışır.

**Önerilen: en fazla 2–3 paralel oturum.** Darboğaz Sonnet değil, senin görsel kontrolün.

| Oturum | Klasör | Kuyruk | Neden birbirinden bağımsız |
|---|---|---|---|
| **1** (ana) | `yetkin360/` | `2` → `3` | Public sayfalar; `3`, `2`'nin üst barını paylaşabilir, o yüzden ikisi aynı oturumda |
| **2** | `yetkin360-shell/` | `shell` → `10` → `10b` → `10c` | Kabuk ve çalışma detayı |
| **3** (opsiyonel) | `yetkin360-profil/` | `13` → `11` → `9` | Profil ve değerlendirme |

**Kurulum (PowerShell, `yetkin360/` içinde; her worktree için bir kez, ~2 dk):**

```powershell
git pull --ff-only
git worktree add ..\yetkin360-shell -b ekran-shell
cd ..\yetkin360-shell\frontend; npm ci; cd ..
claude
```

Açılan oturumda `/model sonnet`, sonra `/ekran shell`. Paralel oturumlarda **kodu her zaman açıkça ver**; argümansız `/ekran` kullanma.

**Her ekrandan sonra, worktree oturumunda:**

```
git pull --rebase origin main && git push origin HEAD:main
```

Böylece işler hep `main`'de birikir. Rebase'de `tr.json` ya da `planfrontend.md` çakışması çıkarsa Sonnet'e şunu de: "Rebase çakışmasını çöz: iki tarafın anahtarlarını da koru, hiçbirini silme. Sonra testleri çalıştır."

**Görsel kontrol:** Ana klasörde `baslat.bat` açık kalsın. Worktree push ettikten sonra ana klasörde `git pull --ff-only` yap; Next.js değişikliği otomatik yükler. Worktree'de ikinci bir dev sunucu açma. Backend CORS varsayılan olarak yalnız `http://localhost:3000`'e izin veriyor (`backend/app/core/config.py`), 3001'deki sayfa API'ye bağlanamaz.

**Bitince temizlik** (ana klasörde, worktree'deki her şey push edildikten sonra):

```powershell
git worktree remove ..\yetkin360-shell
git branch -d ekran-shell
```

**Paralel modun kuralları** (skill'de de yazıyor):
- Yeni ortak ilkel (`components/ui/Skeleton` vb.) yalnız **oturum 1** ekler. Diğerleri gerekirse kendi ekran dosyasının içinde küçük yerel bir parça yazar; birleştirme sonra yapılır.
- `tr.json`'da yalnız kendi ekranının bölümüne anahtar ekle. Başka bölüme dokunma.

**Neden bu sıra?**
- Seed kontrolü önce, çünkü `VERIFIED` bir kayıt yoksa `/v` ekranı test edilemez.
- `/v` jürinin kendi telefonunda göreceği tek ekran.
- AppShell 15 içeri sayfanın çerçevesi; tek değişiklikle hepsi aynı aileden görünür.

**Takılırsan:** 10 dakikadan fazla aynı hatayla uğraşma. Prompt **PX**'i ("geri al ve atla") kullan, sıradaki adıma geç.

### Model ve skill seçimi

- Claude Code'da `/model sonnet`. Her adım için **yeni oturum** aç (`/clear`). Bağlam küçük kalır, Sonnet daha isabetli çalışır.
- **Kullan:**
  - `/ekran <no>` (yeni, bu iş için yazıldı: oku → uygula → doğrula → commit)
  - `/handoff` (gece sonu devir notu)
- **Kullanma (bu gece):**
  - `atdd → test-copilot → code-copilot → red-team` hattı: görsel iş için çok yavaş. Ayrıca Haiku alt-ajanları daha önce izinsiz commit/push yapıp dosya sildi.
  - `vision-test` ve `frontend-audit`: Playwright/Codex MCP kurulu değilse çalışmaz. Görsel kontrolü kendin yap: tarayıcı DevTools, 375px ve 1280px.
- `/verify` yerine CI'ın birebir komutlarını çalıştır (P5'te yazıyor). Daha hızlı ve aynı sonucu verir.

---

## 10 Ekim (3 kişi, kod dondurma akşam 18:00)

Gece nerede kalındıysa kuyruk oradan devam eder. Sabah ilk iş: `git pull` → `planfrontend.md`'de hangi FE'ler `[x]`, ona bak.

**Çakışmayı önleme kuralı:** Herkes başka bir kuyruk kodu alır. Kodu açıkça ver (`/ekran 13`); argümansız `/ekran` kullanma, iki kişi aynı ekranı seçebilir. Başlamadan önce ekibe "13'ü aldım" yaz. **Aynı dosyaya iki kişi dokunmaz.**

| Kişi | Kuyruktan (gece yapılmadıysa) | Not |
|---|---|---|
| **A** | `10` → `10b` → `10c` → `11` | Demonun kalbi; sabah ilk iş |
| **B** | `13` → `9` → `14` | `profil/` altında 5 bileşen var |
| **C** | Deploy ya da yerel demo kurulumu (aşağıda) → `21` → `16` | Deploy kararı **10 Ekim 12:00**'ye kadar |

Gece bazıları bittiyse kişiler kuyruğun kalanını sırayla paylaşır.

- 15:00: herkes `main`'i çeker, demo akışı baştan sona bir kez tıklanır (FE-32 provası).
- 18:00: kod dondurma. Bundan sonra yalnız kırık olan düzeltilir.
- Akşam: **ekran kaydı yedeği** alınır (canlı demo çökerse oynatılır).
- Kesme sırası (geride kalınırsa): `19` → `18` → `12` → `16` → `21` → `14` → `9`. **`2`, `shell`, `10`, `13`, `11` asla kesilmez.**

---

## Deploy: Render mı, yerel mi?

**Önerim:** Render'ı yalnız biri (Kişi C) 10 Ekim öğlene kadar dener. Olmazsa **yerel demo + ekran kaydı** ile gidilir. Bu gece deploy'a vakit harcama.

### Render'da bilinen engeller (kodda doğrulandı)

1. **Çerez/oturum (kritik):** Backend çerezleri `SameSite=Lax` ile basıyor (`backend/app/api/auth.py`). `onrender.com` Public Suffix List'te. Bu yüzden `frontend-x.onrender.com` ile `api-y.onrender.com` **farklı site** sayılır ve tarayıcı giriş çerezini API'ye göndermez. Sonuç: giriş "başarılı" görünür ama hiçbir sayfa açılmaz.
   **Çözüm:** Next.js `rewrites` ile `/api/*` isteklerini backend'e proxy'lemek. Tarayıcı tek origin görür. `NEXT_PUBLIC_API_BASE_URL` frontend'in kendi adresine (+`/api`) ayarlanır. Bu küçük bir config değişikliği ama `next.config.ts` + `.env.example` + CORS ayarına dokunur, onayla yapılır. Aynı çözüm telefondan yerel ağ veya tünel erişimini de çözer.
   Not: `/v/[token]` giriş istemez. Sadece CORS doğruysa (`ALLOWED_ORIGINS`) proxy olmadan da çalışabilir. Yani en kötü ihtimalle "jüri telefonundan sertifika" kısmı ayakta kalır.
2. **Dosya deposu:** MinIO Render'da yok. Kanıt yükleme için S3 uyumlu harici bir depo gerekir (Cloudflare R2 / Backblaze B2). Yoksa demoda kanıt yükleme adımı gösterilemez.
3. **Outbox worker:** Ayrı bir "Background Worker" servisi gerekir (ücretli plan). Yoksa e-posta gitmez. Demo seed kullanıcıları zaten doğrulanmış olduğu için bu demoyu **engellemez**.
4. **Veritabanı:** Render PostgreSQL → `alembic upgrade head` → `python -m scripts.seed`.
5. Production config kontrolleri açılışta sıkı (`COOKIE_SECURE`, CSRF, CORS `*` reddi). Env eksikse uygulama **bilerek açılmaz**. Log'daki mesaj neyin eksik olduğunu söyler.

### Yerel demo (yedek plan, garanti)

- `baslat.bat` → `python -m scripts.reset_demo --yes --reseed` → tarayıcıda demo akışı.
- Jüri telefonu için: sunum slaytına `/v/{token}` sayfasının **ekran görüntüsü + QR** koy. Canlı link yoksa bile sertifika görülür.

---

## Sunumdan önce son kontrol listesi (11 Ekim sabah)

- [ ] `alembic current` = `heads`
- [ ] `reset_demo --yes --reseed` çalıştı, demo hesaplarıyla giriş denendi
- [ ] Demo akışı (10 adım) baştan sona bir kez tıklandı
- [ ] Ekran kaydı yedeği bilgisayarda **ve** USB'de
- [ ] CI yeşil (jüri repoya bakabilir)
- [ ] `README.md` kurulum talimatı güncel
