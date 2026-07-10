import type {RunDetail} from "../../api";
import type {RunProgress} from "../../lib/runProgress";

import {RunProgressBar} from "../../components/RunProgressBar";
import {formatDuration} from "../../lib/format";
import {humanStageLabel, stageDebugLabel} from "../../lib/stageLabels";
import {isActiveStatus} from "../../lib/status";

export function CurrentProgressPanel({detail, progress, source}: {
  detail: RunDetail;
  progress: RunProgress | null;
  source?: string | null;
}) {
  return (
    <section className="panel current-progress-panel">
      <div className="section-heading split">
        <h2>Current progress</h2>
        {source ? <span className="source-pill" title="Progress data source">{source.replaceAll("_", " ")}</span> : null}
      </div>
      {progress ? (
        <div className="current-progress-hero">
          <strong>{humanStageLabel(progress.currentStep)}</strong>
          {stageDebugLabel(progress.currentStep) ? <small title="Raw pipeline step ID">{progress.currentStep}</small> : null}
          <span>{Math.round(progress.percent)}% complete</span>
          <small>
            Elapsed {formatDuration(detail.started_at, detail.ended_at)}
            {isActiveStatus(detail.status) ? " · ETA based on recent successful runs" : ""}
          </small>
          <RunProgressBar analysisId={detail.analysis_id} progress={progress} />
        </div>
      ) : <p className="empty-state">Progress has not been captured for this run.</p>}
    </section>
  );
}
