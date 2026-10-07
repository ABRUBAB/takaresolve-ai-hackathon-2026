# Static security scans

Run on 2026-10-07 on the working tree (Windows 11, Python 3.12.5, `.venv`). The scanners are development tools only
(`pip install bandit pip-audit detect-secrets`), not runtime dependencies. Raw outputs are next to this file.

| Scan | Command | Result |
|---|---|---|
| Code (SAST) | `python -m bandit -r backend/app ml/uvera_ml -f json -o reports/security/bandit.json` | 5,942 lines. First run: 1 high, 5 medium, 5 low. 2 medium fixed; now **1 high, 3 medium, 5 low**, all reviewed below (no exploitable issue) |
| Dependencies (pinned) | `python -m pip_audit -r constraints.txt` | 12 packages (the pins and their dependencies): **no known vulnerabilities** (`pip_audit_constraints.json`) |
| Dependencies (installed) | `python -m pip_audit --skip-editable --vulnerability-service osv` | 80 installed packages: **no known vulnerabilities** (`pip_audit_env.json`). The PyPI advisory service timed out, so the OSV database was used |
| Secrets, full git history | `python scripts/secrets_scan.py` | 94 commits on all branches, 111,377 added lines, plus 400 working-tree files. **0 high-confidence findings.** 6 values flagged for review: test values, documentation placeholders and one demo PIN (below) |
| Secrets, working tree | `python -m detect_secrets scan` (generated data files excluded) | 54 "Hex High Entropy String" hits, all in `reports/*.json`. Every one is a SHA-256 data hash or a git commit id (`uvera_commit`, `hashes.*`), not a secret |

## bandit findings

| Severity | Rule | Location | Verdict |
|---|---|---|---|
| Medium | B608 SQL built from a string | `backend/app/db/__init__.py` (2, new audit-chain code) | **Fixed**: the column lists were built from a constant tuple, now the queries are plain literals. All values already used `?` parameters. A test stores a `DROP TABLE` string as text, and the audit chain still verifies afterwards |
| High (medium confidence) | B613 bidirectional control characters in source | `ml/uvera_ml/serving/normalize.py:13` | **False positive.** The characters are the data of the AI-2 defence that *removes* invisible and bidi characters from scam texts. They sit inside a string literal and never change how the code is shown. Recommended: write them as `‪`-style escapes so code-review tools do not flag the file (owner: AI-2 adversarial-text code) |
| Medium | B108 hard-coded `/tmp` path | `ml/uvera_ml/models/ai7.py:36` (twice) | Accepted. This is an offline notebook helper that **reads** a Kaggle world cache when one exists. It writes nothing, and the API never uses it |
| Medium | B310 `urllib.urlopen` | `ml/uvera_ml/sim/text.py:214` | Accepted. It downloads the public UCI SMS-spam set from a fixed `https://` constant, only for an evaluation notebook. No user input reaches the URL |
| Low | B107 "hard-coded password" | `security.py:67` (empty default argument), `gemini.py:28` (the *name* of the environment variable) | False positives |
| Low | B110 try/except/pass | `gemini.py:43` (an optional Kaggle-secrets import), `serving/briefs.py:54` (the LLM fails, so the template is used, which is the documented fallback) | Accepted, by design. Template use is counted in `/v1/metrics/summary` |
| Low | B311 `random` | `ml/uvera_ml/sim/text.py:133` | Synthetic-data generation, not used for anything security-related |

## Secrets scan (scripts/secrets_scan.py)

How it works: every added line of every commit on every branch (`git log -p --all`) is checked, and so is every
tracked or untracked, non-ignored file. The high-confidence rules look for Google/Gemini API keys (`AIza...`), AWS keys,
GitHub, Slack, OpenAI/Anthropic and Hugging Face tokens, private-key blocks, JWTs and Kaggle `key` JSON. Notebooks
(including their outputs) and `package-lock.json` are checked with these rules only. Generic `password=`/`secret=`/
`token=`/`pin=` assignments are listed for review. The report never contains a secret value: each finding is a rule,
a file, a commit and the first 12 hex characters of the value's SHA-256 (`secrets_scan.json`).

Result: **no API key, token, private key or JWT has ever been committed.** Items to review:

| File | What | Verdict |
|---|---|---|
| `backend/tests/test_security.py` (2) | Test keyrings built from repeated letters (`"o" * 40`) | Test-only values |
| `docs/security.md:13`, `reports/security/bandit.json` | The `kid:secret` format placeholder in the docs; bandit's own finding text naming the `GEMINI_API_KEY` variable | Documentation, not secrets |
| `backend/app/core/config.py:31`, `backend/tests/test_study.py:16` (same value) | Default `STUDY_RESULTS_PIN` for the study results page | **Low risk, recommend a change.** It only protects the aggregate, anonymous usability-study results (ops tokens also work). For any public deployment, set `STUDY_RESULTS_PIN` in the environment and remove the default from the code. (The PIN is not printed here.) |

`.env` is git-ignored and has never been committed. The Gemini key comes only from the `GEMINI_API_KEY` environment
variable or Kaggle Secret, and is never printed. JWT signing keys come from `JWT_KEYS` / `JWT_KEYS_FILE` (outside the
repository) or a random per-start key (see `docs/security.md`).

## Found and fixed while writing the tests (not by the scanners)

- **500 instead of 422 for non-finite numbers.** `{"amount": 1e309}` (or `NaN` / `Infinity` tokens) crashed FastAPI's own
  validation-error response, because the response could not serialise the rejected value. Fixed in
  `backend/app/core/errors.py`. The response shape is unchanged.
- **`"amount": true` was accepted as Tk 1** (pydantic lax mode). Booleans are now rejected for `amount` and `hour`.
- **Health polling used up the rate limit.** Requests to `/v1/health/*` were never limited, but they still counted
  against the caller's per-minute budget. A client that polled readiness then got 429 on its first real call (found by
  `scripts/failure_recovery_test.py`). Health probes are no longer counted. A regression test was added.
