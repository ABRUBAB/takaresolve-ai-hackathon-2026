# artifacts/

Small exported model files (LightGBM text dumps, calibrators, conformal tables, precomputed forecasts, briefs cache).
Large weights (BGE-M3, Chronos-2) are **downloaded from Hugging Face at build time**, never committed.
Every file is listed in `manifest.json` with its SHA-256, training date, data version and notebook commit.
