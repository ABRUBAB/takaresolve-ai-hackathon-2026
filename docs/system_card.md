# AI system card — UVERA

**What it is:** decision support for mobile-money customers, agents and operations staff: seven AI components behind one
API and one website. Measured results: [`reports/summary.md`](../reports/summary.md); one card per model:
[`reports/model_cards/`](../reports/model_cards/README.md); data: [`data_card.md`](data_card.md).

## Intended use
- **Customers:** a pause with reasons before a risky transfer, a check of suspicious messages, a 7-day cash-flow view.
- **Agents:** cash to hold for a 90%-safe day; QR misuse pressure at **zone level only** (no shop names).
- **Operations:** linked cases with evidence, a grounded brief and a dispute-deadline clock.

**Not for:** automatic approval or denial of money movement, automatic merchant caps, lending or credit decisions.

## Human oversight
- The customer is **never blocked**: every pause offers wait, verify, ask someone, or continue anyway.
- A hold on a large high-risk transfer, a merchant cap or an escalation needs a staff action **with a written reason**,
  stored in the audit log (`review_action`, `audit_log` tables).
- Business rules live in configuration (`configs/rules/`), never inside a model.

## What users see, labelled
Every screen labels its outputs as **model estimate**, **business rule**, **generated wording** or **assumption**, and a
"Behind the screen" panel shows the raw model output (score, calibrated probability, conformal set, unusual-input flag,
exact TreeSHAP weights, rules fired, brief source, trace id).

## Uncertainty
Calibrated probabilities (isotonic or validation residuals), Mondrian conformal sets at 90%, and a novelty check. When
the evidence is mixed or the input is unusual, the answer is **"not sure — a person will check"**, not a guess.

## The language model
Gemini (structured JSON output) only rewrites evidence the models produced. A deterministic validator rejects new
numbers, unknown evidence or policy-card ids, links, phone numbers, certainty claims ("100% safe") and text that
contradicts the risk level; the template text is shown instead. Untrusted message text is passed as quoted data, never as
instructions; prompt-injection attacks are part of the NB07 test set. Only synthetic data is ever sent to Gemini.

## Failure modes and what the user sees
| Failure | Detection | What the user sees |
|---|---|---|
| Input unlike training data | Novelty flag | "Not sure" → a person checks |
| Conflicting evidence | Conformal set holds both labels | "Not sure" → a person checks |
| Model error | Exception in the scoring path | "Basic check only" (transparent rule), marked *degraded* |
| API offline or waking up | Health check, network error | Recorded real responses for the demo scenarios ("Recorded demo" badge) |
| Language model error, quota or invented text | Validator, timeouts | Template text, labelled |
| New scam or disguise style | Held-out family tests; anomaly component in AI-5 | Grey "needs review" state |
| Too many requests | Rate limit per visitor | Recorded response where available |

## Known limits
- All data is synthetic; scam patterns were designed by the team (see the data card). Real deployment needs governed
  data, recalibration and a shadow-mode pilot ([`production_path.md`](production_path.md)).
- AI-2 drops sharply on real English advertising spam (UCI), so real-world text performance is not proven.
- AI-4 cannot tell which day of an agent's week runs short better than chance, so no day is flagged.
- AI-5 catches a never-seen disguise type far less often than the known ones.
