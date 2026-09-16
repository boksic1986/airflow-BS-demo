import {useMemo, useState} from "react";

import type {AirflowTaskProgress, RuleEvent, RulePage, RuleQuery, RunProgressResponse} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {formatDate, formatProgressUnits} from "../../lib/format";
import {humanStageLabel} from "../../lib/stageLabels";
import {normalizeStatus} from "../../lib/status";

export const DEFAULT_RULE_QUERY: RuleQuery = {status: "running", limit: 20, sort: "active_first", offset: 0};

type RulePhaseSummary = {
  phase: string;
  status: string;
  total: number;
  running: number;
  success: number;
  failed: number;
  canceled: number;
};

function summarizeRulePhases(rules: RuleEvent[]): RulePhaseSummary[] {
  const grouped = new Map<string, RuleEvent[]>();
  for (const rule of rules) {
    const phase = rule.phase || "Pipeline";
    grouped.set(phase, [...(grouped.get(phase) || []), rule]);
  }
  return [...grouped.entries()].map(([phase, items]) => {
    const statuses = items.map((item) => normalizeStatus(item.status));
    const failed = statuses.filter((value) => ["failed", "fail", "error"].includes(value)).length;
    const running = statuses.filter((value) => ["running", "started"].includes(value)).length;
    const success = statuses.filter((value) => value === "success").length;
    const canceled = statuses.filter((value) => ["canceled", "cancelled", "terminated"].includes(value)).length;
    return {
      phase,
      status: failed ? "failed" : running ? "running" : success + canceled + statuses.filter((value) => value === "skipped").length < items.length ? "planned" : canceled ? "canceled" : success ? "success" : "skipped",
      total: items.length,
      running,
      success,
      failed,
      canceled,
    };
  });
}

export function RunWorkflowTab({progress, rules, onOpenLog, page, query, onQueryChange}: {
  progress: RunProgressResponse | null;
  rules: RuleEvent[];
  onOpenLog?: (key: string) => void;
  page?: RulePage;
  query?: RuleQuery;
  onQueryChange?: (query: RuleQuery) => void;
}) {
  const airflowTasks = (progress?.airflow_tasks || []).filter((task) => normalizeStatus(task.state) !== "skipped");
  const phases = useMemo(() => page?.phase_summaries || summarizeRulePhases(rules), [rules, page]);
  const [phaseFilter, setPhaseFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("running");
  const [offset, setOffset] = useState(0);
  const effectiveQuery = {...DEFAULT_RULE_QUERY, ...query};
  const [sampleFilter, setSampleFilter] = useState("");
  const [familyFilter, setFamilyFilter] = useState("");
  const filteredRules = onQueryChange ? rules : rules.filter((rule) => (!phaseFilter || rule.phase === phaseFilter) && (!statusFilter || rule.status === statusFilter) && (!sampleFilter || rule.sample_id === sampleFilter) && (!familyFilter || rule.family_id === familyFilter));
  const visibleRules = onQueryChange ? filteredRules : filteredRules.slice(offset, offset + 20);
  const paging = page && onQueryChange ? page : {offset, limit: 20, total: filteredRules.length, items: visibleRules};
  function goTo(next: number) {
    if (onQueryChange) onQueryChange({...effectiveQuery, offset: next});
    else setOffset(next);
  }
  function change(key: "phase" | "status" | "sampleId" | "familyId", value: string) {
    setOffset(0);
    onQueryChange?.({...effectiveQuery, [key]: value, offset: 0});
    if (key === "phase") setPhaseFilter(value);
    if (key === "status") setStatusFilter(value);
    if (key === "sampleId") setSampleFilter(value);
    if (key === "familyId") setFamilyFilter(value);
  }

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
      <section>
        <div className="toolbar">
          <label>Phase<input aria-label="Phase" value={query?.phase ?? phaseFilter} onChange={(e) => change("phase", e.target.value)} placeholder="Exact phase" /></label>
          <label>Status<select aria-label="Rule status" value={query?.status ?? statusFilter} onChange={(e) => change("status", e.target.value)}><option value="">All</option>{["planned", "running", "success", "failed", "canceled"].map((v) => <option key={v}>{v}</option>)}</select></label>
          <label>Sample<input aria-label="Sample" value={query?.sampleId ?? sampleFilter} onChange={(e) => change("sampleId", e.target.value)} placeholder="Exact sample ID" /></label>
          <label>Family<input aria-label="Family" value={query?.familyId ?? familyFilter} onChange={(e) => change("familyId", e.target.value)} placeholder="Exact family ID" /></label>
        </div>
        <RuleInstanceTable rules={visibleRules} onOpenLog={onOpenLog} />
        <nav aria-label="Rule pages"><button disabled={paging.offset === 0} onClick={() => goTo(Math.max(0, paging.offset - paging.limit))}>Previous</button><span>{paging.total ? paging.offset + 1 : 0}–{Math.min(paging.offset + paging.items.length, paging.total)} of {paging.total}</span><button disabled={paging.offset + paging.limit >= paging.total} onClick={() => goTo(paging.offset + paging.limit)}>Next</button></nav>
      </section>
    </div>
  );
}

function RuleInstanceTable({rules, onOpenLog}: {
  rules: RuleEvent[];
  onOpenLog?: (key: string) => void;
}) {
  return <div className="table-wrap"><table className="data-table rule-instance-table" aria-label="Pipeline rule instances">
    <thead><tr>{["Phase", "Rule", "Sample", "Family", "Order", "Job", "Status", "Started", "Finished", "Elapsed", "Remaining", "Message / failure excerpt"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
    <tbody>{rules.map((rule, index) => <tr key={JSON.stringify([rule.attempt, rule.rule_instance_id || [rule.rule, rule.sample_id, rule.family_id, rule.sequence, rule.snakemake_jobid, index]])}>
        <td>{rule.phase || "Unknown"}</td><td className="rule-name-cell">{rule.rule}</td><td>{rule.sample_id || "-"}</td><td>{rule.family_id || "-"}</td><td>{rule.sequence ?? "-"}</td>
        <td>{rule.snakemake_jobid || "-"}</td>
        <td><StatusBadge status={displayRuleStatus(rule.status)} />{rule.status_inferred ? <small>Inferred from run success</small> : null}</td>
        <td>{rule.started_at || rule.start_time ? formatDate(rule.started_at || rule.start_time) : "-"}</td><td>{rule.ended_at || rule.end_time ? formatDate(rule.ended_at || rule.end_time) : "-"}</td><td>{duration(rule.elapsed_seconds)}</td><td>{duration(rule.estimated_remaining_seconds)}</td>
        <td className="rule-message-cell">
          {rule.stderr_excerpt ? <details><summary>{rule.message || "Show failure excerpt"}</summary><pre>{rule.stderr_excerpt}</pre></details> : (rule.message || "-")}
          {rule.analysis_log_key && onOpenLog ? <button type="button" className="text-button" aria-label={`Open log for ${rule.rule}`} onClick={() => onOpenLog(rule.analysis_log_key!)}>Open log</button> : null}
        </td>
      </tr>)}{rules.length === 0 ? <tr><td colSpan={12} className="empty-cell">No matching Rule instances.</td></tr> : null}</tbody>
  </table></div>;
}

function duration(value?: number | null): string {
  if (value == null) return "-";
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${(value / 3600).toFixed(1)}h`;
}

function displayRuleStatus(value: string): string {
  return ["planned", "accepted"].includes(normalizeStatus(value)) ? "not_started" : value;
}

function LayeredWorkflowTimeline({airflowTasks, phases, pipeline: _pipeline, progress}: {
  airflowTasks: AirflowTaskProgress[];
  phases: RulePhaseSummary[];
  pipeline?: string;
  progress: RunProgressResponse | null;
}) {
  const title = "Workflow execution path";
  return (
    <section className="layered-timeline" aria-label="Layered workflow timeline">
      <div className="section-heading"><h2>{title}</h2><p>Project orchestration and biological analysis phases</p></div>
      {(progress?.orchestration_stages || []).length ? <PipelineStageGraph progress={progress} /> : <div aria-label="Selected Airflow execution path"><TimelineLane title="Airflow project tasks" empty="No Airflow task instances returned yet." items={airflowTasks.map((task) => ({id: task.task_id, label: humanStageLabel(task.task_id), status: task.state || "unknown", meta: `try ${task.try_number ?? "not captured"}`}))} /></div>}
      <TimelineLane title="Pipeline phases" empty="No rule events captured for this run." items={phases.map((phase) => ({id: phase.phase, label: phase.phase, status: phase.status, meta: `${phase.success}/${phase.total} jobs complete`}))} />
    </section>
  );
}

function PipelineStageGraph({progress}: {progress: RunProgressResponse | null}) {
  const stages = progress?.orchestration_stages || [];
  return <div className="wgs-stage-graph" aria-label="Pipeline stage dependency graph">{stages.map((stage) => <div key={stage.stage_code} className={`wgs-stage-node ${normalizeStatus(stage.status)}`} title={`开始：${stage.started_at ? formatDate(stage.started_at) : "未记录"}\n完成：${stage.ended_at ? formatDate(stage.ended_at) : "未记录"}`}><span>Step{stage.step_number}</span><strong>{stage.label}</strong>{stage.progress_available ? <small>{formatProgressUnits(stage.completed_units ?? 0, stage.total_units, stage.unit)}</small> : null}</div>)}{stages.length === 0 ? <p className="empty-state">No orchestration stage evidence captured.</p> : null}</div>;
}

function TimelineLane({title, items, empty}: {title: string; items: Array<{id: string; label: string; status: string; meta: string}>; empty: string}) {
  return (
    <div className="timeline-lane">
      <strong className="timeline-lane-title">{title}</strong>
      {items.length ? <ol>{items.map((item, index) => <li key={`${item.id}-${index}`} className={`timeline-node timeline-${normalizeStatus(item.status)}`}><span className="timeline-dot">{index + 1}</span><div><strong>{item.label}</strong><small title={item.id}>{item.meta}</small></div><StatusBadge status={item.status} size="sm" /></li>)}</ol> : <p className="empty-state">{empty}</p>}
    </div>
  );
}
