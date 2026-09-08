import {Link} from "react-router-dom";

import type {DashboardOverview, DashboardPipeline, PipelineCapability} from "../../api";

export function PipelineRail({pipeline, onChange, pipelines}: {
  pipeline: DashboardPipeline;
  onChange: (pipeline: DashboardPipeline) => void;
  pipelines: PipelineCapability[];
}) {
  const items = pipelines.length > 1
    ? [{id: "all", display_name: "All pipelines", dag_id: "", version: null, enabled: true, submit_enabled: false, capabilities: [], execution_targets: []}, ...pipelines]
    : pipelines;
  return (
    <aside className="pipeline-rail" aria-label="Pipeline selector">
      {items.map((item) => (
        <button
          aria-label={item.display_name}
          className={pipeline === item.id ? "active" : ""}
          key={item.id}
          type="button"
          onClick={() => onChange(item.id)}
        >
          <strong>{item.display_name}</strong>
          <span>{item.id === "all" ? "Deployed workflows" : item.dag_id}</span>
        </button>
      ))}
    </aside>
  );
}

export function OperationsOverview({overview, period, loading, onPeriodChange, showQc = true}: {
  overview: DashboardOverview | null;
  period: "24h" | "7d" | "30d";
  loading: boolean;
  onPeriodChange: (period: "24h" | "7d" | "30d") => void;
  showQc?: boolean;
}) {
  return (
    <section className="panel dashboard-operations-panel" aria-busy={loading} title="Actionable operating conditions and sample throughput">
      <div className="dashboard-insight-grid dashboard-attention-grid">
        <AttentionRequired overview={overview} />
        <SampleThroughput overview={overview} period={period} onPeriodChange={onPeriodChange} showQc={showQc} />
      </div>
    </section>
  );
}

function AttentionRequired({overview}: {overview: DashboardOverview | null}) {
  const items = overview?.attention_items || [];
  return (
    <article className="insight-card attention-card">
      <div className="section-heading-inline">
        <div>
          <h3>Attention required</h3>
          <p>Items that may need an operator decision or follow-up.</p>
        </div>
        <strong className="attention-total" aria-label={`${items.length} attention items`}>{items.length}</strong>
      </div>
      <div className="attention-list">
        {items.slice(0, 8).map((item) => {
          const content = <><span className={`attention-marker ${item.severity}`} /><span><strong>{item.title}</strong><small>{item.detail}</small></span></>;
          return item.analysis_id
            ? <Link className="attention-item" key={item.id} to={`/runs/${encodeURIComponent(item.analysis_id)}`}>{content}</Link>
            : <div className="attention-item" key={item.id}>{content}</div>;
        })}
        {items.length === 0 ? <p className="empty-state compact">No current attention items.</p> : null}
      </div>
    </article>
  );
}

function SampleThroughput({overview, period, onPeriodChange, showQc}: {
  overview: DashboardOverview | null;
  period: "24h" | "7d" | "30d";
  onPeriodChange: (period: "24h" | "7d" | "30d") => void;
  showQc: boolean;
}) {
  const summary = overview?.sample_summary || {total: 0, running: 0, workflow_failed: 0, qc_failed: 0, completed: 0};
  const trend = overview?.sample_trend || [];
  const maxSamples = Math.max(1, ...trend.map((item) => item.total));
  return (
    <article className="insight-card sample-throughput-card">
      <div>
        <div className="section-heading-inline">
          <h3>Sample throughput</h3>
          <div className="period-selector" aria-label="Sample throughput period">
            {(["24h", "7d", "30d"] as const).map((item) => (
              <button className={period === item ? "active" : ""} key={item} type="button" onClick={() => onPeriodChange(item)}>{item}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="sample-throughput-grid">
        <span className="sample-total-metric"><small>Total</small><strong>{summary.total}</strong></span>
        <span>Running samples <strong>{summary.running}</strong></span>
        <span>Workflow failed samples <strong>{summary.workflow_failed}</strong></span>
        {showQc ? <span>QC failed samples <strong>{summary.qc_failed}</strong></span> : null}
        <span>Completed samples <strong>{summary.completed}</strong></span>
      </div>
      <div className="sample-stacked-bar" aria-label="Sample throughput distribution">
        <span className="success" style={{width: `${percent(summary.completed, summary.total)}%`}} title={`Completed: ${summary.completed}`} />
        <span className="info" style={{width: `${percent(summary.running, summary.total)}%`}} title={`Running: ${summary.running}`} />
        <span className="danger" style={{width: `${percent(summary.workflow_failed, summary.total)}%`}} title={`Workflow failed: ${summary.workflow_failed}`} />
        {showQc ? <span className="warning" style={{width: `${percent(summary.qc_failed, summary.total)}%`}} title={`QC failed: ${summary.qc_failed}`} /> : null}
      </div>
      <div className="mini-bars sample-bars">
        {trend.map((item) => (
          <span key={item.date} style={{height: `${Math.max(8, (item.total / maxSamples) * 42)}px`}} title={`${item.date}: ${item.total} samples`} />
        ))}
      </div>
    </article>
  );
}

function percent(value: number, total: number): number {
  if (!total) return 0;
  return Math.max(0, Math.min(100, (value / total) * 100));
}
