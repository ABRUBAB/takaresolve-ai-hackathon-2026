# Model card — AI-7 Grounded Brief

*Notebook `NB07` · code commit `393877746d` · results `reports/metrics_ai7.json` · synthetic data only.*

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

- Language model: {'model': 'gemini-3.5-flash-lite', 'fallback_models': ['gemini-3.5-flash', 'gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-2.5-flash-lite'], 'calls': 194, 'cache_hits': 0, 'failures': 0, 'paused_models': ['gemini-3.5-flash', 'gemini-3.8-flash']}; retrieval: tfidf; 140 briefs and 30 prompt-injection tests.
- Validator pass rate of Gemini output: 97.9%; template fallback rate: 2.1%.
- Shown text valid: 100.0%; injection attacks that reached a user: **0.0%** (raw model output before the validator: 10.0%).

## Limitations

Measured on synthetic evidence only; the validator rejects new numbers, links, phone numbers, certainty claims and contradictions.
