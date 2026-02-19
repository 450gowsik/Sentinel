interface StatusBadgeProps {
    status: 'active' | 'processing' | 'idle' | 'error' | 'online' | 'offline' | 'degraded';
    label?: string;
    size?: 'sm' | 'md';
}

const statusConfig: Record<string, { color: string; bg: string; label: string }> = {
    active: { color: 'text-success', bg: 'bg-success/15', label: 'Active' },
    processing: { color: 'text-cyan', bg: 'bg-cyan/15', label: 'Processing' },
    idle: { color: 'text-text-muted', bg: 'bg-text-muted/15', label: 'Idle' },
    error: { color: 'text-danger', bg: 'bg-danger/15', label: 'Error' },
    online: { color: 'text-success', bg: 'bg-success/15', label: 'Online' },
    offline: { color: 'text-danger', bg: 'bg-danger/15', label: 'Offline' },
    degraded: { color: 'text-warning', bg: 'bg-warning/15', label: 'Degraded' },
};

export default function StatusBadge({ status, label, size = 'sm' }: StatusBadgeProps) {
    const config = statusConfig[status] || statusConfig.idle;
    const sizeClasses = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

    return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold tracking-wide uppercase ${config.bg} ${config.color} ${sizeClasses}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${status === 'processing' || status === 'active' ? 'pulse-dot' : ''}`}
                style={{ backgroundColor: 'currentColor' }}
            />
            {label || config.label}
        </span>
    );
}
