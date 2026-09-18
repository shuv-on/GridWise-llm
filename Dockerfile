# ---------- Stage 1: Build ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer cache)
COPY requirements.txt .

# Install Python deps into a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

# Non-root user
RUN useradd --create-home --shell /bin/bash gridwise

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY app/ /app/app/
COPY scripts/ /app/scripts/
COPY data/ /app/data/

# Ensure no .env is copied (defense in depth)
RUN rm -f /app/.env

# Switch to non-root user
USER gridwise

# Expose the service port
EXPOSE 8000

# Bind to 0.0.0.0
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# Healthcheck so orchestrators can detect readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run with uvicorn (single worker; increase for production)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]