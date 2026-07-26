// Maps to backend/api/v1/cases.py (Phase 3 read-only case APIs).
//
// Supported GET /cases query params:
//   page, page_size, fir_number, district, district_id, police_station,
//   police_station_id, crime_head, crime_head_id, crime_sub_head,
//   crime_sub_head_id, status, status_id, date_from, date_to,
//   sort_by, sort_order
//
// NOTE: free-text `q` is NOT supported by the backend — omit it from
// params before sending or it will be silently ignored.
import { api } from "./client";

export const casesApi = {
  /**
   * @param {Object} params - See supported params above.
   *   Pass `fir_number` for exact FIR lookup; `crime_head` / `police_station`
   *   for name-based filters; `date_from` / `date_to` (YYYY-MM-DD) for range.
   *   `q` is stripped here — the backend has no free-text search yet.
   * @returns {Promise<{ items: CaseSummaryOut[], pagination: PaginationMeta }>}
   */
  list: (params, signal) => {
    // Strip unsupported free-text param so it doesn't confuse callers
    // when the backend silently ignores it.
    const { q, ...supported } = params ?? {};
    // If caller passed q, map it to fir_number as the closest equivalent
    // (exact FIR lookup). Remove this mapping once a search endpoint ships.
    if (q) supported.fir_number = q;
    return api.get("/cases", supported, signal);
  },

  /**
   * @param {number} caseId - CaseMasterID
   * @returns {Promise<CaseDetailOut>}
   */
  getById: (caseId, signal) => api.get(`/cases/${caseId}`, null, signal),

  /**
   * POST /cases — NOT YET IMPLEMENTED in the backend (Phase 3 is read-only).
   * Calling this will throw immediately so the UI can show an appropriate
   * message rather than receiving a 405 from the server.
   */
  create: (_payload, _signal) => {
    return Promise.reject(
      new Error("FIR intake (POST /cases) is not yet available — backend write endpoints ship in a future phase.")
    );
  },
};
