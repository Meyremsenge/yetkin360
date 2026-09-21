#!/usr/bin/env python3
"""Deterministic security scanner runner for the ATDD pipeline's security gate.

Wraps detect-secrets / bandit / pip-audit / npm audit behind one command so the
calling agent cannot re-introduce the invocation traps documented in SKILL.md
(absolute-path silent zero, missing PYTHONUTF8, unfiltered bandit noise).

Usage:
    python scan.py <project_dir> [--files a.py b.py ...] [--json]
    python scan.py <project_dir> --accept-secrets   # mevcut bulgulari baseline'a yaz

Exit codes: 0 = gate PASS, 1 = gate FAIL (findings), 2 = runner error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path.home() / ".claude" / "security-tools" / "venv" / "Scripts"
IS_WIN = os.name == "nt"
EXE = ".exe" if IS_WIN else ""

# bandit: -ll = MEDIUM+ severity, -ii = MEDIUM+ confidence. Without both, test
# files alone produce triple-digit B101 noise and the gate gets ignored.
BANDIT_EXCLUDE = ",".join(
    ["tests", "test", ".venv", "venv", "node_modules", ".git", "__pycache__"]
)

# Cache/build artefacts produce pure-noise entropy hits (a .pytest_cache tag file
# is a random hex string by design). Excluding them is not weakening the gate.
# The baseline file stores hashes of accepted findings; scanning it makes every
# stored hash reappear as a fresh high-entropy hit, so it must exclude itself.
SECRET_EXCLUDE_RE = (
    r"(^|/|\\)(\.git|\.venv|venv|node_modules|__pycache__|\.pytest_cache|"
    r"\.mypy_cache|\.ruff_cache|dist|build|\.next|coverage|"
    r"\.secrets\.baseline)(/|\\|$)"
)

BASELINE_NAME = ".secrets.baseline"


def env() -> dict:
    """PYTHONUTF8=1 is mandatory: a non-ASCII character anywhere in the path
    (e.g. a Turkish 'Ç' in the Windows user name) crashes pip-audit with
    UnicodeDecodeError before it prints anything."""
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def tool(name: str) -> str | None:
    p = TOOLS / f"{name}{EXE}"
    return str(p) if p.exists() else shutil.which(name)


def run(cmd: list[str], cwd: Path, timeout: int = 240):
    try:
        return subprocess.run(
            cmd, cwd=str(cwd), env=env(), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None


def load_baseline(root: Path) -> set[str]:
    p = root / BASELINE_NAME
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text(encoding="utf-8")).get("accepted", []))
    except (json.JSONDecodeError, OSError):
        return set()


def scan_secrets(root: Path, files: list[str], accept: bool = False) -> dict:
    """detect-secrets MUST receive paths relative to cwd. Given an absolute
    POSIX-style path it exits 0 with an empty result set and no error - a
    silent pass that looks identical to a clean repo."""
    exe = tool("detect-secrets")
    if not exe:
        return {"status": "MISSING", "detail": "detect-secrets kurulu degil"}

    targets = files or ["--all-files", "."]
    r = run([exe, "scan", "--exclude-files", SECRET_EXCLUDE_RE, *targets], root)
    if r is None:
        return {"status": "TIMEOUT", "detail": "tarama 240s icinde bitmedi - kapsami daralt"}
    if r.returncode != 0 and not r.stdout.strip():
        return {"status": "ERROR", "detail": (r.stderr or "")[:400]}

    try:
        results = json.loads(r.stdout).get("results", {})
    except json.JSONDecodeError:
        return {"status": "ERROR", "detail": "JSON ayristirilamadi"}

    all_hits = [
        {"file": f, "line": i["line_number"], "type": i["type"],
         "hash": i["hashed_secret"]}
        for f, items in results.items()
        for i in items
    ]

    if accept:
        (root / BASELINE_NAME).write_text(
            json.dumps({
                "_comment": "Incelenmis ve kabul edilmis bulgular. Gercek bir sir "
                            "buraya EKLENMEZ - once iptal edilir, sonra silinir.",
                "accepted": sorted({h["hash"] for h in all_hits}),
            }, indent=2),
            encoding="utf-8",
        )
        return {"status": "PASS", "findings": [],
                "detail": f"{len(all_hits)} bulgu baseline'a yazildi"}

    baseline = load_baseline(root)
    new = [h for h in all_hits if h["hash"] not in baseline]
    known = len(all_hits) - len(new)
    detail = f"{known} bulgu baseline'da (yok sayildi)" if known else None
    return {"status": "FAIL" if new else "PASS", "findings": new, "detail": detail}


def scan_python_sast(root: Path, files: list[str]) -> dict:
    exe = tool("bandit")
    if not exe:
        return {"status": "MISSING", "detail": "bandit kurulu degil"}

    py = [f for f in files if f.endswith(".py")]
    if files and not py:
        return {"status": "N/A", "detail": "degisen Python dosyasi yok"}

    cmd = [exe, "-f", "json", "-q", "-ll", "-ii"]
    cmd += py if py else ["-r", ".", "-x", BANDIT_EXCLUDE]

    r = run(cmd, root)
    if r is None:
        return {"status": "TIMEOUT", "detail": "bandit 240s icinde bitmedi"}
    if not r.stdout.strip():
        return {"status": "ERROR", "detail": (r.stderr or "cikti yok")[:400]}

    try:
        results = json.loads(r.stdout).get("results", [])
    except json.JSONDecodeError:
        return {"status": "ERROR", "detail": "JSON ayristirilamadi"}

    findings = [
        {
            "file": x["filename"], "line": x["line_number"], "id": x["test_id"],
            "severity": x["issue_severity"], "text": x["issue_text"][:110],
        }
        for x in results
    ]
    return {"status": "FAIL" if findings else "PASS", "findings": findings}


def scan_python_deps(root: Path) -> dict:
    if not any((root / n).exists() for n in
               ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile")):
        return {"status": "N/A", "detail": "Python bagimlilik manifesti yok"}

    exe = tool("pip-audit")
    if not exe:
        return {"status": "MISSING", "detail": "pip-audit kurulu degil"}

    req = root / "requirements.txt"
    cmd = [exe, "-f", "json", "--progress-spinner", "off"]
    if req.exists():
        cmd += ["-r", "requirements.txt"]

    r = run(cmd, root, timeout=300)
    if r is None:
        return {"status": "TIMEOUT", "detail": "pip-audit 300s icinde bitmedi (ag yavas olabilir)"}
    if not r.stdout.strip():
        return {"status": "ERROR", "detail": (r.stderr or "cikti yok")[:400]}

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"status": "ERROR", "detail": "JSON ayristirilamadi"}

    findings = [
        {"package": d.get("name"), "version": d.get("version"),
         "id": v.get("id"), "fix": (v.get("fix_versions") or ["yok"])[0]}
        for d in data.get("dependencies", [])
        for v in d.get("vulns", [])
    ]
    return {"status": "FAIL" if findings else "PASS", "findings": findings}


def scan_node_deps(root: Path) -> dict:
    if not (root / "package.json").exists():
        return {"status": "N/A", "detail": "package.json yok"}
    exe = shutil.which("npm")
    if not exe:
        return {"status": "MISSING", "detail": "npm kurulu degil"}

    r = run([exe, "audit", "--json", "--audit-level=high"], root, timeout=300)
    if r is None:
        return {"status": "TIMEOUT", "detail": "npm audit 300s icinde bitmedi"}
    if not r.stdout.strip():
        return {"status": "ERROR", "detail": (r.stderr or "cikti yok")[:400]}

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"status": "ERROR", "detail": "JSON ayristirilamadi"}

    findings = [
        {"package": name, "severity": v.get("severity"),
         "via": str(v.get("via", ""))[:90]}
        for name, v in (data.get("vulnerabilities") or {}).items()
        if v.get("severity") in ("high", "critical")
    ]
    return {"status": "FAIL" if findings else "PASS", "findings": findings}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--files", nargs="*", default=[],
                    help="degisen dosyalar (proje koküne GORELI). Bos ise tum proje.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--accept-secrets", action="store_true",
                    help="mevcut sizinti bulgularini .secrets.baseline'a yaz "
                         "(SADECE hepsini tek tek inceledikten sonra)")
    args = ap.parse_args()

    root = Path(args.project_dir).resolve()
    if not root.is_dir():
        print(f"HATA: dizin yok: {root}", file=sys.stderr)
        return 2

    report = {
        "project": str(root),
        "scope": args.files or "tum proje",
        "gates": {
            "secrets": scan_secrets(root, args.files, args.accept_secrets),
            "python_sast": scan_python_sast(root, args.files),
            "python_deps": scan_python_deps(root),
            "node_deps": scan_node_deps(root),
        },
    }
    failed = [k for k, v in report["gates"].items() if v["status"] == "FAIL"]
    broken = [k for k, v in report["gates"].items()
              if v["status"] in ("ERROR", "TIMEOUT")]
    report["verdict"] = "FAIL" if failed else ("INCONCLUSIVE" if broken else "PASS")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\nGUVENLIK TARAMASI - {root.name}")
        print(f"kapsam: {report['scope']}\n")
        for name, g in report["gates"].items():
            n = len(g.get("findings", []))
            extra = f" ({n} bulgu)" if n else ""
            detail = f" - {g['detail']}" if g.get("detail") else ""
            print(f"  [{g['status']:<12}] {name}{extra}{detail}")
            for f in g.get("findings", [])[:10]:
                print(f"        {f}")
            if n > 10:
                print(f"        ... +{n - 10} bulgu daha")
        print(f"\nSONUC: {report['verdict']}")
        if broken:
            print("UYARI: bir gate calisamadi - bunu 'temiz' saymayin.")

    return 1 if report["verdict"] != "PASS" else 0


if __name__ == "__main__":
    sys.exit(main())
