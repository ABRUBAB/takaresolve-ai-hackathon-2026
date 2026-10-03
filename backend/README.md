# UVERA API

FastAPI service for the website. Routes live in `app/api/v1/` (customer, agent, operations, meta, health). The model engines
come from the `uvera_ml.serving` package; business rules stay in `configs/rules/*.yaml`, never inside a model.

```bash
pip install -c ../constraints.txt -e ../ml -e .[dev]
uvicorn app.main:app --port 8000      # the AI engines warm up in the background (~45 s)
pytest -q
```

- Artifacts: `artifacts/` (official Kaggle runs) first, then `_outputs/dev/` (local build from `scripts/build_dev_artifacts.py`).
- Every response carries `trace_id`, `model_version`, `data_version` and `synthetic_data: true`.
- Docker: `docker build -f backend/Dockerfile -t uvera-api .` from the repository root. Deployment: `docs/deploy.md`.
