import type {RunProgress} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus, normalizeStatus} from "../lib/status";

export function RunProgressBar({analysisId, progress, compact = false}: {analysisId: string; progress: RunProgress; compact?: boolean}) {
  const tone = progressTone(progress);
  if (progress.available === false) {
    const status = normalizeStatus(progress.status);
    const active = isActiveStatus(status);
    const terminalSuccess = status === "success";
    const failed = isFailedStatus(status);
    const label = active
      ? "Waiting for runtime evidence"
      : terminalSuccess
        ? "Stage complete"
        : failed
          ? "Stage failed"
          : "Waiting to start";
    return (
      <div className="run-progress unavailable">
        <div className={compact ? "run-progress-meta align-end" : "run-progress-meta"}><strong>{label}</strong></div>
        <div
          aria-label={`${analysisId} progress pending exact measurement`}
          aria-valuetext={label}
          className={`progress-track progress-${failed ? "failed" : terminalSuccess ? "success" : "queued"} ${active ? "progress-indeterminate" : ""}`}
          role="progressbar"
        >
          <span style={{width: terminalSuccess || failed ? "100%" : active ? "34%" : "0%"}} />
        </div>
        {!compact ? <p>{progress.note}</p> : null}
      </div>
    );
  }
  return (
    <div className="run-progress">
      <div className={compact ? "run-progress-meta align-end" : "run-progress-meta"}>
        <strong>{progress.label}</strong>
        {!compact ? <span>{progress.currentStep}</span> : null}
      </div>
      <div
        aria-label={`${analysisId} progress`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={progress.percent}
        className={`progress-track progress-${tone}`}
        role="progressbar"
      >
        <span style={{width: `${Math.min(100, Math.max(0, progress.percent))}%`}} />
      </div>
      {!compact ? <p>{progress.note}</p> : null}
    </div>
  );
}

function progressTone(progress: RunProgress): "queued" | "running" | "success" | "warning" | "failed" {
  const text = `${progress.currentStep} ${progress.note}`.toLowerCase();
  if (text.includes("fail") || text.includes("error") || progress.failedStep) return "failed";
  if (progress.percent >= 100) return "success";
  if (text.includes("warn")) return "warning";
  if (progress.notInAirflow || progress.percent <= 10) return "queued";
  return "running";
}
