---
title: UVERA API
emoji: ⏸️
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Trust you can verify. Synthetic demo API for AI DEV FEST 2026.
---

# UVERA API (synthetic demo)

FastAPI service behind the UVERA website. All data is synthetic. Source, notebooks and model cards:
https://github.com/ABRUBAB/takaresolve-ai-hackathon-2026

Space settings → Variables and secrets:

| Name | Value |
|---|---|
| `ALLOWED_ORIGINS` | the website address, e.g. `https://uvera.vercel.app` |
| `JWT_SECRET` | any long random string (secret) |
