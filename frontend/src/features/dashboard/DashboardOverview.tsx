import {Link} from "react-router-dom";
import {useState} from 'react';

import type {DashboardOverview, DashboardPipeline, PipelineCapability} from "../../api";
import {SubmissionResumeCard, useIncompleteWgsSubmissions} from "../wgs/IncompleteSubmissions";

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
  const incomplete = useIncompleteWgsSubmissions(overview?.pipeline !== "gatk");
  const items = overview?.attention_items || [];
  const [acknowledged, setAcknowledged] = useState<string[]>(() => {
    try { const saved = JSON.parse(localStorage.getItem('attention-confirmed-v1') || '[]'); return Array.isArray(saved) ? saved.filter(x => typeof x === 'string') : []; } catch { return []; }
  });
  const [history, setHistory] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const identity = (item: typeof items[number]) => `${item.id}|${item.detail}`;
  const isArchived = (item: typeof items[number]) => item.severity === 'info' || acknowledged.includes(identity(item));
  const active = items.filter(item => !isArchived(item));
  const archived = items.filter(isArchived);
  const confirm = (item: typeof items[number], restore = false) => {
    const next = restore ? acknowledged.filter(id => id !== identity(item)) : [...acknowledged, identity(item)].slice(-500);
    setAcknowledged(next);
    try { localStorage.setItem('attention-confirmed-v1', JSON.stringify(next)); setSaveError(false); } catch { setSaveError(true); }
  };
  return (
    <article className="insight-card attention-card">
      <div className="section-heading-inline">
        <div>
          <h3>Attention required</h3>
          <p>待处理问题；确认仅在本浏览器收起，不改变流程状态。</p>
        </div>
        <strong className="attention-total" aria-label={`${active.length + incomplete.items.length} attention items`}>{active.length + incomplete.items.length}</strong>
      </div>
      <div className="attention-list">
        {incomplete.items.map(run => <SubmissionResumeCard key={run.analysis_id} run={run} />)}
        {(history ? [...active, ...archived] : active).map((item) => {
          const saved = acknowledged.includes(identity(item));
          return <div className="attention-item" key={identity(item)}><span className={`attention-marker ${item.severity}`} aria-label={item.severity} /><span><strong>{item.title}</strong><small>{item.detail}</small></span><span className="attention-actions">{item.analysis_id ? <Link to={`/runs/${encodeURIComponent(item.analysis_id)}`}>查看批次</Link> : <Link to="/samples">查看样本</Link>}{saved ? <button type="button" onClick={()=>confirm(item,true)}>恢复提醒</button> : <button type="button" aria-label="确认提醒" onClick={()=>confirm(item)}>已确认</button>}</span></div>;
        })}
        {active.length === 0 && incomplete.items.length === 0 && !history ? <p className="empty-state compact">No current attention items.</p> : null}
      </div>
      <button type="button" className="attention-history-toggle" aria-expanded={history} onClick={()=>setHistory(!history)}>{history ? '收起历史与已确认' : '历史与已确认'} ({archived.length})</button>
      {saveError ? <small role="status">本浏览器无法保存确认记录，本次页面内仍有效。</small> : null}
      {incomplete.error ? <small role="status">未完成提交刷新失败，保留上次结果；稍后自动重试。</small> : null}
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
