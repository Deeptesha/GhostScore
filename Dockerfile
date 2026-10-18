# GhostScore — container image (repo-root build context)
#
# The image mirrors the repository layout so the app's relative path logic works unchanged:
#   /app/backend/        FastAPI app        (main.py, app/)
#   /app/frontend/       Stitch UI          (served at /ui)
#   /app/ml/artifacts/   trained model      (loaded by app/gcp/__init__.py)
#
# GHOSTSCORE_MODE defaults to "local": every Google Cloud call is stubbed and the
# model is the sklearn pipeline trained on UCI Taiwan 2009 data. See README.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GHOSTSCORE_MODE=local \
    PORT=8080

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY ml/artifacts/ ml/artifacts/

# Run as a non-root user
RUN useradd --create-home appuser
USER appuser

WORKDIR /app/backend
EXPOSE 8080

# Cloud Run injects $PORT; default 8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
