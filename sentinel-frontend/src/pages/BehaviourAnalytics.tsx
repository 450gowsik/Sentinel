import { Brain, Activity, Eye, Users, Loader2 } from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, RadarChart, Radar, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, LineChart, Line,
} from 'recharts';
import { useState, useEffect } from 'react';
import { useDashboardStore } from '../store/useDashboardStore';
import { analyticsApi } from '../services/api';

export default function BehaviourAnalytics() {
    const behaviourMetrics = useDashboardStore((s) => s.behaviourMetrics);
    const setBehaviourMetrics = useDashboardStore((s) => s.setBehaviourMetrics);
    const [isLoading, setIsLoading] = useState(!behaviourMetrics);

    useEffect(() => {
        const fetchBehaviour = async () => {
            try {
                const data: any = await analyticsApi.getBehaviour();
                setBehaviourMetrics(data);
                setIsLoading(false);
            } catch (error) {
                console.error('Failed to fetch behaviour metrics:', error);
            }
        };

        fetchBehaviour();
        const interval = setInterval(fetchBehaviour, 5000);
        return () => clearInterval(interval);
    }, []);

    if (isLoading && !behaviourMetrics) {
        return (
            <div className="h-full flex flex-col items-center justify-center gap-4 animate-fade-in text-text-muted">
                <Loader2 size={32} className="animate-spin text-purple" />
                <p className="text-sm font-medium">Synchronizing AI behavior telemetry...</p>
            </div>
        );
    }

    // Default fallbacks if metrics are somehow missing keys
    const stats = [
        { icon: Users, label: 'Tracked Entities', value: behaviourMetrics?.tracked_entities.toLocaleString() ?? '0', color: '#00E5FF' },
        { icon: Activity, label: 'Behaviour Events', value: behaviourMetrics?.behaviour_events.toLocaleString() ?? '0', color: '#7B61FF' },
        { icon: Eye, label: 'Anomalies Today', value: behaviourMetrics?.anomalies_today.toString() ?? '0', color: '#FF3D00' },
        { icon: Brain, label: 'AI Confidence', value: `${behaviourMetrics?.ai_confidence ?? 0}%`, color: '#00C853' },
    ];

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto pr-2">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-purple/15 flex items-center justify-center">
                        <Brain size={18} className="text-purple" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Behaviour Analytics</h2>
                        <p className="text-xs text-text-muted">AI-driven crowd behaviour pattern analysis & longitudinal mapping</p>
                    </div>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-purple">
                    <span className="w-2 h-2 rounded-full bg-purple animate-pulse" />
                    TELEMETRY ACTIVE
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-3 shrink-0">
                {stats.map((card, i) => (
                    <div key={i} className="glass-card p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <card.icon size={16} style={{ color: card.color }} />
                            <span className="text-xs text-text-muted">{card.label}</span>
                        </div>
                        <div className="text-xl font-bold text-text-primary">{card.value}</div>
                    </div>
                ))}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-2 gap-4 shrink-0">
                {/* Behaviour Distribution */}
                <div className="glass-card p-4">
                    <h3 className="text-sm font-semibold text-text-primary mb-3">Behaviour Distribution</h3>
                    <div className="h-56">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={behaviourMetrics?.distribution} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" horizontal={false} />
                                <XAxis type="number" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} />
                                <YAxis type="category" dataKey="name" tick={{ fill: '#94A3B8', fontSize: 10 }} width={100} axisLine={false} tickLine={false} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    contentStyle={{ backgroundColor: '#111827', border: '1px solid #1E293B', borderRadius: '8px', fontSize: '11px', color: '#F1F5F9' }}
                                />
                                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                                    {behaviourMetrics?.distribution.map((entry, index) => (
                                        <rect key={index} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Behaviour Radar */}
                <div className="glass-card p-4">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-text-primary">Pattern Analysis Radar</h3>
                        <div className="flex gap-3 text-[9px] font-medium">
                            <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-cyan" /> LIVE</div>
                            <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-purple" /> BASELINE</div>
                        </div>
                    </div>
                    <div className="h-56 flex items-center justify-center">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart data={behaviourMetrics?.radar}>
                                <PolarGrid stroke="#1E293B" />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94A3B8', fontSize: 10 }} />
                                <PolarRadiusAxis domain={[0, 100]} axisLine={false} tick={false} />
                                <Radar name="Live" dataKey="A" stroke="#00E5FF" fill="#00E5FF" fillOpacity={0.15} />
                                <Radar name="Baseline" dataKey="B" stroke="#7B61FF" fill="#7B61FF" fillOpacity={0.05} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111827', border: '1px solid #1E293B', borderRadius: '8px', fontSize: '11px', color: '#F1F5F9' }}
                                />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Anomaly Timeline */}
            <div className="glass-card p-4 shrink-0 mb-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3">24-Hour Anomaly Timeline</h3>
                <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={behaviourMetrics?.timeline}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                            <XAxis dataKey="hour" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} interval={2} />
                            <YAxis tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} />
                            <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #1E293B', borderRadius: '8px', fontSize: '11px', color: '#F1F5F9' }} />
                            <Line type="monotone" dataKey="anomalies" stroke="#FF3D00" strokeWidth={2} dot={{ r: 2, fill: '#FF3D00' }} activeDot={{ r: 4 }} />
                            <Line type="monotone" dataKey="normal" stroke="#00C853" strokeWidth={1.5} dot={false} strokeOpacity={0.3} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
