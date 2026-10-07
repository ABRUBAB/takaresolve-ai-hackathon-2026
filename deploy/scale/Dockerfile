# One small image for every Python role of the scale stack (scorer, feature-worker, producer, load generator).
# Model files are NOT baked in: they are mounted read-only and verified against artifacts/manifest.json at start.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    PYTHONPATH=/srv:/repo/ml UVERA_ROOT=/repo

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 120 --retries 10 -r requirements.txt

COPY uvscale /srv/uvscale
COPY reference_bins.json /srv/reference_bins.json

RUN useradd -u 10001 -m app
USER app
EXPOSE 8000 9100
