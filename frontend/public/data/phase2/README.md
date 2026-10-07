# Phase 2 evidence files

The page `/trust/phase2` ("What we changed after Phase 1") reads the JSON files in this folder at run time
(`fetch("/data/phase2/<name>.json")`). Nothing is built into the page: edit a file, redeploy (or refresh `npm run dev`)
and the page shows the new numbers.

Rules

- **No invented numbers.** A value that is not measured yet is `null` (or a string starting with `TBD`); the page shows
  it as "measuring…". A whole file with `"status": "pending"` is shown as pending, whatever it contains.
- A missing or broken file is also shown as "measuring…", so the page never breaks.
- Set `"status": "measured"` only when every number in the file comes from a script output (name it in `source`).

## Files

| File | Criterion (default mapping) | What goes in it |
|---|---|---|
| `criteria.json` | all | the 7 criteria, Phase 1 scores, the judges' concern, what we built, which evidence to show |
| `robustness.json` | AI/ML depth | multi-world (5 seeds) + 6 shift tests |
| `ablation.json` | AI/ML depth, Prototype, Innovation | ablation ladder (`ladder`), closed loop (`closed_loop`), Case Linker vs naive aggregation (`linking_vs_naive`) |
| `business.json` | Business impact | break-even follow rate, net benefit table, sensitivity (tornado) |
| `fairness.json` | Responsible AI | false-negative rate by account tenure, before/after |
| `scalability.json` | Scalability | p50/p95/p99 latency vs concurrency, throughput vs replicas |
| `security.json` | Responsible AI | tests, scans, audit log, model registry |
| `study.json` | Problem relevance, Innovation | user study summary (sections `triage`, `ratings`); "Download JSON" on `/study/results` writes it |
| `evidence.json` | as referenced in `criteria.json` | e.g. `evidence#public_data` |
| `adversarial.json` | as referenced in `criteria.json` | e.g. `adversarial#text_attacks` |

The page loads exactly these nine evidence files (list `FILES` in `frontend/app/(areas)/trust/phase2/page.tsx`); a new
file name needs one entry there.

`study.json`: while it is `pending`, the page shows the **live** study results instead, if the team PIN was entered on
`/study/results` in the same browser tab. After the session, write the final numbers here (export from
`GET /v1/study/results`) and set `"status": "measured"`, so the page works for everyone without the PIN.

## `criteria.json`

```json
{
  "criteria": [
    {
      "id": "business",                       // anchor: /trust/phase2#business
      "name": "Business impact",
      "score": 13.33, "max": 20,              // Phase 1 score
      "concern": { "text": "…", "quote": true },  // quote: true = the judges' exact words (shown in quotes); false = our paraphrase
      "built": ["One line per thing we built"],   // items starting with "TBD" are hidden
      "evidence": ["business", "study#triage"]    // "file" = whole file (headline + all sections); "file#section" = one section
    }
  ]
}
```

The concerns marked `"text": "TBD"` still need the judges' words from the Phase 1 feedback. The mapping of concerns to
criteria for problem relevance and innovation is our reading of the feedback: check it.

## Evidence file shape (every other file)

```json
{
  "status": "measured",                     // "pending" | "measured"
  "title": "Robustness: five worlds and six shifts",
  "updated_at": "2026-10-07T12:00:00Z",     // or null
  "source": "scripts/phase2/robustness_ai1.py -> reports/phase2/robustness/*.json",
  "summary": "One or two plain sentences.",
  "headline": [                              // KPI tiles (shown when the whole file is referenced)
    { "label": "PR-AUC, mean of 5 seeded worlds", "value": 0.812, "format": "num3", "sub": "min 0.79 · max 0.83" }
  ],
  "sections": [
    {
      "id": "multi_world",                   // referenced as "robustness#multi_world"
      "title": "Five independently seeded worlds",
      "lead": "Short line under the title.",
      "chart": { … one of the chart kinds below, or null … },
      "takeaway": "One sentence: what this shows."
    }
  ],
  "caveats": ["Honest limits, one per line."]
}
```

`format` / `unit` values: `pct` (0.42 → 42%), `pct1` (42.0%), `num`, `num1`, `num3`, `bdt` (Tk 1,234), `ms`, `s`, `x` (2.0×), `text`.

### Chart kinds

Bars (one bar per series for every category; good for before/after, A vs B, seeds, shifts, ablation ladder, tornado):

```json
{ "kind": "bars", "unit": "pct",
  "x": ["Rules only", "+ model", "+ calibration", "+ Case Linker"],
  "series": [ { "name": "scam money paused", "values": [0.41, 0.80, 0.83, 0.87] } ] }
```

Line (good for latency vs concurrency, closed loop over days, net benefit vs follow rate):

```json
{ "kind": "line", "unit": "ms", "x": [1, 10, 50, 100, 200], "x_label": "concurrent users",
  "series": [ { "name": "p50", "values": [12, 15, 22, 40, 90] },
              { "name": "p95", "values": [20, 28, 51, 95, 210] },
              { "name": "p99", "values": [30, 41, 80, 160, 380] } ] }
```

Table (good for the net benefit table and the security checklist; first column is a label):

```json
{ "kind": "table", "columns": ["follow rate", "net benefit per million transfers"], "units": [null, "bdt"],
  "rows": [ ["1%", 120000], ["10%", 2614201] ] }
```

The example numbers above only show the format; they are not results.

### Suggested sections per file

- `robustness.json`: `multi_world` (bars, x = seeds, series = UVERA and the rule baseline), `shifts` (bars, x = the six shifts, series = in-distribution vs shifted).
- `ablation.json`: `ladder` (bars), `closed_loop` (line, x = day), `linking_vs_naive` (bars, x = metrics such as rings recovered / precision / analyst minutes, series = naive aggregation vs Case Linker).
- `business.json`: `net_benefit` (table), `sensitivity` (bars, series = low and high), `break_even` (line, x = follow rate). Put the break-even follow rate in `headline`.
- `fairness.json`: `fnr_by_tenure` (bars, x = tenure bands, series = before and after).
- `scalability.json`: `latency` (line, p50/p95/p99), `replicas` (bars or line).
- `security.json`: `checks` (table: control, result, how it is verified).
- `study.json`: `triage` (bars, series = A and B), `ratings` (bars).
