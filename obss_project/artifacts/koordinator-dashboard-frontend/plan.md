# Plan — koordinator-dashboard-frontend
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (`.tsx` dosyaları + Görsel/UI kriteri dolu) — Discover/Audit/Design Direction `frontend-pipeline` skill'i ile tamamlandı, bulgular aşağıda "Dependencies" ve ilgili bölümlere işlendi.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `frontend/messages/tr.json` | Yeni sayfa için `kurumPanel` anahtarı eklenecek (başlık, sayaç etiketleri, empty-state metinleri, hata mesajları) — CLAUDE.md kuralı: UI metni koda gömülmez | low |

Not: Nav linki (AppShell değişikliği) kararla kapsam dışı bırakıldı — bkz. Kararlar bölümü.

## New Files
| File | Purpose |
|------|---------|
| `frontend/app/kurum/[id]/panel/page.tsx` | Yeni sayfa — client component, TanStack Query ile `GET /institutions/{id}/dashboard` çeker, iki sayaç kartı + iki liste gösterir |
| `frontend/app/kurum/[id]/panel/page.test.tsx` | Component testi (mevcut `calismalar/[id]/page.test.tsx` kalıbıyla tutarlı) |
| `frontend/lib/api/institutions.ts` | Yeni API client — `getCoordinatorDashboard(institutionId)`, `apiFetch` kullanır (bkz. Dependencies) |
| `frontend/lib/api/institutions.test.ts` | API client testi (mevcut `evaluation.test.ts`/`evidence.test.ts` kalıbıyla tutarlı) |

## Dependencies

**Frontend-pipeline Discover bulguları (tekrar keşfedilmeyecek, buradan alınacak):**
- `frontend/app/layout.tsx`'te (RootLayout) global nav YOK — her sayfa kendi `AppShell` sarmalayıcısını kullanıyor. Nav linki eklenecek başka bir dosya mevcut değil (atdd.md'nin Unknown'ı çözüldü, ama bu kez **yeni bir Open Question** doğurdu — bkz. aşağıda).
- `frontend/components/error-banner.tsx` (`ErrorBanner`) — `role="alert"` + retry butonu, AC-5 için **birebir yeniden kullanılacak**, yeniden yazılmayacak.
- `frontend/components/ui/button.tsx` (`Button`) — native `<button>`, focus-ring korunuyor, yeniden kullanılacak.
- `frontend/app/calismalar/[id]/page.tsx` — TanStack Query kalıbı: `useQuery({queryKey: [...], queryFn: () => ...})`, `ApiError` ile 404 ayrımı, Tailwind slate paleti (`text-slate-600`, `bg-slate-50`, `rounded-md border border-slate-200`), `dl`/`dt`/`dd` sayaç çiftleri için, `ul`/`li` liste için, empty-state mesajları `tr.json`'dan. Yeni sayfa BİREBİR bu kalıbı takip edecek.
- `frontend/lib/api/client.ts` (`apiFetch`) — auth cookie + CSRF + 401-refresh-retry mantığı zaten var; yeni API client dosyası (`institutions.ts`) `public.ts`'teki (auth'suz, kendi fetch'i olan) kalıbı DEĞİL, `client.ts` → `apiFetch` kalıbını kullanacak (bu sayfa authenticated).
- `frontend/lib/session/use-session.ts` (`useSession`) — `session.data.institutions` (`unknown[]`, her biri `{id, name}`) üzerinden kullanıcının üye olduğu kurumlar okunabilir; rol bilgisi YOK (bkz. Risks).
- Design Direction: mevcut proje çapında tutarlı minimal Tailwind dili (slate palet, `rounded-md`, `text-sm`) korunacak, yeni bir estetik yön YOK (audit: bu kalıpta HIGH/MEDIUM a11y/UI bulgusu yok, güvenle taşınabilir).

**Backend sözleşmesi (değişiklik gerekmiyor, zaten var):**
- `GET /institutions/{institution_id}/dashboard` → `backend/app/api/institutions.py` (bkz. `koordinator-dashboard-ucu/atdd.md` — tam response şeması orada).

## Migration Required?
**Hayır.** Bu görev sadece var olan bir backend ucunu tüketen bir frontend sayfası ekliyor — şema/migration değişikliği yok.

## Risks
- (atdd.md'den taşındı) MVP'de kullanıcının tek kuruma üye olduğu varsayılıyor — `GET /me`'nin `institutions` alanı rol döndürmüyor, birden fazla kurum durumunda hangi `institution_id`'nin gösterileceği netleşmemiş.
- ~~AppShell nav linki riski~~ — Kararlar bölümünde nav linki kapsam dışı bırakıldığı için bu risk artık geçerli değil, `app-shell.tsx`'e hiç dokunulmuyor.

## Open Questions

1. **Nav linki nereye eklenecek?** Discover bulgusu: proje çapında hiçbir nav/menü bileşeni yok. İki seçenek var: (a) `AppShell`'e koşullu bir link eklemek (yukarıdaki risk), (b) bu görevi SADECE sayfanın kendisiyle sınırlamak, nav linkini kapsam dışı bırakmak (kullanıcı `/kurum/{id}/panel`'e doğrudan URL ile ulaşır, PLAN 3.10'da veya ayrı bir görevde linklenir). **Öneri: (b)** — YET-113'ün kapsamı "koordinatör dashboard" sayfası, genel nav altyapısı değil; `AppShell`'e dokunmak görevi büyütür (scope creep) ve paylaşılan dosya riskini gereksiz yere üstlenir.
2. **`institution_id` nereden geliyor?** Route param (`/kurum/[id]/panel`, mevcut `calismalar/[id]` kalıbıyla tutarlı) mı, yoksa `/me`'den otomatik türetilip kullanıcı hiç ID görmeden `/panel` gibi sabit bir route mu? **Öneri: route param** — backend zaten `institution_id`'yi path'ten alıyor ve yetkiyi kendi scope'unda kontrol ediyor (404), frontend'in ek bir "hangi kurum" mantığı icat etmesine gerek yok; sayfa açılışında `session.data.institutions[0]?.id` varsayılan olarak kullanılabilir ama URL'de görünür kalır (paylaşılabilir link, mevcut `calismalar/[id]` ile tutarlı).

Kullanıcıya sorulacak, "sen karar ver" denirse yukarıdaki öneriler (b) ve "route param" uygulanacak.

## Kararlar
1. Nav linki → **(b) kapsam dışı bırakıldı** (kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı: `AppShell` tüm authenticated sayfaları etkileyen tek paylaşılan dosya, blast-radius riski; YET-113 kapsamı sadece dashboard sayfası).
2. `institution_id` → **route param** (`/kurum/[id]/panel`) (kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı: backend zaten path'ten alıp kendi scope'unda 404 kontrolü yapıyor, URL paylaşılabilir kalır, `calismalar/[id]` kalıbıyla tutarlı).

Bu kararlar doğrultusunda "Files to Modify" tablosundan `frontend/components/app-shell.tsx` satırı KALDIRILDI (nav linki kapsam dışı) — bu görev artık sadece `frontend/messages/tr.json`'a yeni anahtar ekliyor, `app-shell.tsx`'e dokunmuyor.
