# Deploying UVERA

**The website runs on its own.** When no live API is reachable, it plays back real responses that were recorded from the
API for every demo scenario (`frontend/public/data/snapshot.json`, made by `scripts/export_snapshot.py`) and shows a
"Recorded demo" badge. So the hosted demo always works, even on free static hosting. A live API is optional and adds free
typing (any SMS, any transfer) on top of the recorded scenarios.

| Part | Where | Cost |
|---|---|---|
| Website (required) | Vercel, Hobby plan | Free |
| Live API (optional) | Your laptop (best for the on-site final) or a Hugging Face Docker Space | Free / Hugging Face PRO ($9 per month) |

## 1. Before you deploy: refresh the recorded responses

Run this after the last Kaggle results are committed, so the recordings come from the official models.

```bash
cd backend && uvicorn app.main:app --port 8000
```

In a second terminal, once `http://localhost:8000/v1/health/ready` says `ready`:

```bash
python scripts/export_snapshot.py
```

```bash
python scripts/export_web_assets.py
```

Commit both changed files in `frontend/public/data/` and push to GitHub.

## 2. Website on Vercel (free)

1. Sign in at vercel.com with GitHub and choose **Add New… → Project**.
2. Import the GitHub repository `takaresolve-ai-hackathon-2026`.
3. In the import screen set **Root Directory** to `frontend` (later: Project **Settings → Build and Deployment → Root
   Directory**). The framework is detected as **Next.js**; keep the default build settings.
4. Environment variables (Project **Settings → Environment Variables**), Production:
   - `NEXT_PUBLIC_SITE_URL` = the address Vercel gives you, for example `https://uvera.vercel.app` (used for share previews).
   - `NEXT_PUBLIC_API_BASE`: leave it **unset** for recorded mode, or set it to a live API address (step 3).
5. **Deploy.** Every push to `main` deploys again. Environment-variable changes apply only to new deployments: after
   changing one, open **Deployments** and choose **Redeploy** on the latest one.

Check: open the site, press **Run a scam through it** on the homepage and **Send** on the phone. The result appears and the
top bar shows **Recorded demo**.

## 3. Live API (optional)

### A. On your laptop (recommended for the on-site final, 7 Oct)

Nothing depends on the venue's internet except the browser:

```bash
cd backend && uvicorn app.main:app --port 8000
```

```bash
cd frontend && npm run build && npm run start
```

Open `http://localhost:3000`. The site uses the live API and answers any SMS or transfer typed in. Or run both with
`docker compose up --build` (first copy `.env.example` to `.env`).

### B. Hugging Face Docker Space (needs a Hugging Face PRO plan)

Since July 2026 Hugging Face requires a paid plan (PRO, $9/month for a personal account) to create new Docker Spaces.

1. Create a Space: **New Space → SDK: Docker → Blank**, hardware **CPU basic** (2 vCPU, 16 GB RAM).
2. Upload `deploy/huggingface/Dockerfile` and `deploy/huggingface/README.md` to the Space (**Files → Add file → Upload files**).
   The README header sets `sdk: docker` and `app_port: 7860`. The Dockerfile clones this public GitHub repository, installs
   the library versions the Kaggle notebooks used, and rebuilds the seeded synthetic world inside the image.
3. Space **Settings → Variables and secrets**: variable `ALLOWED_ORIGINS` = your Vercel address; secret `JWT_SECRET` = a long
   random string.
4. Wait for the build, then check `https://<user>-<space>.hf.space/v1/health/ready` (about a minute after each start).
5. In Vercel set `NEXT_PUBLIC_API_BASE` = `https://<user>-<space>.hf.space` and redeploy.

Free-hardware Spaces sleep when unused; while the API wakes up, the website keeps answering from the recordings.
`.github/workflows/keepwarm.yml` pings the API every 6 hours once you add the repository secret `API_HEALTH_URL`.

## 4. After new Kaggle results

Commit the new files in `artifacts/` and `reports/`, re-run step 1, push. Vercel redeploys automatically; a Hugging Face
Space rebuilds from GitHub with **Settings → Factory rebuild**.
