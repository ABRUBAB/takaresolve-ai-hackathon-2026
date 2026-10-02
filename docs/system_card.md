# AI System Card — UVERA

_Status: template — filled in during the hackathon from measured results only._

- **Intended use:** decision support for customers, agents and MFS operations staff. Not for autonomous approval/denial of money movement or lending.
- **Human oversight:** customers are never blocked; every hold, merchant cap or escalation needs an ops click + reason (audit log).
- **Output types shown in the UI:** model estimate · business rule · generated wording · assumption.
- **Uncertainty:** calibrated probability, conformal set, novelty flag → "not sure" → human review.
- **LLM:** Gemini writes text only from structured evidence; validator + template fallback; no tools, no actions.
- **Known failure modes:** see the plan, J.6.
