import { TrendingUp, TrendingDown, Minus, Users, ShieldAlert, BellRing, Brain, Zap, ScanEye } from 'lucide-react';
import type { MetricData } from '../types';

const iconMap: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
    users: Users,
    'shield-alert': ShieldAlert,
    'bell-ring': BellRing,
    brain: Brain,
    zap: Zap,
    'scan-eye': ScanEye,
};

interface MetricCardProps {
    metric: MetricData;
}

export default function MetricCard({ metric }: MetricCardProps) {
    const Icon = iconMap[metric.icon] || Users;
    const TrendIcon = metric.trend === 'up' ? TrendingUp : metric.trend === 'down' ? TrendingDown : Minus;
    const trendColor = metric.trend === 'up' ? 'text-danger' : metric.trend === 'down' ? 'text-success' : 'text-text-muted';

    return (
        <div className="glass-card p-4 hover:glass-card-hover transition-all duration-300 group">
            <div className="flex items-start justify-between mb-3">
                <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${metric.color}15` }}
                >
                    <Icon size={20} className={`text-[${metric.color}]`} />
                </div>
                <div className={`flex items-center gap-1 text-xs font-medium ${trendColor}`}>
                    <TrendIcon size={12} />
                    <span>{metric.trendValue}</span>
                </div>
            </div>
            <div className="mb-1">
                <span className="text-2xl font-bold text-text-primary">{metric.value}</span>
                <span className="text-xs text-text-muted ml-1.5">{metric.unit}</span>
            </div>
            <p className="text-xs text-text-secondary font-medium">{metric.label}</p>
            {/* Decorative bottom glow line */}
            <div
                className="mt-3 h-0.5 rounded-full opacity-40 group-hover:opacity-70 transition-opacity"
                style={{ background: `linear-gradient(90deg, ${metric.color}, transparent)` }}
            />
        </div>
    );
}

