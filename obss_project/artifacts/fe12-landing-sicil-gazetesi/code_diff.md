# Code Diff — fe12-landing-sicil-gazetesi
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `frontend/components/ui/chain-progress.tsx` — `ChainProgress`, `{label, completed}[]` prop alır, sadece `completed` adımda `border-success bg-success text-background`/`text-success` token'ları, sayaç çemberinde `motion-reduce:transition-none`.
- `frontend/components/ui/verified-seal.tsx` — `VerifiedSeal`, `name?/issuedAt?/registryNo?` opsiyonel prop'lar, hepsi boşsa sadece mühür ikonu render edilir (crash yok, sahte isim yok), kökte `bg-success`.

## Değiştirilen Dosyalar
- `frontend/app/page.tsx` — tamamen yeniden yazıldı: header (wordmark + Giriş Yap/Kayıt Ol linkleri), asimetrik 7/5 hero (`grid-cols-1 md:grid-cols-[7fr_5fr]`, sol başlık+CTA, sağ VerifiedSeal kartı hafif döndürülmüş `-rotate-1`), ChainProgress bölümü, karşılaştırma bölümü, 3 persona kartı, footer. Rakamlar şeridi hiç yazılmadı (AC-3).
- `frontend/messages/tr.json` — `home.*` altına yeni anahtarlar eklendi (`loginLink`, `registerLink`, `heroTitle`, `heroDescription`, `sealCaption`, `chainTitle`, `chain.{claim,evidence,attestation,verified}`, `comparisonTitle/Claim/Verified`, `personasTitle`, `personas.{student,organization,institution}`, `footerNote`); mevcut `title`/`tagline`/`cta` değişmedi.

## Orkestratör Doğrulaması
- `git status --short` ile 7 dosyanın (2 yeni implementasyon + 2 yeni test + 3 değişen) gerçekten değiştiği doğrulandı.
- `chain-progress.tsx`, `verified-seal.tsx`, `page.tsx` satır satır `Read` ile incelendi — hardcoded test-fixture değeri, icat edilmiş "eğer X ise gizle" kısayolu YOK. Davranış atdd.md'nin Davranış Sözleşmesi tablosuyla birebir uyumlu.
- Test dosyalarına dokunulmadığı `git status` ile teyit edildi (test dosyaları `??` yeni olarak zaten test-copilot adımından kalma, code-copilot onları değiştirmemiş).
- Testler BAĞIMSIZ olarak çalıştırıldı (alt-ajanın "33/33 PASS" iddiasına güvenilmedi): `npx vitest run components/ui/chain-progress.test.tsx components/ui/verified-seal.test.tsx app/page.test.tsx` → **33/33 PASS**.
- Tüm test paketi de çalıştırıldı (regresyon kontrolü): `npx vitest run` → **69 dosya, 1213/1213 PASS**.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | `page.tsx` — header/hero/ChainProgress/karşılaştırma/persona/footer sırası |
| AC-2 | `page.tsx` header "Kayıt Ol"→`/kayit`, "Giriş Yap"→`/giris` (tr.json `registerLink`/`loginLink`) |
| AC-3 | Rakamlar şeridi `page.tsx`'te hiç yazılmadı |
| AC-4 | Hero section `grid-cols-1 md:grid-cols-[7fr_5fr]`, h1 JSX'te VerifiedSeal'dan önce |
| AC-5 | `chain-progress.tsx` — boş `steps` ile `.map` boş diziye uygulanır, crash yok |
| AC-6 | `verified-seal.tsx` — `name ? <p>...</p> : null` deseni, sahte isim yok |
| AC-7 | `chain-progress.tsx` sayaç çemberinde `motion-reduce:transition-none` |
| AC-8 | Tüm metin `messages/tr.json`'dan (`const { home } = messages`) |

## Kalan Sınırlamalar
- "Örnek bir doğrulamayı incele" CTA'sı eklenmedi (atdd.md'de route'u netleşmemişti, Unknowns'ta işaretliydi) — sadece "Kayıt Ol"/"Başla" CTA'ları var. Bu, atdd.md'nin kendi Unknowns bölümüyle tutarlı bir kapsam kararı.
- `button.tsx`'in `slate-900` design-token tutarsızlığı (plan.md'de not edilmişti) bu görevde düzeltilmedi — CTA'lar `<Link>` olarak ayrı class'la stillendi (nested `<a>` içinde `<button>` olmaması için doğru bir karar).

## Varsayımlar
- Hero CTA linki için `button.tsx` yerine doğrudan stillenen `<Link>` kullanıldı (anchor içine button koymak geçersiz HTML olurdu) — görsel olarak eşdeğer.

## Görsel/UI Kriteri
Evet — atdd.md bunu işaretlemişti. `verify` adımında `vision-test` (ve mümkünse Lighthouse) ZORUNLU çalıştırılmalı, N/A geçilmemeli.
