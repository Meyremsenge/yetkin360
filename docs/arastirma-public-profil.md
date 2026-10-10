# Araştırma — Herkese açık profil (`/p/[slug]`)

Amaç: öğrencinin doğrulanmış yetkinlik portfolyosunu, işverenin/kurumun **okumadan** anlayacağı bir vitrine dönüştürmek.
Kapsam: tasarım desenleri. Kod kararı değil; uygulama `PLAN`/prompt 1 aşama 1–2'de.

Tasarım dili sabit: kâğıt-mürekkep-mühür (aydınlık), tek vurgu çam yeşili, Source Serif 4 / IBM Plex Sans / IBM Plex Mono.
Yasaklar: mor/mavi, gradyan, blob/glow, cam efekti, emoji, sahte istatistik, gamification, trust score.

---

## 1. İncelenen ürünler ve "çalınacak" desenler

### LinkedIn profili
| Desen | Bizdeki karşılığı |
|---|---|
| Üstte kimlik bloğu: ad → tek satır başlık → konum/kurum → bağlantı aksiyonları | Hero: ad (Serif büyük) → `headline` → bölüm · sınıf · şehir · kurum. Aksiyonlar: "Linki kopyala", "QR". |
| Deneyim girişi: kuruluş logosu yerine baş harf kutusu, rol kalın, kuruluş + tarih + süre ikincil satırda | Sertifika kartı: rol (Serif) → kuruluş → Mono tarih + süre ("3 ay"). |
| Deneyimin altında "Skills: X, Y" satırı — yetkinliği deneyime bağlar | Kartta **kanıtlı yetkinlik çipleri** — hangi yetkinliğin hangi deneyimden geldiği bir bakışta. |

**Almıyoruz:** takipçi/bağlantı sayısı, "Endorse" (kanıtsız onay — tam da çözdüğümüz problem), aktivite akışı, reklam/öneri sütunu.

### Credly / Accredible (dijital rozet ve sertifika sayfaları)
| Desen | Bizdeki karşılığı |
|---|---|
| Her kaydın **kim tarafından** verildiği belirgin; veren kuruluş adı rozetin hemen altında | Kartta "Tanıklık eden: {kuruluş}" + güven seviyesi (T-seviyesi insan dilinde). |
| "Verify" düğmesi → bağımsız doğrulama sayfası | Her kartta **"Doğrulamayı gör ↗"** → `/v/{token}`. Profilin güvenilirliği tek tek kayıtlara bağlanır. |
| Kazanılan becerilerin çip listesi; "Earning criteria" bölümü | "Bu kayıtlar nasıl doğrulandı?" → `ChainLegend` 4 adım. |
| Paylaş + QR + yazdır | Hero'da Linki kopyala + QR (SVG, bağımlılıksız tercih); print CSS ile tek tık PDF. |

**Almıyoruz:** rozet görselinin altıgen "oyun madalyası" estetiği (gamification çağrışımı), "X kişi bu rozeti kazandı" sayaçları.

### Read.cv (2025'te kapandı) — minimal CV estetiği
| Desen | Bizdeki karşılığı |
|---|---|
| Tek kolon, geniş boşluk, sol sütunda tarih / sağda içerik ızgarası | Zaman çizelgesi: solda Mono yıl/dönem sütunu, sağda kart. Gürültüsüz, "belge" hissi. |
| Bölüm başlıkları küçük ve sakin; içerik öne çıkar | Bölüm başlıkları 12px Mono eyebrow + Serif H2. |

**Almıyoruz:** tamamen tipografik, vurgu rengi olmayan yaklaşım — bizde mühür/çam doğrulanmışlığı **anlatır**, süs değildir.

### Polywork (2025'te kapandı)
| Desen | Bizdeki karşılığı |
|---|---|
| Profilin üstünde kişinin **ne yaptığını özetleyen etiket bulutu** | Yetkinlik haritası: kanıtlı yetkinlikler kategoriye göre gruplu. |

**Almıyoruz:** renkli rozet bulutu, emoji etiketleri, "collab" sosyal ağ katmanı.

### GitHub profili
| Desen | Bizdeki karşılığı |
|---|---|
| Katkı grafiği: zaman içinde emeği **ölçüsüyle** gösteren yoğunluk ızgarası | Hero altındaki **güven şeridi** ve isteğe bağlı küçük "dönem çubuğu" (deneyimlerin zaman ekseni). Isı haritası yok — veri az (3-4 kayıt); seyrek ızgara boş görünür. |
| Sabitlenmiş (pinned) öğeler | İlk sıradaki deneyim en güçlü/son kayıt; ayrıca sabitleme özelliği MVP dışı. |
| README ile kişisel anlatı | `headline` tek satır. Uzun "Hakkımda" prompt 2'nin işi; burada kendi beyanı doğrulanmışla **karışmaz**. |

### Behance
| Desen | Bizdeki karşılığı |
|---|---|
| Büyük, görsel ağırlıklı proje kartları | Sertifika kartı geniş ve "belge" gibi: çift çerçeve, mühür köşede, hover'da hafif kalkış. |

**Almıyoruz:** görsel kapak fotoğrafı (stok görsel yasağı), beğeni/görüntülenme sayıları.

### Europass CV
| Desen | Bizdeki karşılığı |
|---|---|
| Kurumsal, yazdırılabilir, standart bölüm sırası (kişisel → deneyim → beceri) | Print CSS: üst bar/aksiyonlar gizli, beyaz zemin, sayfa kırılımı kart ortasında olmaz, URL ve QR alt bilgide. Jüri "CV olarak çıkar" dediğinde hazır. |
| Beceri seviyesi açıkça adlandırılmış (A1–C2 gibi) | Güç seviyesi **insan dilinde**: "Güçlü kanıt / Orta / Zayıf" — puan, yüzde, yıldız değil. |

### Apple / Stripe ürün sayfaları — hikâye anlatımı
| Desen | Bizdeki karşılığı |
|---|---|
| Her bölüm **tek bir iddia + kanıtı**; kısa başlık, altında açıklama | Bölüm sırası bir hikâye: *Kim?* (hero) → *Ne kadar güvenilir?* (güven şeridi) → *Ne biliyor?* (yetkinlik haritası) → *Nerede kanıtladı?* (zaman çizelgesi) → *Neden inanayım?* (nasıl doğrulandı). |
| Büyük sayı + küçük etiket ("istatistik blokları") | Güven şeridi: Serif 32px sayı + 12px etiket — **yalnız gerçek veri**, sayma animasyonu yok. |
| Ölçülü hareket: tek bir "keyif anı" | Kart ilk görünüşte mühür `y360-stamp` — sayfada tek keyif anı; reduced-motion'da kapalı. |

**Almıyoruz:** paralaks, kaydırınca beliren bölümler, video arka plan, koyu tema (brif §4 yasakları).

---

## 2. Bizim için sentez — sayfa hikâyesi

1. **Hero (kim?)** — ad, headline, bölüm · sınıf · şehir · kurum; "Doğrulanmış yetkinlik sicili" Mono etiketi; sağda sakin mühür motifi; Linki kopyala + QR.
2. **Güven şeridi (ne kadar güvenilir?)** — "X doğrulanmış deneyim · Y kanıtlı yetkinlik · Z kuruluş tanıklığı". Hepsi API'den sayılır; sıfırsa şerit gösterilmez.
3. **Yetkinlik haritası (ne biliyor?)** — kategoriye göre gruplu çipler; çipte güç seviyesi (dolu/yarım/boş 3 nokta + metin etiketi). Mühürlü = en az bir tanıklık; mühürsüz kategori yok çünkü public sayfada **yalnız kanıtlı** yetkinlik gösterilir (kendi beyanı burada yer almaz → prompt 2 ayrı bölüm).
4. **Zaman çizelgesi (nerede kanıtladı?)** — sertifika kartları; rol, kuruluş + güven rozeti, dönem + süre, tanıklık türü, yetkinlik çipleri, "Doğrulamayı gör ↗".
5. **Nasıl doğrulandı? (neden inanayım?)** — `ChainLegend` 4 adım + tek cümle.
6. **Alt bilgi** — "Yetkin360 nedir?", profil URL'si (Mono), baskıda QR.

**Kritik ilke:** doğrulanmış kayıt ile kendi beyanı görsel olarak asla karışmaz. Bu sayfada yalnız doğrulanmış veri var; çam/mühür yalnız doğrulanmışa aittir.

---

## 3. Veri ihtiyacı (aşama 1'e girdi)

| Alan | Kaynak | Not |
|---|---|---|
| `headline`, `department`, `study_year`, `city` | `talent_profiles` | Zaten var; public yanıtta yok. Profil PUBLIC olduğu için sahibi bunları vitrine koymayı seçmiş sayılır. |
| `institution_name` + güven seviyesi | `talent_profiles.institution_id → institutions` | Yalnız ad + seviye. |
| Deneyim başına `public_token` | `verified_experiences.public_token` | `/v/{token}` linki için. Deneyim zaten PUBLIC filtreli. |
| Deneyim başına kanıtlı yetkinlikler + `claim_type` + tanıklık eden kuruluş + güven seviyesi | `attestations` + `skills` | `/v` ucunun mantığı yeniden kullanılır. |
| Yetkinlik başına güç seviyesi + kategori | `skill_signals.strength`, `skills.category` | Yalnız PUBLIC deneyimlere bağlı sinyaller sayılır (PRIVATE deneyimden sızıntı yok). |
| **Asla** | — | e-posta, user_id, talent_id, private_note, kanıt dosyaları, PRIVATE deneyimler. |

Bilinen engel: `verified_experiences.visibility` varsayılanı PRIVATE ve değiştiren uç yok → public profil her zaman boş. Aşama 1'de `PATCH` ucu + Profil'de anahtar gerekir.

---

## 4. Alınmayacaklar (ve neden)

| Desen | Neden almıyoruz |
|---|---|
| Endorsement / "onayla" butonu | Kanıtsız onay — ürünün varlık nedeni bunun tersi. |
| Takipçi, görüntülenme, beğeni sayıları | Sosyal ağ gürültüsü; sahte prestij; MVP dışı. |
| Rozet madalyaları, seviye/puan, ilerleme yüzdesi | Gamification ve trust score yasak listede. |
| Mor/mavi gradyan hero, cam kartlar, blob | Tasarım dili yasakları; "AI şablonu" görünümü. |
| Kapak fotoğrafı, profil fotoğrafı yükleme | Stok görsel yasağı; foto yükleme yeni dosya akışı ister (MVP dışı). Baş harf avatarı yeterli. |
| Isı haritası / katkı grafiği | 3-4 kayıtla boş ve yanıltıcı görünür. |
| "Benzer profiller", öneriler | Matching motoru yasak. |
| Sayıların sayarak artması, paralaks | Brif §4 yasakları. |
