# Build from the repo root:  docker build -f backend/Dockerfile -t uvera-api .
# Hugging Face Docker Spaces expect the app on port 7860 (PORT is overridable).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860 MODEL_DIR=/app/artifacts
WORKDIR /app

COPY ml/ ml/
COPY backend/ backend/
RUN pip install --no-cache-dir ./ml ./backend

COPY configs/ configs/
COPY policy_cards/ policy_cards/
COPY scenarios/ scenarios/
COPY artifacts/ artifacts/

WORKDIR /app/backend
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
