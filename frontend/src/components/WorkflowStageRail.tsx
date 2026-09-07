import type {WorkflowStageSummary} from "../api";
import {normalizeStatus} from "../lib/status";

export function WorkflowStageRail({analysisId, pipeline, stages}: {
  analysisId: string;
  pipeline: string;
  stages?: WorkflowStageSummary[];
}) {
  const items: WorkflowStageSummary[] = stages || [];
  const completed = items.filter((item) => normalizeStatus(item.status) === "success").length;
  const current = items.find((item) => ["running", "failed", "canceled"].includes(normalizeStatus(item.status)))
    || items.find((item) => normalizeStatus(item.status) !== "success")
    || items.at(-1);
  return (
    <div className="workflow-stage-summary" aria-label={`Workflow stages for ${analysisId}`}>
      <div className="workflow-stage-rail">
        {items.map((item) => {
          const status = normalizeStatus(item.status);
          const detail = item.dry_run
            ? `${item.total_jobs} jobs planned; dry-run only`
            : `${item.completed_jobs}/${item.total_jobs} jobs complete`;
          return (
            <span className={`workflow-stage-node stage-${status}`} key={item.key} title={`${item.label}: ${item.status}; ${detail}`}>
              <span className="workflow-stage-dot" />
              <small>{item.label}</small>
            </span>
          );
        })}
      </div>
      <span className="workflow-stage-mobile">{current?.label || "No stages"} / {completed}/{items.length}</span>
    </div>
  );
}
