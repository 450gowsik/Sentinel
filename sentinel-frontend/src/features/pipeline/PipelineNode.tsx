import StatusBadge from '../../components/StatusBadge';
import type { PipelineStage } from '../../types';

interface PipelineNodeProps {
    stage: PipelineStage;
    isLast?: boolean;
}

export default function PipelineNode({ stage, isLast = false }: PipelineNodeProps) {
    const statusColor =
        stage.status === 'active' ? '#00C853' :
            stage.status === 'processing' ? '#00E5FF' :
                stage.status === 'error' ? '#FF3D00' : '#64748B';

    return (
        <div className="flex items-center">
            <div className="glass-card p-3 min-w-[140px] hover:glass-card-hover transition-all duration-300 group relative">
                {/* Top glow line */}
                <div
                    className="absolute top-0 left-2 right-2 h-px opacity-50 group-hover:opacity-100 transition-opacity"
                    style={{ background: `linear-gradient(90deg, transparent, ${statusColor}, transparent)` }}
                />

                <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold text-text-primary">{stage.name}</span>
                </div>

                <StatusBadge status={stage.status} size="sm" />

                <div className="flex items-center justify-between mt-2.5 text-[10px]">
                    <span className="text-text-muted">
                        Latency: <span className="text-text-secondary font-mono">{stage.latency}ms</span>
                    </span>
                </div>
                <div className="mt-1 text-[10px] text-text-muted">
                    Confidence: <span className="font-semibold" style={{ color: statusColor }}>{stage.confidence}%</span>
                </div>
            </div>

            {/* Connector Arrow */}
            {!isLast && (
                <div className="flex items-center mx-1.5">
                    <div className="w-6 h-px bg-gradient-to-r from-border to-cyan/40" />
                    <div className="w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-l-[6px] border-l-cyan/40" />
                </div>
            )}
        </div>
    );
}
