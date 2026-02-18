import { Outlet } from 'react-router-dom';
import TopBar from '../components/TopBar';
import Sidebar from '../components/Sidebar';

export default function MainLayout() {
    return (
        <div className="h-screen flex flex-col bg-bg-primary">
            <TopBar />
            <div className="flex flex-1 overflow-hidden">
                <Sidebar />
                <main className="flex-1 overflow-y-auto p-5">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
