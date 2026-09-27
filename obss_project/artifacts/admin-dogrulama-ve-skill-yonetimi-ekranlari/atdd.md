---
task_slug: admin-dogrulama-ve-skill-yonetimi-ekranlari
jira_id: YET-114
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 30
  e2e: 0
affected_modules:
  - frontend/app/admin/dogrulama-kuyrugu/page.tsx (yeni)
  - frontend/app/admin/skiller/page.tsx (yeni)
  - frontend/lib/api/admin.ts (yeni)
  - frontend/components/app-shell.tsx (admin nav linki)
  - frontend/messages/tr.json (yeni metin anahtarları)
---

# ATDD — admin-dogrulama-ve-skill-yonetimi-ekranlari

## Jira Kaynağı
[YET-114 — [PLAN 3.10] Frontend: kurum dashboard + admin ekranları](https://kuyusuzyusuf123.atlassian.net/browse/YET-114)
Proje: YETKIN360 (YET), tip: Görev, öncelik: Medium, atanan: Meyrsem, durum: Yapılacaklar.
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.10.\nSahip: @fe"
User Story / AC: Jira'da yok — sadece PLAN.md madde referansı var.

PLAN.md madde 3.10: "Frontend: kurum dashboard + admin ekranları @fe"

**Kod tabanı taraması sonucu kapsam daraltması:** "Kurum dashboard" kısmı
PLAN 3.5 (üye listesi, commit `8881008`) ve PLAN 3.9 (koordinatör dashboard,
[frontend/app/kurum/[id]/panel/page.tsx](frontend/app/kurum/[id]/panel/page.tsx))
ile zaten tamamlanmış durumda. Bu görevin net kalan gövdesi PLAN 3.6'da
(commit `15b157b`) backend'i biten ama hiç frontend'i olmayan **admin
ekranları**: kurum doğrulama kuyruğu + skill taksonomi yönetimi
([backend/app/api/admin.py](backend/app/api/admin.py)).

## Persona
Platform admin — `users.is_platform_admin = true` olan kurucu ekip üyesi.
Başka rol bu ekranlara erişemez (backend zaten 404 ile kapatıyor).

## Hedef (Neden)
Bugün kurum doğrulama seviyesi değiştirme ve skill taksonomi yönetimi
(oluşturma/güncelleme/deprecate/merge) yalnızca doğrudan API çağrısıyla
(Postman/curl) yapılabiliyor — backend PLAN 3.6'da bitti ama arayüzü yok.
Bu görev kurucu ekibin bu işlemleri tarayıcıdan yapabilmesini sağlıyor.

## User Story
As a platform admin (is_platform_admin=true)
I want kurum doğrulama kuyruğunu görüp seviye güncelleyebilmek ve skill
taksonomisini (oluştur/güncelle/deprecate/merge) yönetebilmek
So that bu işlemler için artık API istemcisine (Postman/curl) ihtiyaç duymam

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given admin `/admin/dogrulama-kuyrugu` sayfasına girer, When `GET /admin/verification-queue` 200 + dolu `items[]` döner, Then tabloda her kurum satırı (name, legal_id, domain, verification_level, created_at) listelenir.
2. [Critical] Given admin bir kurum satırında yeni seviye seçip onaylar, When `POST /admin/organizations/{id}/verification-level` 200 + güncel `OrganizationSummary` döner, Then satır güncellenir ve "Doğrulama seviyesi güncellendi" başarı bildirimi gösterilir.
3. [Critical] Given `is_platform_admin=false` bir kullanıcı `/admin/dogrulama-kuyrugu` sayfasına girer, When `GET /admin/verification-queue` 404 döner, Then genel "sayfa bulunamadı" ekranı gösterilir — "yetkin yok" gibi admin sayfasının varlığını doğrulayan bir mesaj gösterilmez. (AC-S1)
4. [High] Given `GET /admin/verification-queue` 200 + `items: []` döner, Then boş-durum mesajı ("Bekleyen doğrulama isteği yok") gösterilir — boş beyaz ekran değil.
5. [High] Given admin `/admin/skiller` sayfasında yeni skill oluşturur, When `POST /admin/skills` 201 döner, Then yeni skill listeye eklenir ve form temizlenir.
6. [High] Given admin var olan bir slug ile skill oluşturmaya çalışır, When `POST /admin/skills` 409 CONFLICT döner, Then form alanı altında "Bu slug zaten kullanımda" satır-içi hatası gösterilir, sayfa yeniden yüklenmez.
7. [Medium] Given admin bir skill'i deprecate/merge eder, When ilgili endpoint 200 döner, Then skill listesinde durumu ("DEPRECATED" / "MERGED → hedef") güncellenir.
8. [Medium] Given herhangi bir admin action sırasında API 500/network hatası döner, Then kırmızı hata bildirimi gösterilir ve önceki liste durumu korunur (optimistic update yok).
9. [Critical] Given `is_platform_admin=false` bir kullanıcı `/admin/organizations/{id}/verification-level`, `/admin/skills`, `/admin/skills/{id}`, `/admin/skills/{id}/deprecate`, `/admin/skills/{id}/merge` uçlarından herhangi birine istek atar (var olan veya olmayan bir id ile), Then hepsinde 404 döner ve var/yok id'ler için yanıt ayırt edilemez — kaynağın varlığı sızdırılmaz. (AC-S2)

## Threat Model
Çağrıldı — tetikleyici: yetkilendirme sınırı (`is_platform_admin`) + admin/kurum
verisi ifşası riski. STRIDE-lite: Elevation (yetki sadece backend'de
kontrol ediliyor, frontend'de tekrarlanmayacak — doğru), Info disclosure
(404'ün var/yok ayrımı sızdırmaması) öne çıktı; Spoofing/Tampering/
Repudiation/DoS bu görevde mevcut auth/audit-log altyapısıyla zaten
kapatılıyor (admin.py her action'ı `log_audit_event`'e yazıyor) — ek AC
gerekmedi. AC-S1/AC-S2 yukarıdaki Acceptance Criteria'ya eklendi.

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — bu görev bir LLM agent/tool-calling davranışını değiştirmiyor, silindi.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (kuyruk dolu, seviye güncelleme) | `POST .../verification-level` → `200 {"id":"...","name":"...","verification_level":"T3","verified_at":"2026-09-27T10:00:00Z"}` | `organizations.verification_level` UPDATE edilir (append-only değil, mevcut satır güncellenir), `audit_events`'e `ADMIN_SET_VERIFICATION_LEVEL` yazılır | Satır güncellenir, yeşil bildirim "Doğrulama seviyesi güncellendi" | AC-2 |
| 2 | Girdi geçersiz/eksik (enum dışı `verification_level`) | `422 {"detail":[{"loc":["body","verification_level"],"msg":"..."}]}` | Yok | Form zaten `<select>` ile enum'a kısıtlı — pratikte oluşmaz, oluşursa alan altı hata | — |
| 3 | Kaynak yok (`organization_id` silinmiş/yanlış) | `404 {"code":"NOT_FOUND","message":"Kurum bulunamadı."}` | Yok | "Kurum bulunamadı" hata bildirimi, kullanıcı listeye geri döner | — |
| 4 | Yetkisiz erişim (`is_platform_admin=false`) | Tüm `/admin/*` uçları → `404 {"code":"NOT_FOUND","message":"Kaynak bulunamadı."}` | Yok | Genel "sayfa bulunamadı" ekranı — admin panelinin varlığı sızdırılmaz | AC-3, AC-S1, AC-S2 |
| 5 | Dış bağımlılık hatası (API 500/network) | `500` veya `NetworkError` | Yok | Kırmızı bildirim "Bir hata oluştu, tekrar deneyin", önceki liste durumu korunur | AC-8 |
| 6 | Zaman aşımı | `fetch` `AbortError`/timeout | Yok | Aynı genel hata bildirimiyle birleştirilir ("İstek zaman aşımına uğradı, tekrar deneyin") | AC-8 |
| 7 | **Kısmi başarı** | — silindi | Her admin action'ı (`verification-level`, `create/update/deprecate/merge skill`) tek bir kaynağı tek bir transaction'da değiştiren atomik bir endpoint; iki ayrı yazma adımı içeren bir akış bu görevde yok, dolayısıyla kısmi başarı senaryosu oluşmaz | — | — |
| 8 | **Hiçbir şey yapılamadı ama hata yok** (boş kuyruk) | `200 {"items":[]}` | Yok | Boş-durum UI'ı: "Bekleyen doğrulama isteği yok" mesajı + ikon — sessiz beyaz ekran değil | AC-4 |

Boş sonuç ↔ hata ayrımı: `200 {"items":[]}` "kuyrukta bekleyen kurum yok"
anlamına gelir (AC-4, boş-durum UI'ı gösterilir); `404` ise ya kaynak yok ya
da kullanıcı yetkisiz (AC-3/AC-S1/AC-S2, genel 404 ekranı gösterilir) — ikisi
asla aynı ekranla karışmaz çünkü farklı HTTP durum kodları döner.

**Nullable alan kararları (backend Pydantic şemasında `Optional`):**
| Alan | null ise UI'da ne gösterilir |
|---|---|
| `legal_id` | "-" |
| `domain` | "-" |
| `verified_at` | "-" (henüz doğrulanmamış/kuyrukta anlamına gelir) |
| `name_en` | Gösterilmez, `name_tr` fallback olarak kullanılır (UI dili zaten TR) |
| `parent_id` | "Kök seviye" etiketi (null burada anlamlı bir durumu — üst kategori yok — ifade eder, "-" değil) |
| `merged_into_id` | Skill `status != "MERGED"` ise sütun boş bırakılır (alan alakasız); `"MERGED"` ise `merged_into_id` her zaman dolu olmalı (backend garantisi), null gelirse bu bir backend hatasıdır — "beklenmeyen veri" uyarısı loglanır, UI'da "-" gösterilir |

## Test Strategy
Unit: 70% — `lib/api/admin.ts` fonksiyonları (institutions.ts/evaluation.ts
kalıbı), sayfa bileşenlerinin loading/error/success/empty state render'ları.
Integration: 30% — sayfa + TanStack Query + mock fetch ile tam akış (liste →
aksiyon → optimistic-olmayan güncelleme), 404 route-guard testi (AC-3/AC-S1).
E2E: 0% — mevcut proje konvansiyonunda e2e yok (bkz. kurum panel testleri),
MVP/hackathon kapsamında eklenmiyor.

## Benchmark / Başarı Ölçütü
Coverage Target: 80% (proje genel konvansiyonu; ayrı sayısal hedef Jira'da
belirtilmemiş, mevcut sayfa testlerinin (`page.test.tsx`) kapsamıyla aynı
seviye varsayıldı — **varsayım**).
Performance Target: yok (hackathon/MVP bağlamında ölçülmüyor — **varsayım**).
Memory: yok.
Görsel/UI kriteri: Boş durum tasarlanmadan ekran bitmiş sayılmaz (.claude/rules/frontend.md) — AC-4 ve boş skill listesi için de aynı kural uygulanır. Kontrast 4.5:1, tüm form alanlarında `<label>`, hata mesajları `aria-live` (mevcut ErrorBanner bileşeni bunu zaten sağlıyor).
Diğer: Rol kontrolü yalnız UX amaçlıdır — admin nav linki görünürlüğü güvenlik sınırı değildir (.claude/rules/frontend.md).

## Kapsam Dışı
- `is_platform_admin` rolünün kime, nasıl atandığı (admin kullanıcı yönetimi/rol atama UI'ı) — bu görevde YOK, Jira'da da yok, CLAUDE.md MVP kısıtına da aykırı olurdu (yeni bir yetkilendirme akışı).
- `GET /me` response'una `is_platform_admin` alanı eklenmesi — CLAUDE.md'nin "yetkilendirme/kimlik doğrulama mantığı değişikliği önce açık onay" kuralına giriyor, bu ATDD kapsamında **yapılmayacak**. Sonucu: admin nav linki bu sürümde **herkese görünür** bırakılır, güvenlik backend'in 404'üne bırakılır (bkz. Risks).
- Skill ağacının görsel (tree/graph) gösterimi — düz liste + `parent_id` sütunu yeterli, MVP.
- Toplu (bulk) doğrulama onayı/skill import — Jira'da yok, MVP dışı.
- Audit log görüntüleme ekranı — `admin.py` zaten her action'ı loglar ama bunu okuyan bir UI bu görevde yok.

## Etkilenen Dosyalar/Modüller (bilinen)
- `frontend/lib/api/admin.ts` (yeni) — `institutions.ts` kalıbını izler.
- `frontend/app/admin/dogrulama-kuyrugu/page.tsx` (yeni)
- `frontend/app/admin/skiller/page.tsx` (yeni)
- `frontend/components/app-shell.tsx` — admin nav linki eklenir (herkese görünür, bkz. Risks).
- `frontend/messages/tr.json` — yeni metin anahtarları (`adminVerificationQueue.*`, `adminSkills.*`).
- Backend'de değişiklik YOK — `backend/app/api/admin.py` zaten tam.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup
olmadığı ayrıca kontrol edilmedi. Sonraki adımlarda arama proje klasörüyle
(`yetkin360/`) sınırlanmalı, sınırsız `grep -r`/`git log -p --all` çalıştırılmamalı.

## Rollback Beklentisi
Bir admin action'ı (verification-level güncelleme, skill create/update/
deprecate/merge) başarısız olursa optimistic update yapılmaz — TanStack Query
mutation hata durumunda listeyi eski haliyle bırakır, kırmızı hata bildirimi
gösterilir, kullanıcı formu/aksiyonu tekrar deneyebilir. Sunucu tarafında
zaten append-only olmayan `organizations`/`skills` tabloları normal UPDATE
kullanıyor, ek bir rollback mekanizması (ör. compensating transaction)
gerekmiyor.

## Risks
- **Kabul edilen risk:** Admin nav linki `is_platform_admin` bilgisi `/me`'de
  olmadığı için tüm kullanıcılara görünür olacak — bu, "platformda bir admin
  paneli var" bilgisini sızdırır (düşük önem, kurum/kullanıcı verisi
  sızdırmaz çünkü tıklayınca 404 alınır). Gerekçe: `/me`'ye alan eklemek
  CLAUDE.md'ye göre yetkilendirme mantığı değişikliği sayılır ve ayrı açık
  onay gerektirir; bu ATDD'de kapsam dışı bırakıldı, ayrı bir görev/onay
  olarak öneriliyor.
- Jira YET-114'ün atananı "Meyrsem" — bu görevi başka bir ekip üyesi
  üstlenmiş olabilir; kullanıcıya (yusuf21cinar21@gmail.com) bu çakışmayı
  hard-stop'ta ayrıca belirtiyorum.

## Assumptions
- Coverage target %80 ve performans hedefi yok — Jira'da/PLAN.md'de
  belirtilmediği için proje genel konvansiyonundan varsayıldı, kullanıcı
  onayı bekliyor.
- Test stratejisi oranı (70/20/10 yerine 70/30/0, e2e yok) — mevcut frontend
  test kalıbından (page.test.tsx + lib/api/*.test.ts, e2e altyapısı yok)
  çıkarıldı, kullanıcı onayı bekliyor.
- Route isimleri (`/admin/dogrulama-kuyrugu`, `/admin/skiller`) Türkçe URL
  konvansiyonuna (`/kurum`, `/calismalar`, `/giris`) uyacak şekilde seçildi —
  Jira'da route adı belirtilmediği için varsayım.

## Unknowns
- `/me`'ye `is_platform_admin` eklenip eklenmeyeceği (ayrı onay gerektiren
  alt-görev olarak mı ele alınacak, yoksa bu ATDD'ye mi dahil edilecek) —
  kullanıcı onayı olmadan karar verilmedi.
- Jira'daki atanan kişi (Meyrsem) ile bu oturumu başlatan kullanıcı arasındaki
  ilişki netleşmedi.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Platform admin (`is_platform_admin=true`). (Sonnet 5 low alt-ajanı tarafından yanıtlandı: backend zaten bu role kilitli, başka rol yok.)
2. Ana hedef → Bugün admin işlemleri Postman/curl ile yapılıyor, bu görev UI sağlıyor. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: API zaten var, eksik olan arayüz.)
3. Happy path → Kuyruk sayfası → seviye güncelle → 200 → satır güncellenir + bildirim. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
4. Edge case'ler → boş kuyruk, admin olmayan kullanıcı 404 görür, skill slug çakışması 409. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
5. Nullable alan ilkesi → "-" göster, gizleme (parent_id ve name_en için istisna). (Sonnet 5 low alt-ajanı tarafından yanıtlandı, ben alan bazlı tabloyu netleştirdim.)
6. Başarı ölçütü → Hackathon bağlamında sayısal performans hedefi yok, coverage proje konvansiyonu. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — varsayım olarak işaretlendi, onay bekliyor.)
7. Kapsam dışı → is_platform_admin rol atama UI'ı yok. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
8. Bağımlılıklar → `/me`'ye alan eklemek bu ATDD kapsamı DIŞINDA, ayrı onay gerektiren alt-görev. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — kullanıcı onayı bekliyor, bkz. Unknowns.)
9. Güvenlik kısıtı → Rol kontrolü yalnız UX, backend zaten 404 ile koruyor. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
10. Rollback → Optimistic update yok, hata durumunda eski liste korunur. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
11. Kabul kriteri sahibi → Otomatik test yeşili + kullanıcı review'i (ATDD Hard Stop). (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
12. Test stratejisi → 70/30/0 (unit/integration/e2e), component ağırlıklı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — onay bekliyor.)
