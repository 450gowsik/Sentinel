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
}

// Zone data for pressure field visualization
export interface ZoneData {
    id: string;
    name: string;
    x: number;
    y: number;
    pressure: number;
    direction: number;
    risk: 'low' | 'medium' | 'high' | 'critical';
}

// Collision point data
export interface CollisionPoint {
    x: number;
    y: number;
    force: number;
    label: string;
}

// Flow vector data
export interface FlowVector {
    x: number;
    y: number;
    angle: number;
    magnitude: number;
}

// Extended pipeline data from backend
export interface PipelineData {
    zones: ZoneData[];
    collisionPoints: CollisionPoint[];
    flowVectors: FlowVector[];
    avgPressure: number;
    maxForce: number;
    flowStability: number;
}

// Behaviour analytics data
export interface BehaviourType {
    name: string;
    count: number;
    color: string;
}

export interface PatternRadarPoint {
    subject: string;
    current: number;
    baseline: number;
}

export interface TimelinePoint {
    hour: string;
    anomalies: number;
    normal: number;
}

export interface BehaviourData {
    trackedEntities: number;
    behaviourEvents: number;
    anomaliesToday: number;
    aiConfidence: number;
    behaviourTypes: BehaviourType[];
    radarData: PatternRadarPoint[];
    timelineData: TimelinePoint[];
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
    
    // Pipeline visualization data
    pipelineData: PipelineData | null;
    
    // Behaviour analytics data
    behaviourData: BehaviourData | null;

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
    setPipelineData: (data: PipelineData) => void;
    setBehaviourData: (data: BehaviourData) => void;
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
    
    // Pipeline visualization data
    pipelineData: null,
    
    // Behaviour analytics data
    behaviourData: null,

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
    setPipelineData: (data) => set({ pipelineData: data }),
    setBehaviourData: (data) => set({ behaviourData: data }),
}));
