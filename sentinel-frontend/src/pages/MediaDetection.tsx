import { useState, useCallback, useRef } from 'react';
import { ScanSearch, Upload, X, Image, Video, AlertTriangle, Users, Shield, Gauge, Activity, Zap, Eye, Layers, Camera, Plane } from 'lucide-react';
import { detectApi } from '../services/api';
import type { DetectionMode } from '../services/api';

interface Detection {
    x1: number; y1: number; x2: number; y2: number;
    confidence: number;
    class_name: string;
}

interface DetectionResult {
    frame_idx: number;
    person_count: number;
    detections: Detection[];
    density_estimate: number;
    risk_score: number;
    risk_level: string;
    anomaly_score: number;
    stampede_risk: number;
    flow_rate: number;
    congestion_zones: { zone: string; count: number; congestion: number }[];
    annotated_image_b64: string;
    heatmap_b64: string;
    inference_time_ms: number;
    saved_path?: string;
    detection_mode?: string;
}

interface VideoResult {
    total_frames: number;
    processed_frames: number;
    avg_person_count: number;
    max_person_count: number;
    avg_risk_score: number;
    peak_risk_score: number;
    peak_risk_level: string;
    frames: DetectionResult[];
    processing_time_ms: number;
    saved_path?: string;
    detection_mode?: string;
}

type ViewMode = 'annotated' | 'heatmap' | 'original';

export default function MediaDetection() {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [result, setResult] = useState<DetectionResult | null>(null);
    const [videoResult, setVideoResult] = useState<VideoResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('annotated');
    const [activeFrame, setActiveFrame] = useState(0);
    const [dragActive, setDragActive] = useState(false);
    const [detectionMode, setDetectionMode] = useState<DetectionMode>('auto');
    const fileRef = useRef<HTMLInputElement>(null);

    const isVideo = file?.type.startsWith('video/') || file?.name.match(/\.(mp4|avi|mov|webm)$/i);

    const handleFile = useCallback((f: File) => {
        setFile(f);
        setResult(null);
        setVideoResult(null);
        setError(null);
        setActiveFrame(0);

        if (f.type.startsWith('image/')) {
            const url = URL.createObjectURL(f);
            setPreview(url);
        } else {
            setPreview(null);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragActive(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
    }, [handleFile]);

    const runDetection = useCallback(async () => {
        if (!file) return;
        setLoading(true);
        setError(null);

        try {
            const res = await detectApi.uploadFile(file, detectionMode);
            const data = res as any;

            if (data.frames) {
                // Video result
                setVideoResult(data);
                setResult(data.frames[0] || null);
            } else {
                // Image result
                setResult(data);
                setVideoResult(null);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Detection failed');
        } finally {
            setLoading(false);
        }
    }, [file, detectionMode]);

    const clearFile = () => {
        setFile(null);
        setPreview(null);
        setResult(null);
        setVideoResult(null);
        setError(null);
    };

    const currentResult = videoResult ? videoResult.frames[activeFrame] : result;

    const riskColor = (level: string) => {
        switch (level) {
            case 'CRITICAL': return '#FF3D00';
            case 'HIGH': return '#FF6D00';
            case 'MEDIUM': return '#FFB300';
            default: return '#00C853';
        }
    };

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-purple/15 flex items-center justify-center">
                        <ScanSearch size={18} className="text-purple" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Upload Detection</h2>
                        <p className="text-xs text-text-muted">Analyse images & videos with YOLOv8n AI detection pipeline</p>
                    </div>
                </div>
                
                {/* Detection Mode Selector + File Info */}
                <div className="flex items-center gap-4">
                    {/* Detection Mode Selector */}
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-text-muted uppercase tracking-wider">Mode:</span>
                        <div className="flex items-center rounded-lg bg-bg-primary border border-border overflow-hidden">
                            <button
                                onClick={() => setDetectionMode('auto')}
                                className={`px-3 py-1.5 text-[11px] font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                                    detectionMode === 'auto' 
                                        ? 'bg-cyan/20 text-cyan border-r border-cyan/30' 
                                        : 'text-text-muted hover:text-text-secondary border-r border-border'
                                }`}
                            >
                                <Zap size={12} />
                                Auto
                            </button>
                            <button
                                onClick={() => setDetectionMode('cctv')}
                                className={`px-3 py-1.5 text-[11px] font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                                    detectionMode === 'cctv' 
                                        ? 'bg-success/20 text-success border-r border-success/30' 
                                        : 'text-text-muted hover:text-text-secondary border-r border-border'
                                }`}
                            >
                                <Camera size={12} />
                                CCTV
                            </button>
                            <button
                                onClick={() => setDetectionMode('drone')}
                                className={`px-3 py-1.5 text-[11px] font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                                    detectionMode === 'drone' 
                                        ? 'bg-purple/20 text-purple' 
                                        : 'text-text-muted hover:text-text-secondary'
                                }`}
                            >
                                <Plane size={12} />
                                Drone
                            </button>
                        </div>
                    </div>
                    
                    {file && (
                        <div className="flex items-center gap-2">
                            <span className="text-[11px] text-text-muted font-mono">{file.name}</span>
                            <button onClick={clearFile} className="w-7 h-7 rounded-lg bg-danger/10 flex items-center justify-center text-danger hover:bg-danger/20 transition-colors cursor-pointer">
                                <X size={14} />
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Saved Path Notification */}
            {(result?.saved_path || videoResult?.saved_path) && (
                <div className="mx-1 px-3 py-2 rounded-lg bg-success/10 border border-success/20 flex items-center gap-2 text-xs text-success shrink-0 animate-fade-in">
                    <div className="w-4 h-4 rounded-full bg-success/20 flex items-center justify-center">
                        <ScanSearch size={10} />
                    </div>
                    <span>Result saved to server:</span>
                    <code className="px-1.5 py-0.5 rounded bg-bg-primary border border-success/20 font-mono text-[10px] select-all">
                        {videoResult?.saved_path || result?.saved_path}
                    </code>
                </div>
            )}

            {/* Main Content */}
            <div className="flex gap-4 flex-1 min-h-0">
                {/* Left — Upload Zone / Detection View */}
                <div className="flex-1 flex flex-col gap-3">
                    {!file ? (
                        /* ── Upload Zone ──────────────── */
                        <div
                            className={`flex-1 glass-card border-2 border-dashed flex flex-col items-center justify-center gap-4 transition-all duration-300 cursor-pointer ${dragActive ? 'border-cyan bg-cyan/5 scale-[1.01]' : 'border-border hover:border-cyan/40 hover:bg-bg-card-hover'
                                }`}
                            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                            onDragLeave={() => setDragActive(false)}
                            onDrop={handleDrop}
                            onClick={() => fileRef.current?.click()}
                        >
                            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan/20 to-purple/20 flex items-center justify-center">
                                <Upload size={32} className="text-cyan" />
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-semibold text-text-primary mb-1">
                                    Drop image or video here
                                </p>
                                <p className="text-xs text-text-muted">
                                    or <span className="text-cyan font-medium">click to browse</span>
                                </p>
                            </div>
                            <div className="flex items-center gap-3 text-[10px] text-text-muted">
                                <span className="flex items-center gap-1"><Image size={10} /> JPG, PNG, WebP</span>
                                <span className="text-border">|</span>
                                <span className="flex items-center gap-1"><Video size={10} /> MP4, AVI, MOV</span>
                                <span className="text-border">|</span>
                                <span>Max 100 MB</span>
                            </div>
                            <input
                                ref={fileRef}
                                type="file"
                                accept="image/*,video/*"
                                className="hidden"
                                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                            />
                        </div>
                    ) : (
                        /* ── Detection View ──────────────── */
                        <>
                            {/* View Mode Tabs */}
                            {currentResult && (
                                <div className="flex items-center gap-1 shrink-0">
                                    {([
                                        { id: 'annotated' as ViewMode, label: 'AI Detection', icon: Eye },
                                        { id: 'heatmap' as ViewMode, label: 'Density Heatmap', icon: Layers },
                                        { id: 'original' as ViewMode, label: 'Original', icon: Image },
                                    ]).map(({ id, label, icon: TabIcon }) => (
                                        <button
                                            key={id}
                                            onClick={() => setViewMode(id)}
                                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-colors cursor-pointer ${viewMode === id
                                                ? 'bg-cyan/10 text-cyan border border-cyan/20'
                                                : 'text-text-muted hover:text-text-secondary'
                                                }`}
                                        >
                                            <TabIcon size={12} />
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* Image/Result Display */}
                            <div className="glass-card relative overflow-hidden flex-1">
                                <div className="relative aspect-video bg-bg-primary flex items-center justify-center">
                                    {loading ? (
                                        <div className="flex flex-col items-center gap-3">
                                            <div className="w-12 h-12 rounded-full border-2 border-cyan/30 border-t-cyan animate-spin" />
                                            <p className="text-sm text-text-secondary font-medium">Running YOLOv8n Detection Pipeline...</p>
                                            <p className="text-[10px] text-text-muted">{isVideo ? 'Processing video frames...' : 'Analysing image...'}</p>
                                        </div>
                                    ) : currentResult ? (
                                        <img
                                            src={`data:image/jpeg;base64,${viewMode === 'heatmap' ? currentResult.heatmap_b64 :
                                                viewMode === 'annotated' ? currentResult.annotated_image_b64 :
                                                    preview || currentResult.annotated_image_b64
                                                }`}
                                            alt={viewMode === 'heatmap' ? 'Density Heatmap' : viewMode === 'annotated' ? 'AI Detection' : 'Original'}
                                            className="w-full h-full object-contain"
                                        />
                                    ) : preview ? (
                                        <img src={preview} alt="Preview" className="w-full h-full object-contain" />
                                    ) : (
                                        <div className="flex flex-col items-center gap-2">
                                            <Video size={32} className="text-text-muted" />
                                            <p className="text-xs text-text-muted">Video preview after detection</p>
                                        </div>
                                    )}

                                    {/* Top-left status overlay */}
                                    {currentResult && (
                                        <div className="absolute top-3 left-3 flex items-center gap-2">
                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-bg-primary/80 border border-border text-text-secondary font-mono backdrop-blur-sm">
                                                {currentResult.inference_time_ms.toFixed(0)}ms
                                            </span>
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider`}
                                                style={{ backgroundColor: `${riskColor(currentResult.risk_level)}20`, color: riskColor(currentResult.risk_level) }}
                                            >
                                                {currentResult.risk_level}
                                            </span>
                                            {/* Detection Mode Badge */}
                                            {currentResult.detection_mode && (
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider flex items-center gap-1 ${
                                                    currentResult.detection_mode === 'drone' 
                                                        ? 'bg-purple/20 text-purple' 
                                                        : 'bg-success/20 text-success'
                                                }`}>
                                                    {currentResult.detection_mode === 'drone' ? <Plane size={10} /> : <Camera size={10} />}
                                                    {currentResult.detection_mode.toUpperCase()}
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* Bottom stats bar */}
                                    {currentResult && (
                                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-bg-primary/90 to-transparent py-2.5 px-4">
                                            <div className="flex items-center justify-between text-[10px] text-text-muted font-mono">
                                                <span>Mode: {(currentResult.detection_mode || 'cctv').toUpperCase()} | Model: YOLOv8n | {currentResult.inference_time_ms.toFixed(0)}ms</span>
                                                <span>Detections: {currentResult.detections.length} | Persons: {currentResult.person_count}</span>
                                                <span style={{ color: riskColor(currentResult.risk_level) }}>Risk: {currentResult.risk_level} ({(currentResult.risk_score * 100).toFixed(0)}%)</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Video Frame Slider */}
                            {videoResult && videoResult.frames.length > 1 && (
                                <div className="glass-card p-3 shrink-0">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-[11px] text-text-secondary font-medium">Frame Timeline</span>
                                        <span className="text-[10px] text-text-muted font-mono">
                                            Frame {activeFrame + 1} / {videoResult.frames.length}
                                        </span>
                                    </div>
                                    <input
                                        type="range"
                                        min={0}
                                        max={videoResult.frames.length - 1}
                                        value={activeFrame}
                                        onChange={(e) => {
                                            const idx = parseInt(e.target.value);
                                            setActiveFrame(idx);
                                            setResult(videoResult.frames[idx]);
                                        }}
                                        className="w-full accent-cyan h-1"
                                    />
                                    <div className="flex gap-1 mt-2 overflow-x-auto">
                                        {videoResult.frames.map((f, i) => (
                                            <button
                                                key={i}
                                                onClick={() => { setActiveFrame(i); setResult(videoResult.frames[i]); }}
                                                className={`shrink-0 w-12 h-8 rounded border overflow-hidden cursor-pointer transition-all ${i === activeFrame ? 'border-cyan ring-1 ring-cyan/30' : 'border-border opacity-60 hover:opacity-100'
                                                    }`}
                                            >
                                                <img src={`data:image/jpeg;base64,${f.annotated_image_b64}`} alt="" className="w-full h-full object-cover" />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Detect Button */}
                            {!result && !loading && (
                                <button
                                    onClick={runDetection}
                                    className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan to-purple text-white font-semibold text-sm tracking-wide hover:shadow-lg hover:shadow-cyan/20 transition-all cursor-pointer shrink-0"
                                >
                                    <div className="flex items-center justify-center gap-2">
                                        <ScanSearch size={16} />
                                        Run AI Detection Pipeline
                                    </div>
                                </button>
                            )}

                            {error && (
                                <div className="p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-xs flex items-center gap-2 shrink-0">
                                    <AlertTriangle size={14} />
                                    {error}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Right — Stats Panel */}
                {currentResult && (
                    <div className="w-[300px] shrink-0 flex flex-col gap-3 overflow-y-auto">
                        {/* Crowd Density Gauge */}
                        <div className="glass-card p-4">
                            <div className="text-[11px] text-text-muted mb-3 font-medium">Crowd Density</div>
                            <div className="flex items-center justify-center">
                                <div className="relative w-32 h-32">
                                    <svg viewBox="0 0 140 140" className="w-full h-full -rotate-90">
                                        <circle cx="70" cy="70" r="60" fill="none" stroke="#1E293B" strokeWidth="10" />
                                        <circle
                                            cx="70" cy="70" r="60" fill="none"
                                            stroke={riskColor(currentResult.risk_level)}
                                            strokeWidth="10"
                                            strokeLinecap="round"
                                            strokeDasharray={`${currentResult.risk_score * 377} 377`}
                                        />
                                    </svg>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                        <span className="text-3xl font-bold text-text-primary">{currentResult.person_count}</span>
                                        <span className="text-[10px] text-text-muted">ppl</span>
                                        <span className="text-[10px] font-bold mt-0.5" style={{ color: riskColor(currentResult.risk_level) }}>
                                            {currentResult.risk_level}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { label: 'Persons', value: currentResult.person_count, icon: Users, color: '#00E5FF' },
                                { label: 'Risk Score', value: `${(currentResult.risk_score * 100).toFixed(0)}%`, icon: Shield, color: riskColor(currentResult.risk_level) },
                                { label: 'Stampede Risk', value: `${currentResult.stampede_risk.toFixed(1)}`, icon: AlertTriangle, color: '#FF3D00' },
                                { label: 'Flow Rate', value: `${currentResult.flow_rate.toFixed(1)}`, icon: Activity, color: '#7B61FF' },
                                { label: 'Density', value: `${currentResult.density_estimate.toFixed(1)}`, icon: Gauge, color: '#FFB300' },
                                { label: 'Latency', value: `${currentResult.inference_time_ms.toFixed(0)}ms`, icon: Zap, color: '#00C853' },
                            ].map((stat, i) => (
                                <div key={i} className="glass-card p-3">
                                    <div className="flex items-center gap-1.5 mb-1.5">
                                        <stat.icon size={11} style={{ color: stat.color }} />
                                        <span className="text-[9px] text-text-muted">{stat.label}</span>
                                    </div>
                                    <div className="text-lg font-bold" style={{ color: stat.color }}>{stat.value}</div>
                                </div>
                            ))}
                        </div>

                        {/* Detection Log */}
                        <div className="glass-card p-3 flex-1">
                            <div className="text-[11px] text-text-muted mb-2 font-medium">AI Detection Log</div>
                            <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                {currentResult.detections.slice(0, 20).map((det, i) => (
                                    <div key={i} className="flex items-center justify-between px-2 py-1.5 rounded bg-bg-primary/50 border border-border text-[10px]">
                                        <div className="flex items-center gap-2">
                                            <span className="w-4 h-4 rounded bg-cyan/15 text-cyan flex items-center justify-center font-mono text-[8px]">{i + 1}</span>
                                            <span className="text-text-secondary font-medium">{det.class_name}</span>
                                        </div>
                                        <span className={`font-mono ${det.confidence > 0.8 ? 'text-success' : det.confidence > 0.5 ? 'text-warning' : 'text-danger'}`}>
                                            {(det.confidence * 100).toFixed(1)}%
                                        </span>
                                    </div>
                                ))}
                                {currentResult.detections.length === 0 && (
                                    <div className="text-center py-4 text-text-muted text-[10px]">No detections found</div>
                                )}
                            </div>
                        </div>

                        {/* Congestion Zones */}
                        {currentResult.congestion_zones.length > 0 && (
                            <div className="glass-card p-3">
                                <div className="text-[11px] text-text-muted mb-2 font-medium">Congestion Zones</div>
                                <div className="space-y-1.5">
                                    {currentResult.congestion_zones.map((zone, i) => (
                                        <div key={i} className="flex items-center justify-between">
                                            <span className="text-[10px] text-text-secondary">{zone.zone}</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 h-1.5 rounded-full bg-bg-primary overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all"
                                                        style={{
                                                            width: `${zone.congestion * 100}%`,
                                                            backgroundColor: zone.congestion > 0.7 ? '#FF3D00' : zone.congestion > 0.4 ? '#FFB300' : '#00C853',
                                                        }}
                                                    />
                                                </div>
                                                <span className="text-[10px] text-text-muted font-mono">{zone.count}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Video Summary */}
                        {videoResult && (
                            <div className="glass-card p-3">
                                <div className="text-[11px] text-text-muted mb-2 font-medium">Video Summary</div>
                                <div className="space-y-1.5 text-[10px]">
                                    <div className="flex justify-between"><span className="text-text-muted">Total Frames</span><span className="text-text-primary font-mono">{videoResult.total_frames}</span></div>
                                    <div className="flex justify-between"><span className="text-text-muted">Processed</span><span className="text-text-primary font-mono">{videoResult.processed_frames}</span></div>
                                    <div className="flex justify-between"><span className="text-text-muted">Avg Persons</span><span className="text-text-primary font-mono">{videoResult.avg_person_count.toFixed(1)}</span></div>
                                    <div className="flex justify-between"><span className="text-text-muted">Max Persons</span><span className="text-cyan font-mono">{videoResult.max_person_count}</span></div>
                                    <div className="flex justify-between"><span className="text-text-muted">Peak Risk</span><span className="font-bold" style={{ color: riskColor(videoResult.peak_risk_level) }}>{videoResult.peak_risk_level}</span></div>
                                    <div className="flex justify-between"><span className="text-text-muted">Processing Time</span><span className="text-text-primary font-mono">{(videoResult.processing_time_ms / 1000).toFixed(1)}s</span></div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
