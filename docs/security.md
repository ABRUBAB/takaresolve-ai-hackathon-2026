# Security: what the prototype does now, and what production adds

UVERA is a hackathon prototype on **synthetic data**. This page separates two things. First, the controls that are
implemented **and tested** in this repository, with the evidence. Second, what a real mobile-financial-services
deployment would add. Production controls are not claimed as done. See also `docs/threat_model.md` and
`docs/model_registry.md`.

## 1. Implemented and tested now

| Area | Control | Evidence |
|---|---|---|
| Authentication | Short-lived (12 h) HS256 JWTs. Every token must carry a known `kid`, `exp`, `iat`, `sub` and a valid role. `alg: none`, HS512 and other algorithms, unknown or retired keys, expired or future-dated tokens and forged roles all get **401** | `backend/tests/test_security.py`: 12 bad-token cases x 14 protected routes |
| Key rotation | Keyring `JWT_KEYS="kid:secret,kid:secret"` or `JWT_KEYS_FILE` (a file outside the repo). The first key signs and all listed keys verify, so rotation logs nobody out. A removed key gives 401. Keys shorter than 32 characters are refused at startup. `scripts/rotate_jwt_key.py` makes the new keyring line and refuses to write inside the repository | `test_key_rotation_old_key_verifies_until_retired`, `test_keyring_parsing_and_file`, `test_rotate_script_never_writes_inside_repo` |
| Authorization | Three roles (customer, agent, ops) per route. Customers and agents can read only their own records. Ops can read everything. Demo login is turned off with `DEMO_MODE=false` | Role matrix (14 routes x 3 roles) and 5 ownership tests. Every route is classified as public or protected, so a new unprotected route fails the suite |
| Input validation | Strict schemas (`extra="forbid"`), length caps, id patterns and range checks. SQL is always parameterised. Abuse inputs give **4xx, never 5xx**: SQL-injection-like ids, path traversal, null bytes, 100 KB text, NaN/Infinity/1e309, negative or boolean amounts | 94 input-abuse tests against the real engines. They found and fixed two bugs (non-finite numbers caused a 500; `true` was accepted as Tk 1) |
| Abuse limits | Per-client rate limit, 429 when exceeded. A forged `X-Forwarded-For` does not reset it. Health probes are never limited | `test_rate_limit_returns_429`, `test_health_polling_does_not_use_up_the_rate_limit` |
| CORS | Only the configured origins are echoed. No credentials. Only GET and POST | `test_cors_allows_only_configured_origins` |
| LLM safety (AI-7) | Untrusted text is passed only as a quoted data field. A validator checks every number, citation and banned phrase, with a template fallback. **PII is removed before any live LLM call**: Bangladesh phone numbers (`+8801...`, `01...`, Bangla digits), 10/13/17-digit NIDs, card numbers, emails, links and OTP codes become `[PHONE]`, `[NID]` and so on | `ml/tests/test_pii.py` (23 tests, English, Bangla and Banglish; checks the exact prompt the LLM would receive); prompt-injection tests on `/v1/text-check` and `/v1/pause-check` |
| Model integrity and governance | Every served file is pinned by SHA-256 in `artifacts/registry.json`, and each version has an approval status, approver and time. A missing, changed or stale file, or an unapproved version, means the API serves **no model** and readiness is 503 with the bad files listed. Versions go candidate -> approved -> active, and one command rolls back | `docs/model_registry.md`, `backend/tests/test_artifact_integrity.py`, `ml/tests/test_registry.py`, a real-process stale-artifact test |
| Audit trail | Each `audit_log` row stores `prev_hash` and `hash = sha256(prev_hash + canonical JSON)`. SQLite triggers abort any UPDATE or DELETE on `audit_log` and `review_action`. `GET /v1/ops/audit/verify` (ops role) recomputes the chain and returns the first broken row | `backend/tests/test_audit_log.py`: edits, deletions and re-hashed rows are all detected, the triggers come back on restart, and older databases are migrated |
| Resilience | A supervisor restarts the API after a crash. Clients get *connection refused* during the outage and 503 `warming_up` while models load, so requests never hang. The audit chain survives crashes | `scripts/failure_recovery_test.py`: 3 kills, all recovered without a human (`reports/security/failure_recovery.md`) |
| Supply chain and code | Pinned ML library versions. bandit, pip-audit and a full-history secrets scan were run, and their findings fixed or justified | `reports/security/security_scan.md` |

How to run everything:

```powershell
.venv\Scripts\python scripts\security_report.py          # all security tests -> reports/security/security_tests.md (+ .json)
.venv\Scripts\python scripts\failure_recovery_test.py    # real processes: crash recovery + stale artifact (about 6 min)
.venv\Scripts\python scripts\secrets_scan.py             # whole git history, never prints a secret
.venv\Scripts\python scripts\model_registry.py verify    # artifact hashes + approvals
```

## 2. Secrets: where they live

- **Never in the repository.** `.env` is git-ignored, `.env.example` holds only empty placeholders, and the
  full-history scan finds no committed key (`reports/security/security_scan.md`).
- **JWT signing keys** come from an environment variable or platform secret (`JWT_KEYS`), or from a file **outside**
  the repository (`JWT_KEYS_FILE`, owner-only permissions). On Windows the key can also live in the Credential
  Manager / DPAPI and be loaded into the variable at service start. With nothing set, a random key is made per start,
  which is fine for the demo because tokens are simply issued again.
- **Rotation:** run `scripts/rotate_jwt_key.py --current-file <file> --write <file>`, then restart. New tokens use the
  new key and old ones still verify. After 12 hours (the token lifetime), run it again with `--keep 0`. Tokens signed
  with the retired key now get 401.
- **The Gemini API key** comes only from `GEMINI_API_KEY` (an environment variable or Kaggle Secret) and is never
  printed. Only synthetic data is sent, and PII is removed first anyway.
- **Study PIN:** set `STUDY_RESULTS_PIN` in the environment for any public deployment. Do not rely on the code default.

## 3. What a production fintech deployment adds (not done here)

| Area | Prototype (this repo) | Production |
|---|---|---|
| Identity | Self-service demo login for synthetic personas | The provider's identity platform (OIDC), MFA for staff, device binding for customers, no self-service role tokens (`DEMO_MODE=false`) |
| Keys | Keyring in an environment variable or file, HS256 | Keys in an **HSM / cloud KMS** with automatic rotation. Asymmetric signing (ES256/RS256) so services verify without the signing key. Token revocation list |
| Audit | Hash chain plus SQLite triggers. Anyone who controls the file can rewrite the entire chain, and cutting rows off the end is only detected if the head hash was saved elsewhere | Append-only **WORM storage** (for example S3 Object Lock or immutable ledger tables). The head hash is anchored periodically outside the system. Logs are streamed to a **SIEM** with alerting and retained under Bangladesh Bank rules |
| Model governance | Registry with SHA-256, approval fields and rollback in a JSON file next to the artifacts | Signed artifacts (KMS or Sigstore), a model registry service (for example MLflow) with **two-person approval**, segregation of duties, independent model validation and champion/challenger releases |
| Data | Synthetic data only. PII removed before the LLM. Masked ids in logs | Data classification, encryption at rest and in transit (TLS everywhere, mTLS between services), tokenised account numbers, retention and deletion policies, data protection impact assessment, on-shore or approved LLM endpoint with a no-training agreement |
| Network | API on 127.0.0.1 behind a tunnel, application-level rate limit | WAF, DDoS protection, API gateway quotas per client, private networking, egress allow-list for the LLM |
| Testing | Automated tests above, bandit, pip-audit, secrets scan | Independent **penetration test** and red team, regular DAST/SAST in CI, dependency and container scanning with SBOMs, bug bounty, and **adversarial ML testing** at scale (evasion, poisoning, prompt injection) with sign-off before each model release |
| Operations | Single process with restart loop, about 60-100 s to recover on the demo PC | Several replicas behind a load balancer (no outage on a single crash), health-based rollout, on-call runbooks, disaster-recovery drills |
| Compliance | Documentation only | Bangladesh Bank MFS and ICT security guidelines, PCI DSS where cards are involved, regular audits |
