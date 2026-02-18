import { BellRing, Download } from 'lucide-react';
import AlertStack from '../features/alerts/AlertStack';
import { useState } from 'react';

const automationRules = [
    { id: 1, name: 'Critical Density Auto-Gate', trigger: 'Density > 6 p/m²', action: 'Open auxiliary gates', status: 'active', triggered: 12 },
    { id: 2, name: 'Stampede Risk PA Announcement', trigger: 'Stampede Risk > 80', action: 'Automated PA broadcast', status: 'active', triggered: 3 },
    { id: 3, name: 'Choke Point Marshal Deploy', trigger: 'Choke Point > 70', action: 'Notify on-ground team', status: 'active', triggered: 8 },
    { id: 4, name: 'Night Mode Surveillance', trigger: 'Time 22:00-06:00', action: 'Switch to thermal cameras', status: 'paused', triggered: 0 },
    { id: 5, name: 'Emergency Lockdown', trigger: 'Risk Index > 95', action: 'Full lockdown protocol', status: 'active', triggered: 0 },
];

export default function AlertsAutomation() {
    const [activeTab, setActiveTab] = useState<'live' | 'rules'>('live');

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-danger/15 flex items-center justify-center">
                        <BellRing size={18} className="text-danger" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Alerts & Automation</h2>
                        <p className="text-xs text-text-muted">Real-time alert management & automated response rules</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-primary border border-border text-xs text-text-secondary hover:border-cyan/30 transition-colors cursor-pointer">
                        <Download size={12} />
                        Export
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 shrink-0">
                {[
                    { id: 'live' as const, label: 'Live Alerts' },
                    { id: 'rules' as const, label: 'Automation Rules' },
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer ${activeTab === tab.id
                            ? 'bg-cyan/10 text-cyan border border-cyan/20'
                            : 'text-text-muted hover:text-text-secondary'
                            }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            {activeTab === 'live' ? (
                <div className="flex-1 overflow-hidden">
                    <AlertStack />
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto">
                    <div className="glass-card overflow-hidden">
                        <div className="flex items-center justify-between p-3 border-b border-border">
                            <h3 className="text-sm font-semibold text-text-primary">Automation Rules</h3>
                            <button className="text-[11px] px-3 py-1.5 rounded-lg bg-cyan/10 text-cyan border border-cyan/20 font-medium cursor-pointer hover:bg-cyan/20 transition-colors">
                                + New Rule
                            </button>
                        </div>
                        <div className="divide-y divide-border">
                            {automationRules.map((rule) => (
                                <div key={rule.id} className="flex items-center justify-between p-4 hover:bg-bg-card-hover transition-colors">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-sm font-medium text-text-primary">{rule.name}</span>
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${rule.status === 'active' ? 'bg-success/15 text-success' : 'bg-text-muted/15 text-text-muted'
                                                }`}>
                                                {rule.status.toUpperCase()}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-[11px] text-text-muted">
                                            <span>Trigger: <span className="text-text-secondary">{rule.trigger}</span></span>
                                            <span>Action: <span className="text-text-secondary">{rule.action}</span></span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className="text-center">
                                            <div className="text-sm font-bold text-text-primary">{rule.triggered}</div>
                                            <div className="text-[10px] text-text-muted">Triggered</div>
                                        </div>
                                        <button className="w-10 h-5 rounded-full transition-colors cursor-pointer relative"
                                            style={{ backgroundColor: rule.status === 'active' ? '#00C853' : '#1E293B' }}
                                        >
                                            <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-all ${rule.status === 'active' ? 'left-5.5' : 'left-0.5'
                                                }`} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
