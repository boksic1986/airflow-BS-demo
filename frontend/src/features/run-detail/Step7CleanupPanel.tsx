import {useRef, useState} from "react";

import type {Step7CleanupCapability} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {formatDate} from "../../lib/format";


export function Step7CleanupPanel({capability, acting = false, onCleanup}: {
  capability: Step7CleanupCapability;
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
    <section className="panel destructive-panel" aria-label="Step7 SFS cleanup">
      <div className="section-heading split">
        <div>
          <h2>SFS cleanup</h2>
          <p>Step7 deletes only the frozen run SFS analysis and linkage directories. OBS data is not deleted.</p>
        </div>
        {latest ? <StatusBadge status={latest.status} /> : null}
      </div>
      {latest ? (
        <div className="maintenance-progress" aria-label="Step7 maintenance progress">
          <h3>Step7 progress</h3>
          <p className="maintenance-progress-stage">{step7StageLabel(latest.status)}</p>
          <dl className="detail-list compact">
            <div><dt>Requested</dt><dd>{formatDate(latest.created_at)}</dd></div>
            <div><dt>Generation</dt><dd>{latest.generation ?? 1}</dd></div>
            <div><dt>Started</dt><dd>{formatDate(latest.started_at)}</dd></div>
            <div><dt>Finished</dt><dd>{formatDate(latest.ended_at)}</dd></div>
          </dl>
          <p className="muted">Detailed file progress unavailable</p>
          {latest.error_message ? <div className="inline-error" role="alert">{latest.error_message}</div> : null}
        </div>
      ) : null}
      {canRequest ? (
        <>
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
        </>
      ) : null}
    </section>
  );
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
