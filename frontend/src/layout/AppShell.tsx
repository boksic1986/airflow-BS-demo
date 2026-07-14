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
  const navigate = useNavigate();
  const capabilities = usePlatformCapabilities();
  const [search, setSearch] = useState("");
  const niptOnly = capabilities.deployed_pipelines.length === 1 && capabilities.deployed_pipelines[0] === "nipt_docker";
  const wgsOnly = capabilities.deployed_pipelines.length === 1 && capabilities.deployed_pipelines[0] === "wgs";
  const niptWgs = capabilities.deployed_pipelines.length === 2
    && capabilities.deployed_pipelines.includes("nipt_docker")
    && capabilities.deployed_pipelines.includes("wgs");

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
            <strong>{wgsOnly ? "WGS Control Tower" : niptOnly ? "NIPT Control Tower" : "BioFlow Control"}</strong>
            <span>{wgsOnly ? "WGS only" : niptOnly ? "NIPT Docker only" : niptWgs ? "NIPT Docker + WGS" : "Deployed workflows"}</span>
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
            <span className="operator-pill">Demo operator</span>
          </div>
        </header>
        <main className="content-shell">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
