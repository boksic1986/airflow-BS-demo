import type {RunProgress} from "../lib/runProgress";

export function RunProgressBar({analysisId, progress}: {analysisId: string; progress: RunProgress}) {
  const tone = progressTone(progress);
  return (
    <div className="run-progress">
      <div className="run-progress-meta">
        <strong>{progress.label}</strong>
        <span>{progress.currentStep}</span>
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
      <p>{progress.note}</p>
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
