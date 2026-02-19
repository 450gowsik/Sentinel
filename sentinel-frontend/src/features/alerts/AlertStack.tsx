import { useAlertStore } from '../../store/useAlertStore';
import AlertCard from '../../components/AlertCard';
import { BellRing, Filter } from 'lucide-react';
import { useState } from 'react';
import type { AlertSeverity } from '../../types';

export default function AlertStack() {
    const alerts = useAlertStore((s) => s.alerts);
    const [filter, setFilter] = useState<AlertSeverity | 'all'>('all');

    const filtered = filter === 'all' ? alerts : alerts.filter((a) => a.type === filter);

    const filterButtons: { value: AlertSeverity | 'all'; label: string; color: string }[] = [
        { value: 'all', label: 'All', color: 'text-text-secondary' },
        { value: 'critical', label: 'Critical', color: 'text-danger' },
        { value: 'warning', label: 'Warning', color: 'text-warning' },
        { value: 'info', label: 'Info', color: 'text-cyan' },
    ];

    return (
        <div className="glass-card flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between p-3 border-b border-border shrink-0">
                <div className="flex items-center gap-2">
                    <BellRing size={14} className="text-danger" />
                    <h3 className="text-xs font-semibold text-text-primary tracking-wide">ALERT FEED</h3>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-danger/15 text-danger font-bold">
                        {alerts.filter((a) => !a.acknowledged).length}
                    </span>
                </div>
                <Filter size={12} className="text-text-muted" />
            </div>

            {/* Filters */}
            <div className="flex items-center gap-1 px-3 py-2 border-b border-border shrink-0">
                {filterButtons.map((btn) => (
                    <button
                        key={btn.value}
                        onClick={() => setFilter(btn.value)}
                        className={`text-[10px] px-2 py-1 rounded-md font-medium transition-colors cursor-pointer ${filter === btn.value
                                ? `${btn.color} bg-bg-primary border border-border`
                                : 'text-text-muted hover:text-text-secondary'
                            }`}
                    >
                        {btn.label}
                    </button>
                ))}
            </div>

            {/* Alert List */}
            <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
                {filtered.length === 0 ? (
                    <div className="flex items-center justify-center h-32 text-text-muted text-xs">
                        No alerts in this category
                    </div>
                ) : (
                    filtered.map((alert) => (
                        <AlertCard key={alert.id} alert={alert} />
                    ))
                )}
            </div>
        </div>
    );
}
