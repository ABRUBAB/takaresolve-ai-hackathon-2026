# AI System Card — UVERA

_Status: template — filled in during the hackathon from measured results only._

- **Intended use:** decision support for customers, agents and MFS operations staff. Not for autonomous approval/denial of money movement or lending.
- **Human oversight:** customers are never blocked; every hold, merchant cap or escalation needs an ops click + reason (audit log).
- **Output types shown in the UI:** model estimate · business rule · generated wording · assumption.
- **Uncertainty:** calibrated probability, conformal set, novelty flag → "not sure" → human review.
- **LLM:** Gemini writes text only from structured evidence; validator + template fallback; no tools, no actions.
- **Known failure modes and fallbacks:**

| Failure | Detection | What the user sees |
|---|---|---|
| Input unlike training data | Novelty flag | "Not sure" → a person checks |
| Conflicting evidence | Conformal set holds both labels | "Not sure" → a person checks |
| Model or API down | Health checks, timeouts | "Basic check only" (rule baseline) + banner |
| LLM error, quota or invented text | Validator, 429 / timeout | Fixed template text, labelled |
| New scam or disguise style | Held-out family tests, anomaly component | Grey "needs review" state |
| Synthetic-data bias | Fairness slices, stated limits | Limits written in the report |
