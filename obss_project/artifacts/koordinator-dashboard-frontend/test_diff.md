# Test Diff — koordinator-dashboard-frontend
_Red step (test-copilot) — Haiku alt-ajanı tarafından yazıldı, henüz implementasyon yok_

## Oluşturulan Dosyalar
- `frontend/lib/api/institutions.test.ts` — `getCoordinatorDashboard(institutionId)` API client testleri (9 test)
- `frontend/app/kurum/[id]/panel/page.test.tsx` — `/kurum/[id]/panel` sayfası component testleri (11 test)

## AC Kapsama Tablosu
| AC | institutions.test.ts | page.test.tsx |
|---|---|---|
| AC-1 (happy path) | ✓ | ✓ |
| AC-2 (boş liste) | ✓ | ✓ |
| AC-3 (404 jenerik) | ✓ (tam eşleşme: status 404, code NOT_FOUND) | ✓ (+ "erişiminiz/yetkin" metni YOK doğrulaması) |
| AC-4 (401) | ✓ (tam eşleşme: status 401, code UNAUTHENTICATED) | ✓ (session hook tetiklenmesi) |
| AC-5 (network/500) | ✓ (NetworkError + ApiError(500)) | ✓ (ErrorBanner role="alert" + retry butonu) |
| AC-6/AC-S1 (tenant cache-izolasyonu) | ✓ (ayrı institution_id çağrıları) | ✓ (rerender ile inst-1→inst-2 geçişi, eski verinin kaybolduğu doğrulanıyor) |
| AC-7 (XSS/escape) | ✓ (raw title string döner) | ✓ (script tag DOM'da yok, düz metin render) |
| Loading state | — | ✓ ("Yükleniyor...") |

## Beklenen Durum: RED
`frontend/lib/api/institutions.ts` ve `frontend/app/kurum/[id]/panel/page.tsx` henüz yok — testler import hatasıyla/derleme hatasıyla başarısız olacak. Bu beklenen (test-first).

## Varsayımlar (code-copilot'a devredildi)
- `tr.json` anahtar adları henüz kesinleşmedi — page.test.tsx büyük ölçüde metin varsayımına bağlı kalmadı (görsel içerik/sayaç/başlık üzerinden assert ediliyor), empty-state testi (AC-2) tr.json anahtarına sıkı bağlı değil, sadece sayaç sıfırlarını kontrol ediyor — code-copilot empty-state metnini ekleyip bu testi hâlâ geçirebilir.
- `getCoordinatorDashboard` imzası: `(institutionId: string) => Promise<DashboardResponse | undefined>`, `apiFetch("/institutions/{id}/dashboard")` çağırıyor varsayıldı.
- Sayfa `useParams()` → `{id}` route param'ından institution_id okuyor varsayıldı (plan.md Kararlar bölümüyle tutarlı).
