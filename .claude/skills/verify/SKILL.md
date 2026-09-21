---
name: verify
description: Runs the real quality-gate checklist (build/lint/type-check/unit/e2e/accessibility/security/etc.) against the project and reports PASS/FAIL/N/A per gate — never authors or fixes code, never runs Copilot. Use this after code-copilot has made the tests pass, as the TDD/ATDD pipeline's refactor gate (atdd → test-copilot → code-copilot → verify → red-team → human approval).
---

# Verify — quality gates only, no authoring

## Kullanılacak destek skiller
- `caveman`, `ponytail` (full) — her zaman aktif.
- `superpowers:systematic-debugging` — bir gate kırmızıysa, kör deneme-yanılma yerine bunu izle.

## KURAL: Doğrulama Süreci
- Asla onaysız ✅ işareti konulmaz.
- Supabase tablolarına dokunan kodlarda supabase-check çalıştır.
- Format kontrollerini ve CI komutlarını birebir çalıştır.

## Precondition
`artifacts/<task-slug>/code_diff.md` should exist (from
`code-copilot`, run after `test-copilot`) so you know which files/surfaces to
verify. `test_diff.md`'s (from `test-copilot`) "AC -> Test Mapping" section tells you which
test files to run — read it if present, don't guess.

## The gate checklist

Run **every** gate below against the real project. For each one, either
produce real PASS/FAIL evidence or mark it **N/A** with a one-line reason. Do
not skip a gate silently and do not mark one passing without having actually
run something.

**Before gates 2/4/5/6, check the project's CI workflow file** (e.g.
`.github/workflows/*.yml`) for the exact command it runs for build/lint/
format/type-check/test, and use that same invocation (`uv run pyright`,
`npm run build`, etc.) — not a hand-assembled equivalent. A locally
"equivalent" command can differ from CI in ways that both hide a real
failure (wrong scope — one file instead of the whole project) and
manufacture a fake one (wrong environment — a bare venv interpreter
resolving imports differently than the tool's own runner). If no CI
workflow file exists, fall back to the project's own docs/README for the
canonical command.

1. **Dosya konumu** — confirm the files you're about to verify actually exist
   on disk where `code_diff.md`/`test_report.md` claim (`git status --short`,
   `Read`). Not a pass/fail gate itself, but everything below depends on it.
2. **Build/derleme** — the project's real build or import-sanity command
   (e.g. `uv run python -c "import <module>"` for Python, `npm run build`
   for JS/TS). PASS/FAIL from real output.
3. **Supabase şema/canlı doğrulama** — **MANDATORY, not skippable, whenever
   the change touches a Supabase-backed table** (new/changed migration, a
   service function that calls `{supabase_url}/rest/v1/...`, or a changed
   header/param/payload on an existing such call). Run the `supabase-check`
   skill. N/A **only** if this task's `code_diff.md` touches zero
   Supabase-calling code and zero migration files — state that explicitly,
   don't assume N/A by default. FAIL if the skill finds the migration isn't
   actually applied to the real project, or a Supabase call's header/payload
   doesn't match what a real request needs (e.g. a masked/placeholder secret
   value instead of the real one).
4. **Lint** — the project's configured linter (`ruff check`, `eslint`, etc.)
   if one exists in repo config, **AND**, separately, the project's own
   formatter in check mode if one is configured (e.g. `ruff format --check`,
   `prettier --check`) — a linter and a formatter are different tools with
   different failure modes (rule violations vs. whitespace/layout drift);
   running only one is not evidence for the other. N/A ("proje linter/
   formatter tanımlamıyor") if genuinely neither exists in repo config.
5. **Type check** — the project's configured type checker (`pyright`,
   `mypy`, `tsc --noEmit`) if configured. N/A otherwise, with reason.
6. **Unit testler** — run the real suite: `pytest <test files> -v` (or the
   project's equivalent). Use actual output, don't guess. Also check that
   every Acceptance Criteria in `atdd.md` (happy path + edge cases) has at
   least one covering test — a quick pyramid/code-smell pass too (see
   `lmstudio-test-review` for the fuller rubric). Remember: for DB-touching
   code, green mocked unit tests are necessary but NOT sufficient — gate 3
   is what actually proves the real call works.
7. **E2E testler** — if the project has a configured e2e suite (Playwright,
   Cypress, etc.), run it. If none is configured but the task touches a
   rendered web UI, drive the real user flow with **Playwright MCP**
   (`mcp__playwright__browser_navigate` → `browser_snapshot`/`browser_click`/
   `browser_fill_form` → `browser_console_messages` for JS errors →
   `browser_network_requests` for broken links/failed calls) instead of
   defaulting to N/A — see `frontend-audit` skill for the full tool
   reference and verified traps. N/A only if there is genuinely no web UI
   in scope for this task.
8. **Lighthouse (performans)** — only if the change touches a served web
   page/UI. Start the relevant dev server (`preview_start`), use the
   Lighthouse MCP server (`npm install -g @danielsogl/lighthouse-mcp@latest`
   — tool names: `run_audit`, `get_performance_score`, `get_core_web_vitals`,
   `check_performance_budget`; full 11-tool reference in `frontend-audit`)
   against the running URL. N/A if no web UI in scope for this task.
9. **Erişilebilirlik (accessibility)** — read from the same Lighthouse run's
   `get_accessibility_score` (gate 8) when it applies; report critical
   issues found, not just the numeric score. N/A under the same condition
   as gate 8.
10. **Güvenlik taraması (kritik açık)** — call the `security-scan` skill; do
    not hand-assemble scanner commands here. It runs detect-secrets / bandit /
    pip-audit / npm audit through one runner that already handles the
    invocation traps that silently produce fake-clean results (absolute-path
    zero, missing `PYTHONUTF8`, unfiltered bandit noise — see that skill for
    the evidence). Scope the scan to the changed files from `code_diff.md`:

    ```bash
    "$HOME/.claude/security-tools/venv/Scripts/python.exe" "$HOME/.claude/skills/security-scan/scan.py" <proje> --files <degisen dosyalar> --json
    ```

    Gate mapping: runner exit `0` → PASS, `1` → FAIL, `2` → runner error.
    A gate reported `MISSING`/`ERROR`/`TIMEOUT` makes the result
    **INCONCLUSIVE** — record it as such, never as PASS. This is NOT a
    replacement for the dedicated `red-team` skill that runs after this one:
    scanners prove known signatures, `red-team` reasons about business-logic
    flaws. Say so explicitly rather than claiming security review is "done".
    If the task touched per-user or per-tenant data, `authz-test` is the
    other half — a clean scanner run says nothing about IDOR.
11. **AI code review** — intentionally satisfied by the separate `red-team`
    pipeline step, not duplicated here. Record it as pending/deferred.
12. **Görsel regresyon (visual regression)** — if the task touches a
    rendered web UI, use the `vision-test` skill (Playwright screenshot →
    Copilot vision JSON → Claude reads only the JSON, no raw-image tokens
    spent) instead of marking this N/A by default. N/A only if there is no
    web UI in scope for this task at all.
13. **DAST — dışarıdan web güvenlik taraması** — only if the task touches a
    rendered web UI **and** `threat-model` produced `AC-S<n>` criteria for
    it (a live black-box scan is expensive; run it when there's an actual
    security AC to check, not on every UI change). Use **ZAP MCP** (setup +
    verified 17-tool reference in `frontend-audit`): `zap_create_context` →
    `zap_start_spider`/`zap_start_ajax_spider` → `zap_start_active_scan` →
    `zap_read_resource(uri="zap://alerts")` for findings →
    `zap_generate_report`. This is gate 10's live counterpart — gate 10
    (`security-scan`) proves known signatures in *source*, this gate proves
    them against the *running* app (misconfigured headers, exposed
    endpoints, actual injection responses). Neither replaces `red-team`
    (business-logic flaws) or `authz-test` (IDOR/tenant boundaries). N/A
    with an explicit reason if: no web UI in scope, or no security AC was
    generated for it, or ZAP isn't reachable (say so — don't silently skip).
14. **İnsan onayı** — always the last gate, always pending until the user
    explicitly signs off — this skill and `red-team` can recommend, they
    cannot grant it. Never write this as done in the report.

## Report

Write `artifacts/<task-slug>/verify_report.md`:

```markdown
# Verify Report — <task-slug>
_Reference: atdd.md, code_diff.md, test_report.md (if present)_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS/FAIL | ... |
| 2 | Build/derleme | PASS/FAIL/N/A | ... |
| 3 | Supabase şema/canlı doğrulama | PASS/FAIL/N/A | ... |
| 4 | Lint | PASS/FAIL/N/A | ... |
| 5 | Type check | PASS/FAIL/N/A | ... |
| 6 | Unit testler | PASS/FAIL | ... |
| 7 | E2E testler | PASS/FAIL/N/A | ... |
| 8 | Lighthouse (performans) | PASS/FAIL/N/A | ... |
| 9 | Erişilebilirlik | PASS/FAIL/N/A | ... |
| 10 | Güvenlik taraması | PASS/FAIL/N/A | ... |
| 11 | AI code review | PENDING (red-team) | ... |
| 12 | Görsel regresyon | PASS/FAIL/N/A | ... |
| 13 | DAST (ZAP) | PASS/FAIL/N/A | ... |
| 14 | İnsan onayı | PENDING | ... |

## AC -> Test Mapping
1. <Acceptance Criteria 1> -> <test function> -> PASS/FAIL

## Coverage / Quality Notes
<any AC with no covering test, pyramid imbalance, code smells>
```

## If a gate fails
Don't fix it yourself. If the failure is in test code, tell the user to
re-run `test-copilot` with a sharper description of what's wrong. If it's in
the implementation, tell them to re-run `code-copilot`. Report the failure
honestly; don't mark the whole step "done" while anything mandatory (build,
unit tests, any gate that applies) is still red.

## The one rule that can't bend
This skill never writes or edits implementation or test files — Read, Bash
(to run checks), and the report file only. No gate is ever marked passing
without real evidence behind it.
