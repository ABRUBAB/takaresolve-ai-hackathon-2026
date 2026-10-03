# Architecture

Business rules are kept separate from model predictions (Guideline p9 §12): models estimate, YAML rules decide which
actions are offered, and a person approves anything that holds money.

## 1. System
```mermaid
flowchart LR
  subgraph Web["Next.js website (Vercel)"]
    H[Homepage + 3D Trust Field]:::p
    C[Customer]:::p
    A[Agent]:::p
    O[Operations]:::p
    T[Trust Center]:::p
    SNAP[(Recorded real API responses)]
  end
  subgraph API["FastAPI /v1 (own computer or any Docker host)"]
    R[/Routes · JWT roles · rate limit · trace id/]
    S[Engines: AI-1 pause · AI-2 text · AI-3/4 forecasts · AI-5 QR · AI-6 cases]
    P[Policy: frozen thresholds + configs/rules/*.yaml]
    B[AI-7 brief: cache → Gemini → validator → template]
    DB[(SQLite: case status · decisions · audit log)]
    ART[(artifacts/ · reports/ · configs/)]
  end
  subgraph Kaggle["Kaggle notebooks NB00–NB99 (offline)"]
    K[Generate world · train · calibrate · test once · export]
  end
  H & C & A & O & T -- HTTPS JSON --> R --> S --> P --> B
  S --> ART
  R --> DB
  Web -. API offline or waking .-> SNAP
  K -- artifacts + reports via GitHub --> ART
  classDef p fill:#111,stroke:#D7FF3A,color:#FAFAFA
```

## 2. One Pause Check request
```mermaid
sequenceDiagram
  participant U as Customer screen
  participant API as POST /v1/pause-check
  participant F as Features (19, before the transfer only)
  participant M as LightGBM → isotonic → conformal + novelty
  participant Pol as Policy (actions.yaml)
  participant B as Brief (cache / Gemini / template)
  U->>API: draft transfer (+ optional message → AI-2)
  API->>F: sender, receiver and moment features
  F->>M: score, calibrated probability, conformal set, unusual-input flag
  M-->>Pol: state: low · elevated · high · not sure
  Pol-->>API: recommended actions + human-review flag
  API->>B: evidence JSON (exact TreeSHAP reasons, rules)
  B-->>API: Bangla + English text (validated) or template
  API-->>U: envelope: trace id, model and data versions, decision, reasons, brief
  Note over API: a model error returns the transparent rule check, marked degraded
```

## 3. The golden thread across the three areas
```mermaid
flowchart TD
  A[Rubab drafts a Tk 3,000 'prize fee' transfer] --> B{Pause Check}
  B -- high, confident --> C[Paused: three reasons + wait / verify / ask / continue]
  B -- not sure --> D[Soft warning; a person reviews large amounts]
  C --> E[The receiving mule wallet moves money on within 48 h]
  E --> F[QR payments at a shop look like disguised cash-out]
  F --> G[QR Shield flags the shop]
  G --> H[Case Linker joins the linked alerts into one case, CASE-0001]
  H --> I[Operations: graph, brief, dispute clock]
  I --> J{Abdur Rahman decides, with a reason}
  G --> L[Tanvir sees zone-level QR pressure + cash to hold]
```

## 4. Hosting
- **Website:** Vercel. With no live API connected, it plays back real responses recorded from the API for every demo
  scenario, so the link always works.
- **Live API:** our own computer (or any Docker host), optionally made public with a Cloudflare Quick Tunnel or
  Tailscale Funnel. See [`deploy.md`](deploy.md).
