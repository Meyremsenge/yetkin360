# Sonraki oturum promptları

Her bölüm tek başına bir oturuma yapıştırılmak üzere yazıldı. Sıra önerisi: 1 → 2 → 3 → 4 → 5.
Ortak bağlam her promptun içinde tekrar ediliyor; oturumlar birbirini görmez.

---

## Ortak bağlam (her prompta zaten gömülü — ayrıca yapıştırmana gerek yok)

> Proje: Yetkin360 (Zemin360 Hackathon). Zincir: beyan → kanıt → tanıklık → doğrulanmış deneyim.
> Çalışma dalı: `feat/landing-giris-yeniden-tasarim` (henüz main'e birleşmedi; işe bu daldan yeni bir dal açarak başla).
> Kurallar: `CLAUDE.md`, `.claude/rules/frontend.md`, `.claude/rules/security.md`. UI metinleri `frontend/messages/tr.json`'da.
> Tasarım dili ("kâğıt-mürekkep-mühür", aydınlık sürüm):
> - Zemin `--background` ≈ #FCFBF8, kart beyaz, kum `--sand` açık; vurgu tek renk çam yeşili (`success`), bekleyen aşı boyası (`warning`), hata tuğla (`destructive`). Mor/mavi/gradyan blob/glassmorphism/emoji yok.
> - Yazı: Source Serif 4 (başlık), IBM Plex Sans (arayüz), IBM Plex Mono (kod/tarih/sicil no).
> - `tailwind.config.ts` stok `slate/red/green/amber/blue` skalalarını palete eşliyor — eski sınıflar otomatik uyumlu.
> - Hazır bileşenler: `components/brand/brand-mark.tsx` (`SealMark`, `BrandLockup`), `components/brand/particle-seal.tsx` (parçacık mühür, reduced-motion'da statik), `components/page-layout.tsx` (`PageHeader` beyaz şerit, `PageBody` 1200px ortalı kap, `ChainLegend` 4 adım), `lib/ui/engagement-chain.ts` (`CHAIN_PROGRESS`, `STATUS_TONE`), `app/globals.css` içindeki `y360-*` animasyon sınıfları (`y360-rise`, `y360-stamp`, `y360-dot-grid`, `y360-step-in`…).
> - Kalite çıtası: jüri sunumunda ilk bakışta "vay" dedirtmeli; okumadan anlaşılmalı (ikon, durum rengi, "sıradaki adım" gibi ipuçları). Sahte istatistik/uydurma veri koyma; örnek veri açıkça "örnek" olarak işaretlenir.
> Doğrulama: `npm run lint`, `npm run typecheck`, `npx vitest run` (frontend); backend değişirse ilgili pytest + `pytest tests/authorization -q`. Görsel kontrol: Playwright ile ekran görüntüsü al ve kendin incele (giriş: `ogrenci1@seed.local` / seed şifresi `backend/scripts/seed.py`'de).
> Onay gerektirenler (önce sor): migration, bağımlılık, yetkilendirme mantığı, 3+ dosyalık refactor, docker/CI. Commit: dosyaları adıyla ekle, kendi dalına commit+push; merge/force yok; commit mesajında Co-Authored-By satırı yok.

---

## 1) Herkese açık profil — "vay" dedirten portfolyo sayfası (+ araştırma)

```
Yetkin360'ın herkese açık profil sayfasını (/p/[slug]) yarışmayı kazandıracak seviyede yeniden tasarlamanı istiyorum. Bu sayfa jüriye gösterilecek en önemli ekran: bir öğrencinin doğrulanmış yetkinlik portfolyosu; kurumların ve işverenlerin göreceği vitrin.

ÖNCE OKU: CLAUDE.md, .claude/rules/frontend.md, .claude/rules/security.md, docs/sayfa-tasarim-brifi.md §1–4 ve "3. Herkese açık profil" bölümü. Mevcut kod: frontend/app/p/[slug]/page.tsx (+ page.test.tsx), frontend/lib/api/public.ts, backend'de public talent endpoint'i (grep: "public/talents") ve app/services/visibility_service.py, app/services/authorization.py (scoped_public_*).
[Ortak bağlam: yukarıdaki "Ortak bağlam" bloğunu buraya yapıştır.]

AŞAMA 0 — Tasarım araştırması (kod yazmadan, 20-30 dk):
- Şu ürünlerin profil/portfolyo sayfalarını incele ve her birinden "çalabileceğimiz" 2-3 desen çıkar: LinkedIn profil, Credly/Accredible rozet sayfası, Read.cv, Polywork, GitHub profil (katkı grafiği), Behance, Europass, Apple/Stripe tarzı ürün sayfalarındaki hikâye anlatımı.
- Çıktı: docs/arastirma-public-profil.md — desen listesi, bizim için uyarlaması, alınmayacaklar ve neden (mor gradyan, sosyal ağ gürültüsü vb.). Sonra bana 2 alternatif yerleşim (ASCII taslak) sun ve onay al.

AŞAMA 1 — Veri eksiğini kapat (backend, onaylı):
- Bilinen hata: verified_experiences varsayılan PRIVATE oluşuyor ve görünürlüğü değiştiren uç yok → public profil her zaman "0 doğrulanmış deneyim" gösteriyor. Model notu: "visibility mutable (D6 change-visibility uç, future)". CLAUDE.md'ye göre verified_experiences.visibility append-only istisnası.
- Öner: PATCH /me/verified-experiences/{id}/visibility (yalnız sahibi; scoped_* üzerinden; başka kullanıcı → 404). Aynı commit'te pozitif + negatif yetkilendirme testi (tests/authorization). Bu yetkilendirme değişikliği — BAŞLAMADAN ONAY AL.
- Public profil yanıtına sayfayı zenginleştirecek ama mahremiyeti bozmayacak alanları ekle (öneri: headline, department, study_year, city, kurum adı; doğrulanmış deneyime bağlı kanıtlı yetkinlikler ve güç seviyesi; her deneyimin public doğrulama linki /v/{token}). PII: e-posta ASLA. Ayrı Pydantic response modeli.
- Frontend: Profil sayfasındaki her doğrulanmış deneyime "Herkese açık" anahtarı.
- Demo verisi: backend/scripts/seed.py'yi incele; Ayşe Yılmaz için 3-4 doğrulanmış deneyim (farklı kuruluş/tür), 6-8 kanıtlı yetkinlik, görev/çıktı/tanıklık zinciri ekleyecek şekilde zenginleştirmeyi öner (seed değişikliği — onay al). Demo için PUBLIC görünürlük.

AŞAMA 2 — Sayfa tasarımı (frontend):
Hedef bileşimler (araştırmaya göre uyarla):
- Hero: büyük isim, başlık, bölüm/şehir, kurum; sağda parçacık/mühür motifi (ParticleSeal'in küçük, sakin bir varyantı ya da statik SealMark); "Doğrulanmış yetkinlik sicili" etiketi; paylaş (link kopyala) ve QR kod (bağımlılık gerekiyorsa onay al; yoksa SVG ile basit çözüm) düğmeleri.
- Güven şeridi: "X doğrulanmış deneyim · Y kanıtlı yetkinlik · Z kuruluş tanıklığı" — gerçek veriden.
- Yetkinlik haritası: kanıtlı yetkinlikler güç seviyesine göre (mühürlü/mühürsüz ayrımı net), kategoriye göre gruplu.
- Zaman çizelgesi: her deneyim bir "sertifika kartı" — kuruluş, rol, tarih, tanıklık türü, kanıtlı yetkinlik çipleri, "Doğrulamayı gör" (/v/token) linki; kart hover'da hafif kalkış; ilk görünüşte y360-stamp mühür animasyonu (reduced-motion'da kapalı).
- "Bu kayıtlar nasıl doğrulandı?" bölümü: ChainLegend ile 4 adım.
- Boş durum: profil sahibi değilse nazik bir boş durum; asla kırık görünmesin.
- Yazdırılabilir/PDF görünümü (print CSS) — jüri "CV olarak çıktısı alınabilir mi?" diye sorarsa.
- SEO/paylaşım: <title>, description, Open Graph (isim + "Yetkin360 doğrulanmış profil").
- Mobil kusursuz.
Kabul: mevcut page.test.tsx geçer (gerekirse yeni davranışa göre güncelle ve neden güncellediğini yaz), yeni bileşenlere test, lint/typecheck temiz, 1440 ve 390 genişlikte ekran görüntüsü alıp kendin değerlendir, konsol hatası yok.
Sonunda: kısa rapor + sunumda bu sayfayı nasıl göstereceğime dair 3 cümlelik demo senaryosu.
```

---

## 2) Öğrenci profili: "Hakkımda" + sertifika / çalışma yükleme (araştırma + uygulama)

```
Öğrenci profilini (/profil) "mükemmel öğrenci profili" seviyesine taşımak istiyorum. İki eksik: (a) kişinin kendini anlatabileceği "Hakkımda" alanı, (b) çalışma dışından sertifika/çalışma yükleyebileceği bir alan.

ÖNCE OKU: CLAUDE.md, .claude/rules/*.md, yetkin360-final-analiz.md'de kanıt/evidence ve talent_profile bölümleri (grep ile bul, tamamını okuma), backend/app/models/identity.py (TalentProfile), backend/app/models/evidence.py, frontend/app/profil/*.
[Ortak bağlam bloğunu yapıştır.]

AŞAMA 0 — Araştırma: LinkedIn (About, Licenses & certifications, Featured), Europass, Credly, Handshake, Read.cv profil alanlarını incele. docs/arastirma-ogrenci-profili.md yaz: hangi alanlar gerekli, hangileri MVP dışı (CLAUDE.md "Kapsam" yasak listesine uy: AI, matching, gamification, trust score YOK).
Kritik ilke: kendi beyanı ile doğrulanmış kayıt GÖRSEL OLARAK ASLA karışmamalı. "Hakkımda" ve yüklenen sertifikalar açıkça "kendi beyanı / doğrulanmamış" etiketi taşır; doğrulanmış deneyimler mühürlü kalır.

AŞAMA 1 — Tasarım kararı ve onay: veri modeli önerisi (ör. talent_profiles.about TEXT, uzunluk CHECK; sertifika için ayrı tablo mı evidence'ın genişlemesi mi — evidence modelindeki "PRIVATE only" kısıtını ve dosya güvenliği kurallarını dikkate al). Migration ve yetkilendirme değişikliği → ONAY AL.

AŞAMA 2 — Uygulama: backend uçları (+ yetkilendirme testleri: sahibi ✓, başkası 404), dosya yükleme mevcut güvenli akışı yeniden kullanır (magic-byte, uuid ad, scan_status, imzalı URL — security.md). Frontend: Profil'de "Hakkımda" kartı (karakter sayacı), "Sertifikalar ve çalışmalar" kartı (sürükle-bırak alanı — app/calismalar/[id]/evidence-upload-form.tsx desenini kullan), public profilde "Kendi beyanı" bölümü (görünürlük ayarına bağlı).
AŞAMA 3 — Sertifika vitrini (arkadaşın PLAN 3.55 işi üzerine):
- main'de artık `certificate_checks` var (backend/app/models/certificate_check.py): öğrenci çalışma içinde Udemy/Coursera sertifikası yükler (evidence.kind=CERTIFICATE), rızasıyla OCR/QR çıkarımı yapılır (provider, credential_id, verify_url, extracted_name, name_match), nihai CONFIRMED/REJECTED kararını koordinatör verir. Bugün yalnız /calismalar/[id] içinde görünür; public profilde YOK.
- Hedef: /p/[slug]'da "Sertifikalar" bölümü — yatay kaydırmalı şerit (scroll-snap, klavyeyle gezilebilir, mobilde parmakla; ok düğmeleri masaüstünde). Her kart: sağlayıcı (Coursera/Udemy), sertifika no (Mono), "Koordinatör onaylı" rozeti, "Resmi doğrulama ↗" (verify_url). Yalnız decision=CONFIRMED olanlar. AŞAMA 2'de eklenen çalışma dışı sertifikalar da aynı şeritte ama "Kendi beyanı" etiketiyle, mühürsüz — onaylı ile asla aynı görünmez.
- Mahremiyet: kanıt dosyası PRIVATE; public'e yalnız özet alanlar çıkar (dosya, extracted_name, qr_raw_data, page_name ÇIKMAZ). Öğrenci her sertifika için ayrı "Profilde göster" rızası verir (varsayılan kapalı) → yeni alan/uç = migration + yetkilendirme değişikliği → ONAY AL. verify_url yalnız https ve sağlayıcının alan adıysa link olur (açık yönlendirme/phishing riski).
- Yer: public profilde yetkinlik haritası ile zaman çizelgesi arası; sağdaki "Sicil kartı"na sertifika sayısı satırı.

Not (yerleşim): /p/[slug] artık 1200px; solda içerik, sağda yapışkan "Sicil kartı" (QR, sayılar, linki kopyala, PDF). "Hakkımda" public profilde hero'nun altına, ana sütuna gelir; sicil kartına dokunma.

Kabul: tüm testler, alembic upgrade/downgrade, yetkilendirme paketi, ekran görüntüsüyle görsel kontrol.
```

---

## 3) Üst gezinme çubuğu (LinkedIn tarzı) — sol kenar çubuğunun yerine

```
Uygulama kabuğunu (frontend/components/app-shell.tsx) sol kenar çubuğundan üst gezinme çubuğuna taşımak istiyorum. Gerekçe: öğrencide yalnız 2-3 menü öğesi var; 248px'lik sol bar boş duruyor ve içerik daralıyor. Keşfet de üst barda yer alacak.

ÖNCE OKU: CLAUDE.md, .claude/rules/frontend.md, docs/sayfa-tasarim-brifi.md §5 (AppShell), components/app-shell.tsx ve app-shell.test.tsx (30 test — davranış sözleşmesi: yükleme iskeleti, oturum hatası ekranları, e-posta doğrulama bandı, çıkış hatası, mobil çekmece odak tuzağı, e-posta maskeleme).
[Ortak bağlam bloğunu yapıştır.]

Tasarım:
- Masaüstü (≥1024): 64px beyaz üst bar, alt çizgi. Sol: BrandLockup. Orta: birincil menü (Çalışmalarım, Profil, Keşfet — Keşfet sayfası yoksa gizli/feature flag), aktif öğe altında 2px çam çizgisi. Sağ: "Profilimi gör ↗" (public slug varsa), avatar menüsü (ad + rol başlığı, Çıkış).
- Kuruluş/kurum üyeleri: birden fazla varlığa üye olabilir → üst barda bağlam seçici (ör. "Lale Yazılım A.Ş. ▾" açılır listesi: kuruluşlar, kurumlar, admin ekranları). Rol başına menü öğeleri bu seçiciden gelir.
- Mobil (<1024): mevcut hamburger + çekmece korunur (odak tuzağı testi), ya da alt sekme çubuğu — öner, sor.
- Sayfa iskeleti: PageHeader beyaz şeridi üst barın hemen altında; içerik 1200px ortalı (components/page-layout.tsx).
Bu 3+ dosyalık bir refactor ve testlerin bir kısmı DOM yapısını sabitliyor → önce plan + etkilenecek testlerin listesi, ONAY AL, sonra uygula. Test davranışlarını koru; yalnız yapı sabitleyen beklentileri güncelle ve her güncellemeyi gerekçelendir.
Kabul: tüm frontend testleri, lint/typecheck, öğrenci / kuruluş / kurum / admin hesaplarıyla 1440 ve 390 genişlikte ekran görüntüsü.
```

---

## 4) Keşfet — kurumlar öğrencileri, öğrenciler kurumları görsün

```
"Keşfet" özelliğini tasarlayıp uygulamak istiyorum: kurum ve kuruluşlar herkese açık (PUBLIC) öğrenci profillerini; öğrenciler de kuruluş/kurumları bulup inceleyebilsin. Üst gezinme çubuğunda "Keşfet" öğesi olacak (3. prompt yapıldıysa).

ÖNCE OKU: CLAUDE.md (özellikle Kapsam: matching motoru, AI, Elasticsearch, pgvector YASAK — bu bir DİZİN/ARAMA, eşleştirme değil), .claude/rules/security.md, final analizde visibility/görünürlük ve organizations bölümleri (grep), backend GET /organizations uç (PLAN 3.52-3.53 commit'leri), app/services/authorization.py.
[Ortak bağlam bloğunu yapıştır.]

AŞAMA 0 — Kapsam ve mahremiyet tasarımı (kod yok): kim kimi görür? Öneri: yalnız visibility=PUBLIC profiller (ve INSTITUTION/ORGANIZATIONS seviyeleri için kuralları netleştir); arama = PostgreSQL ILIKE/trigram yeterli mi (yeni bağımlılık yok); sayfalama; rate limit; e-posta asla dönmez. docs/kesfet-tasarim.md yaz ve ONAY AL.
AŞAMA 1 — Backend: GET /discover/talents (filtre: yetkinlik, bölüm, şehir, kurum), GET /discover/organizations. Her uç için pozitif + negatif yetkilendirme testi aynı commit'te; 404 felsefesi.
AŞAMA 2 — Frontend /kesfet: üstte arama + filtre çipleri, sekme (Öğrenciler / Kuruluşlar), kart ızgarası (avatar, isim, başlık, mühürlü yetkinlik çipleri, doğrulanmış deneyim sayısı), boş/yükleme/hata durumları, kartta "Profili gör" (public /p/slug). Animasyon: kart girişinde y360-step-in, reduced-motion kapalı.
Kabul: tüm testler + authorization paketi + ekran görüntüleri.
```

---

## 5) Kurum ve kuruluş panelleri — aynı tasarım dili

```
Öğrenci ekranlarında kurduğumuz tasarım dilini kuruluş ve kurum panellerine taşımak istiyorum: /kurulus/[id]/panel, /kurulus/olustur, /kurum/[id]/panel (en büyük ekran), /kurum/olustur, /kurum/[id]/baglan, değerlendirme formu /calismalar/[id]/degerlendirme, admin ekranları.

ÖNCE OKU: docs/sayfa-tasarim-brifi.md ilgili sayfa bölümleri (14–20), referans olarak yeniden tasarlanmış ekranlar: app/calismalar/page.tsx, app/calismalar/[id]/page.tsx, app/profil/page.tsx, components/page-layout.tsx.
[Ortak bağlam bloğunu yapıştır.]

Her ekran için: PageHeader (eyebrow + başlık + tek cümlelik "bu sayfa ne işe yarar" + ana aksiyon), gerçek veriden özet kartları (ikonlu, ton renkli), tablo/listelerde durum rozetleri ve "sıradaki adım" ipuçları, boş durumlar (ne yapılacağını söyler), sağda yapışkan işlem kartı. Kurum paneli için: öğrenci listesi + doğrulanmış deneyim sayıları + bekleyen bağlanma talepleri bir bakışta.
Ham İngilizce enum gösterme (PLANNED gibi) — tr.json'a etiket ekle. Aynı veriyi iki yerde tekrar etme.
Ekran ekran ilerle; her ekran ayrı commit. Testler davranışı sabitliyorsa koru; yalnız görsel/metin sabitleyen beklentileri gerekçeyle güncelle.
Kabul: tüm testler, lint/typecheck, her ekran için 1440/390 ekran görüntüsü.
```
