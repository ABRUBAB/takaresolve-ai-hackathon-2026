# AI components

Seven AI components, one Kaggle notebook each, plus `NB00` (synthetic world) and `NB99` (evaluation and model cards).
Measured results: [`reports/summary.md`](../reports/summary.md) · one card per model: [`reports/model_cards/`](../reports/model_cards/README.md).

| AI | Name | Notebook | Model served | Compared with | Uncertainty | Explanation | Fallback |
|---|---|---|---|---|---|---|---|
| **AI-1** | Pause Check | `NB01` | **LightGBM** on 19 before-transfer features | Rule baseline, logistic regression, XGBoost, CatBoost (grouped CV × 5 seeds) | Isotonic calibration · Mondrian conformal (90%) · robust novelty flag → "not sure" | Exact TreeSHAP top-3 reasons (EN/BN); counterfactual amount | Transparent rule, marked *degraded* |
| **AI-2** | Scam Text Check | `NB02` | **Character TF-IDF + logistic regression** (CPU) | BGE-M3 embeddings + logistic regression; BGE-M3 + evidential (Dirichlet) head | Calibrated scam probability; likely scam / not sure / likely safe | Phrase occlusion (remove a phrase, measure the drop) | Quick in-process TF-IDF model if the artifact is missing |
| **AI-3** | Cash-Flow Guardian | `NB03` | **LightGBM-quantile** live (results table: validation winner, Chronos-2) | Chronos-2 (zero-shot), seasonal-naive (rolling-origin backtest) | 10/50/90% bands; shortfall probability from validation residuals | Heaviest spending weeks | Normal approximation |
| **AI-4** | Liquidity Copilot | `NB04` | **LightGBM-quantile**: cash to hold = 90% forecast | Chronos-2, seasonal-naive; usual cash; same extra cash spread evenly | 10/50/90% bands | Extra cash above the usual amount | Normal approximation |
| **AI-5** | QR Shield | `NB05` | **70% LightGBM + 30% Isolation Forest** (rank fusion) on peer-relative features | Peer z-score; one disguise family held out entirely | Isotonic calibration · Mondrian conformal → grey "needs review" | Top reasons + peer comparison | — |
| **AI-6** | Case Linker | `NB06` | **Time-respecting path tracing** (≤ 3 hops, ≤ 48 h) + union-find + transparent chain score | One alert = one item | Weak links shown as weak | The evidence subgraph; evidence lines E1–E5 | Per-alert queue |
| **AI-7** | Grounded Brief | `NB07` | **Gemini API** (`gemini-3.8-flash`, structured JSON; fallback `gemini-3.5-flash-lite`) + policy-card retrieval | Template text | Inherits the upstream state; must say "not sure" when unsure | Cites evidence ids and policy-card ids | Template text |

**Where language models are used:** Gemini only rewrites validated evidence (AI-7) and generates synthetic training
messages (NB02). Every risk decision comes from the measured ML models plus the YAML business rules.
