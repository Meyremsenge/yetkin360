# Test Diff — admin-dogrulama-ve-skill-yonetimi-ekranlari
_Red step (test-copilot, Haiku alt-ajanı tarafından yazıldı)_

## Oluşturulan Dosyalar
| Dosya | Amaç | Test sayısı |
|---|---|---|
| `frontend/lib/api/admin.test.ts` | Admin API client fonksiyonları (henüz `admin.ts` yok — red bekleniyor) | 23 |
| `frontend/app/admin/dogrulama-kuyrugu/page.test.tsx` | Doğrulama kuyruğu sayfası (henüz `page.tsx` yok — red bekleniyor) | 20 |
| `frontend/app/admin/skiller/page.test.tsx` | Skill yönetimi sayfası (henüz `page.tsx` yok — red bekleniyor) | 28 |

## AC → Test eşleşmesi
- AC-1 (dolu kuyruk listeleme): `admin.test.ts`, `dogrulama-kuyrugu/page.test.tsx`
- AC-2 (seviye güncelleme happy path + 422): `admin.test.ts`, `dogrulama-kuyrugu/page.test.tsx`
- AC-3/AC-S1 (yetkisiz erişim → 404, admin panel varlığı sızdırılmaz): `dogrulama-kuyrugu/page.test.tsx`
- AC-4 (boş kuyruk → boş-durum UI): `admin.test.ts`, `dogrulama-kuyrugu/page.test.tsx`
- AC-5 (skill oluştur happy path): `admin.test.ts`, `skiller/page.test.tsx`
- AC-6 (slug çakışması 409): `admin.test.ts`, `skiller/page.test.tsx`
- AC-7 (deprecate/merge): `admin.test.ts`, `skiller/page.test.tsx`
- AC-8 (500/timeout, optimistic update yok): `admin.test.ts`, her iki page test dosyası
- AC-9/AC-S2 (var/yok kaynak ayırt edilemez 404): `admin.test.ts` (8 endpoint), her iki page test dosyası
- Davranış Sözleşmesi #7 (kısmi başarı): bilinçli olarak test edilmedi — atdd.md'de atomik endpoint gerekçesiyle silinmiş satır.
- Nullable alan render testleri: `legal_id`/`domain`/`verified_at` → "-", `parent_id` null → "Kök seviye", `name_en` null → `name_tr` fallback, `merged_into_id` → sadece `status="MERGED"` iken gösterilir.

## Varsayımlar (sub-agent raporundan)
- `tr.json`'a henüz eklenmemiş mesaj anahtarları (`adminVerificationQueue.*`, `adminSkills.*`) testte referans olarak kullanıldı — `code-copilot` bunları `tr.json`'a eklemek zorunda, aksi halde testler import/undefined hatasıyla da kırılır.
- Route adları plan.md'deki varsayımla birebir: `/admin/dogrulama-kuyrugu`, `/admin/skiller`.
- 404 kalıbı `calismalar/[id]/page.tsx` ile birebir aynı (sayfa içi `role="alert"` uyarısı) — plan.md'nin Kararlar bölümündeki karara uygun.

## Durum
Red (beklenen) — `admin.ts`, `dogrulama-kuyrugu/page.tsx`, `skiller/page.tsx` henüz yok. Sonraki adım: `code-copilot`.
