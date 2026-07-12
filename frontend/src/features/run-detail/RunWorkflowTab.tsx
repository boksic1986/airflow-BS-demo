import {useEffect, useMemo, useState} from "react";

import type {AirflowTaskProgress, RuleEvent, RunProgressResponse} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {formatDate} from "../../lib/format";
import {sortRuleJobs, summarizeRulePhases} from "../../lib/niptPhases";
import {humanStageLabel, stageDebugLabel} from "../../lib/stageLabels";
import {normalizeStatus} from "../../lib/status";

const rulePageSize = 50;

export function RunWorkflowTab({progress, rules}: {progress: RunProgressResponse | null; rules: RuleEvent[]}) {
  const [page, setPage] = useState(0);
  const airflowTasks = progress?.airflow_tasks || [];
  const selectedAirflowTasks = airflowTasks.filter((task) => normalizeStatus(task.state) !== "skipped");
  const alternateAirflowTasks = airflowTasks.filter((task) => normalizeStatus(task.state) === "skipped");
  const phases = useMemo(() => summarizeRulePhases(rules), [rules]);
  const sortedRules = useMemo(() => sortRuleJobs(rules), [rules]);
  const pageCount = Math.max(1, Math.ceil(sortedRules.length / rulePageSize));
  const safePage = Math.min(page, pageCount - 1);
  const visibleRules = sortedRules.slice(safePage * rulePageSize, (safePage + 1) * rulePageSize);

  useEffect(() => setPage(0), [rules]);

  return (
    <div className="workflow-tab-stack">
      <LayeredWorkflowTimeline airflowTasks={selectedAirflowTasks} phases={phases} />
      {alternateAirflowTasks.length ? (
        <details className="alternate-workflow-paths">
          <summary>Alternate paths · {alternateAirflowTasks.length}</summary>
          <div className="alternate-workflow-grid">
            {alternateAirflowTasks.map((task) => (
              <div key={task.task_id}>
                <strong>{humanStageLabel(task.task_id)}</strong>
                <span>Not selected branch</span>
                <small title="Raw Airflow task ID">{task.task_id}</small>
              </div>
            ))}
          </div>
        </details>
      ) : null}
      <section>
        <div className="section-heading"><h2>Airflow tasks</h2><p>Project-level orchestration stages</p></div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>task</th><th>state</th><th>operator</th><th>try</th><th>started</th><th>ended</th><th>duration</th></tr></thead>
            <tbody>
              {airflowTasks.map((task) => (
                <tr key={`${task.task_id}-${task.try_number || "try"}`}>
                  <td><strong>{humanStageLabel(task.task_id)}</strong>{stageDebugLabel(task.task_id) ? <span className="muted block" title="Raw Airflow task ID">{task.task_id}</span> : null}</td>
                  <td><StatusBadge status={task.state} />{normalizeStatus(task.state) === "skipped" ? <small className="muted block">Not selected branch</small> : null}</td><td>{task.operator || "not set"}</td><td>{task.try_number ?? "not set"}</td>
                  <td>{formatDate(task.start_date)}</td><td>{formatDate(task.end_date)}</td><td>{task.duration ?? "not set"}</td>
                </tr>
              ))}
              {airflowTasks.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No Airflow task instances returned yet.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
      <div className="section-heading">
        <h2>Pipeline steps</h2>
        <p>Snakemake rule and sample events reported by the approved runtime logger</p>
      </div>
      <section>
        <div className="section-heading"><h3>Pipeline phase summary</h3><p>Grouped Snakemake jobs across the selected NIPT batch</p></div>
        <div className="table-wrap">
          <table className="data-table" aria-label="Pipeline phase summary">
            <thead><tr><th>phase</th><th>status</th><th>jobs</th><th>running</th><th>success</th><th>failed</th></tr></thead>
            <tbody>
              {phases.map((phase) => <tr key={phase.phase}><td><strong>{phase.phase}</strong></td><td><StatusBadge status={phase.status} /></td><td>{phase.total}</td><td>{phase.running}</td><td>{phase.success}</td><td>{phase.failed}</td></tr>)}
              {phases.length === 0 ? <tr><td className="empty-cell" colSpan={6}>No rule events captured. Airflow task progress is still available above.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <div className="section-heading"><h2>Pipeline rule jobs</h2><p>Active and failed jobs appear first</p></div>
        <div className="table-wrap">
          <table className="data-table" aria-label="Pipeline rule jobs">
            <thead><tr><th>rule</th><th>phase</th><th>sample</th><th>status</th><th>jobid</th><th>return</th><th>message</th></tr></thead>
            <tbody>
              {visibleRules.map((rule) => (
                <tr key={`${rule.rule}-${rule.sample_id || "project"}-${rule.snakemake_jobid || "none"}`}>
                  <td><strong>{humanStageLabel(rule.rule)}</strong>{stageDebugLabel(rule.rule) ? <span className="muted block" title="Raw pipeline step ID">{rule.rule}</span> : null}</td>
                  <td>{rule.phase || summarizeRulePhases([rule])[0]?.phase || "Pipeline"}</td><td>{rule.sample_id || "project"}</td><td><StatusBadge status={rule.status} /></td><td>{rule.snakemake_jobid || "not set"}</td><td>{rule.return_code ?? "not set"}</td><td>{rule.message || "not set"}</td>
                </tr>
              ))}
              {visibleRules.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No pipeline rule jobs captured.</td></tr> : null}
            </tbody>
          </table>
        </div>
        <div className="pagination-row">
          <span>{sortedRules.length} rule jobs / page {safePage + 1} / {pageCount}</span>
          <div>
            <button className="button ghost" type="button" aria-label="Previous rule jobs" disabled={safePage === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>Previous</button>
            <button className="button ghost" type="button" aria-label="Next rule jobs" disabled={safePage >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}>Next</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function LayeredWorkflowTimeline({airflowTasks, phases}: {airflowTasks: AirflowTaskProgress[]; phases: ReturnType<typeof summarizeRulePhases>}) {
  return (
    <section className="layered-timeline" aria-label="Layered workflow timeline" title="Airflow shows project stages; pipeline events show the current bioinformatics phase.">
      <div className="section-heading"><h2>Layered timeline</h2><p>Orchestration and pipeline execution</p></div>
      <div aria-label="Selected Airflow execution path">
        <TimelineLane title="Airflow project tasks" empty="No Airflow task instances returned yet." items={airflowTasks.map((task) => ({id: task.task_id, label: humanStageLabel(task.task_id), status: task.state || "unknown", meta: `${task.operator || "operator not set"} / try ${task.try_number ?? "not set"}`}))} />
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
