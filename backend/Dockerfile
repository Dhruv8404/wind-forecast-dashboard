# ── Backend: Wind Forecast Intelligence API ──────────────────────────────────
# Python 3.12 slim image keeps the layer small while supporting all dependencies.

FROM python:3.12-slim

# Prevents Python from writing .pyc files and ensures stdout/stderr are unbuffered.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS-level build tools only when a package needs them (none here, but
# kept as a best-practice layer so adding C-extension packages later is painless).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first so Docker can cache this layer independently of code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY app/ ./app/

# Expose the port uvicorn will listen on.
EXPOSE 8000

# Run the FastAPI app.
# --host 0.0.0.0 binds to all container interfaces so Docker can route traffic.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
