# Deploying UVERA

**The website runs on its own.** When no live API is reachable, it plays back real responses that were recorded from the
API for every demo scenario (`frontend/public/data/snapshot.json`, made by `scripts/export_snapshot.py`) and shows a
"Recorded demo" badge. So the hosted demo always works, even on free static hosting. A live API is optional and adds free
typing (any SMS, any transfer) on top of the recorded scenarios.

| Part | Where | Cost |
|---|---|---|
| Website (required) | Vercel, Hobby plan | Free |
| Live API (optional) | Your laptop, optionally made public with a free Cloudflare Quick Tunnel | Free |

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

Create `frontend/.env.local` with one line, `NEXT_PUBLIC_API_BASE=http://localhost:8000` (without it a production build
uses the recordings only), then:

```bash
cd frontend && npm run build && npm run start
```

Open `http://localhost:3000`. The site uses the live API and answers any SMS or transfer typed in. Or run both with
`docker compose up --build` (first copy `.env.example` to `.env`).

### B. Make the laptop API public for the hosted site (free, Cloudflare Quick Tunnel)

The API needs about 1–2 GB of RAM, so free 512 MB hosts (Render, Koyeb) cannot run it, and new Hugging Face Docker
Spaces need a paid plan since July 2026. A Cloudflare Quick Tunnel gives the API on your laptop a public HTTPS address
for free, with no account. The address works only while your laptop and the tunnel are running and changes on every
start, so use it for a live session; the recorded mode covers the rest of the time.

1. Install the tunnel client once (Windows): `winget install --id Cloudflare.cloudflared`
2. Start the API with your Vercel address allowed (PowerShell):
   `$env:ALLOWED_ORIGINS="https://<your-site>.vercel.app"; cd backend; uvicorn app.main:app --port 8000`
3. In a second terminal: `cloudflared tunnel --url http://localhost:8000` and copy the `https://….trycloudflare.com`
   address it prints. Check `<that address>/v1/health/ready` says `ready`.
4. In Vercel set `NEXT_PUBLIC_API_BASE` to that address and **Redeploy**. To go back to recorded mode, delete the
   variable and redeploy.

Anyone with the address can reach the API, which serves synthetic data only. Stop the tunnel when the session ends.

## 4. After new Kaggle results

Commit the new files in `artifacts/` and `reports/`, re-run step 1, push. Vercel redeploys automatically.
