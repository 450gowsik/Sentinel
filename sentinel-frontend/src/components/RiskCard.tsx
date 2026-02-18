import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { Bot } from 'lucide-react';
import type { RiskCardData } from '../types';

const severityConfig = {
    low: { color: '#00C853', bg: 'bg-success/10', border: 'border-success/20', label: 'LOW' },
    medium: { color: '#FFB300', bg: 'bg-warning/10', border: 'border-warning/20', label: 'MEDIUM' },
    high: { color: '#FF3D00', bg: 'bg-danger/10', border: 'border-danger/20', label: 'HIGH' },
    critical: { color: '#FF3D00', bg: 'bg-danger/15', border: 'border-danger/30', label: 'CRITICAL' },
};

interface RiskCardProps {
    data: RiskCardData;
}

export default function RiskCard({ data }: RiskCardProps) {
    const config = severityConfig[data.severity];
    const chartData = data.trend.map((v, i) => ({ idx: i, value: v }));
    const percentage = Math.round((data.value / data.maxValue) * 100);

    return (
        <div className={`glass-card p-4 border ${config.border} hover:glass-card-hover transition-all duration-300`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-text-primary">{data.title}</h3>
                <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${config.bg} tracking-wider`}
                    style={{ color: config.color }}
                >
                    {config.label}
                </span>
            </div>

            {/* Score + Sparkline */}
            <div className="flex items-end justify-between mb-3">
                <div>
                    <span className="text-3xl font-bold" style={{ color: config.color }}>
                        {data.value}
                    </span>
                    <span className="text-xs text-text-muted ml-1">/ {data.maxValue}</span>
                    <div className="mt-1 text-[11px] text-text-muted">{data.zone}</div>
                </div>
                <div className="w-24 h-12">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                            <defs>
                                <linearGradient id={`grad-${data.id}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={config.color} stopOpacity={0.3} />
                                    <stop offset="100%" stopColor={config.color} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke={config.color}
                                strokeWidth={1.5}
                                fill={`url(#grad-${data.id})`}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-1.5 rounded-full bg-bg-primary mb-3">
                <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${percentage}%`, backgroundColor: config.color }}
                />
            </div>

            {/* AI Recommendation */}
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-bg-primary/50 border border-border">
                <Bot size={14} className="text-purple shrink-0 mt-0.5" />
                <p className="text-[11px] text-text-secondary leading-relaxed">{data.recommendation}</p>
            </div>
        </div>
    );
}
