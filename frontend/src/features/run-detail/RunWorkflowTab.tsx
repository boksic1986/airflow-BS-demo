import type {AirflowTaskProgress, RuleEvent, RunProgressResponse} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {formatDate} from "../../lib/format";
import {humanStageLabel, stageDebugLabel} from "../../lib/stageLabels";
import {normalizeStatus} from "../../lib/status";

export function RunWorkflowTab({progress, rules}: {progress: RunProgressResponse | null; rules: RuleEvent[]}) {
  const airflowTasks = progress?.airflow_tasks || [];
  return (
    <div className="workflow-tab-stack">
      <LayeredWorkflowTimeline airflowTasks={airflowTasks} rules={rules} />
      <section>
        <div className="section-heading"><h2>Airflow tasks</h2><p>Project-level orchestration stages</p></div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>task</th><th>state</th><th>operator</th><th>try</th><th>started</th><th>ended</th><th>duration</th></tr></thead>
            <tbody>
              {airflowTasks.map((task) => (
                <tr key={`${task.task_id}-${task.try_number || "try"}`}>
                  <td><strong>{humanStageLabel(task.task_id)}</strong>{stageDebugLabel(task.task_id) ? <span className="muted block" title="Raw Airflow task ID">{task.task_id}</span> : null}</td>
                  <td><StatusBadge status={task.state} /></td><td>{task.operator || "not set"}</td><td>{task.try_number ?? "not set"}</td>
                  <td>{formatDate(task.start_date)}</td><td>{formatDate(task.end_date)}</td><td>{task.duration ?? "not set"}</td>
                </tr>
              ))}
              {airflowTasks.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No Airflow task instances returned yet.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <div className="section-heading"><h2>Pipeline steps</h2><p>Snakemake or runner events</p></div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>rule</th><th>sample</th><th>status</th><th>snakemake jobid</th><th>qsub jobid</th><th>return</th><th>message</th></tr></thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={`${rule.rule}-${rule.sample_id || "project"}-${rule.snakemake_jobid || "none"}`}>
                  <td><strong>{humanStageLabel(rule.rule)}</strong>{stageDebugLabel(rule.rule) ? <span className="muted block" title="Raw pipeline step ID">{rule.rule}</span> : null}</td>
                  <td>{rule.sample_id || "project"}</td><td><StatusBadge status={rule.status} /></td><td>{rule.snakemake_jobid || "not set"}</td><td>{rule.qsub_jobid || "not set"}</td><td>{rule.return_code ?? "not set"}</td><td>{rule.message || "not set"}</td>
                </tr>
              ))}
              {rules.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No rule events captured. Airflow task progress is still available above.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function LayeredWorkflowTimeline({airflowTasks, rules}: {airflowTasks: AirflowTaskProgress[]; rules: RuleEvent[]}) {
  return (
    <section className="layered-timeline" aria-label="Layered workflow timeline" title="Airflow shows project stages; pipeline events show the current bioinformatics step.">
      <div className="section-heading"><h2>Layered timeline</h2><p>Orchestration and pipeline execution</p></div>
      <TimelineLane title="Airflow project tasks" empty="No Airflow task instances returned yet." items={airflowTasks.map((task) => ({id: task.task_id, label: humanStageLabel(task.task_id), status: task.state || "unknown", meta: `${task.operator || "operator not set"} / try ${task.try_number ?? "not set"}`}))} />
      <TimelineLane title="Pipeline steps" empty="No rule events captured for this run." items={rules.map((rule) => ({id: rule.rule, label: humanStageLabel(rule.rule), status: rule.status || "unknown", meta: rule.sample_id ? `sample ${rule.sample_id}` : "project event"}))} />
    </section>
  );
}

function TimelineLane({title, items, empty}: {title: string; items: Array<{id: string; label: string; status: string; meta: string}>; empty: string}) {
  return (
    <div className="timeline-lane">
      <strong className="timeline-lane-title">{title}</strong>
      {items.length ? <ol>{items.map((item, index) => <li key={`${item.id}-${index}`} className={`timeline-node timeline-${normalizeStatus(item.status)}`}><span className="timeline-dot">{index + 1}</span><div><strong>{item.label}</strong><small title={item.id}>{item.meta}</small></div><StatusBadge status={item.status} size="sm" /></li>)}</ol> : <p className="empty-state">{empty}</p>}
    </div>
  );
}
