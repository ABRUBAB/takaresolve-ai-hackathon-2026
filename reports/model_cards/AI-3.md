# Model card — AI-3 Cash-Flow Guardian

*Notebook `NB03` · code commit `856988681c` · results `reports/metrics_ai3.json` · synthetic data only.*

| | |
|---|---|
| Task | 7-day forecast of a customer's net cash flow and the chance the balance ends the week below a safety floor. |
| Inputs | Daily money in and out per customer + calendar covariates (weekday, day of month, salary week, month end, festival). |
| Model | Chronos-2 (zero-shot foundation model), LightGBM-quantile (lags 7–28 days plus the same calendar day 1 and 2 months back, because pay day and bill day repeat monthly) and seasonal-naive, compared by rolling-origin backtest; the winner is chosen on validation pinball loss. The live API serves LightGBM-quantile (CPU-only server). |
| Baseline | Seasonal-naive forecast; historical low-balance frequency for the warning. |
| Uncertainty | 10/50/90% quantile bands; the shortfall probability comes from the empirical distribution of validation residuals. |
| Explanation | Heaviest spending weeks; the forecast band itself. |
| Intended use | A weekly heads-up and savings plans that leave room for a bad month. Nothing moves automatically. |
| Out of scope | Lending or credit scoring. |

## Measured results (test data the model never saw)

- Winner on validation: **lightgbm_quantile**. Test backtest:
  - chronos2: MASE 0.396, pinball 457, 80% coverage 0.814
  - lightgbm_quantile: MASE 0.383, pinball 442, 80% coverage 0.796
  - seasonal_naive: MASE 0.716, pinball 795, 80% coverage 0.838
- Validation backtest (chooses the winner; its weeks include pay days):
  - chronos2: MASE 0.855, pinball 925, 80% coverage 0.775
  - lightgbm_quantile: MASE 0.752, pinball 765, 80% coverage 0.801
  - seasonal_naive: MASE 1.423, pinball 1,521, 80% coverage 0.707
- Shortfall probability (test): PR-AUC 0.500 vs history 0.390; Brier 0.143 vs 0.163; ECE 0.031.

## Limitations

Synthetic cash flows. The warning has modest skill over history; the forecast itself clearly beats seasonal-naive.
