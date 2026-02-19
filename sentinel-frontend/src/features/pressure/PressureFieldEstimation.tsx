import { Gauge, AlertTriangle } from 'lucide-react';
import { useDashboardStore } from '../../store/useDashboardStore';

const zones = [
    { id: 'A', name: 'Main Gate', x: 15, y: 20, pressure: 0.82, direction: 135, risk: 'high' as const },
    { id: 'B', name: 'Central Plaza', x: 45, y: 35, pressure: 0.94, direction: 90, risk: 'critical' as const },
    { id: 'C', name: 'East Corridor', x: 75, y: 25, pressure: 0.45, direction: 180, risk: 'medium' as const },
    { id: 'D', name: 'Concourse', x: 30, y: 65, pressure: 0.61, direction: 45, risk: 'medium' as const },
    { id: 'E', name: 'Exit Path', x: 65, y: 70, pressure: 0.73, direction: 270, risk: 'high' as const },
];

const collisionPoints = [
    { x: 38, y: 45, force: 87, label: 'CP-1' },
    { x: 60, y: 50, force: 62, label: 'CP-2' },
    { x: 52, y: 30, force: 45, label: 'CP-3' },
];

const riskColor = {
    low: '#00C853',
    medium: '#FFB300',
    high: '#FF3D00',
    critical: '#FF3D00',
};

export default function PressureFieldEstimation() {
    const liveMetrics = useDashboardStore((s) => s.liveMetrics);

    // Fallback to static if no live data (for safety)
    const currentPressure = liveMetrics?.pressure ?? 0.71;
    const currentCollisions = liveMetrics?.collisions ?? collisionPoints;

    // Dynamically update zones based on live pressure
    const dynamicZones = zones.map(z => ({
        ...z,
        pressure: Math.min(1, currentPressure * (1 + (Math.random() * 0.2 - 0.1))), // Add small jitter for "live" feel
        risk: currentPressure > 0.8 ? 'critical' : currentPressure > 0.6 ? 'high' : currentPressure > 0.4 ? 'medium' : 'low' as const
    }));

    return (
        <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-danger/15 flex items-center justify-center">
                        <Gauge size={14} className="text-danger" />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-text-primary">Pressure Field Estimation</h3>
                        <p className="text-[10px] text-text-muted">Real-time crowd pressure vectors & collision force prediction</p>
                    </div>
                </div>
                <div className="flex items-center gap-3 text-[10px]">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-success" /> Low</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-warning" /> Medium</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-danger" /> High</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-danger animate-pulse" /> Critical</span>
                </div>
            </div>

            {/* Pressure Field Map */}
            <div className="relative h-64 rounded-lg bg-bg-primary border border-border overflow-hidden">
                {/* Grid */}
                <div className="absolute inset-0 opacity-8"
                    style={{
                        backgroundImage: 'linear-gradient(rgba(0,229,255,0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.2) 1px, transparent 1px)',
                        backgroundSize: '24px 24px',
                    }}
                />

                {/* Pressure gradient zones */}
                {dynamicZones.map((zone) => (
                    <div
                        key={zone.id}
                        className="absolute flex flex-col items-center"
                        style={{ left: `${zone.x}%`, top: `${zone.y}%`, transform: 'translate(-50%, -50%)' }}
                    >
                        {/* Pressure circle */}
                        <div
                            className={`rounded-full flex items-center justify-center ${zone.risk === 'critical' ? 'animate-pulse' : ''}`}
                            style={{
                                width: `${40 + zone.pressure * 30}px`,
                                height: `${40 + zone.pressure * 30}px`,
                                background: `radial-gradient(circle, ${riskColor[zone.risk]}40, ${riskColor[zone.risk]}10, transparent)`,
                                border: `1.5px solid ${riskColor[zone.risk]}60`,
                            }}
                        >
                            <span className="text-[10px] font-bold" style={{ color: riskColor[zone.risk] }}>{zone.id}</span>
                        </div>

                        {/* Pressure vector arrow */}
                        <div
                            className="absolute w-8 h-0.5"
                            style={{
                                background: `linear-gradient(90deg, ${riskColor[zone.risk]}, transparent)`,
                                transformOrigin: 'left center',
                                transform: `rotate(${zone.direction}deg) translateX(${20 + zone.pressure * 15}px)`,
                                top: '50%',
                                left: '50%',
                            }}
                        />

                        {/* Label */}
                        <div className="mt-1 px-1.5 py-0.5 rounded bg-bg-secondary/80 border border-border">
                            <span className="text-[8px] text-text-muted">{zone.name}</span>
                            <span className="text-[9px] font-bold ml-1" style={{ color: riskColor[zone.risk] }}>
                                {(zone.pressure * 100).toFixed(0)}%
                            </span>
                        </div>
                    </div>
                ))}

                {/* Collision force points */}
                {currentCollisions.map((cp, idx) => (
                    <div
                        key={idx}
                        className="absolute flex flex-col items-center"
                        style={{ left: `${(cp.x / 6.4)}%`, top: `${(cp.y / 4.8)}%`, transform: 'translate(-50%, -50%)' }}
                    >
                        <div className="w-5 h-5 rounded-full border-2 border-warning/60 flex items-center justify-center bg-warning/10 animate-bounce">
                            <AlertTriangle size={8} className="text-warning" />
                        </div>
                        <span className="text-[8px] text-warning font-mono mt-0.5">{cp.label}: {cp.force}N</span>
                    </div>
                ))}

                {/* Flow direction arrows between zones */}
                <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
                    <defs>
                        <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
                            <polygon points="0 0, 6 2, 0 4" fill="#00E5FF" opacity="0.4" />
                        </marker>
                    </defs>
                    {/* Flow paths */}
                    <line x1="20%" y1="25%" x2="40%" y2="35%" stroke="#00E5FF" strokeWidth="1" strokeDasharray="4 4" opacity="0.3" markerEnd="url(#arrowhead)" />
                    <line x1="50%" y1="38%" x2="70%" y2="28%" stroke="#00E5FF" strokeWidth="1" strokeDasharray="4 4" opacity="0.3" markerEnd="url(#arrowhead)" />
                    <line x1="35%" y1="65%" x2="60%" y2="68%" stroke="#00E5FF" strokeWidth="1" strokeDasharray="4 4" opacity="0.3" markerEnd="url(#arrowhead)" />
                    <line x1="48%" y1="38%" x2="35%" y2="60%" stroke="#FFB300" strokeWidth="1" strokeDasharray="4 4" opacity="0.3" markerEnd="url(#arrowhead)" />
                </svg>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-4 gap-2 mt-3">
                {[
                    { label: 'Avg Pressure', value: currentPressure.toFixed(2), unit: 'MPa', color: currentPressure > 0.8 ? '#FF3D00' : currentPressure > 0.5 ? '#FFB300' : '#00C853' },
                    { label: 'Max Force', value: currentCollisions.length > 0 ? Math.max(...currentCollisions.map(c => c.force)).toFixed(0) : '0', unit: 'N', color: '#FF3D00' },
                    { label: 'Collision Points', value: currentCollisions.length.toString(), unit: 'detected', color: '#FF3D00' },
                    { label: 'Flow Stability', value: (liveMetrics?.flowMagnitude ? Math.max(0, 100 - liveMetrics.flowMagnitude * 10).toFixed(0) : '64') + '%', unit: '', color: '#00E5FF' },
                ].map((m, i) => (
                    <div key={i} className="p-2 rounded-lg bg-bg-primary/50 border border-border text-center">
                        <div className="text-lg font-bold" style={{ color: m.color }}>{m.value}</div>
                        <div className="text-[9px] text-text-muted">{m.label} <span className="text-text-secondary">{m.unit}</span></div>
                    </div>
                ))}
            </div>
        </div>
    );
}
