---
task_slug: fe15-auth-duzeni-sicil-gisesi
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 80
performance_target: "Lighthouse Performans >=90, Erisilebilirlik >=95"
memory_target: null
test_strategy:
  unit: 70
  integration: 25
  e2e: 5
affected_modules:
  - frontend/components/ui/auth-layout.tsx
  - frontend/app/giris/page.tsx
  - frontend/app/kayit/page.tsx
  - frontend/app/sifre-unuttum/page.tsx
  - frontend/app/sifre-sifirla/page.tsx
  - frontend/app/e-posta-dogrula/page.tsx
  - frontend/app/globals.css
---

# ATDD — fe15-auth-duzeni-sicil-gisesi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (planfrontend.md FE-15 maddesinden). Saga MCP bu oturumda bağlı değil — saga_task_id null.

## Persona
Yetkin360'a kayıt olmak/giriş yapmak isteyen öğrenci, kuruluş veya kurum kullanıcısı — platformun tüm akışı buradan başlıyor.

## Hedef (Neden)
Mevcut 5 auth sayfası ortalanmış, jenerik bir SaaS kartı şablonu (`flex items-center justify-center min-h-screen` + `max-w-md` kart) — "kağıt/mürekkep/mühür" marka diline uymuyor ve FE-12'de kurulan "sicil gazetesi" yönüyle tutarsız. Bu görev amacı **salt görsel/markasal tutarlılıktır** — mevcut form davranışı (validasyon, hata mesajları, yönlendirme, güvenlik kontrolleri) hiç değişmez.

## User Story
As a kayıt olmak/giriş yapmak isteyen kullanıcı
I want auth sayfalarının markayla tutarlı, resmi bir sicil gişesi hissi vermesini
So that platformun geri kalanıyla aynı güven ve kalite izlenimini baştan alayım

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given masaüstü genişliği, When herhangi bir auth sayfası (`/giris`, `/kayit`, `/sifre-unuttum`, `/sifre-sifirla`, `/e-posta-dogrula`) render edilir, Then iki kolonlu bir `AuthLayout` görünür: sol dar sütunda kum zeminli marka paneli (wordmark, serif tek cümle, 4 adımlı ince zincir çizgisi), sağ geniş sütunda kağıt zeminde kart-çerçevesiz form içeriği.
2. [Critical] Given mobil genişlik (375px), When herhangi bir auth sayfası render edilir, Then tek sütuna düşer: üstte ince bir marka şeridi, altında form içeriği.
3. [Critical] Given `app/globals.css`'te `--sand` token'ı yoksa, When bu görev uygulanır, Then yeni bir `--sand` token'ı (kağıt kreminden biraz daha koyu, kum tonu) eklenir ve marka paneli bu tonu kullanır — fallback olarak `--muted` kullanılmaz (token eksikse sessizce başka bir tona düşmek yerine gerçekten eklenir).
4. [Critical] Given `/giris` ve `/kayit` sayfalarındaki MEVCUT form testleri (page.test.tsx + form.test.tsx, ~25+ test — AC-2/AC-3/AC-4/AC-6/AC-9/AC-10/AC-11/AC-12 ve güvenlik testleri AC-S4/AC-S5/AC-S6), When `AuthLayout` bu sayfalara uygulanır, Then TÜM mevcut testler DEĞİŞTİRİLMEDEN ve KIRILMADAN geçer (regresyon sıfır tolerans).
5. [Critical] Given `/sifre-unuttum`, `/sifre-sifirla`, `/e-posta-dogrula` sayfalarının form mantığı (state/handler) sayfanın kendi içinde (ayrı form.tsx yok), When `AuthLayout` uygulanır, Then SADECE JSX yapısı `AuthLayout`'un children'ı olacak şekilde sarmalanır — state/handler/aria-live bağları TAŞINMAZ/bozulmaz, bu sayfaların mevcut testleri değişmeden geçer.
6. [High] Given herhangi bir auth sayfasında satır içi bir hata mesajı (`aria-live`), When `AuthLayout` içine yerleştirilir, Then `aria-live` davranışı korunur (ekran okuyucu hâlâ duyurur).
7. [High] Given sayfalar arası gezinme ("Giriş Yap"/"Kayıt Ol"/"Şifremi Unuttum" linkleri), When `AuthLayout` render edilir, Then bu linkler belirgin şekilde (marka panelinde veya form altında) görünür ve doğru route'lara gider.
8. [Medium] Given `AuthLayout` bileşeni render sırasında bir hata fırlatırsa, When bu olur, Then sayfa SESSİZCE eski görünüme düşmez (fail-fast) — hata görünür kalır, CI'da yakalanır.

## Threat Model
Çağrıldı — STRIDE-lite uygulandı: bu görev yeni bir güven sınırı/veri akışı eklemiyor (sadece dış görsel sarmalayıcı; form state/handler/validasyon/yetkilendirme mantığı hiç değişmiyor). S/T/R/I/D/E kategorilerinin hiçbiri yeni bir saldırı yüzeyi açmadığından yeni `AC-S<n>` üretilmedi. Gerçek güvenlik kontrolü AC-4'e gömülü: mevcut AC-S4 (şifre alanı hijyeni), AC-S5 (açık-redirect sanitizasyonu), AC-S6 (429 sonrası otomatik retry yasağı) testlerinin bu değişiklikten sonra da kırılmadan geçmesi zorunlu regresyon kriteridir.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Masaüstü happy path | Tam sayfa JSX (statik render) | Yok | Sol kum zeminli marka paneli + sağ kağıt zeminde form | AC-1 |
| 2 | Mobil happy path | Tek sütun JSX | Yok | Üstte ince marka şeridi, altında form | AC-2 |
| 3 | `--sand` token eksik | `globals.css`'e eklenir | CSS dosyası değişir | Marka paneli doğru tonda render edilir | AC-3 |
| 4 | Mevcut giris/kayit testleri | Test suite: PASS (değişmeden) | Yok | — | AC-4 (regresyon) |
| 5 | sifre-unuttum/sifre-sifirla/e-posta-dogrula JSX sarmalama | Test suite: PASS (değişmeden) | Mantık aynı dosyada kalır | Form davranışı aynı, sadece görsel çerçeve değişir | AC-5 (regresyon) |
| 6 | Satır içi hata mesajı | DOM'da `aria-live` attribute korunur | Yok | Ekran okuyucu hata mesajını duyurur | AC-6 |
| 7 | Sayfalar arası linkler | `href` doğru route | Yok | Linkler görünür ve tıklanabilir | AC-7 |
| 8 | AuthLayout render hatası | Hata fırlatılır (fail-fast) | Yok | Next.js'in standart error boundary'si devreye girer | AC-8 |

Kısmi başarı: Uygulanamaz — bu saf UI render görevi, DB/ağ yazması yok.
Hiçbir şey yapılamadı ama hata da yok: Uygulanamaz — sayfa her zaman render edilir (statik); render başarısız olursa AC-8 gereği hata görünür kalır, sessiz başarı yok.
Boş sonuç ↔ hata ayrımı: Uygulanamaz (bu görevde sunucu/API çağrısı yok).

## Test Strategy
Unit: 70% — `AuthLayout` bileşeninin kendi render testleri (slot içeriği, responsive class davranışı, `--sand` token kullanımı).
Integration: 25% — her 5 sayfanın `AuthLayout` içinde render olup MEVCUT testlerinin (page.test.tsx/form.test.tsx) hâlâ geçtiğinin doğrulanması.
E2E: 5% — Playwright MCP ile masaüstü/mobil viewport'ta görsel kontrol (mevcut page.test.tsx'ler zaten davranışsal e2e'yi büyük ölçüde karşılıyor).

## Benchmark / Başarı Ölçütü
Coverage Target: 80% (yeni `AuthLayout` bileşeni için; mevcut sayfaların zaten yüksek coverage'ı korunur)
Performance Target: Lighthouse Performans >=90, Erişilebilirlik >=95
Memory: Belirtilmedi (statik sayfa için anlamsız)
Görsel/UI kriteri: Evet — bu görev tamamen UI/layout odaklı, `verify` adımında `vision-test`/Playwright ZORUNLU, N/A geçilmemeli. Stitch referansı: `projects/16390705950406305270/screens/594ab6d6fe6743058b876716d0ef17cf` ("Sicil Girişi ve Kimlik Doğrulama Gişesi") — doku/malzeme dili referansı (NOT: Stitch'te form sol/belge sağ idi, bu görevde planfrontend.md'nin kendi sırası — marka sol, form sağ — esas alınır, Stitch sadece görsel dil referansı).
Diğer ölçülebilir kriterler: Mor/mavi/indigo/gradyan renk kullanımı 0. Mevcut test suite'inde regresyon 0 (tüm 69 dosya/1214+ test kırılmadan geçmeli).

## Kapsam Dışı
- Form mantığının `sifre-unuttum`/`sifre-sifirla`/`e-posta-dogrula` için ayrı bir `form.tsx` dosyasına çıkarılması — ayrı bir refactor görevi.
- Backend/API davranış değişikliği.
- Yeni bir validasyon/doğrulama kuralı eklenmesi.
- Şifre göster/gizle özelliği MEVCUT formda yoksa eklenmesi — bu davranışsal bir form değişikliği, `AuthLayout` sadece sarmalayıcı olduğu için kapsam dışı (ayrı bir görev olarak önerilebilir).
- `--sand` dışında yeni bir design token eklenmesi.

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/components/ui/auth-layout.tsx` — YENİ.
- `frontend/app/giris/page.tsx`, `frontend/app/kayit/page.tsx`, `frontend/app/sifre-unuttum/page.tsx`, `frontend/app/sifre-sifirla/page.tsx`, `frontend/app/e-posta-dogrula/page.tsx` — sarmalayıcı JSX değişir, iç mantık değişmez.
- `frontend/app/globals.css` — `--sand` token'ı eklenebilir (plan adımında doğrulanacak).
- Mevcut `frontend/app/giris/form.tsx`, `frontend/app/kayit/form.tsx` (varsa) — DOKUNULMAZ.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — git reposunun kökü proje klasöründen daha geniş olabilir. Sonraki adımlar Grep/Glob/Bash aramalarını `frontend/` klasörüyle sınırlamalı.

## Rollback Beklentisi
AuthLayout hata verirse sayfa çökmeli (fail-fast, AC-8) — sessiz fallback yok, hata CI'da/prod'da görünür kalmalı.

## Risks
- En yüksek risk: `sifre-unuttum`/`sifre-sifirla`/`e-posta-dogrula` sayfalarında JSX'i yanlış yere taşıyıp state/handler bağlarını (useState, onSubmit, aria-live referansları) koparıp mevcut testleri kırmak. Azaltma: her sayfa değişikliğinden hemen sonra o sayfanın kendi test dosyası çalıştırılmalı.
- `--sand` token'ının gerçekte globals.css'te olup olmadığı plan adımında doğrulanacak (atdd yazılırken doğrulanmadı).

## Assumptions
- `/kayit` sayfasının da `/giris` gibi ayrı bir `form.tsx`'i olduğu varsayıldı (plan adımında doğrulanacak).
- Mevcut testler `getByPlaceholderText`/`getByLabelText`/`getByRole` gibi semantik sorgular kullanıyor (layout değişikliğine duyarlı değil) — bu, AuthLayout'un testleri kırmama ihtimalini güçlendiriyor.

## Unknowns
- `--sand` token'ının gerçek HSL değeri netleşmedi (plan adımında belirlenecek, muhtemelen `--background`'dan biraz daha koyu bir kum tonu).

## Sorular ve Cevaplar (ham kayıt)
1-12: Sonnet 5 low alt-ajanı tarafından yanıtlandı (detaylı gerekçelerle) — persona, hedef, happy path, `--sand` eksikliği, JSX taşıma kapsamı, davranış sözleşmesi tablosu, benchmark, kapsam dışı, etkilenen dosyalar, test stratejisi, rollback, riskler. Tüm cevaplar yukarıdaki bölümlere işlendi.
13. Threat-model STRIDE-lite sonucu: yeni AC-S yok, gerekçe Threat Model bölümünde (orkestratör tarafından, threat-model skill'i çağrılarak).
