import { Eye, Wifi, WifiOff, Camera, AlertTriangle, Monitor, Smartphone, Play, Pause, Square } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';

// WebSocket URLs
const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`;
const WS_URL = `${WS_BASE}/ws/stream/cam_0`;

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
    pressure?: number;
    collisions?: Array<{ x: number, y: number, force: number, label: string }>;
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

    // ── Device Detection ──────────────────────────────────
    const [isMobile] = useState(() => /iPhone|iPad|iPod|Android/i.test(navigator.userAgent));

    // Stream state
    const [imageSrc, setImageSrc] = useState<string | null>(null);
    const [metadata, setMetadata] = useState<StreamMetadata | null>(null);
    const setLiveMetrics = useDashboardStore((s) => s.setLiveMetrics);
    const [status, setStatus] = useState<ConnectionStatus>('connecting');
    const [isDemoMode, setIsDemoMode] = useState(false);

    // Camera source state: Default to BACKEND (Server)
    const [cameraSource, setCameraSource] = useState<CameraSource>('backend');
    const [isStopped, setIsStopped] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const [alert, setAlert] = useState<CameraAlert | null>(null);

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
        setImageSrc(null); // Reset image when switching

        connectTimeoutRef.current = window.setTimeout(() => {
            if (isDestroyedRef.current || isStopped) return;

            // Select endpoint based on source
            const url = cameraSource === 'browser'
                ? `${WS_BASE}/ws/live/browser/cam_0?token=sentinel_demo_token`
                : WS_URL;

            const ws = new WebSocket(url);
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
                        if (isPaused) return; // Skip updates if paused

                        if (data.frame_b64) {
                            setImageSrc(`data:image/jpeg;base64,${data.frame_b64}`);
                        }
                        if (data.metadata) {
                            setMetadata(data.metadata);
                            setLiveMetrics({
                                fps: data.metadata.fps,
                                latencyMs: data.metadata.latency_ms,
                                personCount: data.metadata.person_count,
                                riskScore: data.metadata.risk_score,
                                riskLevel: data.metadata.risk_level,
                                density: data.metadata.density,
                                congestion: data.metadata.congestion,
                                anomaly: data.metadata.anomaly,
                                flowMagnitude: data.metadata.flow_magnitude,
                                trackCount: data.metadata.tracks,
                                pressure: data.metadata.pressure,
                                collisions: data.metadata.collisions,
                            });
                        }
                        setIsDemoMode(data.demo_mode ?? false);
                    }
                } catch (e) {
                    // ignore
                }
            };

            ws.onclose = () => {
                if (isDestroyedRef.current) return;
                setStatus('disconnected');
                if (!isStopped && (cameraSource === 'backend' ? backendCameraActive : true)) {
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
            setAlert(null);

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();

                // Start capture loop
                let lastCapture = 0;
                captureIntervalRef.current = window.setInterval(() => {
                    if (!videoRef.current || !canvasRef.current || !wsRef.current) return;
                    if (wsRef.current.readyState !== WebSocket.OPEN) return;

                    const now = Date.now();
                    if (now - lastCapture < 100) return; // Cap at 10 FPS for browser transmission
                    lastCapture = now;

                    const canvas = canvasRef.current;
                    const video = videoRef.current;
                    const context = canvas.getContext('2d');
                    if (!context) return;

                    canvas.width = 640;
                    canvas.height = 480;
                    context.drawImage(video, 0, 0, 640, 480);

                    const frameBase64 = canvas.toDataURL('image/jpeg', 0.6).split(',')[1];
                    wsRef.current.send(JSON.stringify({
                        type: 'browser_frame',
                        frame_b64: frameBase64
                    }));
                }, 50);
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
            if (isMobile) {
                // On mobile: become the sensor (PUBLISH)
                const perm = await checkCameraPermission();
                if (perm === 'granted' || perm === 'prompt') {
                    setCameraSource(source);
                    setIsStopped(false);
                    startBrowserCamera();
                } else {
                    setAlert({ type: 'error', title: 'Permission Issue', message: 'Camera permission denied.' });
                }
            } else {
                // On laptop: become the dashboard for mobile (SUBSCRIBE)
                stopBrowserCamera();
                setCameraSource(source);
                setIsStopped(false);
                connectWS();
            }
        } else {
            // BACKEND / SERVER mode
            stopBrowserCamera();
            setCameraSource(source);
            setIsStopped(false);
            connectWS();
        }
    }, [checkCameraPermission, startBrowserCamera, stopBrowserCamera, connectWS, isMobile]);

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
        if (!isStopped && (cameraSource === 'backend' ? backendCameraActive : true)) {
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
                            <Monitor size={10} /> LAPTOP AI
                        </button>
                        <button
                            onClick={() => switchToSource('browser')}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-bold transition-all ${cameraSource === 'browser'
                                ? 'bg-cyan text-bg-primary shadow-lg shadow-cyan/20'
                                : 'text-text-muted hover:text-text-secondary'
                                }`}
                        >
                            <Smartphone size={10} /> MOBILE SENSOR
                        </button>
                    </div>

                    <div className="flex items-center gap-1 bg-bg-primary/50 p-1 rounded-md border border-border">
                        <button
                            onClick={() => {
                                if (isStopped) {
                                    switchToSource(cameraSource);
                                } else {
                                    setIsStopped(false);
                                    setIsPaused(false);
                                }
                            }}
                            className={`p-1.5 rounded transition-all ${!isStopped && !isPaused ? 'bg-success text-bg-primary' : 'text-success hover:bg-success/10'}`}
                            title="Start"
                        >
                            <Play size={10} fill={!isStopped && !isPaused ? 'currentColor' : 'none'} />
                        </button>
                        <button
                            onClick={() => setIsPaused(!isPaused)}
                            disabled={isStopped}
                            className={`p-1.5 rounded transition-all ${isPaused ? 'bg-warning text-bg-primary' : 'text-warning hover:bg-warning/10 disabled:opacity-30'}`}
                            title="Pause"
                        >
                            <Pause size={10} fill={isPaused ? 'currentColor' : 'none'} />
                        </button>
                        <button
                            onClick={() => stopAll()}
                            className={`p-1.5 rounded transition-all ${isStopped ? 'bg-danger text-bg-primary' : 'text-danger hover:bg-danger/10'}`}
                            title="Stop"
                        >
                            <Square size={10} fill={isStopped ? 'currentColor' : 'none'} />
                        </button>
                    </div>

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
                    <>
                        {/* Processed Frame Overlay */}
                        {imageSrc && (
                            <img
                                src={imageSrc}
                                alt="Processed"
                                className="absolute inset-0 w-full h-full object-contain z-10"
                            />
                        )}
                        {/* Hidden Source Video */}
                        <video
                            ref={videoRef}
                            className="w-full h-full object-contain"
                            playsInline
                            muted
                            autoPlay
                            style={{ opacity: imageSrc ? 0 : 1 }}
                        />
                    </>
                )}

                {/* Overlays */}
                {isDemoMode && cameraSource === 'backend' && imageSrc && (
                    <div className="absolute top-2 left-2 px-2 py-0.5 rounded text-[9px] font-mono bg-warning/20 text-warning border border-warning/30">DEMO</div>
                )}
                {cameraSource === 'browser' && (
                    <div className="absolute top-2 right-2 px-2 py-0.5 rounded text-[9px] font-mono bg-cyan/20 text-cyan border border-cyan/30 flex items-center gap-1">
                        <Camera size={8} /> {isMobile ? 'DEVICE (SENSING)' : 'REMOTE MOBILE SENSOR'}
                    </div>
                )}

                {/* Stats */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent py-2 px-3">
                    <div className="flex items-center justify-between text-[9px] text-white/90 font-mono">
                        <span>Model: YOLOv9-X | Latency: {metadata?.latency_ms ?? 0}ms</span>
                        <span>Objects: {metadata?.person_count ?? 0}</span>
                    </div>
                </div>

                {/* Live Collision Markers */}
                {metadata?.collisions?.map((cp, idx) => (
                    <div
                        key={idx}
                        className="absolute flex flex-col items-center pointer-events-none"
                        style={{ left: `${(cp.x / 640) * 100}%`, top: `${(cp.y / 480) * 100}%`, transform: 'translate(-50%, -50%)' }}
                    >
                        <div className="w-5 h-5 rounded-full border-2 border-danger/60 flex items-center justify-center bg-danger/10 animate-pulse">
                            <AlertTriangle size={8} className="text-danger" />
                        </div>
                        <span className="text-[8px] text-danger font-mono mt-0.5">{cp.label}: {cp.force}N</span>
                    </div>
                ))}
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-5 gap-2 mt-3">
                {[
                    { label: 'Person Count', value: metadata?.person_count ?? 0 },
                    { label: 'Risk Score', value: (metadata?.risk_score ?? 0).toFixed(2) },
                    { label: 'Density', value: (metadata?.density ?? 0).toFixed(1) },
                    { label: 'Congestion', value: (metadata?.congestion ?? 0).toFixed(2) },
                    { label: 'Pressure', value: (metadata?.pressure ?? 0).toFixed(2) + ' MPa' },
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
