import {AlertTriangle, CheckCircle2, ExternalLink, Terminal} from "lucide-react";
import {Link} from "react-router-dom";

import type {FailureItem} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {compactPipelineName, formatDate} from "../../lib/format";

export function FailureWorkspace({items, selectedId, onSelect}: {
  items: FailureItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const selected = items.find((item) => failureKey(item) === selectedId) || items[0] || null;
  return (
    <div className="failure-workspace">
      <section className="failure-queue panel" aria-label="Failure queue">
        <div className="section-heading">
          <h2>Issue queue</h2>
          <span>{items.length} on this page</span>
        </div>
        <div className="failure-queue-list">
          {items.map((item) => {
            const key = failureKey(item);
            return (
              <button className={key === selectedId ? "active" : ""} key={key} type="button" onClick={() => onSelect(key)}>
                <span className={`failure-kind-icon ${item.failure_kind}`} aria-hidden="true">
                  {item.failure_kind === "qc" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                </span>
                <span>
                  <strong>{item.project_name}</strong>
                  <small>{item.analysis_id}</small>
                  <small>{compactPipelineName(item.pipeline)} · {item.failed_step_label}</small>
                </span>
                <StatusBadge status={item.failure_kind === "qc" ? item.qc_status : item.workflow_status} size="sm" />
              </button>
            );
          })}
          {items.length === 0 ? <p className="empty-state">No issues match the current filters.</p> : null}
        </div>
      </section>
      <section className="failure-diagnosis panel" aria-label="Failure diagnosis detail">
        {selected ? <FailureDiagnosis item={selected} /> : <p className="empty-state">Select an issue to inspect its diagnosis.</p>}
      </section>
    </div>
  );
}

function FailureDiagnosis({item}: {item: FailureItem}) {
  const workflowLabel = item.failure_kind === "qc" ? "Workflow success · QC failed" : "Workflow failed";
  return (
    <div className="failure-diagnosis-stack">
      <div className="section-heading split">
        <div>
          <p className="eyebrow">{item.failure_kind === "qc" ? "Sample QC alert" : "Workflow failure"}</p>
          <h2>{item.failed_step_label}</h2>
          <p>{workflowLabel}</p>
        </div>
        <StatusBadge status={item.failure_kind === "qc" ? item.qc_status : item.workflow_status} />
      </div>
      <dl className="definition-grid compact">
        <div><dt>Project</dt><dd>{item.project_name}</dd></div>
        <div><dt>Run</dt><dd className="mono path-text">{item.analysis_id}</dd></div>
        <div><dt>Layer</dt><dd>{failureLayerLabel(item.failure_layer)}</dd></div>
        <div><dt>Sample</dt><dd>{item.sample_id || "Project level"}</dd></div>
        <div><dt>Return code</dt><dd>{item.return_code ?? "Not captured"}</dd></div>
        <div><dt>Created</dt><dd>{formatDate(item.created_at)}</dd></div>
      </dl>
      <div className="diagnosis-block">
        <h3><Terminal size={16} /> Evidence</h3>
        <pre>{item.stderr_excerpt}</pre>
      </div>
      <div className="diagnosis-block">
        <h3>Possible reason</h3>
        <p>{item.possible_reason}</p>
      </div>
      <div className="diagnosis-block">
        <h3>Recommended action</h3>
        <p>{actionLabel(item.suggested_action_code)}</p>
      </div>
      <div className="panel-actions">
        <Link className="button primary" to={`/runs/${encodeURIComponent(item.analysis_id)}`}>
          Open run detail <ExternalLink size={14} />
        </Link>
        {item.can_resume || item.can_rerun_stage ? <span className="muted">Controlled recovery is available from Run action.</span> : null}
      </div>
    </div>
  );
}

function failureKey(item: FailureItem): string {
  return `${item.failure_kind}:${item.analysis_id}:${item.sample_id || "project"}:${item.failed_step}`;
}

function failureLayerLabel(layer: FailureItem["failure_layer"]): string {
  return {
    airflow: "Airflow task",
    runner: "Workflow runner",
    pipeline_rule: "Pipeline rule",
    qc: "Sample QC",
    unknown: "Unknown layer",
  }[layer];
}

function actionLabel(code: string): string {
  return {
    resume_pgta: "Review stderr, correct the root cause, then open Run Detail for available actions.",
    review_qc: "Review the failed sample metric and threshold before report handoff.",
    inspect_logs: "Open Run Detail Logs and confirm the failed task before retrying.",
  }[code] || "Open Run Detail and review the captured evidence.";
}
