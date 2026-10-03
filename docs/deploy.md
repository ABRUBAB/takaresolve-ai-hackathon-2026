# Deploying UVERA

**The website runs on its own.** When no live API is reachable, it plays back real responses recorded from the API for
every demo scenario (`frontend/public/data/snapshot.json`) and shows a "Recorded demo" badge, so the hosted link always
works. A live API adds free typing (any message, any transfer) on top.

| Part | Where | Cost |
|---|---|---|
| Website (required) | Vercel, Hobby plan | Free |
| Live API (optional) | Our own Windows computer, made public with Tailscale Funnel (fixed address) or a Cloudflare Quick Tunnel | Free |

Why not a free cloud server: the API needs about 1.2 GB of RAM (measured), free web-service plans offer 512 MB, and new
Hugging Face Docker Spaces need a paid plan since July 2026.

## 1. Refresh the website data after new results
After the last notebook results are in `artifacts/` and `reports/`:

```bash
python scripts/finalize.py
```

It rebuilds the results summary and model cards, runs the API in-process to record every demo response, copies the
figures, updates the README table and commits. Then `git push` (Vercel redeploys by itself).

## 2. Website on Vercel (free)
1. Sign in at vercel.com with GitHub → **Add New… → Project** → import `takaresolve-ai-hackathon-2026`.
2. **Project name `uvera-ai`** (gives `https://uvera-ai.vercel.app`) and **Root Directory `frontend`**. Framework Next.js,
   default build settings.
3. Leave `NEXT_PUBLIC_API_BASE` **unset** for recorded mode. **Deploy.**
4. Check: homepage → **Run a scam through it** → **Send**: the result appears and the top bar shows **Recorded demo**.

Every push to `main` redeploys. Environment-variable changes apply only to new deployments: **Deployments → ⋯ → Redeploy**.

## 3. Live API on a Windows computer
Needs Python 3.12, Git and about 2 GB of free RAM; no GPU.

```powershell
git clone https://github.com/ABRUBAB/takaresolve-ai-hackathon-2026.git C:\uvera
cd C:\uvera
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -c constraints.txt -e ./ml -e ./backend
copy .env.example .env
```

In `.env` set `ALLOWED_ORIGINS=https://uvera-ai.vercel.app,http://localhost:3000` and `RATE_LIMIT_PER_MINUTE=600`.
Start it (it restarts itself if it stops; the first start builds the synthetic world in about 45 seconds):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_api.ps1
```

Check `http://127.0.0.1:8000/v1/health/ready` says `ready`, then `.venv\Scripts\python scripts\smoke_api.py` prints `ALL OK`.
Use `127.0.0.1`, not `localhost`: on Windows, `localhost` first tries IPv6 and can add about 2 seconds per request.

### Make it public — option A: Tailscale Funnel (fixed address, survives restarts)
1. Install Tailscale and sign in (free Personal plan).
2. `tailscale funnel --bg http://127.0.0.1:8000` — if it prints a link to enable HTTPS or Funnel for your tailnet, open it,
   approve, and run the command again.
3. `tailscale funnel status` shows the address, `https://<computer>.<tailnet>.ts.net`.
4. In Vercel set `NEXT_PUBLIC_API_BASE` to that address (no trailing slash) and **Redeploy**.
5. To stop: `tailscale funnel reset`.

### Option B: Cloudflare Quick Tunnel (no account; the address changes on every start)
`cloudflared tunnel --url http://127.0.0.1:8000`, then put the printed `https://….trycloudflare.com` address in Vercel and
redeploy. Repeat after every restart.

Anyone with the address can reach the API, which serves synthetic data only, issues demo logins and is rate-limited. The
API listens on 127.0.0.1, so no firewall port is opened. To return to recorded mode, delete `NEXT_PUBLIC_API_BASE` in
Vercel and redeploy.

## 4. Running everything on one laptop (no internet needed)
```bash
cd backend && uvicorn app.main:app --port 8000
```
Create `frontend/.env.local` with `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`, then:
```bash
cd frontend && npm install && npm run build && npm run start
```
Open `http://localhost:3000`. Or run both with `docker compose up --build`.
