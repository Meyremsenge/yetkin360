# Plan — admin-denetim-bildirim-dokuman

## Dosya etkisi
Yeni:
- `backend/app/api/admin_audit.py` (A1, F2; prefix `/admin`, `require_platform_admin`)
- `backend/tests/authorization/test_admin_audit_authz.py`
- `backend/tests/test_organization_verification_notification.py`
- `frontend/lib/api/admin-audit.ts` + `.test.ts`
- `frontend/app/admin/denetim-kayitlari/page.tsx` + `page.test.tsx`
- `frontend/app/admin/sahtekarlik-isaretleri/gecmis/page.tsx` + `page.test.tsx`

Değişen (hedefli, ekleme ağırlıklı):
- `backend/app/main.py` (router kaydı), `services/audit.py` (`list_audit_events`),
  `services/fraud_flag.py` (`list_fraud_history`), `services/organization.py` (iki fonksiyonda outbox),
  `workers/outbox_worker.py` (handler + kayıt), `core/email_messages.py` (metin sabitleri)
- `frontend/messages/tr.json` (`adminAudit`, `adminFraudHistory`, shell/adminHome satırları),
  `components/app-shell.tsx`, `app/admin/page.tsx` (yalnız bağlantı satırları)
- `docs/API.md`, `docs/AUTHORIZATION.md`, `docs/SECURITY.md`, `PLAN.md`

Migration yok. Yeni bağımlılık yok.

## Sıra
1. Testler (authz matrisi + O2 servis/handler) → kırmızı
2. Servis fonksiyonları + router + outbox + handler → yeşil
3. Frontend client + sayfalar + testler
4. Dokümanlar
5. verify

## Riskler
- Paylaşılan dosyalar (`tr.json`, `app-shell.tsx`, `outbox_worker.py`, `organization.py`): hedefli Python replace, öncesinde yeniden okuma.
- `AdminPagination` bileşeni başka ajandan geldi; arayüzü sabit varsayıldı.
