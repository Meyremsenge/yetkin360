---
task_slug: tasarim-sistemi-temel-bilesenler
jira_id: YET-247
saga_task_id: null
threat_model: not-applicable
priority: medium
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 85
  integration: 15
  e2e: 0
affected_modules:
  - frontend/components/ui/button.tsx
  - frontend/components/ui/card.tsx
  - frontend/components/ui/badge.tsx
  - frontend/components/ui/alert.tsx
---

# ATDD — tasarim-sistemi-temel-bilesenler

## Jira Kaynağı
[YET-247 — TASARIM-04: Tasarım sistemi kurulumu — Card/Badge/Alert bileşenleri, Button varyantları, marka rengi](https://kuyusuzyusuf123.atlassian.net/browse/YET-247)

User Story (Jira'dan birebir, TAM kapsam): "~45 yerde text-red-600, 39 yerde bg-red-50, 29 yerde bg-green-50 gibi doğrudan renk sınıfı kullanılmış — Alert bileşenine (variant: error/success/warning/info) taşınmalı. Button (ui/button.tsx) varyantsız; çağıranlar className ile rastgele renk eziyor. variant (primary/secondary/destructive/ghost) + size prop'ları eklenmeli (cva zaten shadcn kalıbında mevcut). Kart/rozet stilleri her sayfada elle tekrarlanmış — Card ve Badge bileşenleri eklenmeli. Tek bir primary marka rengi seçilmeli. Font tanımlı değil — next/font ile Inter/Geist eklenmeli. Bölüm boşlukları tutarsız."

**Kullanıcı onayıyla DARALTILMIŞ kapsam (bu atdd.md SADECE bunu kapsıyor):** Sadece temel bileşenlerin (Card, Badge, Alert, Button variant/size) kurulumu. Mevcut sayfaların migrasyonu, marka rengi uygulaması, next/font eklenmesi, boşluk standardizasyonu — hepsi AYRI takip görevlerine bırakıldı (bkz. Kapsam Dışı).

## Persona
Yetkin360 frontend geliştiricisi — bileşenler doğrudan son kullanıcıya değil, gelecekteki sayfa geliştirmelerine hizmet ediyor (bu turda hiçbir sayfa bu bileşenleri kullanmayacak). *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Hedef (Neden)
Tekrarlanan renk/kart class-string'lerini (text-red-600, bg-slate-50 vb.) tek yerden yönetilen, tutarlı bir bileşen setine indirgemek — gelecekteki sayfa geliştirmeleri için temel oluşturmak. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

**Önemli düzeltme (orkestratör kod incelemesi):** Jira'nın "cva zaten shadcn kalıbında mevcut" iddiası YANLIŞ — proje `class-variance-authority` kullanmıyor (`package.json`'da yok). CLAUDE.md yeni bağımlılık eklemeyi açık onay gerektiren bir işlem sayıyor; bu turda **cva eklenmeyecek**, mevcut `clsx` + `tailwind-merge` (zaten `frontend/lib/utils.ts`'teki `cn()` yardımcısında kullanılıyor) ile basit bir obje-tabanlı variant deseni kurulacak.

## User Story
As a Yetkin360 frontend geliştiricisi
I want Card/Badge/Alert bileşenlerini ve genişletilmiş bir Button'ı kullanabilmeyi
So that yeni sayfalar yazarken renk/kart stilini elle tekrar etmek zorunda kalmayayım

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given bir geliştirici `<Button variant="primary">` yazar (veya `variant` prop'unu hiç vermez), When render edilir, Then mevcut varsayılan görünüm (`bg-slate-900 text-white hover:bg-slate-700`) korunur — geriye dönük uyumluluk.
2. [Critical] Given bir geliştirici `<Button variant="destructive">` yazar, When render edilir, Then `--destructive` CSS token'ına dayalı kırmızı bir buton render edilir.
3. [High] Given bir geliştirici `<Button variant="secondary">` veya `<Button variant="ghost">` yazar, When render edilir, Then sırasıyla `--muted` tabanlı dolgulu / saydam-hover'lı bir buton render edilir.
4. [High] Given bir geliştirici `size="sm"`/`"lg"` verir (veya hiç vermez → `"md"`), When render edilir, Then butonun yükseklik/dolgu class'ları buna göre değişir, mevcut (size verilmemiş) çağıranların görünümü (`md` = mevcut boyut) DEĞİŞMEZ.
5. [Critical] Given mevcut bir çağıran HEM eski `className` (örn. `bg-red-600`) HEM yeni `variant` prop'unu aynı anda verir (geçiş dönemi senaryosu), When render edilir, Then `className` KAZANIR (tailwind-merge ile, variant class'larının üzerine uygulanır) — mevcut hardcoded renkli çağıranlar BOZULMAZ.
6. [High] Given bir geliştirici `<Alert variant="error"|"success"|"warning"|"info">` yazar (veya hiç vermez → `"info"`), When render edilir, Then ilgili token'a dayalı (destructive/success/warning/muted) arkaplan+kenarlık+metin rengiyle bir uyarı kutusu render edilir.
7. [High] Given bir geliştirici `<Badge variant="success"|"error"|"warning"|"default">` yazar (veya hiç vermez → `"default"`), When render edilir, Then küçük, yuvarlak köşeli, ilgili token renginde bir rozet render edilir.
8. [Medium] Given bir geliştirici `<Card>İçerik</Card>` yazar (tek tip, variant yok), When render edilir, Then `--card`/`--border` token'larına dayalı dolgulu/kenarlıklı bir kapsayıcı render edilir.
9. [Critical] Given bu değişiklik mevcut `button.tsx` kullanıcılarını (örn. `skills-section.tsx`'teki `bg-red-600` className'li çağrı) etkiliyor, When tüm mevcut frontend test suite'i (1039 test) çalıştırılır, Then hiçbiri kırılmaz (regresyon yok).

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme, kullanıcı girdisi, dosya yükleme/indirme, ödeme, KVKK/kişisel veri, multi-tenant sınır, dış API çağrısı, arka plan işi, yeni HTTP ucu. Hiçbiri uymadı çünkü bu görev saf UI bileşen kodu — backend'e, kullanıcı girdisine veya veri erişimine dokunmuyor.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Render edilen durum | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Button variant="primary" (veya verilmez) | `bg-slate-900 text-white hover:bg-slate-700` (mevcut varsayılan korunur) | Yok | Koyu lacivert dolgulu buton | AC-1 |
| 2 | Button variant="destructive" | `bg-destructive text-white hover:bg-destructive/90` | Yok | Kırmızı dolgulu buton | AC-2 |
| 3 | Button variant="secondary"/"ghost" | secondary: `bg-muted text-foreground hover:bg-muted/80`; ghost: `bg-transparent hover:bg-muted` | Yok | secondary: gri dolgulu; ghost: sadece hover'da arkaplan | AC-3 |
| 4 | Button size="sm"/"md"/"lg" (veya verilmez→md) | sm: `h-8 px-3 text-sm`; md: mevcut boyut (değişmez); lg: `h-12 px-6 text-base` | Yok | Buton yüksekliği/dolgusu değişir | AC-4 |
| 5 | Mevcut çağıran hem className hem variant veriyorsa | `cn(variantClasses, sizeClasses, className)` — className en sonda, twMerge çakışan class'ı className lehine çözer | Yok (saf class birleştirme) | Eski hardcoded renk (örn. `bg-red-600`) görsel olarak korunur, bozulma yok | AC-5 |
| 6 | Alert variant="error"/"success"/"warning"/"info" (verilmez→info) | error: `bg-destructive/10 text-destructive border-destructive/30`; success: `bg-success/10 ...`; warning: `bg-warning/10 ...`; info: `bg-muted text-foreground border-border` | Yok | Renkli kenarlıklı/arkaplanlı bilgi kutusu | AC-6 |
| 7 | Badge variant="success"/"error"/"warning"/"default" (verilmez→default) | success: `bg-success/10 text-success`; error: `bg-destructive/10 text-destructive`; warning: `bg-warning/10 text-warning`; default: `bg-muted text-foreground` | Yok | Küçük, yuvarlak köşeli renkli rozet | AC-7 |
| 8 | Card (tek tip, variant yok) | `bg-card text-foreground border border-border rounded-lg p-6` | Yok | Dolgulu, kenarlıklı kapsayıcı | AC-8 |
| 9 | Mevcut tüm çağıranlar (regresyon) | Hiçbir mevcut test kırılmaz | Yok | Mevcut sayfalar görsel olarak değişmez | AC-9 |

Kısmi başarı: N/A — bu görevde bileşenler ya tam doğru render olur ya da test kırmızı kalır, ara bir "kısmen çalışan" durum yok.
Hiçbir şey yapılamadı ama hata da yok: N/A — bileşenler saf fonksiyon/component, çağrılmazlarsa hiçbir şey render etmezler ama bu bir hata durumu değil (kullanılmayan bileşen, kapsam dışı bırakıldığı için beklenen).
Boş sonuç ↔ hata ayrımı: N/A — bu görev bir liste/arama sonucu döndürmüyor.

## Test Strategy
Unit: 85% — Her bileşen (`Button`, `Card`, `Badge`, `Alert`) için her variant/size kombinasyonunun doğru class'ları ürettiğini doğrulayan render testleri + AC-5'in (className override) tam olarak doğrulandığı bir test.
Integration: 15% — Mevcut tüm frontend test suite'inin (1039 test, `button.tsx` kullanan her yer dahil) değişiklik sonrası regresyonsuz PASS kaldığını doğrulayan tam suite koşusu.
E2E: 0% — Hiçbir sayfa bu bileşenleri henüz kullanmadığından (migrasyon kapsam dışı) e2e/vision-test'e konu yok.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Bu turda hiçbir sayfa yeni bileşenleri kullanmadığı için `vision-test` gerekmiyor — tek görsel garanti, mevcut `button.tsx` çağıranlarının (zaten var olan component testleriyle) görsel olarak BOZULMAMASI.
Diğer ölçülebilir kriterler: `npm run test` sonrası 1039 (+ bu görevin yeni testleri) test de PASS olmalı, 0 regresyon.

## Kapsam Dışı
`next/font` ile Inter/Geist font eklenmesi, marka renginin (indigo/teal) `--primary` token'ına uygulanması, mevcut sayfaların (profil, calismalar, admin vb.) yeni bileşenlere migrasyonu, bölüm boşluklarının (`space-y-8`) standardizasyonu, `class-variance-authority` (cva) bağımlılığı eklenmesi. Bunların hepsi, kullanıcının onayıyla, AYRI takip görevlerine bırakıldı. *(Kullanıcı onayı + Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/components/ui/button.tsx` — genişletilecek (variant/size prop'ları eklenecek), geriye dönük uyumlu.
- `frontend/components/ui/card.tsx` — YENİ dosya.
- `frontend/components/ui/badge.tsx` — YENİ dosya.
- `frontend/components/ui/alert.tsx` — YENİ dosya.
- `frontend/lib/utils.ts` — muhtemelen değişmez, mevcut `cn()` kullanılacak.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup olmadığı kontrol edilmedi. Sonraki adımlarda arama `frontend/` klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Migration gerekmiyor (saf frontend). Hiçbir sayfa bu bileşenleri kullanmadığı için (migrasyon kapsam dışı) yeni bileşenlerde bir sorun çıkarsa etkisi sıfır sayfaya yayılır. `button.tsx`'in geriye-dönük uyumluluğu AC-1/AC-5/AC-9 ile garanti altına alınıyor; bir regresyon bulunursa `git revert` yeterli.

## Risks
- `button.tsx` genişletmesi tek gerçek risk taşıyan değişiklik (zaten kullanımda) — AC-9'un (tam suite regresyon testi) bu riski kapsadığından emin olunmalı.

## Assumptions
- `cva` yerine `clsx`/`tailwind-merge` (mevcut `cn()`) ile basit obje-tabanlı variant deseni kurmanın, Jira'nın "cva zaten mevcut" varsayımından farklı ama CAVEMAN ilkesine (gereksiz bağımlılık ekleme) daha uygun olduğu kabul edildi — kullanıcı onayı bekleniyor (Hard Stop'ta).

## Unknowns
- Yok — kapsam daraltma kararı ve teknik yaklaşım (cva yerine clsx/tailwind-merge) netleşti.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Frontend geliştiricisi, son kullanıcı bu turda etkilenmiyor (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef/neden → Tekrarlanan class-string'leri tek bileşen setine indirgemek (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path → Alert/Badge/Card/Button örnek render'ları (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → varsayılan variant'lar + className/variant çakışmasında className kazanır (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
6. Başarı ölçütü → 1039 mevcut test + yeni testler PASS, 0 regresyon (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → font/marka rengi/migrasyon/boşluk/cva, ayrı görevlere bırakıldı (kullanıcı onayı + Sonnet 5 low alt-ajanı).
8. Bağımlılıklar → button.tsx + 3 yeni dosya (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör doğruladı).
9. Performans/güvenlik → yok, saf UI (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → migration yok, git revert yeterli (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri sahibi → kullanıcı onayı + otomatik test, vision-test bu turda gerekmiyor (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → unit 85 / integration 15 / e2e 0 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. Görev slug'ı → `tasarim-sistemi-temel-bilesenler` (kullanıcı onayı, AskUserQuestion).
14. Kapsam daraltma → küçük parçalara bölme (kullanıcı onayı, AskUserQuestion) — bu tur sadece bileşen kurulumu, migrasyon ayrı.
15. cva vs clsx/tailwind-merge → orkestratör kod incelemesiyle cva'nın projede olmadığını buldu, CLAUDE.md bağımlılık-ekleme onay kuralı gereği clsx/tailwind-merge (mevcut) tercih edildi — Hard Stop'ta kullanıcı onayı bekleniyor.
