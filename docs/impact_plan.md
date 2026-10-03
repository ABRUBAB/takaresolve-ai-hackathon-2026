# Business and customer impact plan

All values come from `reports/` (written by the notebooks). Money figures use transparent assumptions in
`configs/assumptions.yaml` and are reported as conservative / base / optimistic scenarios.

| Metric | Baseline | How it is measured |
|---|---|---|
| Scam loss prevented at the same alert rate | Rule baseline (large amount + new receiver) | Test split; warned customers stop with an assumed follow rate (0.3 / 0.5 / 0.7) |
| False alerts per 1,000 normal transfers | Rule baseline | Test split at the frozen red threshold |
| QR misuse caught (precision@k per week) | Peer z-score only | Test merchants, including the unseen family D |
| Agent days short of cash + forecast error | Usual cash on hand; same extra cash spread evenly; seasonal-naive | Rolling-origin backtest (test weeks) |
| Customer shortfall warnings | Historical low-balance frequency | Rolling-origin backtest, Brier score |
| Analyst items per scam | One item per alert | Linked cases vs alerts (AI-6) |
| Unsafe generated text shown to users | — | Prompt-injection test set (AI-7) |

**Limits:** simulated follow rates and synthetic behaviour are assumptions, not production evidence. Real impact would be
measured in a shadow-mode pilot and an A/B holdout (see `production_path.md`).
