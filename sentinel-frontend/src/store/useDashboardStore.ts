import { create } from 'zustand';
import type { MetricData, ChartDataPoint, CrowdDensityUpdate, RiskPrediction } from '../types';

// Live metrics from the backend pipeline
interface LiveMetrics {
    fps: number;
    latencyMs: number;
    personCount: number;
    riskScore: number;
    riskLevel: string;
    density: number;
    congestion: number;
    anomaly: number;
    flowMagnitude: number;
    trackCount: number;
    pressure?: number;
    collisions?: Array<{ x: number, y: number, force: number, label: string }>;
}

interface BehaviourMetrics {
    tracked_entities: number;
    behaviour_events: number;
    anomalies_today: number;
    ai_confidence: number;
    distribution: Array<{ name: string; count: number; color: string }>;
    radar: Array<{ subject: string; A: number; B: number }>;
    timeline: Array<{ hour: string; anomalies: number; normal: number }>;
}

interface DashboardStore {
    metrics: MetricData[];
    chartData: ChartDataPoint[];
    crowdDensity: CrowdDensityUpdate | null;
    riskPrediction: RiskPrediction | null;
    systemStatus: 'operational' | 'degraded' | 'critical';
    aiEngineHealth: number;
    activeLocation: string;

    // Live backend fields
    liveFrame: string | null;
    backendConnected: boolean;
    backendCameraActive: boolean;
    liveMetrics: LiveMetrics | null;
    behaviourMetrics: BehaviourMetrics | null;

    // Actions
    setMetrics: (metrics: MetricData[]) => void;
    addChartPoint: (point: ChartDataPoint) => void;
    setCrowdDensity: (data: CrowdDensityUpdate) => void;
    setRiskPrediction: (data: RiskPrediction) => void;
    setSystemStatus: (status: 'operational' | 'degraded' | 'critical') => void;
    setAiEngineHealth: (health: number) => void;
    setActiveLocation: (location: string) => void;
    setLiveFrame: (frame: string | null) => void;
    setBackendConnected: (connected: boolean) => void;
    setBackendCameraActive: (active: boolean) => void;
    setLiveMetrics: (metrics: LiveMetrics) => void;
    setBehaviourMetrics: (metrics: BehaviourMetrics) => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
    metrics: [],
    chartData: [],
    crowdDensity: null,
    riskPrediction: null,
    systemStatus: 'operational',
    aiEngineHealth: 98.7,
    activeLocation: 'Mumbai Central Station',

    // Live backend fields
    liveFrame: null,
    backendConnected: false,
    backendCameraActive: true,
    liveMetrics: null,
    behaviourMetrics: null,

    // Actions
    setMetrics: (metrics) => set({ metrics }),
    addChartPoint: (point) =>
        set((state) => ({
            chartData: [...state.chartData, point].slice(-30),
        })),
    setCrowdDensity: (data) => set({ crowdDensity: data }),
    setRiskPrediction: (data) => set({ riskPrediction: data }),
    setSystemStatus: (status) => set({ systemStatus: status }),
    setAiEngineHealth: (health) => set({ aiEngineHealth: health }),
    setActiveLocation: (location) => set({ activeLocation: location }),
    setLiveFrame: (frame) => set({ liveFrame: frame }),
    setBackendConnected: (connected) => set({ backendConnected: connected }),
    setBackendCameraActive: (active) => set({ backendCameraActive: active }),
    setLiveMetrics: (metrics) => set({ liveMetrics: metrics }),
    setBehaviourMetrics: (metrics) => set({ behaviourMetrics: metrics }),
}));
