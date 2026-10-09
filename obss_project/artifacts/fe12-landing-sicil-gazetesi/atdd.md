---
task_slug: fe12-landing-sicil-gazetesi
jira_id: null
saga_task_id: null
threat_model: not-applicable
priority: high
coverage_target: 80
performance_target: "Lighthouse Performans >=90, Erisilebilirlik >=95, SEO >=90"
memory_target: null
test_strategy:
  unit: 60
  integration: 30
  e2e: 10
affected_modules:
  - frontend/app/page.tsx
  - frontend/components/ui/chain-progress.tsx
  - frontend/components/ui/verified-seal.tsx
  - frontend/messages/tr.json
---

# ATDD — fe12-landing-sicil-gazetesi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (planfrontend.md FE-12 maddesinden).
Saga MCP bu oturumda bağlı değil — saga_task_id null bırakıldı.

## Persona
Kayıtsız ziyaretçi (potansiyel öğrenci/işveren/kurum kullanıcısı) ve hackathon jürisi — ikisi aynı anda hedef kitle; landing hem gerçek pazarlama girişi hem teslim materyali.

## Hedef (Neden)
Mevcut 17 satırlık placeholder, "beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirini ve markanın (kağıt/mürekkep/mühür) somut bir kanıtını hiç göstermiyor — ziyaretçi/jüri ürünün ne yaptığını anlayamıyor. Bu görev, Stitch'te tasarlanan "Resmi Sicil Gazetesi ve İlan Panosu" yönünü (asimetrik, editoryal, gerçek mühür/belge görselli) gerçek Next.js koduna taşır.

## User Story
As a kayıtsız ziyaretçi
I want landing sayfasında ürünün ne yaptığını ve zincirin nasıl işlediğini tek bakışta anlamak
So that kayıt olmaya veya örnek bir doğrulamayı incelemeye karar verebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given ziyaretçi `/`'ye gelir, When sayfa yüklenir, Then üst bar (logo, Giriş Yap, Kayıt Ol), hero (sol 7/12 başlık+CTA, sağ 5/12 doğrulama sertifikası kartı), ChainProgress bölümü, 3 persona kartı ("Öğrenci", "Kuruluş", "Kurum"), beyan-vs-doğrulanmış karşılaştırması ve footer sırayla DOM'da render edilir.
2. [Critical] Given hero bölümü render edilir, When "Kayıt Ol" veya "Örnek bir doğrulamayı incele" CTA'sına tıklanır, Then ilgili route'a (`/kayit`, örnek doğrulama sayfası) link gider (sayfaların kendisi bu görevin kapsamında değil — sadece link doğru hedefe gider).
3. [High] Given seed verisinde gerçek rakam yoksa, When sayfa render edilir, Then "rakamlar şeridi" bölümü DOM'a hiç girmez (koşullu gizleme değil, koşullu var-olmama) — uydurma istatistik asla render edilmez.
4. [High] Given viewport 375px (mobil), When hero bölümü render edilir, Then tek sütuna düşer ve sıralama önce başlık+alt metin+2 CTA, sonra sertifika kartı görseli olur.
5. [Medium] Given `ChainProgress` bileşeni boş `status` prop'uyla (`[]`) çağrılır, When render edilir, Then hiçbir adım gösterilmez ama bileşen hata fırlatmaz (crash yok).
6. [Medium] Given `VerifiedSeal` bileşeni `name` prop'u olmadan çağrılır, When render edilir, Then sahte/placeholder isim ("Ad Soyad" gibi) render edilmez, isim alanı boş bırakılır, bileşen crash olmaz.
7. [Medium] Given kullanıcının sisteminde `prefers-reduced-motion: reduce` aktif, When sayfa/ChainProgress render edilir, Then geçiş/animasyon uygulanmaz, statik render gösterilir.
8. [Low] Given tüm metin içerikleri, When sayfa render edilir, Then hiçbir Türkçe metin doğrudan JSX içine gömülmez — tamamı `messages/tr.json`'daki `home.*` anahtarlarından gelir.

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme, kullanıcı girdisi formu, dosya yükleme/indirme, ödeme, kişisel veri (KVKK), çok kiracılı sınır, dış API çağrısı, arka plan işi, yeni HTTP endpoint'i. Hiçbiri uymuyor çünkü bu görev saf statik/pazarlama sayfası render'ı — backend çağrısı yok, kullanıcı girdisi alınmıyor, sadece mevcut auth sayfalarına link veriliyor (auth sayfalarının kendisi FE-15'te, bu görevin kapsamı dışında).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path render (desktop) | Tam sayfa JSX ağacı | Yok (statik) | Üst bar, hero (sol başlık+CTA, sağ sertifika kartı), ChainProgress, 3 persona kartı, karşılaştırma, footer sırayla | AC-1 |
| 2 | Rakamlar şeridi — seed verisi yok | `null` (hiç render edilmez) | Yok | Bölüm hiç görünmez, önceki/sonraki bölüm arası boşluk normal akar | AC-3 |
| 3 | Mobilde (375px) hero layout | Tek sütun JSX, CSS sırası değişir | Yok | Önce başlık+alt metin+2 CTA, sonra sertifika kartı görseli | AC-4 |
| 4 | ChainProgress boş status prop (`[]`) | Boş liste render, hata fırlatmaz | Yok | Component boş/minimal alan gösterir, sayfa çökmez | AC-5 |
| 5 | VerifiedSeal eksik `name` prop | Sessiz/minimal render, crash yok | Yok | İsim alanı boş geçilir, mühür ikonu yine görünür, sahte isim yazılmaz | AC-6 |
| 6 | `prefers-reduced-motion: reduce` aktif | Statik render, animasyon yok | Yok | Geçişler anında olur, hareket yok | AC-7 |

Kısmi başarı: Uygulanamaz — bu saf UI render görevi, DB/ağ yazması yok, "kısmi" bir yan etki senaryosu oluşmaz.
Hiçbir şey yapılamadı ama hata da yok: Uygulanamaz — sayfa her zaman render edilir (statik); render başarısız olursa bu bir build/compile hatasıdır, sessiz başarı senaryosu yok.
Boş sonuç ↔ hata ayrımı: Rakamlar şeridi "veri yok" durumunda DOM'a hiç girmez (AC-3) — bu kasıtlı tasarım, hata değil.

## Test Strategy
Unit: 60% — ChainProgress/VerifiedSeal bileşen render testleri (prop varyasyonları: dolu, boş, eksik alan), sayfa bölüm bileşenlerinin ayrı ayrı render testleri.
Integration: 30% — sayfa bütünlüğü (tüm bölümler doğru sırada render oluyor mu), rakamlar şeridinin koşullu gizlenmesi, tr.json anahtarlarının eksiksiz çözülmesi.
E2E: 10% — Playwright ile 375px/desktop responsive görsel kontrol, CTA linklerinin doğru route'a gittiğinin doğrulanması.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Lighthouse Performans >=90, Erişilebilirlik >=95, SEO >=90 (statik sayfa, ağır asset/gradyan yok)
Memory: Belirtilmedi (statik sayfa için anlamsız)
Görsel/UI kriteri: Evet — bu görev tamamen UI/layout odaklı, `verify` adımında `vision-test` (ve mümkünse Lighthouse MCP) ZORUNLU çalıştırılmalı, N/A geçilmemeli. Stitch referans ekranı: `projects/16390705950406305270/screens/38f4a09e6fe643c5a0229c079fea94a9` ("Resmi Sicil Gazetesi ve İlan Panosu") — asimetrik 7/5 hero, gerçek mühür görseli, eşit-olmayan zincir adımları, büyük manifesto alıntısı.
Diğer ölçülebilir kriterler: Mor/mavi/indigo/gradyan renk kullanımı 0 (lint/red-team ile doğrulanabilir — CSS'te bu tonların aranması).

## Kapsam Dışı
- Gerçek rakamlar için API entegrasyonu (seed'de veri olmadığı sürece bölüm hiç render edilmez).
- ChainProgress/VerifiedSeal'ın interaktif/canlı veri versiyonu (ileride FE-16/FE-17 bunları genişletecek) — bu görevde sadece display-only, static prop alan minimal versiyon.
- Auth sayfalarının (`/giris`, `/kayit`) kendisinin değiştirilmesi — o FE-15'in kapsamında, bu görev sadece link verir.
- next-intl/i18n altyapısının kurulumu — zaten var varsayımı, sadece `tr.json`'a `home.*` anahtarları eklenir.
- React Error Boundary eklenmesi — bileşenler zaten savunmacı yazılacağı (AC-5/AC-6) için ayrı bir Error Boundary bu görevde eklenmez.

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/app/page.tsx` — tamamen yeniden yazılır.
- `frontend/components/ui/chain-progress.tsx` — YENİ, minimal (display-only, status listesi prop alır).
- `frontend/components/ui/verified-seal.tsx` — YENİ, minimal (name/tarih/sicil-no prop alır).
- `frontend/messages/tr.json` — `home.*` anahtarları eklenir.
- Mevcut `card.tsx`, `button.tsx`, `badge.tsx` bileşenleri import edilir, değiştirilmez.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — git reposunun kökü proje klasöründen daha geniş olabilir. Sonraki adımlar (plan/code-copilot/test-copilot/red-team) Grep/Glob/Bash aramalarını `frontend/` klasörüyle sınırlamalı, kök dizinden veya parametresiz geniş kapsamda arama yapılmamalı.

## Rollback Beklentisi
Bir alt-bileşen (ChainProgress/VerifiedSeal) render hatası verirse sayfa tamamen çökmemeli — ama bu görevde ayrı bir Error Boundary eklenmiyor (Kapsam Dışı); bunun yerine bileşenler AC-5/AC-6 gereği zaten crash etmeyecek şekilde savunmacı yazılır. Build/derleme hatası durumunda normal Next.js hata sayfası davranışı kabul edilir.

## Risks
- ChainProgress/VerifiedSeal bu görevde minimal yazılacağı için, ileride FE-16/FE-17 bunları genişletirken API/prop sözleşmesi değişebilir — bu, gelecekteki bir breaking change riski taşır (kabul edilen risk, plan'ın kendi Faz sıralaması bunu öngörüyor).
- Stitch referans tasarımının bazı görsel detayları (gerçek mühür dokusu, kağıt texture) CSS/SVG ile birebir taklit edilemeyebilir — code-copilot'un en yakın pratik karşılığı üretmesi beklenir, piksel-mükemmel eşleşme zorunlu değil.

## Assumptions
- next-intl (veya proje standardı i18n kütüphanesi) zaten kurulu ve `messages/tr.json` üzerinden çalışıyor (doğrulanmadı, plan dosyasının "tr.json" referansından çıkarım).
- Seed verisinde şu an gerçek "doğrulanmış kayıt sayısı" gibi bir istatistik yok (bu yüzden AC-3 koşullu gizleme olarak yazıldı) — plan.md adımında bu doğrulanmalı.

## Unknowns
- "Örnek bir doğrulamayı incele" CTA'sının hedef route'u henüz netleşmedi (muhtemelen `/v/[token]` örnek bir sabit token ile, ama bu FE-13'ün kapsamında) — plan adımında netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Persona: Kayıtsız ziyaretçi + hackathon jürisi — ikisi aynı anda hedef kitle (Sonnet 5 low alt-ajanı tarafından yanıtlandı: landing MVP teslim materyali ve pazarlama girişi aynı sayfada, ayrı persona yok).
2. Hedef: Mevcut placeholder zinciri/markayı göstermiyor, jüri ürünü anlayamıyor (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path: ziyaretçi gelir → üst bar → hero → ChainProgress → persona kartları → karşılaştırma → CTA tıklar (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Rakamlar şeridi veri yoksa: DOM'a hiç girmez, koşullu var-olmama (Sonnet 5 low alt-ajanı tarafından yanıtlandı: plan'ın "konmaz" ifadesi literal).
5. Mobil sıralama: önce metin+CTA, sonra görsel (Sonnet 5 low alt-ajanı tarafından yanıtlandı: LCP/okuma önceliği).
6. ChainProgress boş prop: sessiz boş DOM, crash yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Davranış sözleşmesi tablosu: yukarıda, Sonnet 5 low alt-ajanı tarafından üretildi.
8. Benchmark: Lighthouse Performans>=90/Erişilebilirlik>=95/SEO>=90, coverage %80 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: statik sayfa, ağır asset yok).
9. Kapsam dışı: yukarıda listelendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Etkilenen dosyalar: yukarıda listelendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı + orkestratörün Bash ile doğrudan dosya sistemi kontrolü — ChainProgress/VerifiedSeal'ın gerçekten yok olduğu teyit edildi).
11. Test stratejisi: unit 60/integration 30/e2e 10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: UI-ağırlıklı statik sayfa).
12. Rollback: bölüm atlanıp devam eder ama ayrı Error Boundary eklenmez, bileşenler savunmacı yazılır (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. ChainProgress/VerifiedSeal bağımlılık kararı: FE-12 kapsamına minimal versiyonları dahil et (kullanıcı onayı, AskUserQuestion).
