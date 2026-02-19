import { ShieldAlert, Loader2 } from 'lucide-react';
import RiskCard from '../components/RiskCard';
import CrowdFlowVisualization from '../features/flow/CrowdFlowVisualization';
import { useState, useEffect } from 'react';
import type { RiskCardData } from '../types';
import { metricsApi } from '../services/api';

export default function RiskIntelligence() {
    const [riskCards, setRiskCards] = useState<RiskCardData[]>([]);
    const [overallRisk, setOverallRisk] = useState({ score: 0, level: 'LOW' });
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const data: any = await metricsApi.getLive();
                setOverallRisk({ score: data.risk_score, level: data.risk_level });

                // Map backend metrics to Risk Cards
                const cards: RiskCardData[] = [
                    {
                        id: 'stampede',
                        title: 'Stampede Risk',
                        severity: data.risk_level.toLowerCase() as any,
                        value: Math.round(data.risk_score * 100),
                        maxValue: 100,
                        recommendation: data.risk_score > 0.7 ? 'Open auxiliary gates to reduce directional pressure' : 'Continue monitoring — no immediate action required',
                        trend: Array.from({ length: 10 }, () => Math.random() * 20 + data.risk_score * 80),
                        zone: 'Primary Monitoring Zone',
                    },
                    {
                        id: 'chokepoint',
                        title: 'Choke Point Analysis',
                        severity: data.congestion_score > 0.8 ? 'critical' : data.congestion_score > 0.5 ? 'high' : 'medium',
                        value: Math.round(data.congestion_score * 100),
                        maxValue: 100,
                        recommendation: data.congestion_score > 0.6 ? 'Deploy crowd marshals to identified hotspots' : 'Normal flow maintained at known choke points',
                        trend: Array.from({ length: 10 }, () => Math.random() * 20 + data.congestion_score * 80),
                        zone: 'Primary Monitoring Zone',
                    },
                    {
                        id: 'anomaly',
                        title: 'Behaviour Anomaly',
                        severity: data.anomaly_score > 0.7 ? 'high' : 'low',
                        value: Math.round(data.anomaly_score * 100),
                        maxValue: 100,
                        recommendation: data.anomaly_score > 0.5 ? 'Investigate unusual group formation' : 'No significant behavioural anomalies detected',
                        trend: Array.from({ length: 10 }, () => Math.random() * 10 + data.anomaly_score * 90),
                        zone: 'Primary Monitoring Zone',
                    },
                    {
                        id: 'flow',
                        title: 'Flow Dynamics',
                        severity: data.avg_flow_magnitude > 5 ? 'high' : 'medium',
                        value: Math.min(100, Math.round(data.avg_flow_magnitude * 10)),
                        maxValue: 100,
                        recommendation: 'Monitor directional turbulence at intersections',
                        trend: Array.from({ length: 10 }, () => Math.random() * 30 + data.avg_flow_magnitude * 5),
                        zone: 'Primary Monitoring Zone',
                    }
                ];

                setRiskCards(cards);
                setIsLoading(false);
            } catch (error) {
                console.error('Failed to fetch metrics:', error);
            }
        };

        fetchMetrics();
        const interval = setInterval(fetchMetrics, 3000);
        return () => clearInterval(interval);
    }, []);

    const riskColor = overallRisk.level === 'CRITICAL' ? 'text-danger' :
        overallRisk.level === 'HIGH' ? 'text-danger' :
            overallRisk.level === 'MEDIUM' ? 'text-warning' : 'text-success';

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-danger/15 flex items-center justify-center">
                        <ShieldAlert size={18} className="text-danger" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Risk Intelligence</h2>
                        <p className="text-xs text-text-muted">AI-powered threat assessment, pressure analysis & prediction</p>
                    </div>
                </div>
                {isLoading && <Loader2 size={16} className="text-cyan animate-spin" />}
            </div>

            {/* Risk Overview Bar */}
            <div className="glass-card p-4 shrink-0">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-text-primary">Overall Threat Level</h3>
                    <span className={`text-xs font-bold px-3 py-1 rounded-full bg-bg-primary/50 border border-border ${riskColor}`}>
                        {overallRisk.level}
                    </span>
                </div>
                <div className="w-full h-2 rounded-full bg-bg-primary flex overflow-hidden">
                    <div className="h-full bg-success" style={{ width: `${Math.min(100, overallRisk.score < 0.25 ? overallRisk.score * 400 : 25)}%` }} />
                    <div className="h-full bg-warning" style={{ width: `${Math.max(0, Math.min(25, overallRisk.score >= 0.25 ? (overallRisk.score - 0.25) * 400 : 0))}%` }} />
                    <div className="h-full bg-danger" style={{ width: `${Math.max(0, Math.min(50, overallRisk.score >= 0.5 ? (overallRisk.score - 0.5) * 200 : 0))}%` }} />
                </div>
                <div className="flex justify-between mt-2 text-[10px] text-text-muted">
                    <span>Low</span>
                    <span>Medium</span>
                    <span>High</span>
                    <span>Critical</span>
                </div>
            </div>

            {/* Crowd Flow Visualization */}
            <div className="shrink-0">
                <CrowdFlowVisualization />
            </div>

            {/* Risk Cards Grid */}
            <div className="grid grid-cols-2 xl:grid-cols-2 gap-3 pb-4">
                {riskCards.map((card) => (
                    <RiskCard key={card.id} data={card} />
                ))}
            </div>
        </div>
    );
}
