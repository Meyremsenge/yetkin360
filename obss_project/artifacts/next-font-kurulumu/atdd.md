---
task_slug: next-font-kurulumu
jira_id: YET-249
saga_task_id: null
threat_model: not-applicable
priority: medium
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 30
  e2e: 0
affected_modules:
  - frontend/app/layout.tsx
  - frontend/app/globals.css
---

# ATDD — next-font-kurulumu

## Jira Kaynağı
[YET-249 — TASARIM-04b: next/font ile Inter/Geist eklenmesi + başlık ölçeği sabitlenmesi](https://kuyusuzyusuf123.atlassian.net/browse/YET-249) (YET-247'nin alt görevi)

User Story (Jira'dan birebir): "Konum: frontend/app/layout.tsx, frontend/app/globals.css. Kapsam: next/font ile Inter veya Geist font ailesi eklenmesi, h1/h2/h3 başlık ölçeğinin sabitlenmesi."

**Kullanıcı kararı:** Inter seçildi (Geist yerine).

## Persona
Platformu kullanan son kullanıcı (font/başlık görsel deneyim kalitesini fark eder); uygulayan geliştirici. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Hedef (Neden)
Font tanımsızlığı (tarayıcı varsayılanı) işletim sistemine göre değişen tutarsız bir görünüme yol açıyor (Windows'ta Arial, Mac'te San Francisco vb.) — marka kimliği ve profesyonellik algısı zayıflıyor. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## User Story
As a platform ziyaretçisi
I want tutarlı bir yazı tipi ve başlık ölçeği görmeyi
So that platform her cihaz/işletim sisteminde aynı profesyonel görünüme sahip olsun

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `layout.tsx` `next/font/google`'dan `Inter` import eder, When sayfa render edilir, Then `document.body`'nin (veya `html`'in) computed `font-family`'sinde `"Inter"` geçer.
2. [High] Given bir geliştirici yeni bir `<h1>`/`<h2>`/`<h3>` yazıp HİÇ class vermez, When render edilir, Then `globals.css`'teki `@layer base` kuralından miras alarak sırasıyla `text-3xl font-bold`/`text-2xl font-bold`/`text-xl font-semibold` uygulanır.
3. [Critical] Given mevcut bir sayfanın kendi `<h1 className="text-xl font-bold">` gibi bir class'ı var (migrasyon bu görevde yapılmıyor), When render edilir, Then Tailwind'in `@layer base` önceliği en düşük olduğundan sayfanın kendi class'ı kazanır — mevcut sayfalar görsel olarak DEĞİŞMEZ (regresyon yok).
4. [High] **AC-4 (performans/gizlilik):** Given `next/font/google` kullanılıyor, When proje derlenir (`npm run build`), Then font dosyası derleme zamanında indirilip self-host edilir — çalışma zamanında Google'a hiçbir ağ çağrısı yapılmaz (üretilen HTML/CSS'te `fonts.googleapis.com`'a bir `<link>`/`@import` OLMAMALI, font `/_next/static/media/...`'tan servis edilmeli).
5. [Critical] Given bu değişiklik mevcut tüm sayfaları (layout.tsx her sayfayı sarmalıyor) etkiliyor, When tüm frontend test suite'i (1134 test) çalıştırılır, Then hiçbiri kırılmaz (regresyon yok).

## Threat Model
Tetikleyici yok — saf UI/font/CSS değişikliği, auth/input/upload/payment/PII/multi-tenant/dış API/background job/yeni HTTP ucu yok. (`next/font` derleme zamanında self-host ettiği için runtime'da da dış bir ağ çağrısı yaratmıyor — AC-4 bunu zaten doğruluyor.)

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Render edilen durum | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — body font | `<body>`/`<html>` `font-family: Inter, ...fallback` | Yok | Tüm sayfada Inter tipografisi | AC-1 |
| 2 | h1/h2/h3 class'sız (yeni/gelecek kod) | `@layer base`'den miras: h1 `text-3xl font-bold`, h2 `text-2xl font-bold`, h3 `text-xl font-semibold` | Yok | Tutarlı başlık ölçeği | AC-2 |
| 3 | Mevcut sayfa kendi h1 class'ını veriyor (çakışma yok) | Sayfanın class'ı kazanır (Tailwind specificity) | Yok (regresyon yok) | Mevcut sayfalar görsel olarak değişmez | AC-3 |
| 4 | Font derleme zamanı self-host | Font dosyası build çıktısına gömülü, `/_next/static/media/...` | Runtime'da Google'a istek atılmaz | Offline/CSP kısıtlı ortamda bile doğru fontla yüklenir | AC-4 |
| 5 | Tüm mevcut sayfalar (regresyon) | 1134 test de PASS kalır | Yok | Hiçbir sayfa bozulmaz | AC-5 |

Kısmi başarı: N/A — font ya doğru uygulanır ya da test kırmızı kalır.
Hiçbir şey yapılamadı ama hata da yok: N/A.
Boş sonuç ↔ hata ayrımı: N/A.

## Test Strategy
Unit: 70% — `layout.tsx`'in render edilen çıktısında font class'ının/değişkeninin varlığını, `globals.css`'teki `@layer base` kurallarının varlığını doğrulayan kaynak-dosya ve render testleri.
Integration: 30% — Gerçek tarayıcıda (Browser pane) `getComputedStyle(document.body).fontFamily`'nin "Inter" içerdiğini ve üretilen HTML'de `fonts.googleapis.com`'a dışarıya giden bir `<link>` olmadığını doğrulayan canlı kontrol.
E2E: 0% — Hiçbir sayfa migrate olmadığından (ayrı YET-251) piksel-seviyesi geniş kapsamlı bir e2e'ye gerek yok.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: next/font'un kendi garantisi — derleme zamanı self-host, runtime ağ çağrısı yok (CLS/performans için olumlu).
Memory: yok
Görsel/UI kriteri: `document.body` computed `font-family`'de "Inter" geçmeli. Bu kriter `verify` adımında canlı tarayıcı kontrolüyle (Browser pane, `getComputedStyle`) doğrulanacak — tam `vision-test` akışı gerekmiyor çünkü hiçbir sayfa stili migrate olmadı, piksel etkisi minimal.
Diğer ölçülebilir kriterler: 1134 mevcut test + bu görevin yeni testleri PASS, 0 regresyon.

## Kapsam Dışı
Mevcut sayfalardaki h1/h2/h3'lerin yeni ölçeğe migrasyonu (ayrı YET-251). Marka rengi uygulaması (ayrı YET-250). *(Sonnet 5 low alt-ajanı tarafından yanıtlandı, kullanıcı onaylı Jira alt-görev ayrımı.)*

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/app/layout.tsx` — `next/font/google`'dan `Inter` import edilip `<body>`/`<html>`'e className olarak eklenecek.
- `frontend/app/globals.css` — `@layer base` içinde `h1`/`h2`/`h3` için varsayılan class'lar eklenecek.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — arama `frontend/` klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Migration gerekmiyor (saf CSS/TSX). Bir regresyon bulunursa `git revert` yeterli.

## Risks
- `layout.tsx` her sayfayı sarmaladığı için bu değişiklik TÜM sayfaları etkiliyor — AC-5'in (tam suite regresyon testi) bu riski kapsaması şart.

## Assumptions
- `next/font/google`'ın Next.js 16.3.8'de hâlâ desteklendiği (deprecated olmadığı) varsayıldı — `plan` adımında `next` sürümünün resmi dokümantasyonuyla (ya da en azından `node_modules/next`'teki tip tanımlarıyla) doğrulanmalı.

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → son kullanıcı (görsel etki), geliştirici (uygular) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef → font tutarsızlığı, marka kimliği zayıflığı (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path → body font-family Inter, h1/h2/h3 varsayılan ölçek (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → self-host (ağ bağımlılığı yok), mevcut sayfa class'ı çakışmaz (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
6. Başarı ölçütü → computed font-family Inter içerir, 1134 test PASS (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → sayfa migrasyonu (YET-251), marka rengi (YET-250) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. Bağımlılıklar → layout.tsx, globals.css, yeni npm paketi yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör doğruladı).
9. Performans/güvenlik → derleme zamanı self-host, runtime ağ çağrısı yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → migration yok, git revert (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri → kullanıcı onayı + test + canlı tarayıcı kontrolü (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → unit 70 / integration 30 / e2e 0 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. Görev slug'ı → `next-font-kurulumu` (kullanıcı onayı).
14. Font seçimi → Inter (kullanıcı onayı, Geist yerine).
