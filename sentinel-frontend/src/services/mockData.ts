import type {
    Alert,
    MetricData,
    PipelineStage,
    RiskCardData,
    ChartDataPoint,
    CrowdDensityUpdate,
    RiskPrediction,
    Zone,
    SensorStatus,
} from '../types';

const zones = ['Zone A - Main Gate', 'Zone B - Central Plaza', 'Zone C - East Wing', 'Zone D - Concourse', 'Zone E - Exit Corridor'];
const alertMessages = [
    'Crowd density exceeding safe threshold in monitored zone',
    'Unusual movement pattern detected — potential counter-flow',
    'Rapid density increase — stampede risk elevated',
    'Choke point congestion building at corridor junction',
    'Behavioral anomaly: group formation detected near exit',
    'Queue overflow warning — capacity approaching limit',
    'Flow collision risk at intersection point',
];

const recommendations = [
    'Divert incoming flow to alternate route via Gate 3',
    'Deploy additional crowd marshals to affected zone',
    'Activate overflow barriers at choke point',
    'Open auxiliary exit gates to reduce density',
    'Issue PA announcement for orderly dispersal',
    'Increase surveillance coverage on flagged area',
    'Initiate soft lockdown on incoming pathways',
];

let idCounter = 0;
const uid = () => `evt-${Date.now()}-${++idCounter}`;

export function generateAlert(): Alert {
    const types: Alert['type'][] = ['critical', 'warning', 'info'];
    const type = types[Math.floor(Math.random() * types.length)];
    return {
        id: uid(),
        type,
        title: type === 'critical' ? 'CRITICAL ALERT' : type === 'warning' ? 'Warning' : 'Information',
        message: alertMessages[Math.floor(Math.random() * alertMessages.length)],
        zone: zones[Math.floor(Math.random() * zones.length)],
        timestamp: new Date().toISOString(),
        acknowledged: false,
        recommendedAction: recommendations[Math.floor(Math.random() * recommendations.length)],
    };
}

export function generateMetrics(): MetricData[] {
    return [
        {
            label: 'Crowd Density',
            value: (2.5 + Math.random() * 3).toFixed(1),
            unit: 'persons/m²',
            trend: Math.random() > 0.5 ? 'up' : 'stable',
            trendValue: `${(Math.random() * 0.5).toFixed(1)}`,
            icon: 'users',
            color: '#00E5FF',
        },
        {
            label: 'Risk Index',
            value: Math.floor(30 + Math.random() * 50),
            unit: '/100',
            trend: Math.random() > 0.6 ? 'up' : 'down',
            trendValue: `${Math.floor(Math.random() * 10)}`,
            icon: 'shield-alert',
            color: '#FFB300',
        },
        {
            label: 'Active Alerts',
            value: Math.floor(Math.random() * 8) + 1,
            unit: 'active',
            trend: Math.random() > 0.5 ? 'up' : 'down',
            trendValue: `${Math.floor(Math.random() * 3)}`,
            icon: 'bell-ring',
            color: '#FF3D00',
        },
        {
            label: 'Prediction Window',
            value: `${Math.floor(10 + Math.random() * 20)}`,
            unit: 'min ahead',
            trend: 'stable',
            trendValue: '0',
            icon: 'brain',
            color: '#7B61FF',
        },
    ];
}

export function generateChartPoint(): ChartDataPoint {
    const now = new Date();
    return {
        time: now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
        actual: 2 + Math.random() * 5,
        predicted: 2.5 + Math.random() * 4.5,
        threshold: 6,
    };
}

export function generateInitialChartData(count = 20): ChartDataPoint[] {
    const data: ChartDataPoint[] = [];
    const now = Date.now();
    for (let i = count; i > 0; i--) {
        const t = new Date(now - i * 60000);
        data.push({
            time: t.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
            actual: 2 + Math.random() * 5,
            predicted: 2.5 + Math.random() * 4.5,
            threshold: 6,
        });
    }
    return data;
}

export function generateCrowdDensityUpdate(): CrowdDensityUpdate {
    const zone = zones[Math.floor(Math.random() * zones.length)];
    return {
        zoneId: zone.split(' ')[0].toLowerCase() + zone.split(' ')[1],
        zoneName: zone,
        density: +(2 + Math.random() * 4).toFixed(1),
        timestamp: new Date().toISOString(),
        trend: (['increasing', 'decreasing', 'stable'] as const)[Math.floor(Math.random() * 3)],
    };
}

export function generateRiskPrediction(): RiskPrediction {
    const zone = zones[Math.floor(Math.random() * zones.length)];
    const score = Math.floor(Math.random() * 100);
    return {
        zoneId: zone.split(' ')[0].toLowerCase(),
        zoneName: zone,
        riskScore: score,
        riskLevel: score > 75 ? 'critical' : score > 50 ? 'high' : score > 25 ? 'medium' : 'low',
        predictionWindow: `${Math.floor(5 + Math.random() * 25)} min`,
        confidence: +(80 + Math.random() * 19).toFixed(1),
        factors: ['High density', 'Counter-flow detected', 'Narrow passage'].slice(0, Math.floor(Math.random() * 3) + 1),
    };
}

export function generateRiskCards(): RiskCardData[] {
    return [
        {
            id: 'stampede',
            title: 'Stampede Risk',
            severity: 'high',
            value: 72,
            maxValue: 100,
            recommendation: 'Open auxiliary gates to reduce directional pressure',
            trend: Array.from({ length: 10 }, () => 40 + Math.random() * 40),
            zone: 'Zone B - Central Plaza',
        },
        {
            id: 'chokepoint',
            title: 'Choke Point Analysis',
            severity: 'critical',
            value: 89,
            maxValue: 100,
            recommendation: 'Deploy crowd marshals to Corridor Junction C3',
            trend: Array.from({ length: 10 }, () => 60 + Math.random() * 35),
            zone: 'Zone C - East Wing',
        },
        {
            id: 'collision',
            title: 'Flow Collision',
            severity: 'medium',
            value: 45,
            maxValue: 100,
            recommendation: 'Implement one-way flow control at intersection',
            trend: Array.from({ length: 10 }, () => 20 + Math.random() * 40),
            zone: 'Zone A - Main Gate',
        },
        {
            id: 'anomaly',
            title: 'Behaviour Anomaly',
            severity: 'low',
            value: 23,
            maxValue: 100,
            recommendation: 'Continue monitoring — no immediate action required',
            trend: Array.from({ length: 10 }, () => 10 + Math.random() * 25),
            zone: 'Zone D - Concourse',
        },
        {
            id: 'queue',
            title: 'Queue Analysis',
            severity: 'medium',
            value: 56,
            maxValue: 100,
            recommendation: 'Open additional service counters to reduce wait time',
            trend: Array.from({ length: 10 }, () => 30 + Math.random() * 40),
            zone: 'Zone E - Exit Corridor',
        },
    ];
}

export function generatePipelineStages(): PipelineStage[] {
    const statuses: PipelineStage['status'][] = ['active', 'processing', 'active', 'active', 'processing', 'active', 'idle'];
    return [
        { id: 'camera', name: 'Camera Feed', status: statuses[0], latency: 8 + Math.floor(Math.random() * 15), confidence: +(97 + Math.random() * 3).toFixed(1) },
        { id: 'detection', name: 'AI Detection', status: statuses[1], latency: 30 + Math.floor(Math.random() * 30), confidence: +(93 + Math.random() * 5).toFixed(1) },
        { id: 'tracking', name: 'Tracking', status: statuses[2], latency: 15 + Math.floor(Math.random() * 20), confidence: +(90 + Math.random() * 7).toFixed(1) },
        { id: 'behaviour', name: 'Behaviour Analysis', status: statuses[3], latency: 50 + Math.floor(Math.random() * 30), confidence: +(87 + Math.random() * 8).toFixed(1) },
        { id: 'risk', name: 'Risk Prediction', status: statuses[4], latency: 20 + Math.floor(Math.random() * 25), confidence: +(85 + Math.random() * 10).toFixed(1) },
        { id: 'decision', name: 'Decision Engine', status: statuses[5], latency: 10 + Math.floor(Math.random() * 15), confidence: +(92 + Math.random() * 6).toFixed(1) },
        { id: 'response', name: 'Auto Response', status: statuses[6], latency: 3 + Math.floor(Math.random() * 8), confidence: +(95 + Math.random() * 4).toFixed(1) },
    ];
}

export function generateZones(): Zone[] {
    return zones.map((name, i) => ({
        id: `zone-${String.fromCharCode(65 + i).toLowerCase()}`,
        name,
        capacity: 500 + Math.floor(Math.random() * 1500),
        currentOccupancy: 200 + Math.floor(Math.random() * 800),
        status: (['normal', 'caution', 'danger'] as const)[Math.floor(Math.random() * 3)],
        cameras: 4 + Math.floor(Math.random() * 8),
        sensors: 6 + Math.floor(Math.random() * 10),
    }));
}

export function generateSensors(): SensorStatus[] {
    const types: SensorStatus['type'][] = ['camera', 'lidar', 'pressure', 'thermal'];
    return Array.from({ length: 16 }, (_, i) => ({
        id: `sensor-${i + 1}`,
        name: `${types[i % 4].toUpperCase()}-${Math.floor(i / 4) + 1}${String.fromCharCode(65 + (i % 4))}`,
        type: types[i % 4],
        status: (['online', 'online', 'online', 'degraded', 'offline'] as const)[Math.floor(Math.random() * 5)],
        zone: zones[Math.floor(Math.random() * zones.length)],
        lastUpdate: new Date(Date.now() - Math.random() * 300000).toISOString(),
        uptime: +(95 + Math.random() * 5).toFixed(1),
    }));
}

export function generateInitialAlerts(count = 6): Alert[] {
    return Array.from({ length: count }, () => generateAlert());
}
