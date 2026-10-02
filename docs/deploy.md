# Deploying UVERA

Two free services: the API on a **Hugging Face Docker Space**, the website on **Vercel**. Both build from this repository.
Everything also runs locally (see the README) or with `docker compose up`.

## 1. API on Hugging Face Spaces

1. Create a new Space → SDK **Docker** → blank template, CPU basic (free).
2. Upload `deploy/huggingface/Dockerfile` and `deploy/huggingface/README.md` to the Space (the README header sets port 7860).
3. Space → Settings → Variables and secrets:
   - `ALLOWED_ORIGINS` = the website address (e.g. `https://uvera.vercel.app`)
   - `JWT_SECRET` = a long random string (as a secret)
4. The Space clones this repository, installs the same library versions the Kaggle notebooks used, and rebuilds the seeded
   synthetic world inside the image. After a cold start the AI engines are ready in about a minute; the website shows a
   "waking up" state meanwhile.
5. Check: `https://<user>-<space>.hf.space/v1/health/ready` returns `{"status": "ready"}`.

To build the same image locally: `docker build -f backend/Dockerfile -t uvera-api .` then `docker run -p 7860:7860 uvera-api`.

## 2. Website on Vercel

1. Import the GitHub repository in Vercel. **Root directory: `frontend`** (framework is detected as Next.js).
2. Environment variable: `NEXT_PUBLIC_API_BASE` = the Space address, e.g. `https://<user>-<space>.hf.space`.
3. Deploy. Then put the Vercel address into the Space's `ALLOWED_ORIGINS` and restart the Space.

## 3. After new Kaggle results

New result files are committed to `artifacts/` and `reports/`. Re-run `python scripts/export_web_assets.py` if NB00 changed,
push to GitHub, then restart the Space (Settings → Factory rebuild) so it picks up the new files. Vercel redeploys on push.
