import { useEffect, useRef, useState } from "react";
import {
  sessionToken,
  webSocketUrl,
  type WikiEvent,
} from "../lib/api";

interface Options {
  onEvent: (event: WikiEvent) => void;
  onConnected?: () => void;
}

export function useLiveEvents({ onEvent, onConnected }: Options): boolean {
  const [connected, setConnected] = useState(false);
  const eventHandler = useRef(onEvent);
  const connectedHandler = useRef(onConnected);

  useEffect(() => {
    eventHandler.current = onEvent;
    connectedHandler.current = onConnected;
  }, [onConnected, onEvent]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let cancelled = false;
    let reconnectTimer: number | null = null;
    let attempt = 0;

    const connect = async () => {
      try {
        const token = await sessionToken();
        if (cancelled) return;
        socket = new WebSocket(webSocketUrl());
        socket.onopen = () => {
          socket?.send(JSON.stringify({ type: "auth", token }));
          attempt = 0;
          setConnected(true);
          connectedHandler.current?.();
        };
        socket.onmessage = (message) => {
          try {
            eventHandler.current(JSON.parse(message.data) as WikiEvent);
          } catch {
            // Ignore malformed local events.
          }
        };
        socket.onerror = () => socket?.close();
        socket.onclose = () => {
          setConnected(false);
          if (cancelled) return;
          const delay = [1, 2, 5, 10][Math.min(attempt, 3)] * 1000;
          attempt += 1;
          reconnectTimer = window.setTimeout(connect, delay);
        };
      } catch {
        if (!cancelled) {
          const delay = [1, 2, 5, 10][Math.min(attempt, 3)] * 1000;
          attempt += 1;
          reconnectTimer = window.setTimeout(connect, delay);
        }
      }
    };

    void connect();
    return () => {
      cancelled = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return connected;
}

