# Fairness report

Generated from `reports/metrics_ai1.json`, `metrics_ai2.json` and `metrics_ai5.json` (NB99 collects them).

| AI | Slices | Metrics |
|---|---|---|
| AI-1 Pause Check | account age, zone, channel (app / USSD), language, customer segment | false-positive rate, false-negative rate, calibration (ECE), "not sure" rate |
| AI-2 Scam Text | Bangla, Banglish, English | verdict PR-AUC and F1 |
| AI-5 QR Shield | merchant size; honest round-price shops | false-positive rate |

For each finding we write **what we observed**, **possible reasons**, and **what real data must confirm**.
We do not use or invent sensitive attributes.
