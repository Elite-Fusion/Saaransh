/**
 * useNotifications — notification state + unread count.
 *
 * Depends on the WebSocket context for real-time updates.
 * Also provides REST fallback for initial load and marking read.
 */
import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useNotifications(ws) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Initial fetch via REST
  const fetchNotifications = useCallback(async () => {
    try {
      const data = await api.get("/notifications", { limit: 50 });
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch {
      // Silent fail — WS will provide live updates
    }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await api.get("/notifications/unread-count");
      setUnreadCount(data.unread_count || 0);
    } catch {
      // Silent
    }
  }, []);

  // Load on mount
  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Listen for real-time notification events via WebSocket
  useEffect(() => {
    if (!ws?.subscribe) return;

    const unsubNotification = ws.subscribe("notification.created", (data) => {
      const notif = data?.notification || data;
      if (notif?.id) {
        setNotifications((prev) => [notif, ...prev]);
        setUnreadCount((c) => c + 1);
      }
    });

    const unsubAck = ws.subscribe("notification.ack", (data) => {
      if (data?.notification_id) {
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === data.notification_id ? { ...n, read: true } : n
          )
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      }
    });

    return () => {
      unsubNotification?.();
      unsubAck?.();
    };
  }, [ws?.subscribe]);

  const markRead = useCallback(async (notificationId) => {
    try {
      await api.post(`/notifications/${notificationId}/read`);
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, read: true } : n
        )
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // Silent
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await api.post("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // Silent
    }
  }, []);

  const acknowledge = useCallback(
    (notificationId) => {
      // Send ack via WebSocket for real-time update
      ws?.send?.({ type: "ack", notification_id: notificationId });
      // Also optimistically update locally
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, read: true } : n
        )
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    },
    [ws?.send]
  );

  return {
    notifications,
    unreadCount,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    acknowledge,
  };
}
