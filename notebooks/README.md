# UVERA notebooks — one notebook per AI

These Kaggle notebooks train and evaluate every AI component. They are **thin**: all logic lives in the tested
Python package [`ml/uvera_ml`](../ml/uvera_ml), so the notebooks only orchestrate, show results and package outputs.

| Notebook | AI | Accelerator | Internet / secret | Extra input | Runtime* |
|---|---|---|---|---|---|
| [`NB00_synthetic_world`](NB00_synthetic_world.ipynb) | Synthetic world + data card + leakage guard | CPU | On | — | 5–10 min |
| [`NB01_ai1_pause_check`](NB01_ai1_pause_check.ipynb) | AI-1 Pause Check (scam risk before Confirm) | CPU | On | — | 20–40 min |
| [`NB02_ai2_scam_text`](NB02_ai2_scam_text.ipynb) | AI-2 Scam Text Sentinel (Bangla / Banglish / English) | GPU T4 ×2 | On · `GEMINI_API_KEY` | [UCI SMS Spam Collection](https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset) | 45–90 min |
| [`NB03_ai3_cashflow_guardian`](NB03_ai3_cashflow_guardian.ipynb) | AI-3 Cash-Flow Guardian (forecast + shortfall risk) | GPU T4 ×2 | On | — | 20–40 min |
| [`NB04_ai4_agent_liquidity`](NB04_ai4_agent_liquidity.ipynb) | AI-4 Agent Liquidity Copilot (cash stock-out risk) | GPU T4 ×2 | On | — | 20–40 min |
| [`NB05_ai5_qr_shield`](NB05_ai5_qr_shield.ipynb) | AI-5 QR Shield (Bangla QR used as cash-out) | CPU | On | — | 10–20 min |
| [`NB06_ai6_case_linker`](NB06_ai6_case_linker.ipynb) | AI-6 Case Linker (alerts → evidence-backed cases) | CPU | On | AI-1 + AI-5 results in repo | 5–15 min |
| [`NB07_ai7_grounded_brief`](NB07_ai7_grounded_brief.ipynb) | AI-7 Grounded Brief (Gemini + validator) | CPU | On · `GEMINI_API_KEY` | AI-1 + AI-6 results in repo | 20–40 min |
| [`NB99_evaluation`](NB99_evaluation.ipynb) | Evaluation, fairness, summary for the Trust Center | CPU | On | all `reports/metrics_ai*.json` | 2–5 min |

\*Estimates on Kaggle; actual times are written to `reports/versions_nbXX.json`.

## Reproduce a result
1. Kaggle → **New Notebook → File → Import Notebook** → upload the `.ipynb`.
2. Settings: accelerator as above, **Internet On**. For NB02/NB07 add a Kaggle Secret named `GEMINI_API_KEY` (free key from Google AI Studio). Without it, those notebooks still run with template text only.
3. Optional: set `REF` in cell 1 to a commit hash for an exact reproduction.
4. **Save Version → Save & Run All (Commit)** (background run: no idle timeout; 12-hour session cap).
5. Download `outputs/NBxx_outputs.zip` from the **Output** tab and unzip it at the repo root — it contains `artifacts/` and `reports/`.

## Order
NB00–NB05 are independent (the synthetic world is regenerated from a fixed seed in every notebook and checked by hash).
NB06 uses AI-1 and AI-5 results, NB07 uses AI-1 and AI-6 results, NB99 runs last. If an input is missing, NB06/NB07 run a
quick, clearly-labelled re-training instead.

## Rules every notebook follows
- Fixed seeds; library versions and the code commit are saved with the results.
- Time-based and entity-disjoint splits; StratifiedGroupKFold inside the training window; the test set is used once.
- Thresholds are chosen on validation data and frozen before testing.
- Only synthetic data or open-licensed public data. No real customer data.
