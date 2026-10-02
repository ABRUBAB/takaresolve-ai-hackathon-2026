# Threat model

| Threat | Attacker | Asset | Prevention | Detection | Fallback |
|---|---|---|---|---|---|
| Prompt injection in a pasted SMS or note | Scammer / user | Brief text shown to customers | Untrusted text is passed only as a quoted data field; the LLM has no tools and no actions | Validator (banned phrases, risk contradiction, unknown numbers or links); 30-case injection test set | Template text |
| Invented reasons or numbers (hallucination) | — | Trust in explanations | Evidence-only prompt, structured JSON output | Validator checks every number and citation | Template text |
| Model evasion (scammers adapt) | Scammer | Detection quality | Hybrid signals (receiver behaviour, anomaly detector), held-out family tests | Novelty flag, drift checks | "Not sure" + human review |
| Data leakage between users | Insider / API abuse | Customer data | Role-based JWT; agents and customers read only their own data; masked IDs in logs | Audit log | Request denied |
| API abuse / scraping | Bot | Model endpoint | Rate limiting, strict Pydantic schemas (`extra="forbid"`), length caps | Logs, rate-limit counters | 429 response |
| Secret leakage | — | Gemini key, JWT secret | `.env` only, platform secrets, never in Git | Secret scan before commits | Rotate the key |
| Unsafe automated action | — | Customer money | The customer is never blocked; holds need a staff click with a reason | Audit log | — |
| Dependency vulnerability | Supply chain | Web / API | Pinned versions, `npm audit` in CI | CI | Patch and redeploy |
