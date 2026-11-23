import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Analytics from "./pages/Analytics";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import Health from "./pages/Health";
import LiveFeed from "./pages/LiveFeed";
import Models from "./pages/Models";
import Monitoring from "./pages/Monitoring";
import Overview from "./pages/Overview";
import Replay from "./pages/Replay";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/feed" element={<LiveFeed />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/cases/:caseId" element={<CaseDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/models" element={<Models />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/replay" element={<Replay />} />
        <Route path="/health" element={<Health />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
