import { Brain, Activity, Eye, Users, Radio } from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, RadarChart, Radar, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, LineChart, Line,
} from 'recharts';
import { useDashboardStore } from '../store/useDashboardStore';
import { useMemo } from 'react';

// Default values when no data available
const defaultBehaviourTypes = [
    { name: 'Normal Flow', count: 0, color: '#00C853' },
    { name: 'Counter Flow', count: 0, color: '#FFB300' },
    { name: 'Clustering', count: 0, color: '#FF3D00' },
    { name: 'Dispersal', count: 0, color: '#00E5FF' },
    { name: 'Queue Formation', count: 0, color: '#7B61FF' },
    { name: 'Anomalous', count: 0, color: '#FF3D00' },
];

const defaultRadarData = [
    { subject: 'Speed', current: 0, baseline: 60 },
    { subject: 'Density', current: 0, baseline: 50 },
    { subject: 'Direction', current: 0, baseline: 55 },
    { subject: 'Grouping', current: 0, baseline: 45 },
    { subject: 'Spacing', current: 0, baseline: 65 },
    { subject: 'Flow Rate', current: 0, baseline: 60 },
];

export default function BehaviourAnalytics() {
    const behaviourData = useDashboardStore((s) => s.behaviourData);
    const isLive = !!behaviourData;
    
    // Use real data or defaults
    const behaviourTypes = useMemo(() => {
        return behaviourData?.behaviourTypes || defaultBehaviourTypes;
    }, [behaviourData]);
    
    const radarData = useMemo(() => {
        return behaviourData?.radarData || defaultRadarData;
    }, [behaviourData]);
    
    const timelineData = useMemo(() => {
        if (!behaviourData?.timelineData?.length) {
            // Generate placeholder hourly data
            return Array.from({ length: 24 }, (_, i) => ({
                hour: `${String(i).padStart(2, '0')}:00`,
                anomalies: 0,
                normal: 0,
            }));
        }
        return behaviourData.timelineData;
    }, [behaviourData]);
    
    // Summary card values
    const trackedEntities = behaviourData?.trackedEntities?.toLocaleString() || '0';
    const behaviourEvents = behaviourData?.behaviourEvents?.toLocaleString() || '0';
    const anomaliesToday = behaviourData?.anomaliesToday?.toString() || '0';
    const aiConfidence = behaviourData?.aiConfidence ? `${behaviourData.aiConfidence}%` : '0%';
    
    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-purple/15 flex items-center justify-center">
                        <Brain size={18} className="text-purple" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Behaviour Analytics</h2>
                        <p className="text-xs text-text-muted">AI-driven crowd behaviour pattern analysis</p>
                    </div>
                </div>
                {/* Live indicator */}
                <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${isLive ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}`}>
                    <Radio size={10} className={isLive ? 'animate-pulse' : ''} />
                    {isLive ? 'LIVE DATA' : 'WAITING'}
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-3 shrink-0">
                {[
                    { icon: Users, label: 'Tracked Entities', value: trackedEntities, color: '#00E5FF' },
                    { icon: Activity, label: 'Behaviour Events', value: behaviourEvents, color: '#7B61FF' },
                    { icon: Eye, label: 'Anomalies Today', value: anomaliesToday, color: '#FF3D00' },
                    { icon: Brain, label: 'AI Confidence', value: aiConfidence, color: '#00C853' },
                ].map((card, i) => (
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
                            <BarChart data={behaviourTypes} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                                <XAxis type="number" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} />
                                <YAxis type="category" dataKey="name" tick={{ fill: '#94A3B8', fontSize: 10 }} width={100} axisLine={false} tickLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111827', border: '1px solid #1E293B', borderRadius: '8px', fontSize: '11px', color: '#F1F5F9' }}
                                />
                                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                                    {behaviourTypes.map((entry, index) => (
                                        <rect key={index} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Behaviour Radar */}
                <div className="glass-card p-4">
                    <h3 className="text-sm font-semibold text-text-primary mb-3">Pattern Analysis Radar</h3>
                    <div className="h-56 flex items-center justify-center">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart data={radarData}>
                                <PolarGrid stroke="#1E293B" />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94A3B8', fontSize: 10 }} />
                                <PolarRadiusAxis tick={{ fill: '#64748B', fontSize: 9 }} domain={[0, 100]} />
                                <Radar name="Current" dataKey="current" stroke="#00E5FF" fill="#00E5FF" fillOpacity={0.15} />
                                <Radar name="Baseline" dataKey="baseline" stroke="#7B61FF" fill="#7B61FF" fillOpacity={0.15} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Anomaly Timeline */}
            <div className="glass-card p-4 shrink-0">
                <h3 className="text-sm font-semibold text-text-primary mb-3">24-Hour Anomaly Timeline</h3>
                <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={timelineData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                            <XAxis dataKey="hour" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} interval={2} />
                            <YAxis tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} />
                            <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #1E293B', borderRadius: '8px', fontSize: '11px', color: '#F1F5F9' }} />
                            <Line type="monotone" dataKey="anomalies" stroke="#FF3D00" strokeWidth={2} dot={false} />
                            <Line type="monotone" dataKey="normal" stroke="#00C853" strokeWidth={1.5} dot={false} strokeOpacity={0.5} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
