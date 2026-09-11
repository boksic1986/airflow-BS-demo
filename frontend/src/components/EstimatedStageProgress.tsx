import type {StageEstimate} from "../api";

export function EstimatedStageProgress({stage}: {stage?: StageEstimate | null}) {
  if (stage?.estimated_progress_percent == null) return null;
  return <div className="estimated-stage-progress" title="Display-only estimate from a fixed median of matching successful stage executions; not measured progress.">
    <span>Estimated {stage.estimated_progress_percent}%</span>
    <progress aria-label="Estimated stage progress" value={stage.estimated_progress_percent} max={100} />
    {stage.estimate_overrun ? <small>Still executing — historical baseline exceeded</small> : null}
  </div>;
}
