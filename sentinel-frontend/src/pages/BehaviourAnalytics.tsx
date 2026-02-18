import { Brain, Activity, Eye, Users } from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, RadarChart, Radar, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, LineChart, Line,
} from 'recharts';

const behaviourTypes = [
    { name: 'Normal Flow', count: 1247, color: '#00C853' },
    { name: 'Counter Flow', count: 89, color: '#FFB300' },
    { name: 'Clustering', count: 34, color: '#FF3D00' },
    { name: 'Dispersal', count: 156, color: '#00E5FF' },
    { name: 'Queue Formation', count: 203, color: '#7B61FF' },
    { name: 'Anomalous', count: 12, color: '#FF3D00' },
];

const radarData = [
    { subject: 'Speed', A: 75, B: 60 },
    { subject: 'Density', A: 85, B: 70 },
    { subject: 'Direction', A: 60, B: 50 },
    { subject: 'Grouping', A: 45, B: 80 },
    { subject: 'Spacing', A: 70, B: 55 },
    { subject: 'Flow Rate', A: 80, B: 65 },
];

const timelineData = Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(i).padStart(2, '0')}:00`,
    anomalies: Math.floor(Math.random() * 15),
    normal: 50 + Math.floor(Math.random() * 50),
}));

export default function BehaviourAnalytics() {
    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center gap-3 shrink-0">
                <div className="w-9 h-9 rounded-lg bg-purple/15 flex items-center justify-center">
                    <Brain size={18} className="text-purple" />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-text-primary">Behaviour Analytics</h2>
                    <p className="text-xs text-text-muted">AI-driven crowd behaviour pattern analysis</p>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-3 shrink-0">
                {[
                    { icon: Users, label: 'Tracked Entities', value: '1,741', color: '#00E5FF' },
                    { icon: Activity, label: 'Behaviour Events', value: '3,892', color: '#7B61FF' },
                    { icon: Eye, label: 'Anomalies Today', value: '12', color: '#FF3D00' },
                    { icon: Brain, label: 'AI Confidence', value: '94.2%', color: '#00C853' },
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
                                <Radar name="Zone A" dataKey="A" stroke="#00E5FF" fill="#00E5FF" fillOpacity={0.15} />
                                <Radar name="Zone B" dataKey="B" stroke="#7B61FF" fill="#7B61FF" fillOpacity={0.15} />
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
