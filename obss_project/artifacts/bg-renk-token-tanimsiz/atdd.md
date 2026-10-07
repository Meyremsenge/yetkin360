---
task_slug: bg-renk-token-tanimsiz
jira_id: YET-244
saga_task_id: null
threat_model: not-applicable
priority: critical
coverage_target: 60
performance_target: null
memory_target: null
test_strategy:
  unit: 30
  integration: 0
  e2e: 70
affected_modules:
  - frontend/app/globals.css
  - frontend/tailwind.config.ts
  - frontend/app/layout.tsx
---

# ATDD — bg-renk-token-tanimsiz

## Jira Kaynağı
[YET-244 — TASARIM-01: Sayfa arka planı/renk token'ları tanımsız — kart dışı alanlar siyah görünüyor](https://kuyusuzyusuf123.atlassian.net/browse/YET-244)

User Story (Jira'dan birebir): "Konum: frontend/app/globals.css (sadece @tailwind direktifleri, :root değişkeni yok), frontend/tailwind.config.ts:8 (theme.extend boş), frontend/app/layout.tsx:15 (body'de sınıf yok). Sorun: body/html üzerinde background-color tanımlı değil (computed: rgba(0,0,0,0)). Sistem koyu temadayken kart dışındaki her alan siyah görünüyor. Profil sayfasındaki 'devasa boş alan' da aynı kökten geliyor — içerik DOM'da var ama siyah metin saydam/siyah zeminde okunamıyor."

AC (Jira'dan birebir öneri): "globals.css'e shadcn standardı :root değişkenleri ekle (--background, --foreground, --card, --primary, --muted, --border, --destructive, --success, --warning). body { @apply bg-background text-foreground antialiased }. tailwind.config.ts'de colors: { background: \"hsl(var(--background))\", ... } bağlantısı. html { color-scheme: light } (MVP'de koyu mod gerekmiyor)."

## Persona
Giriş yapmış herhangi bir kullanıcı (aday/kurum/doğrulayıcı fark etmez) — sistem dark temadayken platformun her sayfasında kart dışı alanlar siyah görünüyor, tüm kullanıcı tiplerini etkiliyor. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı: Jira açıklaması belirli bir role özgü değil, genel bir render kusuru.)*

## Hedef (Neden)
Erişilebilirlik/okunabilirlik: body arka planı tanımsız (`rgba(0,0,0,0)`) olduğundan sistem koyu temada metin siyah zemin üzerinde siyah/saydam render oluyor, içerik DOM'da olsa da okunamıyor. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## User Story
As a giriş yapmış kullanıcı (aday/kurum/doğrulayıcı)
I want platformun her sayfasında kart dışı alanların okunabilir bir arka plan/metin renk kontrastına sahip olmasını
So that sistem temam (özellikle koyu tema) ne olursa olsun içeriği okuyabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kullanıcı herhangi bir sayfayı (örn. profil) açar, When sayfa render edilir, Then `body` elemanı `bg-background text-foreground antialiased` sınıflarını taşır ve computed `background-color` artık `rgba(0,0,0,0)` değil, `--background` token'ından gelen somut bir renktir.
2. [Critical] Given işletim sistemi koyu temadadır, When sayfa açılır, Then `html { color-scheme: light }` nedeniyle sayfa yine de light token'larla render edilir (MVP'de dark mode desteklenmiyor) — sistem temasından bağımsız tutarlı görünüm.
3. [High] Given `tailwind.config.ts`'de `colors.background: "hsl(var(--background))"` tanımlı, When `globals.css`'teki `:root` içinde karşılık gelen `--background` değişkeni de tanımlıysa, Then Tailwind class'ı geçerli bir renge çözülür (AC-4'teki ters durumla karıştırılmaz).
4. [High] Given bir komponent zaten kendi `bg-*` class'ını (örn. `bg-white`) set etmiş, When sayfa render edilir, Then o komponentin kendi rengi korunur (Tailwind specificity ile ezilmez), geri kalan body alanı token rengini alır.
5. [Medium] Given profil sayfasındaki önceden "devasa boş alan" olarak görünen bölüm, When düzeltme uygulanır, Then aynı DOM içeriği artık okunabilir kontrastla görünür (ayrı bir DOM/veri değişikliği gerekmez, sadece renk kontrastı).

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme, kullanıcı girdisi, dosya yükleme/indirme, ödeme, KVKK/kişisel veri, multi-tenant sınır, dış API çağrısı, arka plan işi, yeni HTTP ucu. Hiçbiri uymadı çünkü bu değişiklik salt frontend CSS/Tailwind token tanımı ekliyor; backend, veri erişimi veya kullanıcı girdisi işlemiyor.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Render edilen durum | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (düzeltme sonrası, light mode) | `body` sınıfı `bg-background text-foreground antialiased`, computed bg = token rengi | Yok | Açık zemin, koyu okunabilir metin, kart ile body arası net ayrım | AC-1 |
| 2 | Sistem dark mode açık (MVP'de desteklenmiyor) | `color-scheme: light` sayesinde yine light token'lar uygulanır, OS dark mode yok sayılır | Yok | Sistem ayarından bağımsız her zaman light görünüm | AC-2 |
| 3 | `tailwind.config.ts`'de token tanımlı, `globals.css`'te `:root` de tanımlı (doğru durum) | `hsl(var(--background))` geçerli renge çözülür | Yok | Beklenen açık zemin | AC-3 |
| 4 | Bir komponent zaten kendi bg rengini set ediyor (çakışma) | Komponentin kendi `bg-*` class'ı (daha spesifik) kazanır, body'nin `bg-background`'ı o alanda ezilir | Yok (beklenen Tailwind davranışı) | O komponent kendi rengini korur, geri kalan sayfa token rengini alır | AC-4 |
| 5 | Kısmi uygulama: `:root` değişkenleri `globals.css`'e eklendi ama `tailwind.config.ts`'de `colors.background` bağlanmadı | `bg-background` class'ı Tailwind tarafından tanınmaz/derlenmez (geçersiz class, stil uygulanmaz) | Build hatasız geçer ama stil hiç uygulanmaz (sessiz hata) | Sorun aynen sürer — hâlâ siyah/saydam alan görünür | AC-1 (regresyon durumu) |
| 6 | Kısmi uygulama: `tailwind.config.ts` + `globals.css` değişti ama `layout.tsx`'te `body` class'ı eklenmedi | `:root` token'ları tanımlı ve Tailwind class'ı derlenebilir durumda ama hiçbir element bunu kullanmıyor | Yok | Değişiklik etkisiz, sorun aynen sürer | AC-1 (regresyon durumu) |

Kısmi başarı: Yukarıdaki 5 ve 6 numaralı satırlar kısmi uygulamayı kapsıyor — her iki durumda da "sessiz başarı" riski var (build/derleme hatasız geçer ama görsel düzelme olmaz). Bu yüzden AC-1 sadece class varlığını değil, **computed `background-color` değerinin `rgba(0,0,0,0)` olmadığını** da doğrular (bkz. Benchmark).
Hiçbir şey yapılamadı ama hata da yok: Satır 5/6 ile aynı sınıf — derleme/build başarıyla biter ama stil uygulanmaz. Bu, salt "class eklendi mi" testiyle yakalanamaz; `vision-test`/Playwright ile computed style kontrolü zorunlu.
Boş sonuç ↔ hata ayrımı: Bu görevde "boş sonuç" kavramı yok (CSS/render değişikliği, API/veri dönüşü değil) — bu satır N/A, çünkü görev herhangi bir sorgu/liste döndürmüyor.

## Test Strategy
Unit: 30% — `body` class listesinde `bg-background text-foreground antialiased` varlığını doğrulayan bir snapshot/DOM testi (örn. React Testing Library ile layout render testi).
Integration: 0% — backend/veri katmanı yok, integration testi uygulanmaz.
E2E: 70% — Playwright/`vision-test` ile gerçek tarayıcıda `document.body` computed `background-color` değerinin token rengine eşit olduğunu ve `rgba(0,0,0,0)` olmadığını doğrulayan test; ayrıca ekran görüntüsü ile kart içi/dışı kontrast kontrolü.

## Benchmark / Başarı Ölçütü
Coverage Target: 60%
Performance Target: yok (saf CSS değişikliği, performans etkisi yok)
Memory: yok
Görsel/UI kriteri: `document.body` computed `background-color` artık `rgba(0,0,0,0)` olmamalı; body/card arası kontrast WCAG AA 4.5:1 (normal metin) eşiğini geçmeli. Bu kriter `verify` adımında `vision-test` skill'iyle kontrol edilecek.
Diğer ölçülebilir kriterler: `html` elemanının `color-scheme: light` stilini taşıdığı doğrulanır.

## Kapsam Dışı
Dark mode desteği, tema değiştirme (light/dark) toggle'ı, mevcut `bg-*` kullanan komponentlerin tek tek component-bazlı renk refactor'ü. Bunlar Jira açıklamasında istenmiyor; MVP kapsamı sadece tasarım-token iskeletiyle sınırlı. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/app/globals.css` — `:root` CSS değişkenleri (`--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--border`, `--destructive`, `--success`, `--warning`) ve `body { @apply bg-background text-foreground antialiased }` eklenecek.
- `frontend/tailwind.config.ts:8` — `theme.extend.colors` içinde token'ların `hsl(var(--...))` bağlantısı eklenecek.
- `frontend/app/layout.tsx:15` — `body` elemanına sınıf eklenecek (veya globals.css'teki `body` seçicisi zaten yeterliyse değişmeyebilir — `plan` adımında netleşir).
- (Olası, kapsam dışı tutulacak) `frontend/components/ui/*` (shadcn) bileşenlerinin hardcoded renkleri — bunlara dokunulmayacak, sadece token'ın varlığı doğrulanacak.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup olmadığı kontrol edilmedi. Sonraki adımlarda (plan/code-copilot/test-copilot/red-team) arama `frontend/` klasörüyle sınırlı tutulmalı; sınırsız `grep -r`/`git log -p --all` kullanılmamalı.

## Rollback Beklentisi
Yeni token bir bileşeni bozarsa (görsel regresyon), değişiklik `git revert` ile geri alınır; mevcut commit history'de bırakılıp üstüne düzeltme commit'i atılır (CLAUDE.md'deki "düzeltme = yeni migration/commit" ilkesiyle tutarlı).

## Risks
- Mevcut bir komponentin hardcoded rengi, yeni global token ile beklenmedik bir görsel çakışma yaratabilir (AC-4 ile test edilecek).

## Assumptions
- shadcn/ui bileşen kütüphanesi projede zaten kullanılıyor veya kullanılması planlanıyor (Jira açıklamasındaki "shadcn standardı" ifadesinden varsayıldı — `plan` adımında doğrulanmalı).

## Unknowns
- `layout.tsx:15`'teki mevcut `body` elemanının zaten bir class içerip içermediği (Jira "body'de sınıf yok" diyor ama tam içerik `plan` adımında okunarak doğrulanmalı).

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Giriş yapmış herhangi bir kullanıcı (aday/kurum/doğrulayıcı) (Sonnet 5 low alt-ajanı tarafından yanıtlandı: Jira açıklaması role özgü değil, genel render kusuru).
2. Ana hedef/neden → Erişilebilirlik/okunabilirlik, siyah zeminde siyah/saydam metin sorunu (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path → body `bg-background text-foreground` sınıflarını taşır, token rengi uygulanır, kontrast sağlanır (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → (a) sistem dark mode açık, `color-scheme: light` ile zorla light; (b) komponent kendi bg'sini set etmiş, Tailwind specificity ile korunur (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör tarafından 2 ek "kısmi uygulama" satırıyla genişletildi).
6. Başarı ölçütü → computed `background-color` ≠ `rgba(0,0,0,0)`, WCAG AA 4.5:1 kontrast (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → dark mode, tema toggle, component-bazlı refactor (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. Bağımlılıklar → layout.tsx diğer wrapper'lar, shadcn bileşenleri (dokunulmayacak) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
9. Performans/güvenlik kısıtı → yok, saf CSS değişikliği (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → git revert, yeni düzeltme commit'i (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → otomatik (vision-test) + kullanıcı onayı birlikte (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → unit 30 / e2e 70, integration 0 (Sonnet 5 low alt-ajanı tarafından yanıtlandı, saf frontend-CSS görevi olduğu için).
13. Görev slug'ı → `bg-renk-token-tanimsiz` (kullanıcı onayı, AskUserQuestion).
