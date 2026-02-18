import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    Area,
    ComposedChart,
    Line,
} from 'recharts';
import { useDashboardStore } from '../store/useDashboardStore';
import MetricCard from '../components/MetricCard';
import LiveFeedContainer from '../components/LiveFeedContainer';
import AIRecommendationPanel from '../components/AIRecommendationPanel';
import PipelineFlow from '../features/pipeline/PipelineFlow';
import AlertStack from '../features/alerts/AlertStack';
import PressureFieldEstimation from '../features/pressure/PressureFieldEstimation';
import CrowdFlowVisualization from '../features/flow/CrowdFlowVisualization';
import { Activity } from 'lucide-react';

export default function Dashboard() {
    const metrics = useDashboardStore((s) => s.metrics);
    const chartData = useDashboardStore((s) => s.chartData);

    return (
        <div className="h-full flex gap-4 animate-fade-in">
            {/* Main Content */}
            <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-1">
                {/* Metrics Row */}
                <div className="grid grid-cols-4 gap-3 shrink-0">
                    {metrics.map((metric, i) => (
                        <MetricCard key={i} metric={metric} />
                    ))}
                </div>

                {/* Live Feed */}
                <div className="shrink-0">
                    <LiveFeedContainer />
                </div>

                {/* Predictive Trend Chart */}
                <div className="glass-card p-4 shrink-0">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <Activity size={14} className="text-cyan" />
                            <h3 className="text-sm font-semibold text-text-primary">Crowd Density — Predictive Trend</h3>
                        </div>
                        <div className="flex items-center gap-3 text-[10px]">
                            <span className="flex items-center gap-1">
                                <span className="w-3 h-0.5 bg-cyan rounded" />
                                <span className="text-text-muted">Actual</span>
                            </span>
                            <span className="flex items-center gap-1">
                                <span className="w-3 h-0.5 bg-purple rounded" />
                                <span className="text-text-muted">Predicted</span>
                            </span>
                            <span className="flex items-center gap-1">
                                <span className="w-3 h-0.5 bg-danger rounded" />
                                <span className="text-text-muted">Threshold</span>
                            </span>
                        </div>
                    </div>
                    <div className="h-52">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={chartData}>
                                <defs>
                                    <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#00E5FF" stopOpacity={0.2} />
                                        <stop offset="100%" stopColor="#00E5FF" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                                <XAxis
                                    dataKey="time"
                                    tick={{ fill: '#64748B', fontSize: 10 }}
                                    axisLine={{ stroke: '#1E293B' }}
                                    tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: '#64748B', fontSize: 10 }}
                                    axisLine={{ stroke: '#1E293B' }}
                                    tickLine={false}
                                    domain={[0, 8]}
                                    label={{ value: 'persons/m²', angle: -90, position: 'insideLeft', fill: '#64748B', fontSize: 10 }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: '#111827',
                                        border: '1px solid #1E293B',
                                        borderRadius: '8px',
                                        fontSize: '11px',
                                        color: '#F1F5F9',
                                    }}
                                />
                                <ReferenceLine y={6} stroke="#FF3D00" strokeDasharray="5 5" strokeOpacity={0.5} />
                                <Area type="monotone" dataKey="actual" fill="url(#actualGrad)" stroke="transparent" />
                                <Line type="monotone" dataKey="actual" stroke="#00E5FF" strokeWidth={2} dot={false} />
                                <Line type="monotone" dataKey="predicted" stroke="#7B61FF" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Pressure Field Estimation — from mind map */}
                <div className="shrink-0">
                    <PressureFieldEstimation />
                </div>

                {/* Crowd Flow Visualization — from mind map */}
                <div className="shrink-0">
                    <CrowdFlowVisualization />
                </div>

                {/* Pipeline */}
                <div className="shrink-0">
                    <PipelineFlow />
                </div>

                {/* AI Recommendations */}
                <div className="shrink-0">
                    <AIRecommendationPanel />
                </div>
            </div>

            {/* Alert Stack (Right Sidebar) */}
            <div className="w-[320px] shrink-0 h-full">
                <AlertStack />
            </div>
        </div>
    );
}
