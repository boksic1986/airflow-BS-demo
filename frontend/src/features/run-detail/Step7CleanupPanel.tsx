import {useRef, useState} from "react";

import type {Step7CleanupCapability} from "../../api";
import {formatDate} from "../../lib/format";


export function Step7CleanupPanel({capability, canManage = true, acting = false, onCleanup}: {
  capability: Step7CleanupCapability;
  canManage?: boolean;
  acting?: boolean;
  onCleanup: (batchConfirmation: string, retryFailed?: boolean) => void;
}) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [batchConfirmation, setBatchConfirmation] = useState("");
  const batchTokenRef = useRef<HTMLInputElement>(null);
  const requiredBatch = capability.required_batch.trim();
  const normalizedConfirmation = batchConfirmation.trim();
  const matches = requiredBatch.length > 0 && normalizedConfirmation === requiredBatch;
  const latest = capability.latest_action;
  const retryFailed = Boolean(latest?.status === "failed" && capability.retry_available);
  const canRequest = capability.available || retryFailed;

  async function copyRequiredBatch() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(requiredBatch);
      } else {
        batchTokenRef.current?.select();
        if (!document.execCommand("copy")) throw new Error("copy unavailable");
      }
    } catch {
      batchTokenRef.current?.focus();
      batchTokenRef.current?.select();
    }
  }

  return (
    <section className="step7-cleanup-compact" aria-label="Step7 SFS cleanup">
      {latest ? (
        <div className="maintenance-progress" aria-label="Step7 maintenance progress">
          <h3>Step7 progress</h3>
          <p className="maintenance-progress-stage">{step7StageLabel(latest.status)}</p>
          <p className="step7-compact-meta">Generation {latest.generation ?? 1} · Updated {formatDate(latest.ended_at || latest.started_at || latest.created_at)}</p>
          {latest.error_message ? <div className="inline-error" role="alert">{latest.error_message}</div> : null}
        </div>
      ) : null}
      {!canRequest && capability.reason ? <p className="muted step7-block-reason">{step7ReasonLabel(capability.reason)}</p> : null}
      {canManage && canRequest ? (
        <details className="step7-action-details">
          <summary>{retryFailed ? "Retry SFS release" : "Release SFS data"}</summary>
          <p className="muted">Deletes only this run's frozen SFS analysis and linkage directories. OBS data is retained.</p>
          <label className="field checkbox-field">
            <input
              type="checkbox"
              aria-label="Acknowledge SFS cleanup"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
            />
            <span>I verified Step5 and Step6 results and understand SFS cleanup is destructive.</span>
          </label>
          <div className="step7-copy-row">
            <input
              ref={batchTokenRef}
              className="confirmation-copy-value"
              aria-label="Required Step7 Batch"
              readOnly
              value={requiredBatch}
              onFocus={(event) => event.currentTarget.select()}
            />
            <button
              className="button ghost"
              type="button"
              aria-label={`Copy batch ${requiredBatch}`}
              onClick={() => void copyRequiredBatch()}
            >
              Copy
            </button>
          </div>
          <label className="field">
            <span>Type <strong className="confirmation-token">{requiredBatch}</strong> to confirm</span>
            <input
              aria-label="Step7 Batch confirmation"
              autoComplete="off"
              value={batchConfirmation}
              onChange={(event) => setBatchConfirmation(event.target.value)}
            />
          </label>
          {normalizedConfirmation && !matches ? (
            <p className="field-error" role="status">Confirmation must exactly match {requiredBatch}.</p>
          ) : null}
          <button
            className="button danger"
            type="button"
            disabled={acting || !acknowledged || !matches}
            onClick={() => onCleanup(normalizedConfirmation, retryFailed)}
          >
            {retryFailed ? "Retry Step7 SFS cleanup" : "Run Step7 SFS cleanup"}
          </button>
        </details>
      ) : null}
    </section>
  );
}

function step7ReasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    cleanup_in_progress: "SFS cleanup is in progress.",
    cleanup_completed: "SFS cleanup completed.",
    cleanup_failed: "SFS cleanup failed; an administrator can retry it.",
    cce_workload_active: "CCE workload evidence is still active.",
    transfer_lease_active: "A transfer lease is still active.",
    download_not_verified: "Result download has not been verified.",
    results_not_materialized: "Local results have not been materialized.",
    run_not_successful: "Workflow is not successful.",
    runtime_unavailable: "SFS cleanup runtime is unavailable.",
  };
  return labels[reason] || reason.replaceAll("_", " ");
}

function step7StageLabel(status: string): string {
  switch (status.toLowerCase()) {
    case "requested":
    case "queued":
      return "Waiting for Step7 worker";
    case "running":
      return "Cleaning frozen SFS workspace";
    case "success":
      return "SFS cleanup completed";
    case "failed":
      return "SFS cleanup failed";
    default:
      return status;
  }
}
