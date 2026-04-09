# Dockerfile — Multi-stage build for the laidlaw decarbonisation comparator.
#
# Stage 1 (builder) installs dev dependencies and runs the test suite so the
# build fails fast on regressions. Stage 2 (runtime) ships only the runtime
# deps, the FastAPI app, the data assumptions, and the frontend, and runs as
# a non-root user.

# ──────────────────────────────────────────────────────────────────────────
# Stage 1 — Builder
# ──────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY backend/ ./backend/
COPY data/ ./data/
COPY frontend/ ./frontend/

RUN pip install --upgrade pip \
 && pip install -e ./backend[dev] \
 && cd backend && pytest -q --no-cov

# ──────────────────────────────────────────────────────────────────────────
# Stage 2 — Runtime
# ──────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 1000 laidlaw \
 && useradd  --system --uid 1000 --gid laidlaw --create-home laidlaw

WORKDIR /app
COPY backend/ ./backend/
COPY data/ ./data/
COPY frontend/ ./frontend/

RUN pip install --upgrade pip && pip install ./backend && rm -rf /root/.cache

USER laidlaw
WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
