import { Server, Wifi, WifiOff, Camera, Thermometer, Gauge, Activity } from 'lucide-react';
import StatusBadge from '../components/StatusBadge';
import { generateSensors, generateZones } from '../services/mockData';
import { useState, useEffect } from 'react';
import type { SensorStatus, Zone } from '../types';

export default function Infrastructure() {
    const [sensors, setSensors] = useState<SensorStatus[]>([]);
    const [zones, setZones] = useState<Zone[]>([]);

    useEffect(() => {
        setSensors(generateSensors());
        setZones(generateZones());
    }, []);

    const sensorIcon: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
        camera: Camera,
        lidar: Activity,
        pressure: Gauge,
        thermal: Thermometer,
    };

    const onlineCount = sensors.filter(s => s.status === 'online').length;
    const degradedCount = sensors.filter(s => s.status === 'degraded').length;
    const offlineCount = sensors.filter(s => s.status === 'offline').length;

    return (
        <div className="h-full flex flex-col gap-4 animate-fade-in overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-cyan/15 flex items-center justify-center">
                        <Server size={18} className="text-cyan" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-text-primary">Infrastructure</h2>
                        <p className="text-xs text-text-muted">Sensor & camera network monitoring</p>
                    </div>
                </div>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-3 gap-3 shrink-0">
                <div className="glass-card p-4">
                    <div className="flex items-center gap-2 mb-1">
                        <Wifi size={14} className="text-success" />
                        <span className="text-xs text-text-muted">Online</span>
                    </div>
                    <div className="text-2xl font-bold text-success">{onlineCount}</div>
                </div>
                <div className="glass-card p-4">
                    <div className="flex items-center gap-2 mb-1">
                        <Wifi size={14} className="text-warning" />
                        <span className="text-xs text-text-muted">Degraded</span>
                    </div>
                    <div className="text-2xl font-bold text-warning">{degradedCount}</div>
                </div>
                <div className="glass-card p-4">
                    <div className="flex items-center gap-2 mb-1">
                        <WifiOff size={14} className="text-danger" />
                        <span className="text-xs text-text-muted">Offline</span>
                    </div>
                    <div className="text-2xl font-bold text-danger">{offlineCount}</div>
                </div>
            </div>

            {/* Zones */}
            <div className="glass-card p-4 shrink-0">
                <h3 className="text-sm font-semibold text-text-primary mb-3">Zone Capacity Overview</h3>
                <div className="grid grid-cols-5 gap-3">
                    {zones.map((zone) => {
                        const utilization = Math.round((zone.currentOccupancy / zone.capacity) * 100);
                        const color = zone.status === 'normal' ? '#00C853' : zone.status === 'caution' ? '#FFB300' : '#FF3D00';
                        return (
                            <div key={zone.id} className="p-3 rounded-lg bg-bg-primary border border-border">
                                <div className="text-[11px] font-semibold text-text-primary mb-2">{zone.name}</div>
                                <div className="text-lg font-bold" style={{ color }}>{utilization}%</div>
                                <div className="text-[10px] text-text-muted">{zone.currentOccupancy}/{zone.capacity}</div>
                                <div className="w-full h-1 rounded-full bg-bg-secondary mt-2">
                                    <div className="h-full rounded-full transition-all" style={{ width: `${utilization}%`, backgroundColor: color }} />
                                </div>
                                <div className="flex gap-2 mt-2 text-[9px] text-text-muted">
                                    <span>📷 {zone.cameras}</span>
                                    <span>📡 {zone.sensors}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Sensor Grid */}
            <div className="glass-card p-4 shrink-0">
                <h3 className="text-sm font-semibold text-text-primary mb-3">Sensor Network</h3>
                <div className="grid grid-cols-4 gap-2">
                    {sensors.map((sensor) => {
                        const Icon = sensorIcon[sensor.type] || Activity;
                        return (
                            <div key={sensor.id} className="p-3 rounded-lg bg-bg-primary border border-border hover:border-border-active transition-colors">
                                <div className="flex items-center justify-between mb-2">
                                    <Icon size={14} className="text-text-secondary" />
                                    <StatusBadge status={sensor.status} size="sm" />
                                </div>
                                <div className="text-[11px] font-semibold text-text-primary">{sensor.name}</div>
                                <div className="text-[10px] text-text-muted mt-1">{sensor.zone}</div>
                                <div className="text-[10px] text-text-muted mt-0.5">Uptime: {sensor.uptime}%</div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
