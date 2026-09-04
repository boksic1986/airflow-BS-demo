import {useMemo, useState} from "react";

import type {AirflowTaskProgress, RuleEvent, RunProgressResponse} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {formatProgressUnits} from "../../lib/format";
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

export function RunWorkflowTab({progress, rules, onOpenLog}: {
  progress: RunProgressResponse | null;
  rules: RuleEvent[];
  onOpenLog?: (key: string) => void;
}) {
  const airflowTasks = (progress?.airflow_tasks || []).filter((task) => isSelectedTask(task, progress?.pipeline));
  const phases = useMemo(() => summarizeRulePhases(rules, progress?.pipeline), [progress?.pipeline, rules]);
  const [phaseFilter, setPhaseFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sampleFilter, setSampleFilter] = useState("");
  const filteredRules = rules.filter((rule) => (!phaseFilter || rule.phase === phaseFilter) && (!statusFilter || rule.status === statusFilter) && (!sampleFilter || rule.sample_id === sampleFilter || rule.family_id === sampleFilter));

  return (
    <div className="workflow-tab-stack">
      <LayeredWorkflowTimeline airflowTasks={airflowTasks} phases={phases} pipeline={progress?.pipeline} progress={progress} />
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
      {progress?.pipeline === "wgs" ? <section><div className="section-heading"><div><h2>Rule instances</h2><p>Ordered by production phase, logger execution order and sample. Failed Rules show a bounded excerpt from the registered WGS analysis log; the full log remains in Logs.</p></div></div><div className="rule-filters"><label>Phase<select aria-label="Rule phase filter" value={phaseFilter} onChange={(event) => setPhaseFilter(event.target.value)}><option value="">All</option>{[...new Set(rules.map((rule) => rule.phase).filter(isText))].map((phase) => <option key={phase} value={phase}>{phase}</option>)}</select></label><label>Status<select aria-label="Rule status filter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All</option>{[...new Set(rules.map((rule) => rule.status))].map((status) => <option key={status} value={status}>{status}</option>)}</select></label><label>Sample / family<select aria-label="Rule sample filter" value={sampleFilter} onChange={(event) => setSampleFilter(event.target.value)}><option value="">All</option>{[...new Set(rules.flatMap((rule) => [rule.sample_id, rule.family_id]).filter(isText))].map((sample) => <option key={sample} value={sample}>{sample}</option>)}</select></label></div><div className="table-wrap"><table className="data-table rule-instance-table" aria-label="WGS rule instances"><thead><tr><th>Phase</th><th>Rule</th><th>Sample</th><th>Family</th><th>Execution order</th><th>Job</th><th>Status</th><th>Elapsed</th><th>Remaining</th><th>Message / failure excerpt</th></tr></thead><tbody>{filteredRules.map((rule, index) => <tr key={`${rule.rule}-${rule.sample_id || "all"}-${rule.sequence ?? index}`}><td>{rule.phase || "-"}</td><td className="rule-name-cell">{rule.rule}</td><td>{rule.sample_id || "-"}</td><td>{rule.family_id || "-"}</td><td>{rule.sequence ?? "-"}</td><td>{rule.snakemake_jobid || "-"}</td><td><StatusBadge status={rule.status} /></td><td>{duration(rule.elapsed_seconds)}</td><td>{duration(rule.estimated_remaining_seconds)}</td><td className="rule-message-cell">{rule.stderr_excerpt ? <details><summary>{rule.message || "Show failure excerpt"}</summary><pre>{rule.stderr_excerpt}</pre><small>Full WGS analysis log is available in Logs.</small></details> : (rule.message || "-")}{rule.analysis_log_key && onOpenLog ? <button type="button" className="text-button" aria-label={`Open log for ${rule.rule}`} onClick={() => onOpenLog(rule.analysis_log_key!)}>Open log</button> : null}</td></tr>)}{filteredRules.length === 0 ? <tr><td colSpan={10} className="empty-cell">No matching Rule instances.</td></tr> : null}</tbody></table></div></section> : null}
    </div>
  );
}

function duration(value?: number | null): string {
  if (value == null) return "-";
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${(value / 3600).toFixed(1)}h`;
}

function isText(value: string | null | undefined): value is string {
  return typeof value === "string" && value.length > 0;
}

function isSelectedTask(task: AirflowTaskProgress, pipeline?: string): boolean {
  if (normalizeStatus(task.state) === "skipped") return false;
  if (pipeline === "pgta") return PGTA_PREDICT_TASKS.has(task.task_id);
  if (pipeline === "nipt_docker") return NIPT_DOCKER_TASKS.has(task.task_id);
  // WGS renders the backend-projected Step1-Step6 contract instead of an
  // Airflow task allow-list. Keep raw task filtering out of the UI contract.
  if (pipeline === "wgs") return false;
  return true;
}

function LayeredWorkflowTimeline({airflowTasks, phases, pipeline, progress}: {
  airflowTasks: AirflowTaskProgress[];
  phases: ReturnType<typeof summarizeRulePhases>;
  pipeline?: string;
  progress: RunProgressResponse | null;
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
      {pipeline === "wgs" ? <WgsStageGraph progress={progress} /> : <div aria-label="Selected Airflow execution path"><TimelineLane title="Airflow project tasks" empty="No Airflow task instances returned yet." items={airflowTasks.map((task) => ({id: task.task_id, label: humanStageLabel(task.task_id), status: task.state || "unknown", meta: `try ${task.try_number ?? "not captured"}`}))} /></div>}
      <TimelineLane title="Pipeline phases" empty="No rule events captured for this run." items={phases.map((phase) => ({id: phase.phase, label: phase.phase, status: phase.status, meta: `${phase.success}/${phase.total} jobs complete`}))} />
    </section>
  );
}

function WgsStageGraph({progress}: {progress: RunProgressResponse | null}) {
  const stages = progress?.orchestration_stages || [];
  return <div className="wgs-stage-graph" aria-label="WGS stage dependency graph">{stages.map((stage) => <div key={stage.stage_code} className={`wgs-stage-node ${normalizeStatus(stage.status)}`}><span>Step{stage.step_number}</span><strong>{stage.label}</strong>{stage.progress_available ? <small>{formatProgressUnits(stage.completed_units ?? 0, stage.total_units, stage.unit)}</small> : null}</div>)}{stages.length === 0 ? <p className="empty-state">No orchestration stage evidence captured.</p> : null}</div>;
}

function TimelineLane({title, items, empty}: {title: string; items: Array<{id: string; label: string; status: string; meta: string}>; empty: string}) {
  return (
    <div className="timeline-lane">
      <strong className="timeline-lane-title">{title}</strong>
      {items.length ? <ol>{items.map((item, index) => <li key={`${item.id}-${index}`} className={`timeline-node timeline-${normalizeStatus(item.status)}`}><span className="timeline-dot">{index + 1}</span><div><strong>{item.label}</strong><small title={item.id}>{item.meta}</small></div><StatusBadge status={item.status} size="sm" /></li>)}</ol> : <p className="empty-state">{empty}</p>}
    </div>
  );
}
