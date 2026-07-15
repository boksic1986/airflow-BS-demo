import {Link} from "react-router-dom";

import {formatSecondsDuration} from "../lib/format";
import {isActiveStatus, normalizeStatus} from "../lib/status";

export function OperationProjectCell({
  analysisId,
  projectName,
  fallbackId,
  submittedBy,
  sampleCount,
  source,
  sourceBatchId,
}: {
  analysisId?: string | null;
  projectName?: string | null;
  fallbackId: string;
  submittedBy?: string | null;
  sampleCount: number;
  source: "manual" | "intake";
  sourceBatchId?: string | null;
}) {
  const title = projectName || fallbackId;
  const displaySourceBatchId = sourceBatchId?.trim() && sourceBatchId.trim() !== "." ? sourceBatchId.trim() : null;
  return (
    <div className="operation-project-cell">
      {analysisId ? (
        <Link className="tracker-primary-link" to={`/runs/${encodeURIComponent(analysisId)}`}>{title}</Link>
      ) : <strong>{title}</strong>}
      {analysisId ? (
        <Link className="mono tracker-run-link" to={`/runs/${encodeURIComponent(analysisId)}`}>{analysisId}</Link>
      ) : null}
      <span className="muted">Operator {submittedBy || "not captured"} / {sampleCount} samples</span>
      <span className="tracker-source-line">
        <span className={`run-source-tag source-${source}`}>{source === "intake" ? "Intake" : "Manual"}</span>
        {displaySourceBatchId ? <span title="Source batch">{displaySourceBatchId}</span> : null}
      </span>
    </div>
  );
}

export function OperationRuntimeCell({
  status,
  elapsedSeconds,
  estimatedRemainingSeconds,
  submitted,
}: {
  status: string;
  elapsedSeconds?: number | null;
  estimatedRemainingSeconds?: number | null;
  submitted: boolean;
}) {
  if (!submitted) {
    return <div className="runtime-cell"><strong>Not submitted</strong><span>ETA unavailable</span></div>;
  }
  const active = isActiveStatus(normalizeStatus(status));
  return (
    <div className={active ? "runtime-cell active" : "runtime-cell"}>
      <strong>Elapsed {formatSecondsDuration(elapsedSeconds)}</strong>
      <span>{active ? (estimatedRemainingSeconds == null ? "ETA needs history" : `ETA ~${formatSecondsDuration(estimatedRemainingSeconds)}`) : elapsedSeconds == null ? "Runtime not captured" : "Finished"}</span>
    </div>
  );
}
