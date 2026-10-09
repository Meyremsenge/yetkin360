# Plan — fe15-auth-duzeni-sicil-gisesi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (`.tsx` dosyaları + Görsel/UI kriteri dolu) — Discover/Design Direction tamamlandı, bulgular aşağıda. Audit atlandı (mevcut UI zaten bilinen jenerik desen, ek tarama gereksiz — fe12'deki aynı gerekçe).

## Discover Bulguları (Playwright ile gerçek app)
- `/giris` Playwright ile gezildi: klasik ortalanmış kart (`flex items-center justify-center min-h-screen` + `max-w-md`), beklenen jenerik SaaS deseni doğrulandı.
- **`--sand` token'ı `app/globals.css`'te GERÇEKTEN YOK** (atdd.md'nin Unknowns'ı doğrulandı) — eklenmesi gerekiyor. Mevcut token deseni: `:root` içinde `--isim: H S% L%;` formatında, `tailwind.config.ts`'te `isim: "hsl(var(--isim))"` olarak eşleniyor.
  - Önerilen değer: `--sand: 36 30% 89%;` (mevcut `--background: 40 30% 97%` ve `--muted: 38 20% 92%`'den biraz daha koyu/doygun bir kum tonu, aynı sıcak palet ailesinde).
- **Tüm 5 sayfanın dış sarmalayıcısı BİREBİR AYNI desende** (`Read` ile doğrulandı):
  ```
  <div className="flex items-center justify-center min-h-screen">
    <div className="max-w-md w-full p-6"> (veya px-4)
      ...sayfa-özel içerik (h1, form, state mesajları)...
    </div>
  </div>
  ```
  Bu, 5 sayfanın da AYNI basit dönüşümle (iki dış `div`'i `<AuthLayout>`'a değiştirme) güncellenebileceği anlamına gelir — iç JSX/state/handler'lara dokunulmaz.
- `/giris` ve `/kayit`: form mantığı ayrı `form.tsx` dosyasında (`LoginForm`/`RegisterForm`), `page.tsx` sadece başlık + form'u render ediyor — EN DÜŞÜK risk.
- `/sifre-unuttum`, `/sifre-sifirla`, `/e-posta-dogrula`: mantık `page.tsx`'in içinde (hook'lar, `useState`, `onSubmit` hep aynı dosyada) — dış sarmalayıcı yine aynı iki `div`, ama JSX'in geri kalanı (yaklaşık 100-200 satır) olduğu gibi `AuthLayout`'un children'ı olarak taşınmalı, TEK BİR SATIR BİLE DEĞİŞTİRİLMEDEN.
- **AC-7 çakışması bulundu ve çözüldü:** `/giris` ve `/kayit`'in `form.tsx` dosyalarında ŞU AN hiç çapraz link yok ("Kayıt Ol"/"Giriş Yap" gibi). atdd.md'nin AC-7'si bu linklerin "belirgin" olmasını istiyor, ama `form.tsx`'e DOKUNULMAZ kısıtı var. **Karar:** çapraz linkler `form.tsx`'e değil, `AuthLayout` bileşeninin kendisine eklenir — her sayfa `AuthLayout`'a kendi ilgili linklerini (`links` prop'u, `{href, label}[]`) geçer, `AuthLayout` bunları marka panelinin altında veya form alanının altında render eder. Bu, hem AC-7'yi karşılar hem `form.tsx`'e dokunmaz.
- `/sifre-sifirla` zaten kendi içinde `/giris`/`/sifre-unuttum`'a linkler barındırıyor (satır 109/137/157) — bu linkler JSX taşınırken OLDUĞU GİBİ korunur, `AuthLayout`'un `links` prop'una AYRICA eklenmez (çift link olmasın diye).

## Design Direction
- **Sıra:** planfrontend.md'nin kendi sırası esas — SOL kum (`--sand`) zeminli marka paneli, SAĞ kağıt zeminde form (Stitch ekranı 594ab6d6'da sıra ters/form sol idi — sadece DOKU/malzeme dili referansı olarak kullanılır, kolon sırası değil).
- Marka paneli içeriği: "Yetkin360" wordmark (serif), serif tek cümle (örn. "Sicil kaydınız, kanıtlarınızla birlikte güvenle saklanır."), altta ince bir çizgi üzerinde 4 adımlı zincir (Beyan/Kanıt/Tanıklık/Doğrulanmış Deneyim — FE-12'de yazılan `ChainProgress` bileşeni YENİDEN KULLANILABİLİR, aynı prop sözleşmesi: `{label, completed}[]`).
- Form tarafı: kağıt zemin (`bg-background`), kart çerçevesi YOK — form doğrudan sayfaya oturur (mevcut `max-w-md` kart hissi kaldırılır).
- Mobilde: tek sütun, üstte ince marka şeridi (tam panel değil — sadece wordmark + tek cümle, zincir gizlenebilir dar ekranda).
- Mor/mavi/indigo/gradyan YOK, sadece mevcut token'lar (`--background`, `--foreground`, `--success`, yeni `--sand`).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/app/globals.css | `--sand` token eklenir | low |
| frontend/tailwind.config.ts | `sand: "hsl(var(--sand))"` renk eşlemesi eklenir | low |
| frontend/app/giris/page.tsx | Dış sarmalayıcı `AuthLayout`'a değişir, `form.tsx` İÇERİĞİNE DOKUNULMAZ | low |
| frontend/app/kayit/page.tsx | Aynı | low |
| frontend/app/sifre-unuttum/page.tsx | Dış sarmalayıcı `AuthLayout`'a değişir, iç JSX/state/handler AYNEN taşınır | medium |
| frontend/app/sifre-sifirla/page.tsx | Aynı (2 render dalı var — ikisi de aynı şekilde sarmalanır) | medium |
| frontend/app/e-posta-dogrula/page.tsx | Aynı | medium |

## New Files
| File | Purpose |
|------|---------|
| frontend/components/ui/auth-layout.tsx | İki kolonlu (masaüstü) / tek kolonlu (mobil) sarmalayıcı: sol marka paneli (wordmark, cümle, ChainProgress, opsiyonel `links` prop), sağ/alt `children` (form içeriği) |
| frontend/components/ui/auth-layout.test.tsx | AuthLayout'un kendi unit testleri |

## Dependencies
- `frontend/components/ui/chain-progress.tsx` (FE-12'de yazıldı) — marka panelindeki 4 adımlı zincir için YENİDEN KULLANILIR, değiştirilmez.
- `frontend/messages/tr.json` — marka panelindeki sabit cümle için yeni `authLayout.*` anahtarları eklenir.
- Mevcut `components/ui/button.tsx` — form içeriklerinde zaten kullanılıyor, dokunulmaz.

## Migration Required?
Hayır — sadece frontend statik render + CSS token.

## Risks
- (atdd.md'den taşındı) En yüksek risk: 3 sayfada JSX'i taşırken state/handler/aria-live bağlarını koparmak. Azaltma: her sayfa değişikliğinden hemen sonra o sayfanın kendi test dosyası ayrı ayrı çalıştırılacak (code-copilot adımında).
- (yeni, Discover'da bulundu) AC-7 (çapraz linkler) çözümü `AuthLayout`'un `links` prop'una bağlı — code-copilot bu prop'u doğru şekilde her sayfaya geçmezse AC-7 kısmen karşılanmaz. Test-copilot bu prop'un her sayfada doğru linklerle geçtiğini ayrı ayrı test etmeli.
- `/sifre-sifirla`'nın zaten kendi içinde linkleri olması (satır 109/137/157) — code-copilot bunları AuthLayout'un `links` prop'uyla ÇİFTLEMEMELİ, sadece JSX'i olduğu gibi taşımalı.

## Open Questions
Yok — atdd.md'nin Unknowns'ındaki `--sand` HSL değeri Discover'da netleştirildi (`36 30% 89%` önerisi, mevcut palet ailesiyle tutarlı). AC-7/form.tsx çakışması yukarıda "AuthLayout'un links prop'u" kararıyla çözüldü.
