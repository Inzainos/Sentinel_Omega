import { useEffect, useRef, useState, useCallback } from "react";

export interface WebSocketMessage<T = any> {
  type: string;
  payload: T;
  timestamp: number;
}

export interface UseWebSocketOptions<T> {
  url: string;
  protocols?: string | string[];
  onMessage?: (data: T) => void;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  fallbackPolling?: boolean;
  pollingInterval?: number;
  pollingFn?: () => Promise<T>;
}

export interface UseWebSocketReturn<T> {
  data: T | null;
  lastMessage: WebSocketMessage<T> | null;
  status: "connecting" | "open" | "closed" | "error" | "polling";
  error: Event | null;
  send: (message: any) => void;
  reconnect: () => void;
  close: () => void;
}

export function useWebSocket<T = any>({
  url,
  protocols,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
  fallbackPolling = true,
  pollingInterval = 20000,
  pollingFn,
}: UseWebSocketOptions<T>): UseWebSocketReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage<T> | null>(null);
  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error" | "polling">("connecting");
  const [error, setError] = useState<Event | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMounted = useRef(true);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (!fallbackPolling || !pollingFn || pollingIntervalRef.current) return;
    setStatus("polling");
    const poll = async () => {
      if (!isMounted.current) return;
      try {
        const result = await pollingFn();
        if (isMounted.current) {
          setData(result);
          setLastMessage({ type: "poll", payload: result, timestamp: Date.now() });
        }
      } catch (err) {
        console.warn("Polling failed:", err);
      }
    };
    poll();
    pollingIntervalRef.current = setInterval(poll, pollingInterval);
  }, [fallbackPolling, pollingFn, pollingInterval]);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!isMounted.current) return;
    cleanup();
    setStatus("connecting");
    setError(null);

    try {
      const ws = new WebSocket(url, protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted.current) return;
        reconnectAttempts.current = 0;
        setStatus("open");
        stopPolling();
        onOpen?.();
      };

      ws.onmessage = (event) => {
        if (!isMounted.current) return;
        try {
          const message: WebSocketMessage<T> = JSON.parse(event.data);
          setData(message.payload);
          setLastMessage(message);
          onMessage?.(message.payload);
        } catch {
          console.warn("Failed to parse WebSocket message:", event.data);
        }
      };

      ws.onerror = (event) => {
        if (!isMounted.current) return;
        setError(event);
        setStatus("error");
        onError?.(event);
      };

      ws.onclose = (event) => {
        if (!isMounted.current) return;
        setStatus("closed");
        onClose?.(event);

        if (reconnect && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMounted.current) {
              connect();
            }
          }, reconnectInterval * Math.min(reconnectAttempts.current, 5));
        } else if (fallbackPolling && pollingFn) {
          startPolling();
        }
      };
    } catch (err) {
      setError(err as Event);
      setStatus("error");
      if (fallbackPolling && pollingFn) {
        startPolling();
      }
    }
  }, [url, protocols, reconnect, maxReconnectAttempts, reconnectInterval, fallbackPolling, pollingFn, onOpen, onClose, onError, onMessage, cleanup, startPolling, stopPolling]);

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const forceReconnect = useCallback(() => {
    reconnectAttempts.current = 0;
    connect();
  }, [connect]);

  const close = useCallback(() => {
    reconnect = false;
    cleanup();
    setStatus("closed");
  }, [cleanup]);

  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      isMounted.current = false;
      cleanup();
    };
  }, [connect, cleanup]);

  return {
    data,
    lastMessage,
    status,
    error,
    send,
    reconnect: forceReconnect,
    close,
  };
}

export function createPollingHook<T>(pollingFn: () => Promise<T>, interval: number = 20000) {
  return function usePolling() {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const isMounted = useRef(true);

    const fetchData = useCallback(async () => {
      if (!isMounted.current) return;
      try {
        setError(null);
        const result = await pollingFn();
        if (isMounted.current) {
          setData(result);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted.current) {
          setError(err as Error);
          setLoading(false);
        }
      }
    }, [pollingFn]);

    useEffect(() => {
      isMounted.current = true;
      fetchData();
      intervalRef.current = setInterval(fetchData, interval);
      return () => {
        isMounted.current = false;
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }, [fetchData, interval]);

    return { data, loading, error, refetch: fetchData };
  };
}