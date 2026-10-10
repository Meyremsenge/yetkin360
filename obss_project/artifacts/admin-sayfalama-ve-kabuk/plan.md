# Plan — admin-sayfalama-ve-kabuk

Order: tests first (red) -> code (green) -> verify.

## Backend
1. `services/organization.py::list_verification_queue`, `services/skill.py::list_all_skills`, `services/fraud_flag.py::list_fraud_queue`: fetch `limit+1`, return `(rows[:limit], has_more)`. Only caller: `api/admin.py`.
2. `api/admin.py`: add `limit/offset/has_more` to the three response models; endpoints pass them through.
3. Tests: `tests/test_admin_pagination.py` (service + endpoint, limit+1 and exact-limit, 250 rows/limit=200, empty envelope, item keys); `tests/authorization/test_admin_pagination_authz.py` (role x endpoint, 404 body without envelope keys, 422 bounds, 401 anon). Update existing tests only if envelope breaks them (it extends).

## Frontend
4. `lib/api/admin.ts`: envelope types, `getVerificationQueue/getSkills/getFraudQueue({limit,offset})`, `getAllSkills()`, S4 type fixes.
5. `components/admin-pagination.tsx` (new, shared Prev/Next with `nav aria-label`, page indicator).
6. Three pages: `offset` state, query key includes offset, pagination controls, error `role=alert` + retry, preserve envelope in `setQueryData`.
7. `app/admin/layout.tsx` guard + `app/admin/page.tsx` link list (data array so others can add rows).
8. `messages/tr.json`: new keys under `adminPagination`, `adminHome` (own keys only).
9. Tests: update `lib/api/admin.test.ts`, three `page.test.tsx`; new `layout.test.tsx`, `page.test.tsx` for `/admin`.

## Verify
backend: new tests, `pytest tests/authorization -q`, `ruff check . && mypy app`; frontend: lint, typecheck, vitest on touched files.
