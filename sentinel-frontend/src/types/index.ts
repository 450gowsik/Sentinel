export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface Alert {
    id: string;
    type: AlertSeverity;
    title: string;
    message: string;
    zone: string;
    timestamp: string;
    acknowledged: boolean;
    recommendedAction: string;
}

export interface MetricData {
    label: string;
    value: number | string;
    unit: string;
    trend: 'up' | 'down' | 'stable';
    trendValue: string;
    icon: string;
    color: string;
}

export interface PipelineStage {
    id: string;
    name: string;
    status: 'active' | 'processing' | 'idle' | 'error';
    latency: number;
    confidence: number;
}

export interface CrowdDensityUpdate {
    zoneId: string;
    zoneName: string;
    density: number;
    timestamp: string;
    trend: 'increasing' | 'decreasing' | 'stable';
}

export interface RiskPrediction {
    zoneId: string;
    zoneName: string;
    riskScore: number;
    riskLevel: 'low' | 'medium' | 'high' | 'critical';
    predictionWindow: string;
    confidence: number;
    factors: string[];
}

export interface AnomalyEvent {
    id: string;
    type: string;
    description: string;
    severity: AlertSeverity;
    zone: string;
    timestamp: string;
    confidence: number;
}

export interface Zone {
    id: string;
    name: string;
    capacity: number;
    currentOccupancy: number;
    status: 'normal' | 'caution' | 'danger';
    cameras: number;
    sensors: number;
}

export interface SensorStatus {
    id: string;
    name: string;
    type: 'camera' | 'lidar' | 'pressure' | 'thermal';
    status: 'online' | 'offline' | 'degraded';
    zone: string;
    lastUpdate: string;
    uptime: number;
}

export interface RiskCardData {
    id: string;
    title: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    value: number;
    maxValue: number;
    recommendation: string;
    trend: number[];
    zone: string;
}

export interface ChartDataPoint {
    time: string;
    actual: number;
    predicted: number;
    threshold?: number;
}
