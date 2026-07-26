import { api } from "./client";

export const mapApi = {
  getPoliceStations: (signal) => api.get("/map/stations", {}, signal),

  getFirMarkers: (filters = {}, signal) =>
    api.get(
      "/map/firs",
      {
        district: filters.district || undefined,
        police_station: filters.police_station || undefined,
        crime_type: filters.crime_type || undefined,
        severity: filters.severity || undefined,
        status: filters.status || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        bbox_min_lat: filters.bbox_min_lat || undefined,
        bbox_max_lat: filters.bbox_max_lat || undefined,
        bbox_min_lng: filters.bbox_min_lng || undefined,
        bbox_max_lng: filters.bbox_max_lng || undefined,
        repeat_offender_only: filters.repeat_offender_only || undefined,
      },
      signal
    ),

  getHeatmapPoints: (params = {}, signal) =>
    api.get(
      "/map/heatmap",
      {
        time_range: params.time_range || "7d",
        crime_type: params.crime_type || undefined,
        district: params.district || undefined,
      },
      signal
    ),

  getHotspots: (signal) => api.get("/map/hotspots", {}, signal),

  getPredictedZones: (timeframe = "24h", signal) =>
    api.get("/map/predictions", { timeframe }, signal),

  getClusters: (signal) => api.get("/map/clusters", {}, signal),

  getPatrols: (signal) => api.get("/map/patrols", {}, signal),

  getAlerts: (signal) => api.get("/map/alerts", {}, signal),

  getInvestigationOverlay: (caseId, signal) =>
    api.get(`/map/investigation-overlay/${caseId}`, {}, signal),

  getMapStats: (signal) => api.get("/map/stats", {}, signal),
};
