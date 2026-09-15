import type {StageEstimate} from "../api";
import {RunProgressBar} from "./RunProgressBar";
import {formatPercent, formatSecondsDuration} from "../lib/format";
import {isActiveStatus} from "../lib/status";

export function EstimatedStageProgress({stage, status, compact = false}: {stage?: StageEstimate | null; status?: string; compact?: boolean}) {
  if (stage?.estimate_model === "stage_median_linear_v1") {
    const percent = stage.estimated_progress_percent;
    const note = stage.estimate_frozen ? "预估已冻结，执行已结束" : stage.estimate_overrun ? "已超过预计时间，等待完成" : stage.estimate_remaining_seconds != null ? `预计剩余 ${formatSecondsDuration(stage.estimate_remaining_seconds)}` : "缺少足够历史或有效开始时间";
    return <div className="estimated-stage-progress">
      <RunProgressBar analysisId={stage.estimate_execution_id || "stage"} compact={compact} progress={{
        percent: percent ?? 0, available: percent != null, estimated: true,
        label: percent == null ? "暂无预估" : `预估进度 ${formatPercent(percent)}`,
        currentStep: (stage.estimate_generation ?? 1) > 1 && !stage.estimate_frozen && status === "running" ? "续跑中" : "",
        note, notInAirflow: false, status: stage.estimate_frozen && isActiveStatus(status || "") ? "unknown" : status,
        failedStep: status === "failed" ? "stage" : undefined,
      }} />
      {compact ? <small>{(stage.estimate_generation ?? 1) > 1 && !stage.estimate_frozen && status === "running" ? "续跑中 · " : ""}{note}</small> : null}
    </div>;
  }
  if (stage?.estimated_progress_percent == null) return null;
  return <div className="estimated-stage-progress" title="Display-only estimate from a fixed median of matching successful stage executions; not measured progress.">
    <span>Estimated {stage.estimated_progress_percent}%</span>
    <progress aria-label="Estimated stage progress" value={stage.estimated_progress_percent} max={100} />
    {stage.estimate_frozen ? <small>Estimate frozen — execution ended</small> : stage.estimate_overrun ? <small>Still executing — historical baseline exceeded</small> : null}
  </div>;
}
