import type {RunDetail} from "../../api";
import type {RunProgress} from "../../lib/runProgress";

import {RunProgressBar} from "../../components/RunProgressBar";
import {formatBytes, formatDuration, formatProgressUnits, formatSecondsDuration} from "../../lib/format";
import {isActiveStatus} from "../../lib/status";

export function CurrentProgressPanel({detail, progress, source, stage, slotUsage}: {
  detail: RunDetail;
  progress: RunProgress | null;
  source?: string | null;
  stage?: {completed_units?: number | null; total_units?: number | null; unit?: string | null; speed_bps?: number | null; eta_seconds?: number | null; current_item?: string | null} | null;
  slotUsage?: {pool: string; used: number; limit: number; waiting: number; mode: string} | null;
}) {
  return (
    <section className="panel current-progress-panel">
      <div className="section-heading split">
        <h2>Current progress</h2>
        {source ? <span className="source-pill" title="Progress data source">{source.replaceAll("_", " ")}</span> : null}
      </div>
      {progress ? (
        <div className="current-progress-hero">
          <strong>{progress.currentStep}</strong>
          <span>{progress.available === false ? "Detailed progress unavailable" : `${Math.round(progress.percent)}% complete`}</span>
          {progress.available !== false && stage?.total_units != null ? <span>{formatProgressUnits(stage.completed_units ?? 0, stage.total_units, stage.unit || "units")}</span> : null}
          {stage?.current_item ? <small className="path-text">Current: {stage.current_item}</small> : null}
          {stage?.speed_bps ? <small>{formatBytes(stage.speed_bps)}/s{stage.eta_seconds != null ? ` / ETA ${formatSecondsDuration(stage.eta_seconds)}` : ""}</small> : null}
          <small>
            Elapsed {formatDuration(detail.submitted_at || detail.started_at, detail.pipeline_finished_at || detail.ended_at)}
            {isActiveStatus(detail.status) ? " / ETA based on recent successful runs" : ""}
          </small>
          {slotUsage ? <div className="slot-usage" aria-label="High IO work pod quota">
            <strong>{slotUsage.used} / {slotUsage.limit} heavy work pods</strong>
            <small>{slotUsage.waiting} waiting / {slotUsage.mode.replaceAll("-", " ")}</small>
          </div> : null}
          <RunProgressBar analysisId={detail.analysis_id} progress={progress} />
        </div>
      ) : <p className="empty-state">Progress has not been captured for this run.</p>}
    </section>
  );
}
