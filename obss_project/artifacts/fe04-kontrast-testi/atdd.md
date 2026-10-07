---
task_slug: fe04-kontrast-testi
jira_id: null
saga_task_id: null
threat_model: not-applicable
priority: high
coverage_target: 100
performance_target: null
memory_target: null
test_strategy:
  unit: 100
  integration: 0
  e2e: 0
affected_modules:
  - frontend/lib/ui/contrast-ratio.ts
  - frontend/lib/ui/contrast-ratio.test.ts
---

# ATDD — fe04-kontrast-testi

## Jira Kaynağı
Jira'ya bağlı değil — kaynak `planfrontend.md` FE-04.

User Story (planfrontend.md §3 Faz 1'den birebir): "Kontrast kontrolü: §1.2'deki hesaplanmış değerleri token'lar koda girdikten sonra küçük bir unit testle sabitle (renk değişirse test kırılır)."

§1.2'den birebir: "Kontrast (WCAG, hesaplandı): mürekkep/kâğıt **15.5:1** · ikincil metin/kâğıt **6.2:1** · ikincil metin/kum **5.6:1** · çam/kâğıt **8.1:1** · beyaz yazı/çam buton **8.5:1** · aşı boyası/zemini **5.1:1** · tuğla/zemini **5.8:1**. Hepsi ≥ 4.5:1. FE-04 bunu kodda tekrar doğrular."

## Persona
Geliştirici/QA — doğrudan son kullanıcı değil. Bu bir regresyon bariyeri: `globals.css`'teki bir HSL değişikliğinin erişilebilirlik gereksinimini (WCAG AA) yanlışlıkla bozmasını otomatik yakalar. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Hedef (Neden)
`.claude/rules/frontend.md`: "Kontrast 4.5:1... Müşteri kamu üniversitesi olabilir; erişilebilirlik satın alma şartı olabilir." Plan'ın §1.2'de "hesaplandı" dediği değerleri koda sabitleyip gelecekteki bir renk değişikliğinde ihlali otomatik yakalamak. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## User Story
As a bu projenin geliştiricisi/QA'sı
I want token renklerinin WCAG AA kontrast oranlarının bir unit testle sabitlenmesini
So that gelecekte bir token rengi değiştirildiğinde erişilebilirlik ihlali sessizce geçmesin, test kırmızı olsun

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `frontend/lib/ui/contrast-ratio.ts`'te `hslToRgb` ve `contrastRatio` (WCAG formülü: `(L1+0.05)/(L2+0.05)`, L1 daha açık renk) saf fonksiyonları tanımlı, When "40 30% 97%" (kağıt) ve "30 12% 12%" (mürekkep) HSL string'leri verilir, Then hesaplanan kontrast oranı `15.5` değerine ±0.1 toleransla eşittir.
2. [Critical] Given aynı fonksiyonlar, When plan'ın listelediği diğer 6 çift ("ikincil metin/kâğıt", "ikincil metin/kum", "çam/kâğıt", "beyaz yazı/çam buton", "aşı boyası/zemini", "tuğla/zemini") test edilir, Then her biri sırasıyla `6.2`/`5.6`/`8.1`/`8.5`/`5.1`/`5.8` değerlerine ±0.1 toleransla eşittir.
3. [Critical] Given 7 çiftin tamamı, When her birinin oranı kontrol edilir, Then hepsi `>= 4.5` (WCAG AA eşiği) koşulunu sağlar — bu, değerlerin kendisinden BAĞIMSIZ ayrı bir assertion'dır (sadece "15.5'e eşit" değil, "15.5 VE >= 4.5" ikisi de).
4. [High] **AC-4 (parse hatası, fail-closed):** Given `hslToRgb` fonksiyonuna bozuk formatlı bir string (örn. `"geçersiz"`, boş string, veya `"abc def ghi"`) verilir, When fonksiyon çağrılır, Then bir hata fırlatır (throw) — sessizce yanlış bir sayı (örn. `NaN` kontrast oranına sessizce yayılan) DÖNMEZ, hata erken ve net olmalı.
5. [Medium] Given "beyaz" rengi (`0 0% 100%`) bir CSS custom property değil, literal bir HSL string, When `contrastRatio` fonksiyonuna doğrudan bu literal string verilir, Then token-okuma gerektirmeden doğru hesaplanır (fonksiyon hem token hem literal HSL string'i aynı şekilde kabul eder — ayrım yok, ikisi de "H S% L%" formatında string).

## Threat Model
Tetikleyici yok — saf matematik/test yardımcı fonksiyonu, auth/input/upload/payment/PII/multi-tenant/dış API/background job/yeni HTTP ucu yok.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Çift | Beklenen Oran (±0.1) | WCAG AA (≥4.5) | AC |
|---|---|---|---|---|
| 1 | foreground (mürekkep, `30 12% 12%`) / background (kâğıt, `40 30% 97%`) | 15.5 | ✓ | AC-1, AC-3 |
| 2 | muted-foreground (ikincil metin, `30 7% 36%`) / background (kâğıt) | 6.2 | ✓ | AC-2, AC-3 |
| 3 | muted-foreground (ikincil metin) / muted (kum, `38 20% 92%`) | 5.6 | ✓ | AC-2, AC-3 |
| 4 | success (çam, `160 38% 24%`) / background (kâğıt) | 8.1 | ✓ | AC-2, AC-3 |
| 5 | beyaz (`0 0% 100%`) / success (çam buton) | 8.5 | ✓ | AC-2, AC-3, AC-5 |
| 6 | warning (aşı boyası, `34 75% 32%`) / background (zemin) | 5.1 | ✓ | AC-2, AC-3 |
| 7 | destructive (tuğla, `8 58% 40%`) / background (zemin) | 5.8 | ✓ | AC-2, AC-3 |
| 8 | Bozuk HSL string'i | throw (fail-closed) | N/A | AC-4 |

Kısmi başarı: N/A — her çift ya doğru hesaplanır ya da test kırmızı kalır.
Hiçbir şey yapılamadı ama hata da yok: AC-4 bu riski kapsıyor — parse edilemeyen bir girdi SESSİZCE yanlış bir sayı (NaN) üretip kontrast testini yanlışlıkla PASS/anlamsız yapmamalı, açıkça hata fırlatmalı.
Boş sonuç ↔ hata ayrımı: N/A.

## Test Strategy
Unit: 100% — bu görevin tamamı saf fonksiyon + unit test. Integration/E2E: 0% — görsel değişiklik yok, canlı tarayıcı gerekmiyor.

## Benchmark / Başarı Ölçütü
Coverage Target: 100%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: yok — bu saf bir hesaplama doğrulaması.
Diğer ölçülebilir kriterler: 7/7 çift PASS, hepsi ≥4.5 WCAG AA eşiğini geçiyor.

## Kapsam Dışı
Plan'da listelenmeyen başka token çiftlerinin (örn. `border`/`background`) test edilmesi — sadece plan'ın kendi listelediği 7 çift test edilir. Gerçek bir Lighthouse/axe-core erişilebilirlik taraması (FE-28'in kapsamı, bu görevde değil). `globals.css`'in runtime'da otomatik okunup karşılaştırılması (over-engineering, CAVEMAN ilkesine aykırı — HSL değerleri test dosyasında literal olarak tutulacak, bilinçli bir senkronizasyon riski kabul ediliyor). *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/lib/ui/contrast-ratio.ts` — YENİ dosya, `hslToRgb`/`relativeLuminance`/`contrastRatio` saf fonksiyonları.
- `frontend/lib/ui/contrast-ratio.test.ts` — YENİ dosya, 7 çift + 1 edge case testi.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — arama `frontend/` klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Migration gerekmiyor. Bir sorun bulunursa `git revert` yeterli.

## Risks
- **Senkronizasyon riski (kabul edilen):** Test dosyasındaki HSL değerleri `globals.css`'teki gerçek değerlerle MANUEL senkron tutulmalı — eğer `globals.css` değişir ama bu test dosyası güncellenmezse, test eski (artık gerçek olmayan) değerleri doğrular. Bu, CSS dosyasını TypeScript runtime'da parse etmenin getireceği karmaşıklığa (over-engineering) tercih edilen bilinçli bir trade-off. Test dosyasına bu riski hatırlatan bir yorum eklenecek.

## Assumptions
- WCAG kontrast formülünün ((L1+0.05)/(L2+0.05), L1 her zaman daha açık renk) standart W3C formülü olduğu ve plan'daki değerlerin bu formülle hesaplandığı varsayıldı.

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → geliştirici/QA, regresyon bariyeri (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef → frontend.md kuralı + kamu kurumu erişilebilirlik gereksinimi (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path → 7 çift ±0.1 tolerans + ≥4.5 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → bozuk HSL throw eder, beyaz literal olarak kabul edilir (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
6. Başarı ölçütü → 7/7 PASS, ≥4.5 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → başka token çiftleri, Lighthouse/axe-core, CSS runtime parse (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. Bağımlılıklar → yeni lib/ui/contrast-ratio.ts + test (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör lib/ui/ klasörünün henüz var olmadığını doğruladı).
9. Performans/güvenlik → yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → migration yok, git revert (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
11. Kabul kriteri → kullanıcı onayı + test, vision-test gerekmiyor (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → unit 100 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. Görev slug'ı → `fe04-kontrast-testi` (kullanıcı onayı).
