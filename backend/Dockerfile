# Slim Python image sized for a small free-tier host.
#
# Pinned to 3.13 rather than 3.14 (local dev's version) because the libsql driver behind the
# [turso] extra ships prebuilt wheels only up to cp313. On 3.14 pip falls back to building the
# Rust crate from source, which fails here — this image has no C compiler or Rust toolchain, and
# adding them would balloon the image and blow past free-tier build limits.
# Revisit once libsql-experimental publishes cp314 wheels.
FROM python:3.13-slim

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
