# Plan — yet-14-talent-profil-yetkinlik
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| frontend/lib/api/client.ts | `updateTalentProfile`, `listSkills`, `getMySkills`, `addSkill`, `removeSkill` eklenir (AC-2, AC-4, AC-5, AC-8) | low — mevcut `apiFetch` üstüne ekleme, `register`/`login` deseniyle birebir aynı (positional parametreler) |
| frontend/lib/session/types.ts | `MeResponse.talent_profile`'ı `Record<string, unknown>` yerine somut alanlarla (`headline`, `department`, `study_year`, `city`, `visibility`, `public_slug`) güçlendirir | low — backend `GetMeResponse.talent_profile` zaten `TalentProfileResponse` (opsiyonel değil), tip sıkılaştırması geriye uyumlu |
| frontend/messages/tr.json | Yeni anahtarlar: `profil.*`, `errors.slugTaken` vb. | low |

## New Files
| File | Purpose |
|------|---------|
| frontend/lib/talent/schemas.ts | Zod: `talentProfileSchema` (headline/department/study_year/city/visibility/public_slug) |
| frontend/lib/talent/schemas.test.ts | Şema testleri |
| frontend/app/profil/page.tsx | `/profil` sayfası — `AppShell` içinde `ProfileForm` + `SkillsSection` render eder (AC-1) |
| frontend/app/profil/page.test.tsx | Sayfa entegrasyon testi |
| frontend/app/profil/profile-form.tsx | Profil düzenleme formu (RHF + Zod), `updateTalentProfile` çağırır (AC-2, AC-3, AC-S3) |
| frontend/app/profil/profile-form.test.tsx | Form testi |
| frontend/app/profil/skills-section.tsx | Yetkinlik listesi + arama/ekleme + kaldırma (AC-4–9, AC-S1, AC-S2) |
| frontend/app/profil/skills-section.test.tsx | Bileşen testi |

**Not (vision-test):** `profil/page.tsx`, `profile-form.tsx`, `skills-section.tsx` render edilen web UI dosyaları — `verify` adımında gate 12 (görsel regresyon) N/A değil, gerekirse aktif değerlendirilmeli.

## Dependencies
- `apiFetch` (lib/api/client.ts) — değişmeden kullanılır; yeni fonksiyonlar `register`/`login` deseniyle (positional parametreler, `body` object olarak apiFetch'e geçirilir) ince sarmalayıcı olur.
- `ApiError`/`NetworkError` duck-typing deseni (YET-13'te tutarlılaştırıldı: `"status" in error`) — bu görevde de AYNI desen kullanılır, `instanceof` kullanılmaz.
- `fetchMe`/`MeResponse` (lib/session/fetch-me.ts, lib/session/types.ts) — GET /me için YENİDEN YAZILMAZ, mevcut `useSession()` hook'u zaten bunu sarıyor; `/profil` sayfası `useSession()`'dan `talent_profile`'ı okur.
- `SESSION_QUERY_KEY` (lib/session/use-session.ts) — `updateTalentProfile` başarılı olduğunda `queryClient.invalidateQueries({queryKey: SESSION_QUERY_KEY})` ile senkronize edilmeli (AppShell/header'ın güncel veriyi göstermesi için — kayit/giriş formlarındaki aynı desen).
- `AppShell` (components/app-shell.tsx) — `/profil/page.tsx` bunu İLK KEZ gerçek bir sayfada kullanır; `AppShell` zaten `useSession` loading/error state'lerini kendi içinde yönetiyor, `page.tsx`'in bunları TEKRAR yönetmesine gerek yok — sadece `<AppShell><ProfileForm/><SkillsSection/></AppShell>` şeklinde children verir.
- `Button`/`Input`/`Label` (components/ui/) + `ErrorBanner` (components/error-banner.tsx) — form-üstü genel hatalar için tekrar kullanılabilir.
- `cn` (lib/utils.ts) — gerekirse.
- Yetkinlik listesi için ayrı bir TanStack Query key (`["talent-skills"]` gibi) — `SESSION_QUERY_KEY`'den bağımsız, skill ekleme/çıkarma sonrası sadece bu key invalidate edilir (AC-5, AC-8) — profil sorgusunu gereksiz yeniden tetiklemez.

## Migration Required?
**Hayır.** Backend'de `skills` tablosu zaten var (`backend/app/models/skill.py`) ama talent-skill ilişki tablosu (`claimed_level` tutan junction table) HİÇ yok — YET-11 (backend) henüz başlamadı, şema dahil. Bu görev tamamen frontend, backend şeması bu görevin kapsamında DEĞİL.

## Risks
(atdd.md'den taşındı + netleşen)
- Backend'de `/talents/me/skills` (GET/POST/DELETE) ve `/skills` uçları — hem router hem DB şeması hiç yok (grep ile doğrulandı: `backend/app/api/` altında skills router yok, `backend/app/models/` altında talent-skill junction tablosu yok). "Sözleşme önce" kuralıyla mock'la ilerleniyor.
- `MeResponse.talent_profile` tip sıkılaştırması `fetch-me.test.ts`/`use-session.test.tsx`'teki mevcut testleri etkileyebilir (şu an gevşek tip bekliyor olabilirler) — `test-copilot` bu testlere DOKUNMAYACAK, sadece yeni alanlar EKLEYECEK şekilde tip genişletilmeli (union/optional alanlar, mevcut testleri kırmayacak şekilde).

## Open Questions
Yok — atdd.md'nin Unknowns bölümündeki 2 madde (kurumsal kullanıcı senaryosu, public_slug format validasyonu) bu görevin kapsamını etkilemeyecek kadar düşük öncelikli (ikisi de "varsayılan davranış zaten çalışır" ile kapanmış); code-copilot aşamasında ek karar gerekmiyor.
