# UVERA scale stack: production-path reference deployment

A working, measured answer to "deployment latency and live MFS integration are unproven" and "no distributed queue,
shared cache, persistent transactional database, model-serving fleet, centralized monitoring, or demonstrated horizontal
scaling". Everything here runs with `docker compose` on one laptop and every number in
[`reports/scalability/README.md`](../../reports/scalability/README.md) was measured on that laptop.

The hackathon API in `backend/` is unchanged: it stays the demo app (whole synthetic world in memory, SQLite audit).
This folder is the path to production for the part that has to scale: the pre-transfer Pause Check.

## Architecture

```mermaid
flowchart LR
  subgraph MFS core
    CORE[Transfer service] -- "pre-transfer check (HTTP)" --> LB
    CORE -- "executed transfers, cash-in/out, security events" --> PROD
  end
  PROD[producer<br/>replays events.parquet] -- XADD --> STREAM[(Redis Stream<br/>uvera:events)]
  STREAM -- "consumer group 'features'" --> W[feature-worker xN<br/>Lua: atomic, in-order updates]
  W -- "per-wallet rolling state" --> FS[(Redis online feature store)]
  W -- "micro-batches of point-in-time features (shadow mode, POST /score/batch)" --> LB
  W -- "PSI drift window" --> M
  LB[nginx<br/>least_conn, DNS re-resolve] --> S1[scorer 1] & S2[scorer 2] & SN[scorer N]
  S1 & S2 & SN -- "READ features (1 Lua call)" --> FS
  S1 & S2 & SN -- "batched COPY: decisions, alerts" --> PG[(Postgres<br/>decisions, alerts, cases,<br/>audit, labels)]
  ART[artifacts/ (read-only)<br/>SHA-256 vs manifest.json] -. verified at start .-> S1 & S2 & SN
  M[Prometheus<br/>DNS discovery + alert rules] -- scrape /metrics --> S1 & S2 & SN & W
  G[Grafana (optional)] --> M
```

ASCII version:

```
 MFS core --(pre-transfer HTTP)--> nginx :8080 --least_conn--> scorer x N (1 vCPU each) --COPY--> Postgres
     |                                                             |  ^
     |                                                             |  | 1 Lua READ per request (19 features)
     +--(events)--> producer --XADD--> Redis Stream --> feature-worker --Lua APPLY--> Redis online store
                                                         |   \--> shadow scoring --> nginx (same fleet)
                                                         \--> drift window (PSI) --> /drift, /metrics
 Prometheus scrapes every scorer + worker (DNS service discovery), evaluates drift / latency / error alert rules.
```

| Component | Image | Role |
|---|---|---|
| `redis` | redis:7-alpine | Event bus (Redis Streams + consumer groups, bounded with `MAXLEN ~`) and online feature store / shared cache |
| `postgres` | postgres:16-alpine | Transactional store: `decisions`, `alerts`, `cases`, `case_wallets`, `audit_log`, `fraud_labels`, `transactions`, `model_deployments` ([schema](postgres/init.sql)) |
| `scorer` | uvera-scale (python:3.12-slim) | Stateless model server: AI-1 Pause Check (LightGBM + isotonic + conformal + novelty + policy + TreeSHAP reasons) and AI-2 SMS check; `--scale scorer=N` |
| `nginx` | nginx:alpine | Load balancer, keep-alive pool, retries on 502/503, re-resolves the replica set every 5 s |
| `feature-worker` | uvera-scale | Streaming feature computation, drift monitor, shadow-mode scoring client |
| `producer` | uvera-scale (profile `tools`) | Replays the synthetic event log at a chosen rate, optional shifted streams |
| `prometheus` | prom/prometheus | Central metrics + [alert rules](prometheus/alerts.yml) (drift, p99 latency, errors, stream lag, replica down) |
| `grafana` | grafana-oss (profile `dashboards`) | Provisioned dashboard [uvera-scale.json](grafana/provisioning/dashboards/uvera-scale.json) |

## How each judge concern maps to a component

| Judge concern | Answer in this stack | Evidence |
|---|---|---|
| No distributed queue / event stream | Redis Streams with a consumer group (`features`), at-least-once delivery, backpressure in the producer, bounded stream | stream ingestion table (section 6 of the results) |
| No shared cache / streaming feature computation | Redis online feature store, updated per event by an atomic Lua script; the scorer reads all 19 features in one round trip | parity test (section 8): online vs batch features on the whole test window |
| No persistent transactional database | Postgres 16 with indexed tables for decisions, alerts, cases, audit, labels; batched `COPY` on the hot path, transactions + advisory locks for case linking | DB mode table (section 4), mixed workload (section 5), shadow replay (section 7) |
| No model-serving fleet / horizontal scaling | Stateless scorer replicas (1 vCPU each) behind nginx; `docker compose up --scale scorer=N`; k8s Deployment + HPA template in [`k8s/`](k8s/) | sections 1-2: throughput and p95/p99 at 1/2/4 replicas, concurrency 1-128 |
| No model registry / artifact integrity | Every replica verifies the SHA-256 of each served file against `artifacts/manifest.json` and refuses to start on a mismatch; version exposed on `/model`, `/health`, `uvera_model_info` and written to `model_deployments` | `GET /model` |
| No centralized monitoring | Prometheus scrapes every replica via DNS discovery; latency histograms, outcomes, stage timings, RSS, stream lag, PSI gauges; alert rules | `prometheus/alerts.yml`, Grafana dashboard |
| Retraining / drift monitoring | PSI per feature vs training reference bins (`reference_bins.json`), sliding window in the worker, `GET /drift`, warn 0.1 / alert 0.2 | drift demo (section 9) |
| Deployment latency unproven; live MFS integration | p50/p95/p99 under concurrent load; shadow-mode replay of the full test window through producer -> stream -> worker -> scorer -> Postgres, with end-to-end decision latency | sections 1, 7 |

## Run it

Prerequisites: Docker, the synthetic world in `_outputs/world_full` and the project venv (for the two offline steps).
Set `UVERA_PG_PASSWORD` in the shell before starting Compose. Use a random URL-safe value; it is required and is not stored in the repository. This single-host stack is a measured reference deployment, not a production security configuration.

```bash
# 0. offline, once (batch side): reference bins for drift, batch features for parity, compact replay files
.venv\Scripts\python deploy/scale/offline/build_reference.py
.venv\Scripts\python deploy/scale/offline/export_replay.py

cd deploy/scale
# 1. the stack, 4 scorer replicas
docker compose up -d --build --scale scorer=4
curl http://127.0.0.1:8080/health          # through nginx: model version, artifact verification, RSS
curl http://127.0.0.1:8080/model           # SHA-256 of every served file vs the manifest

# 2. seed the online store and replay history into the stream (state warm-up, max speed)
docker compose --profile tools run --rm loadgen python -m uvscale.bootstrap --flush
docker compose --profile tools run --rm producer python -m uvscale.producer --from-day 0 --to-day 100 --rate 0

# 3. score a transfer (features come from the online store)
curl -X POST http://127.0.0.1:8080/score/transfer -H "content-type: application/json" \
     -d '{"sender":"C007339","receiver":"C008337","amount":2500,"channel":"app","t":8683200}'
curl http://127.0.0.1:9090/targets         # Prometheus sees every replica
```

Measurements (each writes JSON into `reports/scalability/`):

```bash
# (Git Bash on Windows: export MSYS_NO_PATHCONV=1 first, otherwise /repo/... paths get rewritten)
# A. shadow replay of the test window + parity sink (worker recreated with shadow scoring on)
SHADOW_URL=http://nginx:8080/score/batch PARITY_OUT=/repo/_outputs/scale/online_features_window.npy \
  docker compose up -d --force-recreate feature-worker
docker compose --profile tools run --rm loadgen python -m uvscale.bootstrap --flush
docker compose --profile tools run --rm loadgen python -m uvscale.producer --from-day 0 --to-day 100 --rate 0
docker compose --profile tools run --rm loadgen python -m uvscale.phase reset
docker compose --profile tools run --rm loadgen python -m uvscale.producer --from-day 100 --to-day 120 \
  --rate 2500 --score-from-day 100 --end-marker
docker compose --profile tools run --rm loadgen python -m uvscale.phase save /repo/reports/scalability/shadow_worker_stats.json shadow
docker compose --profile tools run --rm loadgen python -m uvscale.shadow_report
.venv\Scripts\python deploy/scale/parity_test.py                     # online vs batch features

# B. stream ingestion steps on a fresh store (the last step finishes the days 0-99 warm-up), then the drift demo
docker compose up -d --force-recreate feature-worker                   # shadow off
docker compose --profile tools run --rm loadgen python -m uvscale.bootstrap --flush
docker compose --profile tools run --rm loadgen python -m uvscale.streambench --from-day 0 --to-day 100 \
  --rates 1000 2000 5000 10000 --seconds 30 --finish
docker compose --profile tools run --rm loadgen python -m uvscale.driftdemo
# HTTP load: replicas x concurrency, explanation cost, DB write modes, mixed workload
.venv\Scripts\python deploy/scale/bench.py sweep --replicas 1 2 4 --conc 1 8 32 64 128
.venv\Scripts\python deploy/scale/bench.py explain --replicas 4 --conc 64
.venv\Scripts\python deploy/scale/bench.py dbmode --replicas 4 --conc 64
.venv\Scripts\python deploy/scale/bench.py mixed --replicas 4 --conc 32 64
# charts + results README
.venv\Scripts\python deploy/scale/charts.py
.venv\Scripts\python deploy/scale/report.py
docker compose down          # keeps images; add -v to drop the Postgres volume
```

## Online features: what is computed where

The 19 AI-1 features are defined once for training (`ml/uvera_ml/features/ai1.py`, batch, pandas) and once for serving
([`uvscale/online_features.py`](uvscale/online_features.py), streaming, Redis Lua). The Lua script keeps per-wallet,
per-day counters (pruned after 30 days), last money-in times, last device change / PIN reset times and a per-sender
counterparty map. Balances come from a daily start-of-day ledger snapshot (`ledger:sod:{day}`, what a core ledger
publishes once a day; the batch feature is defined on that same start-of-day balance), with a balance rebuilt from the
stream as fallback. The rebuilt balance alone matched only 37.9% exactly (70.4% within 1%), because 0.9% of
customer-days in the synthetic ledger have outflows that never appear as events; with the snapshot the feature is exact.
Because each event is applied by one atomic
script and a pipelined batch executes in order, the feature vector a transfer sees is exactly the state before it,
like the batch builder's "strictly before" windows. The parity test checks this on every p2p transfer of the test window.

## Drift monitoring and the retraining policy

* Reference: quantile bins (10 per feature, NaN as its own bin) of the 19 features from the same `build_ai1_features`
  the model was trained on, over the 30 days just before go-live (days 70-99: the calibration + validation windows on
  which the calibrator, conformal sets and alert thresholds were fitted): `reference_bins.json`. The train split
  (days 14-69) is kept as `reference_bins_train.json`. We measured that a train-split reference raises alerts on
  perfectly normal test-window traffic, because tenure, wallet age and first-time-pair depend on how much history
  exists (PSI 0.24 / 0.19 / 0.34; `drift_shadow_window_train_reference.json`), so the deployed reference is the most
  recent pre-deployment window and is refreshed at every retrain.
* Live: the feature-worker keeps a sliding window of the last 30,000 p2p transfers (about 7 days here, so day-of-week
  never aliases: a 20,000 window covering ~5 days gave `dow` a PSI of 3.7 on normal traffic) and computes PSI per
  feature; exposed as `uvera_feature_psi{feature}`, `uvera_drift_status` and `GET /drift` (worker port 9100).
* Thresholds: PSI >= 0.1 warn (ticket), >= 0.2 alert (page), as Prometheus rules `FeatureDriftWarn` / `FeatureDriftAlert`.

Retraining trigger policy (the registry itself is `artifacts/registry.json` + `scripts/model_registry.py`, built separately):

1. **Trigger**: `FeatureDriftAlert` for 1 h on any feature, OR the weekly label-delayed check from `fraud_labels`
   (recall at red or false pauses per 1,000 outside the model card's band), OR a scheduled monthly retrain.
2. **Retrain job**: rebuild features with `build_ai1_features` on the most recent window, the same leakage-safe splits,
   the same pre-registered selection rule; outputs a candidate with its metrics, manifest hashes and data version.
3. **Candidate -> registry**: registered as `candidate`; a human approves (model card, fairness slices, calibration)
   before it can serve. Registry records who approved and when.
4. **Shadow**: the candidate scores the live stream next to the champion (the shadow path in this stack), decisions
   stored with their `model_version`; compared on the same transfers once labels arrive.
5. **Canary**: a small share of scorer replicas (e.g. 1 of 10) load the candidate; Prometheus compares p99 latency,
   error rate, pause rate and PSI of the scores between versions.
6. **Promote or roll back**: promote = point the registry's champion to the candidate and roll the scorer Deployment
   (every replica re-verifies hashes at start); roll back = point the champion back, which is a restart, not a rebuild.

## Limitations (honest)

* One laptop, not a cluster: the load generator, nginx, Redis, Postgres, Prometheus and every replica share the same
  12 hardware threads (and other jobs were running). Absolute numbers are a lower bound for dedicated hardware;
  the shape of the curves (replicas vs throughput, tail latency vs concurrency) is the evidence.
* Redis and Postgres are single instances (no replication, no Redis Cluster, no Postgres HA); in production they would
  be managed services. Redis persistence is off for benchmarking.
* The stream is a single Redis Stream. Several feature-workers in one consumer group share it, but per-wallet ordering
  across workers is then not guaranteed; exact ordering needs partitioning by wallet (Kafka partitions, or N streams).
  Delivery is at-least-once: a crash between applying and acknowledging a batch can double-count that batch.
* The synthetic world is small (20,000 wallets). The online store holds about 30 days of per-day counters per wallet;
  memory scales linearly with active wallets.
* Shadow mode sends the worker's point-in-time features to `POST /score/batch` (micro-batches of 32, exact and
  replayable); the live pre-transfer path (`POST /score/transfer`) reads them from Redis instead. Both paths run the
  same model, policy and reason code. A first version sent one HTTP call per transfer from the worker and was capped
  at ~430 events/s by client overhead; micro-batching removed that bottleneck.
* The feature-worker is single-threaded Python: about 4.8k events/s per worker with the hiredis parser (2.7k without).
  Higher volume needs more workers on a partitioned stream (or a compiled consumer); Redis itself stayed below 15% CPU.
* The Kubernetes manifests in `k8s/` are a documented template and were not run.
* Grafana (profile `dashboards`) is provisioned (datasource + dashboard JSON) but its image was not pulled or run during
  the measurements (slow network, tight RAM); Prometheus itself was running and scraping every replica throughout.
* AI-2 is served with the TF-IDF + LR variant (CPU-cheap); the BGE-M3 embedding variant would need its own GPU/CPU pool.
