# Model registry: integrity, approval, rollback

`artifacts/registry.json` records which version of each model the API serves (AI-1 to AI-7, plus the homepage data
asset `web`). For every version it stores:

| Field | Meaning |
|---|---|
| `version` | e.g. `v1` |
| `status` | `approved` (may be served), `candidate` (registered, waiting for review), `retired` (rolled back or replaced) |
| `files` | every file's path, size and **SHA-256** |
| `data_version` | hash of the synthetic world the model was trained on |
| `notebook`, `code_commit` | the Kaggle notebook that produced it and that run's code commit |
| `metrics` | pointer to the evaluation report (`reports/metrics_aiN.json`) plus that report's SHA-256 |
| `model_card` | `reports/model_cards/AI-N.md` |
| `approved_by`, `approved_at`, `notes` | who approved it, when, and why |

`active` names the served version. `history` is an append-only list of every `init`, `register`, `approve`,
`activate` and `rollback`, with who did it and when. The current models are `v1`, approved by "team (phase-1
release)" with the time of the release commit.

## What the API does at startup

Before it loads any model, `state.load()` runs `uvera_ml.registry.verify(MODEL_DIR)`, which checks four things:

1. Every model's active version has status **approved**.
2. Every file of that version exists, and its **SHA-256 matches** the registry.
3. `manifest.json` lists the same hash. A manifest written later (artifacts rebuilt without a registry update) means
   the files are **stale**.
4. No file in the manifest is missing from the registry.

If any check fails, the API **fails closed**. It loads no model and logs `ARTIFACT INTEGRITY CHECK FAILED: <file>
(<problem>)`. `/v1/health/ready` returns **503** like this:

```json
{"status": "failed", "reason": "Model artifact integrity check failed: ...",
 "bad_files": [{"model": "ai1", "path": "ai1/model.txt", "problem": "sha256 mismatch: file changed, stale or tampered"}],
 "models": {"ai1": {"version": "v1", "status": "approved", "verified": false}, "ai2": {"...": "..."}}}
```

Every model endpoint answers 503 as well. When the check passes, `/v1/health/ready` and `/v1/meta` (field
`model_registry`) list each model's version, status and `verified: true`. `ARTIFACT_VERIFY=warn` serves anyway and
reports `verified: false`. It exists for local development with dev-built artifacts only. Keep the default (`strict`)
everywhere else.

Why the API fails closed for every model, not only the bad one: the demo scenarios and the case linker combine
several models. Serving half a pipeline would show customers mixed results.

## Commands

```powershell
.venv\Scripts\python scripts\model_registry.py status            # table: active version, status, verified, approver
.venv\Scripts\python scripts\model_registry.py verify            # exit 1 and a list of bad files if anything fails
.venv\Scripts\python scripts\model_registry.py history ai1

# a retrained model: register (candidate) -> approve (a named person) -> activate (served after the next restart)
.venv\Scripts\python scripts\model_registry.py register ai1 --from D:\new_ai1 --version v2 --by "Name" --metrics reports/metrics_ai1.json
.venv\Scripts\python scripts\model_registry.py approve ai1 v2 --by "Reviewer" --notes "AUC, calibration and fairness slices checked"
.venv\Scripts\python scripts\model_registry.py activate ai1 v2 --by "Reviewer"

# something goes wrong in production: serve the previous approved version again
.venv\Scripts\python scripts\model_registry.py rollback ai1 --by "On-call" --reason "false-positive spike"
```

- `register` copies the files to `artifacts/_versions/<model>/<version>/` and records their hashes. The new version is
  a candidate and **cannot be served** (`activate` refuses it, and so does the startup check if someone edits the
  registry by hand).
- `approve` checks the stored files against their hashes again, so a file changed after registration cannot be approved.
- `activate` archives the current files to `_versions/<model>/<current>/`, copies the approved version into
  `artifacts/<model>/`, updates `manifest.json`, then verifies the result.
- `rollback` activates the previous approved version and marks the bad one `retired`. The restored files are
  byte-identical to the original release (`ml/tests/test_registry.py` checks the hashes).
- Restart the API after `activate` or `rollback`. Models are loaded once, at startup.
- `scripts/finalize.py` skips `registry.json` and `_versions/` when it rewrites the manifest. If new notebook results
  are copied in, the startup check reports them as stale until they are registered and approved, which is intended.

## Tests

| Test | What it proves |
|---|---|
| `backend/tests/test_artifact_integrity.py` | Copies `artifacts/` to a temp folder and points `MODEL_DIR` at it. One flipped byte in `ai1/model.txt` gives ready **503** naming exactly that file, and `/v1/cases` gives 503. Restoring the byte gives **200**. Also covers a missing file, an unapproved active version, a stale manifest, a missing registry and warn mode |
| `ml/tests/test_registry.py` | A tampered archive cannot be approved, a candidate cannot be activated, and register -> approve -> activate -> rollback restores v1 byte for byte. Also the CLI exit codes |
| `scripts/failure_recovery_test.py` (part B) | The same check on a **real uvicorn process**: tampered copy gives 503 with `bad_files=["ai1/model.txt"]` within seconds, and the restored copy gives 200 with every model verified (`reports/security/failure_recovery.md`) |

## Limits (honest)

The registry sits next to the files it protects. It catches accidents, stale or partial copies and tampering by
anyone who cannot also rewrite `registry.json`. It does **not** stop an attacker with write access to the whole
artifacts folder. Production signs the registry, for example a KMS/HSM-held key or Sigstore/cosign signatures checked
at startup. It also keeps artifacts in write-once object storage and records approvals in a separate system with
two-person review. See `docs/security.md`.
