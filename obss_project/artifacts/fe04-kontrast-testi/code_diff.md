# Code Diff — fe04-kontrast-testi
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `frontend/lib/ui/contrast-ratio.ts` — `hslToRgb`/`relativeLuminance` (iç yardımcı) + `contrastRatio` (export) saf fonksiyonları. Standart WCAG/CSS Color 4 formülü, bağımlılıksız.

## Review Sürecinde Bulunan ve Düzeltilen Sorun — kritik bulgu
İlk doğrulamada test suite'i 18 testten 4'ünü FAIL verdi. İncelemede implementasyonun DOĞRU olduğu, ama `planfrontend.md` §1.2'nin kendi dokümantasyon değerlerinin (3 çift için) matematiksel olarak hatalı hesaplanmış olduğu ortaya çıktı:

| Çift | Plan'ın iddiası | Gerçek (standart WCAG formülü, 2 bağımsız hesapla doğrulandı) |
|---|---|---|
| beyaz/çam buton | 8.5 | **8.57** |
| aşı boyası/zemin | 5.1 | **5.46** |
| tuğla/zemin | 5.8 | **6.25** |

Doğrulama: hem Haiku alt-ajanının implementasyonu hem orkestratörün bağımsız Node.js hesabı (CSS Color 4 HSL→RGB + WCAG relative luminance formülü) AYNI sonuçları üretti. Bu, CLAUDE.md'nin "mimari karara aykırı somut kanıt görürsen sessizce sapma, sor" kuralına göre kullanıcıya bildirildi — kullanıcı onayıyla testler gerçek (doğru) değerlere güncellendi. Tüm çiftler hâlâ ≥4.5 WCAG AA eşiğini geçiyor (hatta daha güçlü kontrast) — bu bir regresyon değil, kaynak planın dokümantasyon hatasının düzeltilmesi.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | `contrastRatio` — mürekkep/kâğıt 15.5 |
| AC-2 | `contrastRatio` — 6 çift (3'ü düzeltilmiş gerçek değerle) |
| AC-3 | `lighter/darker` karşılaştırması + `>= 4.5` testleri |
| AC-4 | `hslToRgb`'nin `NaN`/format kontrolü → throw |
| AC-5 | Literal HSL string (`"0 0% 100%"`) token ile aynı şekilde kabul ediliyor |

## Orkestratör Doğrulaması
`git status --short` ile dosyanın oluştuğu doğrulandı. `Read` ile implementasyon satır satır incelendi — CAVEMAN'a uygun (3 fonksiyon, bağımlılık yok). Testler GERÇEKTEN çalıştırıldı: ilk koşuda 4/18 FAIL (alt-ajanın "implementasyon doğru, beklenen değerler şüpheli" iddiası bağımsız Node.js hesabıyla doğrulandı), kullanıcı onayıyla test beklentileri düzeltildi, son koşu **18/18 PASS**.

## Görsel/UI Kriteri
Yok — saf hesaplama, görsel değişiklik içermiyor.
