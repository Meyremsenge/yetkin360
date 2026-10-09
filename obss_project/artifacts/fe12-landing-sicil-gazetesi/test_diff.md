# Test Diff — fe12-landing-sicil-gazetesi
_Reference: atdd.md, plan.md_

## Oluşturulan / Güncellenen Dosyalar
- `frontend/components/ui/chain-progress.test.tsx` — YENİ.
- `frontend/components/ui/verified-seal.test.tsx` — YENİ.
- `frontend/app/page.test.tsx` — ÜZERİNE YAZILDI (eski placeholder'a özgü AC-9 testleri, bu redesign'da geçersiz olduğu için değiştirildi — eski hali `git show HEAD:frontend/app/page.test.tsx` ile geri alınabilir, veri kaybı yok).

## AC -> Test Mapping
| AC | Test dosyası / açıklama |
|---|---|
| AC-1 (bölüm sırası, 4 zincir adımı, 3 persona kartı) | `page.test.tsx` "AC-1: ..." testleri + `chain-progress.test.tsx` "AC-1: ..." testleri |
| AC-2 (Kayıt Ol → /kayit, Giriş Yap → /giris, tam href) | `page.test.tsx` "AC-2: ..." testleri |
| AC-3 (rakamlar şeridi veri yoksa DOM'a girmez) | `page.test.tsx` "AC-3: ..." testleri (stats-strip test-id + başlık metni yokluğu) |
| AC-4 (mobil tek sütun, metin görsel önce) | `page.test.tsx` "AC-4: ..." testleri (`grid-cols-1` + DOM sıra kontrolü) |
| AC-5 (ChainProgress boş steps, crash yok) | `chain-progress.test.tsx` "AC-5: ..." testleri |
| AC-6 (VerifiedSeal eksik name, crash yok, sahte isim yok, çam yeşili token) | `verified-seal.test.tsx` "AC-6: ..." testleri |
| AC-7 (prefers-reduced-motion) | `chain-progress.test.tsx` "AC-7: ..." testleri |
| AC-8 (metinler tr.json'dan) | `page.test.tsx` "AC-8: ..." testleri |

## Orkestratör Doğrulaması
- `git status --short` ile 3 dosyanın değiştiği doğrulandı.
- `git diff frontend/app/page.test.tsx` ile üzerine yazılan dosyanın git'te takipli olduğu ve geri alınabilir olduğu teyit edildi (veri kaybı yok).
- İki yeni test dosyası (`chain-progress.test.tsx`, `verified-seal.test.tsx`) satır satır okunup AC kapsaması doğrulandı — tam token eşleşmesi kullanılmış, gevşek substring/regex yok.
- Alt-ajanın raporu: 14 test, 9 kırmızı (beklenen — component'ler henüz yok), 5 yeşil (AC-3 ve AC-8'in bir kısmı mevcut placeholder'da da tesadüfen sağlanıyor — bu normal, "red" olması gereken sadece YENİ davranış, zaten var olan davranış için test baştan yeşil olabilir).

## Varsayımlar (implementasyonun uyması gereken sözleşme — code-copilot'a aktarılacak)
- `ChainProgress`: named export, prop `steps: { label: string; completed: boolean }[]`.
- `VerifiedSeal`: named export, prop'lar `name?`, `issuedAt?`, `registryNo?` (hepsi opsiyonel string).
- `page.tsx`: hero bir `<section>` içinde, `grid-cols-1` class'ı taşımalı; `VerifiedSeal` kökü `data-testid="verified-seal"` almalı; rakamlar şeridi `data-testid="stats-strip"` ile işaretlenmeli (veri yoksa hiç render edilmez).
- "Örnek bir doğrulamayı incele" CTA route'u ve "neden farklı" karşılaştırma bölümünün tam metni test edilmedi (atdd.md'de netleşmemiş detaylar) — code-copilot makul bir karar verebilir, red-team bunu gözden geçirir.
