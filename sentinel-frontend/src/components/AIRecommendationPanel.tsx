import { Bot, Lightbulb, TrendingUp, AlertTriangle } from 'lucide-react';

interface AIRecommendationPanelProps {
    recommendations?: {
        type: 'action' | 'insight' | 'warning';
        message: string;
        confidence: number;
    }[];
}

const defaultRecommendations = [
    {
        type: 'action' as const,
        message: 'Deploy 3 additional crowd marshals to Zone B Central Plaza to manage density increase',
        confidence: 94.2,
    },
    {
        type: 'warning' as const,
        message: 'Predicted density spike in Zone C East Wing within next 12 minutes — prepare overflow gates',
        confidence: 87.5,
    },
    {
        type: 'insight' as const,
        message: 'Flow patterns indicate reduced exit efficiency — consider reversing Lane 4 direction',
        confidence: 91.8,
    },
];

const typeConfig = {
    action: { icon: TrendingUp, color: 'text-cyan', bg: 'bg-cyan/10', label: 'ACTION' },
    insight: { icon: Lightbulb, color: 'text-purple', bg: 'bg-purple/10', label: 'INSIGHT' },
    warning: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', label: 'WARNING' },
};

export default function AIRecommendationPanel({ recommendations = defaultRecommendations }: AIRecommendationPanelProps) {
    return (
        <div className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-lg bg-purple/15 flex items-center justify-center">
                    <Bot size={14} className="text-purple" />
                </div>
                <h3 className="text-sm font-semibold text-text-primary">AI Recommendations</h3>
                <span className="text-[10px] text-text-muted ml-auto">Auto-generated</span>
            </div>

            <div className="space-y-2.5">
                {recommendations.map((rec, index) => {
                    const config = typeConfig[rec.type];
                    const Icon = config.icon;

                    return (
                        <div
                            key={index}
                            className="flex items-start gap-3 p-2.5 rounded-lg bg-bg-primary/50 border border-border hover:border-border-active transition-colors"
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
