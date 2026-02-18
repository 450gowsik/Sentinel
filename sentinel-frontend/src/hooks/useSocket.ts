/**
 * SENTINEL — useSocket (legacy compatibility wrapper)
 *
 * This hook is kept for backward compatibility but now delegates to
 * the native WebSocket service in socket.ts. The primary entry point
 * is useBackendStream — prefer that in new code.
 */

import { useEffect, useRef } from 'react';
import { onStreamMessage, onStreamStatus } from '../services/socket';
import { useAlertStore } from '../store/useAlertStore';
import { useDashboardStore } from '../store/useDashboardStore';

export function useSocket() {
    const addAlert = useAlertStore((s) => s.addAlert);
    const setCrowdDensity = useDashboardStore((s) => s.setCrowdDensity);
    const setRiskPrediction = useDashboardStore((s) => s.setRiskPrediction);
    const connected = useRef(false);

    useEffect(() => {
        if (connected.current) return;
        connected.current = true;

        const unsubStatus = onStreamStatus((isConnected) => {
            if (isConnected) {
                console.log('[SENTINEL] Socket connected');
            } else {
                console.log('[SENTINEL] Socket disconnected');
            }
        });

        const unsubMessage = onStreamMessage((msg) => {
            if (msg.type !== 'frame' || !msg.metadata) return;

            const m = msg.metadata;
            setCrowdDensity({
                zoneId: msg.camera_id,
                zoneName: `Camera ${msg.camera_id}`,
                density: m.density,
                timestamp: new Date().toISOString(),
                trend: m.density > 100 ? 'increasing' : 'stable',
            });

            setRiskPrediction({
                zoneId: msg.camera_id,
                zoneName: `Camera ${msg.camera_id}`,
                riskScore: Math.round(m.risk_score * 100),
                riskLevel: m.risk_level === 'CRITICAL' ? 'critical' : m.risk_level === 'HIGH' ? 'high' : m.risk_level === 'MEDIUM' ? 'medium' : 'low',
                predictionWindow: '15 min',
                confidence: 92,
                factors: m.congestion > 0.5 ? ['High congestion', 'Counter-flow'] : ['Normal flow'],
            });

            if (m.alert_tier) {
                addAlert({
                    id: `ws-${Date.now()}`,
                    type: m.alert_tier === 'EMERGENCY' || m.alert_tier === 'DANGER' ? 'critical' : 'warning',
                    title: m.alert_tier,
                    message: `Risk ${(m.risk_score * 100).toFixed(0)}% — ${m.person_count} persons`,
                    zone: `Camera ${msg.camera_id}`,
                    timestamp: new Date().toISOString(),
                    acknowledged: false,
                    recommendedAction: 'Monitor and take appropriate action',
                });
            }
        });

        return () => {
            unsubStatus();
            unsubMessage();
        };
    }, [addAlert, setCrowdDensity, setRiskPrediction]);
}
