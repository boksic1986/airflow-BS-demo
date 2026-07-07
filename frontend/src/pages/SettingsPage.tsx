import {getApiBaseUrl} from "../api";

export function SettingsPage() {
  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Demo configuration</p>
          <h1>Settings</h1>
          <p>Non-secret frontend configuration and demo boundaries.</p>
        </div>
      </section>
      <section className="panel">
        <div className="definition-grid">
          <div><dt>Environment</dt><dd>Demo / Local</dd></div>
          <div><dt>API base</dt><dd className="path-text">{getApiBaseUrl()}</dd></div>
          <div><dt>Airflow UI</dt><dd>{`${window.location.protocol}//${window.location.hostname}:12958`}</dd></div>
          <div><dt>Secrets</dt><dd>Not displayed in frontend</dd></div>
          <div><dt>Remote acceptance</dt><dd>Runtime validation must run on ssh fengxian</dd></div>
          <div><dt>Unsupported pipelines</dt><dd>NIPT/WGS are demo/mock UI surfaces until backend/DAG work lands</dd></div>
        </div>
      </section>
    </div>
  );
}
