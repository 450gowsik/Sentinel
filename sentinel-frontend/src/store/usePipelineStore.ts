import { create } from 'zustand';
import type { PipelineStage } from '../types';

interface PipelineStore {
    stages: PipelineStage[];
    setStages: (stages: PipelineStage[]) => void;
    updateStage: (id: string, updates: Partial<PipelineStage>) => void;
}

export const usePipelineStore = create<PipelineStore>((set) => ({
    stages: [
        { id: 'camera', name: 'Camera Feed', status: 'active', latency: 12, confidence: 99.2 },
        { id: 'detection', name: 'AI Detection', status: 'processing', latency: 45, confidence: 96.8 },
        { id: 'tracking', name: 'Tracking', status: 'active', latency: 23, confidence: 94.5 },
        { id: 'behaviour', name: 'Behaviour Analysis', status: 'active', latency: 67, confidence: 91.3 },
        { id: 'risk', name: 'Risk Prediction', status: 'processing', latency: 34, confidence: 88.7 },
        { id: 'decision', name: 'Decision Engine', status: 'active', latency: 18, confidence: 95.1 },
        { id: 'response', name: 'Auto Response', status: 'idle', latency: 5, confidence: 97.4 },
    ],
    setStages: (stages) => set({ stages }),
    updateStage: (id, updates) =>
        set((state) => ({
            stages: state.stages.map((s) =>
                s.id === id ? { ...s, ...updates } : s
            ),
        })),
}));
