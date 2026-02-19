/**
 * SENTINEL — useBackendStream
 *
 * Connects to the FastAPI backend via WebSocket and populates all
 * Zustand stores with live pipeline data. Falls back to the mock
 * simulator if the backend is unreachable after initial attempts.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useAlertStore } from '../store/useAlertStore';
import { useDashboardStore } from '../store/useDashboardStore';
import { usePipelineStore } from '../store/usePipelineStore';
import {
    connectStream,
    disconnectStream,
    onStreamMessage,
    onStreamStatus,
    type StreamMessage,
} from '../services/socket';
import { healthApi } from '../services/api';
import {
    generateMetrics,
    generateChartPoint,
    generateInitialChartData,
    generatePipelineStages,
    generateInitialAlerts,
    generateAlert,
} from '../services/mockData';
import type { PipelineStage } from '../types';

const FALLBACK_DELAY_MS = 5000; // wait 5s before falling back to mock

export function useBackendStream(cameraId = 'cam_0') {
    const initialized = useRef(false);
    const fallbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const usingMock = useRef(false);
    const mockIntervals = useRef<ReturnType<typeof setInterval>[]>([]);

    // ── Store actions ──────────────────────────────────────
    const addAlert = useAlertStore((s) => s.addAlert);
    const setAlerts = useAlertStore((s) => s.setAlerts);
    const setMetrics = useDashboardStore((s) => s.setMetrics);
    const addChartPoint = useDashboardStore((s) => s.addChartPoint);
    const setAiEngineHealth = useDashboardStore((s) => s.setAiEngineHealth);
    const setLiveFrame = useDashboardStore((s) => s.setLiveFrame);
    const setBackendConnected = useDashboardStore((s) => s.setBackendConnected);
    const setLiveMetrics = useDashboardStore((s) => s.setLiveMetrics);
    const setStages = usePipelineStore((s) => s.setStages);

    // ── Mock fallback ──────────────────────────────────────
    const startMockSimulator = useCallback(() => {
        if (usingMock.current) return;
        usingMock.current = true;
        console.log('[SENTINEL] Backend unreachable — falling back to mock data');

        setMetrics(generateMetrics());
        setAlerts(generateInitialAlerts(5));
        setStages(generatePipelineStages());
        generateInitialChartData(20).forEach((p) => addChartPoint(p));

        mockIntervals.current.push(
            setInterval(() => setMetrics(generateMetrics()), 3000),
            setInterval(() => addChartPoint(generateChartPoint()), 5000),
            setInterval(() => setStages(generatePipelineStages()), 4000),
            setInterval(() => addAlert(generateAlert()), 10000),
            setInterval(() => setAiEngineHealth(+(95 + Math.random() * 4.5).toFixed(1)), 6000),
        );
    }, [addAlert, setAlerts, setMetrics, addChartPoint, setStages, setAiEngineHealth]);

    const stopMockSimulator = useCallback(() => {
        mockIntervals.current.forEach(clearInterval);
        mockIntervals.current = [];
        usingMock.current = false;
    }, []);

    // ── Live data handler ──────────────────────────────────
    const handleMessage = useCallback(
        (msg: StreamMessage) => {
            if (msg.type !== 'frame') return;

            const m = msg.metadata;

            // Stop mock if it was running
            if (usingMock.current) stopMockSimulator();

            // Live frame
            if (msg.frame_b64) {
                setLiveFrame(`data:image/jpeg;base64,${msg.frame_b64}`);
            }

            // Live metrics for dashboard store
            setLiveMetrics({
                fps: m.fps,
                latencyMs: m.latency_ms,
                personCount: m.person_count,
                riskScore: m.risk_score,
                riskLevel: m.risk_level,
                density: m.density,
                congestion: m.congestion,
                anomaly: m.anomaly,
                flowMagnitude: m.flow_magnitude,
                trackCount: m.tracks,
            });

            // Update metric cards with live data
            setMetrics([
                {
                    label: 'Crowd Density',
                    value: m.density.toFixed(1),
                    unit: 'persons',
                    trend: m.density > 100 ? 'up' : 'stable',
                    trendValue: m.density.toFixed(0),
                    icon: 'users',
                    color: '#00E5FF',
                },
                {
                    label: 'Risk Index',
                    value: Math.round(m.risk_score * 100),
                    unit: '/100',
                    trend: m.risk_score > 0.6 ? 'up' : 'down',
                    trendValue: `${Math.round(m.risk_score * 100)}`,
                    icon: 'shield-alert',
                    color: m.risk_level === 'CRITICAL' ? '#FF3D00' : '#FFB300',
                },
                {
                    label: 'Persons Tracked',
                    value: m.person_count,
                    unit: 'active',
                    trend: m.person_count > 50 ? 'up' : 'stable',
                    trendValue: `${m.tracks}`,
                    icon: 'scan-eye',
                    color: '#7B61FF',
                },
                {
                    label: 'Pipeline Latency',
                    value: `${m.latency_ms.toFixed(0)}`,
                    unit: 'ms',
                    trend: m.latency_ms > 100 ? 'up' : 'down',
                    trendValue: `${m.fps.toFixed(1)} FPS`,
                    icon: 'zap',
                    color: '#00C853',
                },
            ]);

            // Chart point
            addChartPoint({
                time: new Date().toLocaleTimeString('en-US', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                }),
                actual: m.density,
                predicted: m.density * (0.9 + Math.random() * 0.2),
                threshold: 150,
            });

            // Pipeline stages from live data
            const liveStages: PipelineStage[] = [
                { id: 'acquire', name: 'Camera Acquire', status: 'active', latency: Math.round(m.latency_ms * 0.05), confidence: 99 },
                { id: 'preprocess', name: 'Preprocess', status: 'active', latency: Math.round(m.latency_ms * 0.05), confidence: 99 },
                { id: 'detection', name: 'YOLO Detection', status: 'processing', latency: Math.round(m.latency_ms * 0.25), confidence: 96 },
                { id: 'tracking', name: 'OC-SORT Track', status: 'active', latency: Math.round(m.latency_ms * 0.1), confidence: 94 },
                { id: 'flow', name: 'Optical Flow', status: 'active', latency: Math.round(m.latency_ms * 0.1), confidence: 92 },
                { id: 'density', name: 'Density Est.', status: 'processing', latency: Math.round(m.latency_ms * 0.1), confidence: 90 },
                { id: 'risk', name: 'Risk Scoring', status: m.risk_level === 'CRITICAL' ? 'error' : 'active', latency: Math.round(m.latency_ms * 0.05), confidence: 88 },
                { id: 'alert', name: 'Alert & Visualize', status: m.alert_tier ? 'processing' : 'idle', latency: Math.round(m.latency_ms * 0.05), confidence: 95 },
            ];
            setStages(liveStages);

            // AI engine health based on latency
            setAiEngineHealth(m.latency_ms < 80 ? 99.2 : m.latency_ms < 150 ? 96.5 : 91.0);

            // Alert from backend
            if (m.alert_tier) {
                addAlert({
                    id: `live-${msg.frame_idx}-${Date.now()}`,
                    type: m.alert_tier === 'EMERGENCY' || m.alert_tier === 'DANGER' ? 'critical' : m.alert_tier === 'WARNING' ? 'warning' : 'info',
                    title: m.alert_tier === 'EMERGENCY' ? 'EMERGENCY ALERT' : m.alert_tier === 'DANGER' ? 'DANGER' : m.alert_tier,
                    message: `Risk score ${(m.risk_score * 100).toFixed(0)}% — Density: ${m.density.toFixed(0)}, Congestion: ${(m.congestion * 100).toFixed(0)}%`,
                    zone: `Camera ${msg.camera_id}`,
                    timestamp: new Date().toISOString(),
                    acknowledged: false,
                    recommendedAction: m.congestion > 0.7
                        ? 'Open auxiliary gates to reduce crowd pressure'
                        : 'Monitor closely and deploy crowd marshals if risk increases',
                });
            }
        },
        [addAlert, addChartPoint, setAiEngineHealth, setLiveFrame, setLiveMetrics, setMetrics, setStages, stopMockSimulator]
    );

    // ── Connection status handler ──────────────────────────
    const handleStatus = useCallback(
        (connected: boolean) => {
            setBackendConnected(connected);
            if (connected) {
                // Clear fallback timer
                if (fallbackTimer.current) {
                    clearTimeout(fallbackTimer.current);
                    fallbackTimer.current = null;
                }
            }
        },
        [setBackendConnected]
    );

    // ── Main effect ────────────────────────────────────────
    useEffect(() => {
        if (initialized.current) return;
        initialized.current = true;

        // Subscribe to WebSocket events
        const unsubMessage = onStreamMessage(handleMessage);
        const unsubStatus = onStreamStatus(handleStatus);

        // Try connecting to backend
        healthApi.check()
            .then(() => {
                console.log('[SENTINEL] Backend reachable — connecting WebSocket');
                connectStream(cameraId);
            })
            .catch(() => {
                console.log('[SENTINEL] Backend unreachable — will retry, using mock in the meantime');
                connectStream(cameraId); // still try WS (auto-reconnect will keep trying)
                fallbackTimer.current = setTimeout(startMockSimulator, FALLBACK_DELAY_MS);
            });

        return () => {
            unsubMessage();
            unsubStatus();
            disconnectStream();
            stopMockSimulator();
            if (fallbackTimer.current) clearTimeout(fallbackTimer.current);
        };
    }, [cameraId, handleMessage, handleStatus, startMockSimulator, stopMockSimulator]);
}
