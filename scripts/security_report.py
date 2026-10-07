"""Run the security test suites and write the route x test coverage matrix.

    python scripts/security_report.py

Runs (JUnit XML, no extra plugins):
  backend: tests/test_security.py, tests/test_audit_log.py, tests/test_artifact_integrity.py
  ml:      tests/test_pii.py, tests/test_registry.py
and writes reports/security/security_tests.md + security_tests.json. Exit code 1 if any test failed.
The input-abuse and prompt-injection tests load the real AI engines (about a minute) when the synthetic world exists.
"""
from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "security"
SUITES = [("backend", ROOT / "backend", ["tests/test_security.py", "tests/test_audit_log.py", "tests/test_artifact_integrity.py"]),
          ("ml", ROOT, ["ml/tests/test_pii.py", "ml/tests/test_registry.py"])]
TOKEN_CASES = ["missing_token", "wrong_scheme", "malformed", "bad_signature", "expired", "alg_none", "alg_hs512",
               "unknown_kid", "missing_kid", "no_exp_claim", "issued_in_future", "forged_role"]
ROUTE_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) (/\S*)")


def norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


def run_suite(name: str, cwd: Path, files: list[str], tmp: Path) -> list[dict]:
    xml = tmp / f"{name}.xml"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", *files]
    print(f"[{name}] {' '.join(cmd[3:])}", flush=True)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [line for line in proc.stdout.splitlines() if line.strip()][-1:] or ["(no output)"]
    print(f"[{name}] {tail[0]}", flush=True)
    cases = []
    for tc in ET.parse(xml).getroot().iter("testcase"):
        outcome = "passed"
        for tag, label in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            el = tc.find(tag)
            if el is not None:
                outcome = label
                message = (el.get("message") or "")[:300]
                break
        else:
            message = ""
        cases.append({"suite": name, "file": tc.get("classname"), "name": tc.get("name"), "outcome": outcome,
                      "seconds": float(tc.get("time") or 0), "message": message})
    return cases


def classify(case: dict) -> tuple[str, str | None, str]:
    """(test family, route or None, column)."""
    name = case["name"]
    func, _, param = name.partition("[")
    param = param[:-1] if param.endswith("]") else param
    if func == "test_protected_route_rejects_bad_token":
        route, _, token_case = param.rpartition("-")
        return "token", route, token_case
    if func == "test_role_matrix":
        route, _, role = param.rpartition(" as ")
        return "role", route, f"as {role}"
    if func == "test_ownership_cannot_read_someone_else":
        route, _, _ = param.rpartition(" as ")
        return "ownership", route, "ownership"
    if func == "test_public_route_needs_no_token":
        return "public", param, "public"
    m = ROUTE_RE.match(param)
    if m:
        return "input", f"{m.group(1)} {m.group(2)}", "input abuse"
    return "other", None, func


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="uvera_security_"))
    t0 = time.time()
    cases = []
    for name, cwd, files in SUITES:
        cases += run_suite(name, cwd, files, tmp)
    seconds = round(time.time() - t0, 1)

    sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "ml")]
    import os

    os.environ.setdefault("WARM_ON_START", "false")
    sys.path.insert(0, str(ROOT / "backend" / "tests"))
    import test_security as T  # the same route classification the tests use

    routes = [(m, p) for m, p, *_ in T.ALL_ROUTES]
    access = {(m, p): ("public" if (m, p) in T.PUBLIC else "roles: " + ", ".join(T.PROTECTED.get((m, p), ())) or "?")
              for m, p in routes}
    cells: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    other = []
    for c in cases:
        family, route, col = classify(c)
        c["family"], c["route"], c["column"] = family, route, col
        if route:
            m, _, p = route.partition(" ")
            key = next((f"{rm} {rp}" for rm, rp in routes if rm == m and norm(rp) == norm(p)), route)
            c["route"] = key
            cells[key][col].append(c["outcome"])
        else:
            other.append(c)

    def cell(outcomes: list[str]) -> str:
        if not outcomes:
            return "-"
        if any(o in ("failed", "error") for o in outcomes):
            return "FAIL"
        if all(o == "skipped" for o in outcomes):
            return "skip"
        n = sum(o == "passed" for o in outcomes)
        return "pass" if len(outcomes) == 1 else f"{n}/{len(outcomes)} pass"

    columns = ["public"] + TOKEN_CASES + ["as customer", "as agent", "as ops", "ownership", "input abuse"]
    totals = {k: sum(c["outcome"] == k for c in cases) for k in ("passed", "failed", "error", "skipped")}
    by_family = defaultdict(lambda: defaultdict(int))
    for c in cases:
        by_family[c["family"]][c["outcome"]] += 1

    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "python": platform.python_version(),
              "platform": platform.platform(), "seconds": seconds, "totals": {**totals, "tests": len(cases)},
              "by_family": {k: dict(v) for k, v in by_family.items()},
              "routes": [{"route": f"{m} {p}", "access": access[(m, p)],
                          "cells": {col: cell(cells[f"{m} {p}"][col]) for col in columns}} for m, p in routes],
              "tests": cases}
    (OUT / "security_tests.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    md = ["# Security test coverage", "",
          f"Generated by `python scripts/security_report.py` on {report['generated_at']} (Python {report['python']}, "
          f"{platform.system()}), {seconds} s.", "",
          f"**{len(cases)} tests: {totals['passed']} passed, {totals['failed']} failed, {totals['error']} errors, "
          f"{totals['skipped']} skipped.**", "",
          "Suites: `backend/tests/test_security.py`, `backend/tests/test_audit_log.py`, `backend/tests/test_artifact_integrity.py`, "
          "`ml/tests/test_pii.py`, `ml/tests/test_registry.py`. Token, role and ownership tests run without the AI engines "
          "(authorization happens before any model is used); input-abuse and prompt-injection tests run against the real "
          "engines and are skipped when the synthetic world is not on disk (e.g. CI).", "",
          "| Family | passed | failed | skipped |", "|---|---|---|---|"]
    for fam, v in sorted(by_family.items()):
        md.append(f"| {fam} | {v.get('passed', 0)} | {v.get('failed', 0) + v.get('error', 0)} | {v.get('skipped', 0)} |")
    md += ["", "## Route x test matrix", "",
           "Every route of the running app (`app.routes`), its access rule, and the outcome of each test against it. "
           "Token columns: the request carries that kind of bad token and must get 401. Role columns: allowed roles must "
           "not get 401/403, other roles must get 403. Ownership: a customer/agent token for someone else's id gets 403 "
           "(ops may read). Input abuse: SQL-injection-like ids, path traversal, null bytes, 100 KB text, NaN/Infinity/huge "
           "or negative amounts must give 4xx, never 5xx. `-` = not applicable.", ""]
    short = {"missing_token": "no token", "wrong_scheme": "Basic auth", "malformed": "malformed", "bad_signature": "bad sig",
             "expired": "expired", "alg_none": "alg none", "alg_hs512": "alg HS512", "unknown_kid": "unknown kid",
             "missing_kid": "no kid", "no_exp_claim": "no exp", "issued_in_future": "future iat", "forged_role": "forged role"}
    head = ["route", "access"] + [short.get(c, c) for c in columns]
    md += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in report["routes"]:
        md.append(f"| `{r['route']}` | {r['access']} | " + " | ".join(r["cells"][c] for c in columns) + " |")
    md += ["", "## Other security tests", "", "| Test | Outcome |", "|---|---|"]
    for c in other:
        label = c["name"] if len(c["name"]) < 110 else c["name"][:107] + "..."
        md.append(f"| `{c['suite']}::{label}` | {c['outcome']} |")
    failed = [c for c in cases if c["outcome"] in ("failed", "error")]
    if failed:
        md += ["", "## Failures", ""] + [f"- `{c['name']}`: {c['message']}" for c in failed]
    (OUT / "security_tests.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(cases)} tests: {totals} -> {OUT / 'security_tests.md'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
