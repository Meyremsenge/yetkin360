---
task_slug: admin-link-rol-sizintisi
jira_id: YET-245
saga_task_id: null
threat_model: done
priority: high
coverage_target: 75
performance_target: null
memory_target: null
test_strategy:
  unit: 55
  integration: 35
  e2e: 10
affected_modules:
  - backend/app/api/me.py
  - frontend/lib/session/types.ts
  - frontend/lib/session/use-session.ts
  - frontend/components/app-shell.tsx
---

# ATDD — admin-link-rol-sizintisi

## Jira Kaynağı
[YET-245 — TASARIM-02: Navigasyon sayfa altında + admin linkleri herkese görünüyor (rol sızıntısı)](https://kuyusuzyusuf123.atlassian.net/browse/YET-245)

User Story (Jira'dan birebir): "Konum: frontend/components/app-shell.tsx:174-191. Sorun 1 (tasarım): 'Kurum Doğrulama', 'Yetkinlik Yönetimi', 'Çıkış' linkleri children bloğundan SONRA, border-t ile footer olarak render ediliyor — üstte olması beklenirdi. 'Çalışmalarım' ve 'Profil' için hiç nav linki yok. Sorun 2 (yetki/rol sızıntısı): Admin linkleri ('Kurum Doğrulama', 'Yetkinlik Yönetimi') rol kontrolü olmadan TÜM kullanıcılara (öğrenci dahil) gösteriliyor."

AC (Jira'dan birebir öneri): "AppShell'e üst bar (logo + Çalışmalarım/Profil linkleri + kullanıcı menüsü), admin linkleri yalnız admin/coordinator rolünde render edilsin."

## Persona
Platform admin (admin linklerinin yanlış gösterildiğini fark eder) ve öğrenci/talent kullanıcı (yanlışlıkla erişemeyeceği linkleri görür) — kurum temsilcisi/coordinator bu görevin kapsamı dışında. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Hedef (Neden)
Admin linklerinin yetkisiz kullanıcılara gösterilmesini önleyerek kötü UX'i gidermek ve savunma-derinliği ilkesi gereği frontend'i backend'in zaten uyguladığı yetki sınırıyla tutarlı hale getirmek. *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)* **Not:** Orkestratörün kod incelemesi, `backend/app/api/admin.py`'deki `_require_admin()`'in zaten `is_platform_admin` kontrolü yapıp yetkisiz istekte 404 döndürdüğünü doğruladı — bu GERÇEK bir yetki açığı değil, UI katmanında eksik bir ikinci savunma hattı.

## User Story
As a platformu kullanan herhangi bir kullanıcı
I want AppShell navigasyonunun rolümle tutarlı linkler göstermesini (admin linklerini yalnız gerçekten platform admin isem görmek)
So that arayüz erişemeyeceğim özellikleri bana göstermesin ve admin olduğumda tüm admin araçlarına üst bar üzerinden kolayca ulaşabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `GET /me` yanıtı `user.is_platform_admin: true` döner, When AppShell render edilir, Then üst bar'da logo + Çalışmalarım + Profil linkleri + "Kurum Doğrulama" + "Yetkinlik Yönetimi" linkleri + kullanıcı menüsünde Çıkış birlikte görünür.
2. [Critical] Given `GET /me` yanıtı `user.is_platform_admin: false` döner, When AppShell render edilir, Then render edilen DOM'da `messages.shell.adminVerificationQueueLink` ve `messages.shell.adminSkillsLink` metinleri HİÇ bulunmaz (sadece Çalışmalarım/Profil/Çıkış görünür).
3. [Critical] Given `GET /me` henüz `isPending` durumunda (loading), When AppShell render edilir, Then admin linkleri gösterilmez (fail-closed varsayılan) — veri gelene kadar belirsiz rolle link gösterilmez.
4. [High] Given `GET /me` yanıtında `user.is_platform_admin` alanı `null`/`undefined` (şema hatası, eski client cache, kısmi yanıt), When AppShell render edilir, Then admin linkleri GİZLENİR (fail-closed; `=== true` ile kesin eşitlik kontrolü, truthy/falsy belirsizliğine güvenilmez) — sessizce gizlenir, hata fırlatılmaz.
5. [High] Given herhangi bir oturum durumu, When AppShell render edilir, Then "Çalışmalarım" ve "Profil" linkleri üst bar'da (logo yanında/sonrasında) görünür, sayfa altındaki eski `border-t` footer bloğu kaldırılmıştır.
6. [Critical] **AC-S1 (güvenlik/regresyon):** Given bir kullanıcının `is_platform_admin: false` olduğu doğrulanmış bir oturumu var, When bu kullanıcı admin linkine hiç tıklamadan DOĞRUDAN `GET /admin/dogrulama-kuyrugu` veya `GET /admin/skiller` backend ucuna istek atar, Then backend yine 404 döner (bu görev `_require_admin()`'in mevcut davranışını DEĞİŞTİRMEZ — frontend değişikliği sunucu tarafı korumanın YERİNE geçmez, ona EK bir UX katmanıdır).
7. [Medium] **AC-S2 (bilgi ifşası minimizasyonu):** Given `GET /me` yanıtı üretiliyor, When response serialize edilir, Then yanıt SADECE `is_platform_admin` alanını ekler — `institution_admin_ids`, `org_admin_ids`, `supervisor_institution_ids` gibi başka hiçbir ek rol/yetki alanı `GetMeResponse`'a eklenmez (bu görevin kapsamı platform-admin bayrağıyla sınırlı).

## Threat Model
Çağrıldı — AC-S1 ve AC-S2 kriterleri yukarıdaki Acceptance Criteria'ya eklendi. STRIDE-lite özeti: **Elevation of Privilege** en kritik kategori olarak değerlendirildi (frontend linkini gizlemek gerçek yetki sınırı değil, backend'in zaten doğru çalıştığının regresyon testiyle korunması AC-S1'i doğurdu); **Information Disclosure** ikinci kategori oldu (AC-S2, yeni response alanının kapsamını sınırlıyor). Spoofing/Tampering/DoS/Repudiation bu değişiklikle ilgisiz bulunup atlandı (auth mekanizmasına, istemciden gelen veriye, sınırsız kaynağa veya loglamaya dokunmuyor).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Render edilen durum | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — platform admin | Üst bar: logo + Çalışmalarım + Profil + Kurum Doğrulama + Yetkinlik Yönetimi + Çıkış | Yok | Tüm linkler üstte, admin linkleri dahil | AC-1 |
| 2 | Happy path — admin DEĞİL (`false`) | Üst bar: logo + Çalışmalarım + Profil + Çıkış; admin linkleri DOM'da yok | Yok | Admin linkleri hiç görünmez | AC-2 |
| 3 | `GET /me` loading/pending | Üst bar: logo + Çalışmalarım + Profil + Çıkış; admin linkleri gösterilmez (fail-closed) | Yok | Admin linkleri loading sırasında yok, veri gelince admin ise belirir | AC-3 |
| 4 | `is_platform_admin` null/undefined (şema hatası) | Admin linkleri gösterilmez (fail-closed, `=== true` kontrolü) | Yok (sessiz gizleme, hata fırlatılmaz) | Admin linkleri görünmez, diğer nav normal | AC-4 |
| 5 | Nav üst bar yerleşimi | Çalışmalarım/Profil linkleri üst bar'da; eski `border-t` footer kaldırıldı | Yok | Nav artık sayfa altında değil üstte | AC-5 |
| 6 | Doğrudan URL ile admin ucuna erişim (admin olmayan) | Backend 404 (`_require_admin()` değişmedi) | Yok | "Kaynak bulunamadı" (zaten mevcut davranış) | AC-S1 |

Kısmi başarı: Bu görevde "kısmi başarı" senaryosu yok — ya `is_platform_admin` alanı doğru eklenip doğru render edilir, ya da hiçbiri. Satır 3/4 (loading/null) zaten "belirsizlikte gösterme" kuralını kapsıyor.
Hiçbir şey yapılamadı ama hata da yok: Satır 3/4 ile aynı — admin linkleri render edilmez ama sayfa çökmez, hata fırlatılmaz. Bu kasıtlı (fail-closed), sessiz başarı DEĞİL çünkü render edilen sonuç (gizli link) doğru/beklenen durumdur.
Boş sonuç ↔ hata ayrımı: N/A — bu görev bir liste/arama sonucu döndürmüyor, bir render kararı veriyor.

## Test Strategy
Unit: 55% — `GetMeResponse` şemasının `is_platform_admin` alanını doğru serialize ettiğini doğrulayan backend testi + `AppShell` component'inin `is_platform_admin: true/false/null/undefined/loading` senaryolarında doğru linkleri render ettiğini doğrulayan frontend testleri.
Integration: 35% — `GET /me` endpoint'inin gerçek bir admin ve gerçek bir admin-olmayan principal ile uçtan uca doğru alanı döndürdüğünü doğrulayan backend integration testi; AC-S1 için `tests/authorization`'da zaten var olan (veya eklenecek) admin-endpoint negatif testinin bu görevle BOZULMADIĞINI doğrulayan regresyon testi.
E2E: 10% — nav yerleşimi değiştiği için `vision-test` ile üst bar görsel doğrulaması (desktop/mobile).

## Benchmark / Başarı Ölçütü
Coverage Target: 75%
Performance Target: yok (tek bool alan eklemek, ek sorgu/JOIN gerektirmiyor)
Memory: yok
Görsel/UI kriteri: Admin linkleri artık `border-t` footer bloğunda değil, üst bar'da. Bu kriter `verify` adımında `vision-test` skill'iyle kontrol edilecek.
Diğer ölçülebilir kriterler: `is_platform_admin: false` olan bir render çıktısında `adminVerificationQueueLink`/`adminSkillsLink` metinlerinin DOM'da sıfır kez geçmesi (component testiyle tam sayım).

## Kapsam Dışı
Coordinator/supervisor'a özel ayrı bir nav bölümü (admin linkleri SADECE `is_platform_admin`'e bağlı, coordinator ayrımı bu görevde YOK — admin.py'de zaten tek kontrol bu). Yeni bir tasarım sistemi/Card-Badge bileşeni icat edilmez (bu YET-247'nin kapsamı). Genel layout/sayfa düzeni değişikliği yapılmaz (sadece AppShell nav). *(Sonnet 5 low alt-ajanı tarafından yanıtlandı.)*

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/me.py` — `UserResponse`/`GetMeResponse` şemasına `is_platform_admin: bool` eklenecek, `get_me()` içinde `principal.is_platform_admin` değeri response'a geçirilecek.
- `frontend/lib/session/types.ts` — `MeResponse.user` arayüzüne `is_platform_admin?: boolean` eklenecek (opsiyonel, zorunlu alan değil — `isMeResponse` guard'ı değişmeyebilir, `plan` adımında netleşir).
- `frontend/lib/session/use-session.ts` — tip değişikliği varsa burada da yansıması kontrol edilecek (muhtemelen değişmez, sadece tip akışı).
- `frontend/components/app-shell.tsx` — nav yeniden düzenleme (üst bar), admin linklerinin `session.data?.user.is_platform_admin === true` koşuluna bağlanması.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup olmadığı kontrol edilmedi. Sonraki adımlarda arama `backend/`ve `frontend/` klasörleriyle sınırlı tutulmalı.

## Rollback Beklentisi
Migration GEREKMİYOR — `is_platform_admin` kolonu zaten var (`users` tablosu, `85ce30db9b84_add_is_platform_admin_to_users` migration'ı ile önceden eklenmiş), bu görev sadece response şeması ve frontend tip/render değişikliği yapıyor. Bir regresyon bulunursa `git revert` ile geri alınır.

## Risks
- Session cache/staleness: Bir kullanıcının admin yetkisi backend'de aniden kaldırılırsa, frontend TanStack Query refetch'e kadar bir süre eski admin linkini gösterebilir. **Kabul edilen risk** — bu görevde ele alınmıyor çünkü (a) gerçek yetki her zaman backend'de yeniden kontrol ediliyor (AC-S1), UI gecikmesi sadece görünürlük, (b) mevcut session yönetimi davranışı bu görevin kapsamı dışında bir konu, MVP'de kabul edilebilir.

## Assumptions
- `frontend/lib/session/use-session.ts`'in `MeResponse` tipini genişletmenin, mevcut `isMeResponse` type guard'ını bozmayacağı varsayıldı (`is_platform_admin` opsiyonel alan olarak ekleniyor) — `plan` adımında doğrulanmalı.
- Admin linklerinin yalnızca `is_platform_admin`'e bağlı olduğu (coordinator/supervisor rolünün bu iki admin ucuyla hiç ilgisi olmadığı) `backend/app/api/admin.py`'deki `_require_admin()` fonksiyonunun tek kontrolü okunarak doğrulandı — varsayım değil, kod incelemesiyle kanıtlandı.

## Unknowns
- Üst bar'ın tam görsel tasarımı (logo neyle gösterilecek, kullanıcı menüsü dropdown mu yoksa düz buton mu) — Jira sadece "logo + linkler + kullanıcı menüsü" diyor, YET-247'nin (tasarım sistemi) henüz uygulanmadığı göz önüne alınırsa mevcut class'larla (Tailwind utility, Card/Badge icat etmeden) minimal bir üst bar yapılacak; `plan` adımında netleşecek.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Platform admin + öğrenci/talent, coordinator kapsam dışı (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Ana hedef/neden → Kötü UX'i gidermek + savunma-derinliği, gerçek authz açığı değil (Sonnet 5 low alt-ajanı tarafından yanıtlandı; orkestratör kod incelemesiyle doğruladı: `admin.py:_require_admin()` zaten 404 dönüyor).
3. Happy path → admin: tüm linkler üstte; admin değil: admin linkleri yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
4. Edge case'ler → loading'de gizli, null/undefined'da fail-closed gizli (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör AC-S1 satırıyla genişletti).
6. Başarı ölçütü → DOM'da admin link metni sıfır kez (false/null/loading'de) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → coordinator ayrımı yok, YET-247 icat edilmez, genel layout değişmez (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. Bağımlılıklar → me.py, types.ts, use-session.ts, app-shell.tsx (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör kod okuyarak doğruladı).
9. Performans/güvenlik → performans etkisi yok, PII değil (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
10. Rollback → migration gerekmiyor, kolon zaten var (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör migration dosyasını (`85ce30db9b84`) bularak doğruladı).
11. Kabul kriteri sahibi → kullanıcı onayı + otomatik test + vision-test (nav yerleşimi değiştiği için) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
12. Test stratejisi → unit 55 / integration 35 / e2e-vision 10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
13. Görev slug'ı → `admin-link-rol-sizintisi` (kullanıcı onayı, AskUserQuestion).
14. Threat-model → çağrıldı, AC-S1 (backend 404 regresyonu) ve AC-S2 (fazla rol alanı dönmemeli) eklendi (orkestratör, STRIDE-lite analiziyle).
