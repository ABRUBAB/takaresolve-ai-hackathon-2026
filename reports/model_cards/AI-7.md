# Model card — AI-7 Grounded Brief

*Notebook `NB07` · code commit `—` · results `reports/metrics_ai7.json` · synthetic data only.*

| | |
|---|---|
| Task | Short Bangla and English explanation that only restates the evidence the other AIs produced. |
| Inputs | Structured evidence (reasons, rules, case facts) + retrieved policy cards. |
| Model | Gemini API (structured JSON output) with a deterministic validator and a template fallback; policy cards retrieved by embedding similarity. |
| Baseline | Template text built directly from the evidence. |
| Uncertainty | Inherits the upstream state; must say "not sure" when the case is not sure. |
| Explanation | Cites evidence ids and policy-card ids. |
| Intended use | Customer, agent and analyst screens. |
| Out of scope | Any decision; the language model never decides anything. |

## Measured results (test data the model never saw)

- Not measured yet: run `NB07`.

## Limitations

Measured on synthetic evidence only; the validator rejects new numbers, links, phone numbers, certainty claims and contradictions.
