import { Gauge, AlertTriangle, Radio } from 'lucide-react';
import { useDashboardStore, type ZoneData } from '../../store/useDashboardStore';

// Fallback data when no pipeline data is available
const defaultZones: ZoneData[] = [
    { id: 'A', name: 'Main Gate', x: 15, y: 20, pressure: 0.1, direction: 135, risk: 'low' },
    { id: 'B', name: 'Central Plaza', x: 45, y: 35, pressure: 0.1, direction: 90, risk: 'low' },
    { id: 'C', name: 'East Corridor', x: 75, y: 25, pressure: 0.1, direction: 180, risk: 'low' },
    { id: 'D', name: 'Concourse', x: 30, y: 65, pressure: 0.1, direction: 45, risk: 'low' },
    { id: 'E', name: 'Exit Path', x: 65, y: 70, pressure: 0.1, direction: 270, risk: 'low' },
];

const riskColor: Record<string, string> = {
    low: '#00C853',
    medium: '#FFB300',
    high: '#FF3D00',
    critical: '#FF3D00',
};

export default function PressureFieldEstimation() {
    // Get real-time data from the store
    const pipelineData = useDashboardStore((s) => s.pipelineData);
    
    // Use real data if available, otherwise fallback
    const zones = pipelineData?.zones?.length ? pipelineData.zones : defaultZones;
    const collisionPoints = pipelineData?.collisionPoints || [];
    const avgPressure = pipelineData?.avgPressure || 0;
    const maxForce = pipelineData?.maxForce || 0;
    const flowStability = pipelineData?.flowStability || 0;
    
    const isLive = pipelineData !== null && pipelineData.zones.length > 0;

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
                    {/* Live indicator */}
                    <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${isLive ? 'bg-success/20 text-success' : 'bg-text-muted/20 text-text-muted'}`}>
                        <Radio size={8} className={isLive ? 'animate-pulse' : ''} />
                        {isLive ? 'LIVE' : 'WAITING'}
                    </span>
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
                {zones.map((zone) => (
                    <div
                        key={zone.id}
                        className="absolute flex flex-col items-center transition-all duration-300"
                        style={{ left: `${zone.x}%`, top: `${zone.y}%`, transform: 'translate(-50%, -50%)' }}
                    >
                        {/* Pressure circle */}
                        <div
                            className={`rounded-full flex items-center justify-center transition-all duration-300 ${zone.risk === 'critical' ? 'animate-pulse' : ''}`}
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
                            className="absolute w-8 h-0.5 transition-all duration-300"
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
                            <span className="text-[9px] font-bold ml-1 transition-all duration-300" style={{ color: riskColor[zone.risk] }}>
                                {(zone.pressure * 100).toFixed(0)}%
                            </span>
                        </div>
                    </div>
                ))}

                {/* Collision force points */}
                {collisionPoints.map((cp) => (
                    <div
                        key={cp.label}
                        className="absolute flex flex-col items-center transition-all duration-300"
                        style={{ left: `${cp.x}%`, top: `${cp.y}%`, transform: 'translate(-50%, -50%)' }}
                    >
                        <div className="w-5 h-5 rounded-full border-2 border-warning/60 flex items-center justify-center bg-warning/10 animate-pulse">
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
                
                {/* No data overlay */}
                {!isLive && (
                    <div className="absolute inset-0 flex items-center justify-center bg-bg-primary/50 backdrop-blur-sm">
                        <div className="text-center">
                            <Radio size={24} className="text-text-muted mx-auto mb-2" />
                            <p className="text-xs text-text-muted">Waiting for pipeline data...</p>
                            <p className="text-[10px] text-text-secondary mt-1">Start camera to see live pressure analysis</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-4 gap-2 mt-3">
                {[
                    { label: 'Avg Pressure', value: avgPressure.toFixed(2), unit: 'MPa', color: avgPressure > 0.5 ? '#FF3D00' : '#FFB300' },
                    { label: 'Max Force', value: maxForce.toString(), unit: 'N', color: maxForce > 80 ? '#FF3D00' : '#FFB300' },
                    { label: 'Collision Points', value: collisionPoints.length.toString(), unit: 'detected', color: collisionPoints.length > 2 ? '#FF3D00' : '#00C853' },
                    { label: 'Flow Stability', value: `${(flowStability * 100).toFixed(0)}%`, unit: '', color: flowStability > 0.6 ? '#00E5FF' : '#FFB300' },
                ].map((m, i) => (
                    <div key={i} className="p-2 rounded-lg bg-bg-primary/50 border border-border text-center">
                        <div className="text-lg font-bold transition-all duration-300" style={{ color: m.color }}>{m.value}</div>
                        <div className="text-[9px] text-text-muted">{m.label} <span className="text-text-secondary">{m.unit}</span></div>
                    </div>
                ))}
            </div>
        </div>
    );
}
