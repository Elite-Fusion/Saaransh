# Saaransh AI — Root Production Dockerfile for Render

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 & curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from backend directory
COPY backend/requirements.txt ./backend/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy full application code
COPY . .

# Set PYTHONPATH to root directory so `backend` module is importable
ENV PYTHONPATH=/app

# Run uvicorn on Render's dynamic $PORT (fallback 8000)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
