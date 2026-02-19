import { Navigation, ArrowRightLeft, TrendingUp, Users, Radio } from 'lucide-react';
import { useDashboardStore } from '../../store/useDashboardStore';
import { useMemo } from 'react';

const statusConfig = {
    normal: { color: '#00C853', bg: 'bg-success/10', label: 'NORMAL' },
    congested: { color: '#FFB300', bg: 'bg-warning/10', label: 'CONGESTED' },
    critical: { color: '#FF3D00', bg: 'bg-danger/10', label: 'CRITICAL' },
};

// Zone position mapping for visualization (using short IDs from backend: A, B, C, D, E)
const zonePositions: Record<string, { x: number; y: number }> = {
    'A': { x: 10, y: 50 },
    'B': { x: 40, y: 35 },
    'C': { x: 70, y: 25 },
    'D': { x: 30, y: 75 },
    'E': { x: 88, y: 55 },
};

function getStatusFromPressure(pressure: number): 'normal' | 'congested' | 'critical' {
    if (pressure >= 0.7) return 'critical';
    if (pressure >= 0.4) return 'congested';
    return 'normal';
}

export default function CrowdFlowVisualization() {
    const pipelineData = useDashboardStore((s) => s.pipelineData);
    const isLive = !!pipelineData;

    // Derive flow segments from real data
    const flowSegments = useMemo(() => {
        if (!pipelineData?.zones) {
            return [
                { id: 'F1', from: 'A', to: 'B', speed: 0, density: 0, direction: 'inbound', status: 'normal' as const },
            ];
        }
        const zones = pipelineData.zones;
        const segments: Array<{
            id: string;
            from: string;
            to: string;
            speed: number;
            density: number;
            direction: string;
            status: 'normal' | 'congested' | 'critical';
        }> = [];

        // Create flow segments between adjacent zones
        for (let i = 0; i < zones.length - 1; i++) {
            const fromZone = zones[i];
            const toZone = zones[i + 1];
            const avgPressure = (fromZone.pressure + toZone.pressure) / 2;
            segments.push({
                id: `F${i + 1}`,
                from: fromZone.id,
                to: toZone.id,
                speed: Math.max(0.2, 1.5 - avgPressure),
                density: avgPressure * 7,
                direction: i % 2 === 0 ? 'inbound' : 'outbound',
                status: getStatusFromPressure(avgPressure),
            });
        }
        return segments.length > 0 ? segments : [
            { id: 'F1', from: 'Zone-A', to: 'Zone-B', speed: 0, density: 0, direction: 'inbound', status: 'normal' as const },
        ];
    }, [pipelineData]);

    // Derive zone nodes from real data
    const zoneNodes = useMemo(() => {
        if (!pipelineData?.zones) {
            return Object.keys(zonePositions).map((id) => ({
                name: id,
                x: zonePositions[id].x,
                y: zonePositions[id].y,
                color: '#00C853',
                pressure: 0,
            }));
        }
        return pipelineData.zones.map((z) => {
            const pos = zonePositions[z.id] || { x: 50, y: 50 };
            const status = getStatusFromPressure(z.pressure);
            return {
                name: z.id,
                x: pos.x,
                y: pos.y,
                color: statusConfig[status].color,
                pressure: z.pressure,
            };
        });
    }, [pipelineData]);
    return (
        <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-cyan/15 flex items-center justify-center">
                        <Navigation size={14} className="text-cyan" />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-text-primary">Crowd Flow Visualization</h3>
                        <p className="text-[10px] text-text-muted">Directional movement patterns & flow rate analysis</p>
                    </div>
                </div>
                {/* Live indicator */}
                <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${isLive ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}`}>
                    <Radio size={10} className={isLive ? 'animate-pulse' : ''} />
                    {isLive ? 'LIVE' : 'WAITING'}
                </div>
            </div>

            {/* Flow Map */}
            <div className="relative h-48 rounded-lg bg-bg-primary border border-border overflow-hidden mb-3">
                {/* Grid */}
                <div className="absolute inset-0 opacity-5"
                    style={{
                        backgroundImage: 'linear-gradient(rgba(0,229,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.3) 1px, transparent 1px)',
                        backgroundSize: '20px 20px',
                    }}
                />

                {/* Zone nodes from real data */}
                {zoneNodes.map((node) => (
                    <div
                        key={node.name}
                        className="absolute flex flex-col items-center"
                        style={{ left: `${node.x}%`, top: `${node.y}%`, transform: 'translate(-50%, -50%)' }}
                    >
                        <div
                            className="w-10 h-10 rounded-full flex items-center justify-center border-2"
                            style={{ borderColor: `${node.color}80`, backgroundColor: `${node.color}15` }}
                        >
                            <Users size={14} style={{ color: node.color }} />
                        </div>
                        <span className="text-[8px] text-text-secondary mt-1 font-semibold bg-bg-primary/80 px-1.5 py-0.5 rounded">
                            {node.name}
                        </span>
                        <span className="text-[7px] text-text-muted">
                            {(node.pressure * 100).toFixed(0)}%
                        </span>
                    </div>
                ))}

                {/* Flow arrows - dynamically generated */}
                <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
                    <defs>
                        <marker id="flowArrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#00C853" opacity="0.5" />
                        </marker>
                        <marker id="flowArrowWarning" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#FFB300" opacity="0.6" />
                        </marker>
                        <marker id="flowArrowDanger" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#FF3D00" opacity="0.7" />
                        </marker>
                    </defs>
                    {/* Dynamic flow paths based on segments */}
                    {flowSegments.map((seg, idx) => {
                        const fromPos = zonePositions[seg.from] || { x: 20, y: 50 };
                        const toPos = zonePositions[seg.to] || { x: 80, y: 50 };
                        const midX = (fromPos.x + toPos.x) / 2;
                        const midY = Math.min(fromPos.y, toPos.y) - 10 + (idx * 5);
                        const color = statusConfig[seg.status].color;
                        const markerEnd = seg.status === 'critical' ? 'url(#flowArrowDanger)' : seg.status === 'congested' ? 'url(#flowArrowWarning)' : 'url(#flowArrow)';
                        const strokeWidth = seg.status === 'critical' ? 2.5 : seg.status === 'congested' ? 2 : 1.5;
                        const animDur = seg.status === 'critical' ? '1s' : seg.status === 'congested' ? '2s' : '1.5s';
                        
                        return (
                            <path
                                key={seg.id}
                                d={`M ${fromPos.x + 4}% ${fromPos.y}% Q ${midX}% ${midY}%, ${toPos.x - 4}% ${toPos.y}%`}
                                fill="none"
                                stroke={color}
                                strokeWidth={strokeWidth}
                                strokeDasharray="6 3"
                                opacity="0.5"
                                markerEnd={markerEnd}
                            >
                                <animate attributeName="stroke-dashoffset" values="0;-18" dur={animDur} repeatCount="indefinite" />
                            </path>
                        );
                    })}
                </svg>
            </div>

            {/* Flow Segments Table */}
            <div className="space-y-1.5">
                {flowSegments.map((seg) => {
                    const cfg = statusConfig[seg.status];
                    return (
                        <div key={seg.id} className="flex items-center gap-3 p-2 rounded-lg bg-bg-primary/50 border border-border">
                            <span className="text-[10px] font-mono text-text-muted w-8">{seg.id}</span>
                            <div className="flex items-center gap-1.5 flex-1 min-w-0">
                                <span className="text-[11px] text-text-secondary truncate">{seg.from}</span>
                                <ArrowRightLeft size={10} className="text-text-muted shrink-0" />
                                <span className="text-[11px] text-text-secondary truncate">{seg.to}</span>
                            </div>
                            <span className="text-[10px] text-text-muted">
                                <TrendingUp size={9} className="inline mr-0.5" />{seg.speed.toFixed(1)} m/s
                            </span>
                            <span className="text-[10px] text-text-muted">{seg.density.toFixed(1)} p/m²</span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${cfg.bg}`} style={{ color: cfg.color }}>
                                {cfg.label}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
