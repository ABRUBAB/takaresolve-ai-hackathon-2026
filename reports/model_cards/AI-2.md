# Model card — AI-2 Scam Text Sentinel

*Notebook `NB02` · code commit `ef989c6b69` · results `reports/metrics_ai2.json` · synthetic data only.*

| | |
|---|---|
| Task | Is a received message a scam, which of six scam families, and which phrases moved the verdict. |
| Inputs | Message text in Bangla, Banglish or English (synthetic: templates + Gemini-generated, never real messages). |
| Model | Served live: character TF-IDF (2–5-grams) + logistic regression (tfidf_lr), because it runs on a CPU-only server. Compared with BGE-M3 embeddings + logistic regression and BGE-M3 + an evidential (Dirichlet) head. |
| Baseline | The three models compared with each other; external sanity test on the UCI SMS Spam Collection (English advertising spam, a different task). |
| Uncertainty | Isotonic-calibrated scam probability: likely scam ≥ 0.7, likely safe ≤ 0.3, otherwise "not sure". |
| Explanation | Phrase occlusion: remove a phrase and measure how much the scam probability drops. |
| Intended use | Customers check a suspicious message before acting on it. |
| Out of scope | Filtering or deleting messages; any decision without the person reading the result. |

## Measured results (test data the model never saw)

- Corpus: 11,092 synthetic messages; best on cross-validation: emb_lr.
- Held-out writing style (never seen in training):
  - tfidf_lr (served): verdict PR-AUC 0.986, scam-family macro F1 0.855, ECE 0.073
  - emb_lr: verdict PR-AUC 0.977, scam-family macro F1 0.871, ECE 0.072
  - emb_evidential: verdict PR-AUC 0.978, scam-family macro F1 0.853, ECE 0.067
  - served model, bangla: PR-AUC 0.996, F1 0.957
  - served model, banglish: PR-AUC 0.979, F1 0.878
  - served model, english: PR-AUC 0.983, F1 0.893
- External real English SMS spam (UCI, a different task): tfidf_lr PR-AUC 0.224, emb_lr PR-AUC 0.538, emb_evidential PR-AUC 0.517 (spam share 13.4%).

## Limitations

Trained and tested on synthetic text. On real English spam (UCI) the scores drop sharply, so real-world performance is not proven.
