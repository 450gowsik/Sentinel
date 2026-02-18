import { useEffect, useRef, useState, useCallback } from 'react';

const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`;
const MAX_RECONNECT_DELAY = 10000;
const MAX_RECONNECT_ATTEMPTS = 5;

export const StreamStatus = {
  CONNECTING: 'CONNECTING',
  OPEN: 'OPEN',
  CLOSED: 'CLOSED',
  ERROR: 'ERROR',
} as const;

export type StreamStatus = (typeof StreamStatus)[keyof typeof StreamStatus];

interface StreamMetadata {
  person_count: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  density: number;
  congestion: number;
  anomaly: number;
  latency_ms: number;
  alert_tier: string | null;
  tracks: number;
  fps: number;
  flow_magnitude: number;
}

interface StreamFrame {
  type: string;
  camera_id: string;
  frame_idx: number;
  frame_b64: string;
  metadata: StreamMetadata;
}

interface UseSentinelStreamReturn {
  frame: string | null;
  metadata: StreamMetadata | null;
  status: StreamStatus;
  error: string | null;
  reconnectCount: number;
  connected: boolean; // Added for backward compatibility/easy check
}

export function useSentinelStream(cameraId: string = 'cam_0', enabled: boolean = true): UseSentinelStreamReturn {
  const [frame, setFrame] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<StreamMetadata | null>(null);
  const [status, setStatus] = useState<StreamStatus>(StreamStatus.CLOSED);
  const [error, setError] = useState<string | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  // Refs for stable execution without triggering re-renders
  const wsRef = useRef<WebSocket | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isDestroyedRef = useRef(false);

  // 1. Cleanup Function
  const cleanup = useCallback(() => {
    isDestroyedRef.current = true; // Mark as destroyed immediately

    if (wsRef.current) {
      const ws = wsRef.current;
      // Remove listeners to prevent "stale" event firing
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      ws.onopen = null;

      if (ws.readyState === WebSocket.CONNECTING) {
        // Guard: if socket.readyState === CONNECTING, wait for open then close
        // to avoid "WebSocket is closed before the connection is established"
        ws.onopen = () => {
          try { ws.close(); } catch (e) { }
        };
      } else {
        try { ws.close(); } catch (e) { }
      }
      wsRef.current = null;
    }

    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // 2. Message Handler
  const handleMessage = useCallback((event: MessageEvent) => {
    if (isDestroyedRef.current) return;
    if (event.data === 'pong') return;

    try {
      const data: StreamFrame = JSON.parse(event.data);
      if (data.type === 'frame' && data.frame_b64) {
        setFrame(`data:image/jpeg;base64,${data.frame_b64}`);
        setMetadata(data.metadata);
      }
    } catch (err) {
      // ignore
    }
  }, []);

  // 3. Connection Logic
  const connect = useCallback(() => {
    if (!enabled) {
      setStatus(StreamStatus.CLOSED);
      setFrame(null);
      setMetadata(null);
      return;
    }

    if (reconnectCount >= MAX_RECONNECT_ATTEMPTS) {
      setError(`Stream unavailable after ${MAX_RECONNECT_ATTEMPTS} attempts.`);
      return;
    }

    // Ensure clean state (safe check, cleanup usually handles this)
    if (wsRef.current) {
      try { wsRef.current.close(); } catch (e) { }
    }

    // Reset destroyed flag for NEW connection attempt
    isDestroyedRef.current = false;

    // Add token for auth (implied requirement from user)
    // Note: User asked to fix 403 on browser stream, but using token here is safe practice too.
    const url = `${WS_BASE}/ws/live/${cameraId}`;

    setStatus(StreamStatus.CONNECTING);
    if (reconnectCount === 0) setError(null);

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (isDestroyedRef.current) {
        ws.close();
        return;
      }
      setStatus(StreamStatus.OPEN);
      setReconnectCount(0);
      setError(null);
      console.log(`[SENTINEL] Connected to ${cameraId}`);

      // Start Heartbeat (30s)
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      if (isDestroyedRef.current) return;
      setStatus(StreamStatus.ERROR);
    };

    ws.onclose = (event) => {
      // If destroyed, ignore
      if (isDestroyedRef.current) return;

      setStatus(StreamStatus.CLOSED);

      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }

      if (event.code === 1013) {
        setError('Server capacity reached.');
        return;
      }

      // Retry Logic
      const nextCount = reconnectCount + 1;
      if (nextCount > MAX_RECONNECT_ATTEMPTS) {
        setError('Max reconnection attempts reached.');
        return;
      }

      const delay = Math.min(1000 * Math.pow(2, reconnectCount), MAX_RECONNECT_DELAY);

      retryTimeoutRef.current = setTimeout(() => {
        if (!isDestroyedRef.current) {
          setReconnectCount(c => c + 1);
        }
      }, delay);
    };
  }, [cameraId, cleanup, handleMessage, reconnectCount]);

  // 4. Lifecycle Effect
  useEffect(() => {
    isDestroyedRef.current = false;
    connect();

    return () => {
      cleanup();
    };
  }, [cameraId, enabled, connect]); // cleanup is stable

  return {
    frame,
    metadata,
    status,
    connected: status === StreamStatus.OPEN,
    error,
    reconnectCount
  };
}
