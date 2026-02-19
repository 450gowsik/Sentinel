import { ShieldAlert, MapPin, Radio } from 'lucide-react';
import RiskCard from '../components/RiskCard';
import CrowdFlowVisualization from '../features/flow/CrowdFlowVisualization';
import { useDashboardStore } from '../store/useDashboardStore';
import { useMemo } from 'react';
import type { RiskCardData } from '../types';

// Zone position mapping for Zone Risk Map (using short IDs from backend: A, B, C, D, E)
const zoneMapPositions: Record<string, { top: string; left: string; size: string }> = {
    'A': { top: '20%', left: '25%', size: 'w-16 h-16' },
    'B': { top: '30%', left: '50%', size: 'w-20 h-20' },
    'C': { top: '40%', left: '75%', size: 'w-14 h-14' },
    'D': { top: '60%', left: '35%', size: 'w-18 h-18' },
    'E': { top: '55%', left: '65%', size: 'w-16 h-16' },
};

// Status config for colors
const statusConfig = {
    low: { color: 'success', border: 'border-success/50', text: 'text-success' },
    medium: { color: 'warning', border: 'border-warning/50', text: 'text-warning' },
    high: { color: 'danger', border: 'border-danger/50', text: 'text-danger' },
    critical: { color: 'danger', border: 'border-danger/50', text: 'text-danger' },
};

function getStatusFromPressure(pressure: number): 'low' | 'medium' | 'high' | 'critical' {
    if (pressure >= 0.8) return 'critical';
    if (pressure >= 0.6) return 'high';
    if (pressure >= 0.35) return 'medium';
    return 'low';
}

export default function RiskIntelligence() {
    const pipelineData = useDashboardStore((s) => s.pipelineData);
    const isLive = !!pipelineData;

    // Calculate threat level distribution from zones
    const threatDistribution = useMemo(() => {
        const defaultCounts = { low: 0, medium: 0, high: 0, critical: 0 };
        if (!pipelineData?.zones) {
            return { low: 100, medium: 0, high: 0, critical: 0, label: 'NORMAL', labelClass: 'text-success bg-success/15', counts: defaultCounts };
        }
        const counts = { low: 0, medium: 0, high: 0, critical: 0 };
        pipelineData.zones.forEach((z) => {
            const status = getStatusFromPressure(z.pressure);
            counts[status]++;
        });
        const total = pipelineData.zones.length || 1;
        const percentages = {
            low: Math.round((counts.low / total) * 100),
            medium: Math.round((counts.medium / total) * 100),
            high: Math.round((counts.high / total) * 100),
            critical: Math.round((counts.critical / total) * 100),
        };

        // Determine overall label
        let label = 'NORMAL';
        let labelClass = 'text-success bg-success/15';
        if (counts.critical > 0) {
            label = 'CRITICAL';
            labelClass = 'text-danger bg-danger/15';
        } else if (counts.high > 0) {
            label = 'HIGH';
            labelClass = 'text-danger bg-danger/15';
        } else if (counts.medium > 0) {
            label = 'ELEVATED';
            labelClass = 'text-warning bg-warning/15';
        }
        return { ...percentages, label, labelClass, counts };
    }, [pipelineData]);

    // Generate RiskCards from real pipeline data
    const riskCards = useMemo<RiskCardData[]>(() => {
        if (!pipelineData) {
            return [
                { id: 'r1', title: 'Crowd Density', severity: 'low' as const, value: 0, maxValue: 10, recommendation: 'Awaiting data', trend: [0], zone: 'All' },
                { id: 'r2', title: 'Avg Pressure', severity: 'low' as const, value: 0, maxValue: 100, recommendation: 'Awaiting data', trend: [0], zone: 'All' },
                { id: 'r3', title: 'Max Force', severity: 'low' as const, value: 0, maxValue: 10, recommendation: 'Awaiting data', trend: [0], zone: 'All' },
                { id: 'r4', title: 'Flow Stability', severity: 'low' as const, value: 0, maxValue: 100, recommendation: 'Awaiting data', trend: [0], zone: 'All' },
                { id: 'r5', title: 'Collision Risk', severity: 'low' as const, value: 0, maxValue: 10, recommendation: 'Awaiting data', trend: [0], zone: 'All' },
                { id: 'r6', title: 'Active Zones', severity: 'low' as const, value: 0, maxValue: 10, recommendation: 'Awaiting data', trend: [0], zone: 'All' },
            ];
        }

        const avgPressure = pipelineData.avgPressure || 0;
        const maxForce = pipelineData.maxForce || 0;
        const flowStability = pipelineData.flowStability || 0;
        const collisions = pipelineData.collisionPoints?.length || 0;
        const zones = pipelineData.zones?.length || 0;

        // Calculate density from zones
        const avgDensity = pipelineData.zones?.reduce((sum, z) => sum + z.pressure * 7, 0) / (zones || 1);

        const getSeverity = (val: number, thresholds: [number, number]): 'low' | 'medium' | 'high' | 'critical' => {
            if (val >= thresholds[1]) return 'critical';
            if (val >= thresholds[0]) return 'high';
            if (val >= thresholds[0] * 0.5) return 'medium';
            return 'low';
        };

        return [
            {
                id: 'r1',
                title: 'Crowd Density',
                severity: getSeverity(avgDensity, [3, 5]),
                value: avgDensity,
                maxValue: 10,
                recommendation: avgDensity > 5 ? 'Open additional exits' : avgDensity > 3 ? 'Monitor closely' : 'Status normal',
                trend: [avgDensity * 0.8, avgDensity * 0.9, avgDensity],
                zone: 'All Zones',
            },
            {
                id: 'r2',
                title: 'Avg Pressure',
                severity: getSeverity(avgPressure, [0.4, 0.7]),
                value: avgPressure * 100,
                maxValue: 100,
                recommendation: avgPressure > 0.7 ? 'Critical - take action' : avgPressure > 0.4 ? 'Elevated pressure' : 'Normal pressure',
                trend: [avgPressure * 80, avgPressure * 90, avgPressure * 100],
                zone: 'All Zones',
            },
            {
                id: 'r3',
                title: 'Max Force',
                severity: getSeverity(maxForce, [2, 4]),
                value: maxForce,
                maxValue: 10,
                recommendation: maxForce > 4 ? 'High force detected' : maxForce > 2 ? 'Moderate force' : 'Normal force levels',
                trend: [maxForce * 0.7, maxForce * 0.85, maxForce],
                zone: 'Peak Zone',
            },
            {
                id: 'r4',
                title: 'Flow Stability',
                severity: flowStability < 0.3 ? 'critical' : flowStability < 0.5 ? 'high' : flowStability < 0.7 ? 'medium' : 'low',
                value: flowStability * 100,
                maxValue: 100,
                recommendation: flowStability < 0.5 ? 'Unstable flow detected' : flowStability < 0.7 ? 'Monitor flow' : 'Stable flow',
                trend: [flowStability * 95, flowStability * 98, flowStability * 100],
                zone: 'All Zones',
            },
            {
                id: 'r5',
                title: 'Collision Risk',
                severity: getSeverity(collisions, [3, 7]),
                value: collisions,
                maxValue: 10,
                recommendation: collisions > 7 ? 'High collision risk' : collisions > 3 ? 'Moderate risk' : 'Low collision risk',
                trend: [Math.max(0, collisions - 2), Math.max(0, collisions - 1), collisions],
                zone: 'Hotspots',
            },
            {
                id: 'r6',
                title: 'Active Zones',
                severity: zones > 7 ? 'high' : zones > 4 ? 'medium' : 'low',
                value: zones,
                maxValue: 10,
                recommendation: `${zones} zones being monitored`,
                trend: [zones, zones, zones],
                zone: 'System',
            },
        ];
    }, [pipelineData]);

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
                {/* Live indicator */}
                <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${isLive ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}`}>
                    <Radio size={10} className={isLive ? 'animate-pulse' : ''} />
                    {isLive ? 'LIVE DATA' : 'WAITING'}
                </div>
            </div>

            {/* Risk Overview Bar - Uses real data */}
            <div className="glass-card p-4 shrink-0">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-text-primary">Overall Threat Level</h3>
                    <span className={`text-xs font-bold px-3 py-1 rounded-full ${threatDistribution.labelClass}`}>
                        {threatDistribution.label}
                    </span>
                </div>
                <div className="w-full h-2 rounded-full bg-bg-primary flex overflow-hidden">
                    <div className="h-full bg-success transition-all duration-500" style={{ width: `${threatDistribution.low}%` }} />
                    <div className="h-full bg-warning transition-all duration-500" style={{ width: `${threatDistribution.medium}%` }} />
                    <div className="h-full bg-orange-500 transition-all duration-500" style={{ width: `${threatDistribution.high}%` }} />
                    <div className="h-full bg-danger transition-all duration-500" style={{ width: `${threatDistribution.critical}%` }} />
                </div>
                <div className="flex justify-between mt-2 text-[10px] text-text-muted">
                    <span>Low ({threatDistribution.counts?.low || 0} zones)</span>
                    <span>Medium ({threatDistribution.counts?.medium || 0} zones)</span>
                    <span>High ({threatDistribution.counts?.high || 0} zones)</span>
                    <span>Critical ({threatDistribution.counts?.critical || 0} zones)</span>
                </div>
            </div>

            {/* Crowd Flow Visualization — from mind map */}
            <div className="shrink-0">
                <CrowdFlowVisualization />
            </div>

            {/* Zone Risk Map - Real data */}
            <div className="glass-card p-4 shrink-0">
                <div className="flex items-center gap-2 mb-3">
                    <MapPin size={14} className="text-cyan" />
                    <h3 className="text-sm font-semibold text-text-primary">Zone Risk Map</h3>
                </div>
                <div className="h-40 rounded-lg bg-bg-primary border border-border flex items-center justify-center relative overflow-hidden">
                    <div className="absolute inset-0 opacity-10"
                        style={{
                            backgroundImage: 'linear-gradient(rgba(0,229,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.3) 1px, transparent 1px)',
                            backgroundSize: '20px 20px',
                        }}
                    />
                    {/* Dynamic zone markers from pipeline data */}
                    {pipelineData?.zones?.map((zone) => {
                        const pos = zoneMapPositions[zone.id] || { top: '50%', left: '50%', size: 'w-16 h-16' };
                        const status = getStatusFromPressure(zone.pressure);
                        const cfg = statusConfig[status];
                        const isPulsing = status === 'critical' || status === 'high';
                        return (
                            <div
                                key={zone.id}
                                className={`absolute ${pos.size} rounded-full ${cfg.border} border-2 flex flex-col items-center justify-center ${isPulsing ? 'animate-pulse' : ''}`}
                                style={{ top: pos.top, left: pos.left, transform: 'translate(-50%, -50%)' }}
                            >
                                <span className={`text-[10px] ${cfg.text} font-bold`}>{zone.id}</span>
                                <span className={`text-[8px] ${cfg.text}`}>{(zone.pressure * 100).toFixed(0)}%</span>
                            </div>
                        );
                    }) || (
                        <span className="text-text-muted text-sm">No zone data</span>
                    )}
                </div>
            </div>

            {/* Risk Cards Grid */}
            <div className="grid grid-cols-2 xl:grid-cols-3 gap-3 pb-4">
                {riskCards.map((card) => (
                    <RiskCard key={card.id} data={card} />
                ))}
            </div>
        </div>
    );
}
