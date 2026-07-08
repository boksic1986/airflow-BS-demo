import type {RunProgress} from "../lib/runProgress";

export function RunProgressBar({analysisId, progress}: {analysisId: string; progress: RunProgress}) {
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
        className="progress-track"
        role="progressbar"
      >
        <span style={{width: `${Math.min(100, Math.max(0, progress.percent))}%`}} />
      </div>
      <p>{progress.note}</p>
    </div>
  );
}
