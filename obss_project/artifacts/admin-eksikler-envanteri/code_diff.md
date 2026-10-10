# code_diff — admin-eksikler-envanteri (birleşik, 2026-10-10)

Kullanıcıya ait ve KAPSAM DIŞI: backend/app/services/engagement.py, backend/tests/test_engagement_tasks.py

## Değişen izlenen dosyalar (git diff --stat)
```
 .env.example                                       |   4 +
 PLAN.md                                            |  11 +
 backend/app/api/admin.py                           |  56 +++-
 backend/app/api/discover.py                        |   4 +-
 backend/app/api/institutions.py                    |   3 +
 backend/app/api/organizations.py                   |  23 +-
 backend/app/core/config.py                         |   6 +
 backend/app/core/email_messages.py                 |  28 ++
 backend/app/main.py                                |   8 +
 backend/app/models/__init__.py                     |   4 +
 backend/app/services/audit.py                      |  25 ++
 backend/app/services/authorization.py              |  70 +++-
 backend/app/services/discover.py                   |   5 +
 backend/app/services/fraud_flag.py                 |  28 +-
 backend/app/services/organization.py               |  30 +-
 backend/app/services/skill.py                      |  10 +-
 backend/app/workers/outbox_worker.py               | 182 +++++++++++
 .../tests/authorization/test_admin_router_gate.py  |  10 +-
 backend/tests/authorization/test_discover_authz.py |   3 +-
 docs/API.md                                        |  64 +++-
 docs/AUTHORIZATION.md                              |  22 ++
 docs/SECURITY.md                                   |  20 ++
 frontend/app/admin/dogrulama-kuyrugu/page.test.tsx |  92 +++++-
 frontend/app/admin/dogrulama-kuyrugu/page.tsx      |  27 +-
 .../app/admin/sahtekarlik-isaretleri/page.test.tsx | 110 ++++++-
 frontend/app/admin/sahtekarlik-isaretleri/page.tsx |  26 +-
 frontend/app/admin/skiller/page.test.tsx           | 191 +++++++++--
 frontend/app/admin/skiller/page.tsx                |  68 +++-
 .../calismalar/[id]/certificate-checks-section.tsx |  19 +-
 frontend/app/calismalar/[id]/page.tsx              |  17 +-
 frontend/app/kesfet/page.tsx                       |   2 +
 frontend/app/kurulus/[id]/panel/page.tsx           |   2 +
 frontend/components/app-shell.tsx                  |  49 +++
 frontend/lib/api/admin.test.ts                     |  63 +++-
 frontend/lib/api/admin.ts                          |  73 ++++-
 frontend/lib/api/discover.ts                       |   2 +
 frontend/lib/api/organizations.ts                  |   2 +
 frontend/messages/tr.json                          | 363 ++++++++++++++++++++-
 38 files changed, 1580 insertions(+), 142 deletions(-)
```

## Yeni (izlenmeyen) dosyalar
```
?? backend/alembic/versions/q7c1m2p3l4n5_add_complaints.py
?? backend/app/api/admin_audit.py
?? backend/app/api/admin_complaints.py
?? backend/app/api/admin_directory.py
?? backend/app/api/complaints.py
?? backend/app/models/complaint.py
?? backend/app/schemas/complaint.py
?? backend/app/services/admin_directory.py
?? backend/app/services/complaint.py
?? backend/tests/_complaint_data.py
?? backend/tests/authorization/test_admin_audit_actor_ip.py
?? backend/tests/authorization/test_admin_audit_authz.py
?? backend/tests/authorization/test_admin_directory_authz.py
?? backend/tests/authorization/test_admin_pagination_authz.py
?? backend/tests/authorization/test_complaints_authz.py
?? backend/tests/test_admin_pagination.py
?? backend/tests/test_complaints.py
?? backend/tests/test_organization_verification_notification.py
?? frontend/app/admin/denetim-kayitlari/
?? frontend/app/admin/kullanicilar/
?? frontend/app/admin/kuruluslar/
?? frontend/app/admin/kurumlar/
?? frontend/app/admin/layout.test.tsx
?? frontend/app/admin/layout.tsx
?? frontend/app/admin/page.test.tsx
?? frontend/app/admin/page.tsx
?? frontend/app/admin/sahtekarlik-isaretleri/gecmis/
?? frontend/app/admin/sikayetler/
?? frontend/app/sikayetlerim/
?? frontend/components/admin-pagination.tsx
?? frontend/components/admin/
?? frontend/components/complaint-attachment-link.tsx
?? frontend/components/upheld-complaint-badge.test.tsx
?? frontend/components/upheld-complaint-badge.tsx
?? frontend/lib/api/admin-audit.test.ts
?? frontend/lib/api/admin-audit.ts
?? frontend/lib/api/admin-directory.test.ts
?? frontend/lib/api/admin-directory.ts
?? frontend/lib/api/complaints.test.ts
?? frontend/lib/api/complaints.ts
?? frontend/lib/complaints/
```

## Tam diff için: git diff -- <dosya>  (yeni dosyalar doğrudan okunur)
