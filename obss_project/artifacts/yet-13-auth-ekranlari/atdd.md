---
task_slug: yet-13-auth-ekranlari
jira_id: YET-13
saga_task_id: null
priority: high
threat_model: done
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 60
  integration: 40
  e2e: 0
affected_modules:
  - frontend/app/kayit/ (yeni)
  - frontend/app/giris/page.tsx (placeholder → gerçek form)
  - frontend/app/e-posta-dogrula/ (yeni)
  - frontend/app/sifre-unuttum/ (yeni)
  - frontend/app/sifre-sifirla/ (yeni)
  - frontend/lib/api/client.ts (register/login/verifyEmail/forgotPassword/resetPassword fonksiyonları eklenir)
  - frontend/lib/auth/should-redirect.ts (public route allowlist genişler — AUTH MANTIĞI, onay gerekir)
  - frontend/messages/tr.json (yeni UI metinleri)
---

# ATDD — yet-13-auth-ekranlari

## Jira Kaynağı
[YET-13 — Frontend: kayıt, giriş, e-posta doğrulama, şifre sıfırlama ekranları](https://kuyusuzyusuf123.atlassian.net/browse/YET-13)
User Story (Jira'dan birebir): "As a new or returning user I want registration, login, email verification and password reset screens So that I can manage my own account without contacting support"
Not (Jira açıklamasından birebir): "PLAN.md Faz 1, madde 1.13. Owner: frontend. Bağımlılık (sözleşme önce kuralı): 1.4/1.6'nın API sözleşmesi (docs/API.md) — backend'in bitmesini beklemeden mock ile ilerlenir."

## Persona
İkisi de: yeni kayıt olan kullanıcı (/kayit, /e-posta-dogrula) ve mevcut kullanıcı (/giris, /sifre-unuttum, /sifre-sifirla).

## Hedef (Neden)
Kullanıcı destek ekibiyle iletişime geçmeden kendi hesabını yönetebilsin (kayıt, giriş, unutulan şifreyi kurtarma) — destek yükünü azaltır.

## User Story
As a new or returning user
I want registration, login, email verification and password reset screens
So that I can manage my own account without contacting support

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given /kayit sayfası, When kullanıcı geçerli email+password(≥8)+full_name girip submit eder, Then backend 201 döner, oturum AÇILMAZ (cookie yok), kullanıcı "e-postanı doğrula" mesajıyla /giris'e yönlendirilir.
2. [Critical] Given /giris sayfası, When kullanıcı doğru email+password girer, Then backend 200 + 3 cookie döner, oturum kurulur (use-session), `next` param varsa oraya yoksa ana sayfaya yönlendirilir.
3. [Critical] Given /giris sayfası, When email veya password yanlıştır, Then backend 401 INVALID_CREDENTIALS döner, kullanıcı TEK ve genel bir mesaj görür ("E-posta veya şifre hatalı"), hangi alanın yanlış olduğu belirtilmez.
4. [High] Given /giris sayfası, When hesap kilitliyse, Then backend 423 döner, kullanıcı 401'den FARKLI, kilitlenme durumunu belirten bir mesaj görür.
5. [High] Given /e-posta-dogrula?token=... sayfası açılır, When token geçerliyse, Then otomatik POST edilir, backend 204 döner, "doğrulandı" mesajı + /giris linki gösterilir.
6. [High] Given /e-posta-dogrula veya /sifre-sifirla sayfası, When token geçersiz/süresi dolmuşsa (400/410), Then kullanıcı "bağlantı geçersiz/süresi dolmuş" mesajı + ilgili yeniden başlatma linkini görür (doğrulama: tekrar gönder akışına yönlendirme; reset: /sifre-unuttum'a dön).
7. [Critical] Given /sifre-unuttum sayfası, When herhangi bir email girilip submit edilirse (kayıtlı olsun olmasın), Then backend her zaman 204 döner, kullanıcı HER ZAMAN aynı tek mesajı görür.
8. [High] Given /sifre-sifirla?token=... sayfası, When geçerli token + yeni şifre (≥8, tekrar alanıyla eşleşen) girilirse, Then backend 204 döner, oturum AÇILMAZ, "şifren değişti" mesajıyla /giris'e yönlendirilir.
9. [Medium] Given herhangi bir form, When backend 422 (validasyon) döner, Then ilgili alanın altında backend mesajı gösterilir; ayrıca client-side ön-doğrulama (email formatı, password min 8) submit öncesi anında geri bildirim verir.
10. [Medium] Given herhangi bir form, When backend 429 döner, Then kullanıcı genel bir "çok fazla deneme" mesajı görür, form OTOMATİK yeniden denemez.
11. [Medium] Given herhangi bir form, When ağ hatası/timeout oluşursa (fetch reddi), Then kullanıcı "bağlantı hatası" mesajı görür, submit butonu tekrar aktif olur (kilitli kalmaz).
12. [High] Given herhangi bir form, When submit tıklanır, Then buton submit süresince disabled+loading olur; ikinci tıklama HİÇBİR ek istek göndermez (çift submit engeli).
13. [Critical] **AC-S1 (kayıt numaralandırma):** Given /kayit formu, When zaten kayıtlı bir email ile submit edilirse, Then backend'in "her zaman 201" davranışı UI'da AYNEN yansıtılır — farklı mesaj, farklı gecikme veya farklı stil YOK.
14. [Critical] **AC-S2 (şifre-unuttum numaralandırma):** Given /sifre-unuttum formu, When kayıtlı olmayan bir email girilirse, Then kullanıcı kayıtlı email girilmiş gibi AYNI tek mesajı görür (farklı metin/durum yok).
15. [High] **AC-S3 (token XSS/log sızıntısı):** Given /e-posta-dogrula veya /sifre-sifirla sayfası, When URL'deki `token` query param'ı işlenirse, Then `dangerouslySetInnerHTML` kullanılmaz, token sayfada ham HTML olarak render edilmez, yalnızca POST body'sinde backend'e gönderilir.
16. [High] **AC-S4 (şifre alanı hijyeni):** Given herhangi bir password input'u, When form render edilir/submit edilirse, Then `type="password"` + uygun `autoComplete` (`new-password`/`current-password`) kullanılır; password değeri hiçbir `console.*` çağrısına veya network log'una yazılmaz.
17. [Medium] **AC-S5 (open redirect yok):** Given kayıt/doğrulama/reset sonrası yönlendirme, When hedef URL üretilirse, Then hedef URL kullanıcı girdisinden (query param, backend body) DEĞİL sabit route sabitlerinden (`/giris` vb.) türetilir — `next` param'ı yalnızca mevcut middleware/login akışında ve mevcut `sanitizeNext` ile kullanılmaya devam eder, yeni sayfalar kendi serbest redirect hedefi üretmez.
18. [Medium] **AC-S6 (DoS — otomatik retry yok):** Given 429 yanıtı alınmış bir form, When kullanıcı hiçbir ek eylemde bulunmazsa, Then istemci otomatik olarak isteği tekrar GÖNDERMEZ (retry/backoff istemci tarafında yok).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Kayıt happy path | 201 user_id | Oturum kurulmaz (cookie yok) | "Kaydınız alındı, e-postanızı doğrulayın" + /giris'e yönlendirme | AC-1 |
| 2 | Giriş happy path | 200 user_id+role+email_verified+cookies | Oturum kurulur | `next` hedefi veya ana sayfa | AC-2 |
| 3 | Giriş - geçersiz kimlik bilgisi | 401 INVALID_CREDENTIALS | Form hata state'i | "E-posta veya şifre hatalı." (ayrım yok) | AC-3 |
| 4 | Giriş - hesap kilitli | 423 ACCOUNT_LOCKED | Form hata state'i | "Hesabınız geçici olarak kilitlendi." | AC-4 |
| 5 | E-posta doğrulama happy path | 204 | Yok | "Doğrulandı" + /giris linki | AC-5 |
| 6 | Doğrulama/reset - geçersiz/süresi dolmuş token | 400/410 | Sayfa hata state'i | "Bağlantı geçersiz/süresi dolmuş" + yeniden başlatma linki | AC-6 |
| 7 | Şifre unuttum happy path (her koşulda) | 204 (her zaman) | Yok (numaralandırma önlemi) | Tek sabit mesaj | AC-7, AC-S2 |
| 8 | Şifre sıfırlama happy path | 204 | Oturum kurulmaz | "Şifren değişti" + /giris'e yönlendirme | AC-8 |
| 9 | Validasyon hatası | 422 | Alan bazlı hata state'i | Backend mesajı ilgili alan altında | AC-9 |
| 10 | Rate limit | 429 | Form geçici disable | "Çok fazla deneme" mesajı | AC-10, AC-S6 |
| 11 | Ağ hatası/timeout | - (fetch reddi) | Loading kapanır, buton tekrar aktif | "Bağlantı hatası" mesajı | AC-11 |
| 12 | Çift submit | UI seviyesinde engellenir | Tek pending state | Hiçbir şey (buton zaten disabled) | AC-12 |
| 13 | Kayıt - zaten kayıtlı email | 201 (backend farkı yansıtmaz) | Yok | Happy path ile AYNI mesaj | AC-S1 |

Kısmi başarı: Login'de 200 dönüp cookie tarayıcı tarafından reddedilirse (örn. 3rd-party cookie engeli) → kullanıcı yönlendirilir ama korumalı sayfada /me 401 alır → middleware onu tekrar /giris'e döndürür; sessiz sonsuz döngüye girmemesi test edilir (middleware zaten `next` ile tek seferlik yönlendirme yapıyor, döngü riski düşük ama gözlemlenmeli).
Hiçbir şey yapılamadı ama hata da yok: Bu görevde oluşmaz — her form submit'i ya bir HTTP yanıtı (2xx/4xx) ya da NetworkError fırlatır; apiFetch hiçbir zaman sessizce "hiçbir şey olmadı" dönmez (mevcut client.ts mimarisi).
Boş sonuç ↔ hata ayrımı: Şifre-unuttum'da "e-posta yok" ile "e-posta var" backend seviyesinde zaten ayrılmıyor (ikisi de 204) — bu KASITLI (numaralandırma önleme), frontend bu ayrımı asla yapmamalı (AC-S2).

## Test Strategy
Unit: 60% — form validasyon fonksiyonları (email format, password min-length, şifre eşleşme), hata kodu → mesaj eşleme, redirect hedefi üretimi (sabit route, open-redirect yok).
Integration: 40% — her sayfa component'i + mock apiFetch ile happy path + her hata kodu (401/423/422/429/400/410/network) senaryosu, çift-submit engeli, token'ın HTML'e ham basılmadığının kontrolü.
E2E: 0% — PLAN 1.12 ile tutarlı, bu pipelin'da e2e yok.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Form hata mesajları görünür ve `aria-live` ile duyurulur olmalı (PLAN 1.12'deki error-banner deseniyle tutarlı) — `verify` adımında gerekirse `vision-test` ile kontrol edilir.
Diğer ölçülebilir kriterler: `ruff`/`mypy` bu görevde N/A (frontend); `npm run lint && npm run typecheck` zorunlu.

## Kapsam Dışı
- "Beni hatırla" checkbox'ı
- Sosyal login (Google vb.)
- 2FA
- Captcha
- Backend endpoint değişikliği (register/login zaten var; verify-email/forgot-password/reset-password backend'de HENÜZ YOK — bkz. Riskler)
- E2E test senaryoları

## Etkilenen Dosyalar/Modüller (bilinen)
- Yeni: `frontend/app/kayit/page.tsx` + form component + test
- Değişen: `frontend/app/giris/page.tsx` (placeholder → gerçek form)
- Yeni: `frontend/app/e-posta-dogrula/page.tsx`
- Yeni: `frontend/app/sifre-unuttum/page.tsx`
- Yeni: `frontend/app/sifre-sifirla/page.tsx`
- Değişen: `frontend/lib/api/client.ts` — register/login/verifyEmail/forgotPassword/resetPassword fonksiyonları eklenir (mevcut apiFetch üstüne, breaking change yok)
- Değişen: `frontend/lib/auth/should-redirect.ts` — `isPublicRoute` allowlist'ine yeni sayfalar eklenir (AUTH mantığı değişikliği → **kod aşamasında kullanıcıdan açık onay istenecek**, CLAUDE.md kuralı)
- Değişen: `frontend/messages/tr.json` — yeni UI metinleri

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı: git reposunun kökü proje klasörüyle (`/Users/elifsarahan/Desktop/yetkin360`) aynı, devasa/harici bir geçmiş yok (bu oturumda `git log --oneline -5` ile kontrol edildi, repo küçük). Yine de sonraki adımlar aramayı proje klasörüyle sınırlı tutar.

## Rollback Beklentisi
Form içi hata state'i (401/422/423/429/400/410/network) formun kendi içinde gösterilir. Beklenmeyen render/JS hatası mevcut `app/error.tsx` error boundary'sine düşer — yeni bir error boundary icat edilmez.

## Risks
- **Backend eksik:** `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password` endpoint'leri backend/app'de henüz implemente edilmemiş (yalnız `RegisterRequest`/`LoginRequest` şemaları var, grep ile doğrulandı). Jira'nın kendi bağımlılık notu ("backend'in bitmesini beklemeden mock ile ilerlenir") bunu zaten öngörmüş — frontend docs/API.md sözleşmesine göre yazılır, testler `apiFetch`'i mock'lar (gerçek backend'e bağımlı değil). Backend bitince ek entegrasyon testi gerekmeyecek (sözleşme zaten sabit).
- `should-redirect.ts`'deki `isPublicRoute` değişikliği kimlik doğrulama mantığına dokunuyor — CLAUDE.md gereği kod yazılmadan önce kullanıcıdan açık onay alınacak.

## Assumptions
- Giriş sonrası varsayılan yönlendirme hedefi `/` (proje ana sayfası) — middleware.ts'de ayrı bir `/panel` gibi rota tanımlı değil, kod aşamasında teyit edilecek.
- Password min-length: register için 8 (backend/app/schemas/auth.py:18, grep ile doğrulandı); reset-password şeması backend'de henüz yok, aynı 8 kuralı varsayılır (API.md'de ayrı belirtilmemiş).

## Unknowns
- Backend `/auth/reset-password` implemente edildiğinde `new_password` alanının gerçek min-length kısıtı ne olacak (şu an varsayım: 8).

## Sorular ve Cevaplar (ham kayıt)
1-18: Sonnet 5 low alt-ajanı tarafından yanıtlandı (persona, happy path akışları, hata mesajları, test stratejisi, kapsam dışı, coverage, bağımlılıklar, rollback, kabul kriteri sahibi) — tam gerekçeler subagent raporunda, atdd.md'ye özetlenerek işlendi.
19 (threat-model, 5b adımı): Tetikleyici VAR (kimlik doğrulama + kullanıcı girdisi) → threat-model skill'i çağrıldı, AC-S1..AC-S6 üretildi ve yukarıdaki AC listesine gömüldü.
- middleware.ts, should-redirect.ts, backend/app/schemas/auth.py doğrudan bu oturumda okunarak (kullanıcı mesajından değil) doğrulandı: public route allowlist'in şu an sadece `/` ve `/giris` içerdiği, register/login şemalarının var ama verify/forgot/reset şemalarının backend'de henüz yazılmadığı.
