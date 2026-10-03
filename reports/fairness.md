# Fairness slices (synthetic data)

Error rates by group on the test data. Large gaps would be flagged here; they are reported even when they look bad. No sensitive attributes are used or invented.

## AI-1 Pause Check (test window, pause threshold)

| Slice | Group | Transfers | Scams | False-positive rate | Missed scams (FNR) | Calibration error | 'Not sure' rate |
|---|---|---|---|---|---|---|---|
| zone | rural | 20,954 | 161 | 0.9% | 18.0% | 0.001 | 0.6% |
| zone | semi_urban | 25,293 | 167 | 0.8% | 24.6% | 0.002 | 0.6% |
| zone | urban | 37,308 | 258 | 0.8% | 26.4% | 0.002 | 0.5% |
| channel | app | 58,411 | 387 | 0.8% | 25.3% | 0.001 | 0.6% |
| channel | ussd | 25,144 | 199 | 1.0% | 20.1% | 0.002 | 0.5% |
| tenure_bucket | 90-365d | 23,651 | 281 | 0.9% | 19.2% | 0.003 | 0.6% |
| tenure_bucket | <90d | 6,713 | 43 | 1.6% | 18.6% | 0.002 | 0.6% |
| tenure_bucket | >365d | 53,191 | 262 | 0.7% | 29.0% | 0.001 | 0.5% |
| language | bangla | 33,100 | 228 | 0.9% | 21.5% | 0.001 | 0.5% |
| language | banglish | 29,098 | 198 | 0.8% | 22.2% | 0.001 | 0.6% |
| language | english | 21,357 | 160 | 0.8% | 28.1% | 0.002 | 0.5% |
| segment | daily_wage | 24,656 | 216 | 1.0% | 21.8% | 0.002 | 0.5% |
| segment | remittance | 14,984 | 93 | 0.7% | 31.2% | 0.002 | 0.6% |
| segment | salaried | 36,639 | 198 | 0.9% | 27.3% | 0.001 | 0.6% |
| segment | student | 7,276 | 79 | 0.4% | 10.1% | 0.003 | 0.5% |

## AI-2 Scam Text (held-out writing style, served model)

| Language | Messages | Verdict PR-AUC | F1 at 0.5 |
|---|---|---|---|
| bangla | 1,852 | 0.996 | 0.957 |
| banglish | 1,815 | 0.979 | 0.878 |
| english | 1,819 | 0.983 | 0.893 |

## AI-5 QR Shield (honest shops wrongly flagged, by size)

| Shop size | False-positive rate |
|---|---|
| small | 11.0% |
| medium | 9.2% |
| large | 7.9% |

