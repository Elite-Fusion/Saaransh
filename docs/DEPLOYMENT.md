# Saaransh AI — Deployment Guide

This guide covers deploying Saaransh AI to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Environment Variables](#environment-variables)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.12+ (for local development)
- PostgreSQL 16+ (or Supabase account)
- Google Gemini API key

---

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/your-org/saaransh-ai.git
cd saaransh-ai
```

### 2. Setup Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Setup Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your API URL

npm run dev
```

### 4. Access Services

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Health Check**: http://localhost:8000/api/v1/health

---

## Docker Deployment

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production

```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Scale backend
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

---

## Production Deployment

### Option 1: Docker Compose (Recommended)

1. **Clone and configure**:
   ```bash
   git clone https://github.com/your-org/saaransh-ai.git
   cd saaransh-ai
   cp backend/.env.example backend/.env.production
   # Edit backend/.env.production with production values
   ```

2. **Start services**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Verify**:
   ```bash
   curl http://localhost/api/v1/health
   ```

### Option 2: Railway/Render

#### Backend (Railway)

1. Connect GitHub repository
2. Set environment variables
3. Deploy will auto-detect Python and use `requirements.txt`

#### Frontend (Vercel)

1. Connect GitHub repository
2. Set build command: `npm run build`
3. Set output directory: `dist`
4. Set environment variable: `VITE_API_BASE_URL`

### Option 3: Kubernetes

See `k8s/` directory for Kubernetes manifests (future).

---

## Environment Variables

### Backend

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_NAME` | Application name | Saaransh AI | No |
| `APP_VERSION` | Version string | 1.0.0 | No |
| `ENVIRONMENT` | deployment env | development | No |
| `DEBUG` | Debug mode | true | No |
| `HOST` | Server host | 0.0.0.0 | No |
| `PORT` | Server port | 8000 | No |
| `DATABASE_URL` | PostgreSQL URL | - | Yes |
| `GEMINI_API_KEY` | Gemini API key | - | Yes |
| `JWT_SECRET_KEY` | JWT secret | - | Yes |
| `CORS_ORIGINS` | Allowed origins | localhost | No |
| `LOG_LEVEL` | Log level | INFO | No |
| `LOG_FORMAT` | json/text | text | No |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | http://localhost:8000/api/v1 |

---

## Monitoring

### Health Endpoints

- **Basic Health**: `GET /api/v1/health`
- **Readiness**: `GET /api/v1/ready`
- **Liveness**: `GET /api/v1/live`

### Docker Health Checks

All Docker containers include health checks:
- Backend: checks `/api/v1/health` every 30s
- Frontend: checks root endpoint every 30s
- PostgreSQL: checks `pg_isready` every 10s

### Logging

Logs are structured JSON in production:
```bash
# View backend logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Filter by level
docker-compose -f docker-compose.prod.yml logs -f backend | grep '"level":"ERROR"'
```

---

## Troubleshooting

### Common Issues

1. **Database connection refused**
   - Check `DATABASE_URL` in `.env`
   - Ensure PostgreSQL is running
   - Check firewall rules

2. **CORS errors**
   - Add frontend URL to `CORS_ORIGINS`
   - Format: `http://localhost:5173,https://your-domain.com`

3. **JWT authentication failing**
   - Regenerate `JWT_SECRET_KEY`: `openssl rand -hex 32`
   - Ensure same secret on all instances

4. **WebSocket connection failed**
   - Check proxy configuration for WebSocket upgrade
   - Ensure `proxy_read_timeout` is足够长

### Health Check Failures

```bash
# Check component status
curl http://localhost:8000/api/v1/health | jq

# Expected response:
{
  "status": "ok",
  "components": [
    {"name": "database", "status": "up"},
    {"name": "websocket", "status": "up"},
    {"name": "gemini_api", "status": "up"}
  ]
}
```

---

## Backup & Recovery

See [BACKUP_RECOVERY.md](./BACKUP_RECOVERY.md) for detailed backup procedures.

---

## Security

- All secrets stored in environment variables
- JWT tokens for authentication
- Rate limiting enabled
- Security headers configured
- CORS restricted to allowed origins

---

## Support

For deployment issues:
- Check logs: `docker-compose logs -f`
- Health check: `curl http://localhost/api/v1/health`
- API docs: http://localhost/docs
