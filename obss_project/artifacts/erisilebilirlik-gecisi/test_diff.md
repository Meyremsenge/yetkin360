# Test Diff — erisilebilirlik-gecisi
_Red step (test-copilot, Haiku alt-ajanı tarafından yazıldı)_

## Genişletilen/Oluşturulan Dosyalar
| Dosya | İşlem | Yeni test |
|---|---|---|
| `frontend/app/kayit/form.test.tsx` | Yeni (daha önce yoktu) | 6 |
| `frontend/app/e-posta-dogrula/page.test.tsx` | Genişletildi | 2 |
| `frontend/app/admin/dogrulama-kuyrugu/page.test.tsx` | Genişletildi | 2 |
| `frontend/app/admin/skiller/page.test.tsx` | Genişletildi | 7 |

Diskte doğrulandı (`git status --short`): 3 dosya `M`, 1 dosya `??` (yeni).

## AC → Test eşleşmesi
- AC-1 (başarı mesajı role="status" ile duyurulur): her 4 dosyada birer test.
- AC-4 (görsel stil regresyonu yok): her 4 dosyada birer test (yeşil renk/kenarlık kontrolü).
- AC-2 (focus trap — Tab modal dışına çıkmaz): `skiller/page.test.tsx`'te Tab + Shift+Tab yönlü 2 test.
- AC-3 (Escape ile kapan, odak tetikleyiciye döner): `skiller/page.test.tsx`'te 1 test.
- AC-6 (mevcut davranış korunur — Cancel/backdrop): `skiller/page.test.tsx`'te 2 test (bunlar implementasyon değişmeden de GREEN olmalı, regresyon kontrolü).

## Bilinen isim çakışması (not, hata değil)
`admin/skiller/page.test.tsx` içinde iki farklı ATDD'den gelen "AC-6" adlı
testler var (önceki görevin AC-6'sı: slug çakışması; bu görevin AC-6'sı:
dialog mevcut davranış). İkisi de bağımsız, çakışmıyor, sadece isimlendirme
farklı bağlamlardan geldiği için görsel olarak kafa karıştırıcı — fonksiyonel
bir sorun değil.

## Durum
Red (beklenen) — `kayit/form.tsx`, `e-posta-dogrula/page.tsx`,
`admin/dogrulama-kuyrugu/page.tsx`'te `role="status"` yok; `admin/skiller/page.tsx`'te
hem `role="status"` hem merge dialog'un `role="dialog"`/focus-trap/Escape
mantığı yok. Sonraki adım: `code-copilot`.
