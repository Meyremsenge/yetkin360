# Yetkin360 Final Engineering & Product Analysis

> Bu rapor, `yetkin360-on-arastirma.md` dokümanından bağımsız olarak hazırlanmış, sonrasında o dokümanla karşılaştırılmış nihai mühendislik ve ürün analizidir.
> Tarih: 2026-09-15
> **Bağlam: Zemin360 Hackathon (GİRVAK × İstanbul Kalkınma Ajansı × İstanbul Bilgi Üniversitesi).**

---

## 0. Yarışma Bağlamı — Her Şeyi Belirleyen Kısıtlar

Bu rapor önce bağımsız bir ürün analizi olarak yazıldı. Sonrasında ortaya çıktı ki proje bir **hackathon şartnamesine** bağlı. Bu, raporun bazı sonuçlarını doğrudan değiştiriyor. Bu bölüm o farkı kayıt altına alır.

### 0.1 Şartnamenin dayattığı kısıtlar

| Kısıt | Değer | Rapora etkisi |
|---|---|---|
| **6 problem alanı** | Şartnamede tanımlı, "bir veya birkaçını" çözmek serbest | Ön araştırmadaki 6 problem bir **hipotez değil, verilen girdi.** Eleştirilemez, sadece hangilerine odaklanılacağı seçilebilir |
| **Açık kaynak zorunlu** | Platform açık kaynak olacak | Lisans, repo yapısı, bağımlılık lisansları kararı gerekiyor (raporun ilk halinde yoktu) |
| **Tek web servisi** | Tek platform | Modüler monolit kararını **doğruluyor** |
| **Takvim** | 18 Eylül – 9 Ekim uzaktan (3 hafta), 9-11 Ekim İstanbul'da yüz yüze | **24 haftalık plan geçersiz.** Bkz. §35 |
| **Ekip** | 1-3 kişi, 18-30 yaş | Tek geliştirici varsayımı geçerli olabilir; kapsam buna göre |
| **Ödül** | 200.000 TL geliştirme bütçesi (hibe değil) + 4 ay geliştirme sözleşmesi + pilot + kullanıcı eğitimi | Jüri **demo değil, 4 ay sürdürülebilir temel** arıyor |
| **Fiziksel katılım** | İstanbul, 9-11 Ekim zorunlu | Son 3 gün sunum ve son rötuş |

### 0.2 Bu, raporun hangi sonuçlarını değiştiriyor?

**Değişen 1 — Üniversite modeline tam geçiş artık doğrudan önerilmiyor.**

Raporun orijinal ana tezi: "marketplace'i bırakın, üniversite staj süreci yönetimine geçin." Hackathon bağlamında bu **riskli**, çünkü jüri 6 başlığa bakıyor ve tam geçiş 3. (eşleştirme) ve 4. (yaşayan ağ) başlıklarını MVP'den çıkarıyordu.

**Revize edilmiş öneri: Konumlandırmayı değiştirmeyin, cold start cevabı olarak kullanın.**

Ürün yine Yetkin360'tır ve 6 başlığa hitap eder. Ancak "nasıl başlayacaksınız, ilk kullanıcıyı nereden bulacaksınız?" sorusuna — ki jürinin kesin soracağı ve marketplace kurgusunun en zayıf noktası olan soru — cevabınız şudur:

> "Açık marketplace'e sıfırdan başlamıyoruz. Üniversite staj/bitirme projesi süreciyle başlıyoruz: orada kurum da öğrenci de zaten var, eşleşme zaten olmuş, değerlendirme zaten mevzuat gereği zorunlu. Doğrulanmış deneyim stoğunu böyle biriktirip, marketplace katmanını arz dolduktan sonra açıyoruz."

Bu, §26.2'deki 3 aşamalı stratejinin ta kendisidir — ama ürünü değiştirmeden, **giriş stratejisi (go-to-market)** olarak sunulur. Jüri açısından bu bir zayıflık değil, güçlü bir cevaptır: cold start'ı düşünmüş tek takım siz olursunuz.

**Değişen 2 — Takvim.**
§35'teki 24 haftalık plan, 4 aylık geliştirme sözleşmesinin planı olarak geçerli kalır. Hackathon için ayrı bir 3 haftalık plan gerekiyor (§35.3).

**Değişen 3 — Açık kaynak.**
Raporun ilk halinde hiç ele alınmamıştı. Etkileri: lisans seçimi (AGPL vs MIT vs Apache-2.0), bağımlılıkların lisans uyumu, sırların repoda olmaması (zaten §16.5'te var ama artık kritik), README ve katkı rehberi jürinin göreceği çıktılar arasında.

**Değişen 4 — Jürinin baktığı şey ile ürünün gerçek değeri farklı olabilir.**
Hackathon'da 3 haftada gösterilebilecek şey ile 4 ayda inşa edilecek şey aynı değildir. Bu rapor ikisini ayırıyor: §35.3 hackathon kapsamı, §27 gerçek MVP kapsamı, §35.2 4 aylık plan.

### 0.3 6 problem alanına karşı ürünün konumu

| # | Şartname başlığı | Ürünün cevabı | Hackathon'da gösterilecek mi? |
|---|---|---|---|
| 1 | Genç yeteneklerin görünürlüğü ve fırsata erişimi | Public profil + doğrulama linki + kanıt dökümü | ✅ **Evet — güçlü** |
| 2 | Profil/portfolyo doğruluğu | Attestation modeli, iki eksenli doğrulama, provenance ayrımı | ✅ **Evet — ürünün en güçlü tarafı** |
| 3 | Kurum-kişi yetkinlik eşleştirmesi | Deterministik, açıklanabilir eşleştirme (AI değil) | ⚠️ **Sınırlı** — bkz. §35.3 |
| 4 | Bağlantı ötesinde yaşayan ağ | Ağ, tamamlanan işbirliklerinden doğar (sosyal akış değil) | ⚠️ **Anlatılır, kod olarak sınırlı** |
| 5 | Kurumların ihtiyacını yapılandırması | Yapılandırılmış Need formu | ⚠️ **Basit hâliyle** |
| 6 | Şeffaf işbirliği takibi | Engagement durum makinesi + görev/çıktı + audit | ✅ **Evet — güçlü** |

**Strateji: 1, 2 ve 6'yı derinlemesine yapın; 3, 4, 5'i çalışır ama sade tutun.** Şartname "bir veya birkaç" dediği için altısını da yüzeysel yapmak, üçünü derin yapmaktan daha kötü bir sonuç verir. Derinlik, 2. ve 6. başlıkta gösterilir — çünkü orası rakiplerin olmadığı yer.

---

## 1. Executive Summary

**En kısa özet:** Ürünün temel içgörüsü (beyan yerine kanıt) doğru. Ancak ön araştırma dokümanının kurguladığı ürün — "yetenek keşfi + eşleştirme marketplace'i" — yanlış problem üzerine kurulu ve neredeyse kesin başarısız olur. Doğru ürün, aynı veri modelinin **marketplace olmayan** bir kullanımıdır.

Üç kritik bulgu:

**1. Marketplace tarafı ölür.** Yetkin360 iki taraflı bir marketplace olarak kurgulanmış (yetenek + kurum). İki taraflı marketplace'lerin çoğunluğu 1-3. yıllarda likidite sağlayamadığı için çöküyor; talent marketplace'lerde kategori başına yoğunluk eşiği tutturmak gerekiyor. Tek geliştirici + sıfır bütçeyle Türkiye'de hem kurum hem öğrenci tarafını aynı anda doldurmak gerçekçi değil. Kariyer.net ve 1.200+ kurumsal partnerli Youthall zaten kurum tarafını tutuyor.

**2. "Doğrulanmış yetkinlik" pazarının alıcısı zayıf.** Skills-based hiring söylemi ile pratiği arasındaki uçurum ölçülmüş durumda: diploma şartını kaldırdığını açıklayan şirketlerin %45'i hiçbir işe alım pratiğini değiştirmedi, bazı büyük firmalarda diplomasız işe alım oranı 1/700'ün altında kaldı. Daha da çarpıcısı: **LinkedIn, Skill Assessments ürününü kapattı ve rozetleri profillerden sildi.** Yani dünyanın en büyük profesyonel ağı, "platform içi yetkinlik doğrulama rozeti" fikrini deneyip terk etti. Bu, Yetkin360'ın ana değer önerisine karşı en güçlü kanıt ve dokümanda hiç geçmiyor.

**3. Ama gerçek ve savunulabilir bir problem var — sadece dokümanın işaret ettiği yerde değil.** Türkiye'de üniversitelerin **zorunlu staj ve bitirme projesi** süreçleri hâlâ büyük ölçüde kağıt/Excel/e-posta ile yürüyor. Burada kurum zaten var (staj yeri), yetenek zaten var (zorunlu stajyer öğrenci), eşleşme zaten olmuş, ve değerlendirme **zaten yasal olarak zorunlu** (staj defteri, işveren değerlendirme formu). Yani cold start problemi yok, evaluation motivasyonu yok değil — mevzuat gereği zorunlu. Ve o süreç bugün yapılandırılmamış veri üretiyor, dolayısıyla kanıt kayboluyor.

**Nihai öneri (hackathon bağlamına göre revize — bkz. §0.2):** Ürünü Yetkin360 olarak, 6 başlığa hitap eden hâlinde tutun. Ancak **giriş stratejiniz** açık marketplace olmasın: **üniversite staj/bitirme projesi sürecinden başlayın.** Orada kurum da öğrenci de zaten var, eşleşme zaten olmuş, değerlendirme zaten mevzuat gereği zorunlu. Doğrulanmış deneyim stoğu böyle birikir; marketplace katmanı arz dolduktan sonra açılır. Bu, cold start sorusuna sahip olduğunuz tek güçlü cevaptır ve jürinin soracağı en kritik soruyu kapatır.

Uzun vadede (4 aylık geliştirme sözleşmesi ve sonrası) ödeyen müşteri büyük olasılıkla üniversite kariyer merkezi/bölümüdür — öğrenci veya KOBİ değil.

**Teknoloji tarafında** dokümanın önerileri büyük ölçüde makul; asıl sorun teknoloji seçimi değil, kapsam. Dokümandaki 8 haftalık MVP planı tek geliştirici için gerçekçi değil — içerdiği iş gerçekçi olarak 5-7 aylık. Hackathon'un verdiği süre ise 3 hafta + 3 gün; bu ayrım §35'te üç ayrı plan olarak ele alınıyor. Önerilen stack: FastAPI + PostgreSQL + Next.js, modüler monolit, tek VPS. Redis/Elasticsearch/pgvector/Celery/Kubernetes/blockchain MVP'den çıkarılmalı. AI, MVP'de sadece tek bir yerde (CV parsing, insan onaylı) kullanılmalı.

---

## 2. Problem Definition

### 2.1 Dokümanın tanımladığı problem

> "Gençlerin becerileri CV'de beyan olarak kalıyor; kurum bunun gerçek olup olmadığını bilemiyor."

Bu tanım **doğru ama eksik ve yanıltıcı.** Eksik olduğu yer: problemi yaşayanın kim olduğu ve o kişinin bunu çözmek için para/emek harcamaya razı olup olmadığı belirtilmemiş.

### 2.2 Problemi katman katman ayırmak

Dokümanın "beyan vs kanıt" çerçevesi, aslında üç farklı problemi tek problem gibi gösteriyor:

**Problem A — Doğrulama problemi (verification):** "Bu kişi gerçekten bunu yaptı mı?"

**Problem B — Sinyal problemi (signaling):** "Bu kişinin bunu yapmış olması, benim işimi yapabileceği anlamına mı geliyor?"

**Problem C — Keşif problemi (discovery):** "Bu profildeki kişiyi nasıl bulurum?"

Doküman baştan sona Problem A'yı çözmeye odaklanıyor. Fakat:

- **Kurumlar için asıl acı Problem B'dir, A değil.** Bir işveren, adayın "3 ay Python projesi yaptım" beyanının yalan olmasından değil, doğru olsa bile bunun işe yarar bir sinyal olmamasından muzdarip. Zaten öğrenci CV'lerinde yalan söylemek yaygın bir kriz değil; asıl kriz herkesin CV'sinin birbirinin aynı olması ve ayırt edici sinyal içermemesi.
- **Problem C'yi zaten LinkedIn/Kariyer.net çözüyor** ve ölçek avantajı orada.

**Sonuç: Ürünün ana iddiası (doğrulama) müşterinin en çok acı duyduğu yer değil.** Bu, raporun en önemli eleştirilerinden biri.

### 2.3 Problem gerçekten var mı? Kanıt.

Doğrulama probleminin var olduğuna dair kanıt zayıf değil ama **ürün kararı için yeterli değil:**

- İstihdam doğrulamalarında tespit edilen tutarsızlıklar %44 artmış; AI üretimi CV, sahte referans ve uydurma istihdam kayıtları yaygınlaşıyor. Yani sorun **var.**
- **Ama** bu sorun ağırlıklı olarak deneyimli/orta-kıdem işe alımda ve arka plan kontrolü (background check) endüstrisinde yaşanıyor — yani zaten ödeme yapan bir sektör var ve o sektör öğrenci stajyerine bakmıyor. Bir stajyer için kimse background check yaptırmıyor, çünkü riski düşük.
- Skills-based hiring'in pratikte uygulanmadığına dair veriler (Burning Glass/Harvard: %45 hiçbir şey değiştirmedi, bazı firmalarda 1/700'ün altında etki) gösteriyor ki **kurumlar "daha iyi yetkinlik sinyali" için davranış değiştirmeye isteksiz.**
- **En sert kanıt:** LinkedIn, tam olarak bu fikrin (platform içi yetkinlik doğrulama rozeti) ürününü kapattı. Milyarlarca dolarlık dağıtım gücüne sahip bir şirket, bu özelliğin kullanıcı ve işveren tarafında yeterli değer üretmediğine karar verdi.

**Dürüst değerlendirme: "Kurumlara doğrulanmış yetkinlik satmak" hipotezi, mevcut kanıtlar ışığında zayıf bir hipotezdir.** Doküman bu riski hiç test etmiyor; 119 bölüm boyunca doğrulamanın değerli olduğunu varsayıyor.

### 2.4 Problemi kim yaşıyor? (Aktör bazında)

**Genç yetenek (öğrenci):**
- Gerçek acı: "Deneyim istiyorlar ama deneyim kazanacak yer bulamıyorum." Bu bir **erişim** problemi, doğrulama problemi değil.
- İkincil acı: "Yaptığım şeyleri anlatacak düzgün bir yer yok; GitHub'ım dağınık, CV'm bir sayfa."
- **Yaşamadığı problem:** "Yetkinliğimi doğrulayamıyorum." Öğrenci bunu bir problem olarak deneyimlemiyor, çünkü doğrulamanın eksikliğinin ona ne kaybettirdiğini göremiyor.
- **Kritik sonuç:** Öğrenci, sırf "doğrulanmış profil" için 40 dakika harcayıp kanıt yüklemez. Ekstrinsik bir zorlayıcı gerekir (staj zorunluluğu, ders notu, üniversite şartı).

**Kurum (KOBİ/startup):**
- Gerçek acı: "Stajyer/junior alıyorum, işe yaramıyor, 2 ayda ayrılıyor, eğitim maliyetim boşa gidiyor."
- İkincil acı: "150 başvuru geldi, hepsi aynı, eleyecek vaktim yok."
- **Yaşamadığı problem:** "Adayın beyanının doğruluğunu bilemiyorum." Stajyer seviyesinde risk düşük; yanlış işe alımın maliyeti düşük olduğu için doğrulamaya yatırım yapmaz.
- **Kritik sonuç:** Kurum, doğrulama için para ödemez. **Ödeme yapacağı şey eleme/zaman tasarrufu veya hazır yetenek havuzudur.**

**Üniversite / kariyer merkezi / bölüm (dokümanın neredeyse atladığı aktör):**
- Gerçek acı: **"500 öğrencinin zorunlu staj sürecini Excel ve e-posta ile yönetiyorum."** Staj defteri topluyorum, işveren değerlendirme formlarını kovalıyorum, akreditasyon (MÜDEK vb.) için program çıktısı kanıtı üretmem gerekiyor ve elimde yapılandırılmış veri yok.
- Bu **akut, tekrarlayan, ölçülebilir ve bütçesi olan** bir problemdir.
- **Bu aktörün doğrulama ihtiyacı gerçek ve zorunludur** — çünkü kurumun öğrenci hakkındaki değerlendirmesi zaten resmi bir belgedir.

**Doküman bu aktörü 84. ve 86. bölümlerde bir "kanal" ve "gelir modeli" olarak geçiştiriyor. Bu, raporumun en büyük ayrışma noktası: üniversite bir kanal değil, birincil müşteridir.**

### 2.5 Mevcut yöntemler neden yeterli değil?

| Mevcut yöntem | Neden yetersiz | Ama neden hâlâ kullanılıyor |
|---|---|---|
| CV / PDF | Yapılandırılmamış, doğrulanamaz, statik | Evrensel, sıfır sürtünme, herkes kabul ediyor |
| LinkedIn | Doğrulama yok, herkes "uzman" | Ağ etkisi, dağıtım, işveren zaten orada |
| GitHub | Sadece kod; ekip katkısı/rol görünmez, teknik olmayan beceri yok | Kod için en güçlü kanıt, gerçekten doğrulanabilir |
| Referans mektubu | Ölçeklenmez, sahtesi kolay, standart değil | Güven yüksek, kişisel |
| Staj defteri (kağıt) | Yapılandırılmamış, aranamaz, kaybolur, kanıt üretmez | Yasal zorunluluk, yerleşik |
| Sertifika (Coursera vb.) | İzleme kanıtı, yapma kanıtı değil | Ucuz, hızlı, tanınır |

**En önemli satır:** Kağıt staj defteri. Bu, doğrulamanın **zaten yapıldığı** ama verinin **çöpe gittiği** tek yer. Burası ürünün doğal giriş noktasıdır.

### 2.6 Gerçek Job To Be Done

Dokümanın örtük JTBD'si: *"Yetkinliğimi kanıtla, kurum beni bulsun."* — Bu bir JTBD değil, bir ürün özelliği tarifi. Kimse sabah kalkıp "yetkinliğimi kanıtlamalıyım" demez.

Gerçek JTBD'ler:

- **Öğrenci:** *"Mezun olduğumda elimde, başkasının onayladığı, somut bir iş geçmişi olsun ki ilk işimi bulurken 'deneyimsiz' diye elenmeyeyim."*
- **Kurum:** *"Bana zaman kaybettirmeyecek, ilk günden iş yapabilecek bir junior bul; ve aldığım stajyerin sürecini yönetmek bana ek yük olmasın."*
- **Üniversite:** *"Staj ve proje süreçlerini yönetsem, öğrencinin gerçekten ne öğrendiğini kanıtlayabilsem ve akreditasyon dosyamı bu veriyle üretebilsem."*

**Ürünün ana JTBD'si üniversiteninki olmalı; diğer ikisi bunun üzerine bedava gelir.**

### 2.7 Ürün yanlış problem üzerine mi kurulmuş?

**Kısmen evet.** Açıkça söylüyorum:

- **Doğru olan:** Kanıt-merkezli veri modeli, iş birliğinden otomatik doğrulanmış deneyim üretme döngüsü. Bu gerçekten özgün ve değerli bir mühendislik fikri.
- **Yanlış olan:** Bu modelin bir **açık marketplace** olarak paketlenmesi. Marketplace kurgusu, ürünün en güçlü fikrini (doğrulama döngüsü) hiç çalışamayacağı bir bağlama (cold start, likidite, LinkedIn rekabeti) yerleştiriyor.
- **Eksik olan:** Doğrulama döngüsünün **zaten zorunlu olduğu** bir bağlam arayışı. O bağlam üniversite staj/proje sürecidir.

---

## 3. Target Users

### 3.1 Birincil müşteri (ödeyen): Üniversite bölümü / kariyer merkezi

- **Profil:** 200-1500 öğrencili mühendislik/MYO bölümü, staj koordinatörü (genelde 1 akademisyen + 1 memur).
- **Acı:** Excel, e-posta, kağıt defter, akreditasyon kanıt üretimi.
- **Bütçe:** Var (yazılım/hizmet alımı kalemleri, döner sermaye).
- **Satın alma:** Tek karar verici, cold start yok, bir "evet" 400 öğrenci getirir.
- **Neden kritik:** Bu müşteri tek başına hem talent tarafını (öğrenciler zorunlu kullanır) hem kurum tarafını (staj yerleri davet edilir) platforma sokar. **Cold start problemi bu segmentte yapısal olarak yoktur.**

### 3.2 Birincil kullanıcı (yoğunluk): Öğrenci

- 3-4. sınıf mühendislik/bilgisayar öğrencisi, zorunlu staj yapıyor.
- Platforma **gönüllü gelmez, zorunlu gelir.** Bu bir zayıflık değil, cold start çözümüdür.
- Kalıcı değer: mezuniyette elinde taşınabilir, doğrulanmış bir çalışma geçmişi.

### 3.3 İkincil kullanıcı: Staj veren kurum (KOBİ/startup)

- Zaten stajyer alıyor, zaten değerlendirme formu dolduruyor.
- Platformda yapacağı iş: formu kağıt yerine ekranda doldurmak. **Ek yük değil, yük azaltma.**
- Ödeme yapmaz (MVP'de). Sonradan "yetenek havuzuna erişim" için ödeyebilir.

### 3.4 Dokümanın rol listesi hakkında

Doküman 67. bölümde 5 rol öneriyor (Talent, Organization, Mentor/Evaluator, Org Admin, Platform Admin). **Değerlendirme: Değiştir.**

MVP'de gerekli roller:
- `STUDENT` (talent)
- `ORG_MEMBER` (staj yeri yetkilisi — aynı zamanda değerlendirici)
- `ORG_ADMIN` (kurum üyelerini yönetir)
- `INSTITUTION_COORDINATOR` (**dokümanda yok — en önemli rol**)
- `PLATFORM_ADMIN`

`Mentor` ve `Evaluator` ayrı roller olarak gereksiz — bunlar `ORG_MEMBER`'ın bir yetkisidir, ayrı rol değil. Rol sayısını artırmak authorization test matrisini kombinatoryal olarak büyütür ve güvenlik riski yaratır.

---

## 4. User Journeys

### 4.1 Öğrenci (Talent) — uçtan uca

```
Üniversite davetiyle kayıt (e-posta domain doğrulaması)
   ↓
Profil: bölüm, sınıf, temel bilgiler (2 dk — uzun onboarding YOK)
   ↓
Staj başvurusu / staj yeri bildirimi (koordinatör onayı)
   ↓ [Collaboration OLUŞUR — matching gerekmeden]
Staj süreci: haftalık çalışma kaydı + görev/çıktı ekleme
   ↓  (kağıt staj defterinin yerine geçer — asıl değer burada)
Çıktı yükleme (kod linki, rapor, ekran görüntüsü, doküman)
   ↓
Staj biter → kurum değerlendirme formunu doldurur (zorunlu, zaten yapıyor)
   ↓
Koordinatör onaylar → VERIFIED EXPERIENCE oluşur
   ↓
Yetkinlikler otomatik türetilir: kanıt zinciri + kurum onayı ile
   ↓
Profil güçlenir → paylaşılabilir public doğrulama linki
```

**Değer nerede oluşuyor:**
- Öğrenci için **asıl değer 5. adımda** (staj defteri yükünün azalması), doğrulanmış profilde değil. Doğrulanmış profil **bedava gelen yan üründür.** Ürünü bu şekilde satmak, "yetkinliğini kanıtla" demekten çok daha kolaydır.
- Dokümanın journey'i (bölüm 78) "Discover opportunities → Match" adımını merkeze koyuyor. **Bu adım MVP'den çıkarılmalı**; çünkü staj yeri bulma zaten platform dışında oluyor ve bunu çözmek marketplace kurmak demek.

### 4.2 Kurum (Organization) — uçtan uca

```
Üniversiteden davet linki ile kayıt (kurum e-posta domain doğrulaması)
   ↓
Kurum profili (vergi no / MERSİS — doğrulama için)
   ↓
Stajyerini platformda görür (eşleşme zaten gerçekleşmiş)
   ↓
Görev tanımlar / öğrencinin kayıtlarını onaylar (hafif — Jira değil)
   ↓
Çıktıları görür
   ↓
Staj sonu değerlendirme formu (yapılandırılmış: yetkinlik bazlı + davranışsal)
   ↓
İmzalar → Verified Experience üretilir
```

**Değer nerede:** Kurum için değer, **kağıt form doldurup imzalayıp kargolamak yerine 5 dakikada ekranda bitirmek.** Yetenek keşfi değil.

### 4.3 Koordinatör (Institution) — dokümanda hiç yok

```
Kurum/öğrenci eşleşmelerini onaylar
   ↓
Dashboard: 400 öğrenci, kimin stajı devam ediyor/bitti/formu eksik
   ↓
Eksik değerlendirmeleri tek tıkla hatırlatır (bugün e-posta ile elle yapıyor)
   ↓
Staj defterini dijital olarak onaylar
   ↓
Dönem sonu: yetkinlik bazlı agregat rapor → akreditasyon dosyası
```

**Ürünün parasını kazandıran ekran budur.** Dokümanda hiç tasarlanmamış.

---

## 5. Competitive Analysis

Doküman 111. bölümde 16 rakip listeliyor ama hiçbirini analiz etmiyor; sadece "araştırılmalı" diyor. Analiz:

### 5.1 Kategori kategori

| Platform | Çözdüğü problem | Doğrulama yöntemi | Matching | Gelir | Kullanıcıyı tutan şey |
|---|---|---|---|---|---|
| **LinkedIn** | Profesyonel kimlik + ağ | **Yok** (endorsement gürültü; Skill Assessments **kapatıldı**) | Recruiter arama + ilan | Recruiter aboneliği, reklam | Ağ etkisi (herkes orada) |
| **GitHub** | Kod barındırma | **Gerçek ve güçlü** (commit geçmişi, kriptografik) | Yok | Geliştirici aboneliği | İş aracı — her gün kullanılıyor |
| **Handshake** | ABD üniversite-işveren köprüsü | Üniversite kimliği (kurumsal) | İlan + öneri | Üniversite + işveren ücreti | **Üniversite entegrasyonu (zorunlu kanal)** |
| **Wellfound** | Startup işe alım | Hafif | İlan + filtre | İşveren ücreti | Startup nişi |
| **Upwork/Fiverr** | Freelance iş | **İş geçmişi + para akışı** (en güçlü doğrulama) | Arama + teklif | Komisyon (%10-20) | Gelir — geçim kaynağı |
| **Hired** | Tersine işe alım | Ön eleme + vetting | Kürasyon | İşveren ücreti | Kürasyonlu talep |
| **Credly** | Dijital rozet altyapısı | **İhraççıya devrediyor** (kendi doğrulamıyor) | Yok | **İhraççı kurumlar öder** | Rozet taşınabilirliği |
| **Coursera** | Öğrenme | Sınav/ödev (izleme kanıtı) | Yok | Öğrenci + kurum aboneliği | İçerik |
| **Kaggle** | ML yarışmaları | **Nesnel skor (çok güçlü)** | Yok | Google içi | Sıralama/prestij |
| **Devpost** | Hackathon | Etkinlik hakemliği | Yok | Etkinlik sponsoru | Etkinlikler |
| **ATS (Workday, Greenhouse)** | Başvuru yönetimi | Yok | Anahtar kelime eleme | Kurumsal SaaS | **Kurumun iş akışına gömülü** |
| **Kariyer.net** | TR iş ilanı | Yok | İlan + arama | İşveren ilan ücreti | TR'de ölçek |
| **Youthall** | TR genç yetenek | Yok | Program/etkinlik | Kurumsal partnerlik | 1.200+ kurumsal partner |
| **Toptalent.co** | TR öğrenci kariyer | Yok | İlan | Kurumsal | Üniversite topluluk ağı |

### 5.2 Kalıpları okumak — asıl öğretici kısım

**Kalıp 1: Doğrulamanın gerçekten işe yaradığı her yerde, doğrulama bir yan üründür.**
GitHub commit'i doğrulamak için var olmadı; kod barındırmak için var oldu. Upwork iş geçmişi, para akışının yan ürünü. Kaggle sıralaması, yarışmanın yan ürünü. **Doğrulamayı ana ürün yapan hiçbir platform büyüyemedi.** Credly bile doğrulamıyor, sadece taşıyor.

→ **Yetkin360 için çıkarım:** Doğrulamayı ana ürün yapmayın. Staj/proje sürecini yönetin; doğrulama yan ürün olsun. Bu, raporun en önemli stratejik önerisidir.

**Kalıp 2: Kurumların ödediği şey doğrulama değil, erişim ve iş akışıdır.**
Hiçbir satırda "kurum doğrulama için ödüyor" yok. Ödeme: aday erişimi (LinkedIn Recruiter), iş akışı (ATS), sonuç (Upwork komisyonu) veya **kendi rozetini dağıtmak (Credly — ihraççı öder)**.

→ **Çıkarım:** Yetkin360'ın parası "kuruma doğrulanmış aday satmak"tan değil, **üniversiteye iş akışı satmak**tan gelir. Credly modeli buna en yakın: kanıtı üreten kurum öder.

**Kalıp 3: Üniversite kanalı işe yarıyor — Handshake bunu kanıtladı.**
Handshake, LinkedIn'in gölgesinde, tam olarak üniversite entegrasyonu üzerinden büyüdü. Öğrenci oraya gelir çünkü üniversitesi oradadır.

→ **Çıkarım:** Türkiye'de Handshake'in üniversite-kurumsal katmanı yok; ama Yetkin360'ın ayrışması "Handshake klonu" değil, **staj sürecinin kendisini yönetip kanıt üretmek** olmalı (Handshake bunu yapmıyor — o da bir ilan panosu).

**Kalıp 4: LinkedIn'in Skill Assessments'ı kapatması bir uyarıdır.**
LinkedIn test tabanlı yetkinlik doğrulamayı denedi ve kapattı. Bugünkü yaklaşımı: yetkinliği bir işe/projeye/eğitime **etiketlemek** — yani zayıf bağlamlandırma, doğrulama değil.

→ **Çıkarım:** Test/assessment tabanlı skill verification'ı MVP'den tamamen çıkarın. Dokümanın "Level 4: Assessment" seviyesi (bölüm 7) gerçek dünyada test edilmiş ve başarısız olmuş bir yaklaşımdır.

### 5.3 "Bir kurum neden LinkedIn yerine Yetkin360 kullanmalı?"

**Dürüst cevap: Açık marketplace kurgusunda kullanmaz. Bu soruya güçlü bir cevabım yok ve doküman da veremiyor.**

Bunu net söylüyorum çünkü dokümanın 112. bölümü tam olarak bunu istiyor. LinkedIn'in ağ etkisi, dağıtımı ve alışkanlık avantajı, "bizde kanıt var" argümanıyla aşılamaz. Kurum LinkedIn'i bırakmaz; Yetkin360'ı **LinkedIn'e ek olarak** ve **başka bir iş için** kullanır.

**Cevap verilebilir soru şudur:** *"Bir üniversite neden Excel yerine Yetkin360 kullanmalı?"*
Cevap net: Çünkü 400 öğrencinin staj sürecini Excel'de yönetmek berbat, akreditasyon kanıtı üretmiyor ve koordinatörün her dönem 3 haftasını yiyor. Bu soruya **güçlü cevap var.**

**Stratejik sonuç: Ürünün ilk sorusu yanlış soruydu. Doğru soruyu sorduğunuzda ürün savunulabilir hale geliyor.**

---

## 6. Product Differentiation

### 6.1 Savunulabilir farklılaşma

**Değil:** "AI ile eşleştiriyoruz" (herkes diyor, savunulamaz), "doğrulanmış profil" (LinkedIn denedi, bıraktı), "blockchain" (değer katmıyor — bkz. §11.5).

**Evet, savunulabilir:** **Kanıt, sürecin kendisinden otomatik doğar.**

Bütün diğer platformlarda kanıt, kullanıcının **ekstra çaba** harcayıp sonradan eklediği bir şeydir (CV yaz, rozet ekle, portfolyo doldur) — bu yüzden ya eklenmez ya da uydurulur. Yetkin360'da kanıt, öğrencinin **zaten yapmak zorunda olduğu işin** (staj defteri, görev kaydı, çıktı teslimi, değerlendirme formu) dijital izidir.

Yani ayrışma: **Sıfır ekstra çaba ile kanıt üretimi + üçüncü taraf (üniversite) hakemliği.**

Bunun savunulabilir olmasının nedeni: rakiplerin bu veriye ulaşması için üniversitenin operasyonel sürecine girmesi gerekir; LinkedIn bunu yapmaz (ölçek ekonomisine uymaz), Kariyer.net bunu yapmaz (ilan işi modeli).

### 6.2 İkinci ayrışma: Veri yapısı

Doğrulanmış deneyim verisi zamanla **birikimli bir varlık** oluşturur: "X üniversitesinden Y bölümü mezunlarının staj yaptığı kurumlar, kazandıkları yetkinlikler, hangi kurumun stajyerine gerçekten iş öğrettiği." Bu veri hiçbir yerde yok ve hem üniversiteye hem kuruma satılabilir. Uzun vadeli hendek budur.

### 6.3 Dokümanın farklılaşma iddiasının eleştirisi

Doküman (bölüm 5): *"Yetkin360'ın ağı bağlantı kurarak değil, birlikte iş üreterek büyüyebilir."*

**Değerlendirme: Fikir güzel, mekanizma yok.** Cümle doğru ama "birlikte iş üretmenin" nasıl başlayacağı sorusunu cevaplamıyor — çünkü ilk iş birliğinin oluşması için zaten dolu bir marketplace gerekiyor. Zorunlu staj bu mekanizmayı sağlıyor: ilk iş birliği **mevzuat gereği** başlıyor.

---

## 7. Core Domain Model

### 7.1 Temel tasarım kararı: Claim / Evidence / Attestation ayrımı

Dokümanın modeli `Skill` ve `Evidence`'ı ilişkilendiriyor ama üçüncü ve en kritik kavramı eksik bırakıyor: **Attestation (birinin bir şeye tanıklık etmesi).**

Üç ayrı kavram olmalı:

- **Claim** — Özne kendi hakkında bir iddia ortaya atar. Güven değeri: sıfır. Ama profil UX'i için gerekli.
- **Evidence** — İddiaya bağlanan bir yapıt (artifact): kod deposu, doküman, çıktı, kayıt. Kendi başına doğrulama değildir; **içeriği** vardır.
- **Attestation** — Kimliği doğrulanmış bir **üçüncü taraf**, belirli bir kapsam için, belirli bir tarihte, adıyla tanıklık eder. Güvenin tek gerçek kaynağı budur.

**Kritik kural: Güven, Evidence'tan değil Attestation'dan gelir.** Doküman bu ikisini "evidence" çatısı altında karıştırıyor (bölüm 8'de `ORGANIZATION_VERIFICATION` ve `MENTOR_EVALUATION` bir evidence *türü* olarak listelenmiş). Bu bir modelleme hatasıdır: kurum doğrulaması bir "kanıt türü" değil, **kanıt üzerine bir tanıklıktır.** Ayırmazsanız, kullanıcının yüklediği ekran görüntüsü ile kurumun imzası aynı tabloda, aynı statüde durur ve güven hesabı kirlenir.

### 7.2 Entity listesi

**Çekirdek (MVP'de var):**

| Entity | Var mı? | Gerekçe |
|---|---|---|
| `User` | ✅ | Kimlik |
| `TalentProfile` | ✅ | Öğrenci profili |
| `Institution` | ✅ **(dokümanda yok)** | Üniversite/bölüm — hakem ve müşteri |
| `Organization` | ✅ | Staj veren kurum |
| `OrganizationMember` | ✅ | Kurumda çok kullanıcı |
| `Skill` | ✅ | Kontrollü sözlük (taksonomi) |
| `SkillClaim` | ✅ | Kullanıcının beyanı |
| `Engagement` | ✅ | Doküman buna `Collaboration` diyor — bkz. §10 |
| `EngagementTask` | ✅ | Hafif görev |
| `Deliverable` | ✅ | Çıktı |
| `Evidence` | ✅ | Yapıt |
| `Attestation` | ✅ **(dokümanda yok — en kritik eksik)** | Tanıklık |
| `Evaluation` | ✅ | Yapılandırılmış değerlendirme |
| `VerifiedExperience` | ✅ | Döngünün çıktısı |
| `SkillSignal` | ✅ **(dokümanda yok)** | Türetilmiş yetkinlik kanıtı — bkz. §7.4 |
| `AuditEvent` | ✅ | Denetim |

**MVP'de OLMAYAN (dokümanda önerilen ama çıkarılması gerekenler):**

| Entity | Karar | Gerekçe |
|---|---|---|
| `Need` | ❌ **Çıkar** | Marketplace'in parçası. Staj zaten eşleşmiş geliyor. V2. |
| `Match` / `MatchReason` | ❌ **Çıkar** | Matching MVP'de yok. V2. |
| `Project` | ❌ **Birleştir** | `Engagement` ile aynı şey — bkz. §7.5 |
| `Experience` (ayrı) | ❌ **Birleştir** | `VerifiedExperience` yeterli |
| `Notification` | ⚠️ **Minimal** | MVP'de tek tablo + e-posta; bölüm 55'teki 8 olay türü fazla |
| `Message` / chat | ❌ **Çıkar** | Bkz. §27 |
| `Badge` / gamification | ❌ **Çıkar** | Bkz. §27 |
| `Assessment` | ❌ **Çıkar** | LinkedIn denedi, kapattı |
| `TrustScore` | ❌ **Asla** | Bkz. §8.6 |

### 7.3 Skill tam olarak nedir?

**Tanım: Skill, bir yetkinlik taksonomisindeki kontrollü bir kavramdır. Kullanıcıya ait değildir, platforma aittir.**

Bu önemli çünkü kullanıcının serbest metin girmesine izin verirseniz ("Python", "python3", "Phyton", "Python Programlama") hiçbir eşleştirme, arama veya agregasyon çalışmaz.

```
Skill
  id, slug (unique), name_tr, name_en
  category (LANGUAGE|FRAMEWORK|TOOL|DOMAIN|SOFT)
  parent_id (hafif hiyerarşi: FastAPI → Python)
  status (ACTIVE|MERGED|DEPRECATED), merged_into_id
  is_curated (bool)
```

**Karar:** MVP'de ~300 küratörlü skill ile başlayın (ESCO veya O*NET'ten Türkçeleştirilmiş alt küme + yazılım alanı). Kullanıcı öneri gönderebilir, admin onaylar. **Serbest metin skill'e MVP'de bile izin vermeyin** — sonradan temizlemek çok pahalıdır.

Dokümanın "Skill Graph" fikri (bölüm 62): **Kabul, ama minimal.** Tek seviyeli `parent_id` yeterli. Tam graf yapısı V3.

### 7.4 SkillSignal — dokümanda eksik olan en önemli entity

Sorun: "Bu kişinin Python yetkinliği ne kadar güçlü?" sorusunu her seferinde 6 tabloyu join ederek hesaplamak hem yavaş hem tutarsızdır.

Çözüm: Her kanıt olayı, o kişi-yetkinlik çifti için **değişmez bir sinyal kaydı** üretir.

```
SkillSignal
  id, talent_id, skill_id
  source_type (SELF_CLAIM | DELIVERABLE | TASK | EVALUATION | ATTESTATION | EXTERNAL)
  source_id
  strength (enum: NONE | WEAK | MODERATE | STRONG)
  attested_by_org_id (nullable)
  occurred_at            -- yetkinliğin kullanıldığı tarih (recency için)
  created_at
  superseded_by_id (nullable)
```

Bu tablo **append-only**'dir. Bir yetkinliğin "seviyesi" bir kolon değil, bu sinyallerin bir fonksiyonudur. Bu tasarımın üç faydası:

1. **Zaman içindeki geçmiş bedavaya gelir** (dokümanın 33. bölümünün sorduğu şey).
2. **Açıklanabilirlik bedavaya gelir**: "Neden STRONG?" → sinyalleri listele.
3. **Geri alınabilirlik**: kurum tanıklığını geri çekerse sinyal `superseded` olur, geçmiş silinmez.

### 7.5 Experience ile Project farkı — dokümanın karışıklığı

Doküman hem `Project` (bölüm 17) hem `Collaboration` (bölüm 19) hem `Experience` (bölüm 16) tutuyor. Bu üçü büyük ölçüde aynı şeydir ve ayrı tutmak gereksiz karmaşıklık üretir.

**Netleştirme:**

- **Engagement** = *olan şey*. Belirli bir zaman aralığında, belirli taraflar arasında, platformda takip edilen bir çalışma. (Staj, bitirme projesi, kısa proje.) **Tek entity.**
- **VerifiedExperience** = *Engagement'ın değişmez kaydı*. Engagement tamamlanıp değerlendirildiğinde **kopyalanarak** üretilir ve bir daha değişmez.

**Neden kopyalanır (denormalizasyon kasıtlı):** Kurum hesabını silerse, adını değiştirirse veya platformdan ayrılırsa, öğrencinin doğrulanmış deneyimi bozulmamalıdır. Bu, dokümanın 99. bölümündeki "kurum hesabını kapatırsa doğrulamaları ne olur?" sorusunun cevabıdır: **Deneyim, tanıklık anındaki gerçeği dondurur.**

`Project` ayrı bir entity olarak **MVP'den çıkarılmalı.** Öğrencinin kişisel projeleri (platform dışı) `Evidence` olarak, düşük güven seviyesiyle eklenir.

### 7.6 Evidence tam olarak nedir?

**Tanım: Evidence, bir iddiaya bağlanan, doğrulanabilir bir kaynağı olan yapıttır.**

```
Evidence
  id, owner_talent_id
  kind (REPOSITORY | DOCUMENT | IMAGE | LINK | DELIVERABLE_REF | CERTIFICATE)
  uri / storage_key
  title, description
  engagement_id (nullable — platform içi mi dışı mı)
  visibility (PRIVATE | INSTITUTION | ORGANIZATION | PUBLIC)
  provenance (SELF_UPLOADED | PLATFORM_GENERATED | EXTERNAL_VERIFIED)
  content_hash          -- bütünlük
  created_at, deleted_at
```

**Kritik alan `provenance`:** Kullanıcının yüklediği PDF (`SELF_UPLOADED`) ile platformda üretilmiş deliverable (`PLATFORM_GENERATED`) asla aynı güven seviyesinde gösterilmemelidir. Doküman bu ayrımı 8. bölümde sezmiş ("evidence source") ama modele işlememiş.

### 7.7 İlişki haritası

```
Institution 1──n TalentProfile        (öğrenci hangi kuruma bağlı)
Institution 1──n Engagement           (hakem — dokümanda YOK)
User        1──1 TalentProfile
User        n──n Organization         (OrganizationMember, role ile)

Engagement  n──1 TalentProfile
Engagement  n──1 Organization
Engagement  n──1 Institution (nullable — platform dışı işbirliği için)
Engagement  1──n EngagementTask
Engagement  1──n Deliverable
Engagement  1──n Evaluation
Engagement  1──0..1 VerifiedExperience

Deliverable 1──n Evidence
Evidence    n──n Skill                (evidence_skills)
Attestation n──1 (polymorphic subject: Evidence | Deliverable | Engagement | SkillClaim)
Attestation n──1 Organization/Institution (attestor)

SkillSignal n──1 TalentProfile
SkillSignal n──1 Skill
SkillSignal n──1 (source: Deliverable | Evaluation | Attestation | SkillClaim)
```

### 7.8 Skill geçmişi tutulmalı mı?

**Evet, kesinlikle — ama dokümanın önerdiği şekilde değil.**

Doküman (bölüm 33) "skill history, evaluation history, verification history, profile changes" için ayrı geçmiş tabloları öneriyor. **Değerlendirme: Değiştir.** 4 ayrı geçmiş tablosu tutmak gereksiz yüktür.

**Alternatif:** `SkillSignal` append-only olduğu için geçmiş zaten yapının içindedir. Ayrıca `Attestation` ve `Evaluation` da doğaları gereği değişmezdir (immutable). Bu üç tablo append-only olunca, ayrı bir "history" mekanizmasına gerek kalmaz. Sadece `SkillClaim` mutable'dır ve onun için basit bir `skill_claim_history` yeterlidir.

**Prensip: Değişmez olması gereken veriyi mutable tasarlayıp sonra geçmiş tablosu eklemek yerine, baştan append-only tasarlayın.**

---

## 8. Verification Model

Bu bölüm ürünün kalbidir ve dokümanın en çok eksiği olan yerdir.

### 8.1 Dokümanın seviye modeli eleştirisi

Doküman (bölüm 7) 5 seviye öneriyor: Level 0 claimed → Level 1 evidence → Level 2 project/task → Level 3 org verification → Level 4 assessment.

**Değerlendirme: Reddet (mevcut haliyle).**

Gerekçeler:

1. **Tek boyutlu bir merdiven, çok boyutlu bir gerçeği temsil edemez.** "Level 3" bir kurumun onayladığı anlamına geliyor — ama *hangi kurum*? Doğrulanmamış bir kurum mu, MERSİS doğrulamalı bir kurum mu? Kimin, neyi, ne zaman onayladığı bilgisi tek sayıya sıkıştırılamaz.
2. **Level 4 (Assessment) en üstte olamaz.** LinkedIn'in kapattığı ürün tam olarak budur. Çoktan seçmeli test, gerçek proje çıktısından **daha zayıf** bir sinyaldir, daha güçlü değil. Merdivenin sıralaması yanlış.
3. **Seviyeler "neyin" doğrulandığını söylemiyor.** Dokümanın kendisi bölüm 7'de doğru soruyu soruyor ("bu kişi projede çalıştı" ≠ "Python'ı iyi kullandı") ama sonra bu ayrımı modele yansıtmayan bir seviye sistemi öneriyor.

### 8.2 Alternatif: İki eksenli doğrulama

Tek merdiven yerine, her tanıklık iki bağımsız eksende tanımlanır:

**Eksen 1 — Ne doğrulanıyor? (Claim Type)**

| Tip | İfade | Doğrulanabilirliği |
|---|---|---|
| `PARTICIPATION` | "Bu kişi bu çalışmada yer aldı" | **Yüksek** — nesnel, kolay |
| `CONTRIBUTION` | "Bu çıktıyı bu kişi üretti" | **Orta** — ekip işinde zor |
| `COMPETENCE` | "Bu kişi bu yetkinliği yeterli düzeyde kullandı" | **Düşük** — öznel, en değerli ama en kırılgan |
| `CONDUCT` | "Bu kişi zamanında/güvenilir çalıştı" | Orta — öznel ama tutarlı |

**Eksen 2 — Kim doğruluyor? (Attestor Trust)**

| Seviye | Attestor | Nasıl doğrulandı |
|---|---|---|
| `T0` | Kişinin kendisi | — (tanıklık sayılmaz) |
| `T1` | Doğrulanmamış kurum | Sadece e-posta |
| `T2` | Domain doğrulamalı kurum | Kurumsal e-posta domain kontrolü |
| `T3` | Kimlik doğrulamalı kurum | MERSİS/vergi no + yetkili teyidi |
| `T4` | Kurum (T3) + Üniversite ortak onayı | İki bağımsız taraf |
| `T5` | Kriptografik dış kanıt | GitHub OAuth commit, imzalı credential |

**Bir doğrulama ifadesi her zaman şu üçlüdür:** `(Ne, Kim, Ne zaman)`

Örnek gösterim:
> **Python** — "Yeterli düzeyde kullandı" (COMPETENCE), *Acme Yazılım A.Ş.* (T3, MERSİS doğrulamalı) ve *XYZ Üniv. Bilg. Müh.* (T4 ortak onay) tarafından, **Ağu 2026**'da doğrulandı. Dayanak: 3 çıktı, 12 görev kaydı.

Bu, tek bir "Level 3" etiketinden kıyaslanamayacak kadar bilgilendiricidir ve **manipülasyona karşı daha dayanıklıdır** çünkü kullanıcı seviyeyi değil, kim olduğunu görür.

### 8.3 "Verified" için gereken kanıt zinciri

`COMPETENCE` tipi bir doğrulamanın geçerli sayılması için **hepsi** gerekli:

1. Bir `Engagement` var ve **tarafların ikisi de** onaylamış (öğrenci + kurum).
2. Engagement'ın **süresi** var (başlangıç/bitiş), ve minimum eşik üstünde (ör. ≥4 hafta veya ≥40 saat).
3. En az bir `Deliverable` var ve o yetkinliğe bağlanmış.
4. Attestor, **doğrulanmış bir kurumda** (≥T2) **doğrulanmış bir üye** ve öğrencinin süpervizörü olarak Engagement'a bağlı.
5. Attestor, tanıklığı **adıyla** yapıyor (anonim tanıklık yok) ve bu kayıt değişmez.
6. **(Üniversite bağlamında)** Koordinatör Engagement'ın gerçekliğini onaylamış (T4).

Herhangi biri eksikse, tanıklık kaydedilir ama **`COMPETENCE` olarak değil, `PARTICIPATION` olarak** gösterilir.

**Kritik kural: Sistem, tanıklığın "doğru" olduğunu iddia etmez. Sadece kimin, neyi, hangi dayanakla söylediğini değişmez biçimde kaydeder ve gösterir.** Bu hem hukuken hem etik olarak tek savunulabilir pozisyondur. Ürün metinlerinde asla "bu kişi Python biliyor" denmemeli; "Acme A.Ş. bu kişinin Python'ı yeterli kullandığını beyan etti" denmelidir.

### 8.4 Organization verification nasıl yapılır?

Doküman (bölüm 103) `Unverified → Email/domain → Verified` öneriyor. **Değerlendirme: Yetersiz.** E-posta domaini sadece "bu kişi bu domaine erişebiliyor"u kanıtlar, kurumun **var olduğunu** ve kişinin **yetkili olduğunu** kanıtlamaz.

Kademeli model:

| Seviye | Kontrol | Otomasyon | Verdiği hak |
|---|---|---|---|
| `T1` | E-posta teyidi | Tam otomatik | Kurum oluştur, üye davet et |
| `T2` | Kurumsal domain (ücretsiz posta sağlayıcıları reddedilir) + DNS TXT kaydı | Otomatik | `PARTICIPATION` tanıklığı |
| `T3` | MERSİS/vergi no + ticaret sicil kontrolü + yetkili beyanı | Yarı-otomatik (admin gözden geçirir) | `COMPETENCE` tanıklığı |
| `T4` | Üniversite tarafından "tanınan staj yeri" olarak işaretlenmiş | Koordinatör onayı | Tam güven, akreditasyon geçerli |

**Anti-abuse kuralları:**
- Yeni kurum ilk 30 gün içinde `COMPETENCE` tanıklığı yapamaz (cooling period).
- Bir kurumun tanıklık yapabileceği kişi sayısı, doğrulanmış üye sayısına göre sınırlanır (ör. üye başına ayda 5).
- **Aynı kişi hem kurum yetkilisi hem öğrenci olarak kendi kendini doğrulayamaz** — `attestor_user_id != talent.user_id` DB seviyesinde CHECK + üyelik grafiği kontrolü.
- Kurumun tüm tanıklıkları tek bir üniversiteye ve tek bir öğrenci kümesine yoğunlaşıyorsa → admin incelemesi için işaretlenir.

### 8.5 Saldırı senaryoları ve savunma

| # | Saldırı | Mekanizma | Savunma |
|---|---|---|---|
| 1 | **Sahte kurum** | Kişi kendi "şirketini" kurar, kendini doğrular | T3 için MERSİS + admin incelemesi; cooling period; self-attestation DB kısıtı |
| 2 | **Karşılıklı doğrulama (collusion ring)** | A, B'yi; B, A'yı doğrular | Doğrulama grafiğinde döngü tespiti; karşılıklı tanıklık oranı metriği; Engagement süre eşiği |
| 3 | **Sahte staj** | Gerçek kurum, hiç çalışmamış akrabasını doğrular | Üniversite koordinatörü ortak onayı (T4); çıktı zorunluluğu; süreç boyunca zaman damgalı kayıt |
| 4 | **Kanıt hırsızlığı** | Başkasının GitHub reposunu kendi kanıtı gösterir | GitHub OAuth ile commit yazarlığı doğrulama (T5); manuel link `SELF_UPLOADED` kalır |
| 5 | **Sybil / sahte öğrenci** | Toplu sahte hesap | Üniversite davet zinciri (kapalı kayıt); .edu.tr domain kontrolü; rate limit |
| 6 | **Değerlendirme intikamı** | Kurum kişisel husumetle kötü not verir | İtiraz mekanizması + koordinatör hakemliği; değerlendirmenin serbest metni gizli, yapılandırılmış kısmı görünür; kurumun not dağılımı istatistiği izlenir |
| 7 | **Not enflasyonu** | Kurum herkese 5/5 verir | Kurum bazlı dağılım normalize edilerek gösterilir ("bu kurum ortalama 4.8 veriyor" bilgisi); tek boyutlu skor yerine davranışsal göstergeler |
| 8 | **Doğrulama geri çekme kötüye kullanımı** | Kurum, öğrenci ayrılınca tanıklığı siler | Tanıklıklar **silinmez**, `revoked` işaretlenir ve gerekçe istenir; hem asıl hem geri çekme görünür kalır |

**Doküman bu senaryoların çoğunu 101-104. bölümlerde *sorun olarak* tanımlıyor ama hiçbirine mekanizma önermiyor. Yukarıdaki tablo o boşluğu dolduruyor.** Özellikle 2 (collusion ring) ve 7 (not enflasyonu) dokümanda hiç yok ve gerçek platformlarda en sık görülen iki sorundur.

### 8.6 Trust Score — kesin red

Doküman (bölüm 65) tek bir güven skoru (87/100) fikrini öneriyor ve kendisi de şüphe duyuyor.

**Değerlendirme: Reddet. Kesinlikle yapılmamalı.**

Gerekçeler:
1. **Goodhart yasası:** Skor hedefe dönüşür, insanlar skoru optimize eder, sinyal ölür.
2. **Açıklanamaz ve itiraz edilemez.** "Neden 87?" sorusunun tatmin edici cevabı yoktur.
3. **Hukuki risk:** KVKK m.11 kapsamında otomatik işlemeyle aleyhte sonuç doğuran skorlamaya itiraz hakkı doğar. Tek sayı üzerinden bir öğrencinin elenmesi, açıklama yükümlülüğü yaratır.
4. **Ürün değerine aykırı:** Ürünün tüm iddiası "beyan değil kanıt". Kanıtı tek sayıya çevirmek, kanıtı tekrar beyana dönüştürmektir.

**Alternatif (dokümanın kendi önerdiği ve doğru olan):** Yetkinlik bazlı, sözel, kaynak gösteren göstergeler. Bunu destekliyorum.

---

## 9. Matching Model

### 9.1 Matching MVP'de olmalı mı?

**Hayır. MVP'den tamamen çıkarılmalı.**

Gerekçe: Matching'in çalışması için (a) yeterli talent stoğu, (b) yeterli kurum ihtiyacı, (c) her ikisinin de yapılandırılmış olması gerekir. MVP'de hiçbiri olmayacak. 50 öğrenci ve 5 kurumla matching algoritması yazmak, çözümü olmayan bir problemi çözmektir — sonuçlar bir SQL `WHERE` sorgusuyla aynı olur.

Doküman matching'i MVP'ye koyuyor (bölüm 57, madde 7) ve 6. haftayı buna ayırıyor (bölüm 107). **Bu, MVP'nin en büyük kaynak israfıdır.**

### 9.2 Matching gerektiğinde (V2) doğru mimari

AI gerekli mi? **Hayır, ilk aşamada kesinlikle değil.** Kademeli mimari:

```
Katman 1 — Hard filters (deterministik SQL)
  müsaitlik, şehir/uzaktan, süre, bölüm, sınıf, çalışma izni
  → Aday havuzunu 10.000'den 200'e indirir
  → SQL + index. AI yok. Bu katman adayların %90'ını eler.

Katman 2 — Deterministik skorlama (açıklanabilir, ağırlıklı)
  skill kapsamı (zorunlu/tercih ayrı)
  kanıt gücü (SkillSignal'lerden türetilir)
  tanıklık seviyesi (T0-T5)
  recency (2 yıl önceki kanıt daha zayıf)
  → Her kriterin katkısı ayrı ayrı saklanır ve gösterilir
  → Bu katman tek başına vakaların ~%85'ini çözer

Katman 3 — Semantik genişletme (SADECE geri çağırma için)
  "web servis geliştiren" ↔ "REST API yazdım"
  Kullanım: yeni ADAY EKLEMEK için, sıralamayı değiştirmek için DEĞİL
  Uygulama: skill eşanlamlı sözlüğü (elle) → yetmezse embedding
  → Bu katman MVP'de ve muhtemelen V2'de de gerekmez

Katman 4 — Doğal dil açıklama (opsiyonel, süsleme)
  Katman 2'nin ürettiği YAPILANDIRILMIŞ veriyi cümleye çevirir
  Yeni bilgi ÜRETMEZ, sadece biçimlendirir
  Çalışmazsa tablo gösterilir — sistem etkilenmez
```

**Kritik mimari kural: AI hiçbir zaman sıralamayı belirlemez.** Sıralama deterministik ve tekrarlanabilir olmalıdır; aynı girdi her zaman aynı çıktıyı vermelidir. Aksi halde "neden bu aday?" sorusuna cevap verilemez ve hukuki olarak savunulamaz.

### 9.3 Açıklanabilirlik — veri modeli

Skor asla tek sayı olarak saklanmaz:

```
MatchExplanation
  match_id, criterion (SKILL_REQUIRED|SKILL_PREFERRED|AVAILABILITY|LOCATION|EVIDENCE|RECENCY)
  skill_id (nullable)
  outcome (MET | PARTIAL | NOT_MET | UNKNOWN)
  weight, contribution
  supporting_evidence_ids[]   -- kanıta doğrudan link
  human_readable_tr
```

Kuruma gösterim dokümanın 12. bölümündeki formatla uyumlu (bu fikri destekliyorum):

```
Python           ✓ 2 doğrulanmış çıktı (Acme A.Ş., T3)
FastAPI          ✓ 1 doğrulanmış çıktı
PostgreSQL       △ Beyan var, kanıt yok
Docker           ✗ Kayıt yok
Müsaitlik        ✓ Haziran-Ağustos, tam zamanlı
```

**"Neden bu kişi?" sorusuna cevap, hesaplanmış değil, kaydedilmiştir.** Bu ayrım önemlidir: açıklama sonradan üretilirse (özellikle LLM ile) uydurma riski vardır; kayıtlıysa doğrudur.

### 9.4 Dokümanın matching kriterleri değerlendirmesi

Doküman 13. bölümde 6 kriter sayıyor. Değerlendirme:

| Kriter | Karar | Gerekçe |
|---|---|---|
| Skill match | ✅ Kabul | Temel |
| Skill level | ⚠️ Değiştir | "Level" öznel; **kanıt gücü** kullanın |
| Evidence strength | ✅ Kabul | En değerli kriter |
| Experience | ⚠️ Birleştir | Evidence strength'in içinde |
| Availability | ✅ Kabul — **hard filter** olmalı, skor değil | Müsait olmayan aday %90 uygun olsa da işe yaramaz |
| Project relevance | ⚠️ Araştırılmalı | Ölçmesi zor, MVP'de atlayın |
| **Recency** (doküman skorlama listesine koymamış) | ✅ **Ekle** | 3 yıl önceki kanıt bugünkü yetkinliği göstermez |

---

## 10. Collaboration Model

### 10.1 İsimlendirme ve sınır

Doküman `Collaboration` diyor; ben `Engagement` tercih ediyorum (Türkçe arayüzde "Çalışma" / "Staj"). Sebep: "collaboration" eşit ortaklık ima ediyor; staj/proje ilişkisi asimetriktir (bir taraf değerlendirir).

**Jira'ya dönüşmeme sınırı — somut kurallar:**

Doküman (bölüm 20) bu riski doğru tespit ediyor ama sınırı tanımlamıyor. Somut sınır:

- ✅ Görev **var** ama: alt görev yok, bağımlılık yok, sprint yok, board yok, etiket yok, tahmini süre yok.
- ✅ Görev durumu sadece 3 hâl: `PLANNED | IN_PROGRESS | DONE`.
- ✅ Görevin tek amacı: **bir çıktıya ve bir yetkinliğe bağlanmak.** Bağlanamayan görev, sistemde olmamalıdır.
- ❌ Zaman takibi, iş yükü, burndown, Gantt — hiçbiri yok.

**Test sorusu:** "Bu özellik olmadan, tamamlanmış bir stajdan geçerli bir doğrulanmış deneyim üretilebilir mi?" Cevap evet ise özellik eklenmez.

### 10.2 State machine

Dokümanın önerisi (bölüm 19): `PROPOSED → ACCEPTED → ACTIVE → PAUSED → COMPLETED → CANCELLED`.

**Değerlendirme: Değiştir.** İki sorun: (a) `COMPLETED`'dan sonra doğrulamanın nerede olduğu belirsiz, (b) `PAUSED` gerçek bir ihtiyaç değil ve state machine'i karmaşıklaştırıyor.

Önerilen:

```
DRAFT ──────────► PENDING_APPROVAL ──────► ACTIVE
  │                      │                    │
  │                      ├──► REJECTED        ├──► CANCELLED (gerekçeli)
  │                      │                    │
  └──► (silinebilir)     │                    ▼
                         │              PENDING_EVALUATION
                         │                    │
                         │                    ▼
                         │                EVALUATED
                         │                    │
                         │                    ▼
                         │                VERIFIED ──► (VerifiedExperience üretilir)
                         │                    │
                         │                    └──► DISPUTED ──► RESOLVED
```

**Dokümandan farklar ve gerekçeleri:**

- **`PENDING_APPROVAL` eklendi:** Üniversite koordinatörünün onay noktası. Bu, sahte staj saldırısına karşı en güçlü savunma. Dokümanda yok.
- **`PENDING_EVALUATION` eklendi:** "İş bitti ama değerlendirme gelmedi" durumu gerçek hayatta çok yaygın ve koordinatörün en çok kovaladığı durum. Ayrı bir hâl olmazsa bu takip edilemez. **Ürünün en kritik operasyonel ekranı bu listedir.**
- **`VERIFIED` ayrıldı:** `EVALUATED` (form dolduruldu) ile `VERIFIED` (onaylandı, deneyim üretildi) farklıdır.
- **`DISPUTED` eklendi:** İtiraz mekanizması olmadan değerlendirme sistemi kötüye kullanıma açıktır. Dokümanda hiç yok.
- **`PAUSED` çıkarıldı:** Gerçek bir iş ihtiyacı değil; `ACTIVE` içinde bir tarih boşluğu olarak temsil edilebilir.

**Geçiş kuralları (DB seviyesinde zorlanmalı):**
- `ACTIVE → PENDING_EVALUATION`: en az 1 `Deliverable` olmalı.
- `EVALUATED → VERIFIED`: kurum tanıklığı **ve** (kurumsal bağlamda) koordinatör onayı olmalı.
- `VERIFIED` **terminal ve değişmez**: sadece `DISPUTED`'a gidebilir, geri dönemez.
- Her geçiş `AuditEvent` üretir.

### 10.3 Collaboration → Profil dönüşümü (tek transaction)

Dokümanın 35. bölümü bu soruyu doğru soruyor. Cevap:

`VERIFIED`'a geçiş **tek bir veritabanı transaction'ında** şunları yapar:

1. `Engagement.status = VERIFIED`
2. `VerifiedExperience` kaydı oluştur (kurum adı, tarih, rol **kopyalanarak** — snapshot)
3. Her onaylanmış yetkinlik için `SkillSignal` ekle (`source_type=ATTESTATION`)
4. `Attestation` kayıtlarını `final` olarak işaretle
5. `AuditEvent` yaz
6. Bildirim kuyruğuna ekle (**transaction dışında, outbox pattern ile**)

**Kritik:** 1-5 atomik olmalı. 6 asla transaction içinde yapılmamalı (e-posta gönderimi transaction'ı kilitler). Outbox tablosu kullanın: transaction içinde `outbox` tablosuna satır yaz, ayrı bir süreç okur ve gönderir.

### 10.4 Deneyim geri alınabilir mi?

**Hayır, silinemez. Ama geri çekilebilir (revoke).**

- Kurum tanıklığını geri çekerse: `Attestation.revoked_at` + zorunlu gerekçe. Orijinal kayıt kalır.
- Profilde gösterim: deneyim görünür kalır, "doğrulama geri çekildi" notu ile.
- `SkillSignal` `superseded` olur, silinmez.
- Öğrenci deneyimi **gizleyebilir** (`visibility=PRIVATE`) ama silemez.

**Gerekçe:** Silinebilir doğrulama, doğrulama değildir. Öğrenci kötü değerlendirmeleri silebiliyorsa, iyi değerlendirmelerin de bir anlamı kalmaz. Bu, Upwork'ün iş geçmişini silmeye izin vermemesiyle aynı mantıktır.

---

## 11. AI Strategy

### 11.1 Genel duruş

**MVP'de AI'ın rolü: Tek bir yerde, opsiyonel, insan onaylı, kapatılabilir.**

Dokümanın 14. bölümü 7 AI kullanım alanı sayıyor. Her biri için analiz:

| Alan | AI gerekli mi? | MVP? | Karar ve gerekçe |
|---|---|---|---|
| **CV parsing** | Evet (gerçekten zor problem) | ✅ **Evet — tek AI özelliği** | Onboarding sürtünmesini 20 dk'dan 3 dk'ya indirir. En yüksek ROI. |
| Need extraction | Kısmen | ❌ V2 | Need entity MVP'de yok |
| Skill extraction (metinden) | Kısmen | ⚠️ CV parsing'e dahil | Ayrı özellik değil |
| Semantic matching | Hayır | ❌ V2+ | Bkz. §9.2 |
| Match explanation | **Hayır** | ❌ | Yapılandırılmış veri şablonla cümleye dönüşür; LLM gereksiz risk |
| Profile improvement | Hayır | ❌ V2 | Kural tabanlı yeterli: "Python'da kanıt yok" bir SQL sorgusudur |
| Evidence analysis | **Hayır — tehlikeli** | ❌ **Asla** | Bkz. §11.4 |
| Recommendation | Hayır | ❌ V2 | Kural tabanlı |

### 11.2 CV parsing — detaylı analiz

- **Problem:** Boş profil, kullanıcıyı kaçırır. Elle 20 alan doldurmak sürtünme yaratır.
- **AI gerekli mi?** Evet — serbest formatlı PDF'den yapılandırılmış veri çıkarmak regex ile güvenilir çözülemez.
- **Input:** Kullanıcının yüklediği CV metni (PDF→metin).
- **Output:** **Kesinlikle yapılandırılmış** — JSON schema ile zorlanmış `{education[], skills[], experiences[]}`. Serbest metin çıktısı yok.
- **Model:** Küçük/hızlı model yeterli (bu bir çıkarım görevi, akıl yürütme değil). Maliyet CV başına ihmal edilebilir.
- **Failure mode:** Yanlış alan eşleme, uydurma tarih, olmayan deneyim ekleme.
- **Hallucination riski:** **Yüksek** — ve bu kabul edilemez, çünkü ürünün tüm iddiası doğruluk.
- **Human verification: ZORUNLU.** AI çıktısı asla doğrudan kaydedilmez. Kullanıcıya **ön-doldurulmuş form** olarak gösterilir, kullanıcı her alanı görür ve onaylar.
- **Fallback:** AI başarısız olursa → boş form + "CV'nizi yükleyemedik, bilgileri elle girebilirsiniz." Akış devam eder.
- **Veri kaydı:** `source=AI_EXTRACTED, confirmed_by_user_at=<timestamp>`. Onaylanmamış hiçbir AI verisi profilde görünmez.
- **KVKK:** CV üçüncü taraf AI sağlayıcısına gönderileceği için **ayrı açık rıza** gerekir + yurt dışı aktarım mekanizması (bkz. §17).

### 11.3 AI'ın uydurmayı engelleyen mimari

Üç katmanlı savunma:

**1. AI hiçbir zaman veritabanına doğrudan yazmaz.**
```
AI çıktısı → `ai_extraction` staging tablosu → kullanıcı onayı → asıl tablo
```
Onaylanmamış çıktı hiçbir sorguda görünmez.

**2. Üretim (generation) değil, sadece dönüştürme (transformation).**
AI'ın kullanılabileceği tek işlem: var olan bir metni yapılandırmak. AI'ın **yeni olgu üretmesine** hiçbir yerde izin verilmez. "Bu adayın ileri seviye Python bildiğini düşünüyorum" cümlesi sistemde hiçbir zaman üretilemez — çünkü böyle bir çıktı tipi yoktur.

**3. Görsel ayrım (UI seviyesi).**
AI kaynaklı, onaylanmamış veri farklı görünür ve "doğrulanmış" rozetini **asla** alamaz. `provenance` alanı UI'ya kadar taşınır.

**Dokümanın 15. bölümündeki "grounded cevaplar" fikri doğru ama yeterince güçlü değil.** "Kaynak göstersin" demek yetmez; mimari olarak kaynaksız çıktı **üretilemez** olmalıdır. Fark: ilki bir prompt tercihi, ikincisi bir sistem kısıtı.

### 11.4 AI'ın kesinlikle kullanılmaması gereken yerler

1. **Yetkinlik seviyesi belirleme.** "Bu kişi Python'da ileri seviye" → sadece insan tanıklığı.
2. **Evidence gerçekliği değerlendirme.** "Bu kod gerçekten bu kişi tarafından mı yazıldı?" → AI bunu bilemez, tahmini güvenilirlik görüntüsü yaratır ki bu doğrulamasızlıktan **daha tehlikelidir.**
3. **Aday eleme/reddetme.** Otomatik olumsuz karar → hem etik hem KVKK riski.
4. **Değerlendirme metni yazma.** Kurum adına değerlendirme üretmek, tanıklığın kendisini geçersiz kılar.
5. **Sıralama belirleme.** Bkz. §9.2.
6. **Sahtekârlık tespiti kararı.** AI işaretleyebilir (flag), ama hesap kapatma kararını **insan verir.**

### 11.5 Blockchain

Doküman 60. bölümde "blockchain gerekli mi araştırılmalı" diyor.

**Değerlendirme: Reddet. Kesin ve net.**

Gerekçe: Blockchain'in çözdüğü problem "merkezi bir otoriteye güvenilemeyen ortamda değişmezlik"tir. Yetkin360'da **merkezi otorite zaten var ve zaten güveniliyor** — üniversite ve platform. Kullanıcı platforma güvenmiyorsa blockchain'e yazılan veriyi de platform yazdığı için güvenmez. Çözdüğü problem yok.

**Değişmezlik ihtiyacı varsa** doğru çözüm çok daha ucuz: append-only tablolar + `content_hash` + imzalı W3C Verifiable Credential. Open Badges 3.0 zaten W3C VC modelini kullanıyor ve kriptografik imza ile çevrimdışı doğrulanabiliyor — blockchain'siz.

**Doğru yol (V3):** Blockchain değil, **Open Badges 3.0 / W3C VC uyumlu imzalı credential ihracı.** Bu, gerçek ve standart bir taşınabilirlik sağlar; ekosistem (Europass, dijital cüzdanlar) bunu zaten konuşuyor.

---

## 12. Database Architecture

### 12.1 PostgreSQL kararı

Doküman PostgreSQL öneriyor (bölüm 24) ve "alternatifler değerlendirilmeli" diyor. Değerlendirdim:

| Aday | Değerlendirme |
|---|---|
| **PostgreSQL** | ✅ **Seçilen.** İlişkisel domain, güçlü kısıt desteği, transaction, JSONB esnekliği, FTS, gerekirse RLS ve pgvector aynı kutuda. |
| MySQL | ❌ CHECK constraint ve tip sistemi zayıf, JSON ve FTS daha kısıtlı. Kazandırdığı hiçbir şey yok. |
| MongoDB | ❌ **Kesinlikle hayır.** Domain baştan sona ilişkisel (yetkinlik-kanıt-tanıklık zinciri). Referans bütünlüğü ve çok-tablolu transaction ürünün temel gereksinimi. Doküman veritabanı burada aktif zarar verir. |
| SQLite | ❌ Tek kullanıcılı; çok kullanıcılı yazma ve RLS yok. (Test için evet.) |

**Karar: PostgreSQL 17+. Dokümanın önerisi doğru — Kabul.**

Not: Dokümandaki "ileride pgvector" ifadesi doğru çerçeveleme; MVP'de kurulmamalı.

### 12.2 Şema (MVP çekirdeği)

Tüm tablolarda ortak: `id UUID PK DEFAULT gen_random_uuid()`, `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()`.

**UUID kararı:** UUIDv7 tercih edilmeli (zaman sıralı → index locality). Sebep: ID'ler URL'de görünecek; artan integer ID enumeration saldırısına ve iş verisi sızıntısına ("kaç öğrenciniz var?") açıktır.

```sql
-- KİMLİK
users
  id uuid PK
  email citext UNIQUE NOT NULL
  password_hash text NOT NULL          -- Argon2id
  email_verified_at timestamptz
  status text NOT NULL DEFAULT 'ACTIVE'
      CHECK (status IN ('PENDING','ACTIVE','SUSPENDED','DELETED'))
  failed_login_count int NOT NULL DEFAULT 0
  locked_until timestamptz
  deleted_at timestamptz
  -- INDEX: (email) unique, (status) partial where deleted_at is null

institutions                            -- ÜNİVERSİTE (dokümanda yok)
  id uuid PK
  name text NOT NULL
  domain citext UNIQUE                  -- ör. 'xyz.edu.tr'
  verification_level text NOT NULL DEFAULT 'T1'
      CHECK (verification_level IN ('T1','T2','T3','T4'))
  status text NOT NULL DEFAULT 'ACTIVE'

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
  public_slug citext UNIQUE             -- paylaşılabilir profil linki
  deleted_at timestamptz
  -- INDEX: (institution_id) where deleted_at is null
  --        (public_slug) unique where public_slug is not null

organizations
  id uuid PK
  name text NOT NULL
  legal_id text                         -- MERSİS / vergi no
  domain citext
  verification_level text NOT NULL DEFAULT 'T1'
      CHECK (verification_level IN ('T1','T2','T3','T4'))
  verified_at timestamptz
  verified_by_user_id uuid REFERENCES users(id)
  status text NOT NULL DEFAULT 'ACTIVE'
  deleted_at timestamptz
  -- UNIQUE (legal_id) where legal_id is not null   -- aynı şirket iki kez kurulamaz

organization_members
  id uuid PK
  organization_id uuid NOT NULL REFERENCES organizations(id)
  user_id uuid NOT NULL REFERENCES users(id)
  role text NOT NULL CHECK (role IN ('ADMIN','MEMBER'))
  status text NOT NULL DEFAULT 'ACTIVE'
  UNIQUE (organization_id, user_id)
  -- INDEX: (user_id)   -- "bu kullanıcı hangi kurumlarda" — her istekte çalışır

institution_members                     -- koordinatörler
  id uuid PK
  institution_id uuid NOT NULL REFERENCES institutions(id)
  user_id uuid NOT NULL REFERENCES users(id)
  role text NOT NULL CHECK (role IN ('ADMIN','COORDINATOR'))
  UNIQUE (institution_id, user_id)

-- YETKİNLİK
skills
  id uuid PK
  slug citext UNIQUE NOT NULL
  name_tr text NOT NULL, name_en text
  category text NOT NULL
      CHECK (category IN ('LANGUAGE','FRAMEWORK','TOOL','DOMAIN','SOFT'))
  parent_id uuid REFERENCES skills(id)
  status text NOT NULL DEFAULT 'ACTIVE'
      CHECK (status IN ('ACTIVE','MERGED','DEPRECATED'))
  merged_into_id uuid REFERENCES skills(id)
  CHECK (status <> 'MERGED' OR merged_into_id IS NOT NULL)

skill_claims
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  skill_id uuid NOT NULL REFERENCES skills(id)
  claimed_level text CHECK (claimed_level IN ('BEGINNER','INTERMEDIATE','ADVANCED'))
  source text NOT NULL DEFAULT 'MANUAL'
      CHECK (source IN ('MANUAL','AI_EXTRACTED'))
  confirmed_by_user_at timestamptz      -- AI çıktısı için ZORUNLU
  UNIQUE (talent_id, skill_id)          -- aynı skill iki kez eklenemez (doküman b.71 ✓)
  CHECK (source <> 'AI_EXTRACTED' OR confirmed_by_user_at IS NOT NULL)

-- ÇALIŞMA
engagements
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  organization_id uuid NOT NULL REFERENCES organizations(id)
  institution_id uuid REFERENCES institutions(id)
  supervisor_user_id uuid REFERENCES users(id)   -- kurumdaki sorumlu
  kind text NOT NULL CHECK (kind IN ('INTERNSHIP','PROJECT','PART_TIME'))
  title text NOT NULL
  status text NOT NULL DEFAULT 'DRAFT'
      CHECK (status IN ('DRAFT','PENDING_APPROVAL','REJECTED','ACTIVE',
                        'CANCELLED','PENDING_EVALUATION','EVALUATED',
                        'VERIFIED','DISPUTED','RESOLVED'))
  started_on date, ended_on date
  confidential boolean NOT NULL DEFAULT false
  version int NOT NULL DEFAULT 1        -- optimistic locking (doküman b.36 ✓)
  CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on)
  -- INDEX: (organization_id, status), (talent_id, status),
  --        (institution_id, status)    -- koordinatör dashboard'unun ANA sorgusu
  --        (status) WHERE status='PENDING_EVALUATION'  -- partial, takip ekranı

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
  title text NOT NULL, description text
  submitted_at timestamptz
  accepted_at timestamptz
  accepted_by_user_id uuid REFERENCES users(id)
  -- INDEX: (engagement_id)

-- KANIT
evidence
  id uuid PK
  owner_talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  deliverable_id uuid REFERENCES deliverables(id)
  kind text NOT NULL
      CHECK (kind IN ('REPOSITORY','DOCUMENT','IMAGE','LINK','CERTIFICATE'))
  provenance text NOT NULL
      CHECK (provenance IN ('SELF_UPLOADED','PLATFORM_GENERATED','EXTERNAL_VERIFIED'))
  storage_key text, external_uri text
  content_hash text
  mime_type text, size_bytes bigint
  scan_status text NOT NULL DEFAULT 'PENDING'
      CHECK (scan_status IN ('PENDING','CLEAN','INFECTED','FAILED'))
  visibility text NOT NULL DEFAULT 'PRIVATE'
  deleted_at timestamptz
  -- INDEX: (owner_talent_id) where deleted_at is null, (deliverable_id)

evidence_skills
  evidence_id uuid REFERENCES evidence(id) ON DELETE CASCADE
  skill_id uuid REFERENCES skills(id)
  PRIMARY KEY (evidence_id, skill_id)

-- TANIKLIK (dokümanda YOK — en kritik ekleme)
attestations
  id uuid PK
  subject_type text NOT NULL
      CHECK (subject_type IN ('ENGAGEMENT','DELIVERABLE','SKILL_IN_ENGAGEMENT'))
  subject_id uuid NOT NULL
  skill_id uuid REFERENCES skills(id)       -- COMPETENCE ise dolu
  claim_type text NOT NULL
      CHECK (claim_type IN ('PARTICIPATION','CONTRIBUTION','COMPETENCE','CONDUCT'))
  attestor_user_id uuid NOT NULL REFERENCES users(id)
  attestor_org_id uuid REFERENCES organizations(id)
  attestor_institution_id uuid REFERENCES institutions(id)
  trust_level text NOT NULL CHECK (trust_level IN ('T1','T2','T3','T4','T5'))
  statement text
  revoked_at timestamptz, revoke_reason text
  created_at timestamptz NOT NULL DEFAULT now()
  -- APPEND-ONLY: UPDATE sadece revoked_at/revoke_reason için (trigger ile zorlanır)
  CHECK (claim_type <> 'COMPETENCE' OR skill_id IS NOT NULL)
  CHECK (attestor_org_id IS NOT NULL OR attestor_institution_id IS NOT NULL)
  -- INDEX: (subject_type, subject_id), (attestor_org_id, created_at)

skill_signals                            -- dokümanda YOK
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  skill_id uuid NOT NULL REFERENCES skills(id)
  source_type text NOT NULL
      CHECK (source_type IN ('SELF_CLAIM','DELIVERABLE','EVALUATION','ATTESTATION','EXTERNAL'))
  source_id uuid
  strength text NOT NULL CHECK (strength IN ('NONE','WEAK','MODERATE','STRONG'))
  attested_by_org_id uuid REFERENCES organizations(id)
  occurred_at timestamptz NOT NULL
  superseded_by_id uuid REFERENCES skill_signals(id)
  -- APPEND-ONLY
  -- INDEX: (talent_id, skill_id, occurred_at DESC)   -- profil sayfasının ana sorgusu
  --        (skill_id, strength) WHERE superseded_by_id IS NULL  -- yetenek arama

-- DEĞERLENDİRME
evaluations
  id uuid PK
  engagement_id uuid NOT NULL REFERENCES engagements(id)
  evaluator_user_id uuid NOT NULL REFERENCES users(id)
  direction text NOT NULL
      CHECK (direction IN ('ORG_TO_TALENT','TALENT_TO_ORG'))
  submitted_at timestamptz
  private_note text                     -- öğrenciye GÖSTERİLMEZ
  UNIQUE (engagement_id, evaluator_user_id, direction)
  -- APPEND-ONLY (submitted_at sonrası değiştirilemez)

evaluation_items
  id uuid PK
  evaluation_id uuid NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE
  skill_id uuid REFERENCES skills(id)
  criterion text NOT NULL               -- yetkinlik veya davranışsal kriter
  rating text NOT NULL
      CHECK (rating IN ('BELOW','MEETS','EXCEEDS','NOT_OBSERVED'))
  comment text
  -- 'NOT_OBSERVED' kritik: gözlemlenmemiş şeye not vermeye zorlamak veriyi bozar

verified_experiences                     -- SNAPSHOT — değişmez
  id uuid PK
  talent_id uuid NOT NULL REFERENCES talent_profiles(id)
  engagement_id uuid UNIQUE NOT NULL REFERENCES engagements(id)
  org_name_snapshot text NOT NULL       -- kasıtlı denormalizasyon
  org_verification_level_snapshot text NOT NULL
  institution_name_snapshot text
  title text NOT NULL
  started_on date NOT NULL, ended_on date NOT NULL
  verified_at timestamptz NOT NULL
  visibility text NOT NULL DEFAULT 'PUBLIC'
  public_token text UNIQUE              -- paylaşılabilir doğrulama linki
  -- APPEND-ONLY (sadece visibility değişebilir)

-- ALTYAPI
audit_events
  id bigserial PK                       -- burada UUID gereksiz, sıralı daha iyi
  actor_user_id uuid, actor_ip inet
  action text NOT NULL
  subject_type text NOT NULL, subject_id uuid
  result text NOT NULL CHECK (result IN ('SUCCESS','DENIED','ERROR'))
  metadata jsonb
  occurred_at timestamptz NOT NULL DEFAULT now()
  -- APPEND-ONLY. INDEX: (subject_type, subject_id, occurred_at DESC),
  --                     (actor_user_id, occurred_at DESC)
  -- Aylık partition (pg_partman) — büyüyecek tek tablo budur

outbox                                   -- transaction güvenli yan etki
  id bigserial PK
  topic text NOT NULL, payload jsonb NOT NULL
  created_at timestamptz NOT NULL DEFAULT now()
  processed_at timestamptz
  attempts int NOT NULL DEFAULT 0
  -- INDEX: (created_at) WHERE processed_at IS NULL
```

### 12.3 Soft delete politikası — dokümanın atladığı incelik

Doküman (bölüm 34) "soft delete mi hard delete mi araştırılmalı" diyor. Cevap **tabloya göre değişir** ve tek politika uygulanamaz:

| Tablo | Politika | Gerekçe |
|---|---|---|
| `users` | **Anonimleştirme** | KVKK silme hakkı. Satır kalır, PII temizlenir (`email='deleted-<uuid>@invalid'`, `password_hash=''`). FK bütünlüğü korunur. |
| `talent_profiles` | Soft delete + PII anonimleştirme | Aynı |
| `evidence` | Soft delete → 30 gün sonra dosya hard delete | Yanlışlıkla silmeye karşı koruma |
| `attestations` | **Asla silinmez** — sadece revoke | Doğrulamanın anlamı bu |
| `verified_experiences` | **Asla silinmez** — visibility değişir | Aynı |
| `audit_events` | **Asla silinmez** — retention süresi sonunda arşiv | Denetim |
| `engagement_tasks` | Hard delete OK | Değeri yok |

**Kritik nokta:** KVKK silme hakkı ile doğrulamanın değişmezliği çelişir gibi görünür. Çözüm: **kişisel veri silinir, olgu kalır.** "Ahmet Yılmaz" → "Silinmiş Kullanıcı" olur ama "Acme A.Ş. 2026'da bir stajyeri doğruladı" kaydı kalır. Bu hem KVKK'ya hem denetlenebilirliğe uyar. Bunu **kayıt sırasında aydınlatma metninde açıkça belirtmek** gerekir.

### 12.4 Büyüdüğünde ne olur?

En kritik sorgular ve davranışları:

| Sorgu | Ölçek | Risk | Çözüm |
|---|---|---|---|
| Profil sayfası (skill + sinyaller) | Kişi başı ~200 satır | Düşük | `(talent_id, skill_id, occurred_at DESC)` index |
| Koordinatör dashboard (400 engagement) | Kurum başı düşük | Düşük | `(institution_id, status)` index |
| "Değerlendirme bekleyenler" | Tüm tablo taraması riski | **Orta** | **Partial index** `WHERE status='PENDING_EVALUATION'` |
| Yetenek arama (skill filtreli) | Tablolar arası | **Yüksek — asıl risk** | Bkz. aşağı |
| Audit log sorgusu | En hızlı büyüyen tablo | **Yüksek** | Aylık partition + retention |

**Yetenek arama problemi:** "Python'da STRONG sinyali olan, İstanbul'daki, müsait öğrenciler" sorgusu `skill_signals × talent_profiles` join'i gerektirir ve `skill_signals` en büyük tablodur.

Çözüm sırası: (1) MVP'de doğrudan join yeterli (<10K öğrenci). (2) 10K+ için **materialized view** (`talent_skill_summary`, saatlik yenilenir). (3) Yalnızca 100K+ ve gerçek darboğaz kanıtlanırsa arama motoru. **Elasticsearch MVP'de kesinlikle gereksiz** — 10M dokümanın altında ve birkaç yüz sorgu/sn altında PostgreSQL FTS+GIN uygulaması daha hızlı, işletmesi daha ucuz ve bakımı daha basittir.

### 12.5 Transaction sınırları

| İşlem | Transaction içinde | Dışında |
|---|---|---|
| Engagement → VERIFIED | status, VerifiedExperience, SkillSignal'ler, Attestation, AuditEvent, outbox satırı | E-posta, bildirim |
| Evidence yükleme | DB kaydı (`scan_status=PENDING`) | Dosya yükleme, virüs taraması |
| Kullanıcı kaydı | user + profile | Doğrulama e-postası |
| Değerlendirme gönderimi | evaluation + items + audit | Bildirim |

**Kural: Ağ çağrısı (e-posta, S3, AI) asla açık transaction içinde yapılmaz.** Doküman bu konuyu 35. bölümde soruyor ama cevaplamıyor; cevap outbox pattern'dir.

### 12.6 Concurrency

Doküman (bölüm 36) optimistic locking öneriyor. **Kabul — ama sadece gereken yerde.**

- `engagements.version` — evet (durum çakışması gerçek bir risk).
- Diğer tablolar — hayır, gereksiz karmaşıklık.
- Durum geçişleri için ek güvenlik: `UPDATE ... WHERE id=? AND status=? AND version=?` → 0 satır dönerse 409 Conflict.

---

## 13. Backend Architecture

### 13.1 Teknoloji kararı

| Kriter | FastAPI | Spring Boot | NestJS | ASP.NET Core | Django |
|---|---|---|---|---|---|
| Geliştirme hızı (tek kişi) | ★★★★★ | ★★ | ★★★ | ★★★ | ★★★★ |
| Tip güvenliği | ★★★★ (Pydantic) | ★★★★★ | ★★★★ | ★★★★★ | ★★ |
| Ekosistem (genel) | ★★★★ | ★★★★★ | ★★★★ | ★★★★ | ★★★★ |
| AI/NLP ekosistemi | ★★★★★ | ★★ | ★★★ | ★★ | ★★★★★ |
| Öğrenme eğrisi | ★★★★★ | ★★ | ★★★ | ★★★ | ★★★★ |
| Test edilebilirlik | ★★★★ | ★★★★★ | ★★★★ | ★★★★★ | ★★★★ |
| Güvenlik varsayılanları | ★★★ | ★★★★ | ★★★ | ★★★★★ | ★★★★★ |
| Deployment basitliği | ★★★★ | ★★ | ★★★★ | ★★★ | ★★★★ |
| Kurumsal algı (TR) | ★★★ | ★★★★★ | ★★★ | ★★★★ | ★★★ |

**Karar: FastAPI + Python 3.12 + SQLAlchemy 2.0 + Alembic. Dokümanın önerisi — Kabul.**

Gerekçe: Tek geliştirici için hız belirleyici faktördür ve FastAPI burada açık ara önde. Pydantic'in şema doğrulaması güvenlik için gerçek bir kazanç (girdi doğrulama varsayılan olarak var). AI entegrasyonu Python ekosisteminde en kolay. Spring Boot'un tip güvenliği avantajı, tek kişilik projede geliştirme hızı kaybını telafi etmez.

**Uyarı (dokümanda yok):** FastAPI'nin Django'ya göre eksiği, **hazır admin paneli ve kimlik doğrulama altyapısının olmaması.** Bunlar elle yazılacak ve MVP planında bu iş küçümseniyor. Admin paneli için hazır çözüm (SQLAdmin) kullanın, elle yazmayın.

### 13.2 Katmanlama — dokümanın "gereksiz abstraction" endişesine cevap

Doküman (bölüm 70) Router→Service→Repository→DB öneriyor ve "gereksiz abstraction üretir mi" diye soruyor. **Cevap: Evet, Repository katmanı bu projede gereksizdir.**

Gerekçe: Repository pattern'in amacı veritabanını soyutlamaktır (değiştirilebilir kılmak). PostgreSQL'i değiştirmeyeceksiniz. SQLAlchemy zaten bir soyutlama katmanıdır. Üstüne bir katman daha koymak, her sorgu için iki dosya yazmak demektir ve hiçbir şey kazandırmaz.

**Önerilen (2 katman):**

```
api/        → HTTP: routing, şema doğrulama, auth bağımlılıkları, HTTP kodları
             İş mantığı YOK.
services/   → İş mantığı, yetkilendirme kararları, transaction sınırları,
             SQLAlchemy sorguları (doğrudan)
models/     → SQLAlchemy ORM modelleri
schemas/    → Pydantic request/response (ORM modellerinden AYRI)
```

**Kritik kural:** Pydantic şemaları ile ORM modelleri **asla aynı sınıf olmamalı.** ORM modelini doğrudan response olarak döndürmek, en yaygın veri sızıntısı yoludur (`password_hash`, `private_note`, silinmiş kayıtlar yanlışlıkla döner). Bu, OWASP API3:2023 (Broken Object Property Level Authorization) riskinin tam karşılığıdır.

### 13.3 Modül yapısı

```
app/
  api/v1/           auth, talents, organizations, institutions,
                    engagements, evidence, attestations, evaluations, admin
  services/         (aynı domain ayrımı)
  models/
  schemas/
  core/             config, security, deps, errors, pagination
  db/               session, migrations
  workers/          outbox_processor, file_scanner
```

**Modüler monolit kararı: Kabul (doküman bölüm 40).** Tek geliştirici için microservice kesinlikle yanlıştır — dağıtık transaction, servisler arası auth, ayrı deploy, debugging zorluğu getirir ve hiçbir problemi çözmez. Doküman bunu doğru söylüyor.

**Microservice'e geçiş kriteri (dokümanın istediği, bölüm 89):** Aşağıdakilerin **en az ikisi** doğru olmadan ayırmayın:
1. Ekip 8+ kişi ve deploy çakışmaları gerçek bir sorun,
2. Bir modül gerçekten farklı ölçekleniyor (ölçülmüş, tahmin edilmemiş),
3. Farklı SLA veya uyumluluk sınırı zorunlu.

### 13.4 API tasarımı

REST + `/api/v1`. Dokümanın endpoint listesi (bölüm 37) makul ama `/matches` MVP'de yok.

**Kritik tasarım kuralı — BOLA'ya karşı:** Kaynak sahipliği **URL'den çıkarılmalı**, gövdeden değil.

```
✅ GET /api/v1/engagements/{id}          → servis, kullanıcının erişimini KONTROL EDER
❌ GET /api/v1/engagements?org_id={id}   → org_id'ye güvenmek = BOLA
```

BOLA, API saldırılarının ~%40'ında görülüyor ve OWASP API Security Top 10'da 2019 ve 2023 sürümlerinin ikisinde de 1 numara. Bu, Yetkin360'ın en olası ihlal vektörüdür (çok kiracılı, kimlik doğrulamalı, nesne merkezli API).

**Hata formatı** (dokümanın 75. bölümü — Kabul):
```json
{ "code": "ENGAGEMENT_NOT_FOUND", "message": "Kayıt bulunamadı", "request_id": "..." }
```
**Kural: Yetkisiz erişimde 403 değil 404 dönün.** 403, kaynağın varlığını sızdırır ("bu ID var ama senin değil" → enumeration).

**Sayfalama:** Doküman (bölüm 73) cursor vs offset karşılaştırması istiyor. Karar: **liste uçlarında cursor** (`created_at, id` bileşik), admin ekranlarında offset kabul edilebilir. Gerekçe: offset derin sayfalarda `OFFSET 10000` ile lineer yavaşlar ve eşzamanlı ekleme olduğunda kayıt atlar.

---

## 14. Frontend Architecture

### 14.1 Teknoloji kararı

**Karar: Next.js (App Router) + TypeScript + React. Dokümanın önerisi — Kabul, ama gerekçesi düzeltilerek.**

Doküman "SEO" gerekçesini öne çıkarıyor. Bu **büyük ölçüde yanlış**: uygulamanın %95'i giriş yapmış kullanıcı ekranı, SEO'nun hiç rolü yok. SEO'nun gerçekten önemli olduğu tek yer **public profil ve public doğrulama sayfaları** — ki bunlar da ürünün viral dağıtım kanalıdır (öğrenci linkini paylaşır). Yani Next.js seçimi doğru, ama tek gerekçesi bu iki sayfa türü.

Asıl gerekçeler: dosya bazlı routing, server component'lerle veri çekme basitliği, tek çatı altında hem public hem app.

**Alternatif değerlendirmesi:** Vite + React SPA da tamamen geçerli olurdu ve public sayfalar için ayrı bir statik çözüm kullanılabilirdi. Vue/Nuxt teknik olarak eşdeğer; Türkiye'de React iş gücü havuzu daha büyük olduğu için React tercih edilir.

### 14.2 Mimari kararlar

| Konu | Karar | Gerekçe |
|---|---|---|
| State | **TanStack Query** (sunucu durumu) + React state (yerel). **Redux YOK** | Uygulamanın durumu neredeyse tamamen sunucu durumudur; Redux gereksiz katman |
| Form | React Hook Form + Zod | Zod şemaları Pydantic ile hizalanabilir; çift doğrulama |
| Stil | Tailwind + shadcn/ui | Tek geliştirici için en hızlı; erişilebilir bileşen tabanı hazır |
| Auth | **httpOnly cookie** | Bkz. §15.3 |
| Tip güvenliği | OpenAPI'den TS tipi üretimi | FastAPI OpenAPI'yi otomatik üretir — bedava kazanç |

### 14.3 Sayfa yapısı

```
(public)/                  landing, /p/[slug] (profil), /v/[token] (doğrulama)
(auth)/                    login, register, verify-email, reset-password
(talent)/                  dashboard, profile, skills, evidence,
                           engagements/[id], engagements/[id]/log
(org)/[orgId]/             dashboard, interns, engagements/[id],
                           engagements/[id]/evaluate, members, settings
(institution)/[instId]/    dashboard, engagements, pending-evaluations,
                           students, reports
(admin)/                   verifications, users, orgs, skills, flags
```

### 14.4 Erişilebilirlik

Doküman (bölüm 77) WCAG'i MVP'de bile atlamamayı söylüyor — **Kabul, ve bu ciddiye alınmalı.** Ek gerekçe: ürünün müşterisi **kamu üniversitesidir** ve kamu kurumları için erişilebilirlik çoğu zaman bir satın alma şartıdır. Yani bu sadece etik değil, ticari bir gerekliliktir.

Somut asgari: semantik HTML, tüm form alanlarında `<label>`, klavye ile tam gezinme, görünür focus, 4.5:1 kontrast, hata mesajlarının `aria-live` ile duyurulması. shadcn/ui (Radix tabanlı) bunların çoğunu hazır getirir.

### 14.5 Frontend güvenlik

Dokümanın 76. bölümündeki "butonu gizlemek yetmez" vurgusu **doğru ve kritik — Kabul.** Somutlaştırma: her yetkilendirme kararı sunucuda **tekrar** verilir. Frontend'deki rol kontrolü sadece UX'tir (kullanıcıya yapamayacağı şeyi göstermemek), güvenlik sınırı değildir.

---

## 15. Authentication & Authorization

### 15.1 Kavramsal ayrım

- **Authentication:** "Sen kimsin?" → Bir kez, oturum başında.
- **Authorization:** "Bunu yapabilir misin?" → **Her istekte, her nesne için.**

Doküman bu ayrımı yapıyor (bölüm 26-27) — Kabul. Ancak kritik nokta şu: yetkilendirme **rol** sorusu değil, **nesne** sorusudur.

### 15.2 Multi-tenancy kararı

Doküman (bölüm 25) beş yaklaşımı karşılaştırmayı istiyor:

| Yaklaşım | Değerlendirme |
|---|---|
| Ayrı veritabanı | ❌ Yüzlerce kurum için işletilemez; migration cehennemi |
| Ayrı şema | ❌ Aynı sorun, biraz daha hafif; ayrıca **öğrenci birden fazla kuruma ait olabilir** — model uymuyor |
| `tenant_id` + uygulama filtresi | ✅ **Temel katman** |
| PostgreSQL RLS | ⚠️ **İkinci katman — ama MVP'de değil** |
| Sadece uygulama yetkilendirmesi | ⚠️ Tek başına yetersiz ama MVP için kabul edilebilir |

**Karar: Uygulama seviyesinde zorunlu kapsamlama (scoping) + V2'de RLS'i güvenlik ağı olarak ekle.**

**RLS hakkında dürüst değerlendirme (dokümanın sorduğu soru):** RLS'in performans maliyeti düşüktür (indekslenmiş tenant kolonunda tipik %2-5). Ancak MVP'de **erteleme gerekçem performans değil, operasyonel tuzaklar:** RLS politikaları tablo sahibine ve superuser'a uygulanmaz (uygulama rolünün sahip olmayan bir rol olması ve doğru GRANT'lerin verilmesi gerekir), bağlantı havuzu (PgBouncer) kullanıldığında oturum değişkenleri sızabilir, ve `current_setting()` gibi çağrılar politika içinde yanlış kullanılırsa sorgu planı bozulup index kullanımı kaybolabilir. Tek geliştirici için bunlar MVP'de yönetilebilir riskler değildir — **yanlış kurulmuş RLS, olmayan RLS'ten daha tehlikelidir** çünkü sahte güven yaratır.

**Doğru sıra:** Önce uygulama katmanını sağlam kur ve **test et**; sonra RLS'i ikinci bir ağ olarak ekle.

**Yapısal çözüm (asıl önemli olan):** Kapsamlamayı unutulabilir olmaktan çıkarın.

```python
# Her sorgu bunun üzerinden geçer — çıplak session kullanımı lint ile yasaklanır
def scoped_engagements(session, principal: Principal):
    q = select(Engagement)
    if principal.kind == "TALENT":
        return q.where(Engagement.talent_id == principal.talent_id)
    if principal.kind == "ORG_MEMBER":
        return q.where(Engagement.organization_id.in_(principal.org_ids))
    if principal.kind == "COORDINATOR":
        return q.where(Engagement.institution_id.in_(principal.institution_ids))
    raise Forbidden()
```

**Güvenlik kuralı: Filtrelemeyi hatırlamak zorunda olmak, er ya da geç unutmak demektir.** Varsayılanı güvenli yapın.

### 15.3 Token stratejisi

**Karar: httpOnly + Secure + SameSite=Lax cookie içinde kısa ömürlü JWT access token (15 dk) + veritabanında saklanan, döndürülen (rotating) refresh token (30 gün).**

Gerekçeler:
- `localStorage`'da token = herhangi bir XSS açığı tam hesap ele geçirmesi demektir. httpOnly cookie JavaScript'ten okunamaz.
- Refresh token DB'de saklanır → **anında iptal edilebilir** (JWT'nin en büyük zaafı iptal edilememesidir). Hesap ele geçirilirse tüm oturumlar kapatılabilir.
- Rotation + yeniden kullanım tespiti: eski bir refresh token tekrar kullanılırsa, o ailenin tüm token'ları iptal edilir (çalınma sinyali).
- SameSite=Lax + CSRF token (double-submit) → CSRF koruması.

**Şifre:** Argon2id (OWASP'ın mevcut önerisi; bcrypt'in 72 bayt sınırı ve GPU direnci zayıflığı yok).

### 15.4 Object-level authorization — ürünün en kritik güvenlik noktası

Her kaynak erişimi için tek bir merkezî fonksiyon:

```python
def can(principal, action: str, resource) -> bool
```

**Karar matrisi (kısmi):**

| Kaynak | Talent (sahip) | Talent (diğer) | Org üyesi (ilgili) | Org üyesi (ilgisiz) | Koordinatör (kendi kurumu) | Admin |
|---|---|---|---|---|---|---|
| TalentProfile (public alanlar) | RW | R (visibility'ye göre) | R (eşleşmişse) | ✗ | R | R |
| TalentProfile (e-posta, tel) | RW | ✗ | R (sadece aktif engagement) | ✗ | R | R |
| Evidence (PRIVATE) | RW | ✗ | ✗ | ✗ | ✗ | ✗ (**admin bile hayır**) |
| Evidence (engagement'a bağlı) | RW | ✗ | R | ✗ | R | R |
| Engagement | R + sınırlı W | ✗ | RW | ✗ | R + onay | R |
| Evaluation (yapılandırılmış) | R (gönderildikten sonra) | ✗ | RW (yazar) | ✗ | R | R |
| Evaluation (`private_note`) | **✗ asla** | ✗ | R (sadece kendi kurumu) | ✗ | ✗ | R |
| Attestation | R | R (public ise) | RW (kendi yaptığı) | ✗ | R | R |

**Dikkat edilecek incelik:** "Admin her şeyi görür" varsayımı **yanlıştır.** Öğrencinin PRIVATE kanıtı (örneğin kişisel sağlık raporu içeren bir belge) platform admininin işi değildir. En az yetki ilkesi admin'e de uygulanır; admin erişimi gerekiyorsa gerekçeli ve denetim kaydına yazılan bir "break-glass" akışı olmalıdır.

---

## 16. Security Architecture

OWASP Top 10 ve OWASP API Security Top 10 referansıyla:

### 16.1 Risk bazlı analiz

| OWASP riski | Yetkin360'daki karşılığı | Önlem |
|---|---|---|
| **API1: BOLA** | **En yüksek risk.** Org A, Org B'nin engagement'ını okur | Merkezî `can()`, `scoped_*` sorgular, UUIDv7, 404 dönüşü, **her uç için otomatik test** |
| API2: Broken Auth | Token çalınması, brute force | httpOnly cookie, rotation, rate limit, hesap kilitleme |
| **API3: Broken Object Property Level Auth** | **Çok gerçek risk.** `private_note` veya `password_hash` yanlışlıkla response'a girer | Pydantic response şemaları ZORUNLU; ORM modeli asla doğrudan dönmez; mass-assignment'a karşı request şemalarında sıkı alan listesi |
| API4: Kaynak tüketimi | Büyük dosya, pahalı sorgu, AI çağrısı | Boyut limiti, sayfalama zorunlu, AI kotası |
| API5: Function Level Auth | Talent, admin ucuna erişir | Uç bazlı rol bağımlılığı + test |
| A03: Injection | SQL injection | SQLAlchemy parametreli sorgular; ham SQL yasak |
| A03: XSS | Değerlendirme yorumu, profil metni | React varsayılan escape; `dangerouslySetInnerHTML` yasak; CSP |
| CSRF | Cookie tabanlı auth | SameSite=Lax + double-submit token |
| SSRF | **Gerçek risk**: kullanıcı URL'si (GitHub linki) çekiliyor | Allowlist (sadece github.com vb.), özel IP aralıkları engelli, yönlendirme takip edilmez |
| A08: Bütünlük | Bağımlılık zinciri | Lock dosyaları, `pip-audit`/`npm audit` CI'da |
| A09: Logging | İhlal tespit edilemez | Audit log + güvenlik olayı logları |

### 16.2 Dosya yükleme güvenliği

Dokümanın 29. bölümü doğru konuları sayıyor — **Kabul.** Somutlaştırma:

1. Dosya **asla** uygulama sunucusunda tutulmaz → object storage (S3/R2/MinIO), private bucket.
2. Uzantıya **asla** güvenilmez → içerikten magic-byte ile MIME tespiti.
3. Allowlist: `pdf, png, jpg, docx, zip`. Blacklist kullanılmaz (her zaman eksiktir).
4. Boyut sınırı: 10 MB (dosya), toplam kota kullanıcı başına 100 MB.
5. Dosya adı **asla korunmaz** → `{uuid}.{ext}`, orijinal ad sadece DB'de metadata.
6. Virüs taraması (ClamAV) **yükleme sonrası, asenkron**; `scan_status=PENDING` iken indirilemez.
7. İndirme: **kısa ömürlü imzalı URL** (5 dk), her indirmede yetki kontrolü, audit kaydı.
8. **Kritik:** Kullanıcı içeriği ana domainden **asla** servis edilmez (ayrı domain/subdomain) → yüklenen HTML/SVG ile aynı-origin XSS engellenir. Doküman bunu atlamış; gerçek dünyada en sık yapılan dosya güvenliği hatasıdır.
9. `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff`.

### 16.3 Rate limiting

| Uç | Limit |
|---|---|
| Login | 5/dk/IP + 10/saat/hesap, sonra artan gecikme |
| Kayıt | 3/saat/IP |
| Şifre sıfırlama | 3/saat/hesap |
| Dosya yükleme | 20/saat/kullanıcı |
| AI (CV parse) | 5/gün/kullanıcı |
| Arama | 60/dk/kullanıcı |
| Genel API | 300/dk/kullanıcı |

**MVP uygulaması: Nginx rate limit + PostgreSQL sayaç.** Redis MVP'de bunun için gerekmez.

### 16.4 Yetkin360'a özgü saldırı senaryoları (dokümanın istediği)

| # | Senaryo | Önlem |
|---|---|---|
| 1 | Sahte kurum oluşturma | T3 için MERSİS + admin; `legal_id` unique; cooling period |
| 2 | Sahte doğrulama | Self-attestation DB kısıtı; koordinatör ortak onayı; grafik analizi |
| 3 | **Başka kurumun aday verisini okuma** | Merkezî scoping + BOLA testleri (her uç için) |
| 4 | Değerlendirme manipülasyonu | Append-only; itiraz akışı; kurum dağılım izleme |
| 5 | Sahte evidence | `provenance` ayrımı; GitHub OAuth doğrulaması; content hash |
| 6 | Hesap ele geçirme | Argon2id, MFA (V2), oturum iptali, giriş bildirimi |
| 7 | Spam kurum | Domain doğrulama, oran limitleri, admin kuyruğu |
| 8 | Zararlı dosya yükleme | §16.2'nin tamamı |
| 9 | **Enumeration** (dokümanda yok) | UUIDv7, 404 dönüşü, rate limit |
| 10 | **Kayıt sırasında kullanıcı sayımı** (dokümanda yok) | Kayıt/şifre sıfırlamada tek tip cevap ("e-posta gönderildi") |

### 16.5 Secrets

`.env` sadece geliştirme. Production: barındırıcı ortam değişkenleri veya (tek VPS'te) `systemd` credential / dosya izinleri kısıtlı. Sırlar asla git'e girmez → `gitleaks` pre-commit + CI. Deploy anahtarları ayrı.

---

## 17. KVKK / Privacy Considerations

*(Teknik analizdir; hukuki danışmanlık değildir. Aydınlatma metni ve rıza akışları için avukat onayı alınmalıdır.)*

### 17.1 Kritik güncel bilgi — dokümanın atladığı

Türkiye'de yurt dışına veri aktarımı rejimi değişti: **açık rıza artık istisna, uygun güvenceler (özellikle standart sözleşme) kural.** Standart sözleşmeler imzalandıktan sonra ayrıca izin gerekmeksizin uygulanabiliyor, **ancak imzadan itibaren 5 iş günü içinde Kurul'a bildirilmesi zorunlu.** Bildirim yükümlülüğüne uyulmamasının 2026 itibarıyla parasal yaptırımı var (milyon TL mertebesinde).

**Yetkin360 için doğrudan sonuç:** Yurt dışı bir AI sağlayıcısına CV gönderiyorsanız (CV parsing), bu bir yurt dışı aktarımdır ve bir hukuki mekanizma + bildirim gerektirir. Bunu MVP'de çözmenin iki yolu var:

- **(A) Kaçın:** CV parsing'i ya yapmayın ya da yerel/AB bölgesinde barındırılan bir model kullanın. **MVP için önerim budur.**
- **(B) Uy:** Standart sözleşme + 5 iş günü bildirim + ayrı açık rıza + aydınlatma. Tek geliştirici için bu gerçek bir yüktür.

Ayrıca Kurul'un 2026 tarihli ilke kararı uyarınca **açık rıza ve aydınlatma metinleri ayrı ayrı düzenlenmeli** — tek bir birleşik onay kutusu kullanmayın. Bu, kayıt ekranının tasarımını doğrudan etkiler.

### 17.2 Veri haritası

| Veri | Kategori | Hukuki sebep | Saklama |
|---|---|---|---|
| Ad, e-posta | Kimlik/iletişim | Sözleşme | Hesap + 6 ay |
| Eğitim, bölüm | Kişisel | Sözleşme | Hesap süresi |
| CV dosyası | Kişisel (yoğun) | **Açık rıza** | 12 ay veya silme talebi |
| Engagement/çıktı | Kişisel | Sözleşme | Kalıcı (anonimleştirilebilir) |
| Değerlendirme | Kişisel (hassas etki) | Meşru menfaat + aydınlatma | Kalıcı |
| `private_note` | Kişisel | Meşru menfaat | 24 ay |
| IP, audit | İşlem güvenliği | Hukuki yükümlülük | 12 ay |
| **Özel nitelikli veri** | — | — | **Toplanmaz. Hiç.** |

**Sert kural: Sağlık, din, siyasi görüş, sendika, ceza mahkûmiyeti gibi özel nitelikli kişisel veri hiçbir alanda toplanmaz.** Serbest metin alanlarında kullanıcıya bu konuda uyarı gösterilir. Özellikle "engellilik durumu" gibi staj süreçlerinde sorulabilecek alanları **eklemeyin**.

### 17.3 Gizli proje sorunu (dokümanın 100. bölümü)

Doküman doğru bir problemi işaret ediyor: "XYZ şirketinin yeni ürününde çalıştı" demek bile gizlilik ihlali olabilir.

**Çözüm — kademeli ifşa:**

```
engagements.confidential = true ise:
  Public profilde:  "Yazılım sektöründe bir kurumda 3 ay staj (doğrulandı)"
                    + doğrulanan yetkinlikler
                    - kurum adı YOK, proje başlığı YOK, çıktı YOK
  Doğrulama linkiyle (token ile erişen kişi):
                    kurum adı gösterilir (kurum izin verdiyse)
  Koordinatör:      tam görünürlük
```

**Kritik nokta (dokümanda yok):** Gizlilik kararı **kuruma ait olmalı, öğrenciye değil** — çünkü ticari sır kurumundur. Ama öğrencinin de deneyimini gösterme hakkı vardır. Çözüm: kurum `confidential` bayrağını belirler, öğrenci bu sınır içinde kalarak gösterim seviyesini seçer. Bu ikisi arasındaki çatışma, engagement oluşturulurken **sözleşmesel olarak** çözülmelidir.

### 17.4 Kullanıcı hakları — teknik karşılıklar

| Hak | Uygulama |
|---|---|
| Erişim/taşınabilirlik | `/settings/export` → JSON + dosyalar, ZIP, 24 saatte hazır |
| Silme | Anonimleştirme akışı (§12.3); tanıklıklar olgu olarak kalır — **bu kayıt sırasında açıkça bildirilir** |
| Düzeltme | Profil düzenleme; **ama tanıklık ve değerlendirme düzeltilemez** (başkasının beyanıdır) — itiraz akışı ile |
| Rıza geri çekme | AI işleme rızası bağımsız kapatılabilir; geri çekme geçmişi etkilemez |
| İtiraz | `DISPUTED` durumu + koordinatör hakemliği |

---

## 18. File & Evidence Architecture

```
Yükleme:  İstemci → API (yetki + kota kontrolü)
                  → imzalı PUT URL üret
          İstemci → Object Storage (doğrudan — API'den geçmez)
          İstemci → API (yükleme tamamlandı bildirimi)
          API     → evidence kaydı (scan_status=PENDING)
                  → outbox: tarama işi
          Worker  → indir, ClamAV tara, hash hesapla, MIME doğrula
                  → scan_status=CLEAN | INFECTED
İndirme:  API (yetki kontrolü + audit) → imzalı GET URL (5 dk)
                                        → sadece scan_status=CLEAN ise
```

**Neden doğrudan storage'a yükleme:** Büyük dosyaların API sunucusundan geçmesi worker'ları bloke eder ve tek VPS'te bellek tüketir.

**Storage seçimi:** MVP'de MinIO (aynı VPS, S3 uyumlu) veya Cloudflare R2 (çıkış trafiği ücretsiz, S3 uyumlu). S3 API uyumluluğu sayesinde sonradan geçiş maliyetsizdir. Doküman R2/MinIO/S3'ü listeliyor ama karşılaştırmıyor; **R2 öneriyorum** — çıkış ücreti yok ve KVKK açısından bölge seçilebilir.

---

## 19. Search Architecture

**MVP:** PostgreSQL. Bitti.

- Yetkinlik filtresi → normal index'li join.
- Metin arama → `tsvector` + GIN index, Türkçe için `unaccent` + basit konfigürasyon.
- **Türkçe uyarısı (dokümanda yok):** PostgreSQL'in yerleşik Türkçe stemmer'ı yoktur. `simple` + `unaccent` kullanın; sondan eklemeli dil nedeniyle kök bulma zayıf olacaktır. Bu MVP ölçeğinde kabul edilebilir; ciddi Türkçe arama gerekirse V2'de özel sözlük.

**V2 tetikleyicisi:** >50K profil veya p95 arama süresi >500 ms **ölçüldüğünde** → materialized view. **V3:** yalnızca gerçek kanıtla → arama motoru.

**Elasticsearch/OpenSearch kararı: MVP'de Reddet.** 10M dokümanın altında ve orta sorgu hızlarında PostgreSQL FTS uygulaması daha hızlı, işletmesi daha ucuz ve bakımı daha basit; GIN index'li FTS standart karşılaştırmalarda geri çağırma açısından Elasticsearch'e yakın sonuç veriyor. Ayrı bir arama motoru, tek geliştiriciye ikinci bir veri deposu senkronizasyonu yükü getirir — en sık görülen tutarsızlık kaynağıdır.

**pgvector: MVP'de Reddet, V2'de değerlendir.** Semantik arama, aday havuzu küçükken hiçbir şey kazandırmaz. Gerektiğinde pgvector + HNSW aynı veritabanında çalışır ve ayrı altyapı gerektirmez — bu yüzden ertelemenin maliyeti yoktur. (HNSW index'inin bellekte kalması kritik; küçük VPS'te bu bir kaynak planlama konusudur.)

---

## 20. Notification Architecture

**MVP:** In-app bildirim tablosu + işlemsel e-posta. Push, SMS, gerçek zamanlı yok.

Dokümanın 55. bölümü 8 olay türü sayıyor. **Değerlendirme: Azalt.** MVP'de sadece 5 olay:

1. E-posta doğrulama / şifre sıfırlama (işlemsel, zorunlu)
2. Engagement daveti / onayı
3. **Değerlendirme hatırlatması** (en değerli — koordinatörün elle yaptığı işi otomatikleştirir)
4. Engagement doğrulandı
5. İtiraz açıldı

**Teslimat:** outbox tablosu → worker → SMTP sağlayıcı. E-posta gönderimi asla istek döngüsünde yapılmaz.

**Güvenilirlik:** E-posta sağlayıcısı çökerse outbox birikir, geri gelince gönderilir. Kullanıcı akışı etkilenmez.

---

## 21. Testing Strategy

### 21.1 Katmanlar ve öncelik

| Katman | Kapsam hedefi | Öncelik |
|---|---|---|
| Unit (domain kuralları) | Durum geçişleri, sinyal hesabı, doğrulama kuralları | ★★★★ |
| **Authorization** | **Her uç × her aktör** | ★★★★★ **En yüksek** |
| Integration (DB) | Gerçek PostgreSQL (testcontainers), transaction davranışı | ★★★★ |
| API (sözleşme) | Şema, hata formatı, sayfalama | ★★★ |
| E2E | 2 ana senaryo (Playwright) | ★★★ |
| Güvenlik | BOLA taraması, bağımlılık taraması | ★★★★ |
| Performans | Sadece 3 kritik sorgu | ★★ |

**Neden authorization en yüksek öncelikli:** BOLA, API saldırılarının ~%40'ında görülüyor ve otomatik tarayıcılar bunu yakalayamıyor — çünkü uygulama mantığı hatasıdır, girdi doğrulama hatası değil. Tek savunma, sistematik testtir.

### 21.2 Authorization test matrisi (dokümanın istediği)

Bu matris **elle yazılmaz, parametrik üretilir** — her uç × her aktör kombinasyonu otomatik denenir.

| Aktör | Kaynak | Eylem | Beklenen |
|---|---|---|---|
| Org A üyesi | Org B engagement | Read | **404** |
| Org A üyesi | Org B engagement | Update | **404** |
| Org A üyesi | Org B need/evaluation | Read | **404** |
| Talent A | Kendi evidence | Update | 200 |
| Talent A | Talent B evidence | Read (PRIVATE) | **404** |
| Talent A | Talent B evidence | Update | **404** |
| Talent A | Kendi evaluation (`private_note`) | Read | **403 / alan yok** |
| Talent A | Kendi engagement | Status→VERIFIED | **403** (sadece kurum+koordinatör) |
| Org üyesi | Kendi kurum engagement | Evaluate | 200 |
| Org üyesi (MEMBER) | Kurum üyesi silme | Delete | **403** (sadece ADMIN) |
| Koordinatör A | Kendi kurumu engagement | Read | 200 |
| Koordinatör A | Başka üniversite engagement | Read | **404** |
| Koordinatör A | Öğrenci PRIVATE evidence | Read | **404** |
| Anonim | Public profil | Read | 200 |
| Anonim | PRIVATE profil | Read | **404** |
| Anonim | Doğrulama linki (geçerli token) | Read | 200 |
| Anonim | Doğrulama linki (iptal edilmiş) | Read | **410** |
| Platform admin | Talent PRIVATE evidence | Read | **403** (break-glass hariç) |
| Askıya alınmış kullanıcı | Herhangi bir yazma | Write | **403** |

**Kural: Yeni bir uç eklendiğinde, yetkilendirme testi olmadan CI geçmez.** Bunu bir CI kuralı olarak zorlayın (uç sayısı ile test sayısı karşılaştırması).

### 21.3 E2E senaryoları (dokümanın 46. bölümü — Kabul, güncellenmiş)

**Senaryo 1 — Staj döngüsü (ürünün özü):**
Koordinatör kurumu davet eder → Öğrenci kayıt olur → Kurum stajı oluşturur → Koordinatör onaylar → Öğrenci 4 hafta kayıt girer + 2 çıktı yükler → Kurum çıktıları kabul eder → Kurum değerlendirme formunu doldurur → Koordinatör onaylar → Doğrulanmış deneyim oluşur → Profilde yetkinlik sinyalleri görünür → Public doğrulama linki çalışır.

**Senaryo 2 — İzolasyon (güvenlik):**
İki kurum, iki öğrenci, iki üniversite oluştur → Her aktör diğerinin her kaynağını denesin → Hepsi 404.

---

## 22. DevOps / CI/CD

### 22.1 MVP dağıtımı

```
Tek VPS (Hetzner/DigitalOcean, 4 vCPU / 8 GB)
├── Caddy (reverse proxy, otomatik TLS)
├── FastAPI (systemd, uvicorn, 2-4 worker)
├── Next.js (systemd veya Vercel)
├── PostgreSQL 17 (aynı makinede — MVP için yeterli)
├── MinIO (veya harici R2)
└── worker (systemd: outbox + dosya tarama)
```

**Docker kararı:** Docker Compose **evet** (ortam tutarlılığı, kolay yeniden kurulum). **Kubernetes: Reddet.** Tek VPS'te K8s, çözdüğünden fazla problem yaratır. Dokümanın 88. bölümü bunu doğru sezmiş — Kabul.

**Yönetilen PostgreSQL mi?** MVP'de aynı makinede kabul edilebilir (maliyet). Ancak **ilk ödeyen müşteriden sonra yönetilen PostgreSQL'e geçin** — otomatik yedek ve PITR'ı kendiniz doğru kurmak, tek geliştirici için gerçek bir risktir.

### 22.2 CI pipeline

```
push → lint (ruff, eslint) → tip kontrolü (mypy, tsc)
     → unit + integration (testcontainers PostgreSQL)
     → AUTHORIZATION TESTLERİ (ayrı, zorunlu aşama)
     → güvenlik: pip-audit, npm audit, gitleaks
     → build
main → staging deploy → smoke test → manuel onay → production
```

**Migration kuralı:** Alembic migration'ları **her zaman geriye uyumlu** olmalı (önce ekle, sonra kullan, sonra eski alanı kaldır — üç ayrı deploy). Tek geliştirici için bile bu disiplin, geri alma (rollback) ihtiyacında hayat kurtarır.

### 22.3 Açık kaynak (şartname gereği — raporun ilk halinde eksikti)

Şartname platformun açık kaynak olmasını zorunlu tutuyor. Bunun somut sonuçları:

**Lisans seçimi:**

| Lisans | Ne sağlar | Bu proje için |
|---|---|---|
| **AGPL-3.0** | Ağ üzerinden sunan herkes kaynağı paylaşmak zorunda | ✅ **Önerilen.** Birinin kodu alıp kapalı SaaS yapmasını engeller. Ticarileşme opsiyonunu korur (siz çift lisanslayabilirsiniz) |
| Apache-2.0 | İzin verici + patent koruması | ⚠️ Kurumsal benimseme kolay, ama kapalı fork mümkün |
| MIT | En izin verici | ❌ Ticarileşme hedefi varken en zayıf koruma |

**Öneri: AGPL-3.0.** Gerekçe: ödül bir "geliştirme bütçesi" ve sonrasında ticarileşme opsiyonu var. AGPL, kodu açık tutarken sizin ticari pozisyonunuzu korur. Ancak bu **hackathon şartnamesiyle uyumlu mu** teyit edilmeli — bazı şartnameler izin verici lisans şart koşar (§37, açık soru).

**Diğer gereklilikler:**
- Bağımlılık lisans uyumu: GPL uyumsuz bağımlılık olmamalı (`pip-licenses` ile kontrol)
- `.env` asla repoda olmaz; `.env.example` olur (§16.5 artık kritik — repo herkese açık)
- README: problem tanımı, mimari şeması, kurulum (tek komutla `docker compose up`), demo verisi yükleme
- `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md` (güvenlik açığı bildirimi)
- Commit geçmişi temiz — jüri repoya bakabilir; tek dev bomba commit iyi görünmez

**Kritik güvenlik notu:** Repo açık olduğu için, bir yetkilendirme açığı artık herkes tarafından okunabilir durumda. Bu, §21.2'deki authorization test matrisinin önemini artırır, azaltmaz.

---

## 23. Observability

**MVP'de minimum (ama atlanmaz):**

- **Yapılandırılmış JSON log** + her istekte `request_id` (yanıt başlığında da döner — kullanıcı hata bildirdiğinde izlenebilir).
- **Hata takibi:** Sentry (ücretsiz katman yeterli).
- **Uptime:** harici ping (UptimeRobot) → `/health`.
- `/health` (canlı mı) ve `/ready` (DB bağlantısı var mı) ayrımı — dokümanın 49. bölümü doğru.
- Yavaş sorgu logu: PostgreSQL `log_min_duration_statement = 500ms`.

**Loglanmayacaklar (kritik):** şifre, token, CV içeriği, `private_note`, tam e-posta (maskeli logla). Log'lar da kişisel veri içerir ve KVKK kapsamındadır.

**Audit log ≠ uygulama logu.** Dokümanın 51. bölümü bu ayrımı doğru yapıyor — **Kabul.** Audit log iş verisidir, PostgreSQL'de durur, yedeklenir, silinmez. Uygulama logu operasyoneldir, döner (rotate), 30 günde temizlenir.

---

## 24. Backup & Disaster Recovery

| Hedef | Değer |
|---|---|
| RPO | ≤ 15 dakika (WAL arşivleme) |
| RTO | ≤ 4 saat (MVP için gerçekçi) |

- Günlük tam yedek (`pg_dump` veya `pgBackRest`) + sürekli WAL arşivi → **PITR**.
- Yedekler **farklı sağlayıcıda**, **şifreli** (yedek anahtarı sunucuda tutulmaz).
- Object storage: sürüm kontrolü (versioning) açık.
- **Ayda bir geri yükleme tatbikatı — takvime yazılır.** Test edilmemiş yedek, yedek değildir. Doküman (bölüm 50) "restore test"i listelemiş — **Kabul ve altını çiziyorum**; en sık ihmal edilen madde budur.
- Retention: günlük 7, haftalık 4, aylık 6.

---

## 25. Scalability

Doküman (bölüm 22 sorusu) "10 milyon kullanıcı" varsayımı yapmamayı söylüyor — **Kabul.**

**Gerçekçi MVP ölçeği: 1 üniversite, 300-800 öğrenci, 50-150 kurum, yılda 2 staj dönemi.** Bu, tek VPS'in kapasitesinin çok altındadır.

| Ölçek | Değişiklik |
|---|---|
| **1K kullanıcı** | Hiçbir şey. Tek VPS fazlasıyla yeter. |
| **10K** | PostgreSQL'i ayrı makineye al; index ayarı; audit log partition |
| **100K** | Yönetilen PostgreSQL + okuma replikası; birden fazla API instance + LB; **Redis** (oturum/rate limit/cache); materialized view'lar; ayrı worker makinesi |
| **1M** | Arama motoru değerlendir; okuma/yazma ayrımı; CDN; bölgesel storage; muhtemelen matching ayrı servis |

**Redis ne zaman?** Dokümanın 41. bölümünün sorduğu soru. Cevap: **birden fazla API instance çalıştırdığınız an.** Tek instance'ta in-memory cache ve PostgreSQL sayaçları yeterlidir. Redis'i erken eklemek, yedeklenmesi ve izlenmesi gereken ikinci bir durum deposu demektir.

**Queue (Celery) ne zaman?** Asenkron iş sayısı ve çeşitliliği outbox+worker ile yönetilemez hale geldiğinde. MVP'de `outbox` tablosu + basit bir polling worker, Celery'nin yaptığının %90'ını broker (RabbitMQ/Redis) kurmadan yapar. **Celery MVP'de Reddet.**

---

## 26. Business Model

### 26.1 İlk müşteri ve fiyat

**Kim öder: Üniversite bölümü / kariyer merkezi / MYO.**

- Fiyatlama: öğrenci başına yıllık ücret (ör. 40-80 TL/öğrenci/yıl) veya bölüm başına sabit yıllık lisans.
- 500 öğrencili bir bölüm → yıllık 20-40K TL. İlk 5 bölüm → sürdürülebilir başlangıç.
- Satın alma gerekçesi: koordinatör iş yükü + akreditasyon kanıtı. **ROI anlatılabilir** ("her dönem 3 hafta kazanıyorsunuz").

**Kim ödemez (MVP'de): Öğrenci ve staj veren kurum.** İkisi de ücretsiz — çünkü ikisi de arz tarafıdır ve ücret koymak benimsemeyi öldürür.

### 26.2 Cold start çözümü

Dokümanın 83. bölümü bu problemi doğru tespit ediyor ama çözmüyor.

**Çözüm: Marketplace'i baştan kurmayın.**

```
Aşama 1 (0-12 ay):  Tek üniversite, tek bölüm. Marketplace YOK.
                    Zorunlu staj süreci → öğrenciler ve kurumlar
                    ZORUNLULUK nedeniyle platformda.
                    Çıktı: 400 doğrulanmış deneyim/yıl.

Aşama 2 (12-24 ay): 5-10 bölüm. Kurum havuzu 200-500'e çıkar.
                    Kurumlar aynı üniversitenin başka öğrencilerini
                    aramaya başlar → İLK GERÇEK TALEP SİNYALİ.
                    Matching burada anlam kazanır — önce değil.

Aşama 3 (24+ ay):   Üniversiteler arası keşif.
                    Arz zaten dolu (binlerce doğrulanmış profil).
                    Marketplace artık cold start problemi olmadan açılır.
```

**Bu, bir "marketplace kurma" stratejisi değil, "önce arzı zorunlulukla doldur, sonra talebi aç" stratejisidir.** Cold start problemi, marketplace'i sonraya bırakarak çözülür.

### 26.3 Network effect

Klasik marketplace ağ etkisi **Aşama 3'e kadar yoktur** ve bunu kabul etmek gerekir.

Aşama 1-2'de işleyen şey **veri birikimi (data network effect)**: her tamamlanan staj, ürünü biraz daha değerli kılar (kurum havuzu, yetkinlik dağılımları, akreditasyon verisi). Bu daha yavaş ama daha savunulabilir bir hendektir — çünkü kopyalanamaz.

**Sızıntı (leakage) riski:** Kurum ve öğrenci platformu atlayıp doğrudan anlaşabilir. Marketplace modelinde bu ölümcüldür. **Üniversite modelinde ise sorun değil** — çünkü ürün işlemden değil, sürecin yönetiminden para kazanır ve süreç zaten üniversitenin elindedir.

### 26.4 Dokümanın iş modeli önerilerinin değerlendirmesi

| Öneri (bölüm 86) | Karar |
|---|---|
| Organization subscription | ⚠️ V2+ — kurumun ödemesi için önce havuz gerekir |
| Premium verification | ❌ **Reddet.** "Parayla daha iyi doğrulama" ürünün güvenilirliğini yok eder |
| Enterprise (SSO, analytics) | ⚠️ V3 |
| **University model** | ✅ **Kabul — ve birincil model olmalı** (doküman bunu son sıraya koymuş) |

---

## 27. MVP Scope

### Must have (bunlar olmadan ürün yok)

1. Kimlik doğrulama (kayıt, giriş, e-posta doğrulama, şifre sıfırlama)
2. Talent profili (temel bilgiler + yetkinlik beyanı, küratörlü skill listesinden)
3. Institution + koordinatör rolü
4. Organization + üyelik + domain doğrulama (T2)
5. Engagement yaşam döngüsü (DRAFT → VERIFIED, koordinatör onayı dahil)
6. Hafif görev + çıktı + kanıt yükleme (güvenli dosya akışı)
7. Yapılandırılmış değerlendirme formu (yetkinlik + davranış, `NOT_OBSERVED` dahil)
8. Attestation + VerifiedExperience üretimi (tek transaction)
9. SkillSignal türetme + profilde kanıt gösterimi
10. **Koordinatör dashboard** (durum takibi + değerlendirme hatırlatma) ← *ürünü satan ekran*
11. Public profil + public doğrulama linki
12. Object-level authorization + audit log
13. Temel admin (kurum doğrulama kuyruğu, skill yönetimi)

### Should have (değerli, MVP'siz de çalışır)

- CV parsing (AI, insan onaylı) — KVKK çözülürse
- Basit yetenek arama (kurum için, kendi üniversitesi içinde)
- İtiraz (DISPUTED) akışı
- Bildirim e-postaları (hatırlatma dışındakiler)
- Kurum için çıktı yorumlama
- Excel/PDF rapor dışa aktarma (akreditasyon için — aslında bu Must'a yakın)

### Later (kesinlikle ertele)

| Özellik | Ne zaman | Gerekçe |
|---|---|---|
| **Matching motoru** | V2 | Arz/talep yokken anlamsız |
| **Need entity + marketplace** | V2 | Cold start |
| Semantic search / pgvector | V2-V3 | Ölçek gerekçesi yok |
| Elasticsearch | V3 veya asla | PostgreSQL yeterli |
| Chat | **V3 veya asla** | Moderasyon, spam, gerçek zamanlı altyapı — devasa yük, küçük değer. E-posta yeterli |
| **Gamification / badge** | **Asla (bu üründe)** | Akademik/kurumsal ciddiyeti bozar; Goodhart riski |
| **Blockchain** | **Asla** | §11.5 |
| **Trust score** | **Asla** | §8.6 |
| **Assessment / test** | **Asla (bu haliyle)** | LinkedIn denedi, kapattı |
| GitHub entegrasyonu | V2 | Yüksek değerli ama MVP'yi geciktirir |
| Digital credentials (OB 3.0) | V3 | Değerli ama önce veri birikmeli |
| Mentor rolü | V2 | ORG_MEMBER yeterli |
| Gelişmiş analitik | V2 | Basit sayımlar MVP'de yeter |
| Kubernetes, microservice, Celery, Redis | Ölçek kanıtlanınca | §25 |

---

## 28. V2 Scope

Tetikleyici: **3+ üniversite, 1000+ doğrulanmış deneyim.**

- Üniversite içi yetenek arama + deterministik matching (Katman 1-2)
- Need entity (kurum ihtiyaç tanımlama)
- GitHub OAuth ile commit doğrulama (T5 kanıt)
- CV parsing (KVKK mekanizması kurulduysa)
- Kurum analitiği + üniversite akreditasyon raporları
- RLS'i ikinci güvenlik katmanı olarak ekle
- MFA
- Redis (çok instance'a geçildiyse)

## 29. V3 / Future

Tetikleyici: **10+ üniversite, gerçek kurum talebi ölçülmüş.**

- Üniversiteler arası açık keşif (gerçek marketplace)
- Semantik genişletme (pgvector)
- Open Badges 3.0 / W3C VC ile imzalı, taşınabilir credential ihracı
- Kurum ATS entegrasyonları
- Yetkinlik grafiği ve eksik yetkinlik analizi
- Mezun takibi (uzun vadeli sonuç verisi — en değerli veri seti)

---

## 30. Risks

| # | Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|---|
| 1 | **Üniversite satışı uzun sürer (kamu alım süreçleri)** | **Yüksek** | **Yüksek** | Bir bölümle ücretsiz pilot; bütçe döngüsünü (yıl sonu) hedefle |
| 2 | Kurumlar değerlendirme formunu doldurmaz | Yüksek | Yüksek | Zaten zorunlu forma bağla; 3 dakikada bitir; koordinatör hatırlatma otomasyonu |
| 3 | Öğrenciler kayıt girmez | Orta | Yüksek | Staj defterinin **yerine geçsin**, ek yük olmasın — bu tasarımın belkemiği |
| 4 | **Doğrulanmış profilin işe alımda karşılığı olmaz** | **Yüksek** | Orta | Değer önerisini "süreç yönetimi"ne dayandır; doğrulama bonus olsun |
| 5 | Sahte doğrulama ağı | Orta | **Yüksek** (güven ölür) | §8.5'in tamamı; koordinatör hakemliği |
| 6 | BOLA / veri sızıntısı | Orta | **Çok yüksek** (ürün biter) | §15.4, §21.2 |
| 7 | KVKK ihlali (özellikle AI aktarımı) | Orta | Yüksek | MVP'de AI'ı ertele veya yerel model; ayrı rıza; bildirim disiplini |
| 8 | Kapsam şişmesi | **Çok yüksek** | Yüksek | §39 listesine sadık kal; "Not Build" listesini görünür tut |
| 9 | Tek geliştirici tükenmesi / zaman aşımı | **Yüksek** | Yüksek | Gerçekçi takvim (§35); sürekli çalışan bir dilim tut |
| 10 | Üniversite kendi çözümünü yapar / var olan sistemine gömer | Orta | Yüksek | Entegrasyon (OBS) ve veri taşınabilirliği ile değer ver |

**En büyük teknik risk: BOLA.** **En büyük ürün riski: Kurumların değerlendirme formunu doldurmaması** (döngünün tek kırılma noktası — buradan sonrası çalışmaz). **En büyük ticari risk: Üniversite satış döngüsünün uzunluğu.**

### 30.1 Hackathon'a özgü riskler (§0 sonrası eklendi)

| # | Risk | Olasılık | Azaltma |
|---|---|---|---|
| H1 | **3 haftada kapsam yetişmez, hiçbir akış tam çalışmaz** | **Çok yüksek** | §35.2: tek dikey dilim. Hafta 2 sonunda ana zincir çalışmıyorsa kapsamı derhal kes |
| H2 | **Demo boş ekranlarla sunulur** | Yüksek | Seed verisi Hafta 1'de yazılır, sonda değil |
| H3 | Sunumda canlı demo çöker | Orta | Canlı URL + yedek olarak kayıtlı video; localhost'a asla güvenme |
| H4 | Jüri "bu LinkedIn'de var" der | **Yüksek** | §5.2 ve §6.1'deki ayrışma argümanı hazır olmalı: LinkedIn Skill Assessments'ı kapattı, kanıt orada sürecin yan ürünü değil |
| H5 | Jüri "ilk kullanıcıyı nereden bulacaksınız?" der | **Çok yüksek** | §0.2: üniversite giriş stratejisi cevabı |
| H6 | 6 başlığın hepsini yüzeysel yapıp hiçbirinde derinleşmeme | Yüksek | §0.3: 1, 2, 6 derin; 3, 4, 5 sade |
| H7 | Açık kaynak gereklilikleri son güne kalır (lisans, README, sır temizliği) | Orta | Hafta 1'de repo doğru kurulur |
| H8 | Ekip içi iş bölümü yok (1-3 kişi) | Orta | Kapsam dondurulurken sahiplik de dondurulur |

---

## 31. Technology Decision Matrix

| Alan | Aday 1 | Aday 2 | Aday 3 | **Karar** | Gerekçe |
|---|---|---|---|---|---|
| Backend | FastAPI | Spring Boot | NestJS | **FastAPI** | Tek kişi için hız; Pydantic doğrulama; AI ekosistemi |
| Frontend | Next.js | Vite+React | Nuxt | **Next.js** | Public profil/doğrulama sayfaları için SSR; tek çatı |
| DB | PostgreSQL | MySQL | MongoDB | **PostgreSQL** | İlişkisel domain, kısıtlar, transaction, JSONB |
| ORM | SQLAlchemy 2.0 | SQLModel | Tortoise | **SQLAlchemy 2.0** | Olgun, tipli, karmaşık sorguda esnek |
| Arama | PostgreSQL FTS | Elasticsearch | Meilisearch | **PostgreSQL FTS** | Ölçek gerekçesi yok; ikinci veri deposu yükü yok |
| Vektör | Yok | pgvector | Ayrı vektör DB | **Yok (MVP)** | Gerektiğinde pgvector aynı DB'de — ertelemek bedava |
| Cache | Yok | Redis | Memcached | **Yok (MVP)** | Tek instance; PostgreSQL yeterli |
| Kuyruk | Outbox+worker | Celery | RabbitMQ | **Outbox tablosu** | Broker'sız, transaction güvenli, basit |
| Storage | Cloudflare R2 | AWS S3 | MinIO | **R2** (veya MinIO) | Çıkış ücreti yok; S3 uyumlu |
| Auth | Kendi (cookie+JWT) | Auth0 | Keycloak | **Kendi** | Kontrol; maliyet; basit gereksinim |
| Şifre | **Argon2id** | bcrypt | scrypt | **Argon2id** | OWASP güncel önerisi |
| Deploy | VPS + Compose | PaaS | Kubernetes | **VPS + Compose** | Maliyet, basitlik, kontrol |
| CI | GitHub Actions | GitLab CI | — | **GitHub Actions** | Ücretsiz, yeterli |
| Hata takibi | Sentry | Kendi | — | **Sentry** | Ücretsiz katman yeterli |
| E-posta | Resend/Postmark | SES | Kendi SMTP | **Resend/Postmark** | Teslimat oranı; kendi SMTP'si zaman kaybı |
| AI (V2) | Küçük/hızlı model | Büyük model | Yerel model | **Yerel veya AB-bölge** | KVKK aktarım yükünü azaltır |

---

## 32. Recommended Architecture

```
┌─────────────────────────────────────────────────────┐
│  Next.js (public profil/doğrulama + uygulama)       │
└───────────────────────┬─────────────────────────────┘
                        │ httpOnly cookie + CSRF
┌───────────────────────▼─────────────────────────────┐
│  Caddy (TLS, güvenlik başlıkları, rate limit)       │
└───────────────────────┬─────────────────────────────┘
┌───────────────────────▼─────────────────────────────┐
│  FastAPI — Modüler Monolit                          │
│  api/ → services/ → models/                         │
│  ┌───────────────────────────────────────────────┐  │
│  │ Merkezî yetkilendirme: can() + scoped_*()     │  │
│  │ (TÜM veri erişimi buradan geçer)              │  │
│  └───────────────────────────────────────────────┘  │
│  auth │ talent │ org │ institution │ engagement     │
│  evidence │ attestation │ evaluation │ admin        │
└────┬──────────────────┬─────────────────┬───────────┘
     │                  │                 │
┌────▼──────┐   ┌───────▼───────┐   ┌─────▼─────────┐
│PostgreSQL │   │ Object Storage│   │ Worker        │
│ + audit   │   │ (private)     │   │ outbox, scan  │
│ + outbox  │   └───────────────┘   └───────────────┘
└───────────┘
```

Mimarinin tek "akıllı" kısmı, tüm veri erişiminin merkezî yetkilendirmeden geçmesidir. Geri kalanı kasıtlı olarak sıkıcıdır — tek geliştirici için doğru olan budur.

---

## 33. Recommended Database Schema

Bkz. §12.2 (tam DDL taslağı).

**Özet prensipler:**
1. UUIDv7 birincil anahtar (enumeration'a karşı + index locality)
2. Kısıtlar veritabanında (FK, CHECK, UNIQUE) — uygulamaya güvenilmez
3. `attestations`, `skill_signals`, `evaluations`, `audit_events`, `verified_experiences` **append-only**
4. Soft delete tabloya göre değişir; PII anonimleştirilir, olgu kalır
5. `verified_experiences` kasıtlı denormalize (snapshot)
6. `engagements.version` optimistic locking
7. `audit_events` aylık partition
8. Partial index'ler durum sorguları için (`WHERE status='PENDING_EVALUATION'`)

---

## 34. Recommended API Structure

```
POST   /api/v1/auth/register | login | logout | refresh
POST   /api/v1/auth/verify-email | forgot-password | reset-password

GET    /api/v1/me
GET    /api/v1/talents/{id}                    (visibility'ye göre)
PATCH  /api/v1/talents/me
GET    /api/v1/talents/me/skills
POST   /api/v1/talents/me/skills
DELETE /api/v1/talents/me/skills/{skillId}
GET    /api/v1/talents/me/signals              (kanıt dökümü)

GET    /api/v1/skills                          (küratörlü liste, arama)

POST   /api/v1/organizations
GET    /api/v1/organizations/{id}
POST   /api/v1/organizations/{id}/members
POST   /api/v1/organizations/{id}/verify-domain

GET    /api/v1/institutions/{id}/dashboard
GET    /api/v1/institutions/{id}/engagements   (filtre: status)
POST   /api/v1/institutions/{id}/reminders     (toplu hatırlatma)

POST   /api/v1/engagements
GET    /api/v1/engagements/{id}
POST   /api/v1/engagements/{id}/transitions    (tek geçiş ucu — durum makinesi)
POST   /api/v1/engagements/{id}/tasks
POST   /api/v1/engagements/{id}/deliverables

POST   /api/v1/evidence/upload-url             (imzalı URL)
POST   /api/v1/evidence                        (yükleme tamamlandı)
GET    /api/v1/evidence/{id}/download-url

POST   /api/v1/engagements/{id}/evaluation
POST   /api/v1/engagements/{id}/attestations
POST   /api/v1/attestations/{id}/revoke
POST   /api/v1/engagements/{id}/dispute

GET    /api/v1/public/p/{slug}                 (kimlik doğrulamasız)
GET    /api/v1/public/v/{token}                (doğrulama kaydı)

GET    /api/v1/admin/verification-queue
POST   /api/v1/admin/organizations/{id}/verification-level
```

**Not:** Durum geçişleri için tek bir `/transitions` ucu, durum makinesini tek yerde tutar ve her geçişe ayrı uç yazmaktan daha güvenlidir (her uçta yetkilendirmeyi tekrar yazma riski ortadan kalkar).

---

## 35. Project Timeline

### Dokümanın planının değerlendirmesi

Doküman (bölüm 107) 8 haftalık plan öneriyor. **Değerlendirme: Reddet — gerçekçi değil.**

Gerekçe: O 8 haftaya sığdırılan iş (auth + profil + skill + evidence + org + need + matching + collaboration + task + evaluation + test + güvenlik + deployment + frontend) tek geliştirici için **5-7 aylık** bir iştir. Bu tahmin frontend'i, güvenlik testlerini, dosya altyapısını ve hata ayıklamayı ciddi biçimde küçümsüyor. Gerçekçi olmayan takvim, kalitenin (özellikle authorization testlerinin) ilk feda edilen şey olmasına yol açar — ki bu üründe ölümcüldür.

Dokümanın 108. bölümündeki "3-4 haftalık ultra MVP" fikri ise **daha da yanıltıcı:** o kapsamda çıkan şey bir demo olur, ürün olmaz — ve dokümanın kendi amacı ("demo değil, gerçek ürün") ile çelişir.

### 35.1 Üç ayrı plan var, karıştırılmamalı

Hackathon bağlamı ortaya çıktıktan sonra tek bir takvim yeterli değil. Üç farklı ufuk var:

| Plan | Süre | Amaç | Bölüm |
|---|---|---|---|
| **A. Hackathon** | 18 Eylül – 11 Ekim (3 hafta + 3 gün) | Jüriyi ikna eden, çalışan, açık kaynak platform | §35.3 |
| **B. Geliştirme sözleşmesi** | Kazanılırsa 4 ay | Pilot uygulanabilir gerçek ürün | §35.4 |
| **C. Tam ürün** | ~24 hafta | Ticarileşebilir ürün | §35.5 |

**En sık yapılan hata: A planını C planı gibi kurgulamak.** 3 haftada 24 haftalık kapsamı hedeflerseniz, hiçbiri bitmez ve elinizde yarım ekranlar kalır. A planı, C planının **küçük ama uçtan uca çalışan bir dilimi** olmalıdır — yatay olarak kesilmiş (her katmandan biraz) değil, **dikey olarak kesilmiş** (tek senaryo, baştan sona tam).

### 35.2 Hackathon planının altın kuralı

**Tek bir uçtan uca senaryo, kusursuz çalışsın. Geri kalan her şey ikinci sırada.**

O senaryo şudur (§21.3 Senaryo 1'in kısaltılmışı):

```
Öğrenci kayıt → yetkinlik beyan eder
Kurum kayıt → doğrulanır (T2, domain)
Engagement oluşur → öğrenci çıktı yükler
Kurum değerlendirir → Attestation üretilir
VerifiedExperience oluşur → SkillSignal'ler türer
Public doğrulama linki açılır → herkes doğrulayabilir
```

Bu zincir jüriye şunu gösterir: **beyan → kanıt → tanıklık → doğrulanmış deneyim.** Bu, hiçbir rakip platformun yapmadığı şeydir ve ürünün tüm iddiası budur. Bu zincir çalışıyorsa, eksik ekranlar affedilir. Çalışmıyorsa, 40 ekran da kurtarmaz.

### 35.3 Plan A — Hackathon (18 Eylül – 11 Ekim)

| Dönem | Odak | Çıktı |
|---|---|---|
| **15-18 Eylül** (online hazırlık) | Karar kilitleme | Kapsam dondurulur, şema kesinleşir, repo + CI kurulur. **Ürün kodu yok.** |
| **Hafta 1** (18-25 Eylül) | Omurga | Auth, User/Talent/Organization/Institution, merkezî yetkilendirme (`can()` + `scoped_*`), skill taksonomisi (~150 skill), temel UI kabuğu |
| **Hafta 2** (25 Eylül - 2 Ekim) | Ana döngü | Engagement durum makinesi, çıktı yükleme, değerlendirme formu, **Attestation + VerifiedExperience + SkillSignal** |
| **Hafta 3** (2-9 Ekim) | Görünür yüz | Profil sayfası (kanıt dökümü), public doğrulama linki, kurum ve koordinatör dashboard'u, seed verisi, deploy |
| **9-11 Ekim** (İstanbul) | Sunum | Demo provası, son hata düzeltme, sunum. **Yeni özellik yok.** |

**Hafta 3'ün sonunda mutlaka olması gerekenler:**
- Canlı, erişilebilir bir URL (localhost demosu yapmayın — ağ sorunu sunumu öldürür)
- Gerçekçi seed verisi (boş ekran demo öldürür — en az 20 öğrenci, 5 kurum, 15 tamamlanmış engagement)
- Public doğrulama linki gerçekten çalışıyor (jüri telefonundan açabilmeli)
- README + lisans + kurulum talimatı (açık kaynak şartı)

**Hackathon'da kesinlikle yapılmayacaklar:** AI (hiç), matching motoru (sadece basit filtre), chat, bildirim e-postaları (in-app yeter), virüs taraması (MIME + boyut kontrolü yeterli, ClamAV'i sonraya bırakın), RLS, Redis, mobil.

**Riskli ama değerli:** Basit bir aday filtreleme ekranı (3. başlığı göstermek için). Hafta 3'te vakit kalırsa yapın, kalmazsa sunumda yol haritası olarak anlatın.

### 35.4 Plan B — 4 aylık geliştirme sözleşmesi (kazanılırsa)

Hackathon çıktısının üstüne, pilot uygulanabilir hâle getirme:

| Ay | Odak |
|---|---|
| 1 | Faz 0 (§35.5) — gerçek kullanıcı görüşmeleri + hackathon kodunun sertleştirilmesi (BOLA test matrisi, dosya güvenliği, audit) |
| 2 | Koordinatör dashboard derinleştirme, raporlama/dışa aktarma, itiraz akışı, kurum doğrulama (T3) |
| 3 | Pilot kurulumu, KVKK dokümantasyonu, yedekleme/izleme, kullanıcı eğitimi materyali |
| 4 | Pilot yürütme, geri bildirimle düzeltme, eşleştirme katmanı (deterministik) |

### 35.5 Plan C — Tam ürün (~24 hafta)

| Faz | Süre | Çıktı |
|---|---|---|
| **0. Doğrulama** | 2-3 hafta | 5 koordinatör + 5 kurum + 10 öğrenci görüşmesi. **Kod yok.** |
| **1. Temel** | 3 hafta | Proje iskeleti, auth, kullanıcı/kurum/institution, yetkilendirme çekirdeği + testleri |
| **2. Profil & Skill** | 2 hafta | Talent profili, skill taksonomisi, beyan |
| **3. Engagement çekirdeği** | 4 hafta | Durum makinesi, görev, çıktı, koordinatör onayı |
| **4. Kanıt & Dosya** | 2 hafta | Güvenli yükleme, tarama, indirme, izinler |
| **5. Değerlendirme & Doğrulama** | 3 hafta | Form, attestation, VerifiedExperience, SkillSignal |
| **6. Dashboard & Public** | 3 hafta | Koordinatör dashboard, public profil, doğrulama linki |
| **7. Sertleştirme** | 3 hafta | Güvenlik testleri, BOLA taraması, E2E, performans, erişilebilirlik |
| **8. Deploy & Pilot** | 2 hafta | Production, yedek, izleme, pilot başlangıcı |
| **Toplam** | **~24 hafta (5.5 ay)** | Çalışan, pilotlanabilir ürün |

**Faz 0 pazarlık konusu değildir** (Plan B'de 1. aya taşınmıştır). 3 hafta görüşme, 3 ay yanlış kod yazmaktan ucuzdur. Ön araştırma dokümanı bu fazı hiç içermiyor — 1. hafta doğrudan "product analysis" ile başlıyor ama gerçek kullanıcıyla konuşma adımı yok.

---

## 36. Definition of Done

Bir özellik şunların **hepsi** sağlanmadan bitmiş sayılmaz:

1. ✅ Yetkilendirme testi yazıldı (pozitif **ve** negatif — en az bir "başka kiracı erişemez" testi)
2. ✅ Girdi doğrulama Pydantic şemasıyla; response şeması **ayrı** tanımlı (ORM sızıntısı yok)
3. ✅ Veritabanı kısıtları eklendi (sadece uygulama kontrolü yetmez)
4. ✅ Durum değişikliği `AuditEvent` üretiyor
5. ✅ Transaction sınırı bilinçli seçildi; ağ çağrısı transaction dışında
6. ✅ Hata durumları ele alındı; kullanıcıya teknik detay sızmıyor
7. ✅ Erişilebilirlik: klavye + label + kontrast
8. ✅ Boş durum (empty state) tasarlandı
9. ✅ KVKK: bu veri neden toplanıyor, kim görüyor, ne zaman siliniyor — cevaplanmış
10. ✅ Migration geriye uyumlu

---

## 37. Open Questions

Kodlamadan önce **kesinleşmesi gereken** kararlar:

**Hackathon (en acil — 18 Eylül'e kadar):**
0a. Ekip kaç kişi, kim neyi sahipleniyor?
0b. Şartname izin verici lisans (MIT/Apache) şart koşuyor mu, yoksa AGPL serbest mi? (§22.3)
0c. Jüri değerlendirme kriterleri ayrıntılı yayımlandı mı? (Ağırlıklar biliniyorsa kapsam ona göre ayarlanır)
0d. Demo için gerçek bir pilot kurum/üniversite teması kurulabilir mi? (Gerçek kullanıcı referansı sunumu çok güçlendirir)

**Ürün:**
1. **Hedef: üniversite mi, açık marketplace mi?** (Revize öneri §0.2: ürün marketplace kalır, **giriş stratejisi** üniversite olur.)
2. Pilot üniversite/bölüm belirlendi mi? Erişim var mı?
3. Koordinatör bu ürüne bütçe ayırabilir mi — yoksa bu bir bitirme projesi mi? (Cevap "bitirme projesi" ise kapsam daha da daraltılmalı.)
4. Zorunlu staj mevzuatı ve üniversitenin mevcut süreci tam olarak nasıl işliyor?
5. Değerlendirme formu üniversitenin resmi formuyla uyumlu olmalı mı?

**Teknik:**
6. Skill taksonomisi kaynağı: ESCO alt kümesi mi, elle mi?
7. CV parsing MVP'de olacak mı? (KVKK kararına bağlı)
8. Kurum doğrulaması için MERSİS kontrolü elle mi, otomatik mi?
9. Public doğrulama linki gerçekten public mi, yoksa token'lı mı?
10. Mobil kullanım ne kadar kritik? (Öğrenci telefondan kayıt girecekse tasarım değişir)

**Hukuki:**
11. Aydınlatma metni ve rıza akışları avukat onayından geçecek mi?
12. Üniversite ile veri sorumlusu/veri işleyen ilişkisi nasıl kurulacak? (Bu bir sözleşme meselesi ve satışın önkoşulu)

---

## 38. Final Recommendation

**Ürünün merkezindeki mühendislik fikri sağlam: Kanıt, sürecin yan ürünü olmalıdır.**

Ama ön araştırma dokümanı bu fikri yanlış bir pakete koyuyor. Marketplace paketinde bu fikir hiç çalışma şansı bulamaz — cold start, LinkedIn rekabeti ve kurumların doğrulamaya para ödememesi üçlüsü onu boğar. LinkedIn'in tam olarak bu fikri (platform içi yetkinlik doğrulama) deneyip kapatmış olması, üzerinde ciddi düşünülmesi gereken bir veridir.

**Üç somut karar:**

**1. Giriş stratejisini değiştirin (ürünü değil).** Ürün Yetkin360 olarak kalır ve 6 başlığa hitap eder. Ama sıfırdan açık marketplace kurmayın: **üniversite staj/bitirme projesi sürecinden başlayın.** Aynı veri modeli, aynı teknik fikir, ama çalışabilir bir başlangıç bağlamı. Cold start problemi ortadan kalkar çünkü katılım zorunludur, evaluation problemi ortadan kalkar çünkü form zaten yasal olarak doldurulmaktadır, ilk ödeyen müşteri nettir. Bunu jüriye **go-to-market cevabı** olarak sunun — vizyonun daralması olarak değil, cold start'a verilmiş tek somut cevap olarak.

**2. MVP'yi yarıya indirin.** Matching, need, chat, AI, gamification, blockchain, trust score, assessment, Redis, Elasticsearch, Celery, pgvector, Kubernetes — hepsi çıksın. Kalan: staj döngüsü + doğrulama + koordinatör dashboard. **Ürünün parasını kazandıran ekran, koordinatör dashboard'udur** — dokümanda hiç tasarlanmamış olması en büyük boşluktur.

**3. Yetkilendirmeyi birinci sınıf mühendislik konusu yapın.** Bu üründe BOLA bir hata değil, varoluşsal bir tehdittir — kurumların öğrenci verisi ve değerlendirmeleri sızarsa ürün biter. Merkezî `can()` + `scoped_*()` + parametrik yetkilendirme test matrisi, MVP'nin ilk haftasından itibaren var olmalıdır, sonradan eklenmemelidir.

**Teknoloji tarafında dokümanın önerileri büyük ölçüde doğru** (FastAPI, PostgreSQL, Next.js, modüler monolit, K8s'siz deploy). Asıl sorun teknoloji seçimi değil, **kapsam ve konumlandırma.** Bu ikisi düzeltilirse ürün gerçekten inşa edilebilir.

---

## 39. What We Should NOT Build

### Asla (bu üründe)

| Yapılmayacak | Gerekçe |
|---|---|
| **Blockchain / NFT credential** | Merkezî otorite zaten var ve güveniliyor; çözdüğü problem yok. İmzalı W3C VC aynı işi bedavaya yapar |
| **Tek sayılık güven skoru** | Goodhart yasası; açıklanamaz; KVKK'da otomatik karar riski; ürünün "kanıt" iddiasıyla çelişir |
| **Gamification / rozet / seviye / liderlik tablosu** | Akademik ve kurumsal ciddiyeti bozar; yanlış davranışı teşvik eder |
| **Çoktan seçmeli yetkinlik testi** | LinkedIn denedi ve kapattı; gerçek çıktıdan zayıf sinyal |
| **AI'ın yetkinlik seviyesi belirlemesi** | Uydurma riski; ürünün temel iddiasını yok eder |
| **AI'ın aday elemesi/reddetmesi** | Etik + hukuki risk |
| **Sosyal akış / beğeni / takip** | LinkedIn klonu riski (dokümanın Risk 1'i) |
| **Ücretli "premium doğrulama"** | Doğrulamanın satılabilir olması güvenilirliği yok eder |
| **Özel nitelikli kişisel veri toplama** | Hiçbir zaman, hiçbir alanda |

### Şimdilik değil (V2/V3)

| Ertelenecek | Ne zaman |
|---|---|
| Matching motoru | 1000+ doğrulanmış profil sonrası |
| Need entity / açık marketplace | Aşama 3 |
| Chat / mesajlaşma | Muhtemelen hiç; e-posta yeterli |
| Semantic search / pgvector | Arama şikayeti **ölçüldüğünde** |
| Elasticsearch | >10M doküman veya kanıtlanmış darboğaz |
| Redis | Çok instance'a geçildiğinde |
| Celery / broker | Outbox yetersiz kaldığında |
| Kubernetes | Muhtemelen hiç |
| Microservice | §13.3 kriterleri |
| RLS | V2 (uygulama katmanı test edildikten sonra) |
| MFA | V2 |
| Mentor rolü ayrı olarak | V2 |
| GitHub entegrasyonu | V2 (yüksek değer ama MVP'yi geciktirir) |
| Open Badges 3.0 ihracı | V3 |
| Mobil uygulama | V3 (responsive web yeterli) |

---

## EK: Kodlamaya Geçmeden Kesinleşmesi Gereken Kararlar

Dokümanın son isteği buydu. Sıralı kontrol listesi:

**Bloke edici (bunlar olmadan kod yazılmamalı):**
1. ☐ Konumlandırma: giriş stratejisi üniversite mi, doğrudan açık marketplace mi? *(Diğer her şey buna bağlı — revize öneri §0.2)*
2. ☐ Hackathon kapsamı §35.3'e göre dondurulacak mı? **Ana zincir (beyan→kanıt→tanıklık→doğrulanmış deneyim) tek öncelik mi?**
3. ☐ Lisans kararı (§22.3) ve şartname uyumu teyit edildi mi?
4. ☐ Ekip iş bölümü net mi?
5. ☐ Pilot üniversite/bölüm teması kurulabildi mi? *(Hackathon için şart değil ama sunumu çok güçlendirir)*
6. ☐ Faz 0 görüşmeleri ne zaman yapılacak? *(Hackathon'da vakit yoksa Plan B ay 1'e)*

**Mimari (1. hafta başlamadan):**
6. ☐ Teknoloji stack'i onaylandı mı (§31)?
7. ☐ Yetkilendirme modeli: merkezî `can()` + `scoped_*()` kabul mü?
8. ☐ RLS MVP'de yok — onay?
9. ☐ Append-only tablo listesi kesin mi?
10. ☐ UUIDv7 + 404 politikası kabul mü?

**Domain (2. hafta):**
11. ☐ Entity listesi (§7.2) onaylandı mı? Özellikle `Attestation` ve `SkillSignal` eklenmesi
12. ☐ Doğrulama modeli: iki eksen (claim type × trust level) kabul mü?
13. ☐ Engagement durum makinesi (§10.2) kesin mi?
14. ☐ Skill taksonomisi kaynağı ve ilk 300 skill belirlendi mi?
15. ☐ Değerlendirme formu kriterleri (üniversitenin formuyla uyumlu) belirlendi mi?

**Uyum (kayıt ekranı yazılmadan):**
16. ☐ Aydınlatma metni + ayrı rıza metinleri hazır mı?
17. ☐ AI MVP'de var mı? Varsa yurt dışı aktarım mekanizması kurulu mu?
18. ☐ Saklama süreleri ve silme/anonimleştirme politikası yazılı mı?
19. ☐ Üniversite ile veri sorumlusu/işleyen sözleşme taslağı var mı?

---

## Kaynaklar

- [Burning Glass Institute — Skills-Based Hiring: The Long Road from Pronouncements to Practice](https://www.burningglassinstitute.org/research/skills-based-hiring-2024)
- [Harvard Kennedy School — Project on Workforce: Skills-Based Hiring](https://pw.hks.harvard.edu/post/skills-based-hiring-the-long-road-from-pronouncements-to-practice)
- [LinkedIn Help — Skill Assessments: no longer available](https://www.linkedin.com/help/linkedin/answer/a1690529)
- [OWASP API Security Top 10 — API1:2023 Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [OWASP API Security Top 10 — API3:2023 Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/)
- [KVKK — Kişisel Verilerin Yurt Dışına Aktarılması Rehberi](https://www.kvkk.gov.tr/Icerik/8142/Kisisel-Verilerin-Yurt-Disina-Aktarilmasi-Rehberi)
- [KVKK — Açık Rıza ve Aydınlatma Metinlerinin Ayrı Düzenlenmesi (2026/347 İlke Kararı)](https://www.kvkk.gov.tr/Icerik/8710/veri-sorumlulari-tarafindan-acik-riza-ve-aydinlatma-metinlerinin-ayri-ayri-duzenlenmesi-gerektigi-hakkinda-kisisel-verileri-koruma-kurulunun-18-02-2026-tarihli-ve-2026-347-sayili-ilke-kararina-iliskin-kamuoyu-duyurusu)
- [1EdTech — Open Badges 3.0 Standard](https://www.1edtech.org/1edtech-article/new-open-badges-30-standard-provides-enhanced-security-and-mobility/411060)
- [IMS Global — Open Badges v3.0 Specification](https://www.imsglobal.org/spec/ob/v3p0)
- [pgvector — GitHub](https://github.com/pgvector/pgvector)
- [Jobtech Alliance — From Cold Start to Liquidity: Two-Sided Marketplaces](https://jobtechalliance.com/wp-content/uploads/2026/03/Chicken-and-Egg-Dilemma-SOlving-for-two-sided-marketplaces-Jobtech-Alliance.pdf)
- [Youthall](https://www.youthall.com/) · [Kariyer.net](https://www.kariyer.net/) · [Toptalent.co](https://toptalent.co/)
