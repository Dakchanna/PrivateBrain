import { useState, useEffect, useRef, useCallback } from 'react';
import { WsEvent } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const MAX_EVENTS = 200;

export function useWebSocket() {
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [latestEvent, setLatestEvent] = useState<WsEvent | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(`${WS_URL}/ws`);

      ws.current.onopen = () => {
        setConnected(true);
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      };

      ws.current.onmessage = (e) => {
        try {
          const event: WsEvent = JSON.parse(e.data);
          setLatestEvent(event);
          setEvents(prev => {
            const next = [event, ...prev];
            return next.slice(0, MAX_EVENTS);
          });
        } catch {/* ignore bad messages */}
      };

      ws.current.onclose = () => {
        setConnected(false);
        // Auto-reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.current.onerror = () => {
        ws.current?.close();
      };
    } catch {
      reconnectTimer.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  return { events, connected, latestEvent };
}
