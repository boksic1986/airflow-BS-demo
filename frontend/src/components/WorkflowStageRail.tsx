import type {WorkflowStageSummary} from "../api";
import {normalizeStatus} from "../lib/status";

const templates: Record<string, Array<{key: string; label: string}>> = {
  pgta: [
    {key: "mapping", label: "Mapping"},
    {key: "metadata", label: "Metadata"},
    {key: "cnv_qc", label: "CNV QC"},
    {key: "cnv_prediction", label: "CNV prediction"},
  ],
  nipt_docker: [
    {key: "input_qc", label: "Input QC"},
    {key: "mapping", label: "Mapping"},
    {key: "cnv", label: "CNV"},
    {key: "t21_classifier", label: "T21"},
    {key: "fetal_fraction", label: "Fetal fraction"},
    {key: "final_qc", label: "Final QC"},
  ],
};

export function WorkflowStageRail({analysisId, pipeline, stages}: {
  analysisId: string;
  pipeline: string;
  stages?: WorkflowStageSummary[];
}) {
  const items = stages?.length ? stages : (templates[pipeline] || []).map((stage) => ({...stage, status: "pending", completed_jobs: 0, total_jobs: 0}));
  const completed = items.filter((item) => normalizeStatus(item.status) === "success").length;
  const current = items.find((item) => ["running", "failed", "canceled"].includes(normalizeStatus(item.status)))
    || items.find((item) => normalizeStatus(item.status) !== "success")
    || items.at(-1);
  return (
    <div className="workflow-stage-summary" aria-label={`Workflow stages for ${analysisId}`}>
      <div className="workflow-stage-rail">
        {items.map((item) => {
          const status = normalizeStatus(item.status);
          return (
            <span className={`workflow-stage-node stage-${status}`} key={item.key} title={`${item.label}: ${item.status}; ${item.completed_jobs}/${item.total_jobs} jobs complete`}>
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
