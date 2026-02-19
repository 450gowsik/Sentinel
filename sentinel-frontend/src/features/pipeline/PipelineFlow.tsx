import { usePipelineStore } from '../../store/usePipelineStore';
import PipelineNode from './PipelineNode';
import { Workflow, Zap } from 'lucide-react';

export default function PipelineFlow() {
    const stages = usePipelineStore((s) => s.stages);

    const totalLatency = stages.reduce((a, s) => a + s.latency, 0);
    const avgConfidence = (stages.reduce((a, s) => a + s.confidence, 0) / stages.length).toFixed(1);

    return (
        <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-cyan/15 flex items-center justify-center">
                        <Workflow size={14} className="text-cyan" />
                    </div>
                    <h3 className="text-sm font-semibold text-text-primary">AI Processing Pipeline</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/15 text-success font-bold tracking-wider">LIVE</span>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-text-muted">
                    <span className="flex items-center gap-1">
                        <Zap size={10} className="text-warning" />
                        Total Latency: <span className="text-text-secondary font-mono">{totalLatency}ms</span>
                    </span>
                    <span>
                        Avg Confidence: <span className="text-cyan font-mono">{avgConfidence}%</span>
                    </span>
                </div>
            </div>

            <div className="flex items-center overflow-x-auto pb-2">
                {stages.map((stage, index) => (
                    <PipelineNode
                        key={stage.id}
                        stage={stage}
                        isLast={index === stages.length - 1}
                    />
                ))}
            </div>

            {/* Pipeline Description */}
            <div className="mt-3 p-2.5 rounded-lg bg-bg-primary/50 border border-border">
                <div className="flex items-center gap-4 text-[10px] text-text-muted">
                    <span>CCTV Input → YOLO v9 Detection → Multi-Object Tracking → Behaviour Pattern Analysis → Pressure Field Estimation → Risk Scoring Engine → Automated Safety Response</span>
                </div>
            </div>
        </div>
    );
}
