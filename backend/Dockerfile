# Slim Python image sized for a Fly Machines VM. Python 3.14 matches local dev.
FROM python:3.14-slim

# --no-cache: no wheel cache in the image. --no-compile: skip .pyc; smaller image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first so re-deploys with only source changes stay in Docker's layer cache.
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install .

# App code.
COPY app ./app

# The SQLite file lives on a Fly volume mounted at /data (see fly.toml).
# We tell the app where to put it via DATABASE_URL at runtime.
ENV DATABASE_URL=sqlite:////data/muvi.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
