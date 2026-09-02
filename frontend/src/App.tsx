import {BrowserRouter, Navigate, Route, Routes} from "react-router-dom";

import {AppShell} from "./layout/AppShell";
import {PlatformCapabilitiesProvider} from "./features/platform/PlatformCapabilitiesContext";
import {SessionProvider, useSession} from "./features/auth/SessionContext";
import {DashboardPage} from "./pages/DashboardPage";
import {FailuresPage} from "./pages/FailuresPage";
import {RunDetailPage} from "./pages/RunDetailPage";
import {RunsPage} from "./pages/RunsPage";
import {SamplesPage} from "./pages/SamplesPage";
import {SubmitPage} from "./pages/SubmitPage";
import {WorkflowsPage} from "./pages/WorkflowsPage";
import {LoginPage} from "./pages/LoginPage";
import {AccountsPage} from "./pages/AccountsPage";

export default function App() {
  return (
    <SessionProvider><BrowserRouter><AppRoutes /></BrowserRouter></SessionProvider>
  );
}

function AppRoutes() {
  const session = useSession();
  if (session.loading) return <p className="muted">Restoring session...</p>;
  if (!session.user) return <LoginPage />;
  return <PlatformCapabilitiesProvider><Routes>
    <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          {session.hasRole("operator") ? <Route path="submit" element={<SubmitPage />} /> : null}
          <Route path="runs" element={<RunsPage />} />
          <Route path="runs/:analysisId" element={<RunDetailPage />} />
          <Route path="samples" element={<SamplesPage />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="failures" element={<FailuresPage />} />
          {session.hasRole("admin") ? <Route path="accounts" element={<AccountsPage />} /> : null}
    </Route>
  </Routes></PlatformCapabilitiesProvider>;
}
