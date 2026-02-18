import { create } from 'zustand';
import type { Alert } from '../types';

interface AlertStore {
    alerts: Alert[];
    unacknowledgedCount: number;
    addAlert: (alert: Alert) => void;
    acknowledgeAlert: (id: string) => void;
    clearAlerts: () => void;
    setAlerts: (alerts: Alert[]) => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
    alerts: [],
    unacknowledgedCount: 0,
    addAlert: (alert) =>
        set((state) => {
            const newAlerts = [alert, ...state.alerts].slice(0, 50);
            return {
                alerts: newAlerts,
                unacknowledgedCount: newAlerts.filter((a) => !a.acknowledged).length,
            };
        }),
    acknowledgeAlert: (id) =>
        set((state) => {
            const updated = state.alerts.map((a) =>
                a.id === id ? { ...a, acknowledged: true } : a
            );
            return {
                alerts: updated,
                unacknowledgedCount: updated.filter((a) => !a.acknowledged).length,
            };
        }),
    clearAlerts: () => set({ alerts: [], unacknowledgedCount: 0 }),
    setAlerts: (alerts) =>
        set({
            alerts,
            unacknowledgedCount: alerts.filter((a) => !a.acknowledged).length,
        }),
}));
