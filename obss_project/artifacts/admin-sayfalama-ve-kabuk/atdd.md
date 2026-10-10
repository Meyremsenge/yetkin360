---
task_slug: admin-sayfalama-ve-kabuk
parent: admin-eksikler-envanteri
threat_model: carried (AC-S1..AC-S5 from umbrella)
priority: high
coverage_target: 85
test_strategy: {unit: 60, integration: 30, e2e: 10}
affected_modules:
  - backend/app/api/admin.py
  - backend/app/services/organization.py
  - backend/app/services/skill.py
  - backend/app/services/fraud_flag.py
  - frontend/lib/api/admin.ts
  - frontend/app/admin/{layout,page}.tsx
  - frontend/app/admin/{dogrulama-kuyrugu,skiller,sahtekarlik-isaretleri}/page.tsx
  - frontend/messages/tr.json
---

# ATDD — admin-sayfalama-ve-kabuk (O5, S3, F3, S4, X1)

Clarification questions answered from the umbrella `admin-eksikler-envanteri/atdd.md` (no user questions asked).

## Scope
Umbrella ACs owned: AC-1..AC-6, AC-8, AC-9, AC-S1..AC-S5 and behaviour-contract rows 1, 2, 4, 5, 6, 8 (empty queue), 10.
Not owned: AC-7 (docs, other agent). No new endpoint, no migration.

## Decisions
- Response envelope for the 3 list endpoints: `{"items":[...],"limit":N,"offset":M,"has_more":bool}`; item schemas unchanged.
- `has_more` computed in the service layer by fetching `limit+1` rows. Service functions return `(rows, has_more)`; the extra row never reaches the response. (Only caller of each service function is `admin.py`.)
- Merge dialog target list: dialog fetches ALL skills by walking pages (limit=200) via `getAllSkills()` only while the dialog is open. Reason: simplest option that is complete and needs no new endpoint (a search endpoint would be a new feature); ~300 skills = 2 requests.
- `/admin` guard: `layout.tsx` is a client component; reads `/me` through `useSession()` and only `data.user.is_platform_admin === true` lets children render. Pending -> loading text, not admin -> `router.replace("/admin/giris")`. `/admin/giris` pathname bypasses the guard (no redirect loop).

## Acceptance criteria (mapped)
- AC-1/AC-2 [Critical]: limit+1 rows seeded -> `len(items)==limit`, `has_more=true`; exactly `limit` rows -> `has_more=false`; offset page returns remainder; UI Next enabled only when `has_more`.
- AC-3: `limit=0|201|-1`, `offset=-1|abc` -> 422 (existing Query bounds).
- AC-4/AC-S1: non-admin (talent, org ADMIN, institution COORDINATOR) -> 404 with no `items/has_more/limit/offset` in body; anonymous -> 401.
- AC-S2: `limit=200` with 250 rows -> 200 items.
- AC-S3: item keys unchanged.
- AC-5/AC-S4/AC-S5: `/admin` page links to the three screens; layout redirects non-admin without rendering children; only `/me` flag read.
- AC-6: `Skill` type aligned (no `created_at`, `SOFT`), `Organization.verification_level` T1-T4.
- AC-8: empty list -> `{"items":[],"limit":50,"offset":0,"has_more":false}` + empty-state text.
- AC-9: list error -> `role="alert"` + "Tekrar dene" button.

## Assumptions / risks
- Suspended-admin 401 is enforced by `get_current_user` (production), which the test client overrides; covered by existing `test_auth_inactive_user_tokens.py`, not repeated here.
- Org-detail mutations use cached list data; after pagination, mutation cache updates must keep the new envelope shape.
- docs (API.md / AUTHORIZATION.md) envelope update belongs to another agent.
