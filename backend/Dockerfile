# UVERA API image. Build from the repo root:  docker build -f backend/Dockerfile -t uvera-api .
# Library versions match the Kaggle runs (reports/versions_nb*.json), so the saved models load exactly
# and the seeded synthetic world is rebuilt bit-for-bit at build time.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PORT=7860 UVERA_ROOT=/app MODEL_DIR=/app/artifacts WORLD_DIR=/app/_outputs/world_full \
    DB_PATH=/tmp/uvera.db LLM_MODE=cached
WORKDIR /app

# LightGBM needs the OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install "numpy==2.0.2" "pandas==2.3.3" "scikit-learn==1.6.1" "lightgbm==4.6.0" "pyarrow>=15"

COPY ml/ ml/
COPY backend/ backend/
RUN pip install ./ml ./backend

COPY configs/ configs/
COPY policy_cards/ policy_cards/
COPY scenarios/ scenarios/
COPY artifacts/ artifacts/
COPY reports/ reports/

# Bake the seeded synthetic world into the image, so the API is ready in under a minute after a cold start
RUN python -c "from uvera_ml.sim.world import load_or_generate; load_or_generate('/app/_outputs/world_full', scale='full')"

# Hugging Face Spaces run containers as user 1000
RUN useradd -m -u 1000 user && chown -R user /app
USER user

WORKDIR /app/backend
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
