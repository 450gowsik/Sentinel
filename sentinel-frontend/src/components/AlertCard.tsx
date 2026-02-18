import { AlertTriangle, AlertCircle, Info, Check, MapPin, Clock } from 'lucide-react';
import type { Alert } from '../types';
import { useAlertStore } from '../store/useAlertStore';

const typeConfig = {
    critical: {
        icon: AlertTriangle,
        color: 'text-danger',
        bg: 'bg-danger/10',
        border: 'border-danger/30',
        glow: 'glow-danger',
    },
    warning: {
        icon: AlertCircle,
        color: 'text-warning',
        bg: 'bg-warning/10',
        border: 'border-warning/30',
        glow: 'glow-warning',
    },
    info: {
        icon: Info,
        color: 'text-cyan',
        bg: 'bg-cyan/10',
        border: 'border-cyan/30',
        glow: '',
    },
};

interface AlertCardProps {
    alert: Alert;
}

export default function AlertCard({ alert }: AlertCardProps) {
    const acknowledgeAlert = useAlertStore((s) => s.acknowledgeAlert);
    const config = typeConfig[alert.type];
    const Icon = config.icon;
    const timeAgo = getTimeAgo(alert.timestamp);

    return (
        <div
            className={`glass-card p-3.5 border ${config.border} ${!alert.acknowledged ? config.glow : 'opacity-60'
                } transition-all duration-300 animate-slide-in`}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${config.bg}`}>
                        <Icon size={14} className={config.color} />
                    </div>
                    <div>
                        <span className={`text-xs font-bold uppercase tracking-wide ${config.color}`}>
                            {alert.title}
                        </span>
                    </div>
                </div>
                {!alert.acknowledged && (
                    <button
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-bg-primary/50 border border-border hover:border-success/30 hover:text-success text-text-muted text-[10px] font-medium transition-colors cursor-pointer"
                    >
                        <Check size={10} />
                        ACK
                    </button>
                )}
            </div>

            {/* Message */}
            <p className="text-xs text-text-secondary leading-relaxed mb-2">{alert.message}</p>

            {/* Meta */}
            <div className="flex items-center gap-3 text-[10px] text-text-muted">
                <span className="flex items-center gap-1">
                    <MapPin size={10} />
                    {alert.zone}
                </span>
                <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {timeAgo}
                </span>
            </div>

            {/* Recommended Action */}
            <div className="mt-2 px-2.5 py-1.5 rounded-md bg-bg-primary/50 border border-border">
                <span className="text-[10px] text-purple font-semibold uppercase tracking-wide">Recommended: </span>
                <span className="text-[11px] text-text-secondary">{alert.recommendedAction}</span>
            </div>
        </div>
    );
}

function getTimeAgo(timestamp: string): string {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
}
