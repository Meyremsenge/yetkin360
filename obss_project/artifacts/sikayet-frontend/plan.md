# plan: sikayet-frontend
New: lib/api/complaints.ts(+test), lib/complaints/{rules,format}.ts(+test), components/upheld-complaint-badge.tsx(+test),
app/sikayetlerim/{page,yeni/page,[id]/page}.tsx(+tests), app/admin/sikayetler/{page,[id]/page}.tsx(+tests).
Edit (shared, minimal): messages/tr.json (complaints, adminComplaints), components/app-shell.tsx (2 nav items),
lib/api/discover.ts + app/kesfet/page.tsx (badge), lib/api/organizations.ts + app/kurulus/[id]/panel/page.tsx (badge),
app/calismalar/[id]/page.tsx + certificate-checks-section.tsx ("Sikayet et" link).
Order: tests first (red) -> implementation -> lint/typecheck -> full suite.
