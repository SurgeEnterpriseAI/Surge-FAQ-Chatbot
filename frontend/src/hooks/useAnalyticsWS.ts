import { useEffect, useState, useRef, useCallback } from "react";
import type { LiveActivityEvent } from "../lib/types";

const getWsUrl = () => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/analytics/events`;
};

/** Reconnect backoff: 1s, 2s, 4s … capped, so a stopped backend is not hammered. */
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export function useAnalyticsWS() {
  const [events, setEvents] = useState<LiveActivityEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(true);
  const attemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (!shouldReconnectRef.current || wsRef.current) return;

    const url = getWsUrl();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      attemptsRef.current = 0;
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setEvents((prev) => [parsed, ...prev].slice(0, 100)); // Keep only latest 100 events
      } catch (err) {
        console.error("Error parsing websocket message: ", err);
      }
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      wsRef.current = null;
      if (!shouldReconnectRef.current) return;

      // A close before the socket ever opened means nothing is serving the
      // route — almost always the backend not running on port 8001.
      if (attemptsRef.current === 0 && !event.wasClean) {
        console.warn(
          `Live activity stream unavailable at ${url} ` +
            `(close code ${event.code}${event.reason ? `: ${event.reason}` : ""}). ` +
            "Is the backend running on port 8001? Retrying with backoff.",
        );
      }

      const delay = Math.min(
        RECONNECT_BASE_MS * 2 ** attemptsRef.current,
        RECONNECT_MAX_MS,
      );
      attemptsRef.current += 1;
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    };

    // The browser exposes no detail on a WebSocket error event, so the useful
    // diagnostics are logged from onclose, which always follows.
    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    shouldReconnectRef.current = true;
    attemptsRef.current = 0;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      const ws = wsRef.current;
      wsRef.current = null;
      if (!ws) return;

      // Detach handlers before closing. Closing a still-CONNECTING socket makes
      // the browser fire an error event, which under StrictMode's double-mount
      // would otherwise log a spurious error on every page load.
      ws.onopen = null;
      ws.onmessage = null;
      ws.onclose = null;
      ws.onerror = null;
      ws.close();
    };
  }, [connect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isConnected, clearEvents };
}
