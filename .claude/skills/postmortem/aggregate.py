#!/usr/bin/env python3
"""Aggregate red_team.json findings across finished tasks to find repeat mistakes.

A single task's review tells you what went wrong once. The point of this script
is the pattern ACROSS tasks: the same category showing up task after task is a
process defect, not bad luck, and belongs in the next atdd.md's checklist.

Usage:
    python aggregate.py <docs_dir> [--since-tasks N] [--json]

<docs_dir> is the directory holding one subdirectory per task, each with a
red_team.json (e.g. your-repo/docs).
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

# red_team.json's category field is free text and drifts ("Security" vs
# "security" vs "Correctness / Test Gap"), which makes cross-task counting
# meaningless unless it is normalised first. Keep this map in sync with the
# fixed vocabulary documented in the red-team skill.
CANON = {
    "correctness": "correctness",
    "bug": "correctness",
    "logic": "correctness",
    "security": "security",
    "guvenlik": "security",
    "architecture": "architecture",
    "mimari": "architecture",
    "design": "architecture",
    "maintainability": "maintainability",
    "readability": "readability",
    "okunabilirlik": "readability",
    "performance": "performance",
    "reliability": "reliability",
    "test": "test-gap",
    "test gap": "test-gap",
    "test-gap": "test-gap",
    "coverage": "test-gap",
    "scope": "scope",
    "kapsam": "scope",
    "risk": "risk",
}

SEV_ORDER = ["critical", "high", "medium", "low", "info"]


def canon_category(raw: str) -> str:
    s = (raw or "?").strip().lower()
    if s in CANON:
        return CANON[s]
    # "Correctness / Test Gap" -> match on the most specific token present
    for key, val in CANON.items():
        if key in s:
            return val
    return "other"


# security_scan.md / verify_report.md sonuc sutunu da serbest metin
# ("PASS (manuel)", "N/A", "PENDING (red-team)") - kategori normalizasyonuyla
# ayni mantik: sadece 2+ gorevde tekrarlayan FAIL/MISSING/INCONCLUSIVE bir
# surec kusurudur, tek gorevdeki bir N/A ilgi cekici degildir.
RESULT_CANON = {
    "pass": "PASS", "fail": "FAIL", "n/a": "N/A", "na": "N/A",
    "missing": "MISSING", "inconclusive": "INCONCLUSIVE",
    "error": "ERROR", "timeout": "TIMEOUT", "pending": "PENDING",
}
# Bu sonuclar "ilginc degil" sayilir - normal/beklenen durumlar, kalip aramaya dahil edilmez.
RESULT_IGNORE = {"PASS", "N/A"}


def canon_result(raw: str) -> str:
    s = (raw or "?").strip().lower()
    # "PASS (manuel)" / "PENDING (red-team)" gibi parantezli notlari at
    s = s.split("(")[0].strip()
    return RESULT_CANON.get(s, "OTHER")


def _parse_markdown_table(text: str, header_must_contain: list[str]) -> list[dict]:
    """Metindeki ilk tabloyu bul (basligi verilen kelimelerin hepsini icersin),
    her satiri {header: deger} sozlugu olarak dondur. Ayrac satirini
    (---|---|---) atlar. Format uymuyorsa bos liste dondurur (sessizce)."""
    lines = text.splitlines()
    rows: list[list[str]] = []
    header: list[str] | None = None
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            if in_table:
                break  # tablo bitti
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if header is None:
            lowered = [c.lower() for c in cells]
            if all(any(k in cell for cell in lowered) for k in header_must_contain):
                header = cells
                in_table = True
            continue
        # ayrac satiri (---|:---|---:)
        if all(set(c) <= set("-: ") for c in cells if c):
            continue
        rows.append(cells)

    if header is None:
        return []
    out = []
    for cells in rows:
        row = dict(zip(header, cells))
        out.append(row)
    return out


def _find_header_key(row: dict, *needles: str) -> str | None:
    for k in row:
        lk = k.lower()
        if any(n in lk for n in needles):
            return k
    return None


def load_gate_files(docs: Path, filename: str, header_needles: list[str],
                     gate_needles: list[str], result_needles: list[str]) -> list[dict]:
    """security_scan.md / verify_report.md ortak sablonu: bir 'Gate' ve bir
    'Sonuc/Result' sutunu olan tabloyu bul, gorev basina (gate, sonuc)
    ciftlerini cikar."""
    tasks = []
    for f in sorted(docs.glob(f"*/{filename}")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            tasks.append({"slug": f.parent.name, "error": str(e)[:120], "gates": []})
            continue
        table = _parse_markdown_table(text, header_needles)
        if not table:
            tasks.append({"slug": f.parent.name, "error": "tablo bulunamadi", "gates": []})
            continue
        gate_key = _find_header_key(table[0], *gate_needles)
        result_key = _find_header_key(table[0], *result_needles)
        if not gate_key or not result_key:
            tasks.append({"slug": f.parent.name, "error": "gate/sonuc sutunu bulunamadi", "gates": []})
            continue
        gates = []
        for row in table:
            gate_name = (row.get(gate_key) or "").strip()
            result = canon_result(row.get(result_key) or "")
            if gate_name and result != "OTHER":
                gates.append({"gate": gate_name, "result": result})
        tasks.append({"slug": f.parent.name, "gates": gates})
    return tasks


def summarize_gate_repeats(gate_tasks: list[dict]) -> dict:
    """(gate, sonuc) cifti 2+ farkli gorevde tekrarlarsa surec kusuru adayidir
    - tipki kategori tekrarinda oldugu gibi. Sadece FAIL/MISSING/INCONCLUSIVE/
    ERROR/TIMEOUT/PENDING ilgi cekicidir (RESULT_IGNORE PASS/N/A'yi eler)."""
    pair_tasks = collections.defaultdict(set)
    for t in gate_tasks:
        for g in t.get("gates", []):
            if g["result"] in RESULT_IGNORE:
                continue
            pair_tasks[(g["gate"], g["result"])].add(t["slug"])
    repeats = {f"{gate} -> {result}": sorted(slugs)
               for (gate, result), slugs in pair_tasks.items() if len(slugs) > 1}
    unreadable = [t["slug"] for t in gate_tasks if "error" in t]
    return {"repeat_gate_results": repeats, "unreadable": unreadable}


def load_tasks(docs: Path) -> list[dict]:
    tasks = []
    for f in sorted(docs.glob("*/red_team.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            tasks.append({"slug": f.parent.name, "error": str(e)[:120]})
            continue

        findings = data.get("findings") or []
        if isinstance(findings, dict):
            findings = list(findings.values())

        tasks.append({
            "slug": f.parent.name,
            "reviewed_at": data.get("reviewed_at"),
            "verdict": data.get("verdict") or data.get("ready_to_commit"),
            "findings": [
                {
                    "severity": str(x.get("severity", "?")).strip().lower(),
                    "category": canon_category(x.get("category", "")),
                    "raw_category": x.get("category"),
                    "file": x.get("file"),
                    "issue": (x.get("issue") or "")[:200],
                }
                for x in findings if isinstance(x, dict)
            ],
        })
    return tasks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("docs_dir")
    ap.add_argument("--since-tasks", type=int, default=0,
                    help="sadece en son N gorevi dikkate al (0 = hepsi)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    docs = Path(args.docs_dir).resolve()
    if not docs.is_dir():
        print(f"HATA: dizin yok: {docs}", file=sys.stderr)
        return 2

    tasks = load_tasks(docs)
    if not tasks:
        print(f"HATA: {docs} altinda */red_team.json bulunamadi", file=sys.stderr)
        return 2

    broken = [t for t in tasks if "error" in t]
    ok = [t for t in tasks if "error" not in t]
    ok.sort(key=lambda t: t.get("reviewed_at") or "")
    if args.since_tasks:
        ok = ok[-args.since_tasks:]

    cats = collections.Counter()
    sevs = collections.Counter()
    files = collections.Counter()
    cat_tasks = collections.defaultdict(set)
    file_tasks = collections.defaultdict(set)

    for t in ok:
        for f in t["findings"]:
            cats[f["category"]] += 1
            sevs[f["severity"]] += 1
            if f["file"]:
                files[f["file"]] += 1
                file_tasks[f["file"]].add(t["slug"])
            cat_tasks[f["category"]].add(t["slug"])

    total = sum(cats.values())
    # A category hitting more than one task is a repeating process defect
    # rather than a one-off; that is the only signal worth acting on.
    repeats = {c: sorted(s) for c, s in cat_tasks.items() if len(s) > 1}

    # Header tespiti sadece "gate" sutununu arar; sonuc sutunu adi
    # rapor diline gore degisiyor (Sonuc/Result) - onu result_needles
    # ile ayrica, header bulunduktan SONRA ariyoruz (bkz. load_gate_files).
    security_tasks = load_gate_files(
        docs, "security_scan.md",
        header_needles=["gate"],
        gate_needles=["gate"], result_needles=["sonu", "result"])
    verify_tasks = load_gate_files(
        docs, "verify_report.md",
        header_needles=["gate"],
        gate_needles=["gate"], result_needles=["sonu", "result"])
    security_summary = summarize_gate_repeats(security_tasks)
    verify_summary = summarize_gate_repeats(verify_tasks)

    report = {
        "docs_dir": str(docs),
        "task_count": len(ok),
        "finding_count": total,
        "by_category": dict(cats.most_common()),
        "by_severity": {s: sevs[s] for s in SEV_ORDER if sevs[s]},
        "repeat_categories": repeats,
        # Finding count alone is misleading: one messy task can pile several
        # findings onto a file and make it look chronically bad. A file is only
        # "hot" if it collects findings across MULTIPLE tasks.
        "hot_files": {
            f: {"findings": n, "tasks": len(file_tasks[f])}
            for f, n in files.most_common(5)
        },
        "unreadable": [t["slug"] for t in broken],
        "security_scan_task_count": len([t for t in security_tasks if "error" not in t]),
        "repeat_security_gate_results": security_summary["repeat_gate_results"],
        "security_scan_unreadable": security_summary["unreadable"],
        "verify_task_count": len([t for t in verify_tasks if "error" not in t]),
        "repeat_verify_gate_results": verify_summary["repeat_gate_results"],
        "verify_unreadable": verify_summary["unreadable"],
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(f"\nPOSTMORTEM - {docs.name}")
    print(f"gorev: {len(ok)} | bulgu: {total}")
    if broken:
        print(f"OKUNAMAYAN: {', '.join(report['unreadable'])}")

    print("\nKATEGORI (kac gorevde tekrarladi):")
    for c, n in cats.most_common():
        mark = f"  <-- {len(cat_tasks[c])} farkli gorevde" if c in repeats else ""
        print(f"  {n:>3}  {c}{mark}")

    print("\nSIDDET:")
    for s, n in report["by_severity"].items():
        print(f"  {n:>3}  {s}")

    if files:
        print("\nEN COK BULGU ALAN DOSYALAR (bulgu / kac farkli gorevde):")
        for f, n in files.most_common(5):
            k = len(file_tasks[f])
            mark = "  <-- SICAK (birden fazla gorevde)" if k > 1 else \
                   "  (tek gorevden - kronik degil)"
            print(f"  {n:>3} / {k} gorev  {f}{mark}")

    print("\nTEKRAR EDEN KATEGORILER (surec kusuru adaylari):")
    if repeats:
        for c, slugs in sorted(repeats.items(), key=lambda kv: -cats[kv[0]]):
            print(f"  {c}: {', '.join(slugs)}")
    else:
        print("  yok - henuz tekrar eden kalip olusmamis")

    if len(ok) < 5:
        print(f"\nUYARI: sadece {len(ok)} gorev var. Bu ornekle 'kalip' cikarimi "
              "yapma; egilim en az 5-10 gorevden sonra anlamlidir.")

    def _print_gate_section(title: str, task_count: int, repeats_map: dict, unreadable: list[str]):
        print(f"\n{title} ({task_count} gorev okunabildi):")
        if unreadable:
            print(f"  OKUNAMAYAN: {', '.join(unreadable)}")
        if repeats_map:
            for pair, slugs in sorted(repeats_map.items(), key=lambda kv: -len(kv[1])):
                print(f"  {pair}: {', '.join(slugs)}")
        else:
            print("  yok - henuz 2+ gorevde tekrarlayan gate/sonuc yok")

    _print_gate_section("SECURITY_SCAN.MD - TEKRAR EDEN GATE SONUCLARI",
                         report["security_scan_task_count"],
                         report["repeat_security_gate_results"],
                         report["security_scan_unreadable"])
    _print_gate_section("VERIFY_REPORT.MD - TEKRAR EDEN GATE SONUCLARI",
                         report["verify_task_count"],
                         report["repeat_verify_gate_results"],
                         report["verify_unreadable"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
