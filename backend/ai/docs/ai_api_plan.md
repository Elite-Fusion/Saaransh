# Saaransh AI — Future `/api/v1/ai/*` Route Plan

> **Phase 5 — planning only.** This document describes the
> endpoints that Phase 6 will add. No code in this folder is
> implemented yet — the four Phase 5 prompt files
> (`backend/ai/prompts/*.md`) are the structural contracts
> the routes will fulfil.

The AI HTTP surface is intentionally small. Each route is a
thin FastAPI wrapper that:

1. Deserialises a typed request body (Pydantic).
2. Hands it to `ChatService` (or a future specialised service).
3. Serialises the `ChatResponse` into the standard envelope.

No business logic lives in the route file.

---

## Envelope

Every successful response shares the same shape:

```json
{
  "data": <endpoint-specific payload>,
  "meta": {
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "latency_ms": 421,
    "request_id": "uuid"
  }
}
```

Errors share one envelope too:

```json
{
  "error": {
    "type": "AIRateLimitError",
    "message": "Rate limit exceeded. Try again in 30s.",
    "request_id": "uuid"
  }
}
```

---

## Endpoints (Phase 6)

| Method | Path | Prompt | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/ai/chat` | (free-form) | Generic chat. Caller supplies the messages. |
| `POST` | `/api/v1/ai/sql` | `sql_prompt.md` | Natural language → parameterised SQL. |
| `POST` | `/api/v1/ai/explain` | `explanation_prompt.md` | Turn SQL result rows into an officer-facing paragraph. |
| `POST` | `/api/v1/ai/investigate` | `investigation_prompt.md` | Investigation brief: similar cases, repeat offenders, geo / temporal patterns. |

All four are `POST`. All four accept a JSON body. The body
shape is endpoint-specific but every body carries an optional
`request_id` (UUID) that is echoed in `meta`.

### `POST /api/v1/ai/chat`

Thin wrapper around `ChatService.chat(ChatRequest)`. Body is
a `ChatRequest` minus the `metadata` field (which is filled
in by the route with `request_id` and the authenticated user).

### `POST /api/v1/ai/sql`

Body:

```json
{
  "question": "Cases of theft registered in Kalaburagi in 2024",
  "schema_summary": "<schema reference>",
  "filters": { "district": "Kalaburagi", "year": 2024 },
  "temperature": 0.2
}
```

Response `data`:

```json
{
  "sql": "SELECT CaseMasterID, CrimeNo FROM CaseMaster WHERE ...",
  "params": { ":district_id": 12, ":date_from": "2024-01-01" },
  "tables": ["CaseMaster", "Unit"],
  "estimated_rows": "medium",
  "notes": "Joins through Unit, so cases without a PoliceStationID are excluded."
}
```

The route **does not execute the SQL**. SQL execution lives in
the service layer, which validates the verb allowlist
(`SELECT` only) and runs the parameterised query against
`CaseMaster` and friends.

### `POST /api/v1/ai/explain`

Body:

```json
{
  "question": "How many theft cases in Kalaburagi in 2024?",
  "sql": "SELECT ... FROM ... WHERE ...",
  "rows": [ { "case_id": 12, "fir_number": "...", "label": "..." } ],
  "row_count": 47,
  "filters": { "district": "Kalaburagi", "year": 2024 }
}
```

Response `data` (matches `explanation_prompt.md`):

```json
{
  "summary": "47 theft cases were registered in Kalaburagi in 2024.",
  "evidence": [ { "case_id": 12, "fir_number": "...", "label": "..." } ],
  "why": "The query counts rows in CaseMaster joined to Unit where the district matches and the year of CrimeRegisteredDate is 2024.",
  "confidence": "high",
  "confidence_reason": "The filter is exact and the row count is well below the LIMIT.",
  "caveats": ["Excludes cases with no PoliceStationID."]
}
```

### `POST /api/v1/ai/investigate`

Body:

```json
{
  "case_id": 12,
  "case_summary": "Theft from vehicle, Kalaburagi, 2024-02-12. Accused: 1 known.",
  "similar_cases": [ { "case_id": 18, "fir_number": "...", "label": "..." } ],
  "accused_links": [ { "accused_id": 4, "shared_with_case_id": 18, "via": "phone" } ],
  "geo_context": "5 incidents in Kalaburagi within 2km in the last 30 days",
  "temporal_context": "All 5 incidents occurred between 02:00 and 04:00"
}
```

Response `data` (matches `investigation_prompt.md`):

```json
{
  "headline": "Accused X appears in 3 FIRs in Kalaburagi in 2024 with the same MO and time-of-day.",
  "patterns": [
    {
      "type": "repeat_offender",
      "description": "Same accused in 3 FIRs",
      "evidence": [ { "case_id": 12, "fir_number": "...", "label": "..." } ],
      "strength": "strong"
    }
  ],
  "questions_for_officer": [
    "Has Accused X's phone been seized?",
    "Are the 3 cases on the same beat?"
  ],
  "caveats": ["Sample size is small (3 cases)."]
}
```

---

## Error mapping

The future route layer maps each `AIProviderError` subclass
to an HTTP status code. The mapping is **fixed** so the
frontend can render predictable errors:

| Exception | HTTP status | When |
|---|---|---|
| `AIConfigurationError` | 500 | Startup misconfiguration (no API key). Should not surface in a healthy deploy. |
| `AIRequestError` | 400 | Caller supplied a bad request (context too long, malformed message). |
| `AIRateLimitError` | 429 | Provider throttled us after exhausting retries. |
| `AITimeoutError` | 504 | Call exceeded `ai_request_timeout_seconds` after exhausting retries. |
| `AIResponseError` | 502 | Provider returned 5xx after exhausting retries. |
| `UnsupportedProviderError` | 500 | Misconfiguration (unknown `ai_provider`). |
| `PromptNotFoundError` | 500 | Misconfiguration (a prompt file is missing on disk). |
| `HTTPException` (validation) | 422 | Pydantic rejected the request body. |

---

## What Phase 6 needs to build

| Piece | Where it goes |
|---|---|
| `AISchemas` (Pydantic request / response models) | `backend/schemas/ai.py` |
| `AIService` (per-endpoint orchestrators) | `backend/services/ai_service.py` |
| `ai_router` (FastAPI `APIRouter`) | `backend/api/v1/ai.py` |
| Wire-up in `backend/api/v1/__init__.py` | existing |
| Error → status mapping | `backend/api/v1/_errors.py` (new) |

The existing service layer already has the patterns needed
(session-driven services in `backend/services/`). Phase 6
follows them. The AI service is **not** different — it just
delegates to `ChatService` and the future SQL / explanation
/ investigation helpers.

---

## What is **not** in this plan

* No WebSocket / SSE streaming. Phase 6 returns a single
  response per request.
* No embedded model. Embeddings land in Phase 7 with
  `pgvector`.
* No graph traversal. Neo4j cross-case links land in Phase 8.
* No voice. Phase 9.
* No auth / RBAC. Phase 10.
