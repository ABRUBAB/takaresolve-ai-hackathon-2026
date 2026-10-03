# Model card — AI-4 Agent Liquidity Copilot

*Notebook `NB04` · code commit `856988681c` · results `reports/metrics_ai4.json` · synthetic data only.*

| | |
|---|---|
| Task | How much cash an agent should hold each day for a 90%-safe day. |
| Inputs | Daily cash-out demand per agent + the same calendar covariates as AI-3. |
| Model | Same three forecasters as AI-3; the winner on validation pinball loss is used. Cash to hold = the 90% forecast. |
| Baseline | Seasonal-naive forecast; the agent's usual cash on hand (1.5 × average daily cash-out, an assumption); the same extra cash spread evenly. |
| Uncertainty | 10/50/90% quantile bands; day-level stock-out probability from validation residuals (shown for transparency only). |
| Explanation | The forecast band and the extra cash above the usual amount. |
| Intended use | Planning cash top-ups. No yes/no alarm is shown. |
| Out of scope | Automatic cash movements or limits on agents. |

## Measured results (test data the model never saw)

- Winner on validation: **lightgbm_quantile**. Test backtest:
  - chronos2: MASE 0.608, pinball 2,324, 80% coverage 0.741
  - lightgbm_quantile: MASE 0.604, pinball 2,281, 80% coverage 0.770
  - seasonal_naive: MASE 0.931, pinball 3,732, 80% coverage 0.807
- Validation backtest (chooses the winner; busier weeks):
  - chronos2: MASE 0.919, pinball 3,300, 80% coverage 0.732
  - lightgbm_quantile: MASE 0.899, pinball 3,186, 80% coverage 0.783
  - seasonal_naive: MASE 1.252, pinball 4,861, 80% coverage 0.696
- Days short of cash, usual cash on hand: **21.0%** (mean cash Tk 15,544).
- Days short of cash, hold the 90% forecast (served): **12.6%** (mean cash Tk 20,463).
- Days short of cash, same extra cash spread evenly: **12.9%** (mean cash Tk 20,463).
- Days short of cash, seasonal-naive 90% level: **6.2%** (mean cash Tk 31,551).
- Picking the two riskiest days of an agent's week: precision 22.8% vs chance 21.0% → no day is flagged.
- Ranking agents most at risk each week (top 20%): precision 27.4% vs history 20.4%.
- Best possible forecast (a simulated forecaster that knows every balance and mule cash-out on the day): test MASE 0.579, pinball 2,162. UVERA reaches **92.5%** of the possible improvement over seasonal-naive; the rest is chance that no model can predict.

## Limitations

Which day of an agent's week runs short could not be predicted better than chance, so no day is flagged; a flat top-up with the same total cash performs about as well as the forecast amount in this synthetic world.
