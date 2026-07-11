# Saaransh AI

> **Conversational crime-investigation co-pilot for the Karnataka State Police Datathon.**

Saaransh lets police officers query the KSP FIR database in
natural language (English and Kannada), detect similar cases,
surface cross-case links (shared phones, addresses, vehicles,
gang membership), and get explainable, evidence-backed answers.
Every response cites the cases it relied on; the system never
invents a `case_id` or an FIR number.

The system is built around five principles, lifted directly from
the project brief:

1. **Accuracy** — answers are grounded in real records, not
   generated from model priors.
2. **Explainability** — every response carries a `why`, an
   `evidence` list, and a `confidence` level.
3. **Maintainability** — the codebase is split into
   provider-independent layers so swapping the LLM is a
   one-file change.
4. **Modularity** — every component can be replaced in
   isolation (provider, prompt template, embedding model,
   graph backend).
5. **Security** — secrets stay in `.env`, SQL is parameterised,
   prompts are read-only templates, every AI call is logged
   with timestamp, user, prompt, generated SQL, and outcome.

---

## 📦 Repository layout

```
saaransh-ai/
├── backend/           # FastAPI + SQLAlchemy + Pydantic + AI provider
│   ├── api/           # HTTP routers (v1)
│   ├── ai/            # AI provider abstraction (Phase 5)
│   ├── config/        # Pydantic settings + logging
│   ├── database/      # SQLAlchemy engine + session
│   ├── models/        # ORM models (30+ tables)
│   ├── schemas/       # request / response Pydantic models
│   ├── services/      # business logic (FastAPI-independent)
│   ├── tests/         # pytest (mocked — no live DB needed)
│   └── main.py
├── frontend/          # React + Vite + Tailwind (separate workstream)
├── database/
│   ├── schema/        # KSP FIR schema
│   └── seed/          # seed data
├── scripts/           # project-wide utilities
│   ├── db_test.py
│   └── generate_erd.py
├── .env.example       # top-level env var template
└── README.md          # ← you are here
```

For the backend's full layout, see [`backend/README.md`](./backend/README.md).
The frontend's README lands when Phase 6 begins.

---

## 🧭 Phases

| Phase | What ships | Status |
|---|---|---|
| 1 | Backend foundation: FastAPI + SQLAlchemy + Pydantic settings + logging | ✅ |
| 2 | Database: schema, 30 ORM models, ER doc | ✅ |
| 3 | Read-only case APIs (`GET /api/v1/cases`, `GET /api/v1/cases/{id}`) + service layer | ✅ |
| 3.5 | OpenAPI examples, `BaseService` for AI reuse, API versioning policy | ✅ |
| 4 | Analytics module (`/api/v1/dashboard/*`) + `AnalyticsService` | ✅ |
| 5 | AI foundation: provider abstraction, Gemini provider, prompt loader, `ChatService`, 4 prompt templates, planning doc | ✅ |
| **6** | **AI investigation engine: intent classifier, allowlist SQL validator, read-only executor, explanation layer, 354 unit tests** | **✅** |
| 7 | Embeddings + similarity engine (`pgvector`) | ⏳ |
| 8 | Neo4j cross-case graph + investigation prompt wiring | ⏳ |
| 9 | Voice (STT + TTS) | ⏳ |
| 10 | Auth (JWT), RBAC, AI-call audit logging | ⏳ |

---

## 🚀 Quick start (backend)

The backend runs locally with **no external services required**
for the read-only case and dashboard endpoints — the test
suite uses mocked SQLAlchemy sessions.

```bash
# 1. Set up Python
cd backend
python -m venv .venv
source .venv/Scripts/activate          # Windows Git Bash
# or:  source .venv/bin/activate        # Linux / macOS

# 2. Install deps
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# edit DATABASE_URL if you have a Postgres instance

# 4. Run
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000/docs> for Swagger, or hit
<http://localhost:8000/api/v1/health> for a quick liveness
probe.

For the AI layer (Phase 5), set `GEMINI_API_KEY` in
`backend/.env` and the app will fail fast at startup if the
key is missing.

---

## 🧪 Tests

```bash
# From the repo root
cd backend
pytest tests
```

Expected: **455+ passed** (98 from Phases 1–4, 100+ from
Phase 5 AI foundation, and 200+ from Phase 6 — all hermetic,
no real Gemini call, no real database).

---

## 🧠 Phase 6 — AI investigation engine

Phase 6 wires the Phase 5 AI foundation into a single
end-to-end pipeline that takes an officer's natural-language
question, classifies the intent, generates and validates a
SQL statement, executes it read-only, and produces an
evidence-driven explanation.

### Pipeline

```
InvestigationService.investigate(question)
   │
   ├── IntentService.classify(question)         → Intent
   │     [LLM call with regex fallback]
   │
   ├── IntentRouter.route(intent, question)     → ResolvedOperation
   │     ├── case_search        → CaseService.list_cases
   │     ├── dashboard_analytics→ AnalyticsService.{summary, trends}
   │     ├── explain_case       → CaseService.get_case_detail
   │     ├── investigation_summary → CaseService.get_case_detail
   │     ├── similar_cases      → Phase 7 placeholder
   │     └── unknown            → raise UnknownIntent
   │
   ├── SQLGenerationService.generate(...)       → GeneratedSQL
   │     [LLM call with the SQL prompt + schema]
   │
   ├── SQLValidationService.validate(generated) → ValidatedSQL
   │     [defence-in-depth allowlist: see below]
   │
   ├── SQLExecutor.execute(validated)           → ExecutionResult
   │     [session.execute(text(sql), params) — read-only]
   │
   └── ExplanationService.explain(...)          → ExplanationBlock
         [LLM call with the explanation prompt + rows]
```

### SQL safety rules (enforced in three layers)

1. **Validator (primary defence).** Every generated SQL
   statement passes through
   `backend.ai.services.sql_validation_service.SQLValidationService`
   which rejects:

   - **Forbidden verbs** — `DELETE`, `UPDATE`, `INSERT`,
     `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`,
     `REVOKE`, `MERGE`, `CALL`, `COPY`, `EXEC`, `EXPLAIN`,
     `SHOW`.
   - **Multiple statements** — any `;` other than a trailing
     one.
   - **Comments** — `--` line comments and `/* */` block
     comments, even inside string literals? No — the
     string-literal pass runs first.
   - **Unknown tables** — every `FROM` and `JOIN` table must
     be in the schema allowlist
     (`backend.services.schema_registry.SCHEMA_TABLES`).
   - **Unknown columns** — every column reference in the
     SELECT projection, WHERE, or ORDER BY must be in the
     allowlisted column set of one of the referenced tables.
     `SELECT *` is permitted.
   - **Unbound parameters** — every `:name` in the SQL must
     be present in the `params` dict.
   - **Non-primitive param values** — `list`, `dict`, and
     complex objects are rejected; only `str`, `int`, `float`,
     `bool`, `None` are allowed.

2. **Executor (defence in depth).** Even after the validator,
   `backend.services.sql_executor.SQLAlchemySQLExecutor` runs
   `assert_read_only(sql)` before `session.execute(...)`. The
   executor never concatenates user input — it always uses
   bound parameters through `sqlalchemy.text(sql)`.

3. **Independence rule.** No file under `backend/ai/` imports
   `sqlalchemy`, `backend.database`, `backend.models`,
   `backend.services.sql_executor`, or
   `backend.services.ai_query_service` — the AI layer depends
   on the executor only through a Protocol. The
   `tests/test_ai/test_ai_independence.py` test enforces this.

### Prompt files (the only place prompts live)

```
backend/ai/prompts/
├── system_prompt.md
├── intent_prompt.md      ← classifies the officer's question
├── sql_prompt.md         ← renders a SELECT against the schema
├── explanation_prompt.md ← grounds the answer in the result rows
└── investigation_prompt.md
```

Never hardcode a prompt in Python.

### Response envelope

Every response is a Pydantic v2 `InvestigationResponse`:

```python
InvestigationResponse(
    request_id, intent, operation,
    reasoning, executed_operation, confidence,
    assumptions, supporting_evidence,
    explanation, raw_sql, raw_params,
    row_count, columns, placeholder,
)
```

Where `operation` is one of `service` / `sql` /
`placeholder` / `none`. `extra="forbid"` is set on every
model, so a future caller cannot smuggle unknown keys into
the response.

### Tests

- 354 tests in `tests/test_ai/` and `tests/test_services/`.
- 100% line coverage on `ai/schemas/ai.py`,
  `ai/services/exceptions.py`, `services/ai_query_service.py`.
- 95–99% coverage on the rest of the new code.
- A drift test
  (`tests/test_services/test_schema_registry.py`)
  parses `database/schema/ksp_real_schema.sql` and asserts
  every `CREATE TABLE` and its columns is reflected in
  `SCHEMA_TABLES`. The allowlist can never silently fall out
  of sync with the real schema.
- A 17-case SQL-injection battery in
  `tests/test_ai/test_sql_validation_service.py` proves
  every common attack string (`DROP TABLE`, stacked
  statements, `--` comments, `UNION SELECT password FROM
  users`, `pg_sleep`, `xp_cmdshell`, etc.) is rejected
  before it reaches the database.
- The `test_ai_independence.py` test guarantees no future
  commit breaks the "AI layer is web-framework-, database-,
  and SDK-independent" rule.

See `backend/ai/README.md` for the full module reference.

---

## 📜 Project brief reminders

> Source: `CLAUDE.md`.

- **Never hardcode prompts in Python.** All four Phase 5
  prompts live in `backend/ai/prompts/*.md` and are loaded at
  runtime by `PromptService`.
- **Never hardcode the LLM provider.** Every service depends
  on the `AIProvider` ABC, never on `google-genai`,
  `openai`, or `anthropic` directly. The
  `tests/test_ai/test_ai_independence.py` test fails the
  build if anyone violates this.
- **Every AI request logs timestamp, user, prompt, generated
  SQL, execution time, success/failure.** The `ChatService`
  and `GeminiProvider` log on every call.
- **Every AI answer carries why, which records, confidence,
  and supporting evidence.** The four Phase 5 prompt files
  each declare a JSON output schema that includes those
  fields.
- **SQL is `SELECT` only.** The Phase 6
  `SQLValidationService` rejects any forbidden verb before the
  query reaches the database. The executor re-checks at run
  time, and the AI layer never imports `sqlalchemy` directly.

---

## 📄 License

Internal — Karnataka State Police Datathon.
