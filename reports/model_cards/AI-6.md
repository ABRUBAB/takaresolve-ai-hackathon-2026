# Model card — AI-6 Case Linker

*Notebook `NB06` · code commit `856988681c` · results `reports/metrics_ai6.json` · synthetic data only.*

| | |
|---|---|
| Task | Join many alerts into a few evidence-backed cases. |
| Inputs | High-risk transfers from AI-1, flagged shops from AI-5 and the money paths between wallets, shops and agents. |
| Model | Time-respecting path tracing (≤ 3 hops, ≤ 48 hours) + union-find linking + a transparent chain score; Louvain communities for ring discovery. |
| Baseline | One alert = one item for the analyst. |
| Uncertainty | Weak links are shown as weak; the chain score formula is shown to the analyst. |
| Explanation | The evidence subgraph is the explanation; evidence lines E1–E5. |
| Intended use | Operations case queue with a dispute-deadline clock (business rules). |
| Out of scope | Automatic holds; every action needs an analyst with a written reason (audit log). |

## Measured results (test data the model never saw)

- 377 alerts → 197 cases: **47.7% fewer items** to open.
- Alert pairs paid to the same mule that were linked: 100.0%; mean case purity 90.1%.
- Real scam alerts inside the top 5 / 10 / 20 cases: 94.0% / 96.0% / 98.0%.
- Cash-outs found for detected cases: 72.4%.

## Limitations

Linking quality depends on AI-1 and AI-5 alerts; synthetic money paths.
