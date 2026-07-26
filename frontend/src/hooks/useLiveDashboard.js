/**
 * useLiveDashboard — auto-refresh dashboard/analytics data on WebSocket events.
 *
 * Subscribes to dashboard and analytics rooms.  When a relevant event
 * arrives (case created, case updated, prediction generated, etc.),
 * it triggers React Query refetches for the affected query keys.
 */
import { useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

// Events that should trigger a dashboard summary refresh
const DASHBOARD_EVENTS = new Set([
  "case.created",
  "case.updated",
  "case.closed",
  "dashboard.summary_updated",
]);

// Events that should trigger analytics/trend refresh
const ANALYTICS_EVENTS = new Set([
  "case.created",
  "case.updated",
  "analytics.trends_updated",
  "dashboard.crime_head_updated",
]);

// Events that should trigger prediction refresh
const PREDICTION_EVENTS = new Set([
  "prediction.generated",
  "prediction.updated",
]);

// Events that should trigger risk map refresh
const RISK_MAP_EVENTS = new Set([
  "case.created",
  "prediction.generated",
  "dashboard.risk_map_updated",
]);

export function useLiveDashboard(ws) {
  const queryClient = useQueryClient();

  const invalidateQueries = useCallback(
    (queryKeyPrefix) => {
      queryClient.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0]?.startsWith?.(queryKeyPrefix) ||
          (Array.isArray(query.queryKey[0]) &&
            query.queryKey[0][0]?.startsWith?.(queryKeyPrefix)),
      });
    },
    [queryClient]
  );

  // Subscribe to WebSocket events
  useEffect(() => {
    if (!ws?.subscribe) return;

    const unsubs = [];

    // Dashboard events -> refetch dashboard queries
    unsubs.push(
      ws.subscribe("*", (msg) => {
        const eventType = msg?.type;

        if (DASHBOARD_EVENTS.has(eventType)) {
          invalidateQueries("dashboard");
        }

        if (ANALYTICS_EVENTS.has(eventType)) {
          invalidateQueries("analytics");
        }

        if (PREDICTION_EVENTS.has(eventType)) {
          invalidateQueries("predictions");
        }

        if (RISK_MAP_EVENTS.has(eventType)) {
          // Risk map uses dashboard queries
          invalidateQueries("dashboard");
        }
      })
    );

    return () => {
      unsubs.forEach((fn) => fn?.());
    };
  }, [ws?.subscribe, invalidateQueries]);

  // Join relevant rooms
  useEffect(() => {
    if (!ws?.joinRoom) return;
    ws.joinRoom("dashboard");
    ws.joinRoom("analytics");
    ws.joinRoom("predictions");
  }, [ws?.joinRoom, ws?.leaveRoom]);
}
