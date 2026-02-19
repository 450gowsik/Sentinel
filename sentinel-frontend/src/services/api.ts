import axios from 'axios';

// In dev mode, Vite proxy forwards /api → localhost:8000
// In production, set VITE_API_URL to the deployed backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('sentinel_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        console.error('[SENTINEL API Error]', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// ── Dashboard / Metrics ─────────────────────────────────────
export const metricsApi = {
    getLive: (cameraId = 'cam_0') =>
        api.get(`/metrics/live?camera_id=${cameraId}`),
    getGPUStatus: () => api.get('/gpu-status'),
};

// ── Alerts ──────────────────────────────────────────────────
export const alertsApi = {
    getAlerts: (params?: Record<string, string>) =>
        api.get('/alerts', { params }),
    acknowledgeAlert: (id: string, operatorId = 'operator_1') =>
        api.post(`/alerts/${id}/ack`, { operator_id: operatorId }),
    getActiveCount: () => api.get('/alerts/active/count'),
};

// ── Analytics ───────────────────────────────────────────────
export const analyticsApi = {
    getHeatmap: (cameraId: string) => api.get(`/heatmap/${cameraId}`),
    getTrajectories: (cameraId = 'cam_0') =>
        api.get(`/trajectories?camera_id=${cameraId}`),
    getSafePath: (zoneId: string) => api.get(`/safepath/${zoneId}`),
    getBehaviour: (cameraId = 'cam_0') =>
        api.get(`/analytics/behaviour?camera_id=${cameraId}`),
};

// ── Pipeline / Infrastructure ───────────────────────────────
export const pipelineApi = {
    getDiagnostics: () => api.get('/pipeline/diagnostics'),
};

// ── Detection (Upload) ──────────────────────────────────
export const detectApi = {
    uploadFile: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/detect/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120000,
        });
    },
};

// ── Live Camera Stream ──────────────────────────────────────
export const streamApi = {
    configure: (source: string, cameraId = 'cam_0') =>
        api.post('/live/config', { source, camera_id: cameraId }),
    getStatus: () => api.get('/live/camera-status'),
};

// ── Health ──────────────────────────────────────────────────
export const healthApi = {
    check: () => axios.get(
        import.meta.env.VITE_API_URL
            ? `${import.meta.env.VITE_API_URL}/health`
            : '/health'
    ),
};

export default api;
