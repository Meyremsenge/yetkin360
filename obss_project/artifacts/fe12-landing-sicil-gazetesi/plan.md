# Plan — fe12-landing-sicil-gazetesi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (`.tsx` dosyaları + Görsel/UI kriteri dolu) — Discover/Audit/Design Direction tamamlandı, bulgular aşağıda.

## Discover Bulguları (Playwright ile gerçek app)
- Dev server (`npm run dev`, Next.js 16.3.8 Turbopack) çalıştırıldı, `http://localhost:3000/` gezildi.
- Mevcut landing: 3 satırlık placeholder — başlık, tagline, tek "Başla" linki. Console hatası yok.
- Route haritası (zaten var, bu görev bunlara DOKUNMAYACAK): `/giris`, `/kayit`, `/sifre-unuttum`, `/sifre-sifirla`, `/e-posta-dogrula`, `/calismalar`, `/profil`.
- Design token'ları `app/globals.css`'te mevcut ve atdd.md'nin varsayımıyla uyumlu: `--background` (kağıt kremi), `--foreground`/`--primary` (mürekkep), `--success` (çam yeşili — "doğrulanmış" durumu için), `--ink-soft`, `--muted`, `--border`. Fontlar `tailwind.config.ts`'te tanımlı: `font-sans` (IBM Plex Sans), `font-serif` (Source Serif 4), `font-mono` (IBM Plex Mono).
- **Önemli düzeltme (atdd.md'nin varsayımını geçersiz kılıyor):** Proje **next-intl KULLANMIYOR**. Gerçek desen: `import messages from "@/messages/tr.json"` ile düz JSON nesnesi doğrudan import edilip `messages.home.title` gibi erişiliyor. Yeni metinler de bu desenle (`messages.home.*`) tüketilecek — next-intl `useTranslations` hook'u kullanılmayacak.
- `components/ui/button.tsx` mevcut desen: `variant`/`size` prop'ları, `cn()` ile class birleştirme. **Not:** `primary` variant'ı şu an `bg-slate-900`/`hover:bg-slate-700` kullanıyor (design token değil) — bu önceden var olan bir tutarsızlık, bu görevin kapsamı DIŞINDA (CAVEMAN/scope discipline — button.tsx'i bu görevde değiştirmiyoruz, görsel olarak ink tonuna zaten yakın).
- `components/ui/card.tsx`, `badge.tsx` mevcut ve kullanılabilir durumda.

## Design Direction
Stitch ekranı `projects/16390705950406305270/screens/38f4a09e6fe643c5a0229c079fea94a9` ("Resmi Sicil Gazetesi ve İlan Panosu") — kullanıcı onaylı referans:
- Üst serit: sade, sol wordmark + sağ metin linkler + tek dolu CTA.
- Hero: asimetrik 7/5 (sola yaslanmış, ortalanmamış), büyük Source Serif 4 başlık (farklı ağırlıkta kelimeler içerebilir), sağda hafif döndürülmüş gerçek "doğrulama sertifikası" kartı (VerifiedSeal + isim + yetkinlik çipleri).
- Zincir bölümü: ince yatay çizgi üzerinde 4 nokta/damga, SADECE son adım (Doğrulanmış Deneyim) çam yeşili mühür ile vurgulu, diğerleri nötr.
- "Neden farklı" bölümü: büyük manifesto alıntısı + dar liste (düz 3-kart ızgarası DEĞİL).
- Mor/mavi/indigo/gradyan YOK.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/page.tsx | Placeholder'dan tam landing sayfasına yeniden yazılır (AC-1 ila AC-8) | medium |
| frontend/messages/tr.json | `home.*` altına yeni anahtarlar eklenir (mevcut `home.title`/`tagline`/`cta` korunur veya güncellenir) | low |

## New Files
| File | Purpose |
|------|---------|
| frontend/components/ui/chain-progress.tsx | Minimal, display-only 4 adımlı zincir göstergesi (status listesi prop alır, AC-5) |
| frontend/components/ui/verified-seal.tsx | Minimal, display-only doğrulama mührü/sertifika rozeti (name/tarih/sicil-no prop alır, AC-6) |
| frontend/components/ui/chain-progress.test.tsx | ChainProgress unit testleri |
| frontend/components/ui/verified-seal.test.tsx | VerifiedSeal unit testleri |
| frontend/app/page.test.tsx | Landing sayfa bütünlüğü (integration) testi |

## Dependencies
- `components/ui/button.tsx`, `card.tsx`, `badge.tsx` — mevcut, olduğu gibi kullanılır.
- `lib/utils.ts` (`cn()`) — class birleştirme için.
- `messages/tr.json` — düz JSON import deseni (next-intl DEĞİL).
- `app/globals.css` design token'ları (`--background`, `--foreground`, `--success`, `--muted`, `--border`) — ChainProgress/VerifiedSeal bunları Tailwind `bg-background`/`text-foreground`/`bg-success` vb. üzerinden kullanmalı, ham hex kod gömülmemeli.

## Migration Required?
Hayır — bu görev sadece frontend statik render, veritabanı/şema değişikliği yok.

## Risks
- (atdd.md'den taşındı) ChainProgress/VerifiedSeal minimal yazılacağı için ileride FE-16/FE-17 genişletirken prop sözleşmesi değişebilir — kabul edilen risk.
- (atdd.md'den taşındı) Stitch referansının gerçek mühür/kağıt dokusu CSS/SVG ile birebir taklit edilemeyebilir — piksel-mükemmel eşleşme zorunlu değil.
- (yeni, Discover'da bulundu) `button.tsx`'in `primary` variant'ı design token değil `slate-900` kullanıyor — bu görevde düzeltilmiyor (kapsam dışı), ama red-team bunu "tutarsızlık" olarak işaretleyebilir; şimdiden not düşülüyor ki sürpriz olmasın.

## Open Questions
Yok — Discover'da bulunan next-intl/button.tsx tutarsızlıkları yukarıda "Dependencies"/"Risks" olarak çözüldü (mevcut kod deseni takip edilecek, kullanıcıya sorulacak gerçek bir belirsizlik yok).
