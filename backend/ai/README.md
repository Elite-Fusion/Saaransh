# Saaransh AI — backend/ai/

This package owns every component that touches an LLM.
Phases 1–4 built the database, ORM, services, and HTTP
routes that never reference AI. Phase 5 added the
provider-agnostic AI foundation. Phase 6 (this document)
wires those primitives into a single end-to-end investigation
engine.

The cardinal rule of this package:

> **The AI layer never imports `sqlalchemy`, `backend.database`,
> `backend.models`, `backend.services.sql_executor`, or
> `backend.services.ai_query_service`.** The independence
> test (`tests/test_ai/test_ai_independence.py`) fails the
> build if anyone violates this.

The AI layer depends on the executor only through a
`SQLExecutor` Protocol injected at construction time. The
concrete implementation lives in
`backend.services.sql_executor` so the database driver stays
out of the AI service code.

---

## Layout

```
backend/ai/
├── __init__.py                     # Re-exports the public surface
├── README.md                       # ← you are here
├── models/
│   └── chat.py                     # ChatRequest / ChatResponse
├── providers/
│   ├── base.py                     # AIProvider ABC
│   ├── errors.py                   # AIProviderError, PromptNotFoundError
│   ├── factory.py                  # get_provider()
│   └── gemini.py                   # GeminiProvider (Phase 5)
├── prompts/
│   ├── system_prompt.md
│   ├── intent_prompt.md            # Phase 6
│   ├── sql_prompt.md
│   ├── explanation_prompt.md
│   └── investigation_prompt.md
├── schemas/
│   └── ai.py                       # Phase 6 Pydantic v2 domain models
├── services/
│   ├── chat_service.py             # Thin orchestrator over AIProvider
│   ├── prompt_service.py           # Loads *.md prompt templates
│   ├── exceptions.py               # Phase 6 domain exceptions
│   ├── intent_service.py           # Phase 6
│   ├── sql_generation_service.py   # Phase 6
│   ├── sql_validation_service.py   # Phase 6
│   └── investigation_service.py    # Phase 6 orchestrator
├── utils/
│   ├── latency.py
│   └── token_estimator.py
└── voice/
    └── __init__.py
```

---

## Phase 6 — the investigation pipeline

`InvestigationService.investigate(question, *, request_id, metadata)`
composes the five collaborator services into a single
response.

```
                    +------------------------+
   officer's       | InvestigationService.  |
   question ──────▶| investigate(question)  |
                   +-----------+------------+
                               │
            ┌──────────────────┴───────────────────┐
            ▼                                      ▼
   IntentService.classify                  ChatService.chat_with_prompt
   (LLM → regex fallback)                 (LLM)
            │
            ▼
   IntentRouter.route
   ├── case_search         → CaseService.list_cases
   ├── dashboard_analytics → AnalyticsService.summary / monthly_trends
   ├── explain_case        → CaseService.get_case_detail
   ├── investigation_summary → CaseService.get_case_detail
   ├── similar_cases       → Phase 7 placeholder
   └── unknown             → raise UnknownIntent
            │
            ▼
   SQLGenerationService.generate     ChatService.chat_with_prompt
   (LLM)
            │
            ▼
   SQLValidationService.validate
   (allowlist, no LLM call)
            │
            ▼
   SQLExecutor.execute
   (session.execute(text(sql), params))
            │
            ▼
   ExplanationService.explain        ChatService.chat_with_prompt
   (LLM)
            │
            ▼
   InvestigationResponse
```

### `IntentService` — `backend/ai/services/intent_service.py`

Classifies the officer's question into one of six
categories:

| Intent | Trigger |
|---|---|
| `CASE_SEARCH` | "list cases", "find FIRs", "show me thefts in Mysuru" |
| `DASHBOARD_ANALYTICS` | "how many open cases", "monthly trends", "summary" |
| `EXPLAIN_CASE` | "what happened in case 12", "explain FIR 1044" |
| `INVESTIGATION_SUMMARY` | "investigate case 12", "give me a brief" |
| `SIMILAR_CASES` | "find similar cases to FIR 1044" |
| `UNKNOWN` | anything the regex fallback cannot place |

Two paths: the LLM call first; if the LLM returns garbage
or `UNKNOWN`, a regex pass classifies the question. If
both fail, the service raises `UnknownIntent`.

### `SQLGenerationService` — `sql_generation_service.py`

Renders the SQL prompt with the schema summary injected,
calls the LLM, and parses the JSON reply into a
`GeneratedSQL` object. The LLM is asked to return a JSON
object only (Gemini sometimes wraps the JSON in fences —
the parser handles that).

If the LLM returns an empty SQL string (the documented
"this is not a read query" stub), the service raises
`UnsafeSQL` so the pipeline can short-circuit.

### `SQLValidationService` — `sql_validation_service.py`

The safety heart of the engine. Performs nine checks:

1. SQL is non-empty.
2. No line comments (`--`).
3. No block comments (`/* */`).
4. No multiple statements (no `;` other than trailing).
5. No forbidden verb (`DELETE`, `UPDATE`, `INSERT`, `DROP`,
   `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`,
   `MERGE`, `CALL`, `COPY`, `EXEC`, `EXPLAIN`, `SHOW`).
6. Every `FROM` / `JOIN` table is in the schema allowlist.
7. Every column reference is in its table's allowlist.
8. Every `:name` parameter is bound in the params dict.
9. Every param value is a JSON-primitive scalar.

Each rejection raises `ValidationFailure` (a subclass of
`UnsafeSQL`) with a `category` attribute identifying the
step that failed: `empty`, `comment`, `multiple_statements`,
`forbidden_verb`, `forbidden_token`, `unsupported_verb`,
`unknown_table`, `unknown_column`, `unbound_param`,
`bad_param`, `bad_param_value`.

### `AIQueryService` — `backend/services/ai_query_service.py`

Thin facade. Wraps the executor's read-only
`session.execute(text(sql), params)` and re-raises service-
layer exceptions as AI-domain exceptions
(`UnsafeSQL`, `ExecutionFailure`). The AI service layer
talks to the executor only through this facade.

### `SQLExecutor` — `backend/services/sql_executor.py`

The only file in Phase 6 that touches the database session.
Defence in depth: it runs `assert_read_only(sql)` even
though the validator should already have rejected the
forbidden verb.

### `InvestigationService` — `investigation_service.py`

The orchestrator. Composes the four collaborator services
plus the two domain services (`CaseService`,
`AnalyticsService`) and a `ChatService`. Returns an
`InvestigationResponse` envelope.

Always calls the explanation step at the end. If the
explanation LLM call fails (`ProviderFailure` or
`PromptError`), the service falls back to a low-confidence
explanation built from the structured data — the officer
still gets a structured answer.

---

## Domain exceptions

`backend/ai/services/exceptions.py` defines six
exceptions, all inheriting from `InvestigationError`:

| Exception | Raised when |
|---|---|
| `UnknownIntent` | The intent classifier and the regex fallback both returned `UNKNOWN`. |
| `UnsafeSQL` | The SQL validator rejected the statement. The route layer maps this to 400. |
| `ValidationFailure` | Subclass of `UnsafeSQL` with a `category` field. |
| `PromptError` | `PromptNotFoundError` propagated as this. |
| `ProviderFailure` | `AIProviderError` propagated as this. |
| `ExecutionFailure` | `SQLAlchemyError` from the executor propagated as this. |

The route layer maps the whole hierarchy to a 4xx/5xx
JSON response.

---

## Schemas — `backend/ai/schemas/ai.py`

Pydantic v2 models. Every model has
`model_config = ConfigDict(extra="forbid")` so a future
caller cannot smuggle unknown fields into a route
response.

| Model | Purpose |
|---|---|
| `Intent` | Enum: six categories. |
| `OperationType` | Enum: `service` / `sql` / `placeholder` / `none`. |
| `IntentClassification` | Output of `IntentService.classify`. |
| `GeneratedSQL` | Output of `SQLGenerationService.generate`. |
| `ValidatedSQL` | Output of `SQLValidationService.validate`. |
| `EvidenceItem` | A single row of evidence in the answer. |
| `ExplanationBlock` | Headline + evidence + why + confidence. |
| `InvestigationResponse` | Top-level envelope. |
| `CaseSearchOperation` / `DashboardAnalyticsOperation` / `ExplainCaseOperation` / `InvestigationSummaryOperation` / `PlaceholderOperation` | The intent router's output. |

---

## Prompts — `backend/ai/prompts/`

Every prompt is a Markdown file. Never hardcode a prompt
in Python.

| File | Purpose |
|---|---|
| `system_prompt.md` | Establishes the persona for `ChatService.chat`. |
| `intent_prompt.md` | Phase 6: classifies the officer's question. Renders `{{SCHEMA_SUMMARY}}`. |
| `sql_prompt.md` | Phase 6: produces a parameterised `SELECT` against the schema. Renders `{{SCHEMA_SUMMARY}}` and `{{QUESTION}}`. |
| `explanation_prompt.md` | Phase 6: grounds the answer in the result rows. Renders `{{QUESTION}}`, `{{SQL}}`, `{{ROWS_JSON}}`, `{{ROW_COUNT}}`, `{{FILTERS}}`. |
| `investigation_prompt.md` | Phase 8: builds a multi-case brief. |

`PromptService.render(name, **vars)` returns the rendered
string or raises `PromptNotFoundError` (re-raised as
`PromptError` in the AI service layer).

---

## The independence rule

The Phase 5 test `tests/test_ai/test_ai_independence.py`
asserts no file under `backend/ai/` imports:

- `fastapi` (and `starlette`)
- `sqlalchemy`
- `backend.database`
- `backend.models`
- `backend.services.sql_executor`
- `backend.services.ai_query_service`

The last two are Phase 6 additions — the AI service layer
depends on the executor only through a `SQLExecutor`
Protocol injected at construction time. The concrete
implementation lives in `backend.services.sql_executor` so
the database driver stays out of the AI service code.

This rule is not aesthetic: it lets the AI service layer be
unit-tested with a mock `SQLExecutor` and an in-memory
SQLite engine without spinning up Postgres. The 354 Phase 6
tests run in < 16 seconds.

---

## Tests — `backend/tests/test_ai/` and `backend/tests/test_services/`

354 tests, all hermetic. No real Gemini call. No real
database. Highlights:

- `test_intent_service.py` — happy path + LLM-failure
  fallback + regex-only + edge cases (empty, too-short,
  whitespace-only).
- `test_sql_generation_service.py` — JSON extraction
  (raw, fenced, embedded) + empty SQL → `UnsafeSQL` +
  colon-prefix param key normalisation.
- `test_sql_validation_service.py` — every rejection path,
  17-case SQL-injection battery, every `ALLOWED_CLAUSE_TOKEN`,
  the `*` wildcard, the colon-prefix param key, the
  non-string key rejection.
- `test_investigation_service.py` — every intent type,
  every error path, the malicious-prompt test, the
  response-envelope contract, the call-count assertion,
  the fallback-explanation path.
- `test_ai_independence.py` — the rule above, expanded
  for Phase 6.
- `test_sql_executor.py` — in-memory SQLite + `text()` end
  to end. Proves `Decimal` / `datetime` / `UUID` are
  normalised, `max_rows` truncates, forbidden verbs are
  rejected.
- `test_schema_registry.py` — drift test against
  `database/schema/ksp_real_schema.sql`. A regression
  test catches the most common Phase 6 failure: someone
  adds a column to the SQL schema and forgets to update
  the allowlist.

Coverage on the new modules:

| Module | Coverage |
|---|---|
| `ai/schemas/ai.py` | 100% |
| `ai/services/exceptions.py` | 100% |
| `ai/services/investigation_service.py` | 86% |
| `ai/services/intent_service.py` | 95% |
| `ai/services/sql_generation_service.py` | 99% |
| `ai/services/sql_validation_service.py` | 95% |
| `services/ai_query_service.py` | 100% |
| `services/sql_executor.py` | 99% |
| `services/schema_registry.py` | 98% |
