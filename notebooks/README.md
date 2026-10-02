# Kaggle notebooks — one notebook per AI

| Notebook | AI | Accelerator | Kaggle account |
|---|---|---|---|
| `NB00_synthetic_world.ipynb` | Synthetic World | CPU | K1 (P1) |
| `NB01_ai1_pause_check.ipynb` | AI-1 Pause Check | CPU | K2 (P1) |
| `NB02_ai2_scam_text.ipynb` | AI-2 Scam Text Sentinel | GPU T4 x1 | K3 (P2) |
| `NB03_ai3_cashflow_guardian.ipynb` | AI-3 Cash-Flow Guardian | GPU T4 x1 | K4 (P2) |
| `NB04_ai4_agent_liquidity.ipynb` | AI-4 Agent Liquidity Copilot | GPU T4 x1 | K4 (P2) |
| `NB05_ai5_qr_shield.ipynb` | AI-5 QR Shield | CPU | K2 (P1) |
| `NB06_ai6_case_linker.ipynb` | AI-6 Case Linker | CPU | K2 (P1) |
| `NB07_ai7_grounded_brief.ipynb` | AI-7 Grounded Brief (Gemini) | CPU + internet | K3 (P2) |
| `NB99_evaluation.ipynb` | Evaluation, Fairness & Packaging | CPU | K4 (P2) |

**How to run**
1. Turn on Internet (phone-verified account). For NB02/NB07 attach the `GEMINI_API_KEY` secret.
2. Set `REPO_COMMIT` to the commit you want to reproduce.
3. Attach the `uvera-world-v1` Dataset (from NB00) as input.
4. **Save Version → Save & Run All (Commit)** — background run, no 20-minute idle timeout, 12 h cap.
5. Download `artifacts/` + `metrics_*.json` and commit them to the repo (with the notebook version in `artifacts/manifest.json`).

Details: plan Sections O.0–O.8.
