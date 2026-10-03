# artifacts/

Small exported model files (LightGBM text dumps, calibrators, conformal tables, precomputed forecasts, briefs cache).
Large pretrained weights (BGE-M3, Chronos-2) are only used inside the notebooks and are never committed; the API does not need them.
Every file is listed in `manifest.json` with its size, SHA-256, the notebook that wrote it and that run's code commit (written by `scripts/finalize.py`).
