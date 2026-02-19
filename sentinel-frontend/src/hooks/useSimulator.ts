import { useEffect, useRef } from 'react';
import { useAlertStore } from '../store/useAlertStore';
import { useDashboardStore } from '../store/useDashboardStore';
import { usePipelineStore } from '../store/usePipelineStore';
import {
    generateAlert,
    generateMetrics,
    generateChartPoint,
    generateInitialChartData,
    generatePipelineStages,
    generateInitialAlerts,
} from '../services/mockData';

export function useSimulator() {
    const addAlert = useAlertStore((s) => s.addAlert);
    const setAlerts = useAlertStore((s) => s.setAlerts);
    const setMetrics = useDashboardStore((s) => s.setMetrics);
    const addChartPoint = useDashboardStore((s) => s.addChartPoint);
    const setAiEngineHealth = useDashboardStore((s) => s.setAiEngineHealth);
    const setStages = usePipelineStore((s) => s.setStages);
    const initialized = useRef(false);

    useEffect(() => {
        if (initialized.current) return;
        initialized.current = true;

        // Initialize with seed data
        setMetrics(generateMetrics());
        setAlerts(generateInitialAlerts(5));
        setStages(generatePipelineStages());
        const initial = generateInitialChartData(20);
        initial.forEach((p) => addChartPoint(p));

        // Metrics update every 3s
        const metricsInterval = setInterval(() => {
            setMetrics(generateMetrics());
        }, 3000);

        // Chart update every 5s
        const chartInterval = setInterval(() => {
            addChartPoint(generateChartPoint());
        }, 5000);

        // Pipeline update every 4s
        const pipelineInterval = setInterval(() => {
            setStages(generatePipelineStages());
        }, 4000);

        // New alert every 8-15s
        const alertInterval = setInterval(() => {
            addAlert(generateAlert());
        }, 8000 + Math.random() * 7000);

        // AI health fluctuation every 6s
        const healthInterval = setInterval(() => {
            setAiEngineHealth(+(95 + Math.random() * 4.5).toFixed(1));
        }, 6000);

        return () => {
            clearInterval(metricsInterval);
            clearInterval(chartInterval);
            clearInterval(pipelineInterval);
            clearInterval(alertInterval);
            clearInterval(healthInterval);
        };
    }, [addAlert, setAlerts, setMetrics, addChartPoint, setStages, setAiEngineHealth]);
}
