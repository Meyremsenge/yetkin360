# Plan — public-profil-ve-dogrulama-sayfalari
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (.tsx dosyaları + Görsel/UI kriteri dolu).
Discover/Design Direction bilinçli olarak atlandı — mevcut kart/liste deseni
(`calismalar/[id]/page.tsx`, `skills-section.tsx`) birebir tekrarlanıyor, yeni
bir tasarım yönü kararı gerekmiyor.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/lib/auth/should-redirect.ts | `isPublicRoute()`'a `/p/` ve `/v/` prefix kontrolü eklenir (AC-6) — eğik çizgili, `/profil` ile çakışmayacak şekilde (AC-7) | **high** (yanlış yazılırsa yetkilendirme kaçağı) |
| frontend/lib/auth/should-redirect.test.ts | AC-6 (/p, /v izinli) + AC-7 (/profil hâlâ korumalı — regresyon) testleri eklenir | low |
| frontend/messages/tr.json | Yeni UI metinleri (`publicProfile`/`publicVerification` nesneleri) | low |

## New Files
| File | Purpose |
|------|---------|
| frontend/lib/api/public.ts | `getPublicProfile(slug)`, `getPublicVerification(token)` — basit `fetch()` (credentials YOK), `lib/api/errors.ts`'teki `ApiError`/`parseApiError`/`NetworkError` sınıflarını yeniden kullanır |
| frontend/app/p/[slug]/page.tsx | Public profil sayfası, `"use client"`, `AppShell` KULLANMAZ, `useParams`+`useQuery` deseni (`calismalar/[id]/page.tsx`'ten) |
| frontend/app/p/[slug]/page.test.tsx | Component testi |
| frontend/app/v/[token]/page.tsx | Doğrulama sayfası, aynı desen |
| frontend/app/v/[token]/page.test.tsx | Component testi |

## Dependencies
- `frontend/lib/api/errors.ts` — `ApiError`, `parseApiError`, `NetworkError` sınıfları zaten var, yeniden kullanılacak (yeni hata sınıfı icat edilmeyecek).
- `frontend/lib/auth/should-redirect.ts` — mevcut `isPublicRoute()` fonksiyonu, sadece iki `if` satırı eklenecek, yeniden yazılmayacak.
- `backend/app/api/public.py` — response şemaları zaten sabit (YET-105/106), bu görev onları DEĞİŞTİRMEZ, sadece tüketir.

## Migration Required?
**Hayır.** Sadece frontend değişikliği, backend'e dokunulmuyor.

## Açık Soru Çözümü (atdd.md'nin Unknowns'ından, kod keşfiyle netleşti — kullanıcıya sorulacak yeni bir belirsizlik DEĞİL)
atdd.md'nin Unknowns'ı: SEO meta tag (`generateMetadata`) server component gerektirir, ama proje genelinde tüm sayfalar `"use client"`. Kod keşfi: `app/layout.tsx` zaten statik bir `metadata` export ediyor (server component, kök seviyede). Bu görevde per-sayfa dinamik `generateMetadata` (ör. sayfa başlığına `display_name` eklemek) EKLENMEYECEK — bu, mevcut "hepsi use client" mimarisini değiştirmeyi gerektirir (sayfayı server component + ayrı client alt-bileşene bölmek), ki bu atdd.md'nin SEO kriterini Medium/"kritik değil" olarak işaretlemesiyle orantısız bir mimari genişleme olurdu (CAVEMAN ihlali). Kök `layout.tsx`'in statik "Yetkin360" başlığı yeterli kabul edildi. Bu KAPSAM DIŞI listesine eklendi.

## Risks
- atdd.md'den taşınan: `isPublicRoute()` yanlış yazılırsa (`/profil` ile çakışma) ciddi bir yetkilendirme kaçağı — AC-7 regresyon testi olmadan bu değişiklik commit'e giremez.
- `apiFetch`'in `BASE_URL` fallback tutarsızlığı (`/api/v1` öneki) bu görevin kapsamı dışı — `frontend/lib/api/public.ts`, `client.ts`'teki `BASE_URL` sabitiyle AYNI ifadeyi (`process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"`) kullanmalı (sabit `export` edilmemiş, `client.ts`'i bu görev kapsamında refactor ETMEDEN aynı ifadeyi tekrar yazmak yeterli) — farklı/yeni bir fallback değeri İCAT EDİLMEMELİ.

## Open Questions
Yok.
