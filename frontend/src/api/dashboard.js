// Maps 1:1 to backend/api/v1/dashboard.py (Phase 4 AnalyticsService).
//
// Verified against http://localhost:8000/docs — all paths below exist
// in the running backend unless marked [STUB].
import { api } from "./client";
import { predictionsApi } from "./predictions";

// ---------------------------------------------------------------------------
// Response normalisers
// ---------------------------------------------------------------------------

/**
 * Backend returns:
 *   { total_cases, open_cases, closed_cases, charge_sheet_filed,
 *     convictions, acquittals }
 *
 * Dashboard.jsx STAT_CARDS expect:
 *   { total_firs, active_cases, solved_cases, charge_sheet_filed,
 *     repeat_offenders, high_risk_districts }
 *   plus optional *_delta_pct / *_delta keys (not yet in backend — left null).
 *
 * This normaliser bridges the gap so the UI renders real numbers without
 * any component changes.
 */
function normaliseSummary(raw) {
  if (!raw) return raw;
  return {
    // Direct mappings
    total_firs: raw.total_cases,
    active_cases: raw.open_cases,
    solved_cases: raw.closed_cases,
    charge_sheet_filed: raw.charge_sheet_filed,
    // Not tracked yet — UI will show "—" via the `delta != null` guard
    total_firs_delta_pct: null,
    active_cases_delta_pct: null,
    solved_cases_delta_pct: null,
    // Not in current schema — future phases
    repeat_offenders: null,
    repeat_offenders_delta_pct: null,
    high_risk_districts: null,
    high_risk_districts_delta: null,
    // Pass through originals for any other consumer
    ...raw,
  };
}

/**
 * Backend /crime-head-distribution returns:
 *   { items: [{ key, label, case_count }], total }
 *
 * Dashboard.jsx "Top Crime Types" donut expects:
 *   { crime_types: [{ label, count, pct }] }
 *
 * Analytics.jsx "Trend Analysis" chart expects:
 *   { groups: [{ label, count, pct }] }
 *
 * This normaliser satisfies both shapes from one backend call.
 */
function normaliseCrimeHeadDistribution(raw) {
  if (!raw) return raw;
  const total = raw.total || 1; // avoid /0
  const mapped = (raw.items ?? []).map((item) => ({
    label: item.label,
    count: item.case_count,
    pct: total > 0 ? Math.round((item.case_count / total) * 100) : 0,
    key: item.key,
  }));
  return {
    crime_types: mapped, // Dashboard.jsx donut
    groups: mapped,      // Analytics.jsx table + chart
    total: raw.total,
  };
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const dashboardApi = {
  /**
   * GET /dashboard/summary
   * Optional params: { district, district_id }
   * @returns {Promise<NormalisedSummary>}
   */
  getSummary: (params, signal) =>
    api.get("/dashboard/summary", params ?? null, signal).then(normaliseSummary),

  /**
   * GET /dashboard/crime-head-distribution
   * Replaces the old getTrends("/dashboard/trends") call — that path does not
   * exist. This endpoint returns crime-head counts which the Dashboard donut
   * and Analytics page both consume.
   * Optional params: { district, district_id }
   * @returns {Promise<{ crime_types, groups, total }>}
   */
  getTrends: (params, signal) =>
    api
      .get("/dashboard/crime-head-distribution", params ?? null, signal)
      .then(normaliseCrimeHeadDistribution),

  /**
   * GET /dashboard/monthly-trends
   * @param {{ year?: number, district?: string, district_id?: number }} params
   * @returns {Promise<MonthlyTrendsResponse>}
   */
  getMonthlyTrends: (params, signal) =>
    api.get("/dashboard/monthly-trends", params ?? null, signal),

  /**
   * GET /dashboard/status-distribution
   * @returns {Promise<CategoryDistributionResponse>}
   */
  getStatusDistribution: (signal) =>
    api.get("/dashboard/status-distribution", null, signal),

  /**
   * GET /dashboard/district-distribution
   * @returns {Promise<CategoryDistributionResponse>}
   */
  getDistrictDistribution: (signal) =>
    api.get("/dashboard/district-distribution", null, signal),

  /**
   * GET /dashboard/recent-cases
   * @param {{ page?: number, page_size?: number }} params
   * @returns {Promise<RecentCasesResponse>}
   */
  getRecentCases: (params, signal) =>
    api.get("/dashboard/recent-cases", params ?? null, signal),

  // ---------------------------------------------------------------------------
  // Phase 9: Prediction-powered dashboard panels.
  // ---------------------------------------------------------------------------

  /**
   * District-level hotspot predictions for the choropleth map.
   * Delegates to the predictions API and reshapes the envelope
   * into the { districts: [...] } shape the Dashboard.jsx RiskGrid expects.
   */
  getRiskMap: async (params, signal) => {
    const envelope = await predictionsApi.getHotspots({ top_n: 30 }, signal);
    const hotspots = envelope?.hotspots ?? [];
    const byDistrict = {};
    for (const h of hotspots) {
      if (!byDistrict[h.district_name]) {
        byDistrict[h.district_name] = { name: h.district_name, risk_level: "low", score: 0 };
      }
      const entry = byDistrict[h.district_name];
      entry.score = Math.max(entry.score, h.predicted_count);
      entry.risk_level = h.risk_band;
    }
    return { districts: Object.values(byDistrict) };
  },

  /**
   * AI crime prediction headline for the Dashboard prediction card.
   * Fetches trends and picks the top predicted crime head.
   */
  getPrediction: async (params, signal) => {
    const envelope = await predictionsApi.getTrends({ horizon_months: 1 }, signal);
    const trends = envelope?.trends ?? [];
    if (trends.length === 0) return null;
    const top = trends.reduce((max, t) => t.predicted_count > max.predicted_count ? t : max, trends[0]);
    return {
      headline: `Predicted ${top.predicted_count} ${top.crime_head} cases in ${top.month_label}`,
      districts: [],
      confidence_pct: Math.round(top.confidence * 100),
    };
  },
};
