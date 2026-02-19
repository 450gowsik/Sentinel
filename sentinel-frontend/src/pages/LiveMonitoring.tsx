import { MonitorPlay, Smartphone, Play, Camera, CameraOff } from 'lucide-react';
import YOLODetectionOverlay from '../features/detection/YOLODetectionOverlay';
import PressureFieldEstimation from '../features/pressure/PressureFieldEstimation';
import LiveCameraFeed from '../components/LiveCameraFeed';
import { useState } from 'react';
import { streamApi } from '../services/api';
import { useDashboardStore } from '../store/useDashboardStore';

const cameraConfig = [
    { id: 'cam_0', name: 'Main Gate - North', zone: 'Zone A' },
    { id: 'cam_1', name: 'Central Plaza - East', zone: 'Zone B' },
    { id: 'cam_2', name: 'East Wing - Corridor', zone: 'Zone C' },
    { id: 'cam_3', name: 'Concourse - Level 2', zone: 'Zone D' },
    { id: 'cam_4', name: 'Exit Corridor - South', zone: 'Zone E' },
    { id: 'cam_5', name: 'Parking Entrance', zone: 'Zone A' },
];

export default function LiveMonitoring() {
    const [cameraUrl, setCameraUrl] = useState('');
    const [isConfiguring, setIsConfiguring] = useState(false);

    const backendCameraActive = useDashboardStore((s) => s.backendCameraActive);
    const setBackendCameraActive = useDashboardStore((s) => s.setBackendCameraActive);

    const handleConnect = async () => {
        if (!cameraUrl) return;
        setIsConfiguring(true);
        try {
            await streamApi.configure(cameraUrl);
        } catch (e) {
            console.error('Failed to configure stream', e);
        } finally {
            setIsConfiguring(false);
        }
    };

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-cyan/15 flex items-center justify-center">
                        <MonitorPlay size={18} className="text-cyan" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Live Monitoring</h2>
                        <p className="text-xs text-text-muted">Multi-camera surveillance with YOLO v9 AI overlay</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Master Camera Toggle */}
                    <div className="flex items-center gap-2 bg-bg-primary/50 p-1 rounded-lg border border-border pr-3">
                        <button
                            onClick={() => setBackendCameraActive(!backendCameraActive)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[10px] font-bold transition-all ${backendCameraActive
                                ? 'bg-danger/20 text-danger border border-danger/30'
                                : 'bg-success/20 text-success border border-success/30'
                                }`}
                        >
                            {backendCameraActive ? (
                                <><CameraOff size={12} /> RELEASE HARDWARE</>
                            ) : (
                                <><Camera size={12} /> START BACKEND CAM</>
                            )}
                        </button>
                    </div>

                    {/* Mobile Camera Input */}
                    <div className="flex items-center gap-2 bg-bg-primary/50 p-1.5 rounded-lg border border-border">
                        <Smartphone size={14} className="text-text-muted ml-1" />
                        <input
                            type="text"
                            value={cameraUrl}
                            onChange={(e) => setCameraUrl(e.target.value)}
                            placeholder="IP Webcam URL"
                            className="bg-transparent border-none text-xs text-text-primary w-32 focus:outline-none placeholder:text-text-muted/50"
                        />
                        <button
                            onClick={handleConnect}
                            disabled={isConfiguring || !cameraUrl}
                            className="flex items-center gap-1 bg-cyan text-bg-primary px-3 py-1 rounded text-xs font-bold hover:bg-cyan/90 disabled:opacity-50"
                        >
                            {isConfiguring ? '...' : <><Play size={10} /> Connect</>}
                        </button>
                    </div>

                    {/* Mobile Sensor Helper */}
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => {
                                const url = window.location.origin + window.location.pathname;
                                navigator.clipboard.writeText(url);
                                alert("Mobile Link Copied! Open this URL on your phone and select 'MOBILE SENSOR'.");
                            }}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold bg-bg-primary/50 border border-border text-text-muted hover:text-cyan transition-all"
                            title="Copy link to open on phone"
                        >
                            <Smartphone size={12} /> CONNECT MOBILE
                        </button>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-text-muted">
                        <span className="flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${backendCameraActive ? 'bg-success pulse-dot' : 'bg-text-muted'}`} />
                            {backendCameraActive ? 'Backend Active' : 'Backend Paused'}
                        </span>
                    </div>
                </div>
            </div>

            {/* YOLO Detection Overlay — from mind map */}
            <div className="shrink-0">
                <YOLODetectionOverlay />
            </div>

            {/* Camera Grid */}
            <div className="grid grid-cols-3 gap-3 shrink-0">
                {cameraConfig.map((cam) => (
                    <LiveCameraFeed
                        key={cam.id}
                        cameraId={cam.id}
                        name={cam.name}
                        zone={cam.zone}
                    />
                ))}
            </div>

            {/* Pressure Field — from mind map */}
            <div className="shrink-0">
                <PressureFieldEstimation />
            </div>
        </div>
    );
}
