# Saaransh AI — Backend

FastAPI service for **Saaransh AI**, the conversational crime-investigation
co-pilot built for the Karnataka State Police Datathon.

> **Phase 3 — Read-only Case APIs.** This phase adds `GET /api/v1/cases`
> (paginated, sortable, filterable list) and `GET /api/v1/cases/{case_id}`
> (full case detail with complainant, victims, accused, evidence, recovered
> items, chargesheet, act & sections, and assigned officers), plus the
> service layer, Pydantic schemas, and unit tests that back them.
> No writes, no auth, no AI.
>
> **Phase 3.5 — Documentation & Reusability.** Every endpoint now ships
> with full OpenAPI examples (success, validation error, not found,
> empty results) and curl code samples. The service layer is codified
> behind a `BaseService` abstract class so the upcoming Gemini AI
> provider can reuse it without any FastAPI dependency. See
> [API Versioning](#-api-versioning) below.
>
> **Phase 4 — Analytics Module.** A read-only analytics layer that
> serves both the React dashboard (Phase 4–5) and the future Gemini
> AI provider (Phase 6+). Six new endpoints under
> `/api/v1/dashboard/*` — summary tile, monthly trends, three
> distributions (crime head / status / district) and a recent-cases
> feed — backed by a single FastAPI-independent
> `AnalyticsService`. See [📊 Analytics APIs](#-analytics-apis)
> below.
>
> **Phase 5 — AI Foundation.** A provider-independent AI layer
> that talks to Google Gemini today and can be pointed at
> Claude / OpenAI / Groq / OpenRouter in later phases by
> changing one settings value. The layer ships:
> `AIProvider` ABC, `GeminiProvider`, `ProviderFactory`,
> `PromptService` (loads `backend/ai/prompts/*.md` at
> runtime — no prompt is hardcoded in Python), `ChatService`,
> domain models (`ChatRequest` / `ChatResponse`), exception
> hierarchy, and `backend/ai/docs/ai_api_plan.md` (the
> Phase 6 route spec). No AI HTTP routes yet — those land
> in Phase 6. See [🤖 AI Foundation (Phase 5)](#-ai-foundation-phase-5)
> below.

See `backend/docs/RELATIONSHIPS.md` for a full relationship reference
and `backend/docs/erd.mmd` for the auto-generated ERD.

---

## 📁 Folder Structure

```
backend/
├── api/                # HTTP routers
│   └── v1/
│       ├── __init__.py     # api_router assembly
│       ├── openapi.py      # standard_error_responses() helper
│       ├── examples.py     # literal example payloads (success/empty/…)
│       ├── health.py       # GET /api/v1/health
│       ├── cases.py        # GET /api/v1/cases, GET /api/v1/cases/{id}
│       └── dashboard.py    # GET /api/v1/dashboard/* (Phase 4)
├── config/             # Pydantic settings + logging setup
│   ├── __init__.py
│   ├── settings.py
│   └── logging.py
├── database/           # SQLAlchemy engine + session
│   ├── __init__.py
│   └── session.py
├── models/             # SQLAlchemy ORM models (30 tables)
│   ├── __init__.py         # re-exports every model
│   ├── geography.py        # State, District
│   ├── organisation.py     # UnitType, Unit, Rank, Designation, Employee, Court
│   ├── taxonomy.py         # CrimeHead, CrimeSubHead, Act, Section, lookups…
│   ├── case.py             # CaseMaster + 8 case-centric children
│   └── ai.py               # AuditLog, Users
├── schemas/            # Pydantic request/response models
│   ├── __init__.py
│   ├── common.py           # pagination, sort, error envelope
│   ├── case.py             # case-related response models
│   └── dashboard.py        # analytics response models (Phase 4)
├── services/           # Business logic (FastAPI-independent)
│   ├── __init__.py
│   ├── base.py             # BaseService abstract base
│   ├── case_service.py     # CaseService (list, get_detail, get_summary, count)
│   └── analytics_service.py # AnalyticsService (Phase 4)
├── utils/              # Helpers
│   ├── __init__.py
│   └── pagination.py       # pagination math
├── middleware/         # Auth, audit, error handling
├── ai/                 # AI provider abstraction (added Phase 6+)
│   ├── providers/
│   └── voice/
├── alembic/            # Alembic migrations
│   ├── env.py             # reads DATABASE_URL from settings
│   ├── script.py.mako     # template for new revisions
│   └── versions/          # (empty — first migration in later phase)
├── alembic.ini         # Alembic config
├── docs/               # Phase 2 documentation
│   ├── RELATIONSHIPS.md   # human-readable table-by-table + ER map
│   └── erd.mmd            # Mermaid ER diagram (renders on GitHub)
├── tests/              # Pytest unit tests (no live DB needed)
│   ├── __init__.py
│   ├── conftest.py                # fake-ORM factory functions + fixtures
│   ├── test_case_apis.py          # tests for the case endpoints
│   ├── test_dashboard.py          # tests for the dashboard endpoints
│   ├── test_openapi_examples.py   # OpenAPI documentation contract tests
│   └── test_service_independence.py # service-layer AI-readiness tests
├── pytest.ini
├── main.py             # FastAPI app factory + entry point
├── requirements.txt
├── .env.example
└── README.md
```

The repo root has a `scripts/` folder for project-wide utilities:
```
saaransh-ai/
└── scripts/
    ├── __init__.py
    ├── db_test.py          # verify DB connectivity + schema match
    └── generate_erd.py     # regenerate backend/docs/erd.mmd
```

---

## ⚙️ Prerequisites

- **Python 3.12+** (project target)
- **PostgreSQL 14+** (local install **or** a Supabase project with the
  schema from `database/schema/ksp_real_schema.sql` loaded)
- **pip** + **venv**

---

## 🚀 Quick Start

### 1. Clone & enter the project

```bash
git clone <repo-url>
cd saaransh-ai/backend
```

### 2. Create a virtual environment

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (Git Bash)
python -m venv .venv
source .venv/Scripts/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# then edit .env and set DATABASE_URL
```

For local Postgres the default is fine:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/saaransh
```

For Supabase, use the **Session-mode** connection string (port `5432`),
not the direct `6543` pooler — SQLAlchemy manages pooling itself:

```
DATABASE_URL=postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

### 5. (Optional) Load the schema

If you have a fresh database, load the KSP schema and seed data:

```bash
# From the repo root
psql "<your DATABASE_URL without +psycopg2>" -f database/schema/ksp_real_schema.sql
psql "<your DATABASE_URL without +psycopg2>" -f database/seed/ksp_real_seed.sql
```

### 6. Run the server

```bash
# Option A — uvicorn CLI (recommended during development)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option B — run as a module
python -m backend.main
```

Once running:

- Swagger UI → <http://localhost:8000/docs>
- ReDoc      → <http://localhost:8000/redoc>
- Health     → <http://localhost:8000/api/v1/health>
- Root info  → <http://localhost:8000/>

---

## 🔍 Health Endpoint

`GET /api/v1/health`

Returns `200 OK` when the service **and** the database are reachable,
or `503 Service Unavailable` if the DB is down.

Sample response:

```json
{
  "status": "ok",
  "service": "Saaransh AI",
  "version": "0.1.0",
  "environment": "development",
  "database": "up",
  "timestamp": "2026-07-08T10:15:30.123456+00:00"
}
```

---

## 📂 Case APIs

Both endpoints are **read-only**. All requests go through the SQLAlchemy
ORM — no raw SQL — and every response is a typed Pydantic model that
also shows up in the Swagger schema.

### `GET /api/v1/cases`

List FIRs with pagination, sorting, and seven filters.

| Param               | Type   | Notes                                                         |
|---------------------|--------|---------------------------------------------------------------|
| `fir_number`        | string | Exact match on the 18-digit FIR number                        |
| `district`          | string | Case-insensitive name match on `District`                     |
| `district_id`       | int    | Wins over `district` when both are sent                       |
| `police_station`    | string | Case-insensitive name match on `Unit.UnitName`                |
| `police_station_id` | int    | Wins over `police_station` when both are sent                 |
| `crime_head`        | string | Case-insensitive match on `CrimeHead.CrimeGroupName`          |
| `crime_head_id`     | int    | Wins over `crime_head`                                        |
| `crime_sub_head`    | string | Case-insensitive match on `CrimeSubHead.CrimeHeadName`        |
| `crime_sub_head_id` | int    | Wins over `crime_sub_head`                                    |
| `status`            | string | Case-insensitive match on `CaseStatusMaster.CaseStatusName`   |
| `status_id`         | int    | Wins over `status`                                            |
| `date_from`         | date   | `CrimeRegisteredDate >= date_from`                            |
| `date_to`           | date   | `CrimeRegisteredDate <= date_to`                              |
| `page`              | int    | 1-based, default 1, max 1                                    |
| `page_size`         | int    | 1–100, default 20                                             |
| `sort_by`           | string | Whitelist: `crime_no`, `crime_registered_date`, `case_status`, `created_at`, `case_id` |
| `sort_order`        | string | `asc` or `desc` (default `desc`)                              |

Unknown lookup names yield an empty result set (200, not 400).
Unknown `sort_by` values yield `400 INVALID_SORT_FIELD`.

Example:

```bash
curl 'http://localhost:8000/api/v1/cases?district=Bengaluru%20Urban&page=1&page_size=5'
```

Response shape:

```json
{
  "items": [
    {
      "case_id": 4,
      "crime_no": "104430002202400112",
      "case_no": "202400112",
      "crime_registered_date": "2024-02-03",
      "case_status": { "case_status_id": 4, "case_status_name": "Closed" },
      "case_category": { "case_category_id": 1, "lookup_value": "FIR" },
      "gravity": { "gravity_offence_id": 2, "lookup_value": "Non-Heinous" },
      "crime_major_head": { "crime_head_id": 4, "crime_group_name": "Economic Offences" },
      "crime_minor_head": { "crime_sub_head_id": 13, "crime_head_name": "ATM Skimming" },
      "police_station": {
        "unit_id": 2,
        "unit_name": "Bengaluru Whitefield PS",
        "district": { "district_id": 1, "district_name": "Bengaluru Urban" }
      },
      "brief_facts": "Skimming device found on ATM. Multiple accounts compromised.",
      "is_series_crime": true,
      "series_id": 2
    }
  ],
  "pagination": {
    "total": 6,
    "page": 1,
    "page_size": 5,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  }
}
```

### `GET /api/v1/cases/{case_id}`

Returns the full case detail. `case_id` is the `CaseMasterID` (≥1).

```bash
curl 'http://localhost:8000/api/v1/cases/12'
```

Includes all of the above plus:

- `complainants[]`, `victims[]`, `accused[]`
- `evidence[]`, `recovered_items[]`
- `act_sections[]` (with the resolved act & section descriptions)
- `chargesheet` (or `null`)
- `assigned_officers[]` (IO + chargesheet filer)
- `court`, `incident_from_date`, `incident_to_date`, `info_received_ps_date`,
  `latitude`, `longitude`, `created_at`

Unknown `case_id` → `404 CASE_NOT_FOUND`:

```json
{
  "detail": {
    "code": "CASE_NOT_FOUND",
    "message": "Case 99999 not found",
    "details": { "case_id": 99999 }
  }
}
```

---

## 📊 Analytics APIs

Six read-only endpoints, all under `/api/v1/dashboard/`. Every
response is served by `AnalyticsService` — a FastAPI-independent
class that the Gemini AI provider (Phase 6+) will reuse directly.
All aggregations use `func.count().group_by()` in a single
round-trip; the recent-cases endpoint uses `selectinload` to avoid
N+1 on the child relationships the case summary shape needs.

| Method | Path                                              | Returns                                   |
|--------|---------------------------------------------------|-------------------------------------------|
| GET    | `/api/v1/dashboard/summary`                       | Six headline counters                     |
| GET    | `/api/v1/dashboard/monthly-trends`                | 12-month Jan..Dec counts                  |
| GET    | `/api/v1/dashboard/crime-head-distribution`       | Cases grouped by Crime Head               |
| GET    | `/api/v1/dashboard/status-distribution`           | Cases grouped by Case Status              |
| GET    | `/api/v1/dashboard/district-distribution`         | Cases grouped by District                 |
| GET    | `/api/v1/dashboard/recent-cases`                  | Most recent cases (paginated)             |

> **Convictions & acquittals** are always `0` in the summary
> response — the KSP schema has no verdict table yet. The fields
> exist in the contract (`int`, not `null`) so the API surface
> stays stable for clients and the AI provider; the value will
> be populated when a verdict table lands in a later phase.

### Optional district filter

`/summary`, `/monthly-trends`, and `/crime-head-distribution`
accept an optional district filter. Pass either `district` (name,
case-insensitive) **or** `district_id`; the id wins when both are
sent. An unknown name returns an empty result set with `200` —
never `404` — so the front-end can render a zero-state
unconditionally.

| Param         | Type   | Notes                                                |
|---------------|--------|------------------------------------------------------|
| `district`    | string | Case-insensitive match on `District.DistrictName`    |
| `district_id` | int    | Wins over `district` when both are sent              |

### `GET /api/v1/dashboard/summary`

```bash
curl 'http://localhost:8000/api/v1/dashboard/summary'
curl 'http://localhost:8000/api/v1/dashboard/summary?district_id=2'
```

Response shape:

```json
{
  "total_cases": 30,
  "open_cases": 9,
  "closed_cases": 8,
  "charge_sheet_filed": 6,
  "convictions": 0,
  "acquittals": 0
}
```

`open_cases` aggregates `Open` **and** `Under Investigation`. When
no cases exist for the filter, all six counters are `0`.

### `GET /api/v1/dashboard/monthly-trends`

| Param   | Type | Default            | Notes                                  |
|---------|------|--------------------|----------------------------------------|
| `year`  | int  | current year       | Bounded `[1900, 2200]`                 |
| district filter (optional, see above) |

```bash
curl 'http://localhost:8000/api/v1/dashboard/monthly-trends?year=2024'
curl 'http://localhost:8000/api/v1/dashboard/monthly-trends?year=2024&district=Mysuru'
```

Always returns 12 rows; months with no cases are zero-filled.
Response shape:

```json
{
  "year": 2024,
  "district": { "district_id": 2, "district_name": "Mysuru" },
  "items": [
    { "year": 2024, "month": 1, "month_label": "Jan", "case_count": 3 },
    { "year": 2024, "month": 2, "month_label": "Feb", "case_count": 0 },
    "..."
  ]
}
```

### `GET /api/v1/dashboard/crime-head-distribution`

Optional district filter.

```bash
curl 'http://localhost:8000/api/v1/dashboard/crime-head-distribution'
curl 'http://localhost:8000/api/v1/dashboard/crime-head-distribution?district_id=1'
```

```json
{
  "items": [
    { "key": 2, "label": "Crimes Against Property", "case_count": 12 },
    { "key": 4, "label": "Economic Offences",       "case_count": 6 }
  ],
  "total": 18
}
```

### `GET /api/v1/dashboard/status-distribution`

No filter — global distribution. Returns one row per `CaseStatus`
(seed values: `Open`, `Under Investigation`, `Charge Sheeted`,
`Closed`, `Undetected`).

```bash
curl 'http://localhost:8000/api/v1/dashboard/status-distribution'
```

### `GET /api/v1/dashboard/district-distribution`

No filter — global distribution. One row per `District`.

```bash
curl 'http://localhost:8000/api/v1/dashboard/district-distribution'
```

### `GET /api/v1/dashboard/recent-cases`

Paginated feed of the most recently registered cases. Uses the same
`CaseSummaryOut` shape as the case-list endpoint, so a front-end
can reuse the card / row component.

| Param       | Type | Default | Notes                       |
|-------------|------|---------|-----------------------------|
| `page`      | int  | `1`     | 1-based                     |
| `page_size` | int  | `10`    | Bounded `[1, 50]`           |

Ordered by `CrimeRegisteredDate DESC, CaseMasterID DESC` (stable
secondary order for cases registered on the same day).

```bash
curl 'http://localhost:8000/api/v1/dashboard/recent-cases'
curl 'http://localhost:8000/api/v1/dashboard/recent-cases?page=2&page_size=5'
```

Response shape:

```json
{
  "items": [ /* CaseSummaryOut, identical to /api/v1/cases */ ],
  "pagination": {
    "total": 30, "page": 1, "page_size": 10,
    "total_pages": 3, "has_next": true, "has_prev": false
  }
}
```

### Empty results

All distribution endpoints return `200` with `items: []` when no
rows match. The summary endpoint returns `200` with all six
counters as `0`. The monthly-trends endpoint zero-fills missing
months so the response always has 12 entries. **No 404** is ever
returned by a dashboard endpoint.

---



## 🤖 AI Foundation (Phase 5)

Phase 5 builds the **plumbing only** — no AI HTTP routes, no
SQL generation, no database querying from the AI layer, no
embeddings. The goal is a provider-independent architecture
that can be pointed at a different LLM without changing any
business logic.

### What ships in Phase 5

```
backend/ai/
├── __init__.py                 # public re-exports
├── providers/
│   ├── __init__.py             # AIProvider, GeminiProvider, get_provider
│   ├── base.py                 # abstract AIProvider (the only contract services see)
│   ├── gemini.py               # google-genai SDK wrapper + tenacity retry policy
│   ├── factory.py              # get_provider() — single resolution point
│   └── errors.py               # AIProviderError hierarchy (8 subclasses)
├── services/
│   ├── __init__.py
│   ├── prompt_service.py       # loads backend/ai/prompts/*.md; cache + render
│   └── chat_service.py         # orchestrator; FastAPI-independent
├── models/
│   ├── __init__.py
│   └── chat.py                 # ChatRole, ChatMessage, ChatRequest, ChatResponse
├── utils/
│   ├── __init__.py
│   ├── latency.py              # time.monotonic() wrapper
│   └── token_estimator.py      # char-based fallback (4 chars / token)
├── prompts/                    # Markdown templates — NEVER hardcoded in Python
│   ├── system_prompt.md
│   ├── sql_prompt.md
│   ├── explanation_prompt.md
│   └── investigation_prompt.md
└── docs/
    └── ai_api_plan.md          # Phase 6 /api/v1/ai/* route spec
```

### The contract

Every concrete provider (`GeminiProvider` today; `ClaudeProvider`,
`OpenAIProvider`, `GroqProvider`, `OpenRouterProvider` in later
phases) implements:

```python
class AIProvider(abc.ABC):
    name: str
    model: str

    @abc.abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse: ...

    @abc.abstractmethod
    def count_tokens(self, text: str) -> int: ...

    def health_check(self) -> bool: ...
```

`ChatService` (and the future route layer) depend on
`AIProvider` **only**. They never import `google-genai`,
`openai`, or `anthropic`. Swapping providers = editing one
branch in `backend/ai/providers/factory.py`.

### Hard rules enforced by tests

| Rule | Enforced by |
|---|---|
| No `fastapi` / `starlette` import in `backend/ai/` | `tests/test_ai/test_ai_independence.py` |
| No prompt literal in any `.py` file | `tests/test_ai/test_prompt_service.py` (loads from disk) |
| No `SELECT` / `INSERT` / `UPDATE` / `DELETE` in `backend/ai/` | grep in CI |
| No `from backend.models` / `from backend.database` in `backend/ai/` | grep in CI |
| Every call logs `provider`, `model`, `latency_ms`, success / failure | `tests/test_ai/test_chat_service.py` |

### Configuration

Add to `backend/.env` (see `backend/.env.example`):

```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=<your-key-from-aistudio.google.com>
GEMINI_MODEL=gemini-2.0-flash
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=3
AI_PROMPTS_DIR=     # empty = use backend/ai/prompts/
```

`Settings` refuses to start the app if
`ai_provider == "gemini"` and `gemini_api_key` is empty — the
failure surfaces at process boot, not at the first request.

### Provider-independence proof

```bash
# Replace these greps with a CI check:
grep -r "from google"  backend/ai/services backend/ai/models  # → nothing
grep -r "from openai"  backend/ai                            # → nothing
grep -r "anthropic"    backend/ai                            # → nothing
```

If any of those return hits, something has leaked an SDK
import past the provider layer. The test suite fails closed.

### Retry policy

`GeminiProvider` wraps the SDK call in a `tenacity.Retrying`
loop with exponential backoff + jitter. Retries happen on
the *transient* subset of the exception hierarchy:

| Exception | Retried? | Why |
|---|---|---|
| `AIRateLimitError` (HTTP 429) | ✅ | Provider throttling — will clear |
| `AIResponseError` (5xx) | ✅ | Transient server failure |
| `AITimeoutError` | ✅ | Could be a network blip |
| `AIRequestError` (4xx) | ❌ | Caller's fault — won't fix itself |
| `AIConfigurationError` | ❌ | Programmer error — won't fix itself |

Total attempts = `1 + AI_MAX_RETRIES`.

### Adding a new provider (later phases)

1. Subclass `AIProvider` in `backend/ai/providers/<name>.py`.
2. Add a branch in `backend/ai/providers/factory.py`:
   ```python
   if name == "claude":
       return _build_claude(settings)
   ```
3. Add `<name>_api_key` / `<name>_model` to `Settings` and
   extend the `_validate_ai_credentials` model validator.
4. Add a route in the `tests/test_ai/test_<name>_provider.py`
   pattern. Mocked SDK — no real API call.

Services and routes do not change.

### What is **not** in Phase 5

- No `/api/v1/ai/*` routes (see `backend/ai/docs/ai_api_plan.md`).
- No natural-language → SQL execution.
- No embeddings, no `pgvector`, no similarity search.
- No Neo4j cross-case graph.
- No voice (STT / TTS).
- No real Gemini API call anywhere in CI.

---

```bash
# Run from the repo root
python -m scripts.db_test
```

This will:

1. Print the masked `DATABASE_URL` so you can verify it points to the
   right environment.
2. Attempt to connect (a `psycopg2.OperationalError` is expected if
   Postgres is not running — the script will exit **1** with a clear
   message).
3. Count tables in the `public` schema and warn about any declared
   models that are missing from the live DB.
4. Print a summary of every declared model and its column count.

Exit codes:

| Code | Meaning |
|------|---------|
|  0   | All checks passed |
|  1   | Could not connect to the database |

### Running the unit tests

The case-API tests live in `backend/tests/`. They mock the SQLAlchemy
session, so no database is required.

```bash
# From the repo root, after pip install -r backend/requirements.txt
pytest backend/tests
```

Expected output: **~97 passed** (35 case API + 35 dashboard + 14
OpenAPI docs + 13 service-independence).

### Regenerating the ER diagram

```bash
python -m scripts.generate_erd
```

Writes `backend/docs/erd.mmd` (Mermaid). Open it in
<https://mermaid.live> or any markdown viewer that supports Mermaid.

If you have `graphviz` (`dot` on `PATH`), it will also write a PNG.

---

## 🛠 Configuration Reference

All settings are loaded by **pydantic-settings** from the environment
and a local `.env` file. See `backend/config/settings.py` for the
authoritative list. Highlights:

| Key              | Default                            | Notes                              |
|------------------|------------------------------------|------------------------------------|
| `APP_NAME`       | `Saaransh AI`                      |                                    |
| `ENVIRONMENT`    | `development`                      | `development` / `staging` / `production` |
| `DEBUG`          | `true`                             | Enables reload + verbose errors    |
| `HOST` / `PORT`  | `0.0.0.0` / `8000`                 |                                    |
| `DATABASE_URL`   | local postgres                     | SQLAlchemy DSN                     |
| `DB_ECHO`        | `false`                            | Set `true` to log every SQL stmt   |
| `CORS_ORIGINS`   | localhost:5173, localhost:3000     | Override for prod frontend         |
| `LOG_LEVEL`      | `INFO`                             |                                    |
| `LOG_FORMAT`     | `text`                             | `text` for dev, `json` for prod    |
| `AI_PROVIDER`    | `gemini`                           | Phase 5. `gemini` only today.      |
| `GEMINI_API_KEY` | *(empty)*                          | Phase 5. Required when `AI_PROVIDER=gemini`. |
| `GEMINI_MODEL`   | `gemini-2.0-flash`                 | Phase 5.                           |
| `AI_REQUEST_TIMEOUT_SECONDS` | `30.0`                 | Phase 5. Per-attempt timeout.      |
| `AI_MAX_RETRIES` | `3`                                | Phase 5. Total attempts = 1 + this.|
| `AI_PROMPTS_DIR` | *(empty)*                          | Phase 5. Empty = default location. |

---

## 🏷 API Versioning

The Saaransh API is **URL-versioned**. Every route lives under a
versioned prefix; the version is part of the URL, not a header. The
current prefix is `/api/v1`.

### Current version

| Version | Status    | Base URL                          | Introduced |
|---------|-----------|-----------------------------------|------------|
| `v1`    | Current   | `http://localhost:8000/api/v1`    | Phase 3    |

### Why URL versioning (and not header versioning)?

* **Self-describing URLs.** A developer can tell which version they
  are calling from the address bar, a stack trace, a log line, or a
  curl one-liner. There is no "wait, which version is this server
  serving?" moment.
* **Easy coexistence.** Running `v1` and `v2` side-by-side is just
  two router prefixes mounted on the same `FastAPI` instance. No
  request-level dispatch logic.
* **Cacheable.** Reverse proxies and CDNs cache by full path; the
  version is part of the cache key for free.
* **Honest.** A new URL tells clients they are getting a different
  contract. A new header value silently does not.

### Versioning policy

1. **Additive changes are non-breaking** and do not require a new
   version. Examples:
   * New optional query parameters with sensible defaults.
   * New response fields that are `null`-able (clients ignore them).
   * New endpoints under `/api/v1/...`.
   * New enum values on a string field (clients that switch on a
     fixed list should add a default branch, but old lists keep
     working).
2. **Breaking changes require a new version.** Examples:
   * Removing or renaming a field in a response.
   * Changing the type of a field (`string` → `integer`).
   * Tightening validation (`page_size: int` → `page_size: 1..20`).
   * Changing the meaning of an existing field.
   * Removing an endpoint.
3. **Deprecation.** A deprecated version:
   * Stays live for **at least 6 months** after the successor's
     general availability.
   * Returns the `Deprecation: true` response header on every
     response.
   * Returns a `Sunset: <RFC 7231 date>` header with the date the
     version will be removed.
   * Logs a one-time `WARN` line per caller (per `User-Agent`) so
     we can build a removal list.
4. **Sunset / removal.** When a version is sunset:
   * The router is removed.
   * A short-lived redirect rule is **not** provided — the version
     is gone. Clients that have not migrated will get `404` on the
     old prefix. The README's [CHANGELOG](#-changelog) section
     records the removal.

### Headers used by the API

| Header                  | Direction | When                                   |
|-------------------------|-----------|----------------------------------------|
| `X-API-Version`         | response  | Always. Value: the active version (`1`). |
| `Deprecation: true`     | response  | Deprecated versions only.              |
| `Sunset: <date>`        | response  | Deprecated versions only.              |
| `X-Request-ID`          | request   | Optional. Echoed in logs.              |
| `Accept: application/vnd.saaransh.v1+json` | request | Reserved — accepted but not yet required. |

### Introducing a new version

When it is time for `v2`:

1. Create `backend/api/v2/__init__.py` with its own `api_router`.
2. Add a `Settings.api_v2_prefix: str = "/api/v2"` field (do not
   remove the v1 setting).
3. Wire it in `backend/main.py` next to the v1 mount.
4. Mark v1 as deprecated in the v1 router middleware by adding
   `Deprecation: true` and `Sunset: ...` headers on every response.
5. Update this README's version table and the CHANGELOG below.
6. Do **not** copy the v1 router wholesale — only re-implement the
   routes that v1 has, with the new contract. Shared business logic
   lives in the service layer and is reused by both versions.

### What never carries the version prefix

* `/` (the root service-info endpoint)
* `/docs`, `/redoc`, `/openapi.json` (OpenAPI surfaces are global)
* `/api/v1/health` and any future `/api/v2/health` (versioned
  because the *version* is the thing being probed)

---

## 🧱 Adding Code in Later Phases

| Phase   | Where to add                                                                                |
|---------|---------------------------------------------------------------------------------------------|
| 3 ✅    | `api/v1/cases.py`, `services/case_service.py`, `schemas/case.py` (done)                     |
| 3.5 ✅  | `api/v1/openapi.py`, `services/base.py`, OpenAPI examples, README versioning section (done) |
| 4 ✅    | `api/v1/dashboard.py`, `services/analytics_service.py`, `schemas/dashboard.py` (done)       |
| 5 ✅    | `ai/providers/{base,gemini,factory,errors}.py`, `ai/services/{prompt,chat}_service.py`, `ai/prompts/*.md`, `ai/docs/ai_api_plan.md`, AI settings in `config/settings.py` |
| 6       | `api/v1/ai.py`, `services/ai_service.py`, `schemas/ai.py` — wires `ChatService` to HTTP, implements NL→SQL using `sql_prompt.md` |
| 7       | `ai/embedding_service.py`, `ai/similarity_engine.py`, `pgvector` migration                  |
| 8       | Neo4j cross-case graph traversal service + investigation prompt wiring                      |
| 9       | `ai/voice/` (STT + TTS)                                                                     |
| 10      | Auth middleware (JWT), RBAC, audit logging of every AI call                                |
| ?       | `alembic revision --autogenerate -m "msg"` for any schema change                            |

Every new router is wired in `backend/api/v1/__init__.py`. New versions
are wired in `backend/api/v2/__init__.py` and mounted in
`backend/main.py`.

### Changelog

| Version | Date       | Notes                                                            |
|---------|------------|------------------------------------------------------------------|
| `v1`    | 2026-07-09 | Initial release — health + read-only case list + case detail.    |
| `v1`    | 2026-07-09 | Phase 4 — `/api/v1/dashboard/*` analytics (summary, trends, distributions, recent-cases). |
| `v1`    | 2026-07-10 | Phase 5 — AI foundation (provider abstraction, prompt loader, chat orchestrator, 4 prompt files, planning doc). No new routes. |

---

## 📜 License

Internal — Karnataka State Police Datathon.
