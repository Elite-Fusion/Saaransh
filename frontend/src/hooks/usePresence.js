/**
 * usePresence — track online officers.
 *
 * Listens for presence.user_joined and presence.user_left events
 * via the WebSocket, and maintains a local list of online users.
 * Also provides a REST fetch for initial load.
 */
import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function usePresence(ws) {
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [onlineCount, setOnlineCount] = useState(0);

  // Initial fetch via REST
  const fetchOnlineUsers = useCallback(async () => {
    try {
      const data = await api.get("/presence/online");
      setOnlineUsers(data.users || []);
      setOnlineCount(data.count || 0);
    } catch {
      // Silent
    }
  }, []);

  useEffect(() => {
    fetchOnlineUsers();
  }, [fetchOnlineUsers]);

  // Listen for real-time presence events via WebSocket
  useEffect(() => {
    if (!ws?.subscribe) return;

    const unsubJoin = ws.subscribe("presence.user_joined", (data) => {
      if (data?.user_id) {
        setOnlineUsers((prev) => {
          const exists = prev.some((u) => u.user_id === data.user_id);
          if (exists) return prev;
          return [...prev, {
            user_id: data.user_id,
            email: data.email || "",
            role: data.role || "",
            police_station: data.police_station || "",
            last_active: data.last_active || new Date().toISOString(),
          }];
        });
        setOnlineCount((c) => c + 1);
      }
    });

    const unsubLeave = ws.subscribe("presence.user_left", (data) => {
      if (data?.user_id) {
        setOnlineUsers((prev) => prev.filter((u) => u.user_id !== data.user_id));
        setOnlineCount((c) => Math.max(0, c - 1));
      }
    });

    return () => {
      unsubJoin?.();
      unsubLeave?.();
    };
  }, [ws?.subscribe]);

  // Refresh periodically (every 60s) as a fallback
  useEffect(() => {
    const interval = setInterval(fetchOnlineUsers, 60000);
    return () => clearInterval(interval);
  }, [fetchOnlineUsers]);

  return {
    onlineUsers,
    onlineCount,
    fetchOnlineUsers,
  };
}
