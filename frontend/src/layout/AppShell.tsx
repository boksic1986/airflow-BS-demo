import {
  Activity,
  AlertTriangle,
  ClipboardList,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  ListChecks,
  Search,
  Settings,
  TestTube2,
} from "lucide-react";
import {NavLink, Outlet} from "react-router-dom";

const navItems = [
  {to: "/dashboard", label: "Command Center", Icon: LayoutDashboard},
  {to: "/submit", label: "Submit Run", Icon: ClipboardList},
  {to: "/runs", label: "Batch Runs", Icon: Activity},
  {to: "/samples", label: "Sample Matrix", Icon: TestTube2},
  {to: "/workflows", label: "Workflow Catalog", Icon: GitBranch},
  {to: "/failures", label: "Failure Triage", Icon: AlertTriangle},
  {to: "/settings", label: "Platform Settings", Icon: Settings},
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <FlaskConical size={24} />
          <div>
            <strong>BioFlow Control</strong>
            <span>PGT-A + NIPT Docker</span>
          </div>
        </div>
        <nav aria-label="Primary navigation">
          {navItems.map(({to, label, Icon}) => (
            <NavLink key={to} to={to} className={({isActive}) => (isActive ? "active" : "")}>
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="shell-main">
        <header className="topbar">
          <div className="environment-pill">Demo environment</div>
          <label className="global-search">
            <Search size={16} />
            <span className="sr-only">Search runs, samples, logs</span>
            <input placeholder="Search runs, samples, logs" />
          </label>
          <div className="topbar-actions">
            <a className="button ghost" href={`${window.location.protocol}//${window.location.hostname}:12958`}>
              <ListChecks size={15} />
              Airflow 12958
            </a>
            <button className="button ghost" type="button">
              Demo user
            </button>
          </div>
        </header>
        <main className="content-shell">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
