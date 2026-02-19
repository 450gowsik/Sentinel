/**
 * SENTINEL — Native WebSocket Service
 * Replaces Socket.IO with native WebSocket for FastAPI backend compatibility.
 */

const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`;

export type StreamMessage = {
    type: 'frame' | 'ping';
    camera_id: string;
    frame_idx: number;
    frame_b64: string;
    metadata: {
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
        pressure: number;
        collisions: Array<{ x: number, y: number, force: number, label: string }>;
    };
};

export type StreamCallback = (message: StreamMessage) => void;
export type StatusCallback = (connected: boolean) => void;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_DELAY = 10000;

const messageHandlers: Set<StreamCallback> = new Set();
const statusHandlers: Set<StatusCallback> = new Set();

function notifyStatus(connected: boolean) {
    statusHandlers.forEach((cb) => cb(connected));
}

export function connectStream(cameraId = 'cam_0'): void {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return;
    }

    const url = `${WS_BASE}/ws/live/${cameraId}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
        console.log(`[SENTINEL] WebSocket connected → ${url}`);
        reconnectAttempts = 0;
        notifyStatus(true);
    };

    ws.onmessage = (event) => {
        try {
            const data: StreamMessage = JSON.parse(event.data);
            if (data.type === 'ping') return;
            messageHandlers.forEach((cb) => cb(data));
        } catch (err) {
            console.error('[SENTINEL] WS parse error:', err);
        }
    };

    ws.onerror = () => {
        console.error('[SENTINEL] WebSocket error');
    };

    ws.onclose = (event) => {
        console.log(`[SENTINEL] Disconnected (code=${event.code})`);
        notifyStatus(false);
        ws = null;

        // Auto-reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY);
        reconnectAttempts++;
        reconnectTimer = setTimeout(() => connectStream(cameraId), delay);
    };
}

export function disconnectStream(): void {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    reconnectAttempts = 0;
    if (ws) {
        ws.close();
        ws = null;
    }
    notifyStatus(false);
}

export function onStreamMessage(handler: StreamCallback): () => void {
    messageHandlers.add(handler);
    return () => messageHandlers.delete(handler);
}

export function onStreamStatus(handler: StatusCallback): () => void {
    statusHandlers.add(handler);
    return () => statusHandlers.delete(handler);
}

export function isStreamConnected(): boolean {
    return ws !== null && ws.readyState === WebSocket.OPEN;
}
