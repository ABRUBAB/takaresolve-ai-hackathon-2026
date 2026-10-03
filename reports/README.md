# reports/

Measured results only, written by the Kaggle notebooks. **No number is shown on the website, in the README or in the
report unless it comes from a file here.**

| File | Written by | Contents |
|---|---|---|
| `summary.md`, `metrics.json` | NB99 (or `scripts/finalize.py`, same code) | Headline results of all seven AIs, fairness, run commits |
| `model_cards/` | NB99 | One model card per AI, generated from the files below |
| `fairness.md` | NB99 | Error rates by zone, channel, account age, language, segment and shop size |
| `metrics_ai1.json` … `metrics_ai7.json` | NB01 … NB07 | Every metric of one AI (test, cross-validation, baselines, calibration, uncertainty) |
| `ai1_cv_folds.csv`, `ai2_cv_folds.csv`, `ai5_cv_folds.csv` | NB01, NB02, NB05 | Per-fold, per-seed cross-validation scores |
| `ai3_backtest.csv`, `ai4_backtest.csv` | NB03, NB04 | Rolling-origin backtest per origin and model |
| `data_card_stats.json`, `world_meta.json`, `leakage_check_ai1.json` | NB00 | Synthetic-world statistics, hashes, leakage guard |
| `versions_nbXX.json` | every notebook | Python and library versions, GPU, and the exact code commit of the run |
| `figures/` | notebooks | Calibration curves, PR curves, SHAP importance, forecast examples |
