# Slim Python image sized for a small free-tier host. Python 3.14 matches local dev.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first so re-deploys with only source changes stay in Docker's layer cache.
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install ".[turso]"

# App code.
COPY app ./app

# Default port for local runs; Render (and most PaaS providers) set $PORT and the app must bind
# to it. The shell form of CMD is used so $PORT is expanded at container start.
ENV PORT=8000
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
