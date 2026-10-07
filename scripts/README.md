# scripts/

| Script | What it does |
|---|---|
| `add_result.py` | Adds a Kaggle result zip (`NBxx_outputs.zip`) to `artifacts/` and `reports/` and commits it |
| `finalize.py` | After the last results: summary + model cards, records the API responses for the website (in-process), copies figures, writes the artifact manifest and the README results table, commits |
| `export_snapshot.py` | Records the website's API responses from an API that is already running (`--api http://127.0.0.1:8000`) |
| `export_web_assets.py` | Copies the homepage world sample and the notebook figures into the website |
| `smoke_api.py` | End-to-end check of every endpoint and demo scenario against a running API |
| `start_api.ps1` | Starts the API on Windows (127.0.0.1:8000, or `-Port`) and restarts it if it stops |
| `build_dev_artifacts.py` | Quick local copy of every model, for development before the notebooks have run |
| `model_registry.py` | Model registry: `status`, `verify` (SHA-256 + approval), `register`, `approve`, `activate`, `rollback`, `history` (docs/model_registry.md) |
| `rotate_jwt_key.py` | Makes a new JWT signing key and prints the new keyring line (never writes inside the repo) (docs/security.md) |
| `security_report.py` | Runs the security test suites and writes the route x test matrix to `reports/security/security_tests.md` |
| `secrets_scan.py` | Scans the whole git history and working tree for committed secrets (never prints one) |
| `failure_recovery_test.py` | Real processes: kills the API under `start_api.ps1` 3 times and measures recovery; tampered-artifact check |
