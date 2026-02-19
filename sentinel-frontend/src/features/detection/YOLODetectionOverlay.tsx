import { Eye, Wifi, WifiOff, Camera, AlertTriangle, Monitor, Smartphone, Power } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';

// WebSocket URLs
const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.host}`;
const WS_URL_SERVER = `${WS_BASE}/ws/live/cam_0`;
const WS_URL_BROWSER = `${WS_BASE}/ws/live/browser/cam_0?token=sentinel_demo_token`;

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
    // Extended pipeline data
    zones?: Array<{
        id: string;
        name: string;
        x: number;
        y: number;
        pressure: number;
        direction: number;
        risk: 'low' | 'medium' | 'high' | 'critical';
    }>;
    collision_points?: Array<{
        x: number;
        y: number;
        force: number;
        label: string;
    }>;
    flow_vectors?: Array<{
        x: number;
        y: number;
        angle: number;
        magnitude: number;
    }>;
    avg_pressure?: number;
    max_force?: number;
    flow_stability?: number;
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
    
    // Browser camera processed frame (from backend with YOLO boxes)
    const [browserProcessedFrame, setBrowserProcessedFrame] = useState<string | null>(null);

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

    // ── Frame Capture for Browser Mode ─────────────────────
    const startFrameCapture = useCallback((ws: WebSocket) => {
        if (captureIntervalRef.current) {
            clearInterval(captureIntervalRef.current);
        }
        
        const captureAndSend = () => {
            if (!videoRef.current || !canvasRef.current || ws.readyState !== WebSocket.OPEN) return;
            
            const video = videoRef.current;
            const canvas = canvasRef.current;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;
            
            // Set canvas size to match video
            canvas.width = 640;
            canvas.height = 480;
            
            // Draw video frame to canvas
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Convert to base64 JPEG
            const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
            const base64 = dataUrl.split(',')[1];
            
            // Send to backend
            ws.send(JSON.stringify({
                type: 'browser_frame',
                frame_b64: base64,
                timestamp: Date.now()
            }));
        };
        
        // Capture at ~15 FPS
        captureIntervalRef.current = window.setInterval(captureAndSend, 66);
    }, []);

    // ── Unified WebSocket Connection Logic ─────────────────
    const connectWS = useCallback((forBrowser: boolean = false) => {
        console.log('[YOLO] connectWS called', { forBrowser, isStopped, backendCameraActive, isDestroyed: isDestroyedRef.current });
        
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

        if (isDestroyedRef.current || isStopped) {
            console.log('[YOLO] Connection blocked: destroyed or stopped');
            return;
        }
        if (!forBrowser && !backendCameraActive) {
            console.log('[YOLO] Connection blocked: backend camera not active');
            return;
        }

        setStatus('connecting');

        const wsUrl = forBrowser ? WS_URL_BROWSER : WS_URL_SERVER;
        console.log('[YOLO] Connecting to:', wsUrl);

        connectTimeoutRef.current = window.setTimeout(() => {
            if (isDestroyedRef.current || isStopped) return;
            if (!forBrowser && !backendCameraActive) return;

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[YOLO] WebSocket OPEN');
                if (isDestroyedRef.current) {
                    ws.close();
                    return;
                }
                setStatus('connected');
                setAlert(null);
                
                // Start frame capture loop for browser mode
                if (forBrowser && videoRef.current && canvasRef.current) {
                    startFrameCapture(ws);
                }
            };

            ws.onmessage = (event) => {
                if (isDestroyedRef.current) return;
                try {
                    if (event.data === 'pong') return;
                    const data = JSON.parse(event.data);

                    if (data.type === 'frame') {
                        if (data.frame_b64) {
                            if (forBrowser) {
                                // Browser mode: show processed frame from backend
                                setBrowserProcessedFrame(`data:image/jpeg;base64,${data.frame_b64}`);
                            } else {
                                // Server mode
                                setImageSrc(`data:image/jpeg;base64,${data.frame_b64}`);
                            }
                        }
                        setMetadata(data.metadata);
                        setIsDemoMode(data.demo_mode ?? false);
                        
                        // Extract and store pipeline visualization data
                        const meta = data.metadata;
                        if (meta?.zones || meta?.collision_points || meta?.flow_vectors) {
                            useDashboardStore.getState().setPipelineData({
                                zones: meta.zones || [],
                                collisionPoints: meta.collision_points || [],
                                flowVectors: meta.flow_vectors || [],
                                avgPressure: meta.avg_pressure || 0,
                                maxForce: meta.max_force || 0,
                                flowStability: meta.flow_stability || 0,
                            });
                        }
                        
                        // Extract and store behaviour analytics data
                        if (meta?.behaviour_data) {
                            useDashboardStore.getState().setBehaviourData({
                                trackedEntities: meta.behaviour_data.tracked_entities || 0,
                                behaviourEvents: meta.behaviour_data.behaviour_events || 0,
                                anomaliesToday: meta.behaviour_data.anomalies_today || 0,
                                aiConfidence: meta.behaviour_data.ai_confidence || 0,
                                behaviourTypes: meta.behaviour_data.behaviour_types || [],
                                radarData: meta.behaviour_data.radar_data || [],
                                timelineData: meta.behaviour_data.timeline_data || [],
                            });
                        }
                    }
                } catch (e) {
                    // ignore
                }
            };

            ws.onclose = (event) => {
                console.log('[YOLO] WebSocket CLOSE', event.code, event.reason);
                if (isDestroyedRef.current) return;
                setStatus('disconnected');
                if (!isStopped) {
                    const shouldReconnect = forBrowser ? browserCamActive : (cameraSource === 'backend' && backendCameraActive);
                    if (shouldReconnect) {
                        reconnectTimeoutRef.current = window.setTimeout(() => connectWS(forBrowser), 3000);
                    }
                }
            };

            ws.onerror = (error) => {
                console.error('[YOLO] WebSocket ERROR', error);
                if (isDestroyedRef.current) return;
            };

        }, 0);
    }, [cameraSource, isStopped, backendCameraActive, browserCamActive, startFrameCapture]);

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
        setBrowserProcessedFrame(null);
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
        // Stop everything first
        stopBrowserCamera();
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        
        // Clear frames
        setImageSrc(null);
        setBrowserProcessedFrame(null);
        setStatus('connecting');
        
        setCameraSource(source);
        setIsStopped(false);
        
        if (source === 'browser') {
            // Start browser camera then connect to backend for YOLO
            const perm = await checkCameraPermission();
            if (perm === 'granted' || perm === 'prompt') {
                await startBrowserCamera();
                // Small delay to ensure video is ready
                setTimeout(() => connectWS(true), 500);
            } else {
                setAlert({ type: 'error', title: 'Permission Issue', message: 'Camera permission denied.' });
            }
        } else {
            // SERVER mode - connect to backend camera
            connectWS(false);
        }
    }, [checkCameraPermission, startBrowserCamera, stopBrowserCamera, connectWS]);

    // ── Auto-Fallback Logic (disabled - causes confusion) ────
    // useEffect(() => {
    //     if (!backendCameraActive && cameraSource === 'backend' && !isStopped) {
    //         switchToSource('browser');
    //     }
    // }, [backendCameraActive, cameraSource, isStopped, switchToSource]);

    const stopAll = useCallback(() => {
        stopBrowserCamera();

        setIsStopped(true);
        setStatus('disconnected');
        setImageSrc(null);
        setBrowserProcessedFrame(null);

        if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, [stopBrowserCamera]);

    // ── Lifecycle: Connect on mount or when backendCameraActive changes ────
    useEffect(() => {
        isDestroyedRef.current = false;

        // Auto-connect to SERVER mode if backend camera is active and in backend mode
        if (backendCameraActive && cameraSource === 'backend' && !isStopped) {
            console.log('[YOLO] Auto-connecting to backend WebSocket...');
            connectWS(false);
        }

        return () => {
            isDestroyedRef.current = true;

            if (connectTimeoutRef.current) clearTimeout(connectTimeoutRef.current);
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

            stopBrowserCamera();

            if (wsRef.current) {
                const ws = wsRef.current;
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
    }, [backendCameraActive, cameraSource, isStopped, connectWS, stopBrowserCamera]);

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
                    <>
                        {/* Hidden video element for frame capture */}
                        <video
                            ref={videoRef}
                            className="absolute opacity-0 pointer-events-none"
                            playsInline
                            muted
                            autoPlay
                            width={640}
                            height={480}
                        />
                        
                        {/* Show processed frame with YOLO detection boxes */}
                        {browserProcessedFrame ? (
                            <img src={browserProcessedFrame} alt="Live Detection" className="w-full h-full object-contain" />
                        ) : browserCamActive ? (
                            <div className="text-center p-4">
                                <div className="animate-pulse mb-2"><Camera className="mx-auto text-cyan" size={32} /></div>
                                <p className="text-xs text-cyan">Processing with YOLO...</p>
                            </div>
                        ) : (
                            <div className="text-center p-4">
                                <div className="animate-pulse mb-2"><Camera className="mx-auto text-text-muted" size={32} /></div>
                                <p className="text-xs text-text-muted">{isStopped ? 'Off' : 'Starting camera...'}</p>
                            </div>
                        )}
                    </>
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
