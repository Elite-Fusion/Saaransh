# Saaransh AI

> **AI-powered Crime Investigation Assistant for the Karnataka State Police Datathon.**

Saaransh lets police officers query the KSP FIR database in natural language (English and Kannada), detect similar cases, surface cross-case links (shared phones, addresses, vehicles, gang membership), and get explainable, evidence-backed answers. Every response cites the cases it relied on — the system never invents a `case_id` or an FIR number.

## Core Principles

1. **Accuracy** — answers are grounded in real records, not generated from model priors.
2. **Explainability** — every response carries a `why`, an `evidence` list, and a `confidence` level.
3. **Maintainability** — provider-independent layers so swapping the LLM is a one-file change.
4. **Modularity** — every component can be replaced in isolation (provider, prompt template, embedding model, graph backend).
5. **Security** — secrets in `.env`, parameterised SQL, read-only prompt templates, full audit logging.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, React Router, React Query, Recharts |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL (Supabase), pgvector |
| AI | Google Gemini API (provider-independent abstraction) |
| ML | scikit-learn (DBSCAN, Random Forest, Gradient Boosting, TF-IDF) |
| Real-Time | WebSocket (FastAPI), event bus, connection manager |
| Auth | JWT (python-jose), bcrypt, RBAC |
| Deployment | Docker, Nginx, GitHub Actions CI/CD |

---

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Backend foundation (FastAPI + SQLAlchemy + Pydantic) | ✅ |
| 2 | Database schema (30+ ORM models, ER docs) | ✅ |
| 3 | Case APIs (list, detail, filters, pagination) | ✅ |
| 4 | Analytics (dashboard summary, trends, distributions) | ✅ |
| 5 | AI foundation (provider abstraction, Gemini, prompt loader) | ✅ |
| 6 | Investigation engine (intent classifier, SQL validator, explanation) | ✅ |
| 7 | Frontend (React, routing, pages, components) | ✅ |
| 8 | Hybrid AI (NL-to-SQL, similarity, cross-case linking) | ✅ |
| 9 | Predictive intelligence (hotspots, trends, clustering, risk scoring) | ✅ |
| 10 | Authentication (JWT, RBAC, audit logging) | ✅ |
| 11 | Real-time intelligence (WebSocket, notifications, presence) | ✅ |
| 12 | Production deployment (Docker, Nginx, CI/CD, monitoring) | ✅ |

---

## Repository Layout

```
saaransh-ai/
├── backend/
│   ├── api/v1/            # HTTP routers (auth, cases, dashboard, ai, predictions, health, monitoring, ws)
│   ├── ai/                # AI provider abstraction + prompt templates
│   ├── config/            # Settings, structured logging
│   ├── database/          # SQLAlchemy engine + session
│   ├── middleware/         # Audit, auth, security headers, rate limiting
│   ├── models/            # ORM models (30+ tables)
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # Business logic (FastAPI-independent)
│   ├── tests/             # 692+ tests (pytest)
│   ├── websocket/         # ConnectionManager, EventBus
│   └── main.py            # Application entry point
├── frontend/
│   ├── src/
│   │   ├── api/           # Axios API client with JWT interceptors
│   │   ├── components/    # Card, StatusStates, ProtectedRoute
│   │   ├── contexts/      # AuthContext, WebSocketContext
│   │   ├── hooks/         # useWebSocket, useNotifications, useLiveDashboard, usePresence
│   │   ├── layout/        # Sidebar, Topbar
│   │   ├── pages/         # Login, Dashboard, Cases, Map, Predictions, AI Assistant, Analytics, etc.
│   │   └── App.jsx        # Router + providers
│   ├── Dockerfile         # Multi-stage build (node → nginx)
│   └── nginx.conf         # Frontend nginx config
├── backend/
│   └── Dockerfile         # Multi-stage build (python slim)
├── nginx/
│   └── nginx.conf         # Production reverse proxy config
├── docker-compose.yml     # Development (backend + frontend + PostgreSQL)
├── docker-compose.prod.yml# Production (nginx + backend + Redis)
├── .github/workflows/     # CI/CD (backend-ci, frontend-ci, docker-build)
├── docs/                  # Deployment guide, backup & recovery
├── database/              # Schema, seed data, migrations
├── prompts/               # AI prompt templates
├── scripts/               # Utility scripts
└── CLAUDE.md              # AI development rules
```

---

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows
# source .venv/bin/activate          # Linux/macOS

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set GEMINI_API_KEY and DATABASE_URL

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: <http://localhost:8000/docs>
Health check: <http://localhost:8000/api/v1/health>

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# Edit .env — set VITE_API_BASE_URL

npm run dev
```

Frontend: <http://localhost:5173>

### Docker (Development)

```bash
docker-compose up -d
```

### Docker (Production)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |
| `JWT_SECRET_KEY` | HMAC secret for JWT signing | Yes |
| `ENVIRONMENT` | `development` / `staging` / `production` | No |
| `DEBUG` | Enable debug mode | No |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | No |
| `LOG_FORMAT` | `text` (dev) or `json` (prod) | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | No |
| `DB_POOL_SIZE` | Connection pool size | No |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api/v1` |

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` — Login (returns access + refresh tokens)
- `POST /api/v1/auth/refresh` — Refresh access token
- `GET /api/v1/auth/me` — Current user profile

### Cases
- `GET /api/v1/cases` — List FIRs (paginated, filterable, sortable)
- `GET /api/v1/cases/{id}` — Case detail

### Dashboard & Analytics
- `GET /api/v1/dashboard/summary` — Dashboard summary stats
- `GET /api/v1/dashboard/trends` — Monthly trends
- `GET /api/v1/dashboard/crime-head-distribution` — Crime type breakdown
- `GET /api/v1/dashboard/district-distribution` — District breakdown
- `GET /api/v1/dashboard/recent-cases` — Recent cases

### AI Investigation
- `POST /api/v1/ai/investigate` — Natural language crime investigation

### Predictions
- `GET /api/v1/predictions/hotspots` — Crime hotspot prediction
- `GET /api/v1/predictions/trends` — Trend forecasting
- `GET /api/v1/predictions/repeat-offenders` — Repeat offender detection
- `GET /api/v1/predictions/clusters` — Crime pattern clustering
- `GET /api/v1/predictions/risk-score/{case_id}` — Case risk scoring
- `GET /api/v1/predictions/similar-cases/{case_id}` — Similar case detection
- `GET /api/v1/predictions/recommendations/{case_id}` — Officer recommendations

### Real-Time
- `WebSocket /api/v1/ws?token=<JWT>` — Live event stream
- `GET /api/v1/notifications` — List notifications
- `GET /api/v1/notifications/unread-count` — Unread count
- `POST /api/v1/notifications/{id}/read` — Mark read
- `POST /api/v1/notifications/read-all` — Mark all read
- `GET /api/v1/presence/online` — Online officers
- `GET /api/v1/presence/me` — My presence

### Monitoring
- `GET /api/v1/health` — Health check (database, WebSocket, API key)
- `GET /api/v1/ready` — Readiness probe
- `GET /api/v1/live` — Liveness probe

---

## Architecture

```
React Frontend
    ↓ (Axios + JWT)
FastAPI Backend
    ↓
Service Layer (FastAPI-independent)
    ↓
AI Service → Provider Abstraction → Gemini API
    ↓
PostgreSQL + Supabase + pgvector
    ↓
Machine Learning (scikit-learn)
    ↓
WebSocket → Real-Time Events
```

---

## Testing

```bash
cd backend
pytest tests/ -v
```

**692 tests pass** across:
- Authentication & RBAC (13 tests)
- Case APIs (22 tests)
- Dashboard & Analytics (40+ tests)
- AI Investigation (200+ tests, mocked Gemini)
- Predictive ML (100+ tests)
- WebSocket & Real-Time (33 tests)
- OpenAPI Documentation (14 tests)
- Service Independence (AST-scanned, no FastAPI imports in services)

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment guide.

### Docker

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend
cd frontend
npm install && npm run build
# Serve dist/ with nginx or any static server
```

### CI/CD

GitHub Actions workflows run on every push:
- **Backend CI**: Lint (ruff), type check (mypy), tests (pytest), security scan (bandit)
- **Frontend CI**: Lint (eslint), build (vite), tests
- **Docker Build**: Build and push images on version tags

---

## Security

- JWT authentication with access/refresh token flow
- Role-based access control (admin, sp, dsp, inspector, si, psi, constable)
- Rate limiting (60 req/min per IP)
- Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- CORS restricted to configured origins
- SQL injection prevention (parameterised queries, read-only SQL execution)
- Audit logging for all mutating operations
- Secrets stored in environment variables, never hardcoded

---

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md)
- [Backup & Recovery](docs/BACKUP_RECOVERY.md)
- [API Documentation](http://localhost:8000/docs) (Swagger, when running)
- [CLAUDE.md](CLAUDE.md) — AI development rules

---

## License

Internal — Karnataka State Police Datathon.
