# Plan — admin-dogrulama-ve-skill-yonetimi-ekranlari
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (yeni `.tsx` sayfalar). Discover tamamlandı
(bkz. sohbet — mevcut tasarım tokenları: `slate-900` buton, `slate-50` kart,
`rounded-md`, `border-slate-200`). Design Direction bilinçli atlandı: iç admin
aracı, yeni ürün yüzeyi değil, mevcut sistemi birebir tekrar ediyor.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `frontend/messages/tr.json` | AC-1..9 için yeni metin anahtarları (`adminVerificationQueue.*`, `adminSkills.*`) | low |
| `frontend/components/app-shell.tsx` | Admin nav linki eklenir (AC-3/Risks: herkese görünür, backend 404 ile korunuyor) | low |

## New Files
| File | Purpose |
|------|---------|
| `frontend/lib/api/admin.ts` | `getVerificationQueue`, `updateVerificationLevel`, `createSkill`, `updateSkill`, `deprecateSkill`, `mergeSkill` — `institutions.ts`/`client.ts` kalıbını izler (`apiFetch<T>`, `ApiError`/`NetworkError` fırlatır) |
| `frontend/lib/api/admin.test.ts` | admin.ts client fonksiyonlarının unit testi (institutions.test.ts kalıbı) |
| `frontend/app/admin/dogrulama-kuyrugu/page.tsx` | AC-1/3/4/9: kuyruk listesi + seviye güncelleme formu |
| `frontend/app/admin/dogrulama-kuyrugu/page.test.tsx` | AC-1/3/4/9 component testi |
| `frontend/app/admin/skiller/page.tsx` | AC-5/6/7/9: skill listesi + oluştur/güncelle/deprecate/merge formu |
| `frontend/app/admin/skiller/page.test.tsx` | AC-5/6/7/9 component testi |

## Dependencies
- `apiFetch` (`lib/api/client.ts`) — 404/409/422/500/timeout zaten `ApiError`/
  `NetworkError` olarak ayrıştırıyor, admin.ts bunu aynen kullanır, tekrar
  hata-ayrıştırma yazılmaz.
- `AppShell` + `ErrorBanner` — kurum panel ve `calismalar/[id]` sayfalarındaki
  loading/error/success state kalıbı birebir tekrarlanır.
- `messages/tr.json` — sabit metin kuralı (CLAUDE.md: UI metni Türkçe, koda gömülmez).
- React Hook Form + Zod — seviye güncelleme ve skill formu için (.claude/rules/frontend.md).
- TanStack Query — liste + mutation (`useMutation` + `queryClient.invalidateQueries`), Redux yok.

## Migration Required?
Hayır. Backend zaten tam (`backend/app/api/admin.py`, PLAN 3.6'da bitti).
Bu görev yalnızca var olan endpoint'leri tüketen frontend ekliyor.

## Risks
- (atdd.md'den taşındı) Admin nav linki `/me`'de `is_platform_admin` olmadığı
  için herkese görünür olacak — kabul edilen risk, ayrı onay gerektiren
  alt-görev olarak işaretli.
- (atdd.md'den taşındı) Jira YET-114 atananı "Meyrsem" — çakışma olabilir.
- **Yeni bulgu:** `frontend/app/calismalar/[id]/page.tsx:33-38` mevcut 404
  kalıbı, atdd.md'nin AC-3'ünde tarif edilen "genel sayfa bulunamadı ekranı"
  (global `not-found.tsx`) değil — **sayfa içinde satır içi bir uyarı
  mesajı** (`role="alert"`, kırmızı banner, `messages.calismalar.detailNotFound`).
  Kodda `next/navigation`'ın `notFound()` fonksiyonu hiç kullanılmıyor. AC-3/
  AC-9'u bu mevcut kalıpla tutarlı uygulamayı öneriyorum (bkz. Open Questions).

## Kararlar
1. **AC-3/AC-9 404 gösterimi → (a) mevcut konvansiyon.** (kullanıcı
   yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı: `calismalar/[id]/page.tsx`
   kalıbıyla tutarlı, sayfa içi "Kaynak bulunamadı" satır-içi uyarısı
   (`role="alert"`) kullanılır; global `not-found.tsx`'e yönlendirilmez.
   Gerekçe: projede `notFound()` zaten hiç kullanılmıyor, yeni kalıp
   gereksiz sapma olurdu; AC-3/AC-S1'in asıl güvenlik garantisi zaten
   backend'in 404 davranışı, satır içi mesaj "kaynak bulunamadı" dediği
   sürece admin panelinin varlığını sızdırmaz.) Bu karar atdd.md'nin
   Davranış Sözleşmesi tablosundaki #4 satırını ("Genel sayfa bulunamadı
   ekranı" → "sayfa içi satır-içi uyarı, ErrorBanner/alert kalıbı") netleştirir.
