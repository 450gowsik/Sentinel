import { Eye, Wifi, WifiOff, Camera, AlertTriangle, Monitor, Smartphone, Power } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';

// WebSocket URLs
const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`;
const WS_URL = `${WS_BASE}/ws/live/cam_0`;

type CameraSource = 'backend' | 'browser';
type CameraPermission = 'prompt' | 'granted' | 'denied' | 'unavailable';
type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface StreamMetadata {
    person_count: number;
    risk_score: number;
    risk_level: string;
    density: number;
    congestion: number;
    anomaly: number;
    latency_ms: number;
    alert_tier: string;
    tracks: number;
    fps: number;
    flow_magnitude: number;
}

interface CameraAlert {
    type: 'warning' | 'error' | 'info';
    title: string;
    message: string;
    action?: string;
    onAction?: () => void;
}

import { useDashboardStore } from '../../store/useDashboardStore';

export default function YOLODetectionOverlay() {
    const backendCameraActive = useDashboardStore((s) => s.backendCameraActive);

    // Stream state
    const [imageSrc, setImageSrc] = useState<string | null>(null);
    const [metadata, setMetadata] = useState<StreamMetadata | null>(null);
    const [status, setStatus] = useState<ConnectionStatus>('connecting');
    const [isDemoMode, setIsDemoMode] = useState(false);

    // Camera source state: Default to BACKEND (Server)
    const [cameraSource, setCameraSource] = useState<CameraSource>('backend');
    const [isStopped, setIsStopped] = useState(false);
    const [alert, setAlert] = useState<CameraAlert | null>(null);
    const [browserCamActive, setBrowserCamActive] = useState(false);

    // Refs
    const wsRef = useRef<WebSocket | null>(null);
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const captureIntervalRef = useRef<number | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);
    const connectTimeoutRef = useRef<number | null>(null);
    const isDestroyedRef = useRef(false);
    const isCameraRequestingRef = useRef(false);

    // ── Check browser camera permission ────────────────────
    const checkCameraPermission = useCallback(async (): Promise<CameraPermission> => {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                return 'unavailable';
            }
            if (navigator.permissions) {
                try {
                    const result = await navigator.permissions.query({ name: 'camera' as PermissionName });
                    return result.state === 'granted' ? 'granted'
                        : result.state === 'denied' ? 'denied'
                            : 'prompt';
                } catch { }
            }
            return 'prompt';
        } catch {
            return 'unavailable';
        }
    }, []);

    // ── Unified WebSocket Connection Logic ─────────────────
    const connectWS = useCallback(() => {
        if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

        // Cleanup existing
        if (wsRef.current) {
            const oldWs = wsRef.current;
            oldWs.onclose = null;
            oldWs.onerror = null;
            oldWs.onmessage = null;
            oldWs.onopen = null;
            if (oldWs.readyState === WebSocket.OPEN || oldWs.readyState === WebSocket.CONNECTING) {
                oldWs.close();
            }
            wsRef.current = null;
        }

        if (isDestroyedRef.current || isStopped || !backendCameraActive) return;

        setStatus('connecting');

        connectTimeoutRef.current = window.setTimeout(() => {
            if (isDestroyedRef.current || isStopped || !backendCameraActive) return;

            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                if (isDestroyedRef.current) {
                    ws.close();
                    return;
                }
                setStatus('connected');
                setAlert(null);
            };

            ws.onmessage = (event) => {
                if (isDestroyedRef.current) return;
                try {
                    if (event.data === 'pong') return;
                    const data = JSON.parse(event.data);

                    if (data.type === 'frame') {
                        if (cameraSource === 'backend') {
                            if (data.frame_b64) {
                                setImageSrc(`data:image/jpeg;base64,${data.frame_b64}`);
                            }
                            setMetadata(data.metadata);
                            setIsDemoMode(data.demo_mode ?? false);
                        }
                    }
                } catch (e) {
                    // ignore
                }
            };

            ws.onclose = () => {
                if (isDestroyedRef.current) return;
                setStatus('disconnected');
                if (!isStopped && cameraSource === 'backend' && backendCameraActive) {
                    reconnectTimeoutRef.current = window.setTimeout(() => connectWS(), 3000);
                }
            };

            ws.onerror = () => {
                if (isDestroyedRef.current) return;
            };

        }, 0);
    }, [cameraSource, isStopped, backendCameraActive]);

    // ── Browser Camera Management ──────────────────────────
    const stopBrowserCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (captureIntervalRef.current) {
            clearInterval(captureIntervalRef.current);
            captureIntervalRef.current = null;
        }
        setBrowserCamActive(false);
    }, []);

    const startBrowserCamera = useCallback(async () => {
        // Guard: Prevent duplicate requests (StrictMode double-invoke protection)
        if (isCameraRequestingRef.current) return;
        isCameraRequestingRef.current = true;

        try {
            stopBrowserCamera();
            // Wait for HW release
            await new Promise(resolve => setTimeout(resolve, 300));

            setAlert({ type: 'info', title: 'Requesting Access', message: 'Please allow camera access...' });

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'environment' },
                audio: false
            });

            streamRef.current = stream;
            setBrowserCamActive(true);
            setAlert(null);

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();
            }

        } catch (err: any) {
            console.error('Camera access error:', err);

            if (err.name === 'NotReadableError') {
                setAlert({
                    type: 'error',
                    title: 'Camera Hardware Busy',
                    message: 'Another app (OBS, Zoom, Teams, etc.) is using your camera. Close that app completely, then retry.',
                    action: 'Retry',
                    onAction: () => {
                        setAlert(null);
                        setTimeout(() => startBrowserCamera(), 500);
                    }
                });
            } else if (err.name === 'NotAllowedError') {
                setAlert({
                    type: 'error',
                    title: 'Permission Denied',
                    message: 'Camera permission was denied. Enable it in browser settings.',
                });
            } else {
                setAlert({
                    type: 'error',
                    title: 'Camera Error',
                    message: `Could not access camera: ${err.message}`
                });
            }
        } finally {
            isCameraRequestingRef.current = false;
        }
    }, [stopBrowserCamera]);


    // ── Switch Source ──────────────────────────────────────
    const switchToSource = useCallback(async (source: CameraSource) => {
        if (source === 'browser') {
            const perm = await checkCameraPermission();
            if (perm === 'granted' || perm === 'prompt') {
                setCameraSource(source);
                setIsStopped(false);
                startBrowserCamera();
            } else {
                setAlert({ type: 'error', title: 'Permission Issue', message: 'Camera permission denied.' });
            }
        } else {
            stopBrowserCamera();
            setCameraSource(source);
            setIsStopped(false);
            connectWS();
        }
    }, [checkCameraPermission, startBrowserCamera, stopBrowserCamera, connectWS]);

    // ── Auto-Fallback Logic ───────────────────────────────
    useEffect(() => {
        if (!backendCameraActive && cameraSource === 'backend' && !isStopped) {
            // Automatically switch to browser mode if backend is released
            // or just stop if browser perm is unknown
            switchToSource('browser');
        }
    }, [backendCameraActive, cameraSource, isStopped, switchToSource]);

    const stopAll = useCallback(() => {
        stopBrowserCamera();

        setIsStopped(true);
        setStatus('disconnected');

        if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, [stopBrowserCamera]);

    // ── Lifecycle ──────────────────────────────────────────
    useEffect(() => {
        isDestroyedRef.current = false;

        // Initial setup - ONLY perform safe actions
        // checkCameraPermission(); // Safe query

        // ONLY auto-connect to backend if default is backend
        // This ensures NO camera requests happen on mount if user somehow sets default to browser (which we prevented)
        if (!isStopped && cameraSource === 'backend' && backendCameraActive) {
            connectWS();
        }

        return () => {
            isDestroyedRef.current = true;

            if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

            stopBrowserCamera();

            if (wsRef.current) {
                const ws = wsRef.current;
                // prevent phantom callbacks
                ws.onclose = null;
                ws.onerror = null;
                ws.onmessage = null;
                ws.onopen = null;

                if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
                wsRef.current = null;
            }
        };
    }, [cameraSource, isStopped, backendCameraActive, connectWS, stopBrowserCamera]); // Run on mount or state change

    // ── Render ─────────────────────────────────────────────
    return (
        <div className="glass-card p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-cyan/15 flex items-center justify-center">
                        <Eye size={14} className="text-cyan" />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-text-primary">YOLO v9 Detection Engine</h3>
                        <p className="text-[10px] text-text-muted">Real-time object detection & crowd counting</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 p-0.5 rounded-md bg-bg-primary/70 border border-border">
                        <button
                            onClick={() => switchToSource('backend')}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-bold transition-all ${cameraSource === 'backend'
                                ? 'bg-cyan/20 text-cyan border border-cyan/30'
                                : 'text-text-muted hover:text-text-secondary'
                                }`}
                        >
                            <Monitor size={10} /> SERVER
                        </button>
                        <button
                            onClick={() => switchToSource('browser')}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-bold transition-all ${cameraSource === 'browser'
                                ? 'bg-cyan text-bg-primary shadow-lg shadow-cyan/20'
                                : 'text-text-muted hover:text-text-secondary'
                                }`}
                        >
                            <Smartphone size={10} /> DEVICE
                        </button>
                    </div>

                    <button
                        onClick={() => isStopped ? switchToSource(cameraSource) : stopAll()}
                        className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all border ${isStopped
                            ? 'bg-success/15 text-success border-success/30 hover:bg-success/25'
                            : 'bg-danger/15 text-danger border-danger/30 hover:bg-danger/25'
                            }`}
                    >
                        <Power size={10} />
                        {isStopped ? 'Turn On' : 'Stop'}
                    </button>

                    <div className="flex items-center gap-1 text-[10px]">
                        {status === 'connected' ? (
                            <span className="flex items-center gap-1 text-success">
                                <Wifi size={12} /> {isDemoMode ? 'Demo' : 'Live'}
                            </span>
                        ) : (
                            <span className="flex items-center gap-1 text-danger">
                                <WifiOff size={12} /> {status}
                            </span>
                        )}
                        {metadata && <span className="font-mono text-text-muted">FPS: {metadata.fps}</span>}
                    </div>
                </div>
            </div>

            {/* Alerts */}
            {alert && (
                <div className={`mb-3 p-3 rounded-lg border flex items-start gap-2 text-xs ${alert.type === 'error'
                    ? 'bg-danger/10 border-danger/30 text-danger'
                    : alert.type === 'warning'
                        ? 'bg-warning/10 border-warning/30 text-warning'
                        : 'bg-cyan/10 border-cyan/30 text-cyan'
                    }`}>
                    <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                        <p className="font-semibold text-[11px] mb-0.5">{alert.title}</p>
                        <p className="text-[10px] opacity-90 whitespace-pre-line">{alert.message}</p>
                        {alert.action && alert.onAction && (
                            <button
                                onClick={alert.onAction}
                                className="mt-2 px-3 py-1 rounded-md text-[10px] font-medium bg-white/10 border border-current/20 hover:bg-white/20 transition-colors"
                            >
                                {alert.action}
                            </button>
                        )}
                    </div>
                    <button onClick={() => setAlert(null)} className="opacity-60 hover:opacity-100 px-1">✕</button>
                </div>
            )}

            {/* Video Area */}
            <div className="relative aspect-[16/9] bg-bg-primary rounded-lg border border-border overflow-hidden flex items-center justify-center">

                {cameraSource === 'backend' ? (
                    imageSrc ? (
                        <img src={imageSrc} alt="Live" className="w-full h-full object-contain" />
                    ) : (
                        <div className="text-center p-4">
                            <div className="animate-pulse mb-2"><Camera className="mx-auto text-text-muted" size={32} /></div>
                            <p className="text-xs text-text-muted">{isStopped ? 'Off' : 'Connecting...'}</p>
                        </div>
                    )
                ) : (
                    <video
                        ref={videoRef}
                        className="w-full h-full object-contain"
                        playsInline
                        muted
                        autoPlay
                        style={{ display: browserCamActive ? 'block' : 'none' }}
                    />
                )}

                {/* Overlays */}
                {isDemoMode && cameraSource === 'backend' && imageSrc && (
                    <div className="absolute top-2 left-2 px-2 py-0.5 rounded text-[9px] font-mono bg-warning/20 text-warning border border-warning/30">DEMO</div>
                )}
                {cameraSource === 'browser' && browserCamActive && (
                    <div className="absolute top-2 right-2 px-2 py-0.5 rounded text-[9px] font-mono bg-cyan/20 text-cyan border border-cyan/30 flex items-center gap-1">
                        <Camera size={8} /> DEVICE
                    </div>
                )}

                {/* Stats */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent py-2 px-3">
                    <div className="flex items-center justify-between text-[9px] text-white/90 font-mono">
                        <span>Model: YOLOv9-X | Latency: {metadata?.latency_ms ?? 0}ms</span>
                        <span>Objects: {metadata?.person_count ?? 0}</span>
                    </div>
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-5 gap-2 mt-3">
                {[
                    { label: 'Person Count', value: metadata?.person_count ?? 0 },
                    { label: 'Risk Score', value: (metadata?.risk_score ?? 0).toFixed(2) },
                    { label: 'Density', value: (metadata?.density ?? 0).toFixed(1) },
                    { label: 'Congestion', value: (metadata?.congestion ?? 0).toFixed(2) },
                    { label: 'Anomaly', value: (metadata?.anomaly ?? 0).toFixed(2) },
                ].map((s, i) => (
                    <div key={i} className="p-2 rounded-lg bg-bg-primary/50 border border-border text-center">
                        <div className="text-sm font-bold text-cyan">{s.value}</div>
                        <div className="text-[9px] text-text-muted">{s.label}</div>
                    </div>
                ))}
            </div>

            {/* Hidden canvas for capture */}
            <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
    );
}
