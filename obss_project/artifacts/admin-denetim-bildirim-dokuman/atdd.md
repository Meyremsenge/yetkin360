---
task_slug: admin-denetim-bildirim-dokuman
jira_id: null
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 85
performance_target: "admin liste uçları <300ms (limit=200)"
memory_target: null
test_strategy:
  unit: 50
  integration: 40
  e2e: 10
affected_modules:
  - backend/app/api/admin_audit.py
  - backend/app/services/audit.py
  - backend/app/services/fraud_flag.py
  - backend/app/services/organization.py
  - backend/app/workers/outbox_worker.py
  - frontend/lib/api/admin-audit.ts
  - frontend/app/admin/denetim-kayitlari
  - frontend/app/admin/sahtekarlik-isaretleri/gecmis
  - docs/API.md
  - docs/AUTHORIZATION.md
  - docs/SECURITY.md
  - PLAN.md
---

# ATDD — admin-denetim-bildirim-dokuman

Şemsiye: `admin-eksikler-envanteri/atdd.md` (A1, A2, F2, O2, S2, X2, X3, I1-not; AC-7, AC-12).
Netleştirme soruları şemsiye atdd.md'den cevaplandı; eksikler "Varsayımlar"da.

## Persona / Hedef
Platform admini: denetim kaydını ve incelenmiş işaretleri görmek; kuruluş yöneticisi: doğrulama kararından
haberdar olmak; geliştirici: dokümanın koda uyması.

## Acceptance Criteria
- **AC-1 (A1)** `GET /admin/audit-events?action&subject_type&actor_user_id&limit&offset` →
  `200 {"items","limit","offset","has_more"}`, yeniden eskiye, `has_more` limit+1 ile.
- **AC-2 (F2)** `GET /admin/fraud-flags/history?status&limit&offset` → yalnız CONFIRMED/DISMISSED,
  `reviewed_at` + `reviewed_by_user_id`, aynı zarf.
- **AC-3 (O2)** `set_verification_level` yalnız seviye yükselince, `reject_verification` her başarılı retde
  aynı transaction'da `organization.verification_decided` outbox olayı yazar; payload yalnız
  `organization_id`, `decision`, (`verification_level`). Worker kuruluşun aktif ADMIN üyelerine bildirir.
- **AC-4 (A2)** `admin.py` için IP çözümü tarifi raporlanır (dosya başka ajanın; uygulanmadı).
- **AC-5 (S2)** Ertelendi — dosya çakışması.
- **AC-6 (X2/I1-not/X3)** API.md §2.10, AUTHORIZATION.md uç tablosu, SECURITY.md GUV-02 notu, PLAN.md 3.39/3.49/3.50
  durumu koda göre.
- **AC-7 (UI)** `/admin/denetim-kayitlari` ve `/admin/sahtekarlik-isaretleri/gecmis`: filtre, sayfalama,
  yükleniyor/boş/hata durumu, null-safe render, `aria-live` hata.

## Güvenlik AC'leri (threat_model: done)
- **AC-S1** Admin olmayan (talent, org ADMIN, kurum koordinatörü) → `404`, gövdede `items`/`has_more`/`limit`/`offset` yok;
  oturumsuz → `401`; platform admini → `200`.
- **AC-S2** Audit yanıtında e-posta, şifre, token, serbest metin yok: aktör yalnız `actor_user_id`;
  `metadata` izinli anahtar listesiyle ve ≤100 karakter değerle sınırlı (name, legal_id, domain, title düşer).
- **AC-S3** `limit>200`, `limit=0`, `offset<0`, `offset=abc`, geçersiz `status` → `422 VALIDATION_ERROR`.
- **AC-S4** Outbox payload'ında adres, e-posta, not, ad yok; alıcı ve kuruluş adı worker'da id'den çözülür;
  console backend alıcı çözmez ve log'a adres yazmaz.
- **AC-S5** Uçlar salt okunur: `audit_events`'e satır yazmaz, UPDATE/DELETE yok.

## Davranış Sözleşmesi
Not: projede hata gövdesi düz biçimdedir: `{"code","message","request_id"}` (şemsiye tablodaki `{"error":{…}}`
sarmalayıcısı koddaki gerçeği yansıtmıyor).

| Durum | Dönen | Yan etki |
|---|---|---|
| Happy path | `200` zarf | yok |
| Boş sonuç | `200 {"items":[],"limit":50,"offset":0,"has_more":false}` | yok |
| `limit/offset/status` geçersiz | `422 VALIDATION_ERROR` | yok |
| Admin değil | `404 NOT_FOUND` | yok |
| Oturumsuz | `401` | yok |
| Kuruluşta aktif ADMIN yok / kuruluş yok (handler) | sessiz atlama, hata yok | e-posta yok |
| Kısmi başarı: outbox yazımı düşer | tüm transaction geri alınır | seviye değişmez |
| Seviye aynı/düşürme | olay yok | yok |

## Varsayımlar
- `audit_events.metadata` eski satırlarda ad/legal_id/domain/title taşıyor → izinli-liste yaklaşımı seçildi.
- Bildirim e-postası yalnız ADMIN rolündeki aktif üyelere gider (koordinatör/üye değil).
- Reddedilen kuruluşa bildirimde ret gerekçesi (`note`) gönderilmez (saklanmıyor).

## Test Stratejisi
Authz matrisi (rol × uç), servis/handler birim testleri (gerçek Postgres transaction), vitest (API client + iki sayfa).
