import { Settings as SettingsIcon, Bell, Shield, Monitor, Cpu } from 'lucide-react';
import { useState } from 'react';

const settingSections = [
    {
        icon: Monitor,
        title: 'Display',
        settings: [
            { id: 'dark-mode', label: 'Dark Mode', type: 'toggle', value: true },
            { id: 'animations', label: 'Enable Animations', type: 'toggle', value: true },
            { id: 'heatmap', label: 'Show Heatmap Overlay', type: 'toggle', value: true },
            { id: 'grid', label: 'Show Grid Lines', type: 'toggle', value: false },
        ],
    },
    {
        icon: Bell,
        title: 'Notifications',
        settings: [
            { id: 'sound', label: 'Alert Sound', type: 'toggle', value: true },
            { id: 'critical-only', label: 'Critical Alerts Only', type: 'toggle', value: false },
            { id: 'desktop-notif', label: 'Desktop Notifications', type: 'toggle', value: true },
            { id: 'email-alerts', label: 'Email Alerts', type: 'toggle', value: false },
        ],
    },
    {
        icon: Cpu,
        title: 'AI Engine',
        settings: [
            { id: 'auto-response', label: 'Automated Response', type: 'toggle', value: true },
            { id: 'prediction', label: 'Predictive Mode', type: 'toggle', value: true },
            { id: 'confidence-threshold', label: 'Confidence Threshold', type: 'range', value: 85 },
            { id: 'prediction-window', label: 'Prediction Window (min)', type: 'range', value: 15 },
        ],
    },
    {
        icon: Shield,
        title: 'Security',
        settings: [
            { id: '2fa', label: 'Two-Factor Authentication', type: 'toggle', value: true },
            { id: 'session-timeout', label: 'Session Timeout (min)', type: 'range', value: 30 },
            { id: 'audit-log', label: 'Audit Logging', type: 'toggle', value: true },
        ],
    },
];

export default function Settings() {
    const [settings, setSettings] = useState<Record<string, boolean | number>>(() => {
        const initial: Record<string, boolean | number> = {};
        settingSections.forEach(section =>
            section.settings.forEach(s => { initial[s.id] = s.value; })
        );
        return initial;
    });

    const toggleSetting = (id: string) => {
        setSettings(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const updateRange = (id: string, val: number) => {
        setSettings(prev => ({ ...prev, [id]: val }));
    };

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center gap-3 shrink-0">
                <div className="w-9 h-9 rounded-lg bg-text-muted/15 flex items-center justify-center">
                    <SettingsIcon size={18} className="text-text-secondary" />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-text-primary">Settings</h2>
                    <p className="text-xs text-text-muted">System configuration & preferences</p>
                </div>
            </div>

            {/* Settings Sections */}
            <div className="grid grid-cols-2 gap-4">
                {settingSections.map((section) => (
                    <div key={section.title} className="glass-card p-4">
                        <div className="flex items-center gap-2 mb-4">
                            <section.icon size={16} className="text-cyan" />
                            <h3 className="text-sm font-semibold text-text-primary">{section.title}</h3>
                        </div>
                        <div className="space-y-3">
                            {section.settings.map((setting) => (
                                <div key={setting.id} className="flex items-center justify-between">
                                    <span className="text-xs text-text-secondary">{setting.label}</span>
                                    {setting.type === 'toggle' ? (
                                        <button
                                            onClick={() => toggleSetting(setting.id)}
                                            className="w-10 h-5 rounded-full transition-colors cursor-pointer relative"
                                            style={{ backgroundColor: settings[setting.id] ? '#00C853' : '#1E293B' }}
                                        >
                                            <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-all ${settings[setting.id] ? 'left-5.5' : 'left-0.5'
                                                }`} />
                                        </button>
                                    ) : (
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="range"
                                                min={setting.id.includes('confidence') ? 50 : setting.id.includes('window') ? 5 : 5}
                                                max={setting.id.includes('confidence') ? 99 : setting.id.includes('window') ? 60 : 120}
                                                value={settings[setting.id] as number}
                                                onChange={(e) => updateRange(setting.id, parseInt(e.target.value))}
                                                className="w-24 accent-cyan"
                                            />
                                            <span className="text-xs text-cyan font-mono w-8 text-right">{settings[setting.id]}</span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {/* System Info */}
            <div className="glass-card p-4 shrink-0">
                <h3 className="text-sm font-semibold text-text-primary mb-3">System Information</h3>
                <div className="grid grid-cols-4 gap-4 text-xs">
                    {[
                        { label: 'Version', value: 'SENTINEL v2.4.1' },
                        { label: 'AI Model', value: 'YOLOv9-X + GPT-4 Vision' },
                        { label: 'Server', value: 'Node.js v20.11.0' },
                        { label: 'Database', value: 'MongoDB Atlas v7.0' },
                    ].map((info) => (
                        <div key={info.label}>
                            <span className="text-text-muted">{info.label}</span>
                            <div className="text-text-primary font-medium mt-0.5">{info.value}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
