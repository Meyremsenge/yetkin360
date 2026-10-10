---
task_slug: admin-kullanici-kurulus-kurum-yonetimi
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: "admin liste uçları <300ms (limit=200)"
memory_target: null
test_strategy:
  unit: 60
  integration: 30
  e2e: 10
affected_modules:
  - backend/app/api/admin_directory.py (yeni)
  - backend/app/services/admin_directory.py (yeni)
  - backend/app/main.py (router kaydı)
  - backend/tests/authorization/test_admin_directory_authz.py (yeni)
  - backend/tests/authorization/test_admin_router_gate.py (ikinci gated router)
  - frontend/lib/api/admin-directory.ts (+ test, yeni)
  - frontend/app/admin/{kullanicilar,kuruluslar,kurumlar}/page.tsx (yeni)
  - frontend/components/admin/* (yeni)
  - frontend/components/app-shell.tsx, frontend/messages/tr.json
  - docs/API.md, docs/AUTHORIZATION.md
---

# ATDD — admin-kullanici-kurulus-kurum-yonetimi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Şemsiye: `obss_project/artifacts/admin-eksikler-envanteri/atdd.md`
(kalemler U1, U2, O1, O4, I1). Saga MCP bu oturumda yok → `saga_task_id: null`.

## Persona
Platform admini (`users.is_platform_admin = true`).

## Hedef (Neden)
Admin bugün kullanıcı/kuruluş/kurum listesini göremiyor ve bir hesabı yalnız elle SQL ile askıya
alabiliyor. Bu paket listeleme + askıya alma/geri açma + kurum doğrulama seviyesini panelden yaptırır.

## User Story
As a platform admini
I want kullanıcıları, kuruluşları ve kurumları arayıp listelemek, askıya almak/geri açmak
So that kötüye kullanan bir hesabı SQL'e inmeden, iz bırakarak durdurabileyim.

## Uçlar
| Kalem | Uç |
|---|---|
| U1 | `GET /admin/users?q&status&limit&offset` |
| U2 | `POST /admin/users/{id}/suspend`, `POST /admin/users/{id}/reactivate` |
| O1 | `GET /admin/organizations?q&verification_level&status&limit&offset` |
| O4 | `POST /admin/organizations/{id}/suspend`, `/reactivate` |
| I1 | `GET /admin/institutions?q&limit&offset`, `POST /admin/institutions/{id}/verification-level`, `POST /admin/institutions/{id}/suspend`, `/reactivate` |

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. **AC-12 [High]** Given platform admini, When `GET /admin/users|organizations|institutions?limit=50&offset=0`,
   Then `200` + `{"items":[…],"limit":50,"offset":0,"has_more":false}`; `has_more` limit+1 satır çekilerek
   hesaplanır, ek satır yanıtta yer almaz. `limit=0|201`, `offset=-1` → `422 VALIDATION_ERROR`.
   Admin olmayan (talent, org ADMIN'i, kurum koordinatörü) → `404 NOT_FOUND`; oturumsuz → `401`;
   askıdaki eski admin → `401`. Hata gövdesinde `items/has_more/limit/offset` yoktur.
2. **AC-10 [High]** Given admin, When `POST /admin/users/{id}/suspend`:
   var olmayan id veya `DELETED` kullanıcı → `404`; zaten `SUSPENDED` → `200` + değişmemiş gövde, yeni audit yok;
   hedef = kendi hesabı veya son aktif platform admini → `409 LAST_ADMIN_PROTECTED`;
   iki adminden biri diğerini askıya alır → `200`, `status: SUSPENDED`. `reactivate` simetriktir
   (`SUSPENDED` → `ACTIVE`; askıda değilse `200` idempotent, audit yok). Aynı kurallar (son-admin hariç)
   kuruluş ve kurum askıya alma uçlarında geçerlidir.
3. **AC-11 [High]** Given askıya alma, When audit yazımı hata verir, Then durum değişikliği de geri alınır
   (tek transaction, erken commit yok). Test doğrudan tetikler: `log_audit_event` hata fırlatacak şekilde yamalanır.
4. **AC-I1 [High]** Given admin, When `POST /admin/institutions/{id}/verification-level {"verification_level":"T3"}`,
   Then `200` + güncel kurum; geçersiz seviye → `422`; yok → `404`; aynı seviye → `200`, audit yok.
5. **AC-UI [Medium]** Üç ekranın her birinde: arama, Önceki/Sonraki sayfalama, askıya al/geri aç için onay
   diyaloğu, yükleniyor / boş (ne yapılacağını söyleyen) / hata (`role="alert"` + "Tekrar dene") durumları;
   null alanlar "—" olarak render edilir (`new Date(null)` yok).

Güvenlik (şemsiyeden taşındı, threat-model yeniden çalıştırılmadı):
- **AC-S6 [Critical]** Hedef `id` yalnız path'ten, aktör yalnız oturumdan; body'de
  `actor_id`/`is_platform_admin`/`status` gönderilse yok sayılır. Askıya alınan kullanıcının access
  token'ı (`get_current_user`) ve refresh token'ı bir sonraki istekte `401` alır; refresh token'lar ayrıca
  iptal edilir (geri açılınca eski oturum dirilmez).
- **AC-S7 [High]** Her askıya alma/geri açma/seviye değişikliği `audit_events`'e `actor_user_id`,
  `subject_id`, `action` ile yazılır; serbest metin ve tam e-posta yazılmaz.
- **AC-S8 [High]** `GET /admin/users` öğesi yalnız `id,email,status,is_platform_admin,email_verified,created_at`
  taşır; `password_hash`, token, `failed_login_count`, `locked_until` yoktur. `q` loglanmaz.

## Threat Model
Çağrıldı (şemsiye görevde) — AC-S6…AC-S8 buraya taşındı; orkestratör talimatıyla yeniden çalıştırılmadı.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Liste, happy path | `200 {"items":[{"id":"…","email":"a@b.com","status":"ACTIVE","is_platform_admin":false,"email_verified":true,"created_at":"…"}],"limit":50,"offset":0,"has_more":false}` | Yok | Tablo + sayfalama | AC-12 |
| 2 | `limit=0/201`, `offset=-1`, geçersiz `status`/`verification_level` | `422 {"code":"VALIDATION_ERROR","message":"Girdi doğrulanamadı.","fields":{…},"request_id":"…"}` | Yok | (frontend geçerli değer yollar) | AC-12 |
| 3 | Tekil kaynak yok / `DELETED` | `404 {"code":"NOT_FOUND","message":"Kaynak bulunamadı.","request_id":"…"}` | Yok, audit yok | "Kayıt bulunamadı" | AC-10 |
| 4 | Admin olmayan / oturumsuz / askıdaki | `404 NOT_FOUND` · `401` · `401` | Yok | Sayfa yok | AC-12 |
| 5 | Askıya al, happy path | `200 {"id":"…","email":"…","status":"SUSPENDED",…}` (liste öğesiyle aynı şema) | durum + refresh token iptali + audit, tek transaction | "Askıya alındı" | AC-10, AC-S6, AC-S7 |
| 7 | Kısmi başarı: durum yazıldı, audit hata verdi | `500 {"code":"INTERNAL_ERROR",…}` | Hepsi geri alınır | "İşlem tamamlanamadı" | AC-11 |
| 8 | Hiçbir şey yapılmadı ama hata yok | Zaten askıda: `200` + `status: SUSPENDED`, audit satırı sayısı değişmez · boş liste: `200 {"items":[],"limit":50,"offset":0,"has_more":false}` | Yok | Satır değişmez / boş durum metni | AC-10, AC-12 |
| 9 | Kombinasyon: admin kendini / son aktif admini askıya alır | `409 {"code":"LAST_ADMIN_PROTECTED","message":"…","request_id":"…"}` | Yok | Uyarı | AC-10 |

Hata gövdesi projedeki gerçek sözleşmeyle düzdür (`{code,message,request_id}` — `core/errors.py`); şemsiyedeki
`{"error":{…}}` sarmalı koddaki sözleşmeyle uyuşmadığı için düz biçim kullanıldı.
Satır 5/6 (DB hatası, zaman aşımı): mevcut genel işleyiciler (`unhandled_exception_handler`, frontend
`NetworkError`) — bu pakete özgü davranış yok; yazma zaman aşımında liste yenilenir, körü körüne tekrarlanmaz.
Kısmi başarı: servis `commit` çağırmaz; tek commit `get_session` sonundadır.
Boş sonuç ↔ hata: admin için boş liste `200 + items: []`; `404` yalnız yetki yokluğu veya tekil kaynak yokluğu.
Nullable alanlar: kuruluş `legal_id`, `domain` → "—"; `verified_at` null → "Doğrulanmadı"; kurum `domain` → "—".

## Test Strategy
Unit 60% — servis (sayfalama, has_more, idempotency, son-admin), frontend API client.
Integration 30% — rol × uç matrisi + kombinasyonlar (`tests/authorization`), sayfa testleri.
E2E 10% — bu pakette yazılmadı (Faz dışı; elle doğrulama).

## Benchmark / Başarı Ölçütü
Her yeni uç için ≥1 pozitif + rol matrisi negatif test; `pytest tests/authorization -q` yeşil;
ruff + mypy + eslint + tsc temiz.

## Kapsam Dışı
Migration (CHECK ekleme dahil) · `admin.py` / `admin.ts` / mevcut admin sayfaları · askıdaki kuruluş/kurum
için yeni yetkilendirme kuralı · kurum domain atama · kullanıcı silme · platform admin atama · bildirim e-postası.

## Rollback Beklentisi
Yeni dosyalar silinir, `main.py` / `app-shell.tsx` / `tr.json` / doküman satırları geri alınır. Migration yok.

## Risks
- `organizations.status` ve `institutions.status` üzerinde CHECK kısıtı YOK (serbest metin). `SUSPENDED`
  yazmak migration gerektirmez ama değer DB'de kısıtlanmıyor.
- Askıdaki kuruluş yalnız `status == "ACTIVE"` bakan yerlerde etkisiz kalır (Keşfet/kuruluş seçici, doğrulama
  kuyruğu); üyelerinin çalışma onaylama / değerlendirme / tanıklık yollarında durum kontrolü yok.
  `Institution.status` hiçbir yerde okunmuyor → kurum askısı bugün yalnız etikettir.

## Assumptions
- (varsayım) CHECK olmadığı için `SUSPENDED` "izinli" sayıldı ve O4 + kurum askısı uygulandı.
- (varsayım) "Aktif platform admini" = `is_platform_admin AND status = 'ACTIVE' AND deleted_at IS NULL`.
- (varsayım) Geri açma her zaman `ACTIVE`'e döner (önceki `PENDING` saklanmıyor; e-posta doğrulama kapısı
  `email_verified_at` ile ayrıca korunur).
- (varsayım) Soft-delete edilmiş kuruluş (`deleted_at`) listede görünmez, tekil işlemde `404`.
- (varsayım) Kullanıcı listesinde `DELETED` kullanıcılar da görünür (admin denetimi); üzerlerinde işlem `404`.
- (varsayım) Kurum seviye değişikliği aynı seviyeyse audit yazılmaz (idempotency kuralıyla tutarlı).

## Unknowns
- Askıdaki kuruluş/kurumun tam olarak neyi yapamayacağı (ürün kararı + yetkilendirme değişikliği gerekir).
- `status` sütunlarına CHECK ekleyen migration ne zaman açılacak.

## Sorular ve Cevaplar (ham kayıt)
Kullanıcıya/alt-ajana soru sorulmadı (orkestratör talimatı). Tüm cevaplar şemsiye atdd.md'den ve
orkestratörün iş paketi tanımından alındı; eksikler yukarıda "varsayım" olarak işaretlendi.
