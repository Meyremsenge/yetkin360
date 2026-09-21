#!/usr/bin/env python3
"""Aggregate agentic_judge/*.json findings across finished tasks.

This is the agentic-trajectory counterpart of aggregate.py. A single
agentic-judge call scores one conversation turn; the point of this script
is the pattern ACROSS turns: a tool that keeps showing up as an extra/
missing call, a criteria score that is drifting down, or a scope-creep
rate that keeps hitting a sensitive tool. Any one of those belongs in the
next atdd.md's "Agentic Değerlendirme Kriterleri" section, not just in a
single conversation's report.

Usage:
    python aggregate_agentic.py <docs_dir> [--since-turns N] [--json]

<docs_dir> holds one subdirectory per task, each with an
agentic_judge/*.json per evaluated conversation (e.g.
your-repo/docs/<task-slug>/agentic_judge/<conversation_id>.json).
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

# category is a fixed vocabulary already (see agentic-judge subagent), so no
# canonicalisation map is needed here unlike aggregate.py's free-text
# red_team.json category field. Kept as a guard list anyway, in case a
# malformed record slipped through the skill's validation step.
KNOWN_CATEGORIES = {
    "tool-selection", "tool-args", "hallucination", "refusal-wrong",
    "instruction-drift", "redundant-call", "missing-call",
    "response-quality", "tone", "scope-creep",
}
CRITERIA = ["faithfulness", "completeness", "tone_fit", "actionability"]
SEV_ORDER = ["critical", "high", "medium", "low"]


def invalid_criteria(rr: dict) -> list[str]:
    """response_review.criteria must be 1-5 ints. A record that slipped
    through agentic-judge's validation step (or was hand-edited) with a
    1-10/percent scale would silently skew criteria_avg_per_agent if not
    caught here — the aggregation layer gets its own defense, it doesn't
    trust the skill's validation step alone."""
    bad = []
    for crit in CRITERIA:
        if crit not in rr:
            continue
        v = rr[crit]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not (1 <= v <= 5):
            bad.append(f"{crit}={v!r}")
    return bad


def load_turns(docs: Path) -> list[dict]:
    turns = []
    for f in sorted(docs.glob("*/agentic_judge/*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            turns.append({"slug": f.parent.parent.name, "file": f.name, "error": str(e)[:120]})
            continue

        rr_check = (data.get("response_review") or {}).get("criteria") or {}
        bad = invalid_criteria(rr_check)
        if bad:
            turns.append({
                "slug": f.parent.parent.name, "file": f.name,
                "error": f"response_review.criteria semadisi (1-5 bekleniyor): {', '.join(bad)}",
            })
            continue

        findings = data.get("findings") or []
        turns.append({
            "slug": f.parent.parent.name,
            "conversation_id": data.get("conversation_id") or f.stem,
            "sub_agent": data.get("sub_agent"),
            "evaluated_at": data.get("evaluated_at"),
            "verdict": data.get("verdict"),
            "findings": [
                {
                    "severity": str(x.get("severity", "?")).strip().lower(),
                    "category": str(x.get("category", "?")).strip().lower(),
                }
                for x in findings if isinstance(x, dict)
            ],
            "trajectory_review": data.get("trajectory_review") or {},
            "response_review": (data.get("response_review") or {}).get("criteria") or {},
            "scope_review": data.get("scope_review") or {},
            "user_feedback": data.get("user_feedback"),
        })
    return turns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("docs_dir")
    ap.add_argument("--since-turns", type=int, default=0,
                     help="sadece en son N degerlendirilen turu dikkate al (0 = hepsi)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    docs = Path(args.docs_dir).resolve()
    if not docs.is_dir():
        print(f"HATA: dizin yok: {docs}", file=sys.stderr)
        return 2

    turns = load_turns(docs)
    if not turns:
        print(f"HATA: {docs} altinda */agentic_judge/*.json bulunamadi", file=sys.stderr)
        return 2

    broken = [t for t in turns if "error" in t]
    ok = [t for t in turns if "error" not in t]
    ok.sort(key=lambda t: t.get("evaluated_at") or "")
    if args.since_turns:
        ok = ok[-args.since_turns:]

    # 1) category counts per sub_agent — mirrors aggregate.py's category counting
    cat_counts = collections.Counter()
    cat_by_agent = collections.defaultdict(collections.Counter)
    sev_counts = collections.Counter()

    # 2) trajectory drift — which tool keeps showing up as extra/missing, per agent
    extra_calls = collections.Counter()
    missing_calls = collections.Counter()
    order_errors = collections.Counter()
    total_by_agent = collections.Counter()

    # 3) response criteria trend — running mean per agent per criterion
    criteria_sum = collections.defaultdict(lambda: collections.Counter())
    criteria_n = collections.defaultdict(lambda: collections.Counter())

    # 4) scope-creep rate + sensitive-tool exposure
    scope_total = collections.Counter()
    scope_expanded = collections.Counter()
    sensitive_hits = collections.Counter()

    # 5) judge/user disagreement — judge scored well but user pushed back
    disagreements = []

    for t in ok:
        agent = t["sub_agent"] or "?"
        total_by_agent[agent] += 1

        for f in t["findings"]:
            cat_counts[f["category"]] += 1
            cat_by_agent[agent][f["category"]] += 1
            sev_counts[f["severity"]] += 1

        tr = t["trajectory_review"]
        for tool in tr.get("extra_calls") or []:
            extra_calls[(agent, tool)] += 1
        for tool in tr.get("missing_calls") or []:
            missing_calls[(agent, tool)] += 1
        if tr and tr.get("order_correct") is False:
            order_errors[agent] += 1

        rr = t["response_review"]
        for crit in CRITERIA:
            if crit in rr and isinstance(rr[crit], (int, float)):
                criteria_sum[agent][crit] += rr[crit]
                criteria_n[agent][crit] += 1

        sr = t["scope_review"]
        if sr:
            scope_total[agent] += 1
            if sr.get("scope_expansion"):
                scope_expanded[agent] += 1
            if sr.get("sensitive_tool_involved"):
                sensitive_hits[agent] += 1

        fb = t["user_feedback"]
        if fb and rr:
            vals = [v for k, v in rr.items() if k in CRITERIA and isinstance(v, (int, float))]
            avg = sum(vals) / len(vals) if vals else 0
            if avg >= 4 and fb.get("signal") in ("retry", "edit", "thumbs_down"):
                disagreements.append({
                    "slug": t["slug"], "conversation_id": t["conversation_id"],
                    "agent": agent, "judge_avg": round(avg, 2), "user_signal": fb.get("signal"),
                })

    report = {
        "docs_dir": str(docs),
        "turn_count": len(ok),
        "by_category": dict(cat_counts.most_common()),
        "by_category_per_agent": {a: dict(c.most_common()) for a, c in cat_by_agent.items()},
        "by_severity": {s: sev_counts[s] for s in SEV_ORDER if sev_counts[s]},
        "top_extra_calls": [
            {"agent": a, "tool": tool, "count": n}
            for (a, tool), n in extra_calls.most_common(10)
        ],
        "top_missing_calls": [
            {"agent": a, "tool": tool, "count": n}
            for (a, tool), n in missing_calls.most_common(10)
        ],
        "order_error_rate": {
            a: round(order_errors[a] / total_by_agent[a], 3) for a in total_by_agent
        },
        "criteria_avg_per_agent": {
            a: {c: round(criteria_sum[a][c] / criteria_n[a][c], 2)
                for c in CRITERIA if criteria_n[a][c]}
            for a in criteria_sum
        },
        "scope_creep_rate": {
            a: round(scope_expanded[a] / scope_total[a], 3) for a in scope_total
        },
        "sensitive_tool_hits": dict(sensitive_hits),
        "judge_user_disagreement": disagreements,
        "unreadable": [f"{t['slug']}/{t['file']}" for t in broken],
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(f"\nAGENTIC POSTMORTEM - {docs.name}")
    print(f"degerlendirilen tur: {len(ok)}")
    if broken:
        print(f"OKUNAMAYAN: {', '.join(report['unreadable'])}")

    print("\nKATEGORI (toplam):")
    for c, n in cat_counts.most_common():
        mark = "" if c in KNOWN_CATEGORIES else "  <-- BILINMEYEN KATEGORI, semayi kontrol et"
        print(f"  {n:>3}  {c}{mark}")

    print("\nSIDDET:")
    for s, n in report["by_severity"].items():
        print(f"  {n:>3}  {s}")

    print("\nEN COK FAZLADAN COGRILAN TOOL'LAR (agent, tool, sayi):")
    for row in report["top_extra_calls"][:5]:
        print(f"  {row['agent']:<20} {row['tool']:<25} {row['count']}")

    print("\nEN COK EKSIK COGRILAN TOOL'LAR (agent, tool, sayi):")
    for row in report["top_missing_calls"][:5]:
        print(f"  {row['agent']:<20} {row['tool']:<25} {row['count']}")

    print("\nSCOPE-CREEP ORANI (agent bazinda, esik: 0.03):")
    for a, rate in sorted(report["scope_creep_rate"].items(), key=lambda kv: -kv[1]):
        mark = "  <-- ESIK ASILDI" if rate > 0.03 else ""
        hits = sensitive_hits.get(a, 0)
        sens = f" | hassas tool: {hits}" if hits else ""
        print(f"  {a:<20} {rate:.3f}{sens}{mark}")

    print("\nKRITER ORTALAMASI (agent bazinda):")
    for a, crits in report["criteria_avg_per_agent"].items():
        print(f"  {a}: " + ", ".join(f"{c}={v}" for c, v in crits.items()))

    if disagreements:
        print(f"\nJUDGE-KULLANICI UYUSMAZLIGI ({len(disagreements)} tur):")
        print("  judge yuksek puan verdi ama kullanici retry/edit/thumbs_down verdi")
        print("  -> judge rubric'i kalibre etmeyi dusun")
        for d in disagreements[:5]:
            print(f"  {d['slug']}/{d['conversation_id']}: judge_avg={d['judge_avg']} user={d['user_signal']}")

    if len(ok) < 10:
        print(f"\nUYARI: sadece {len(ok)} tur var. Bu ornekle 'kalip' cikarimi "
              "yapma; egilim en az 10-20 turdan sonra anlamlidir.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
