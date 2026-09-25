import type {RunDetail, StageEstimate} from "../../api";
import {EstimatedStageProgress} from "../../components/EstimatedStageProgress";
import type {RunProgress} from "../../lib/runProgress";
import {runStageLabel} from "../../lib/runProgress";

import {RunProgressBar} from "../../components/RunProgressBar";
import {RecoveryNotice, recoveryPending, recoveryProgress} from "../../components/RecoveryNotice";
import {formatBytes, formatDuration, formatPercent, formatProgressUnits, formatSecondsDuration} from "../../lib/format";
import {isActiveStatus} from "../../lib/status";

export function CurrentProgressPanel({detail, progress, source, stage}: {
  detail: RunDetail;
  progress: RunProgress | null;
  source?: string | null;
  stage?: StageEstimate & {completed_units?: number | null; total_units?: number | null; unit?: string | null; speed_bps?: number | null; eta_seconds?: number | null; current_item?: string | null} | null;
  slotUsage?: {pool: string; used: number; limit: number; waiting: number; mode: string} | null;
}) {
  const pending = recoveryPending(detail.recovery);
  const linear = !pending && stage?.estimate_model === "stage_median_linear_v1";
  return (
    <section className="panel current-progress-panel snapshot-panel-stretch">
      <div className="section-heading split">
        <h2>Current progress</h2>
        {source ? <span className="source-pill" title="Progress data source">{source.replaceAll("_", " ")}</span> : null}
      </div>
      <RecoveryNotice value={detail.recovery} />
      {progress ? (
        <div className="current-progress-hero current-progress-content-centered">
          <strong>{runStageLabel(detail.status, progress.currentStep)}</strong>
          {!linear && !pending ? <span>{progress.available === false ? "Detailed progress unavailable" : `${formatPercent(progress.percent)} complete`}</span> : null}
          {progress.available !== false && stage?.total_units != null ? <span>{formatProgressUnits(stage.completed_units ?? 0, stage.total_units, stage.unit || "units")}</span> : null}
          {stage?.current_item ? <small className="path-text">Current: {stage.current_item}</small> : null}
          {!pending && stage?.speed_bps ? <small>{formatBytes(stage.speed_bps)}/s{stage.eta_seconds != null ? ` / ETA ${formatSecondsDuration(stage.eta_seconds)}` : ""}</small> : null}
          {!linear ? <small>
            Elapsed {formatDuration(detail.submitted_at || detail.started_at, detail.pipeline_finished_at || detail.ended_at)}
            {!pending && isActiveStatus(detail.status) ? " / ETA based on recent successful runs" : ""}
          </small> : stage?.estimate_elapsed_seconds != null ? <small>阶段已运行 {formatSecondsDuration(stage.estimate_elapsed_seconds)}{stage.estimate_baseline_seconds != null ? ` / 预计耗时 ${formatSecondsDuration(stage.estimate_baseline_seconds)}` : ""}</small> : null}
          {pending ? <RunProgressBar analysisId={detail.analysis_id} progress={recoveryProgress(progress)} /> : linear || progress.available === false && stage?.estimated_progress_percent != null ? <EstimatedStageProgress stage={stage} status={progress.status} /> : <RunProgressBar analysisId={detail.analysis_id} progress={progress} />}
        </div>
      ) : <p className="empty-state">Progress has not been captured for this run.</p>}
    </section>
  );
}
