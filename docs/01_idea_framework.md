# Idea Development Framework (Guideline p8 §10)

**Problem statement (organiser template).**
> For first-time upay customers, upay agents and upay operations staff, scam-induced transfers, disguised Bangla QR cash-outs and slow case handling cause lost money, lost agent income and missed dispute deadlines. We will build **UVERA**, an AI platform with customer, agent and operations areas that uses synthetic wallet, agent and QR-merchant data to **score risk with calibrated uncertainty, forecast cash-flow and agent liquidity, and link cases into evidence-backed actions with human approval**, with success measured by **scam loss prevented at a fixed alert rate, false alerts per 1,000 normal transfers, QR-leakage precision@k, forecast error and interval coverage, and analyst minutes per case.**

| Step | Answer | Evidence |
|---|---|---|
| 1. User | Rina (first-time wallet user), Karim (agent), Nusrat (ops analyst) | README: *UVERA in 30 seconds* |
| 2. Problem | Money is lost before detection; QR used as a disguised cash-out; slow, fragmented cases | README: *The problem (2026)* |
| 3. Why now | 2026 QR misuse reports; dispute rules from 1 Dec 2026; open multilingual and forecasting models | Appendix 1 |
| 4. Solution | One website: homepage + customer, agent and ops areas on one backend | README: *One website, three areas* |
| 5. AI role | Prediction, detection, forecasting, grounded generation | [`ai_components.md`](ai_components.md) |
| 6. Impact | [`impact_plan.md`](impact_plan.md) | `docs/impact_plan.md` |
| 7. Data | Own synthetic world + open public sets for sanity/external tests | `docs/data_card.md` |
| 8. Validation | Offline metrics vs baselines + small usability test + simulated A/B | `reports/` |
| 9. Scale | Shadow mode → A/B holdout → pilot on governed data | `docs/production_path.md` |
