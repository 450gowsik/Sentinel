import { Scan, Radio, Wifi, WifiOff, Settings, X, Save } from 'lucide-react';
import { useDashboardStore } from '../store/useDashboardStore';
import { useState } from 'react';
import { streamApi } from '../services/api';

export default function LiveFeedContainer() {
    const liveFrame = useDashboardStore((s) => s.liveFrame);
    const backendConnected = useDashboardStore((s) => s.backendConnected);
    const liveMetrics = useDashboardStore((s) => s.liveMetrics);

    const [showConfig, setShowConfig] = useState(false);
    const [cameraUrl, setCameraUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const handleSaveConfig = async () => {
        if (!cameraUrl) return;
        setIsSaving(true);
        try {
            await streamApi.configure(cameraUrl);
            setShowConfig(false);
            setCameraUrl('');
        } catch (error) {
            console.error('Failed to update camera source:', error);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="glass-card overflow-hidden relative group">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
                <div className="flex items-center gap-2">
                    <Radio size={14} className="text-danger pulse-dot" />
                    <span className="text-xs font-semibold text-text-primary tracking-wide">LIVE AI FEED</span>
                    <span className="text-[10px] text-text-muted">— Camera 01 Main Gate</span>
                </div>
                <div className="flex items-center gap-2">
                    {/* Connection status */}
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider flex items-center gap-1 ${backendConnected
                        ? 'bg-success/15 text-success'
                        : 'bg-warning/15 text-warning'
                        }`}>
                        {backendConnected ? (
                            <><Wifi size={10} /> LIVE</>
                        ) : (
                            <><WifiOff size={10} /> SIMULATED</>
                        )}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-danger/15 text-danger font-bold tracking-wider">
                        ● REC
                    </span>
                    <button
                        onClick={() => setShowConfig(true)}
                        className="p-1 hover:bg-white/10 rounded transition-colors"
                        title="Configure Camera Source"
                    >
                        <Settings size={14} className="text-text-muted hover:text-text-primary" />
                    </button>
                    <Scan size={14} className="text-text-muted" />
                </div>
            </div>

            {/* Video Container */}
            <div className="relative aspect-video bg-bg-primary flex items-center justify-center">
                {liveFrame ? (
                    /* ── Real backend frame ──────────────── */
                    <img
                        src={liveFrame}
                        alt="Live AI Feed"
                        className="w-full h-full object-contain"
                        style={{ imageRendering: 'auto' }}
                    />
                ) : (
                    /* ── Simulated placeholder ───────────── */
                    <>
                        {/* Grid Overlay */}
                        <div className="absolute inset-0 opacity-10"
                            style={{
                                backgroundImage: `
                                    linear-gradient(rgba(0,229,255,0.3) 1px, transparent 1px),
                                    linear-gradient(90deg, rgba(0,229,255,0.3) 1px, transparent 1px)
                                `,
                                backgroundSize: '40px 40px',
                            }}
                        />

                        {/* Simulated Heatmap Overlay */}
                        <div className="absolute inset-0">
                            <div className="absolute top-[20%] left-[30%] w-32 h-32 rounded-full opacity-30"
                                style={{ background: 'radial-gradient(circle, rgba(255,61,0,0.6), transparent 70%)' }}
                            />
                            <div className="absolute top-[40%] left-[55%] w-40 h-40 rounded-full opacity-25"
                                style={{ background: 'radial-gradient(circle, rgba(255,179,0,0.5), transparent 70%)' }}
                            />
                            <div className="absolute top-[55%] left-[15%] w-28 h-28 rounded-full opacity-20"
                                style={{ background: 'radial-gradient(circle, rgba(0,200,83,0.5), transparent 70%)' }}
                            />
                            <div className="absolute top-[30%] left-[70%] w-24 h-24 rounded-full opacity-35"
                                style={{ background: 'radial-gradient(circle, rgba(255,61,0,0.7), transparent 70%)' }}
                            />
                        </div>

                        {/* Simulated AI Bounding Boxes */}
                        <div className="absolute top-[25%] left-[28%] w-16 h-20 border border-cyan/60 rounded-sm">
                            <span className="absolute -top-4 left-0 text-[9px] bg-cyan/20 text-cyan px-1 rounded font-mono">ID-042 96%</span>
                        </div>
                        <div className="absolute top-[35%] left-[50%] w-14 h-18 border border-warning/60 rounded-sm">
                            <span className="absolute -top-4 left-0 text-[9px] bg-warning/20 text-warning px-1 rounded font-mono">ID-087 89%</span>
                        </div>
                        <div className="absolute top-[45%] left-[68%] w-12 h-16 border border-danger/60 rounded-sm">
                            <span className="absolute -top-4 left-0 text-[9px] bg-danger/20 text-danger px-1 rounded font-mono">ID-103 78%</span>
                        </div>

                        {/* Scan Line Animation */}
                        <div className="absolute inset-0 overflow-hidden pointer-events-none">
                            <div
                                className="w-full h-px bg-gradient-to-r from-transparent via-cyan/40 to-transparent"
                                style={{ animation: 'scanLine 4s linear infinite' }}
                            />
                        </div>

                        {/* Corner Markers */}
                        <div className="absolute top-3 left-3 w-6 h-6 border-t-2 border-l-2 border-cyan/50" />
                        <div className="absolute top-3 right-3 w-6 h-6 border-t-2 border-r-2 border-cyan/50" />
                        <div className="absolute bottom-3 left-3 w-6 h-6 border-b-2 border-l-2 border-cyan/50" />
                        <div className="absolute bottom-3 right-3 w-6 h-6 border-b-2 border-r-2 border-cyan/50" />
                    </>
                )}

                {/* Bottom Stats Bar */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-bg-primary/90 to-transparent py-3 px-4">
                    <div className="flex items-center justify-between text-[10px] text-text-muted">
                        {liveMetrics ? (
                            <>
                                <span>FPS: {liveMetrics.fps.toFixed(1)} | Latency: {liveMetrics.latencyMs.toFixed(0)}ms</span>
                                <span>Persons: {liveMetrics.personCount} | Tracks: {liveMetrics.trackCount}</span>
                                <span className={`font-bold ${liveMetrics.riskLevel === 'CRITICAL' ? 'text-danger' :
                                    liveMetrics.riskLevel === 'HIGH' ? 'text-warning' : 'text-success'
                                    }`}>
                                    Risk: {liveMetrics.riskLevel} ({(liveMetrics.riskScore * 100).toFixed(0)}%)
                                </span>
                            </>
                        ) : (
                            <>
                                <span>FPS: 30 | Res: 1920×1080</span>
                                <span>Objects: 47 | Density: 4.2 p/m²</span>
                                <span>AI Model: YOLOv8n-TRT</span>
                            </>
                        )}
                    </div>
                </div>

                {/* Configuration Modal */}
                {showConfig && (
                    <div className="absolute inset-0 bg-bg-primary/95 backdrop-blur-sm z-50 flex items-center justify-center p-6">
                        <div className="w-full max-w-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
                                    <Settings size={14} className="text-brand-primary" />
                                    Camera Source
                                </h3>
                                <button
                                    onClick={() => setShowConfig(false)}
                                    className="text-text-muted hover:text-text-primary"
                                >
                                    <X size={14} />
                                </button>
                            </div>

                            <div className="space-y-3">
                                <div>
                                    <label className="block text-[10px] text-text-muted uppercase tracking-wider font-bold mb-1.5">
                                        RTSP / HTTP Stream URL
                                    </label>
                                    <input
                                        type="text"
                                        value={cameraUrl}
                                        onChange={(e) => setCameraUrl(e.target.value)}
                                        placeholder="e.g. http://192.168.1.5:8080/video"
                                        className="w-full bg-bg-secondary border border-border rounded px-3 py-2 text-xs text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-brand-primary/50 transition-colors"
                                    />
                                    <p className="text-[10px] text-text-muted mt-1.5 leading-relaxed">
                                        For mobile: Use "IP Webcam" app (Android) and enter the video URL (usually ends in /video).
                                    </p>
                                </div>
                                <div className="flex gap-2 pt-2">
                                    <button
                                        onClick={() => setCameraUrl('0')}
                                        className="flex-1 bg-bg-secondary hover:bg-white/5 border border-border text-text-muted hover:text-text-primary text-xs py-2 rounded transition-colors"
                                    >
                                        Reset to Default
                                    </button>
                                    <button
                                        onClick={handleSaveConfig}
                                        disabled={!cameraUrl || isSaving}
                                        className="flex-1 bg-brand-primary hover:bg-brand-primary/90 text-bg-primary font-bold text-xs py-2 rounded transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {isSaving ? 'Connecting...' : <><Save size={12} /> Connect Stream</>}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <style>{`
                @keyframes scanLine {
                    0% { transform: translateY(0); }
                    100% { transform: translateY(400px); }
                }
            `}</style>
        </div>
    );
}
