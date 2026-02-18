import { useState, useEffect } from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import { useAlertStore } from '../store/useAlertStore';
import { Bell, Cpu, MapPin, ChevronDown, Wifi, WifiOff } from 'lucide-react';

const locations = [
    'Mumbai Central Station',
    'Delhi Metro Hub',
    'Bangalore Tech Park',
    'Chennai Marina Zone',
    'Kolkata Howrah Bridge',
];

export default function TopBar() {
    const [time, setTime] = useState(new Date());
    const [locationOpen, setLocationOpen] = useState(false);
    const systemStatus = useDashboardStore((s) => s.systemStatus);
    const aiHealth = useDashboardStore((s) => s.aiEngineHealth);
    const activeLocation = useDashboardStore((s) => s.activeLocation);
    const setActiveLocation = useDashboardStore((s) => s.setActiveLocation);
    const unacknowledgedCount = useAlertStore((s) => s.unacknowledgedCount);

    useEffect(() => {
        const interval = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(interval);
    }, []);

    const statusColor =
        systemStatus === 'operational' ? 'bg-success' :
            systemStatus === 'degraded' ? 'bg-warning' : 'bg-danger';

    const statusLabel =
        systemStatus === 'operational' ? 'All Systems Operational' :
            systemStatus === 'degraded' ? 'Degraded Performance' : 'System Critical';

    return (
        <header className="h-14 bg-bg-secondary border-b border-border flex items-center justify-between px-5 z-50 relative">
            {/* Left Section */}
            <div className="flex items-center gap-6">
                {/* System Status */}
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${statusColor} pulse-dot`} />
                    <span className="text-xs text-text-secondary font-medium tracking-wide uppercase">
                        {statusLabel}
                    </span>
                </div>

                {/* AI Engine Health */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-primary/50 border border-border">
                    <Cpu size={14} className="text-cyan" />
                    <span className="text-xs font-semibold text-text-primary">{aiHealth}%</span>
                    <span className="text-xs text-text-muted">AI Engine</span>
                </div>
            </div>

            {/* Center — Location Selector */}
            <div className="relative">
                <button
                    onClick={() => setLocationOpen(!locationOpen)}
                    className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-bg-primary/50 border border-border hover:border-cyan/30 transition-colors cursor-pointer"
                >
                    <MapPin size={14} className="text-cyan" />
                    <span className="text-sm font-medium text-text-primary">{activeLocation}</span>
                    <ChevronDown size={14} className="text-text-muted" />
                </button>

                {locationOpen && (
                    <div className="absolute top-full mt-1 left-0 w-64 py-1 rounded-lg bg-bg-card border border-border shadow-xl z-50">
                        {locations.map((loc) => (
                            <button
                                key={loc}
                                onClick={() => { setActiveLocation(loc); setLocationOpen(false); }}
                                className={`w-full text-left px-4 py-2 text-sm hover:bg-bg-card-hover transition-colors cursor-pointer ${loc === activeLocation ? 'text-cyan' : 'text-text-secondary'
                                    }`}
                            >
                                {loc}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Right Section */}
            <div className="flex items-center gap-5">
                {/* Connection Status */}
                <div className="flex items-center gap-1.5">
                    {systemStatus !== 'critical' ? (
                        <Wifi size={14} className="text-success" />
                    ) : (
                        <WifiOff size={14} className="text-danger" />
                    )}
                    <span className="text-xs text-text-muted">Live</span>
                </div>

                {/* Live Timestamp */}
                <div className="text-xs font-mono text-text-secondary tracking-wider">
                    {time.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                    <span className="text-cyan mx-1.5">|</span>
                    {time.toLocaleTimeString('en-US', { hour12: false })}
                </div>

                {/* Notifications */}
                <button className="relative p-2 rounded-lg hover:bg-bg-primary/50 transition-colors cursor-pointer">
                    <Bell size={18} className="text-text-secondary" />
                    {unacknowledgedCount > 0 && (
                        <span className="absolute -top-0.5 -right-0.5 w-4.5 h-4.5 flex items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white">
                            {unacknowledgedCount > 9 ? '9+' : unacknowledgedCount}
                        </span>
                    )}
                </button>
            </div>
        </header>
    );
}
