# Code Diff — admin-dogrulama-ve-skill-yonetimi-ekranlari
_Green step (code-copilot, Haiku alt-ajanı tarafından yazıldı)_

## Oluşturulan Dosyalar
- `frontend/lib/api/admin.ts` — 7 API client fonksiyonu (`getVerificationQueue`,
  `updateVerificationLevel`, `createSkill`, `updateSkill`, `deprecateSkill`,
  `mergeSkill`, `getSkills`), `apiFetch<T>` kalıbını izliyor, hepsi AC/AC-S
  numarasıyla JSDoc'lu. Diskte doğrulandı (`git status --short` → `??`).
- `frontend/app/admin/dogrulama-kuyrugu/page.tsx` — kuyruk tablosu +
  seviye güncelleme, `AppShell`/TanStack Query/sayfa-içi `role="alert"` 404
  kalıbı. İçerik okunup AC-1/3/4 ile karşılaştırıldı, uyumlu.
- `frontend/app/admin/skiller/page.tsx` — skill oluşturma formu + liste +
  deprecate/merge. Diskte doğrulandı, henüz satır satır okunmadı (aşağıya bkz).

## Değiştirilen Dosyalar
- `frontend/messages/tr.json` — `adminVerificationQueue.*`, `adminSkills.*`
  anahtarları eklendi. Diskte doğrulandı (`git status --short` → `M`).
- `frontend/components/app-shell.tsx` — admin nav linkleri eklendi. Diskte
  doğrulandı (`git status --short` → `M`).

## AC Kapsama (sub-agent raporu + Read ile çapraz kontrol)
| AC | Durum |
|---|---|
| AC-1 | admin.ts:56-60 + page.tsx tablo render — OK |
| AC-2 | admin.ts:70-81 + useMutation + başarı bildirimi — OK |
| AC-3/AC-S1 | page.tsx:63-71 sayfa-içi `role="alert"` 404 uyarısı — OK, plan.md kararına uygun |
| AC-4 | page.tsx:72-75 boş-durum uyarısı — OK |
| AC-5/AC-6/AC-7 | admin.ts + skiller/page.tsx — sub-agent raporunda var, tam satır satır doğrulama `verify` adımında test çalıştırılarak yapılacak |
| AC-8 | admin.ts hata fırlatma (apiFetch zaten ApiError/NetworkError atıyor) + page.tsx onError dalları — OK |
| AC-9/AC-S2 | Tüm admin.ts fonksiyonları apiFetch üzerinden 404'ü olduğu gibi fırlatıyor, ayırt edici davranış yok — OK |

## Test dosyalarına dokunuldu mu?
Hayır — `git status --short` çıktısında `admin.test.ts`/`page.test.tsx`
dosyaları için değişiklik yok.

## Not
Sub-agent'ın "tüm testler yeşil olmalı" iddiası doğrulanmadı — gerçek test
çalıştırması `verify` adımının işi, burada sadece dosyaların diskte var
olduğu ve AC'lerle örtüştüğü statik olarak teyit edildi.
