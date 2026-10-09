---
name: ekran
description: Tek bir frontend ekranını docs/sayfa-tasarim-brifi.md + tasarimlar/stitch/ mockup'ına göre yeni görsel dile (kâğıt/mürekkep/mühür) geçirir. Yalnız sunum katmanı; veri/iş mantığı değişmez. Kullanıcı /ekran <sayfa-no veya rota> yazdığında çalışır.
disable-model-invocation: true
argument-hint: "<brif sayfa no 1-21 | rota, ör. 2 veya /v/[token] | shell>"
---

# Ekran dönüştür

Amaç: bir ekranı **görünüm olarak** brife uydurmak. Davranış aynı kalır.
Kullanıcıyla **Türkçe** konuş. Kod, yorum, tanımlayıcı İngilizce. UI metni `frontend/messages/tr.json`'da.

## 0. Kapsam kilidi (önce oku, sonra başla)

- **Tek ekran, tek commit.** Argümandaki ekran dışında dosyaya dokunma (o ekranın alt bileşenleri ve testleri hariç).
- **Yalnız sunum:** JSX yapısı, Tailwind sınıfları, `tr.json` metinleri, `components/ui/` ilkellerinin kullanımı. `fetch`/TanStack Query çağrıları, Zod şemaları, yönlendirme mantığı, prop sözleşmeleri **değişmez**.
- **Backend'e dokunma.** Ekranda veri eksikse uydurma — `docs/sayfa-tasarim-brifi.md` "Açık noktalar" ruhuyla raporda not düş.
- **Yeni bağımlılık ekleme** (ikon kütüphanesi dahil). İkon gerekiyorsa küçük inline SVG ya da ikonsuz.
- **Olmayan veriyi çizme:** istatistik, yüzde, puan, fotoğraf, sayaç yok. Mockup'ta varsa bile.
- `dangerouslySetInnerHTML`, `localStorage` yasak. Mor/indigo, gradyan, emoji, kalın gölge yasak.

## 1. Hedefi bul

| Brif no | Ekran | Dosya(lar) | Mockup (`tasarimlar/stitch/proje1-tum-sayfalar/`) |
|---|---|---|---|
| shell | AppShell (sol navbar) — brif §5 | `frontend/components/app-shell.tsx` | `06-…calisma-detayi-appshell.png` (sol kısım) |
| 2 | `/v/[token]` sertifika | `frontend/app/v/[token]/page.tsx` | `19-…dogrulama-sertifikasi-masaustu.png`, `04-…mobil-qr.png` |
| 3 | `/p/[slug]` public profil | `frontend/app/p/[slug]/page.tsx` | `15-…ziyaretci.png`, `05-…profil-sahibi.png` |
| 9 | `/calismalar` | `frontend/app/calismalar/page.tsx` | `09-…calismalarim-liste.png` |
| 10 | `/calismalar/[id]` | `frontend/app/calismalar/[id]/page.tsx` + aynı klasördeki formlar | `06-…calisma-detayi-appshell.png` |
| 11 | değerlendirme formu | `frontend/app/calismalar/[id]/degerlendirme/*` | `12-…appshell.png` (ana), `14-…v2.png` |
| 12 | yeni çalışma | `frontend/app/calismalar/olustur/page.tsx` | `11-…yeni-calisma-olustur.png` |
| 13 | `/profil` | `frontend/app/profil/*` | `07-…profil.png` |
| 14 | kuruluş paneli | `frontend/app/kurulus/[id]/panel/page.tsx` | `10-…kurulus-paneli.png` |
| 16 | kurum paneli | `frontend/app/kurum/[id]/panel/page.tsx` | `16-…kurum-paneli-itu.png` |
| 18 | kuruma bağlan | `frontend/app/kurum/[id]/baglan/page.tsx` | `13-…kuruma-baglanma-talebi.png` |
| 19 | admin doğrulama kuyruğu | `frontend/app/admin/dogrulama-kuyrugu/page.tsx` | `02-…kurum-dogrulama-kuyrugu.png` |
| 21 | 404 / hata | `frontend/app/not-found.tsx`, `error.tsx` | `18-…hata-sayfalari….png` |

Mockup adları kısaltıldı; tam adı numarayla bul: `ls tasarimlar/stitch/proje1-tum-sayfalar/ | grep '^19-'`. Ek referans: `tasarimlar/stitch/proje2-brifi-v2/` (sertifika, çalışma detayı, giriş).

Mockup **ilham**dir, kaynak değil: Stitch HTML'ini kopyalama (CDN Tailwind, sahte veri, farklı sınıf adları içerir). Brif ile mockup çelişirse **brif** kazanır. `planfrontend.md` ile brif çelişirse **brif** kazanır.

## 2. Hedefli oku (bu kadar, fazlası değil)

1. Brifte o sayfanın bölümü: `grep -n '^### <no>\.' docs/sayfa-tasarim-brifi.md` ile satırı bul, yalnız o bölümü oku. Oturumda ilk ekransa ek olarak §1 (Temel, ~satır 25–110) ve §2'de kullanacağın bileşen alt başlıklarını oku.
2. Mockup PNG'sine bak (Read ile görsel).
3. Hedef dosya(lar) + **aynı adlı `.test.tsx`** dosyaları.
4. Kullanacağın ilkeller: `frontend/components/ui/` — `Button` (variant: primary/secondary/destructive/ghost, size: sm/md/lg), `Card`, `Badge` (default/success/error/warning), `Alert` (error/success/warning/info), `Input`, `Label`, `ChainProgress` (`steps: {label, completed}[]`), `VerifiedSeal`, `AuthLayout`. Var olanı kullan; yeni ilkel gerekiyorsa `components/ui/` altına küçük, testli ekle.

## 3. Renk ve yazı — yalnız token

Tailwind sınıfları (`frontend/tailwind.config.ts`):
`bg-background` (kâğıt) · `bg-card` · `bg-sand` (navbar/vurgu) · `bg-muted` · `border-border` · `text-foreground` (mürekkep) · `text-muted-foreground` (ikincil) · `bg-success`/`text-success` (çam, birincil buton, mühür) · `text-warning` (aşı) · `text-destructive` (tuğla) · `font-serif` (başlık) · `font-sans` (gövde) · `font-mono` (kayıt no, slogan, tarih damgası).

**Yasak:** `slate-*`, `gray-*`, `red-*`, `green-*`, `blue-*`, `indigo-*`, `amber-*`, `white`, `black` gibi sabit renkler. Bitişte bu dosyalarda sayı **0** olmalı:

```bash
grep -cE '(slate|gray|zinc|red|green|blue|indigo|amber|emerald|yellow)-[0-9]{2,3}|bg-white|text-white|text-black' <dosyalar>
```

## 4. Uygula

- Brif tablosundaki sırayla: düzen → butonlar tablosu → **durumlar** (yükleniyor / boş / hata — üçü de olmadan ekran bitmez) → mobil (375px) notu.
- Ham enum ekranda görünmez (`ACTIVE`, `T1`, `PENDING_APPROVAL`) → `tr.json` etiketi.
- Yeni metin = `tr.json`'a yeni anahtar. **Var olan anahtarların adını değiştirme** (testler anahtara bağlı); metnini brife göre düzeltebilirsin.
- Erişilebilirlik: her alanda `<label>`, görünür focus (`focus-visible:ring-2 ring-success`), hata `aria-live`, ikon butonda `aria-label`, başlık sırası h1→h2→h3.

## 5. Testler — kural

- **Davranış testi değişmez** (metin, rol, tıklama, çağrılan API, yönlendirme). Kırılırsa **kodu** düzelt.
- Yalnız **sınıf adı/DOM yapısı** doğrulayan assertion'lar görünüm değişikliği yüzünden güncellenebilir; her birini raporda listele.
- Testi geçsin diye silme, `skip`'leme, beklentiyi gevşetme **yasak**.

## 6. Doğrula (hepsi `frontend/` içinde)

```bash
npx vitest run <hedef klasör veya test dosyaları>
npm run typecheck
npm run lint
```
+ §3'teki grep = 0. Hepsi temiz değilse commit yok.

Sonra kullanıcıya söyle: `npm run dev` açıkken ekranı tarayıcıda **375px ve 1280px** genişlikte kontrol etsin (DevTools → cihaz araç çubuğu). Seed hesapları: `ogrenci1@seed.local`, `org1-admin@seed.local`, `kurum1-admin@seed.local`, `kurum1-koordinator@seed.local` (şifre `backend/scripts/seed.py`'de).

## 7. Kapat

1. `planfrontend.md`'de ilgili `FE-xx` satırını `[x]` yap (sayfa → FE eşlemesi: shell=FE-09, 2=FE-13, 3=FE-14, 9=FE-16, 10=FE-17, 11=FE-22, 12=FE-19, 13=FE-18, 14=FE-20, 16=FE-21, 18=FE-23, 19=FE-24, 21=FE-11).
2. Commit — dosyaları **adıyla** ekle (`git add -A`/`git add .` yasak). Mesaj Türkçe, tek satır + gövdede `FE-xx`. **Co-Authored-By satırı ekleme.**
   ```
   feat(ui): /v/[token] sertifika sayfası yeni görsel dile geçirildi

   FE-13
   ```
3. Push **yalnız kullanıcı söylerse**.
4. Rapor (kısa):
   ```
   Değişen: <dosyalar> — <ne>
   Doğrulanan: vitest <n geçti> · typecheck · lint · sabit renk 0
   Güncellenen sınıf testleri: <liste veya —>
   Açık not: <eksik veri / brif sapması veya —>
   ```
