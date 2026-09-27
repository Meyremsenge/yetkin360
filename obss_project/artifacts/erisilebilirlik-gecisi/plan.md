# Plan — erisilebilirlik-gecisi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (.tsx dosyaları). Design Direction
bilinçli atlandı — yeni bir görsel yüzey değil, mevcut görsel stili birebir
koruyan (AC-4) bir davranış/ARIA düzeltmesi (aynı gerekçe
`admin-dogrulama-ve-skill-yonetimi-ekranlari` görevinde kullanıldı).

## Kod keşfi atdd.md'yi düzeltti (önemli)
atdd.md'nin "GERÇEK BULGU 1" varsayımı (9 dosyada `role` eksik) **kısmen
yanlıştı** — gerçek kod okunduğunda 5 dosyada zaten doğru rol vardı:

| Dosya | Gerçek durum |
|---|---|
| `profil/profile-form.tsx` | `role="status"` ✓ zaten var |
| `profil/skills-section.tsx` | `role="status"` ✓ zaten var |
| `calismalar/[id]/transition-actions.tsx` | `role="status"` ✓ zaten var |
| `sifre-unuttum/page.tsx` | `role="alert"` ✓ zaten var |
| `sifre-sifirla/page.tsx` | `role="alert"` ✓ zaten var |
| `kayit/form.tsx` | **rol YOK — gerçek boşluk** |
| `e-posta-dogrula/page.tsx` | **rol YOK — gerçek boşluk** |
| `admin/skiller/page.tsx` | **rol YOK — gerçek boşluk** |
| `admin/dogrulama-kuyrugu/page.tsx` | **rol YOK — gerçek boşluk** |

**Kapsam 9 dosyadan 4 dosyaya daralıyor.** AC-1/AC-4 bu 4 dosyaya uygulanır.

## Kararlar (kod keşfinden, atdd.md'nin planını netleştiriyor)
- **Yeni `SuccessBanner` bileşeni OLUŞTURULMAYACAK.** Kod tabanının
  kendi konvansiyonu incelendi: başarı bantları hiçbir yerde ortak bir
  bileşen üzerinden değil, her sayfada INLINE `<div role="status"|"alert">`
  olarak yazılıyor (5 doğru örnek de böyle). 4 eksik dosyaya da AYNI
  inline kalıpla `role="status"` eklemek, kod tabanıyla tutarlı ve CAVEMAN/
  ponytail ilkesine (YAGNI — sadece 4 kullanım için paylaşılan bileşen
  spekülatif soyutlama olurdu) uygun. atdd.md'nin `success-banner.tsx`
  planı bu nedenle GÜNCELLENDİ — dosya oluşturulmuyor.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `frontend/app/kayit/form.tsx` | Başarı div'ine `role="status"` ekle (AC-1, AC-4) | low |
| `frontend/app/kayit/form.test.tsx` | Yeni role assertion'ı ekle | low |
| `frontend/app/e-posta-dogrula/page.tsx` | Başarı div'ine `role="status"` ekle (AC-1, AC-4) | low |
| `frontend/app/e-posta-dogrula/page.test.tsx` | Yeni role assertion'ı ekle | low |
| `frontend/app/admin/skiller/page.tsx` | Başarı div'ine `role="status"` ekle + merge dialog'a `role="dialog"`/`aria-modal`/Escape/focus-trap/focus-return (AC-1..4, AC-2, AC-3) | medium (dialog davranışı yeni mantık) |
| `frontend/app/admin/skiller/page.test.tsx` | Yeni role + Tab-trap + Escape senaryosu testleri eklenir | medium |
| `frontend/app/admin/dogrulama-kuyrugu/page.tsx` | Başarı div'ine `role="status"` ekle (AC-1, AC-4) | low |
| `frontend/app/admin/dogrulama-kuyrugu/page.test.tsx` | Yeni role assertion'ı ekle | low |

## New Files
Yok — atdd.md'nin `success-banner.tsx` planı yukarıdaki kararla iptal edildi.

## Dependencies
- Mevcut `role="status"`/`role="alert"` inline kalıbı (5 doğru örnek) —
  birebir kopyalanacak, yeni bir desen icat edilmiyor.
- Merge dialog için: `useRef` + `useEffect` ile basit bir focus-trap
  (ilk/son odaklanabilir eleman arasında Tab döngüsü) ve `onKeyDown`
  ile Escape yakalama — üçüncü parti bir modal/a11y kütüphanesi (Radix
  Dialog vb.) EKLENMİYOR, mevcut `package.json`'da yok, yeni bağımlılık
  eklemek bu görevin kapsamı dışı (CLAUDE.md: bağımlılık eklemeden önce
  onay gerekir, bu görev onu gerektirmeyecek şekilde tasarlandı).

## Migration Required?
Hayır — frontend-only, backend/DB'ye dokunulmuyor.

## Risks
- (atdd.md'den taşındı) `Button` bileşeninin focus-visible kontrastı
  doğrulanmadı — bu görevde dokunulmuyor.
- (atdd.md'den taşındı) Jira atananı "Meyrsem" — çakışma olabilir.
- **Yeni risk:** Focus-trap implementasyonu (üçüncü parti kütüphane
  olmadan elle yazılan) küçük bir DOM/ref hatasına açık — `test-copilot`
  bunu somut bir Tab-döngüsü senaryosuyla test etmeli (Tab son elemandan
  sonra ilk elemana dönüyor mu, Shift+Tab tersi yapıyor mu).

## Open Questions
Yok.
