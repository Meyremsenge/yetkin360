---
task_slug: erisilebilirlik-gecisi
jira_id: YET-117
saga_task_id: null
threat_model: not-applicable
priority: medium
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 80
  integration: 20
  e2e: 0
affected_modules:
  - frontend/components/ui/success-banner.tsx (yeni)
  - frontend/app/profil/profile-form.tsx
  - frontend/app/profil/skills-section.tsx
  - frontend/app/calismalar/[id]/transition-actions.tsx
  - frontend/app/kayit/form.tsx
  - frontend/app/e-posta-dogrula/page.tsx
  - frontend/app/sifre-unuttum/page.tsx
  - frontend/app/sifre-sifirla/page.tsx
  - frontend/app/admin/skiller/page.tsx
  - frontend/app/admin/dogrulama-kuyrugu/page.tsx
---

# ATDD — erisilebilirlik-gecisi

## Jira Kaynağı
[YET-117 — [PLAN 3.13] Erişilebilirlik geçişi: klavye, focus, kontrast, aria-live](https://kuyusuzyusuf123.atlassian.net/browse/YET-117)
Proje: YETKIN360 (YET), tip: Görev, öncelik: Medium, atanan: Meyrsem, durum: Yapılacaklar (bu oturum başlatıyor).
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.13.\nSahip: @fe"
User Story / AC: Jira'da yok — sadece PLAN.md madde referansı var.

**Bağımlılık kontrolü:** YET-111 (3.7), YET-112 (3.8), YET-113 (3.9), YET-114
(3.10) hepsi Jira'da "Tamamlandı" ve `main`'e merge edilmiş durumda — bu
geçiş taradığı ekranların tamamı artık `main`'de mevcut.

**Kod tabanı taraması sonucu kapsam daraltması:** `.claude/rules/frontend.md`
kuralı ("Semantik HTML, her form alanında `<label>`, klavye ile tam gezinme,
görünür focus, kontrast 4.5:1, hata mesajları `aria-live` ile duyurulur")
zaten MVP'den beri uygulanıyor — hata bandı (`ErrorBanner`, `role="alert"`)
ve form input'ları (`components/ui/input.tsx`, `focus:ring-2`) büyük ölçüde
DOĞRU. İki somut, sistemik boşluk bulundu (aşağıya bkz.), geçiş bunlara
odaklanıyor — 25 sayfayı tek tek elden geçirmek yerine.

## Persona
Ekran okuyucu kullanıcısı ve klavye-only kullanıcısı (fare kullanamayan/
kullanmayan). İkincil: düşük görüşlü kullanıcı (kontrast). Müşteri kamu
üniversitesi olabilir (İSTKA) — erişilebilirlik satın alma şartı olabilir.

## Hedef (Neden)
Ekran okuyucu kullanıcısının durum değişikliklerini (kayıt başarılı, seviye
güncellendi vb.) kaçırmasını ve klavye kullanıcısının bir modal içinde/
dışında odağını kaybetmesini önlemek — somut, tespit edilmiş iki riski
kapatmak.

## User Story
As a ekran okuyucu / klavye-only kullanıcı
I want form gönderimi sonrası başarı mesajlarını duymak ve modal'larda
odağımı kaybetmemek
So that platformu bağımsız olarak, yardımcı teknolojiyle kullanabilirim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given bir kullanıcı ekran okuyucuyla bir formu (profil, kayıt, şifre sıfırlama, e-posta doğrulama, admin seviye güncelleme/skill oluşturma) başarıyla gönderir, When başarı bandı DOM'a eklenir, Then `role="status"` (`aria-live="polite"` implicit) sayesinde mesaj otomatik duyurulur — kullanıcının bandı aramasına gerek kalmaz.
2. [Critical] Given admin `/admin/skiller` sayfasında "Birleştir" (merge) modal'ını açar, When modal açıkken Tab tuşuna basılır, Then odak modal İÇİNDE kalır (focus trap) — modal arkasındaki sayfa elemanlarına Tab ile geçilemez.
3. [Critical] Given merge modal'ı açıkken kullanıcı Escape tuşuna basar, When modal kapanır, Then odak modal'ı açan tetikleyici butona geri döner.
4. [High] Given bir sayfada mevcut yeşil başarı bandı (`bg-green-50` ile işaretli, `role` olmadan) `SuccessBanner` bileşenine geçirilir, Then görsel stil (renk, kenarlık, metin) DEĞİŞMEZ — sadece `role="status"` eklenir (regresyon yok).
5. [Medium] Given `ErrorBanner` (zaten `role="alert"` kullanıyor), Then bu görevde DEĞİŞTİRİLMEZ — zaten doğru.
6. [Medium] Given merge modal'ı açık, When kullanıcı modal dışına tıklar (mouse) VEYA Escape'e basar, Then her iki durumda da modal kapanır ve `mergeDialog` state'i `null` olur (mevcut davranış korunur, sadece Escape/focus-trap eklenir).

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/
yetkilendirme (bu görev mevcut hiçbir auth/authz mantığına dokunmuyor, sadece
görsel/erişilebilirlik davranışı ekliyor), kullanıcı girdisi (form alanları
zaten var, yeni bir girdi alanı eklenmiyor), dosya yükleme/indirme (yok),
çok kiracılı sınır (yok), dış API çağrısı (yok) — hiçbiri uymadı çünkü bu
görev yalnızca mevcut UI bileşenlerine ARIA rolü/klavye davranışı ekliyor,
yeni bir veri/yetki yüzeyi açmıyor.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (form başarıyla gönderilir) | Yok (frontend-only, API zaten var) | `SuccessBanner` DOM'a `role="status"` ile eklenir | Ekran okuyucu mesajı otomatik duyurur, görme engelli olmayan kullanıcı aynı yeşil bandı görür | AC-1, AC-4 |
| 2 | Modal açıkken Tab | Yok | Focus trap: son odaklanabilir elemandan Tab → ilk elemana döner (ve tersi Shift+Tab) | Odak modal dışına kaçmaz | AC-2 |
| 3 | Modal Escape ile kapanır | Yok | `mergeDialog` state `null` olur, odak tetikleyici butona döner | Modal kapanır, klavye kullanıcısı nerede olduğunu kaybetmez | AC-3 |
| 4 | Girdi geçersiz/eksik | — silindi | Bu görev yeni bir form/validasyon eklemiyor, mevcut validasyon davranışı değişmiyor | — | — |
| 5 | Kaynak yok | — silindi | Frontend-only bir a11y geçişi, backend/kaynak çağrısı değişmiyor | — | — |
| 6 | Yetkisiz erişim | — silindi | Aynı gerekçe | — | — |
| 7 | Kısmi başarı (bazı sayfalar geçirildi, bazıları değil) | Yok (kod değişikliği aşamalı olabilir) | Geçirilmeyen sayfalarda eski davranış (role yok) korunur — regresyon değil, henüz kapsanmamış demektir | Geçirilen sayfalarda yeni davranış, diğerlerinde eski davranış | — |
| 8 | Hiçbir şey yapılamadı ama hata yok | N/A — bu görevde "başarısız API çağrısı" senaryosu yok, sadece statik UI değişikliği | — | — | — |

Kısmi başarı: `affected_modules` listesindeki 9 dosyanın hepsi tek bir PR'da
değiştirilir (`SuccessBanner` ortak bileşen olduğu için atomik bir refactor,
"bazısı oldu bazısı olmadı" senaryosu anlamlı değil — ya hep ya hiç, tek
commit).
Boş sonuç ↔ hata ayrımı: Bu görevde API/veri çağrısı yok, bu ayrım
uygulanmıyor.

## Test Strategy
Unit: 80% — `SuccessBanner` bileşeninin kendi testi (`role="status"` render
ediyor mu), merge modal'ının focus-trap/Escape davranışı (Testing Library +
`userEvent.tab()`/`userEvent.keyboard("{Escape}")`).
Integration: 20% — `admin/skiller/page.test.tsx`'e modal açma/kapama +
Tab-trap + Escape senaryosu eklenir; `SuccessBanner`'ı kullanan 9 dosyanın
mevcut testlerinde `role="status"` varlığı doğrulanır (mevcut testler
`getByText` ile mesajı zaten buluyor, `getByRole("status")` eklemek yeterli).
E2E: 0% — proje genelinde e2e altyapısı yok, MVP kapsamında eklenmiyor.

## Benchmark / Başarı Ölçütü
Coverage Target: 80% (mevcut proje konvansiyonu).
Performance Target: yok.
Memory: yok.
Görsel/UI kriteri: Mevcut başarı bandı görsel stili (renk/kenarlık/metin)
BİREBİR korunur — sadece ARIA rolü eklenir, regresyon yok (AC-4).
Diğer ölçülebilir kriterler: Lighthouse erişilebilirlik skoru sayısal bir
kabul kriteri DEĞİL (MVP/hackathon kapsamında) — `verify` adımında
bilgilendirici referans olarak çalıştırılabilir, ama "kritik bulgular
(GERÇEK BULGU 1 ve 2) kapatıldı" asıl kabul ölçütüdür.

## Kapsam Dışı
- Tam WCAG AA sertifikasyonu.
- Gerçek ekran okuyucu (NVDA/VoiceOver/JAWS) ile manuel uçtan uca test —
  otomatik test + kod incelemesi (red-team) yeterli sayılıyor.
- Renk paletinin/tasarım sisteminin yeniden tasarımı.
- `components/ui/button.tsx`'in focus-visible stilinin DEĞİŞTİRİLMESİ —
  kontrast/görünürlük sorunu DOĞRULANMADI (Lighthouse/manuel kontrol
  gerekiyor), doğrulanmadan spekülatif değişiklik yapılmıyor.
- Kontrast oranının (4.5:1) tüm renk kombinasyonları için elle taranması —
  bu görevde otomatik bir araç (Lighthouse/axe) çalıştırılmıyor, MVP
  kapsamında ayrı bir takip görevi olarak bırakılıyor.
- 25 sayfanın tamamının tek tek elden geçirilmesi — bu görev sistemik
  (`SuccessBanner` + 1 modal) düzeltmeye odaklanıyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/components/ui/success-banner.tsx` (yeni) — `ErrorBanner` kalıbını izler.
- `frontend/app/profil/profile-form.tsx`, `skills-section.tsx`
- `frontend/app/calismalar/[id]/transition-actions.tsx`
- `frontend/app/kayit/form.tsx`
- `frontend/app/e-posta-dogrula/page.tsx`
- `frontend/app/sifre-unuttum/page.tsx`, `sifre-sifirla/page.tsx`
- `frontend/app/admin/skiller/page.tsx` (SuccessBanner geçişi + merge modal focus-trap/Escape)
- `frontend/app/admin/dogrulama-kuyrugu/page.tsx`
- Backend'de değişiklik YOK.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup
olmadığı ayrıca kontrol edilmedi. Sonraki adımlarda arama proje klasörüyle
(`yetkin360/`) sınırlanmalı.

## Rollback Beklentisi
Bu görev frontend-only, statik UI değişikliği — API/DB çağrısı yok, rollback
kavramı (transaction/veri geri alma) uygulanmıyor. Bir değişiklik görsel
regresyon yaratırsa `git revert` yeterli.

## Risks
- `Button` bileşeninin focus-visible kontrastı doğrulanmadı — bu görevde
  DOKUNULMUYOR (kapsam dışı), ama gelecekte Lighthouse taramasıyla ayrı bir
  görev olarak açılması önerilir.
- Jira'daki atanan kişi (Meyrsem) ile bu oturumu başlatan kullanıcı arasında
  aynı çakışma (bkz. YET-114) burada da geçerli.

## Assumptions
- `role="status"` (assertive DEĞİL) doğru seçim — başarı mesajları
  kullanıcının akışını kesmemeli, bu yüzden `role="alert"` değil `role="status"`
  kullanılacak (Sonnet 5 low alt-ajanı tarafından teyit edildi, ama kod
  yazılırken bu netlik korunmalı — "assertive" ile karıştırılmamalı).
- Coverage %80 ve test oranı 80/20/0 — proje genel konvansiyonundan
  varsayıldı, kullanıcı onayı bekliyor.

## Unknowns
- Kontrast oranı (4.5:1) taramasının bu görevde mi yoksa ayrı bir takip
  görevinde mi yapılacağı netleşmedi — bu ATDD'de kapsam dışı bırakıldı
  (bkz. Kapsam Dışı), kullanıcı isterse dahil edilebilir.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Ekran okuyucu + klavye-only + düşük görüşlü kullanıcı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: frontend.md kuralı + İSTKA paydaşı.)
2. Ana hedef → İki somut riski (durum değişikliği kaçırma, modal'da odak kaybı) kapatmak. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
3. Happy path → Tab ile form → submit → SuccessBanner role=status ile otomatik duyurulur. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
4. Edge case'ler → modal focus-trap (Tab modal dışına kaçmaz), Escape ile kapanınca odak tetikleyiciye döner. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
5. Kapsam → Sistemik (SuccessBanner + 1 modal) + kalan sayfalar için otomatik tarama, 25 sayfa elle değil. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — bu ATDD'nin temel kapsam kararı.)
6. Davranış sözleşmesi ilkesi → Tek bileşen, tek davranış (SuccessBanner her yerde aynı). (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
7. Başarı ölçütü → Sayısal Lighthouse hedefi yok, "kritik bulgular kapatıldı" yeterli. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — varsayım, onay bekliyor.)
8. Kapsam dışı → WCAG AA sertifikasyonu, manuel ekran okuyucu testi, palet yeniden tasarımı, Button'a doğrulanmadan dokunma. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
9. Bağımlılıklar → SuccessBanner + 9 dosya + merge modal, Button opsiyonel/kapsam dışı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
10. Test stratejisi → 80/20/0 (unit/integration/e2e). (Sonnet 5 low alt-ajanı tarafından yanıtlandı — onay bekliyor.)
11. Kabul kriteri sahibi → Otomatik test + kod incelemesi (red-team), manuel ekran okuyucu testi kapsam dışı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
12. Risk/varsayım → role="status" = aria-live polite, assertive değil — kod yazılırken teyit edilmeli. (Sonnet 5 low alt-ajanı tarafından yanıtlandı, Assumptions'a işlendi.)
