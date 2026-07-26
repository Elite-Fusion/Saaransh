/**
 * useWebSocket — core WebSocket hook with auto-reconnect.
 *
 * Manages a single WebSocket connection per authenticated user.
 * Handles:
 *   - Connection with JWT auth
 *   - Automatic reconnect with exponential backoff
 *   - Heartbeat (pong responses)
 *   - Message dispatch to registered handlers
 *   - Offline detection
 *   - Queued outgoing messages
 */
import { useEffect, useRef, useCallback, useState } from "react";

const WS_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1")
    .replace(/^http/, "ws");

const STORAGE_KEY_ACCESS = "saaransh_access_token";

const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;
const HEARTBEAT_INTERVAL = 25000;

export function useWebSocket() {
  const wsRef = useRef(null);
  const handlersRef = useRef(new Map());
  const queueRef = useRef([]);
  const reconnectDelayRef = useRef(RECONNECT_BASE_DELAY);
  const reconnectTimerRef = useRef(null);
  const heartbeatRef = useRef(null);
  const [status, setStatus] = useState("disconnected"); // disconnected | connecting | connected

  const getToken = useCallback(() => {
    return localStorage.getItem(STORAGE_KEY_ACCESS);
  }, []);

  const connect = useCallback(() => {
    const token = getToken();
    if (!token || wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(`${WS_BASE_URL}/ws?token=${token}`);

    ws.onopen = () => {
      setStatus("connected");
      reconnectDelayRef.current = RECONNECT_BASE_DELAY;

      // Flush queued messages
      while (queueRef.current.length > 0) {
        const msg = queueRef.current.shift();
        ws.send(JSON.stringify(msg));
      }

      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "pong" }));
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const type = msg.type;

        // Dispatch to registered handlers
        const typeHandlers = handlersRef.current.get(type);
        if (typeHandlers) {
          typeHandlers.forEach((fn) => fn(msg.data || msg));
        }

        // Wildcard handlers
        const wildcardHandlers = handlersRef.current.get("*");
        if (wildcardHandlers) {
          wildcardHandlers.forEach((fn) => fn(msg));
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      clearInterval(heartbeatRef.current);

      // Exponential backoff reconnect
      const delay = reconnectDelayRef.current;
      reconnectDelayRef.current = Math.min(delay * 2, RECONNECT_MAX_DELAY);
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, delay);
    };

    ws.onerror = () => {
      // onclose will fire after this
      ws.close();
    };

    wsRef.current = ws;
  }, [getToken]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimerRef.current);
    clearInterval(heartbeatRef.current);
    reconnectDelayRef.current = RECONNECT_MAX_DELAY; // prevent auto-reconnect
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  const send = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      queueRef.current.push(message);
    }
  }, []);

  const subscribe = useCallback((eventType, handler) => {
    if (!handlersRef.current.has(eventType)) {
      handlersRef.current.set(eventType, new Set());
    }
    handlersRef.current.get(eventType).add(handler);

    // Return unsubscribe function
    return () => {
      handlersRef.current.get(eventType)?.delete(handler);
    };
  }, []);

  const joinRoom = useCallback((room) => {
    send({ type: "subscribe", room });
  }, [send]);

  const leaveRoom = useCallback((room) => {
    send({ type: "unsubscribe", room });
  }, [send]);

  // Auto-connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Detect browser online/offline
  useEffect(() => {
    const handleOnline = () => connect();
    const handleOffline = () => setStatus("disconnected");

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [connect]);

  return {
    status,
    send,
    subscribe,
    joinRoom,
    leaveRoom,
    connect,
    disconnect,
  };
}
