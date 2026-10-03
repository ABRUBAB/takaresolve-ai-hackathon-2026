# Model card — AI-3 Cash-Flow Guardian

*Notebook `NB03` · code commit `ef989c6b69` · results `reports/metrics_ai3.json` · synthetic data only.*

| | |
|---|---|
| Task | 7-day forecast of a customer's net cash flow and the chance the balance ends the week below a safety floor. |
| Inputs | Daily money in and out per customer + calendar covariates (weekday, day of month, salary week, month end, festival). |
| Model | Chronos-2 (zero-shot foundation model), LightGBM-quantile (lags 7–28 days) and seasonal-naive, compared by rolling-origin backtest; the winner is chosen on validation pinball loss. |
| Baseline | Seasonal-naive forecast; historical low-balance frequency for the warning. |
| Uncertainty | 10/50/90% quantile bands; the shortfall probability comes from the empirical distribution of validation residuals. |
| Explanation | Heaviest spending weeks; the forecast band itself. |
| Intended use | A weekly heads-up and savings plans that leave room for a bad month. Nothing moves automatically. |
| Out of scope | Lending or credit scoring. |

## Measured results (test data the model never saw)

- Winner on validation: **chronos2**. Test backtest:
  - chronos2: MASE 0.396, pinball 457, 80% coverage 0.814
  - lightgbm_quantile: MASE 0.383, pinball 442, 80% coverage 0.794
  - seasonal_naive: MASE 0.713, pinball 794, 80% coverage 0.840
- Shortfall probability (test): PR-AUC 0.509 vs history 0.377; Brier 0.139 vs 0.163; ECE 0.037.

## Limitations

Synthetic cash flows. The warning has modest skill over history; the forecast itself clearly beats seasonal-naive.
