# Test Diff — yet-8-institution-koordinator-ogrenci-bagi

## Oluşturulan Dosyalar
- `backend/tests/test_institution.py` (yeni) — kurum oluşturma, üye davet, öğrenci-bağ isteği/onayı fonksiyonel testleri
- `backend/tests/test_institution_authorization.py` (yeni) — AC-4/AC-5 (AC-S1/AC-S2) yetkilendirme + BOLA testleri, Institution A/B karşılaştırmalı authz-test kalıbı

Durum: **RED (beklenen)** — `backend/app/services/institution.py`, `backend/app/api/institutions.py`, `backend/app/models/institution_link_request.py` ve migration henüz yok, testler import hatası/collection hatası verecek.

## Acceptance Criteria → Test Eşlemesi
| AC | Test |
|---|---|
| AC-1 | `test_create_institution_basic`, `test_create_institution_without_domain` |
| AC-2 | `test_admin_invites_coordinator`, `test_admin_invites_admin` |
| AC-3 | `test_student_requests_link_creates_pending` |
| AC-3b | `test_coordinator_approves_link_request`, `test_admin_approves_link_request` |
| AC-4 / AC-S1 | `test_coordinator_invite_member_denied_404`, `test_coordinator_cannot_invite_any_role` |
| AC-5 / AC-S2 (BOLA) | `test_coordinator_a_cannot_invite_to_institution_b`, `test_admin_a_cannot_invite_to_institution_b`, `test_coordinator_a_cannot_approve_link_request_for_b`, `test_admin_a_cannot_approve_link_request_for_b` |
| AC-6 | `test_duplicate_domain_returns_409` |
| AC-7 | `test_invite_member_to_nonexistent_institution` |
| AC-8 | `test_duplicate_pending_link_request_409` |

## Davranış Sözleşmesi → Test Eşlemesi
Satır 1 (happy path), 2 (girdi geçersiz), 3 (kaynak yok), 4 (yetkisiz erişim), 8 (hiçbir şey yapılamadı ama hata yok) test edildi. Satır 5/6/7 (dış bağımlılık hatası, zaman aşımı, kısmi başarı — outbox deseni) atdd.md'nin kendi notuyla tutarlı biçimde bu görevde implementasyon-seviyesinde ele alınacak, ayrı bir senkron test gerektirmiyor (asenkron worker davranışı bu testlerin kapsamı dışı).

## Varsayımlar (alt-ajanın raporundan)
- Endpoint yolları: `POST /institutions`, `POST /institutions/{id}/members`, `POST /institutions/{id}/link-requests`, `POST /institutions/{id}/link-requests/{request_id}/approve`.
- Response şeması alan adları (`id`, `name`, `domain`, `verification_level`, vb.) — `code-copilot` adımında gerçek implementasyonla doğrulanmalı.
- Auth middleware/Principal context'in TestClient testlerinde nasıl inject edileceği henüz netleşmedi — bu proje YET-4'ü (auth) henüz tamamlamadığı için testler muhtemelen doğrudan servis fonksiyonu çağrısına (HTTP'siz) veya bir test-only auth override'ına ihtiyaç duyacak; `code-copilot` bunu netleştirmeli.
