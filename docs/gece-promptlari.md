# Gece prompt'ları (Sonnet için kopyala-yapıştır)

> Sıra ve süreler: [`gece-plani.md`](gece-plani.md). **Her prompt yeni oturumda** (`/clear`), model `/model sonnet`.
> Her prompt'u olduğu gibi yapıştır. Köşeli parantezli yerleri doldur.

---

## P0 — Hazırlık (10 dk)

```
Sunum öncesi frontend işine başlıyoruz. Sadece hazırlık yap, kod değiştirme.

1. `git status` ve `git log --oneline -5` göster. `git pull --ff-only` ile main'i güncelle (çakışma çıkarsa DUR, bana sor).
2. `docker compose up -d` çalıştır, `docker ps` ile postgres ve minio'nun "healthy" olduğunu doğrula.
3. backend/ içinde `alembic current` ve `alembic heads` karşılaştır; farklıysa migration UYGULAMA, bana söyle.
4. Rapor: 3 satır — git, docker, alembic.
```

CI durumuna tarayıcıdan bak: GitHub → repo → **Actions**. Son çalışma (en üstte) yeşil olmalı. Kırmızıysa hata satırını kopyalayıp Sonnet'e "bu CI hatasını düzelt, önce nedenini söyle" de. (`gh` CLI bu makinede kurulu değil.)

Sonra kendin `baslat.bat` ile uygulamayı aç (backend + frontend). Açık kalsın.

---

## P1 — Demo verisi kontrolü: FE-01 / FE-02 (15 dk)

```
planfrontend.md FE-01 ve FE-02'yi yapacağız. Kod DEĞİŞTİRME, sadece doğrula ve raporla.
Backend http://localhost:8000'de çalışıyor.

Oku: planfrontend.md §5 (Seed hesapları) ve backend/scripts/seed.py'de hesap/şifre üretimi (şifreyi çıktıya YAZMA, sadece kullan).
Auth uçlarını backend/app/api/auth.py'den bul.

1. Şu hesapların her biriyle login dene (curl, cookie jar ile), sonra GET /me çağır:
   ogrenci1@seed.local, org1-admin@seed.local, kurum1-admin@seed.local, kurum1-koordinator@seed.local.
   Her biri için: login HTTP kodu, /me'de organizations/institutions/talent_profile dolu mu.
2. Veritabanında (psql değil — backend içinden küçük bir python -c ile, mevcut SessionLocal'i kullanarak, SADECE SELECT):
   - status='VERIFIED' olan engagement sayısı
   - public token'ı olan en az 1 verified experience → /v/{token} linki
   - public_slug'ı dolu en az 1 talent profili → /p/{slug} linki
   - ogrenci1'in bir VERIFIED ve bir ACTIVE/devam eden çalışması var mı (demo akışı için)
3. Bulunan /v/{token} ve /p/{slug} adreslerine curl ile backend'den public uçları çağır, 200 dönüyor mu.
4. planfrontend.md §5 tablosunun "Gösterdiği ekran" sütununu gerçek panel id'leriyle güncelle (yalnız bu tabloyu değiştir; şifre yazma). FE-01 ve FE-02'yi [x] yap (sorun varsa [~] ve not).
5. Rapor: tablo (hesap | login | rol), demo linkleri (/v/..., /p/...), eksik varsa ne eksik.
   Eksik varsa DÜZELTME — bana söyle (backend/seed değişikliği onay ister).
```

**Eksik çıkarsa:** Önce `python -m scripts.reset_demo --yes --reseed` dene ve P1'i tekrar çalıştır. Yine eksikse bu adımı atla ve P2'ye geç. Sertifika ekranı testlerdeki mock veriyle de geliştirilebilir.

---

## P2 — `/v/[token]` doğrulama sertifikası (35 dk)

```
/ekran 2

Ek notlar:
- Brif §6 "2. Doğrulama sertifikası" tablosunu satır satır uygula: çift çerçeveli kart, sağ üstte VerifiedSeal lg (-4°), Serif 32px ad, 2 kolonlu bilgi ızgarası, T1 uyarısı, 4 adımı tamamlanmış ChainProgress, yetkinlik çipleri, Mono damga satırı ("Kayıt no: {token ilk 8}…").
- Mockup: tasarimlar/stitch/proje1-tum-sayfalar/19-yetkin360-dogrulama-sertifikasi-masaustu.png ve 04-yetkin360-dogrulama-sertifikasi-mobil-qr.png.
- 404 durumu brifteki gibi aynı kart + kesik çizgili boş daire. Yükleniyor durumu: kart iskeleti.
- Bu sayfa telefonda açılacak: 375px'de mühür üstte ortalı, ızgara tek kolon.
- Yalnız API'nin döndürdüğü alanlar kullanılır (brifte "Veri (yalnız bunlar)"). Olmayan alanı uydurma; eksikse raporda not et.
- "Linki kopyala" önerisini YAPMA (yeni özellik).
```

**Sonra kendin kontrol et:** P1'de bulduğun `/v/{token}` adresini tarayıcıda aç. DevTools'ta 375px ve 1280px genişlikte bak. Bir de yanlış bir token ile 404 görünümünü dene.

---

## P3 — AppShell sol navbar (35 dk)

```
/ekran shell

Ek notlar:
- Brif §5 (5.1 masaüstü, 5.2 mobil, 5.3 uyarı şeritleri, 5.4 durumlar) uygulanacak. Bugün kodda yatay üst bar var → sol navbar (248px, bg-sand, sağda 1px çizgi, sabit).
- Gruplar: Çalışma (Çalışmalarım, Profil, Herkese açık profilim) / Kuruluşlarım / Kurumlarım / Yönetim — görünürlük kuralları mevcut app-shell.tsx'teki mantıkla AYNI kalır (hangi link kime görünüyor değişmez, sadece yerleşim değişir).
- Aktif öğe: bg-card + 1px border + solda 2px×20px çam çizgi. /calismalar/* alt sayfaları "Çalışmalarım"ı aktif yapar (usePathname).
- Alt kullanıcı kartı + yukarı açılan menü (Profil, Çıkış). Radix YOK, yeni bağımlılık YOK: basit buton + koşullu liste; Esc ve dışarı tıklama kapatır; aria-expanded/aria-haspopup doğru.
- Mobil (<1024px): 56px üst bar + soldan açılan çekmece (280px). Esc/arka plana tıklama/öğeye tıklama kapatır.
- E-posta: tam e-posta GÖSTERİLMEZ, kısaltılır (ör. "meyr…@gmail.com").
- components/app-shell.test.tsx'te 29 test var. Davranış testleri (hangi link görünür, çıkış çağrısı, hata durumları) DEĞİŞMEZ. Sadece yapı/sınıf assertion'ları güncellenebilir, hepsini raporda listele.
- E-posta doğrulama bandı (email-verification-banner.tsx) içeriğe taşınır ama bileşenin kendisine dokunma.
```

**Sonra kendin kontrol et:** `ogrenci1` ve `org1-admin` ile giriş yap. Menüde doğru linkler var mı, aktif öğe doğru mu, çıkış çalışıyor mu bak. 375px'de çekmeceyi aç ve kapat.

---

## P4 — `/p/[slug]` public profil (15 dk, süre kalırsa)

```
/ekran 3

Ek notlar:
- Brif §6 "3. Herkese açık profil" — 720px ortalı, /v sayfasıyla aynı aile (üst bar aynı).
- Doğrulanmış deneyim kartları VerifiedSeal sm ile; her kart ilgili /v/{token}'a link (API veriyorsa).
- Mockup: 15-yetkin360-herkese-acik-profil-ziyaretci.png.
- P2'de /v için yazdığın bir parça (ör. üst bar) iki sayfada aynıysa components/ altında küçük ortak bileşene çıkarabilirsin; başka refactor yok.
```

---

## P5 — Gece kapanışı (10 dk)

```
Gece kapanışı. Kod değiştirme (kırmızı varsa düzeltmeden önce bana sor).

1. frontend/ içinde CI'ın aynısı: `npm run lint && npm run typecheck && npm run test && npm run build`. Sonucu raporla.
2. `git log --oneline origin/main..HEAD` ile bu gecenin commit'lerini listele; `git status --short` temiz mi.
3. Hepsi yeşilse `git push origin main`. (Kırmızıysa push YOK.)
4. /handoff çalıştır: HANDOFF.md'yi güncelle — bu gece biten FE maddeleri, yarım kalan (varsa, hangi dosyada), yarın Kişi A/B/C'nin ilk işi (docs/gece-plani.md "10 Ekim" tablosu), bilinen sorunlar. HANDOFF.md'yi ayrı commit'le ve push'la.
5. 5 satırlık özet ver.
```

---

## PX — Takıldım: geri al ve atla

```
Bu ekranda takıldık, vazgeçiyoruz. Commit edilmemiş değişiklikleri göster (`git status --short`, `git diff --stat`).
Sadece BU ekranın dosyalarındaki değişiklikleri `git restore <dosya>` ile geri al (dosya adlarını tek tek yaz, toplu komut yok; yeni oluşturulmuş dosyaları silmeden önce listeyi bana göster).
planfrontend.md'de ilgili FE satırına "[ ] … — 9 Ekim gece denendi, <tek cümle neden> " notu düş.
Sonra dur.
```

---

## Yarın ekip arkadaşları için (10 Ekim)

Her kişi kendi ekranı için yeni oturumda:

```
git pull --ff-only yap. Sonra:
/ekran [10 | 11 | 13 | 9 | 14 | 16 | 21]
Önce docs/gece-plani.md "10 Ekim" tablosuna bak; benim ekranlarım: [liste]. Başka kişinin dosyasına dokunma.
Bitince commit et ve `git pull --rebase && git push origin main`.
```

**Ekran 10 (`/calismalar/[id]`) için ek not (Kişi A):**

```
/ekran 10

Ek notlar:
- Demonun kalbi. Brif §6 "10. Çalışma detayı" tamamı. Mockup 06-yetkin360-calisma-detayi-appshell.png.
- Aynı klasörde 6 form bileşeni var (task, deliverable, evidence-upload, transition-actions, attestation, attestation-revoke) — her biri kendi test dosyasıyla. Bunları tek tek geçir; her biri ayrı commit olabilir.
- Durum makinesi / izin mantığı (hangi buton kime görünür) DEĞİŞMEZ.
- ChainProgress: durum → adım eşlemesi brif §2.12'de.
```
