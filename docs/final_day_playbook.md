# Extension points (fast, safe changes)

| Change | Where | Typical time |
|---|---|---|
| New scam type or QR pattern | `configs/patterns.yaml` + scenario YAML; retrain NB01 / NB05 | 30–60 min |
| Alert budget or risk tiers | `configs/thresholds.yaml` | 5 min |
| New dispute rule or deadline | `configs/rules/dispute.yaml` | 10 min |
| New action wording or human-review rule | `configs/rules/actions.yaml` | 10 min |
| New explanation text or language | `ml/uvera_ml/xai/reasons.py`, policy cards | 20 min |
| New metric or export | `ml/uvera_ml/eval/` + Trust Center | 30–45 min |
| Swap a model | model adapter + feature flag | 15 min + training |

Every change: issue → small commits with a test → docs updated → pushed.
