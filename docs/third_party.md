# Third-party Resources and Licenses

Rulebook §4.4 / §9.2: every significant external resource is disclosed here. Update this file whenever a dependency, dataset, model, UI component or asset is added.

| Resource | Type | License | Purpose | Modified? | Redistribution |
|---|---|---|---|---|---|
| LightGBM | Library | MIT | AI-1, AI-5, quantile baseline | No | OK |
| scikit-learn | Library | BSD-3 | IForest, isotonic, LR | No | OK |
| SHAP | Library | MIT | XAI | No | OK |
| Chronos-2 | Model | Apache-2.0 (check card) | AI-3, AI-4 | No (zero-shot) | Weights downloaded, not committed |
| BGE-M3 | Model | MIT | AI-2, retrieval | No (frozen) | Downloaded |
| Gemini API (`gemini-3.8-flash`, `gemini-3.5-flash-lite`) + `google-genai` SDK | API + SDK | Gemini API Terms / SDK Apache-2.0 | Briefs, synthetic text generation | No | Outputs cached; synthetic inputs only |
| NetworkX | Library | BSD-3 | AI-6 | No | OK |
| FastAPI, Pydantic, SQLModel, slowapi, structlog | Library | MIT | API | No | OK |
| Next.js, React | Framework | MIT | Web | No | OK |
| shadcn/ui, Magic UI (NumberTicker, AnimatedBeam) | Components | MIT | UI | **Yes (copied + styled)** | Attribute |
| Recharts, Cytoscape.js, TanStack, Motion, lucide | Library | MIT / ISC | Charts, graph, tables, motion, icons | No | OK |
| Geist, Geist Mono, Instrument Serif, Anek Bangla | Fonts | SIL OFL 1.1 | Typography | No | OK |
| three.js, @react-three/fiber, drei, postprocessing, react-force-graph-3d | Library | MIT | Homepage 3D, optional 3D graph | No | OK |
| @shadergradient/react | Library | MIT | Homepage atmosphere | Configured (monochrome preset) | Attribute |
| GSAP (ScrollTrigger, SplitText) | Library | GSAP Standard "no charge" license (not MIT) | Homepage scroll story | No | Free incl. commercial; disclose |
| Lenis | Library | MIT | Smooth scroll | No | OK |
| UCI SMS Spam Collection | Dataset | Check the UCI page (listed as CC BY 4.0) | AI-2 external test only | No | Not committed; download script |
| PaySim (optional) | Dataset | Check Kaggle page | Sanity check only | No | Not committed |
| Vercel, Hugging Face Spaces, Kaggle, GitHub | Services | Free tiers / ToS | Hosting, compute | — | — |
| Pre-existing team code (if any, e.g. evidential head) | Code | Own | AI-2 head | Adapted | Disclose (Rulebook §4.3) |

**Copied / adapted UI code** (shadcn/ui, Magic UI): list each file under `frontend/components/ui/` and `frontend/components/magicui/` here when added.
