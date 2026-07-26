// AI investigation API.
//
// Wires the AI Assistant page to the live /api/v1/ai/investigate
// endpoint. Phase 7 ships the real backend route, so the previous
// stub is gone; we keep a hard failure if a caller forgets to pass
// a request_id, since the backend rejects 422 without one.
//
// When a future phase adds /cases/{caseId}/similar and
// /cases/{caseId}/links, plug those into similarCases() and
// linkedCases() — the shapes are documented inline so callers can
// update their JSDoc in one place.
import { api } from "./client";

// Generate a UUIDv4 in the browser without depending on Node's crypto.
// Two sources of randomness are concatenated; this is good enough for
// the unique-per-request id the backend expects, not for security.
function _generateRequestId() {
  const r = () =>
    Math.floor((1 + Math.random()) * 0x10000)
      .toString(16)
      .substring(1);
  return `${r()}${r()}-${r()}-${r()}-${r()}-${r()}${r()}${r()}`;
}

export const aiApi = {
  /**
   * POST /ai/investigate
   *
   * Request body:
   *   { question: string, request_id: string (UUIDv4) }
   *
   * Returns InvestigationResponse:
   *   { request_id, intent, operation, reasoning, executed_operation,
   *     confidence, assumptions, supporting_evidence, explanation,
   *     raw_sql, raw_params, row_count, columns, placeholder }
   *
   * The endpoint can return:
   *   200 — successful investigation (always returns a body)
   *   400 — UNKNOWN_INTENT or UNSAFE_SQL
   *   404 — CASE_NOT_FOUND (for explain_case intent)
   *   422 — request body validation failure
   *   500 — internal error
   *
   * Rejections are surfaced as ApiError with the structured detail
   * payload, so AIAssistant.jsx can render a meaningful error block.
   *
   * @param {string} question
   * @param {string} [requestId] Optional. If absent, a UUIDv4 is generated.
   * @param {AbortSignal} [signal]
   */
  investigate: (question, requestId, signal) => {
    if (!question || typeof question !== "string") {
      return Promise.reject(
        new Error("investigate() requires a non-empty `question` string")
      );
    }
    const body = {
      question: question.trim(),
      request_id: requestId || _generateRequestId(),
    };
    return api.post("/ai/investigate", body, signal);
  },

  /**
   * [STUB — Phase 8 pgvector]
   * Will be: GET /cases/{caseId}/similar
   */
  similarCases: (_caseId, _signal) => Promise.resolve(null),

  /**
   * [STUB — Phase 8 Neo4j]
   * Will be: GET /cases/{caseId}/links
   */
  linkedCases: (_caseId, _params, _signal) => Promise.resolve(null),
};
