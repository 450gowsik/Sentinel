import { Navigation, ArrowRightLeft, TrendingUp, Users } from 'lucide-react';

const flowSegments = [
    { id: 'F1', from: 'Main Gate', to: 'Central Plaza', speed: 1.4, density: 4.2, direction: 'inbound', status: 'normal' as const },
    { id: 'F2', from: 'Central Plaza', to: 'East Wing', speed: 0.8, density: 5.8, direction: 'outbound', status: 'congested' as const },
    { id: 'F3', from: 'East Wing', to: 'Exit Corridor', speed: 1.1, density: 3.1, direction: 'outbound', status: 'normal' as const },
    { id: 'F4', from: 'Concourse', to: 'Central Plaza', speed: 0.4, density: 6.1, direction: 'counter-flow', status: 'critical' as const },
    { id: 'F5', from: 'Main Gate', to: 'Concourse', speed: 1.2, density: 2.8, direction: 'inbound', status: 'normal' as const },
];

const statusConfig = {
    normal: { color: '#00C853', bg: 'bg-success/10', label: 'NORMAL' },
    congested: { color: '#FFB300', bg: 'bg-warning/10', label: 'CONGESTED' },
    critical: { color: '#FF3D00', bg: 'bg-danger/10', label: 'CRITICAL' },
};

export default function CrowdFlowVisualization() {
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

                {/* Zone nodes */}
                {[
                    { name: 'Main Gate', x: 10, y: 50, color: '#00C853' },
                    { name: 'Central Plaza', x: 40, y: 35, color: '#FF3D00' },
                    { name: 'East Wing', x: 70, y: 25, color: '#FFB300' },
                    { name: 'Concourse', x: 30, y: 75, color: '#FFB300' },
                    { name: 'Exit', x: 88, y: 55, color: '#00C853' },
                ].map((node) => (
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
                        <span className="text-[8px] text-text-secondary mt-1 font-semibold bg-bg-primary/80 px-1.5 py-0.5 rounded">{node.name}</span>
                    </div>
                ))}

                {/* Flow arrows */}
                <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
                    <defs>
                        <marker id="flowArrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#00E5FF" opacity="0.5" />
                        </marker>
                        <marker id="flowArrowWarning" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#FFB300" opacity="0.6" />
                        </marker>
                        <marker id="flowArrowDanger" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#FF3D00" opacity="0.7" />
                        </marker>
                    </defs>
                    {/* Main Gate → Central Plaza */}
                    <path d="M 15% 48% Q 28% 30%, 36% 35%" fill="none" stroke="#00C853" strokeWidth="2" strokeDasharray="6 3" opacity="0.5" markerEnd="url(#flowArrow)">
                        <animate attributeName="stroke-dashoffset" values="0;-18" dur="1.5s" repeatCount="indefinite" />
                    </path>
                    {/* Central Plaza → East Wing */}
                    <path d="M 44% 33% Q 55% 22%, 66% 25%" fill="none" stroke="#FFB300" strokeWidth="2" strokeDasharray="6 3" opacity="0.5" markerEnd="url(#flowArrowWarning)">
                        <animate attributeName="stroke-dashoffset" values="0;-18" dur="2s" repeatCount="indefinite" />
                    </path>
                    {/* East Wing → Exit */}
                    <path d="M 74% 28% Q 80% 40%, 84% 52%" fill="none" stroke="#00C853" strokeWidth="1.5" strokeDasharray="6 3" opacity="0.4" markerEnd="url(#flowArrow)">
                        <animate attributeName="stroke-dashoffset" values="0;-18" dur="1.5s" repeatCount="indefinite" />
                    </path>
                    {/* Concourse → Central Plaza (counter-flow) */}
                    <path d="M 33% 72% Q 36% 55%, 38% 40%" fill="none" stroke="#FF3D00" strokeWidth="2.5" strokeDasharray="4 4" opacity="0.6" markerEnd="url(#flowArrowDanger)">
                        <animate attributeName="stroke-dashoffset" values="0;-16" dur="1s" repeatCount="indefinite" />
                    </path>
                    {/* Main Gate → Concourse */}
                    <path d="M 14% 55% Q 20% 68%, 26% 73%" fill="none" stroke="#00C853" strokeWidth="1.5" strokeDasharray="6 3" opacity="0.4" markerEnd="url(#flowArrow)">
                        <animate attributeName="stroke-dashoffset" values="0;-18" dur="1.5s" repeatCount="indefinite" />
                    </path>
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
                                <TrendingUp size={9} className="inline mr-0.5" />{seg.speed} m/s
                            </span>
                            <span className="text-[10px] text-text-muted">{seg.density} p/m²</span>
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
