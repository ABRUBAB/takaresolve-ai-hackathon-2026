# Demo scenarios

Fixed-seed scenarios used for the demo and end-to-end tests. **Never used for training.**

| Scenario | Expected result |
|---|---|
| `normal_user` | Confident low risk → proceed |
| `golden_prize_scam` | Confident high risk → warning with reasons; linked case in operations |
| `unsure_conflicting_signals` | "Not sure" → a person checks |
| `new_device_takeover` | High risk; reasons include a new device or PIN reset |
| `qr_cashout_unseen_family` | QR Shield grey / amber (an unseen disguise style) |
| `cashflow_shortfall` | Shortfall probability with a forecast band and three savings plans |
| `agent_low_cash` | Stock-out probability and a top-up suggestion |
| `prompt_injection_text` | Verdict unaffected; the validator blocks unsafe wording |
