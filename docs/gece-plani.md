# Sunum öncesi frontend planı (9 Ekim gece → 11 Ekim sunum)

> Kopyala-yapıştır prompt'lar: [`gece-promptlari.md`](gece-promptlari.md) · Ekran prosedürü: `.claude/skills/ekran/SKILL.md` (`/ekran <no>`)
> Tasarım kaynağı: [`sayfa-tasarim-brifi.md`](sayfa-tasarim-brifi.md) (çelişirse `planfrontend.md`'nin önüne geçer) + `tasarimlar/stitch/` mockup'ları.

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
| 2 | 35 dk | **`/v/[token]` sertifika** (FE-13, en kritik) | `/ekran 2` (Prompt **P2**) | 1 commit |
| 3 | 35 dk | **AppShell sol navbar** (FE-09): içerideki tüm sayfaları tek seferde "yeni" gösterir | `/ekran shell` (Prompt **P3**) | 1 commit |
| 4 | 15 dk | **`/p/[slug]`** (FE-14, küçük dosya) — süre kalırsa | `/ekran 3` (Prompt **P4**) | 1 commit |
| 5 | 10 dk | Kapanış: tam frontend testi, push, ekibe devir notu | Prompt **P5** | Push, `HANDOFF.md` güncel |

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

Demo akışı sırasıyla (`planfrontend.md` §4). Her kişi kendi ekranında `/ekran <no>`, her ekran ayrı commit. **Aynı dosyaya iki kişi dokunmaz.**

| Kişi | Ekranlar (öncelik sırası) | Not |
|---|---|---|
| **A** | 10 `/calismalar/[id]` (demonun kalbi, FE-17) → 11 değerlendirme formu (FE-22) | En büyük iş; sabah ilk iş başlamalı |
| **B** | 13 `/profil` (FE-18) → 9 `/calismalar` (FE-16) → 14 kuruluş paneli (FE-20) | `profil/` altında 5 bileşen var |
| **C** | Deploy veya yerel demo kurulumu (aşağıda) → 16 kurum paneli (FE-21) → 21 404/hata | Deploy kararı **10 Ekim 12:00**'ye kadar |

- 15:00: herkes `main`'i çeker, demo akışı baştan sona bir kez tıklanır (FE-32 provası).
- 18:00: kod dondurma. Bundan sonra yalnız kırık olan düzeltilir.
- Akşam: **ekran kaydı yedeği** alınır (canlı demo çökerse oynatılır).
- Kesme sırası (geride kalınırsa): 21 → 16 → 14 → 9. Yani en son eklenen P1'ler ilk kesilir. **10, 11, 13, 2 asla kesilmez.**

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
