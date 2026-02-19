import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import LiveMonitoring from './pages/LiveMonitoring';
import RiskIntelligence from './pages/RiskIntelligence';
import BehaviourAnalytics from './pages/BehaviourAnalytics';
import AlertsAutomation from './pages/AlertsAutomation';
import Infrastructure from './pages/Infrastructure';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import MediaDetection from './pages/MediaDetection';
import { useBackendStream } from './hooks/useBackendStream';

function AppContent() {
  // Connects to backend WebSocket, falls back to mock data if unreachable
  useBackendStream('cam_0');

  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/monitoring" element={<LiveMonitoring />} />
        <Route path="/risk" element={<RiskIntelligence />} />
        <Route path="/analytics" element={<BehaviourAnalytics />} />
        <Route path="/alerts" element={<AlertsAutomation />} />
        <Route path="/infrastructure" element={<Infrastructure />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/detect" element={<MediaDetection />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
