import { Bot, Lightbulb, TrendingUp, AlertTriangle } from 'lucide-react';
import { useDashboardStore } from '../store/useDashboardStore';

interface Recommendation {
    type: 'action' | 'insight' | 'warning';
    message: string;
    confidence: number;
}

const typeConfig = {
    action: { icon: TrendingUp, color: 'text-cyan', bg: 'bg-cyan/10', label: 'ACTION' },
    insight: { icon: Lightbulb, color: 'text-purple', bg: 'bg-purple/10', label: 'INSIGHT' },
    warning: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', label: 'WARNING' },
};

export default function AIRecommendationPanel() {
    const liveMetrics = useDashboardStore((s) => s.liveMetrics);

    // Generate dynamic recommendations based on live metrics
    const getRecommendations = (): Recommendation[] => {
        if (!liveMetrics) {
            return [
                { type: 'insight', message: 'Waiting for AI pipeline telemetry...', confidence: 99 },
                { type: 'action', message: 'Inference engine warming up — stand by', confidence: 98 },
            ];
        }

        const recs: Recommendation[] = [];

        // Risk-based
        if (liveMetrics.riskScore > 0.7) {
            recs.push({
                type: 'warning',
                message: `Critical risk detected (${Math.round(liveMetrics.riskScore * 100)}%). Coordinate emergency response team for immediate intervention.`,
                confidence: 96.4
            });
        } else if (liveMetrics.riskScore > 0.4) {
            recs.push({
                type: 'action',
                message: 'Elevated risk levels — deploy additional marshals to high-density zones',
                confidence: 92.1
            });
        }

        // Congestion-based
        if (liveMetrics.congestion > 0.6) {
            recs.push({
                type: 'action',
                message: 'Choke point identified — optimize exit throughput by opening auxiliary gates',
                confidence: 89.5
            });
        }

        // Anomaly-based
        if (liveMetrics.anomaly > 0.5) {
            recs.push({
                type: 'insight',
                message: 'Unusual group formation detected — possible bottleneck or security localized event',
                confidence: 87.2
            });
        }

        // Default if low activity
        if (recs.length === 0) {
            recs.push({
                type: 'insight',
                message: 'Subliminal flow patterns are stable. Efficiency is within 94% of baseline.',
                confidence: 91.8
            });
            recs.push({
                type: 'action',
                message: 'Maintain current perimeter security protocol.',
                confidence: 99.0
            });
        }

        return recs.slice(0, 3);
    };

    const recommendations = getRecommendations();

    return (
        <div className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-lg bg-purple/15 flex items-center justify-center">
                    <Bot size={14} className="text-purple" />
                </div>
                <h3 className="text-sm font-semibold text-text-primary">AI Recommendations</h3>
                <span className="text-[10px] text-text-muted ml-auto">Live Telemetry Analysis</span>
            </div>

            <div className="space-y-2.5">
                {recommendations.map((rec, index) => {
                    const config = typeConfig[rec.type];
                    const Icon = config.icon;

                    return (
                        <div
                            key={index}
                            className="flex items-start gap-3 p-2.5 rounded-lg bg-bg-primary/50 border border-border hover:border-border-active transition-colors animate-fade-in"
                        >
                            <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 mt-0.5 ${config.bg}`}>
                                <Icon size={12} className={config.color} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className={`text-[9px] font-bold tracking-wider ${config.color}`}>{config.label}</span>
                                    <span className="text-[9px] text-text-muted">Confidence: {rec.confidence}%</span>
                                </div>
                                <p className="text-[11px] text-text-secondary leading-relaxed">{rec.message}</p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
