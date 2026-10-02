# Third-party Resources and Licenses

Rulebook §4.4 / §9.2: every significant external resource is disclosed here. Versions used on Kaggle are recorded in
`reports/versions_nb*.json`.

## Machine learning and data

| Resource | Type | License | Purpose | Modified? |
|---|---|---|---|---|
| LightGBM | Library | MIT | AI-1, AI-5, quantile forecasts; exact TreeSHAP via `pred_contrib` | No |
| XGBoost, CatBoost | Library | Apache-2.0 | AI-1 comparison models (NB01) | No |
| scikit-learn | Library | BSD-3 | Isolation Forest, isotonic calibration, logistic regression, TF-IDF, CV splitters | No |
| NumPy, pandas, PyArrow, SciPy | Library | BSD-3 / Apache-2.0 | Data handling, paired t-intervals | No |
| PyTorch | Library | BSD-3 | AI-2 evidential head | No |
| sentence-transformers | Library | Apache-2.0 | Runs BGE-M3 in NB02 | No |
| BGE-M3 (`BAAI/bge-m3`) | Model | MIT | AI-2 text embeddings (frozen) | No |
| Chronos-2 (`amazon/chronos-2`, `chronos-forecasting`) | Model + library | Apache-2.0 | AI-3 / AI-4 zero-shot forecaster (NB03 / NB04) | No |
| NetworkX | Library | BSD-3 | AI-6 graph, Louvain communities | No |
| Matplotlib | Library | PSF-style | Report figures | No |
| Gemini API + `google-genai` SDK | API + SDK | Gemini API Terms / Apache-2.0 | AI-7 briefs and synthetic message variants (NB02, NB07) | No |
| UCI SMS Spam Collection | Dataset | CC BY 4.0 (UCI) | AI-2 external sanity test only; downloaded in NB02, not committed | No |

Only synthetic data is ever sent to Gemini. The API key is read from a Kaggle Secret or an environment variable and is never
committed.

## API

| Resource | Type | License | Purpose |
|---|---|---|---|
| FastAPI, Starlette, Uvicorn | Library | MIT / BSD-3 | HTTP API |
| Pydantic, pydantic-settings | Library | MIT | Request validation, settings |
| PyJWT | Library | MIT | Demo role tokens |
| SQLite (Python standard library) | Library | Public domain | Audit log of human decisions |

## Website

| Resource | Type | License | Purpose | Modified? |
|---|---|---|---|---|
| Next.js, React | Framework | MIT | Website | No |
| Tailwind CSS, tw-animate-css | Library | MIT | Styling | No |
| shadcn/ui (base-nova style: button, sheet, sonner) + `cn` | Components (copied) | MIT | UI primitives in `frontend/components/ui/` | Yes (styled) |
| Base UI (`@base-ui/react`) | Library | MIT | Accessible primitives behind the shadcn components | No |
| Magic UI — NumberTicker | Component (copied) | MIT | Animated numbers in `frontend/components/ui/number-ticker.tsx` | Yes (styled) |
| class-variance-authority | Library | Apache-2.0 | Component variants | No |
| three.js, @react-three/fiber, @react-three/postprocessing | Library | MIT | Homepage 3D Trust Field (own code in `components/home/trust-field.tsx`) | No |
| Motion | Library | MIT | Animations | No |
| Lenis | Library | MIT | Smooth scrolling on the homepage | No |
| Recharts | Library | MIT | Forecast charts | No |
| Cytoscape.js | Library | MIT | Case money-path graph | No |
| next-themes, sonner, lucide-react | Library | MIT / ISC | Theme, toasts, icons | No |
| Geist, Geist Mono, Instrument Serif, Anek Bangla (Google Fonts) | Fonts | SIL OFL 1.1 | Typography | No |

## Services

| Service | Use |
|---|---|
| Kaggle Notebooks | Official training and evaluation runs (free GPU / CPU) |
| GitHub | Source code and committed results |
| Hugging Face Spaces (Docker) | API hosting |
| Vercel | Website hosting |

## Development tools (not shipped)

Design and motion guidance from Emil Kowalski's writing, Impeccable (Apache-2.0) and the Taste skill (MIT) informed the UI
review. AI coding assistants were used during development; all code was reviewed and is owned by the team.
