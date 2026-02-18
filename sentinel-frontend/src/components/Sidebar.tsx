import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    MonitorPlay,
    ShieldAlert,
    Brain,
    BellRing,
    Server,
    FileBarChart,
    Settings,
    ChevronLeft,
    ChevronRight,
    Radar,
    ScanSearch,
} from 'lucide-react';

const navItems = [
    { path: '/', label: 'Overview', icon: LayoutDashboard },
    { path: '/monitoring', label: 'Live Monitoring', icon: MonitorPlay },
    { path: '/risk', label: 'Risk Intelligence', icon: ShieldAlert },
    { path: '/analytics', label: 'Behaviour Analytics', icon: Brain },
    { path: '/alerts', label: 'Alerts & Automation', icon: BellRing },
    { path: '/infrastructure', label: 'Infrastructure', icon: Server },
    { path: '/detect', label: 'Upload Detection', icon: ScanSearch },
    { path: '/reports', label: 'Reports', icon: FileBarChart },
    { path: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <aside
            className={`h-full bg-bg-secondary border-r border-border flex flex-col transition-all duration-300 ${collapsed ? 'w-[68px]' : 'w-[240px]'
                }`}
        >
            {/* Logo */}
            <div className="h-14 flex items-center gap-3 px-4 border-b border-border shrink-0">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan to-purple flex items-center justify-center shrink-0">
                    <Radar size={18} className="text-white" />
                </div>
                {!collapsed && (
                    <div className="overflow-hidden">
                        <h1 className="text-sm font-bold tracking-wider text-text-primary">SENTINEL</h1>
                        <p className="text-[10px] text-text-muted tracking-widest uppercase">AI Safety System</p>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
                {navItems.map(({ path, label, icon: Icon }) => (
                    <NavLink
                        key={path}
                        to={path}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${isActive
                                ? 'bg-cyan/10 text-cyan border border-cyan/20'
                                : 'text-text-secondary hover:text-text-primary hover:bg-bg-primary/50 border border-transparent'
                            }`
                        }
                    >
                        <Icon size={18} className="shrink-0" />
                        {!collapsed && <span className="truncate">{label}</span>}
                    </NavLink>
                ))}
            </nav>

            {/* Collapse Toggle */}
            <div className="p-2 border-t border-border shrink-0">
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-text-muted hover:text-text-secondary hover:bg-bg-primary/50 transition-colors text-xs cursor-pointer"
                >
                    {collapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /><span>Collapse</span></>}
                </button>
            </div>
        </aside>
    );
}
