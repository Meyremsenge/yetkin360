---
task_slug: sikayet-frontend
priority: Medium
threat_model: carried-over (AC-S9..AC-S14 from admin-eksikler-envanteri/atdd.md; not re-run)
coverage_target: new files covered by vitest
test_strategy: vitest + Testing Library (api client mocked at apiFetch; pages mocked at lib/api/complaints)
affected_modules: frontend/lib/api/complaints.ts, frontend/lib/complaints/*, frontend/app/sikayetlerim/**, frontend/app/admin/sikayetler/**, frontend/components/upheld-complaint-badge.tsx, app-shell, kesfet, kurulus panel, calismalar/[id]
---
# sikayet-frontend (C8 + C7 UI)

Persona: ogrenci (sikayet eden), yetkili (koordinator / kurulus uyesi), platform admin.
Source of truth: ../admin-eksikler-envanteri/atdd.md (Complaint, AC-13..AC-21, AC-S9..AC-S14).

## Acceptance Criteria (frontend slice)
- F-1 [High] API client: exact paths/bodies per contract; mutating calls carry CSRF; multipart upload sends no JSON content-type; 409 codes surface as ApiError.code (AC-13/14/15).
- F-2 [High] Student: "Sikayet et" entry on pending engagement / certificate check; form (description + up to 5 PDF/JPG/PNG <=10MB); TOO_EARLY / ALREADY_OPEN / NOT_PENDING / 429 map to clear Turkish messages; body never carries org/respondent/status (AC-S11).
- F-3 [High] Student list/detail: open complaint shows only "Islem devam etmekte" (never internal status, admin note, explanation text); terminal shows Kapatildi / Cozuldu / Hakli bulundu + admin reason (AC-19).
- F-4 [High] Respondent: sees complaint + admin note, can write explanation when status EXPLANATION_REQUESTED; no attachment UI (AC-17, AC-S9).
- F-5 [High] Admin queue /admin/sikayetler: Onceki/Sonraki via limit/offset + has_more; detail with attachment links; transitions with required-reason validation; UPHOLD behind confirm dialog (AC-16..AC-18, AC-20 -> 409 message).
- F-6 [High] Badge: upheld_complaint_count > 0 -> prominent badge with count on Kesfet org card and org profile; 0/null/undefined/NaN -> nothing rendered; no complaint text/identity (AC-18, AC-S13).
- F-7 [Medium] Every screen: loading, empty, error (aria-live/role=alert); null-safe fields (no "null"/"Invalid Date").
- F-8 [Medium] Nav: admin "Sikayetler", student "Sikayetlerim".

## Behaviour contract (errors)
| Case | UI |
|---|---|
| 409 TOO_EARLY | "Bekleme suresi henuz dolmadi" message on form |
| 409 ALREADY_OPEN | already-open message |
| 409 NOT_PENDING | no-longer-pending message |
| 429 | rate-limit message |
| 404 on detail | not-found state (no existence leak) |
| 409 INVALID_TRANSITION (admin) | invalid-transition message, queue refetched |
| other / network | generic error, role=alert |

## Assumptions (not confirmed with backend; backend/app/api/complaints.py absent at time of writing)
1. Response optional extras: `status` (internal; admin/respondent only), `viewer_role` ("COMPLAINANT"|"RESPONDENT"), `description`, `result_reason`, `admin_note`, `subject_label`, `attachments[{id,filename,size_bytes}]`, `events[]`, `explanation_text`, `subject_still_pending`, `closed_at`. All treated as nullable.
2. Attachment URLs: `/complaints/{id}/attachments/{att}` (owner) and `/admin/complaints/{id}/attachments/{att}` (admin), opened as plain links (cookie auth).
3. OPEN->UNDER_REVIEW has no explicit action in the contract; UI lets admin act on OPEN/UNDER_REVIEW alike, backend decides.
4. Reason required for DISMISS, REJECT_EXPLANATION, RESOLVE, UPHOLD; note required for REQUEST_EXPLANATION; ACCEPT_EXPLANATION optional note. Description 10..2000 chars.
5. Institution (kurum) panel badge omitted: no upheld count field known on institution endpoints; org panel + Kesfet org card covered.
