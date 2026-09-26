# Code Diff — koordinator-dashboard-frontend
_Green step (code-copilot) — Haiku alt-ajanı tarafından yazıldı, orkestratör tarafından Read+test-run ile doğrulandı_

## Oluşturulan Dosyalar
- `frontend/lib/api/institutions.ts` — `getCoordinatorDashboard(institutionId)`, `DashboardResponse`/`PendingItem` tipleri, `apiFetch` kullanıyor (kendi fetch mantığı yok)
- `frontend/app/kurum/[id]/panel/page.tsx` — client component, `useParams` route param, `useQuery(["institution-dashboard", institutionId], ...)`, `AppShell` + `ErrorBanner` (mevcut component'ler, yeniden yazılmadı)

## Değiştirilen Dosyalar
- `frontend/messages/tr.json` — `kurumPanel` anahtarı eklendi (7 alt-anahtar: title, iki sayaç etiketi, iki liste başlığı, iki empty-state metni). Mevcut anahtarlara dokunulmadı (diff ile doğrulandı).

## Doğrulama (orkestratör tarafından, sub-agent özetine güvenilmedi)
- `git status --short` ile dosyaların gerçekten diskte olduğu doğrulandı.
- İki implementasyon dosyası da tam okundu (Read) — CAVEMAN'a uygun, gereksiz soyutlama/dosya yok, mevcut `calismalar/[id]/page.tsx` kalıbı birebir takip edilmiş.
- `tr.json` diff'i incelendi — sadece ekleme, mevcut anahtarlar bozulmamış.
- **Testler gerçekten çalıştırıldı** (sub-agent'ın "geçecek" iddiasına güvenilmedi): `npx vitest run lib/api/institutions.test.ts "app/kurum/[id]/panel/page.test.tsx"` → **2 dosya, 21/21 test PASS**.

## AC Kapsama (kod okumasıyla teyit edildi)
| AC | Karşılandı mı | Not |
|---|---|---|
| AC-1 | ✓ | İki sayaç kartı + iki liste, `title` + `started_on`/`ended_on` render ediliyor |
| AC-2 | ✓ | `length === 0` kontrolü, ayrı empty-state metinleri |
| AC-3 | ✓ | Backend `error.message` olduğu gibi gösteriliyor, ek metin yok |
| AC-4 | ✓ | 401 → `ErrorBanner`, mevcut session-hook auth-guard akışına bırakılmış (page.tsx kendi yönlendirme kodu yazmıyor) |
| AC-5 | ✓ | `ErrorBanner` (role="alert" zaten component içinde) + `onRetry={() => refetch()}` |
| AC-6/AC-S1 | ✓ | `queryKey: ["institution-dashboard", institutionId]` — institutionId cache key'de |
| AC-7 | ✓ | `{item.title}` düz JSX metni, `dangerouslySetInnerHTML` YOK |

## Kalan Sınırlamalar
- Nav linki eklenmedi (plan.md kararı — kapsam dışı).
- `verify` adımında henüz çalıştırılmadı: `npm run lint`, `npm run typecheck`, `vision-test` (bu bir UI görevi, atdd.md Görsel/UI kriteri dolu).
