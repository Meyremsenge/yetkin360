# Test Diff — fe15-auth-duzeni-sicil-gisesi
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar
- `frontend/components/ui/auth-layout.test.tsx` — YENİ (16 test).

## AC -> Test Mapping
| AC | Test |
|---|---|
| AC-1 (masaüstü iki kolon, marka paneli solda) | "AC-1: ..." (4 test — wordmark/cümle, zincir, children, DOM sırası) |
| AC-2 (mobil tek kolon) | "AC-2: sarmalayıcı grid className'inde grid-cols-1 token'ı bulunmalı" |
| AC-3 (--sand token) | "AC-3: ..." (3 test — panelde var, wordmark'ı sarıyor, form içeriğinde YOK) |
| AC-6 (aria-live korunur) | "AC-6: children'daki aria-live='assertive' attribute'u DOM'da aynen korunmalı" |
| AC-7 (çapraz linkler) | "AC-7: ..." (4 test — role/isim, href, links yoksa, links boş dizi) |
| AC-8 (children yokken crash yok) | "AC-8: children undefined iken render hata fırlatmamalı" |

## Not — AC-8 yorumu
AC-8'in atdd.md'deki "fail-fast" ifadesi, AuthLayout GERÇEKTEN hata verirse sessizce eski görünüme düşülmemesi anlamına geliyor (örn. try/catch ile hatayı yutup placeholder göstermek YASAK) — "children opsiyonel geçildiğinde crash olmaması" ile ÇELİŞMİYOR, ikisi farklı şeyler: biri "geçerli ama eksik prop'a dayanıklılık", diğeri "gerçek render hatasını gizlememe". Alt-ajan bu ayrımı doğru yapmış, test değişmedi.

## Orkestratör Doğrulaması
- `git status --short` ile dosyanın oluştuğu doğrulandı.
- Dosya satır satır `Read` ile incelendi — tam token eşleşmesi (`classList.contains`), gevşek substring yok, DOM sıra kontrolü `compareDocumentPosition` ile yapılmış.
- Mevcut 5 auth sayfasının test dosyalarına HİÇ dokunulmadı (`git status` ile teyit edilecek, code-copilot adımında).

## Varsayımlar (implementasyonun uyması gereken sözleşme)
- `AuthLayout`: named export, prop'lar `brandSentence: string`, `links?: {href, label}[]`, `children: React.ReactNode`.
- Marka paneli kökünde `bg-sand` token'ı, form alanında YOK.
- Sarmalayıcı grid'de `grid-cols-1` (mobile-first) + masaüstünde `md:grid-cols-...` ile ikiye bölünür.
- İçeride `ChainProgress` (FE-12'den, değiştirilmeden) kullanılır — "Beyan"/"Kanıt"/"Tanıklık"/"Doğrulanmış Deneyim" metinleri bu yüzden DOM'da görünür.
