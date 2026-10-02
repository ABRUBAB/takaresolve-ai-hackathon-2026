# Hugging Face Docker Space for the UVERA API.
# Copy this file and README.md into a new Space (SDK: Docker). It builds the API from the public GitHub repo.
FROM python:3.12-slim

ARG REPO=https://github.com/ABRUBAB/takaresolve-ai-hackathon-2026.git
ARG REF=main
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PORT=7860 UVERA_ROOT=/app MODEL_DIR=/app/artifacts WORLD_DIR=/app/_outputs/world_full \
    DB_PATH=/tmp/uvera.db LLM_MODE=cached

RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${REF} ${REPO} /app
WORKDIR /app
RUN pip install "numpy==2.0.2" "pandas==2.3.3" "scikit-learn==1.6.1" "lightgbm==4.6.0" "pyarrow>=15" && pip install ./ml ./backend
RUN python -c "from uvera_ml.sim.world import load_or_generate; load_or_generate('/app/_outputs/world_full', scale='full')"

RUN useradd -m -u 1000 user && chown -R user /app
USER user
WORKDIR /app/backend
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
