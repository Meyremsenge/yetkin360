# Plan — admin-link-rol-sizintisi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici VAR (`.tsx` dosyası + Görsel/UI kriteri dolu).
Design Direction adımı atlandı — bu mevcut bir AppShell nav'ının düzeltilmesi,
yeni bir tasarım/reshape değil; Jira zaten somut bir öneri veriyor (logo +
linkler + kullanıcı menüsü) ve YET-247 (tasarım sistemi) henüz uygulanmadığı
için mevcut Tailwind utility class'ları korunacak, yeni bileşen icat edilmeyecek.

## Discover (kod okuma — gerçek tarayıcı gerekmedi, backend auth gerektiriyor)
- `backend/app/api/admin.py:48` — `_require_admin()` sadece `principal.is_platform_admin` kontrol ediyor, coordinator/supervisor'la ilgisi yok. atdd.md'nin varsayımı doğrulandı.
- `backend/app/services/authorization.py:46` — `Principal.is_platform_admin: bool` zaten mevcut.
- `backend/app/api/me.py` — `GetMeResponse`/`UserResponse` şu an `id`, `email`, `email_verified` dönüyor; `is_platform_admin` yok.
- `frontend/lib/session/types.ts` — `MeResponse.user` interface'i opsiyonel alanlara açık (`isMeResponse` guard'ı zorunlu alan olarak sadece `id`yi kontrol ediyor) — `is_platform_admin?: boolean` eklemek guard'ı bozmaz.
- `frontend/lib/session/use-session.ts` — değişiklik gerektirmiyor, `session.data` zaten `MeResponse` tipini pass-through ediyor.
- `frontend/messages/tr.json`'da `shell.adminVerificationQueueLink`/`adminSkillsLink` var ama "Çalışmalarım"/"Profil" nav linkleri için HİÇ mesaj anahtarı yok — yeni eklenecek.
- Mevcut route'lar (başka sayfalardan teyit edildi): `/calismalar` (Çalışmalarım), `/profil` (Profil), `/admin/dogrulama-kuyrugu`, `/admin/skiller`, `/giris`.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/app/api/me.py | `UserResponse`'a `is_platform_admin: bool` alanı eklenecek, `get_me()` içinde `user.is_platform_admin` (veya `principal.is_platform_admin`) response'a geçirilecek (AC-1/2/3/4, AC-S2) | low |
| frontend/lib/session/types.ts | `MeResponse.user` interface'ine `is_platform_admin?: boolean` eklenecek (AC-4: opsiyonel, eksik/null durumunu tip sisteminde de yansıtmak için) | low |
| frontend/components/app-shell.tsx | Nav yeniden düzenleme: üst bar (logo + Çalışmalarım + Profil + [admin linkleri sadece is_platform_admin===true ise] + kullanıcı menüsü/Çıkış), eski alttaki `border-t` footer bloğu kaldırılacak (AC-1/2/3/4/5) | medium — mevcut session/error-state render mantığının (loading/error/empty-org banner'ları) üstüne eklenecek, bunlara dokunulmayacak |
| frontend/messages/tr.json | `shell` altına yeni anahtarlar: örn. `shell.engagementsLink: "Çalışmalarım"`, `shell.profileLink: "Profil"` (AC-5) | low |

## New Files
Yok.

## Dependencies
- `frontend/components/ui/button.tsx` — kullanıcı menüsü/Çıkış butonu için mevcut `Button` bileşeni kullanılabilir (yeni bileşen icat edilmeyecek, kapsam dışı YET-247).
- Backend: `principal.is_platform_admin` zaten `get_current_principal` dependency'sinden geliyor, `get_me()` imzasına ek parametre gerekmiyor (principal zaten mevcut).
- AC-S1 (regresyon): `backend/tests/authorization/test_admin_authz.py` içinde zaten `is_platform_admin: false` ile admin ucuna erişimin 404 döndüğünü doğrulayan bir test VAR MI kontrol edilmeli — `test-copilot` adımında bu dosya okunacak, varsa yeni test eklenmez (zaten regresyon korumalı), yoksa eklenecek.

## Migration Required?
Hayır — `is_platform_admin` kolonu `users` tablosunda zaten var (`85ce30db9b84_add_is_platform_admin_to_users` migration'ı ile). Sadece response şeması ve frontend tip/render değişikliği.

## Risks
(atdd.md'den) Session cache/staleness — TanStack Query refetch'e kadar eski admin durumu bir süre görünebilir. Kabul edilen risk, bu görevde ele alınmıyor (AC-S1 gerçek yetkinin her zaman backend'de kontrol edildiğini garanti ediyor).
(plan aşamasında bulunan) `app-shell.tsx`'in session loading/error/empty-org dallarının HER BİRİNİN üstüne yeni üst bar eklenecek — bu dallardan birini bozmadan eklemek dikkat gerektiriyor, `code-copilot`'a bu sırayı KORUMASI net anlatılmalı.

## Open Questions
Yok — atdd.md'nin "Unknowns" bölümündeki üst bar görsel tasarımı, Jira'nın kendi önerisi + mevcut Tailwind class desenleriyle (CAVEMAN: en basit, mevcut class'larla) netleşti: minimal bir `flex justify-between items-center p-4 border-b` üst bar, mevcut `Button`/`Link` bileşenleri kullanılacak.
