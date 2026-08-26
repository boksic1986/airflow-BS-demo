import {useMemo} from "react";

import type {AirflowTaskProgress, RuleEvent, RunProgressResponse} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {summarizeRulePhases} from "../../lib/niptPhases";
import {humanStageLabel} from "../../lib/stageLabels";
import {normalizeStatus} from "../../lib/status";

const PGTA_PREDICT_TASKS = new Set([
  "validate_request",
  "prepare_pgta_config",
  "pgta_predict.run_pgta_mapping",
  "pgta_predict.run_pgta_metadata",
  "pgta_predict.run_pgta_cnv_qc",
  "pgta_predict.run_pgta_cnv_predict",
  "collect_pgta_artifact",
]);

const NIPT_DOCKER_TASKS = new Set([
  "validate_request",
  "prepare_nipt_docker_run",
  "run_nipt_docker",
  "collect_nipt_artifacts",
]);

const WGS_TASKS = new Set([
  "validate_request", "prepare_wgs_batch",
  "input_transfer.acquire_obs_transfer_slot", "input_transfer.start_step1_upload",
  "input_transfer.wait_step1_upload", "input_transfer.release_obs_transfer_slot",
  "submit_step2_master", "start_step3_monitor", "wait_step3_analysis",
  "start_step4_publish", "wait_step4_publish",
  "result_transfer.acquire_obs_transfer_slot", "result_transfer.start_step5_download",
  "result_transfer.wait_step5_download", "result_transfer.release_obs_transfer_slot",
  "materialize_step6_results", "finalize_run",
  "release_leases",
]);

export function RunWorkflowTab({progress, rules}: {progress: RunProgressResponse | null; rules: RuleEvent[]}) {
  const airflowTasks = (progress?.airflow_tasks || []).filter((task) => isSelectedTask(task, progress?.pipeline));
  const phases = useMemo(() => summarizeRulePhases(rules, progress?.pipeline), [progress?.pipeline, rules]);

  return (
    <div className="workflow-tab-stack">
      <LayeredWorkflowTimeline airflowTasks={airflowTasks} phases={phases} pipeline={progress?.pipeline} />
      <section>
        <div className="section-heading">
          <div><h2>Pipeline steps</h2><h3>Pipeline phase summary</h3></div>
          <p>Rule events are grouped into production phases; failed and current rule logs are available in Logs.</p>
        </div>
        <div className="table-wrap">
          <table className="data-table" aria-label="Pipeline phase summary">
            <thead><tr><th>Phase</th><th>Status</th><th>Jobs</th><th>Running</th><th>Success</th><th>Failed</th><th>Canceled</th></tr></thead>
            <tbody>
              {phases.map((phase) => (
                <tr key={phase.phase}>
                  <td><strong>{phase.phase}</strong></td>
                  <td><StatusBadge status={phase.status} /></td>
                  <td>{phase.total}</td>
                  <td>{phase.running}</td>
                  <td>{phase.success}</td>
                  <td>{phase.failed}</td>
                  <td>{phase.canceled}</td>
                </tr>
              ))}
              {phases.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No rule events captured. Airflow task progress is still available above.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
      {progress?.pipeline === "wgs" ? <section><div className="section-heading"><div><h2>Rule timing</h2><p>ETA appears only after at least three comparable successful batches.</p></div></div><div className="table-wrap"><table className="data-table" aria-label="WGS rule timing"><thead><tr><th>Rule</th><th>Sample</th><th>Layer</th><th>Status</th><th>Elapsed</th><th>Historical median</th><th>Remaining</th><th>Model</th></tr></thead><tbody>{rules.map((rule, index) => <tr key={`${rule.rule}-${rule.sample_id || "all"}-${index}`}><td>{rule.rule}</td><td>{rule.sample_id || "-"}</td><td>{rule.layer ?? "-"}</td><td><StatusBadge status={rule.status} /></td><td>{duration(rule.elapsed_seconds)}</td><td>{duration(rule.historical_median_seconds)}</td><td>{duration(rule.estimated_remaining_seconds)}</td><td>{rule.eta_model === "insufficient_history" ? `No reliable estimate (${rule.eta_history_count || 0}/3)` : rule.eta_model || "-"}</td></tr>)}{rules.length === 0 ? <tr><td colSpan={8} className="empty-cell">No rule events captured.</td></tr> : null}</tbody></table></div></section> : null}
    </div>
  );
}

function duration(value?: number | null): string {
  if (value == null) return "-";
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${(value / 3600).toFixed(1)}h`;
}

function isSelectedTask(task: AirflowTaskProgress, pipeline?: string): boolean {
  if (normalizeStatus(task.state) === "skipped") return false;
  if (pipeline === "pgta") return PGTA_PREDICT_TASKS.has(task.task_id);
  if (pipeline === "nipt_docker") return NIPT_DOCKER_TASKS.has(task.task_id);
  if (pipeline === "wgs") return WGS_TASKS.has(task.task_id);
  return true;
}

function LayeredWorkflowTimeline({airflowTasks, phases, pipeline}: {
  airflowTasks: AirflowTaskProgress[];
  phases: ReturnType<typeof summarizeRulePhases>;
  pipeline?: string;
}) {
  const title = pipeline === "nipt_docker"
    ? "NIPT full analysis path"
    : pipeline === "wgs"
      ? "WGS CCE orchestration path"
      : pipeline === "pgta"
        ? "Predict execution path"
        : "Workflow execution path";
  return (
    <section className="layered-timeline" aria-label="Layered workflow timeline" title="Airflow shows project stages; pipeline events show the current bioinformatics phase.">
      <div className="section-heading"><h2>{title}</h2><p>Project orchestration and biological analysis phases</p></div>
      <div aria-label="Selected Airflow execution path">
        <TimelineLane title="Airflow project tasks" empty="No Airflow task instances returned yet." items={airflowTasks.map((task) => ({id: task.task_id, label: humanStageLabel(task.task_id), status: task.state || "unknown", meta: `try ${task.try_number ?? "not captured"}`}))} />
      </div>
      <TimelineLane title="Pipeline phases" empty="No rule events captured for this run." items={phases.map((phase) => ({id: phase.phase, label: phase.phase, status: phase.status, meta: `${phase.success}/${phase.total} jobs complete`}))} />
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
