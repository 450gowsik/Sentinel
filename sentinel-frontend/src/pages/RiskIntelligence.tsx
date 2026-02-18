import { ShieldAlert, MapPin } from 'lucide-react';
import RiskCard from '../components/RiskCard';
import CrowdFlowVisualization from '../features/flow/CrowdFlowVisualization';
import { generateRiskCards } from '../services/mockData';
import { useState, useEffect } from 'react';
import type { RiskCardData } from '../types';

export default function RiskIntelligence() {
    const [riskCards, setRiskCards] = useState<RiskCardData[]>([]);

    useEffect(() => {
        setRiskCards(generateRiskCards());
        const interval = setInterval(() => {
            setRiskCards(generateRiskCards());
        }, 10000);
        return () => clearInterval(interval);
    }, []);

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
            </div>

            {/* Risk Overview Bar */}
            <div className="glass-card p-4 shrink-0">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-text-primary">Overall Threat Level</h3>
                    <span className="text-xs text-warning font-bold px-3 py-1 rounded-full bg-warning/15">ELEVATED</span>
                </div>
                <div className="w-full h-2 rounded-full bg-bg-primary flex overflow-hidden">
                    <div className="h-full bg-success" style={{ width: '20%' }} />
                    <div className="h-full bg-warning" style={{ width: '35%' }} />
                    <div className="h-full bg-danger" style={{ width: '30%' }} />
                    <div className="h-full bg-bg-primary" style={{ width: '15%' }} />
                </div>
                <div className="flex justify-between mt-2 text-[10px] text-text-muted">
                    <span>Low (1 zone)</span>
                    <span>Medium (2 zones)</span>
                    <span>High (1 zone)</span>
                    <span>Critical (1 zone)</span>
                </div>
            </div>

            {/* Crowd Flow Visualization — from mind map */}
            <div className="shrink-0">
                <CrowdFlowVisualization />
            </div>

            {/* Zone Risk Map Placeholder */}
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
                    {/* Simulated zone markers */}
                    <div className="absolute top-[20%] left-[25%] w-16 h-16 rounded-full border-2 border-success/50 flex items-center justify-center text-[9px] text-success font-bold">A</div>
                    <div className="absolute top-[30%] left-[50%] w-20 h-20 rounded-full border-2 border-danger/50 flex items-center justify-center text-[9px] text-danger font-bold animate-pulse">B</div>
                    <div className="absolute top-[40%] left-[75%] w-14 h-14 rounded-full border-2 border-warning/50 flex items-center justify-center text-[9px] text-warning font-bold">C</div>
                    <div className="absolute top-[60%] left-[35%] w-18 h-18 rounded-full border-2 border-warning/50 flex items-center justify-center text-[9px] text-warning font-bold">D</div>
                    <div className="absolute top-[55%] left-[65%] w-16 h-16 rounded-full border-2 border-danger/50 flex items-center justify-center text-[9px] text-danger font-bold">E</div>
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
