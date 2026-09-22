# Test Diff — yet-13-auth-ekranlari (red step)
_3 paralel Haiku alt-ajanı tarafından yazıldı, diske indiği `git status --short` ile doğrulandı._

## Yeni Dosyalar
| Dosya | Satır | Kapsadığı AC |
|---|---|---|
| frontend/app/kayit/page.test.tsx | 310 | AC-1, AC-9, AC-12, AC-S1, AC-S4 |
| frontend/app/e-posta-dogrula/page.test.tsx | 228 | AC-5, AC-6, AC-S3 |
| frontend/app/sifre-unuttum/page.test.tsx | 370 | AC-7, AC-9, AC-10, AC-11, AC-12, AC-S2, AC-S6 |
| frontend/app/sifre-sifirla/page.test.tsx | 544 | AC-6, AC-8, AC-9, AC-10, AC-11, AC-12, AC-S3, AC-S4 |
| frontend/lib/auth/schemas.test.ts | 253 | AC-9 (Zod: registerSchema, loginSchema, forgotPasswordSchema, resetPasswordSchema) |

## Genişletilen Dosyalar
| Dosya | Ne eklendi | Kapsadığı AC |
|---|---|---|
| frontend/app/giris/page.test.tsx | "Form YOK" testleri SİLİNDİ (kasıtlı — placeholder'dan gerçek forma geçiş); AC-6/AC-4 testleri korundu; 9 yeni describe bloğu | AC-2, AC-3, AC-4, AC-6, AC-9, AC-10, AC-11, AC-12, AC-S4, AC-S6 |
| frontend/lib/api/client.test.ts | 15 yeni test — register/login/verifyEmail/forgotPassword/resetPassword | AC-1, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-S1, AC-S2 |
| frontend/lib/auth/should-redirect.test.ts | 8 yeni test — /kayit, /e-posta-dogrula, /sifre-unuttum, /sifre-sifirla public route | Davranış Sözleşmesi (should-redirect genişlemesi, plan.md kararı) |
| frontend/messages/tr.test.ts | 44 yeni anahtar yolu (kayit.*, epostaDogrula.*, sifreUnuttum.*, sifreSifirla.*, giris.* genişleme, errors.rateLimited) | AC-9 |

## Kapsanmayan / Kısmi
- Davranış Sözleşmesi satır 12 (kısmi başarı — cookie reddi): Ayrı bir test fonksiyonu yazılmadı, alt-ajanlar bunu açıkça belirtmedi. `code-copilot`/`red-team` aşamasında hatırlatılacak; şu an için kabul edilebilir bir eksik (atdd.md'de de "gözlemlenmeli" notuyla düşük öncelikli işaretlenmişti, AC listesine bağlanmamıştı).

## Bilinen Sorun (çözüldü)
`@testing-library/user-event` paketi giris/kayit testlerinde 20 yerde kullanılmış ama kurulu değildi — kullanıcı onayıyla `package.json`'a devDependency olarak eklenmesi kararlaştırıldı (plan.md §1b). `code-copilot` bu paketi kuracak.

## Sonraki Adım
`code-copilot` — bu 9 test dosyasını YEŞİLE çeviren implementasyonu yazacak: `lib/auth/schemas.ts`, `lib/api/client.ts` (5 fonksiyon eklenir), `lib/auth/should-redirect.ts` (4 route eklenir), `messages/tr.json` (44 anahtar eklenir), 5 sayfa (`giris` yeniden yazılır, 4 yeni sayfa), + `package.json`/`npm install` (react-hook-form, zod, @hookform/resolvers, shadcn primitifleri, @testing-library/user-event).
