# Gece prompt'ları (Sonnet için kopyala-yapıştır)

> Sıra ve süreler: [`gece-plani.md`](gece-plani.md). **Her prompt yeni oturumda** (`/clear`), model `/model sonnet`.
> `/ekran` skill'i listede görünmüyorsa Claude Code'u kapatıp aç.

Akışın özeti:

```
P0 (hazırlık) → P1 (demo verisi) → [ /clear → /ekran ] × istediğin kadar → P5 (kapanış)
```

---

## P0 — Hazırlık (10 dk)

```
Sunum öncesi frontend işine başlıyoruz. Sadece hazırlık yap, kod değiştirme.

1. `git status` ve `git log --oneline -5` göster. `git pull --ff-only` ile main'i güncelle (çakışma çıkarsa DUR, bana sor).
2. `docker compose up -d` çalıştır, `docker ps` ile postgres ve minio'nun "healthy" olduğunu doğrula.
3. backend/ içinde `alembic current` ve `alembic heads` karşılaştır; farklıysa migration UYGULAMA, bana söyle.
4. Rapor: 3 satır — git, docker, alembic.
```

Sonra:
- `baslat.bat` ile uygulamayı aç (backend + frontend). Açık kalsın.
- CI durumuna tarayıcıdan bak: GitHub → repo → **Actions**. En üstteki çalışma yeşil olmalı. Kırmızıysa hata satırını kopyala, Sonnet'e "bu CI hatasını düzelt, önce nedenini söyle" de. (`gh` CLI bu makinede kurulu değil.)

---

## P1 — Demo verisi kontrolü: FE-01 / FE-02 (15 dk)

```
planfrontend.md FE-01 ve FE-02'yi yapacağız. Kod DEĞİŞTİRME, sadece doğrula ve raporla.
Backend http://localhost:8000'de çalışıyor.

Oku: planfrontend.md §5 (Seed hesapları) ve backend/scripts/seed.py'de hesap/şifre üretimi (şifreyi çıktıya YAZMA, sadece kullan).
Auth uçlarını backend/app/api/auth.py'den bul.

1. Şu hesapların her biriyle login dene (curl, cookie jar ile), sonra GET /me çağır:
   ayse.yilmaz@posta.test, murat.demirci@yelkovanyazilim.test, nermin.basaran@cinaralti.edu.test, kerem.taskin@cinaralti.edu.test.
   Her biri için: login HTTP kodu, /me'de organizations/institutions/talent_profile dolu mu.
2. Veritabanında (psql değil — backend içinden küçük bir python -c ile, mevcut SessionLocal'i kullanarak, SADECE SELECT):
   - status='VERIFIED' olan engagement sayısı
   - public token'ı olan en az 1 verified experience → /v/{token} linki
   - public_slug'ı dolu en az 1 talent profili → /p/{slug} linki
   - ogrenci1'in bir VERIFIED ve bir ACTIVE/devam eden çalışması var mı (demo akışı için)
3. Bulunan /v/{token} ve /p/{slug} için backend'in public uçlarını curl ile çağır, 200 dönüyor mu.
4. planfrontend.md §5 tablosunun "Gösterdiği ekran" sütununu gerçek panel id'leriyle güncelle (yalnız bu tablo; şifre yazma). FE-01 ve FE-02'yi [x] yap (sorun varsa [~] ve not). Commit et (dosyayı adıyla ekle, Co-Authored-By yok).
5. Rapor: tablo (hesap | login | rol), demo linkleri (/v/..., /p/...), eksik varsa ne eksik.
   Eksik varsa DÜZELTME — bana söyle (backend/seed değişikliği onay ister).
```

**Eksik çıkarsa:** `python -m scripts.reset_demo --yes --reseed` dene, P1'i tekrar çalıştır. Yine eksikse geç. Ekranlar testlerdeki mock veriyle de geliştirilebilir.
**P1'in verdiği `/v/...` ve `/p/...` linklerini bir yere not et.** Ekran kontrollerinde lazım olacak.

---

## Ekran döngüsü (istediğin kadar tekrarla)

```
/clear
/ekran
```

Hepsi bu. Skill şunları kendisi yapar:
1. Kuyrukta sıradaki ekranı seçip söyler.
2. Brifi ve taslağı okur, ekranı dönüştürür.
3. Testleri çalıştırır, commit atar.
4. "Sıradaki: …" diye biter.

Bir ekranı zorlamak istersen kodunu ver: `/ekran 13`.

**Paralel çalışacaksan** (2–3 oturum): kurulum ve kurallar `gece-plani.md` → "Paralel oturumlar" bölümünde. Kısaca: her oturum ayrı worktree klasöründe çalışır, kod her zaman açıkça verilir (`/ekran shell`), her ekrandan sonra `git pull --rebase origin main && git push origin HEAD:main`.

**Her ekrandan sonra 2 dakikalık kendi kontrolün:** Tarayıcıda o ekranı aç, DevTools → cihaz araç çubuğuyla **375px** ve **1280px** genişlikte bak.

| Ekran | Nasıl açılır / neye bakılır |
|---|---|
| `2` | P1'deki `/v/{token}` linki. Yanlış bir token ile 404 görünümünü de dene. |
| `shell` | `ogrenci1` ve `org1-admin` ile giriş yap. Menüde doğru linkler var mı, aktif öğe doğru mu, çıkış çalışıyor mu. 375px'de çekmeceyi aç ve kapat. |
| `3` | P1'deki `/p/{slug}` linki. |
| `10`–`10c` | `ogrenci1` → Çalışmalarım → devam eden bir çalışma. Zincir doğru adımda mı. |
| `13` | `ogrenci1` → Profil. Beyan gri, doğrulanmış yeşil/mühürlü mü. |
| `11` | `org1-admin` → kuruluş paneli → değerlendirme bekleyen bir çalışma → değerlendir. |

Beğenmediğin bir şey varsa aynı oturumda düzeltme iste. Skill zaten commit attıysa düzeltme yeni commit olur, sorun değil:

```
<şu kısım> brifteki gibi değil: <ne görüyorsun>. Brifin ilgili satırına göre düzelt, testleri tekrar çalıştır, commit et.
```

Her 2 ekranda bir:

```
git push origin main
```

---

## P5 — Kapanış (her bıraktığında, 10 dk)

```
Gece kapanışı. Kod değiştirme (kırmızı varsa düzeltmeden önce bana sor).

1. `git status --short` temiz mi? Değilse listele ve DUR.
2. frontend/ içinde CI'ın aynısı: `npm run lint && npm run typecheck && npm run test && npm run build`. Sonucu raporla.
3. `git log --oneline origin/main..HEAD` ile push edilmemiş commit'leri listele.
4. Hepsi yeşilse `git pull --rebase origin main && git push origin main`. (Kırmızıysa push YOK.)
5. /handoff çalıştır ve HANDOFF.md'yi güncelle:
   - bu gece biten FE maddeleri
   - yarım kalan ([~] olanlar; hangi dosyada, ne eksik)
   - yarın kuyrukta sıradaki kodlar (docs/gece-plani.md "10 Ekim" tablosu)
   - bilinen sorunlar
   HANDOFF.md'yi ayrı commit'le ve push'la.
6. 5 satırlık özet ver.
```

---

## PX — Takıldım: geri al ve atla

```
Bu ekranda takıldık, vazgeçiyoruz. Commit edilmemiş değişiklikleri göster (`git status --short`, `git diff --stat`).
Sadece BU ekranın dosyalarındaki değişiklikleri `git restore <dosya>` ile geri al (dosya adlarını tek tek yaz, toplu komut yok; yeni oluşturulmuş dosyaları silmeden önce listeyi bana göster).
planfrontend.md'de ilgili FE satırını "[ ]" yap ve sonuna "— 9 Ekim gece denendi: <tek cümle neden>" notu düş; commit et.
Sonra dur.
```

Not: PX FE satırını `[ ]`'a geri çeker. Bu yüzden argümansız `/ekran` o ekranı yine seçer. Atlamak istiyorsan sıradakini kodla ver: `/ekran <sonraki kod>`.

---

## Yarın ekip arkadaşları için (10 Ekim)

Her kişi kendi ekranı için yeni oturumda (argümanı **mutlaka** ver, iki kişi aynı ekranı seçmesin):

```
git pull --ff-only
```
```
/ekran <kod>
```

Bitince:
```
git pull --rebase origin main && git push origin main
```
