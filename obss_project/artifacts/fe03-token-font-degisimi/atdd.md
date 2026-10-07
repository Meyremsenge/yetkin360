---
task_slug: fe03-token-font-degisimi
jira_id: null
saga_task_id: null
threat_model: not-applicable
priority: critical
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 60
  integration: 40
  e2e: 0
affected_modules:
  - frontend/app/globals.css
  - frontend/tailwind.config.ts
  - frontend/app/layout.tsx
---

# ATDD — fe03-token-font-degisimi

## Jira Kaynağı
Jira'ya bağlı değil — kaynak `planfrontend.md` (repo köküne push edilmiş, kullanıcı onaylı "sunum öncesi frontend yeniden tasarım" planı), görev FE-03 "Token'lar + font".

User Story (planfrontend.md §1.2/§1.3'ten birebir): "Tüm renkler HSL token; bileşenler yalnız token kullanır... Palet bilinçli olarak dar: 1 nötr aile (sıcak gri) + 1 marka rengi (çam yeşili) + 2 durum rengi (aşı boyası, tuğla)... Varsayılan Inter + Tailwind, ürünü 'şablon' gibi gösteren en büyük tek etken. Yeni eşleşme (hepsi next/font/google, npm bağımlılığı değil, hepsi latin-ext, yani Türkçe tam): Source Serif 4 (başlık), IBM Plex Sans (gövde), IBM Plex Mono (kod/doğrulama kodu)."

**Önceki iş ile ilişki (önemli bağlam):** Bu görev, daha önce aynı oturumda Jira YET-249 (Inter font) ve YET-250 (indigo `--primary`) ile yapılan işin **üzerine yazılır** — planfrontend.md keşfedildikten sonra kullanıcı bu planı takip etmeye karar verdi (Inter/indigo, planın "yapay zekâ şablonu" yasak listesine giriyor: "Mor, menekşe, indigo... yok", "Inter + text-slate-* her yerde... varsayılan 'Tailwind şablonu' görünümü").

## Persona
Birincil: demo/jüri izleyicisi (bu değişikliğin doğrudan motivasyonu). İkincil: son kullanıcı (öğrenci/kurum temsilcisi) renk/font farkını günlük kullanımda fark eder. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Hedef (Neden)
planfrontend.md §0 teşhisi: mor/mavi/Inter varsayılan Tailwind paleti "yapay zekâ ürünü yaptı" izlenimi veriyor; ayrıca mevcut Inter `subsets: ["latin"]` Türkçe karakterleri (ş, ğ, ı, ö, ç, ü) doğru render etmiyordu (latin-ext eksik). *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## User Story
As a platformu kullanan/izleyen herkes (son kullanıcı + demo izleyicisi)
I want sıcak, "kağıt/mürekkep/mühür" temalı, Türkçe karakterleri doğru render eden bir tipografi ve renk paleti görmeyi
So that platform "hazır şablon" değil, özenle tasarlanmış bir ürün izlenimi versin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `layout.tsx` üç font ailesini (`Source Serif 4`, `IBM Plex Sans`, `IBM Plex Mono`) `next/font/google`'dan import eder, When sayfa render edilir, Then `document.body`'nin computed `font-family`'sinde IBM Plex Sans (varsayılan gövde fontu) geçer.
2. [Critical] **AC-2 (Türkçe karakter desteği):** Given üç font ailesi de `subsets` içinde `"latin-ext"` ile (veya `["latin", "latin-ext"]`) tanımlanır, When Türkçe karakterli bir metin (örn. "Değerlendirme", "Çalışma") render edilir, Then glyph eksikliği/kutu karakter olmadan doğru render edilir (next/font'un ürettiği font-face kuralında `latin-ext` unicode-range'i mevcut olmalı).
3. [Critical] Given `globals.css`'teki 9 mevcut Tailwind color key'inin (`background`, `foreground`, `card`, `primary`, `muted`, `border`, `destructive`, `success`, `warning`) İSİMLERİ korunur, When bu class'lar (`bg-background`, `text-foreground` vb.) herhangi bir component'te kullanılır, Then hiçbir component dosyasına dokunulmadan yeni renkleri render ederler (CSS custom property DEĞERİ değişti, Tailwind class ADI değişmedi).
4. [High] Given yeni palet §1.2'deki HSL değerleriyle uygulanır, When `bg-background` render edilir, Then computed arka plan rengi `hsl(40, 30%, 97%)` (`--paper`) karşılığına eşittir.
5. [High] Given `success` rolünün değeri "doğrulanmış" semantiğiyle (`--pine`, `160 38% 24%`) güncellenir, When `bg-success`/`text-success` kullanan bir yer render edilir (varsa), Then yeni çam yeşili rengi alır (eski açık yeşil değil) — class ismi aynı kalır, bu bilinçli bir görsel değişikliktir, regresyon değildir.
6. [Medium] Given FE-05'in (component migrasyonu) hazırlığı için, When `tailwind.config.ts` incelenir, Then YENİ iki color key eklenmiştir: `muted-foreground` (`--ink-soft`, `30 7% 36%`) ve `verified` (`--pine`, `success` ile aynı değer, `160 38% 24%`) — bu turda hiçbir component bunları henüz KULLANMAZ, sadece token olarak tanımlıdır.
7. [Critical] Given bu değişiklik `layout.tsx` üzerinden TÜM sayfaları etkiliyor, When tüm frontend test suite'i (1155 test) çalıştırılır, Then hiçbiri kırılmaz — **Unknown (plan aşamasında doğrulanacak): hiçbir mevcut testin tam HSL/hex renk değerine `toContain` ile bağımlı olmadığı varsayılıyor, bu varsayım `plan` adımında gerçek `grep` ile kesinleştirilmeli.**

## Threat Model
Tetikleyici yok — saf UI/token/font değişikliği, auth/input/upload/payment/PII/multi-tenant/dış API/background job/yeni HTTP ucu yok.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Key | Eski değer (HSL) | Yeni değer (HSL) | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | `background` | `0 0% 100%` | `40 30% 97%` (`--paper`) | Kağıt tonu krem arka plan (saf beyaz değil) | AC-4 |
| 2 | `card` | `0 0% 100%` | `40 33% 99.5%` | Hafif daha açık kart yüzeyi (background'dan ayrışır) | AC-3 |
| 3 | `muted` | `220 13% 91%` | `38 20% 92%` (`--sand`) | Kum tonu ikincil yüzey (soğuk griden sıcak kuma) | AC-3 |
| 4 | `foreground` | `222 47% 11%` | `30 12% 12%` (`--ink`) | Neredeyse siyah mürekkep metin (soğuk lacivert yerine sıcak kömür) | AC-3 |
| 5 | `primary` | `243 75% 59%` (indigo, YET-250'den) | `30 12% 12%` (`--ink`, foreground ile AYNI) | Marka/ana buton rengi artık mürekkep siyahı — indigo/mavi TAMAMEN kaldırılır | AC-3 |
| 6 | `border` | `220 13% 91%` | `36 16% 86%` (`--line`) | İnce sıcak-ton kenarlık | AC-3 |
| 7 | `destructive` | `0 84% 60%` | `8 58% 40%` (`--brick`) | Hata/iptal rengi artık tuğla kırmızısı (daha koyu, daha az "alarm" hissi) | AC-3 |
| 8 | `success` | `120 73% 75%` | `160 38% 24%` (`--pine`) | "Doğrulanmış" rengi artık koyu çam yeşili (eski açık/pastel yeşil değil) | AC-5 |
| 9 | `warning` | `38 92% 50%` | `34 75% 32%` (`--ochre`) | "Bekliyor" rengi koyu hardal/aşı boyası (daha az parlak/cırtlak) | AC-3 |
| 10 | `muted-foreground` (YENİ) | — | `30 7% 36%` (`--ink-soft`) | Henüz hiçbir component kullanmıyor (FE-05 hazırlığı) | AC-6 |
| 11 | `verified` (YENİ) | — | `160 38% 24%` (`--pine`, success ile aynı) | Henüz hiçbir component kullanmıyor (FE-05 hazırlığı) | AC-6 |
| 12 | `font-sans` | Inter | IBM Plex Sans | Gövde/arayüz fontu değişir | AC-1 |
| 13 | `font-serif` (YENİ) | — | Source Serif 4 | Başlık/display fontu eklenir (bu turda hiçbir component `font-serif` KULLANMAZ — FE-07/FE-12 vb. ürün bileşenlerinin işi) | AC-6 |
| 14 | `font-mono` (YENİ) | — | IBM Plex Mono | Kod/tarih damgası fontu eklenir (kullanım FE-05+ işi) | AC-6 |

Kısmi başarı: N/A — token/font ya doğru tanımlanır ya da test/derleme kırmızı kalır.
Hiçbir şey yapılamadı ama hata da yok: N/A.
Boş sonuç ↔ hata ayrımı: N/A.

## Test Strategy
Unit: 60% — `globals.css`/`tailwind.config.ts`/`layout.tsx` kaynak dosyalarında yeni HSL değerlerinin, yeni color key'lerin (`muted-foreground`, `verified`) ve `latin-ext` subset'inin varlığını doğrulayan testler.
Integration: 40% — Canlı tarayıcıda (Browser pane) `getComputedStyle` ile `document.body`'nin font-family'sinin IBM Plex Sans içerdiğini, `bg-background`'ın yeni `--paper` rengine eşit olduğunu ve Türkçe karakterli bir başlığın düzgün render edildiğini doğrulayan kontrol.
E2E: 0% — Bu turda hiçbir sayfa stili (component bazında) migrate olmuyor, e2e'ye konu yok.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: next/font'un kendi self-host garantisi (3 font ailesi için de), ek ağ çağrısı yok.
Memory: yok
Görsel/UI kriteri: `document.body` computed `font-family`'de "IBM Plex Sans" geçmeli; `bg-background` computed rengi `rgb(247, 245, 241)` civarında (hsl(40,30%,97%) karşılığı) olmalı. Bu kriter `verify` adımında canlı tarayıcı kontrolüyle doğrulanacak.
Diğer ölçülebilir kriterler: 1155 mevcut test + bu görevin yeni testleri PASS, 0 regresyon (AC-7'deki Unknown varsayımı `plan` aşamasında kesinleştirilecek).

## Kapsam Dışı
`--radius` token'ı eklenmesi, `wash` varyantlarının (`pine-wash`/`ochre-wash`/`brick-wash`) eklenmesi, component (Button/Card/Badge/Alert/ErrorBanner) migrasyonu/yeni variant eklenmesi (FE-05'in işi), mevcut 652 sabit renk sınıfının (`bg-slate-*` vb.) temizliği (FE-30'un işi), `font-serif`/`font-mono`'nun gerçek kullanımı (FE-07/FE-12+ işi — bu turda sadece token olarak tanımlanır). *(Sonnet 5 low alt-ajanı tarafından yanıtlandı, planfrontend.md §3 faz ayrımıyla uyumlu.)*

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/app/globals.css` — `:root` içindeki 9 token'ın HSL değerleri güncellenecek, 2 yeni token (`--ink-soft`, hiçbiri "verified" için ayrı CSS custom property gerekmiyor çünkü `--success`'in Tailwind karşılığı zaten `--pine` değerini alacak — ayrıca `--muted-foreground`'a karşılık gelen CSS custom property de eklenecek).
- `frontend/tailwind.config.ts` — `theme.extend.colors`'a `mutedForeground`/`muted-foreground` ve `verified` eklenecek; `theme.extend.fontFamily`'ye `sans`/`serif`/`mono` eklenecek (next/font'un ürettiği CSS değişkenleri üzerinden).
- `frontend/app/layout.tsx` — Inter yerine 3 font (`Source Serif 4`, `IBM Plex Sans`, `IBM Plex Mono`) import edilip `<html>`/`<body>`'ye uygulanacak.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — arama `frontend/` klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Migration gerekmiyor (saf frontend). Bir regresyon bulunursa `git revert` yeterli — bu değişiklik önceki YET-249/YET-250 commit'lerinin üzerine yazıldığından, revert durumunda hangi commit'e dönüleceği netleştirilmeli (muhtemelen bu görevin kendi commit'i, YET-249/250'ye değil).

## Risks
- `layout.tsx` TÜM sayfaları etkiliyor — AC-7'nin (tam suite regresyon) kapsaması şart.
- **Önceki işin üzerine yazma riski:** YET-249 (Inter) ve YET-250 (indigo) commit'leri zaten push edilmiş ve Jira'da "Tamamlandı" işaretli. Bu görev onları fiilen geçersiz kılıyor — kullanıcıya commit sonrası Jira YET-249/250'nin durumunu yeniden değerlendirmesi önerilecek (bu atdd.md'nin sorumluluğu değil, `commit` adımının Saga/Jira önerisi kısmında ele alınacak).

## Assumptions
- `next/font/google`'ın `Source_Serif_4`, `IBM_Plex_Sans`, `IBM_Plex_Mono` export'larını desteklediği varsayıldı (Google Fonts kataloğunda bu üçü de mevcut) — `plan`/`code-copilot` aşamasında gerçek import adlarının doğrulanması gerekiyor (Google Fonts'taki resmi adlandırma `next/font/google`'da genelde alttan çizgiyle eşlenir, örn. `IBM_Plex_Sans`).

## Unknowns
- AC-7'deki regresyon varsayımı (hiçbir testin tam HSL/hex değerine bağımlı olmadığı) `plan` aşamasında gerçek `grep` ile doğrulanmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → demo izleyicisi (birincil) + son kullanıcı (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef → "yapay zekâ şablonu" izlenimini kırmak + Türkçe karakter desteği (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path → font-sans/serif/mono Tailwind key'leri, bg-background yeni paper rengi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → latin-ext Türkçe karakter desteği, success/pine class-isim-korumalı değer değişikliği (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör eski HSL değerlerini globals.css'ten doldurdu).
6. Başarı ölçütü → computed font-family IBM Plex Sans, bg-background yeni renk, 1155+ test PASS (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → radius/wash/component migrasyonu/652 sınıf temizliği (Sonnet 5 low alt-ajanı tarafından yanıtlandı, planfrontend.md faz ayrımıyla uyumlu).
8. Bağımlılıklar → globals.css, tailwind.config.ts, layout.tsx (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör doğruladı).
9. Performans/güvenlik → self-host, ağ çağrısı yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → migration yok, git revert (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri → kullanıcı onayı + test + canlı tarayıcı kontrolü (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → unit 60 / integration 40 / e2e 0 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. Görev slug'ı → `fe03-token-font-degisimi` (kullanıcı onayı).
14. Yön kararı → planfrontend.md takip edilecek, YET-249/250'nin üzerine yazılacak (kullanıcı onayı).
15. Bağımlılık onayları (K-1/K-2/K-3/K-5) → kullanıcı onayladı (bu görevin kapsamında değil ama genel plan onayı olarak kayıtlı).
