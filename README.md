# UVERA — Trust you can verify

> **AI DEV FEST 2026 · AI Hackathon · DIU-CPC × upay · Track 07 Open Innovation**
> One AI trust layer for a mobile-financial-services ecosystem: it **pauses scams before the customer taps Confirm**, protects **agent cash and income** from disguised Bangla QR cash-outs, and gives **operations** one evidence-backed case instead of five alerts. *The AI recommends. Humans decide.*

| | |
|---|---|
| **Live demo** | _coming soon (Vercel)_ |
| **API docs** | _coming soon (`/docs` on the Hugging Face Space)_ |
| **Video** | _coming soon_ |
| **Report** | _coming soon (`docs/report/`)_ |
| **Plan (single source of truth)** | [`docs/plan/UVERA_PLAN.md`](docs/plan/UVERA_PLAN.md) |

> ⚠️ All data in this project is **synthetic** or from **open-licensed public datasets**. No real customer data or PII is used.

---

## Overview
**Problem.** Many wallet users are tricked into sending money themselves, a few seconds before a fraud system could act. The money is then cashed out through agents or QR merchants acting like ATMs, and the complaint is handled slowly. *(Sources: see the plan, Appendix 1.)*

**Solution.** UVERA is one website with a public homepage and three role areas:
- **Customer** — Pause Check (scam risk before Confirm), Scam Text Check, Cash-Flow Guardian.
- **Agent** — Liquidity Copilot, Agent Risk vs peers, QR leakage in the agent's zone.
- **Operations** — Case Queue, Case Detail (evidence graph, grounded brief, Dispute Clock), QR Watchlist, Trust Center.

**Purpose.** Show how calibrated, explainable, uncertainty-aware AI can make digital money safer, with a believable path to validation on governed data.

## Features
| Feature | Area | AI component | What the AI does | Uncertainty / XAI |
|---|---|---|---|---|
| Pause Check | Customer | AI-1 LightGBM + isotonic + conformal | Scores scam risk of a draft transfer | Conformal set → "not sure" state; SHAP reasons |
| Scam Text Check | Customer | AI-2 BGE-M3 + LR / evidential head | Classifies a pasted message | Evidential "unknown" mass; phrase occlusion |
| Cash-Flow Guardian | Customer | AI-3 Chronos-2 vs LightGBM-quantile | Forecasts shortfall before month-end | 10/50/90 bands, interval coverage |
| Liquidity Copilot | Agent | AI-4 (shared forecaster) | Forecasts cash / e-float stock-out | 10/50/90 bands |
| QR Shield | Agent + Ops | AI-5 peer z-score + IsolationForest + LightGBM | Flags QR used as disguised cash-out | Calibration + conformal + novelty |
| Case Linker | Ops | AI-6 NetworkX graph analytics | Links victim, mule and merchant into one case | Evidence subgraph |
| Grounded Brief | Ops + Customer | AI-7 Gemini API (structured JSON) + retrieval | Writes Bangla/English text **only from evidence** | Validator; template fallback |
| Dispute Clock | Ops | **Rule, not AI** (`configs/rules/dispute.yaml`) | Tracks deadlines | Timer trace |

_Status: under active development during the hackathon window. This table is updated as features land._

## Tech stack
Python 3.12 · pandas / pyarrow · LightGBM · scikit-learn · SHAP · Chronos-2 · BGE-M3 · NetworkX · Gemini API (`google-genai`) · FastAPI · Pydantic · SQLite · Next.js 16 · React · TypeScript · Tailwind CSS · shadcn/ui · Magic UI · Recharts · Cytoscape.js · three.js / React Three Fiber · GSAP · Motion · Vercel · Hugging Face Spaces · Kaggle.
Full license list: [`docs/third_party.md`](docs/third_party.md).

## Requirements
- Python **3.12** (3.11+ works), Node.js **22 LTS**, npm
- ~4 GB free RAM (8 GB if the BGE-M3 text model is enabled)
- Docker (optional, for `docker compose`)
- No GPU needed to run the app. Training notebooks run on Kaggle.
- A **Gemini API key** is optional: without it, the app serves cached briefs and template text.

## Installation and setup
```bash
git clone https://github.com/ABRUBAB/takaresolve-ai-hackathon-2026.git
cd takaresolve-ai-hackathon-2026
cp .env.example .env            # then edit values (never commit .env)
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e "./ml[dev]" -e "./backend[dev]"
cd frontend && npm install && cd ..
```

## Environment variables
| Variable | Purpose | Example (placeholder) |
|---|---|---|
| `JWT_SECRET` | Signs demo-role tokens | `change-me` |
| `ALLOWED_ORIGINS` | CORS allow-list (comma separated) | `http://localhost:3000` |
| `MODEL_DIR` | Folder with exported model artifacts | `../artifacts` |
| `TEXT_MODEL` | `bge` or `tfidf` (lighter) | `bge` |
| `FORECAST_LIVE` | Run the forecaster live (`true`) or serve precomputed forecasts | `false` |
| `LLM_MODE` | `live`, `cached` or `template` | `cached` |
| `GEMINI_API_KEY` | Gemini API key (optional) | `your-gemini-api-key-here` |
| `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` | Gemini model IDs | `gemini-3.8-flash` / `gemini-3.5-flash-lite` |
| `DEMO_MODE` | Enables seeded scenarios + demo logins | `true` |
| `RATE_LIMIT` | API rate limit | `60/minute` |
| `LOG_LEVEL` | Log level | `info` |
| `NEXT_PUBLIC_API_BASE` | API base URL used by the web app | `http://localhost:8000` |

## Run
```bash
make data      # generate the synthetic world (small scale, ~2 min)   — coming soon
make api       # uvicorn on http://localhost:8000  (docs at /docs)
make web       # Next.js on http://localhost:3000
# or everything in containers:
docker compose up --build
```
Without `make` (e.g. Windows):
```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

## Build
```bash
cd frontend && npm run build && npm start
docker build -f backend/Dockerfile -t uvera-api .
```

## Live deployment
_Coming soon:_ web on Vercel, API on a Hugging Face Docker Space.

## Testing
```bash
make test                       # = pytest ml/tests + pytest backend/tests + frontend lint
cd frontend && npm run lint
```
End-to-end tests (Playwright) and a 5-step manual check of the golden scenario will be added here.

## Other configuration
- `configs/*.yaml` — every synthetic assumption, injected pattern, threshold, feature flag and business rule. **Business rules are kept separate from ML.**
- `notebooks/` — one Kaggle notebook per AI (NB00–NB07) + NB99 evaluation. See [`notebooks/README.md`](notebooks/README.md).
- `artifacts/manifest.json` — exported model files with SHA-256, data version and notebook version.

## Responsible AI
Synthetic data only · calibrated probabilities and an explicit "not sure" state · SHAP / evidence explanations · the LLM only writes words from evidence and never decides · every hold or merchant action needs a human click with a reason · fairness slices · prompt-injection tests. Details: [`docs/system_card.md`](docs/system_card.md).

## Limitations
Results on synthetic data show that the pipeline works, not real-world accuracy. See the report and model cards.

## Team and disclosure
Built during the official 72-hour window of AI DEV FEST 2026. Third-party resources and any pre-existing general-purpose components are disclosed in [`docs/third_party.md`](docs/third_party.md).

## License
MIT for our code — see [`LICENSE`](LICENSE). Third-party components keep their own licenses.
