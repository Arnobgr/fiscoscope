import { Routes, Route } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useMeta } from "./data/useData";
import { Overview } from "./pages/Overview";
import { KpiDetail } from "./pages/KpiDetail";
import { Methodology } from "./pages/Methodology";
import { PerformanceDetail } from "./pages/PerformanceDetail";

export default function App() {
  const meta = useMeta();
  return (
    <AppShell lastUpdated={meta?.last_run}>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/kpi/:slug" element={<KpiDetail />} />
        <Route path="/methodologie" element={<Methodology />} />
        <Route path="/performance" element={<PerformanceDetail />} />
      </Routes>
    </AppShell>
  );
}
