# Model card — AI-1 Pause Check

*Notebook `NB01` · code commit `4599b2e045` · results `reports/metrics_ai1.json` · synthetic data only.*

| | |
|---|---|
| Task | Scam risk of a draft person-to-person transfer, before the customer confirms it. |
| Inputs | 19 features known before the transfer: sender (9), receiver (6), moment (4). Leakage-guarded: no single feature separates scams with AUC above 0.80. |
| Model | LightGBM, chosen over logistic regression, XGBoost and CatBoost by StratifiedGroupKFold (5 folds × 5 seeds, grouped by sender). |
| Baseline | Rule: amount of Tk 5,000 or more to a receiver never paid before, at the same alert rate. |
| Uncertainty | Isotonic calibration; Mondrian conformal sets (90%); robust novelty flag. Both labels in the set (on a non-low score) or an unusual input → "not sure" → a person checks. |
| Explanation | Exact TreeSHAP contributions → top-3 reasons in Bangla and English (risk-raising, or what looked normal for a low-risk draft); counterfactual amount. |
| Intended use | Decision support inside the send-money flow. The customer is never blocked; a hold on a large high-risk transfer needs staff approval. |
| Out of scope | Automatic blocking, credit or account decisions; real customers without retraining on governed data. |

## Measured results (test data the model never saw)

- Test: 24,827 transfers from customers never seen in training, 181 scams.
- Scams caught at a 5% alert rate: **86.2%** (rule: 28.2%).
- PR-AUC 0.651 (rule 0.048); ROC-AUC 0.931.
- At the pause threshold: recall 75.7%, precision 38.5%, 8.9 false pauses per 1,000 normal transfers (rule 13.5).
- Calibration error (ECE) 0.002; Brier 0.004.
- Conformal coverage 94.2% (target 90%); shown as "not sure" to customers: 0.6%.

## Limitations

Synthetic data: scam families were designed by the team. 10% label noise and honest look-alikes reduce, but do not remove, the risk that real scams are harder.
