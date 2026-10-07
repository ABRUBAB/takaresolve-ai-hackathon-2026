"""Secrets scan over the WHOLE git history (every added line of every commit on every branch) and the working tree.

    python scripts/secrets_scan.py            # prints a summary, writes reports/security/secrets_scan.json

Never prints a secret: a finding is reported as rule + file + commit + a short SHA-256 fingerprint of the match.
High-confidence rules (provider key formats, private keys, JWTs) fail the run; generic `password = ...`-style
assignments are listed for review (most are test values or code references).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "security"

HIGH = {
    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"),
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "openai_or_anthropic_key": re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{32,}"),
    "huggingface_token": re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}"),
    "kaggle_key_json": re.compile(r"\"key\"\s*:\s*\"[0-9a-f]{32}\""),
}
GENERIC = re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|pwd|token|jwt[_-]?secret|jwt[_-]?keys|access[_-]?key|"
                     r"study[_-]?results[_-]?pin|pin)\b[\"']?\s*(?::\s*[\w|\[\] ]+?\s*)?[:=]\s*[\"']([^\s\"']{6,})[\"']")
PLACEHOLDER = re.compile(r"(?i)^(change[-_]?me.*|x{6,}|\*{3,}|your[_-].*|<.*>|\$\{.*\}|example.*|placeholder|redacted|none|null|"
                         r"true|false|test.*|dummy.*|fake.*|secret|password|token)$")
SKIP_FILES = re.compile(r"\.(parquet|joblib|pt|npz|png|jpg|jpeg|webp|pdf|zip|db)$")  # binary
HIGH_ONLY = re.compile(r"(^|/)package-lock\.json$|\.ipynb$")  # big generated text: provider-format rules only


def fp(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def scan_text(path: str, text_lines, where: str, out: list) -> None:
    for lineno, line in text_lines:
        for rule, pat in HIGH.items():
            for m in pat.finditer(line):
                out.append({"severity": "high", "rule": rule, "file": path, "where": where, "line": lineno, "fingerprint": fp(m.group(0))})
        if HIGH_ONLY.search(path):
            continue
        for m in GENERIC.finditer(line):
            value = m.group(2)
            if PLACEHOLDER.match(value) or value.startswith(("os.", "settings.", "request.", "self.", "env", "{")):
                continue
            out.append({"severity": "review", "rule": f"assignment:{m.group(1).lower()}", "file": path, "where": where,
                        "line": lineno, "fingerprint": fp(value), "value_length": len(value)})


def history(out: list) -> dict:
    proc = subprocess.run(["git", "log", "-p", "--all", "--no-color", "-U0", "--no-ext-diff", "--format=commit %H"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    commit, path, added, n_lines, cur = None, None, [], 0, 0
    commits = set()

    def flush():
        if path and added and not SKIP_FILES.search(path):
            scan_text(path, added, f"commit {commit[:10]}", out)

    for line in proc.stdout.splitlines():
        if line.startswith("commit ") and len(line) == 47:
            flush()
            commit, path, added = line[7:], None, []
            commits.add(commit)
        elif line.startswith("+++ "):
            flush()
            path, added = (line[6:] if line.startswith("+++ b/") else None), []
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            cur = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            n_lines += 1
            added.append((cur, line[1:]))
            cur += 1
    flush()
    return {"commits": len(commits), "added_lines": n_lines}


def working_tree(out: list) -> dict:
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    n = 0
    for f in files:
        p = ROOT / f
        if SKIP_FILES.search(f) or not p.is_file() or p.stat().st_size > 20_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        n += 1
        scan_text(f, enumerate(text.splitlines(), 1), "working tree", out)
    return {"files": n}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    hist, tree = [], []
    h = history(hist)
    t = working_tree(tree)
    dedup = {}
    for f in hist + tree:
        dedup.setdefault((f["rule"], f["file"], f["fingerprint"]), {**f, "seen_in": []})["seen_in"].append(f["where"])
    findings = sorted(dedup.values(), key=lambda f: (f["severity"], f["rule"], f["file"]))
    for f in findings:
        f["seen_in"] = sorted(set(f["seen_in"]))[:5]
    rep = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "history": h, "working_tree": t,
           "rules_high": list(HIGH), "counts": dict(Counter(f["severity"] for f in findings)),
           "by_rule": dict(Counter(f["rule"] for f in findings)), "findings": findings,
           "note": "Values are never stored: fingerprint = first 12 hex of SHA-256 of the matched text."}
    (OUT / "secrets_scan.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"history: {h['commits']} commits, {h['added_lines']} added lines; working tree: {t['files']} files")
    print(f"findings: {rep['counts']}  by rule: {rep['by_rule']}")
    for f in findings:
        print(f"  [{f['severity']}] {f['rule']:<28} {f['file']}:{f['line']}  fp={f['fingerprint']}  in {', '.join(f['seen_in'][:2])}")
    return 1 if rep["counts"].get("high") else 0


if __name__ == "__main__":
    sys.exit(main())
