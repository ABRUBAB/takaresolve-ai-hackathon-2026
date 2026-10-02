# Production path

| Stage | What happens | Exit criterion |
|---|---|---|
| 1. Shadow mode | APIs score real (governed, anonymised) traffic; nothing is shown to customers | Calibration and alert rates match expectations; no latency impact |
| 2. Recalibrate | Retrain on governed labels; refit isotonic + conformal; recheck fairness slices | Coverage near target in every slice |
| 3. A/B holdout | Pause Check shown to a small treatment group | Measured loss reduction and complaint rate vs control |
| 4. Operations pilot | Case Linker + briefs for a few analysts | Minutes per case and deadline compliance improve |
| 5. Scale | Gradual rollout, monitoring, quarterly model review | Stable metrics, audit-ready records |

**Integration points:** wallet send-money flow (Pause Check), agent app home (liquidity, QR view), operations case tool
(linked cases, dispute clock). All models sit behind versioned REST APIs, and business rules live in configuration.
