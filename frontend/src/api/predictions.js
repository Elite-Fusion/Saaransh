// Maps 1:1 to backend/api/v1/predictions.py (Phase 9 Predictive Intelligence).
//
// All endpoints return a PredictionEnvelope shape:
//   { generated_at, predictor, note, hotspots?, repeat_offenders?, trends?,
//     clusters?, similar_cases?, risk_score?, recommendations? }
import { api } from "./client";

export const predictionsApi = {
  /**
   * GET /predictions/hotspots
   * @param {{ top_n?: number }} params
   * @returns {Promise<PredictionEnvelope>}
   */
  getHotspots: (params, signal) =>
    api.get("/predictions/hotspots", params ?? null, signal),

  /**
   * GET /predictions/trends
   * @param {{ horizon_months?: number }} params
   * @returns {Promise<PredictionEnvelope>}
   */
  getTrends: (params, signal) =>
    api.get("/predictions/trends", params ?? null, signal),

  /**
   * GET /predictions/repeat-offenders
   * @param {{ top_n?: number }} params
   * @returns {Promise<PredictionEnvelope>}
   */
  getRepeatOffenders: (params, signal) =>
    api.get("/predictions/repeat-offenders", params ?? null, signal),

  /**
   * GET /predictions/clusters
   * @param {{ top_n?: number }} params
   * @returns {Promise<PredictionEnvelope>}
   */
  getClusters: (params, signal) =>
    api.get("/predictions/clusters", params ?? null, signal),

  /**
   * GET /predictions/risk-score/{case_id}
   * @param {number} caseId
   * @returns {Promise<PredictionEnvelope>}
   */
  getRiskScore: (caseId, signal) =>
    api.get(`/predictions/risk-score/${caseId}`, null, signal),

  /**
   * POST /predictions/similar-cases
   * @param {{ case_id: number, top_k?: number }} body
   * @returns {Promise<PredictionEnvelope>}
   */
  getSimilarCases: (body, signal) =>
    api.post("/predictions/similar-cases", body, signal),

  /**
   * GET /predictions/recommendations/{case_id}
   * @param {number} caseId
   * @param {{ top_n?: number }} params
   * @returns {Promise<PredictionEnvelope>}
   */
  getRecommendations: (caseId, params, signal) =>
    api.get(`/predictions/recommendations/${caseId}`, params ?? null, signal),
};
