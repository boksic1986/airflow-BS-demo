import {BrowserRouter, Navigate, Route, Routes} from "react-router-dom";

import {AppShell} from "./layout/AppShell";
import {DashboardPage} from "./pages/DashboardPage";
import {FailuresPage} from "./pages/FailuresPage";
import {RunDetailPage} from "./pages/RunDetailPage";
import {RunsPage} from "./pages/RunsPage";
import {SamplesPage} from "./pages/SamplesPage";
import {SettingsPage} from "./pages/SettingsPage";
import {SubmitPage} from "./pages/SubmitPage";
import {WorkflowsPage} from "./pages/WorkflowsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="submit" element={<SubmitPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="runs/:analysisId" element={<RunDetailPage />} />
          <Route path="samples" element={<SamplesPage />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="failures" element={<FailuresPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
