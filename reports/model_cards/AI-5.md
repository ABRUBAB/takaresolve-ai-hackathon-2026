# Model card — AI-5 QR Shield

*Notebook `NB05` · code commit `59792ea847` · results `reports/metrics_ai5.json` · synthetic data only.*

| | |
|---|---|
| Task | Find shops whose Bangla QR payments look like disguised cash-out. |
| Inputs | 16 merchant-week features, most relative to shops of the same type, area and size (round amounts, bursts, payments right after a cash-in, wallet drain, one-time payers, …). |
| Model | Rank fusion: 70% LightGBM + 30% Isolation Forest. Disguise family D (rotating ring) is held out of training entirely. |
| Baseline | Peer z-score alone. |
| Uncertainty | Isotonic calibration; Mondrian conformal → grey "not sure, a person checks". |
| Explanation | Top reasons per shop and a peer comparison. |
| Intended use | Weekly review list for analysts (top 20 shop-weeks); agents see only zone-level totals. |
| Out of scope | Automatic merchant caps or closures; naming shops to agents. |

## Measured results (test data the model never saw)

- Test: 2,559 merchant-weeks, 179 disguised.
- Real cash-out shops among the 20 reviewed each week: **92.5%**.
- PR-AUC 0.787 on seen disguise types, 0.708 overall (peer z-score baseline 0.314).
- Honest round-price shops wrongly flagged: 5.9%; all honest shops: 10.2%.
- Calibration error 0.020; conformal coverage 92.1%.
  - recall, A_round_amount_atm: 87.8%
  - recall, B_split_under_limit: 84.4%
  - recall, C_cash_in_pass_through: 90.9%
  - recall, D_rotating_ring (never seen in training): 42.1%

## Limitations

The never-seen disguise type is caught far less often; fee leakage uses an assumed 1.5% cash-out fee inside the public 2026 range.
