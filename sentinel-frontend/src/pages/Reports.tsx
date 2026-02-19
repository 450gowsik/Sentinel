import { FileBarChart, Download, Calendar, Filter } from 'lucide-react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const weeklyData = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return {
        day: date.toLocaleDateString('en-US', { weekday: 'short' }),
        density: +(2 + Math.random() * 4).toFixed(1),
        alerts: Math.floor(Math.random() * 15),
        incidents: Math.floor(Math.random() * 3),
    };
});

const reportTemplates = [
    { id: 1, name: 'Daily Crowd Summary', description: 'Comprehensive daily overview of crowd metrics', lastGenerated: '2h ago', format: 'PDF' },
    { id: 2, name: 'Weekly Risk Assessment', description: 'Weekly analysis of risk patterns and predictions', lastGenerated: '1d ago', format: 'PDF' },
    { id: 3, name: 'Incident Report', description: 'Detailed incident analysis with timeline', lastGenerated: '3d ago', format: 'DOCX' },
    { id: 4, name: 'Sensor Health Report', description: 'Infrastructure uptime and maintenance needs', lastGenerated: '5h ago', format: 'CSV' },
    { id: 5, name: 'AI Performance Metrics', description: 'Model accuracy, latency, and prediction quality', lastGenerated: '12h ago', format: 'PDF' },
];

export default function Reports() {
    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-purple/15 flex items-center justify-center">
                        <FileBarChart size={18} className="text-purple" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Reports</h2>
                        <p className="text-xs text-text-muted">Generate & export analysis reports</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-primary border border-border text-xs text-text-secondary cursor-pointer hover:border-cyan/30 transition-colors">
                        <Calendar size={12} />
                        Date Range
                    </button>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-primary border border-border text-xs text-text-secondary cursor-pointer hover:border-cyan/30 transition-colors">
                        <Filter size={12} />
                        Filter
                    </button>
                </div>
            </div>

            {/* Weekly Overview Chart */}
            <div className="glass-card p-4 shrink-0">
                <h3 className="text-sm font-semibold text-text-primary mb-3">Weekly Overview</h3>
                <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={weeklyData}>
                            <defs>
                                <linearGradient id="densityGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#00E5FF" stopOpacity={0.3} />
                                    <stop offset="100%" stopColor="#00E5FF" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                            <XAxis dataKey="day" tick={{ fill: '#64748B', fontSize: 11 }} axisLine={{ stroke: '#1E293B' }} />
                            <YAxis tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#1E293B' }} />
                            <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #1E293B', borderRadius: '8px', fontSize: '11px', color: '#F1F5F9' }} />
                            <Area type="monotone" dataKey="density" stroke="#00E5FF" fill="url(#densityGrad)" strokeWidth={2} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Report Templates */}
            <div className="glass-card overflow-hidden shrink-0">
                <div className="p-3 border-b border-border">
                    <h3 className="text-sm font-semibold text-text-primary">Report Templates</h3>
                </div>
                <div className="divide-y divide-border">
                    {reportTemplates.map((report) => (
                        <div key={report.id} className="flex items-center justify-between p-4 hover:bg-bg-card-hover transition-colors">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-0.5">
                                    <span className="text-sm font-medium text-text-primary">{report.name}</span>
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-primary border border-border text-text-muted font-mono">
                                        {report.format}
                                    </span>
                                </div>
                                <p className="text-[11px] text-text-muted">{report.description}</p>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-[10px] text-text-muted">Last: {report.lastGenerated}</span>
                                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan/10 text-cyan text-[11px] font-medium border border-cyan/20 cursor-pointer hover:bg-cyan/20 transition-colors">
                                    <Download size={11} />
                                    Generate
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
