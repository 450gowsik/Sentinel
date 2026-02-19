import React from 'react';
import { Wifi, WifiOff, Maximize2, Settings2 } from 'lucide-react';
import { useDashboardStore } from '../store/useDashboardStore';
import { useSentinelStream } from '../hooks/useSentinelStream';

interface LiveCameraFeedProps {
    cameraId: string;
    name: string;
    zone: string;
}

const LiveCameraFeed: React.FC<LiveCameraFeedProps> = ({ cameraId, name, zone }) => {
    const backendCameraActive = useDashboardStore((s) => s.backendCameraActive);
    const { frame, metadata, connected, error } = useSentinelStream(cameraId, backendCameraActive);

    return (
        <div className="glass-card overflow-hidden group">
            {/* Camera Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${connected ? 'bg-danger pulse-dot' : 'bg-text-muted'}`} />
                    <span className="text-[11px] font-semibold text-text-primary">{name}</span>
                </div>
                <div className="flex items-center gap-2">
                    {connected ? (
                        <span className="flex items-center gap-1 text-[9px] text-success">
                            <Wifi size={10} /> LIVE
                        </span>
                    ) : (
                        <span className="flex items-center gap-1 text-[9px] text-text-muted">
                            <WifiOff size={10} /> {error ? 'ERROR' : 'OFFLINE'}
                        </span>
                    )}
                </div>
            </div>

            {/* Camera Feed */}
            <div className="aspect-video bg-bg-primary relative flex items-center justify-center overflow-hidden">
                {frame ? (
                    <img
                        src={frame}
                        alt={name}
                        className="w-full h-full object-cover"
                    />
                ) : (
                    <div className="text-center p-4">
                        <div className={`${!connected ? 'animate-pulse' : ''} mb-1`}>
                            <WifiOff className="mx-auto text-text-muted" size={24} />
                        </div>
                        <div className="text-[10px] text-text-muted">
                            {connected ? 'Waiting for stream...' : 'Connecting...'}
                        </div>
                        {error && <div className="text-[8px] text-danger mt-1">{error}</div>}
                    </div>
                )}

                {/* Overlay Grid (subtle) */}
                {!frame && (
                    <div className="absolute inset-0 opacity-5 pointer-events-none"
                        style={{
                            backgroundImage: 'linear-gradient(rgba(0,229,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.4) 1px, transparent 1px)',
                            backgroundSize: '20px 20px',
                        }}
                    />
                )}

                {/* Inference Stats Overlay (if available) */}
                {metadata && (
                    <div className="absolute top-2 left-2 flex gap-1">
                        <div className="bg-black/60 backdrop-blur-sm px-1.5 py-0.5 rounded text-[8px] text-white font-mono">
                            FPS: {metadata.fps.toFixed(1)}
                        </div>
                    </div>
                )}

                {/* Actions overlay */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="w-6 h-6 rounded bg-bg-primary/70 flex items-center justify-center cursor-pointer hover:bg-bg-primary">
                        <Maximize2 size={10} className="text-text-secondary" />
                    </button>
                    <button className="w-6 h-6 rounded bg-bg-primary/70 flex items-center justify-center cursor-pointer hover:bg-bg-primary">
                        <Settings2 size={10} className="text-text-secondary" />
                    </button>
                </div>
            </div>

            {/* Stats Footer */}
            <div className="flex items-center justify-between px-3 py-2 text-[10px] text-text-muted border-t border-border">
                <span>{zone}</span>
                <div className="flex gap-3">
                    <span>Objects: {metadata?.person_count ?? 0}</span>
                    <span>Risk: {metadata?.risk_level ?? 'LOW'}</span>
                </div>
            </div>
        </div>
    );
};

export default LiveCameraFeed;
