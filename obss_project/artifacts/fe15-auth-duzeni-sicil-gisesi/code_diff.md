# Code Diff — fe15-auth-duzeni-sicil-gisesi
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `frontend/components/ui/auth-layout.tsx` — `AuthLayout`, iki kolonlu (masaüstü `md:grid-cols-[2fr_3fr]`) / tek kolonlu (mobil `grid-cols-1`) sarmalayıcı. Sol/üst `bg-sand` marka paneli (`messages.home.title`, `brandSentence` prop, `ChainProgress` — mobilde `hidden md:block` ile gizli), sağ/alt `children`.

## Değiştirilen Dosyalar
- `frontend/app/globals.css` — `--sand: 36 30% 89%;` eklendi, mevcut token'lar değişmedi.
- `frontend/tailwind.config.ts` — `sand: "hsl(var(--sand))"` eklendi, mevcut eşlemeler değişmedi.
- `frontend/messages/tr.json` — yeni `authLayout.{brandSentence, forgotPasswordLink}` anahtarları eklendi, mevcut anahtarlar korundu.
- `frontend/app/giris/page.tsx`, `kayit/page.tsx`, `sifre-unuttum/page.tsx`, `sifre-sifirla/page.tsx`, `e-posta-dogrula/page.tsx` — dış sarmalayıcı (`flex items-center justify-center min-h-screen` + `max-w-md` div çifti) `<AuthLayout>` ile değiştirildi, iç JSX/state/handler/form.tsx importları değişmedi.

## Orkestratör Doğrulaması (2 ayrı Haiku dispatch + 1 düzeltme turu)
1. İlk dispatch: `AuthLayout` + token'lar yazıldı. Review'da wordmark/zincir etiketlerinin **koda gömülü** olduğu bulundu (CLAUDE.md'nin "UI metni koda gömülmez" kuralı ihlali) — ikinci bir Haiku dispatch'iyle `messages.home.title`/`messages.home.chain.*`'a bağlandı (FE-12'de zaten var olan anahtarlar, yeni anahtar eklenmedi).
2. İkinci dispatch: 5 sayfa sarmalandı. Alt-ajan kendi raporunda bir hata itiraf etti (`e-posta-dogrula/page.tsx`'te bir kapanış etiketini yanlışlıkla silip düzelttiğini söyledi) — bu, orkestratör tarafından `Read` ile satır satır doğrulandı: dosya şu an sözdizimsel olarak doğru, JSX etiketleri düzgün kapanmış.
3. `git status --short` ile 10 dosyanın (1 yeni + 9 değişen) gerçekten değiştiği doğrulandı.
4. Tüm ilgili test dosyaları (`auth-layout.test.tsx` + 5 sayfanın kendi testleri + `chain-progress`/`verified-seal`/`page.test.tsx`) BAĞIMSIZ çalıştırıldı: **116/116 PASS**.
5. Tüm paket (regresyon kontrolü): `npx vitest run` → **70 dosya, 1228/1228 PASS** (önceki 1214'ten +14, yeni `auth-layout.test.tsx`'in kendi testleri).
6. `npm run typecheck` → temiz. `npm run lint` → 0 hata, 6 ilgisiz önceden var olan uyarı.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | `auth-layout.tsx` — `md:grid-cols-[2fr_3fr]`, sol `bg-sand` panel (wordmark+cümle+ChainProgress), sağ children |
| AC-2 | `auth-layout.tsx` — `grid-cols-1` (mobil), zincir `hidden md:block` ile gizli |
| AC-3 | `globals.css`/`tailwind.config.ts` — `--sand` token eklendi, SADECE marka panelinde kullanılıyor |
| AC-4 (regresyon, giris/kayit) | 21+11+3 test PASS |
| AC-5 (regresyon, sifre-unuttum/sifre-sifirla/e-posta-dogrula) | 10+13+10 test PASS |
| AC-6 | `auth-layout.tsx` — `children` olduğu gibi render edilir, `aria-live` dokunulmaz (test ile doğrulandı) |
| AC-7 | `links` prop'u her sayfaya uygun şekilde geçildi; `/sifre-sifirla`/`/e-posta-dogrula`'da ÇİFT LİNK olmasın diye `links` verilmedi (mevcut iç linkler korundu) |
| AC-8 | `auth-layout.tsx`'te try/catch yok, render hatası yukarı çıkar (fail-fast) |

## Kalan Sınırlamalar
- Sarmalanan iç JSX'in girintisi (indentation) düzeltilmedi — "tek satır değişmez" kuralı nedeniyle kasıtlı. Görsel/davranışsal etkisi yok, sadece kozmetik bir biçimlendirme farkı (Prettier varsa ayrı bir format turu gerekebilir, bu görevin kapsamı dışında).
- Görsel doğrulama (Playwright/vision-test, masaüstü+mobil) `verify` adımında yapılacak.

## Varsayımlar
- `brandSentence` tüm sayfalarda aynı tr.json anahtarından (`messages.authLayout.brandSentence`) geliyor — atdd.md bunu sayfaya özel ayırmayı gerektirmiyordu.

## Görsel/UI Kriteri
Evet — atdd.md bunu işaretlemişti. `verify` adımında Playwright ile masaüstü/mobil görsel kontrol ZORUNLU, N/A geçilmemeli.
