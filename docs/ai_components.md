# AI Components

## The seven AIs (one Kaggle notebook each)
| AI | Name | Notebook | Core model | Input | Output | Uncertainty | XAI | Fallback |
|---|---|---|---|---|---|---|---|---|
| **AI-1** | Pause Check Risk Engine | `NB01` | **LightGBM** (+ rule baseline, XGBoost sanity check) | Sender + recipient + pair features | Scam-risk score | Isotonic calibration + class-conditional **split conformal** + novelty flag | Exact TreeSHAP (LightGBM `pred_contrib`) + plain-language reasons | Rule baseline |
| **AI-2** | Scam Text Sentinel | `NB02` | **BGE-M3** frozen embeddings + two heads: logistic regression, **evidential (Dirichlet) MLP** | Message text | Scam family + verdict | Dirichlet "unknown" mass vs calibrated LR; keep whichever has better ECE and abstain-risk curve | Phrase occlusion (remove a phrase, see score drop) | Char n-gram TF-IDF + LR (tiny, CPU) |
| **AI-3** | Cash-Flow Guardian | `NB03` | **Chronos-2** (zero-shot, with covariates) vs **LightGBM quantile** vs seasonal-naive | Daily wallet in/out + calendar | P(shortfall), weeks of heavy outflow, savings options | Quantiles 10/50/90 + conformal width check | Which weeks/categories drive the shortfall | Seasonal-naive |
| **AI-4** | Agent Liquidity Copilot | `NB04` | Same family as AI-3, per agent | Agent cash-in/out + calendar | P(stock-out), top-up time | Quantiles → P(demand > cash) | Peak-demand drivers | Last-4-week average |
| **AI-5** | QR Shield | `NB05` | **Peer z-score + IsolationForest + LightGBM** | Merchant/payer QR behaviour | Merchant risk score | Calibration + conformal + novelty → grey state | SHAP + peer comparison bars | Peer z-score only |
| **AI-6** | Case Linker | `NB06` | **NetworkX** graph analytics (paths, degree, Louvain communities) | Transfers, QR payments, cash-outs, devices | Linked case + chain score + evidence subgraph | Chain score from path evidence; weak links labelled | The subgraph *is* the explanation | Per-alert queue |
| **AI-7** | Grounded Brief | `NB07` (CPU + API) | **Gemini API** (`gemini-3.8-flash`, structured JSON output; fallback `gemini-3.5-flash-lite`) + **BGE-M3** retrieval over the policy cards in `policy_cards/` | Structured evidence JSON + retrieved cards | Bangla + English brief, card IDs | Inherits upstream state; validator rejects unsupported text | Cites card IDs and evidence IDs | Template text |

Plus `NB00` (Synthetic World) and `NB99` (Evaluation, Fairness, Packaging). **Total: 9 notebooks (1 data, 7 AI, 1 evaluation).** No LLM is hosted anywhere. **Gemini is used only for wording (AI-7) and for generating synthetic text data (NB02).** Every risk decision is made by the measured ML models + YAML policy.
