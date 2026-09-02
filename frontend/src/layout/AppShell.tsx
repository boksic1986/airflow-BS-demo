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
import {useState, type FormEvent} from "react";
import {NavLink, Outlet, useNavigate} from "react-router-dom";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {useSession} from "../features/auth/SessionContext";

const navItems = [
  {to: "/dashboard", label: "Command Center", Icon: LayoutDashboard},
  {to: "/runs", label: "Batch Runs", Icon: Activity},
  {to: "/samples", label: "Samples", Icon: TestTube2},
  {to: "/workflows", label: "Workflow Catalog", Icon: GitBranch},
  {to: "/failures", label: "Failure Triage", Icon: AlertTriangle},
];

export function AppShell() {
  const navigate = useNavigate();
  const capabilities = usePlatformCapabilities();
  const session = useSession();
  const [search, setSearch] = useState("");

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const keyword = search.trim();
    if (!keyword) return;
    navigate(`/runs?keyword=${encodeURIComponent(keyword)}`);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <FlaskConical size={24} />
          <div>
            <strong>WGS Control Tower</strong>
            <span>WGS production</span>
          </div>
        </div>
        <nav aria-label="Primary navigation">
          {[...navItems, ...(session.hasRole("operator") ? [{to: "/submit", label: "Submit Run", Icon: ClipboardList}] : [])].map(({to, label, Icon}) => (
            <NavLink key={to} to={to} className={({isActive}) => (isActive ? "active" : "")}>
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
          {session.hasRole("admin") ? <NavLink to="/accounts"><Settings size={17} /><span>Accounts</span></NavLink> : null}
        </nav>
      </aside>
      <div className="shell-main">
        <header className="topbar">
          <div className="environment-pill">{capabilities.environment} environment</div>
          <form className="global-search" role="search" onSubmit={submitSearch}>
            <Search size={16} />
            <label className="sr-only" htmlFor="global-run-search">Search project or run ID</label>
            <input
              id="global-run-search"
              type="search"
              value={search}
              placeholder="Search project or run ID"
              onChange={(event) => setSearch(event.target.value)}
            />
          </form>
          <div className="topbar-actions">
            <a className="button ghost" href={capabilities.airflow_url || `${window.location.protocol}//${window.location.hostname}:12958`}>
              <ListChecks size={15} />
              Airflow 12958
            </a>
            <span className="operator-pill">{session.user?.username} / {session.user?.role}</span>
            <button className="button ghost" type="button" onClick={() => void session.logout()}>Sign out</button>
          </div>
        </header>
        <main className="content-shell">
          {capabilities.error ? (
            <div className="inline-error" role="alert">
              Deployment capabilities unavailable: {capabilities.error} Showing the WGS compatibility view.
            </div>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
