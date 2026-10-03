# UVERA — measured results (synthetic data)

All results are on synthetic data: they show that the pipeline works, not real-world accuracy.

| AI | What is measured (test data the model never saw) | UVERA | Baseline |
|---|---|---|---|
| AI-1 Pause Check | Scams caught when 5% of transfers are flagged | 86.2% | 28.2% |
| AI-1 Pause Check | PR-AUC on customers never seen in training | 0.651 | 0.048 |
| AI-1 Pause Check | False pauses per 1,000 normal transfers | 8.9 | 13.5 |
| AI-1 Pause Check | Calibration error (ECE) | 0.002 | — |
| AI-2 Scam Text | Verdict PR-AUC, unseen writing style (served model: tfidf_lr) | 0.986 | — |
| AI-2 Scam Text | Scam-family macro F1, unseen writing style | 0.855 | — |
| AI-3 Cash-Flow | Forecast error, MASE (chronos2) | 0.396 | 0.713 |
| AI-3 Cash-Flow | 80% range holds the truth (target 0.80) | 0.814 | 0.840 |
| AI-3 Cash-Flow | Shortfall warning PR-AUC (vs history) | 0.509 | 0.377 |
| AI-4 Liquidity | Forecast error, MASE (lightgbm_quantile) | 0.604 | 0.931 |
| AI-4 Liquidity | Days short of cash: hold the 90% forecast (vs usual cash) | — | — |
| AI-5 QR Shield | Real cash-out shops among the 20 reviewed each week | 92.5% | — |
| AI-5 QR Shield | Honest round-price shops wrongly flagged | 5.9% | — |
| AI-5 QR Shield | Recall on a disguise type never seen in training | 42.1% | — |
| AI-6 Case Linker | Fewer items for analysts (alerts → cases) | — | — |
| AI-6 Case Linker | Real scam alerts inside the top 5 cases | — | — |
| AI-7 Grounded Brief | Prompt-injection attacks shown to users | — | — |

Baselines: AI-1 a simple rule (large amount to a new receiver) flagging the same number of transfers; AI-3/AI-4 seasonal-naive forecasts and historical frequencies; AI-4 'usual cash' = the agent's normal cash on hand.
Each AI's details are in [`model_cards/`](model_cards) and fairness slices in [`fairness.md`](fairness.md).
