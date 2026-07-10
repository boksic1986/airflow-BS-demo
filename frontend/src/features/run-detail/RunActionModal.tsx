export type PgtaStage = "mapping" | "metadata" | "baseline_qc";

export function RunActionModal({canResume, disabled, onClose, onResume, onRerunStage}: {
  canResume: boolean;
  disabled: boolean;
  onClose: () => void;
  onResume: () => void;
  onRerunStage: (stage: PgtaStage) => void;
}) {
  return (
    <div className="modal-backdrop">
      <section aria-modal="true" className="modal-panel run-action-modal" role="dialog" aria-label="Run action">
        <div className="section-heading split">
          <div>
            <h2>Run action</h2>
            <p>Controlled PGT-A baseline_qc actions only.</p>
          </div>
          <button className="button ghost" type="button" onClick={onClose}>Close</button>
        </div>
        <div className="run-action-list">
          <button disabled={disabled || !canResume} type="button" onClick={onResume}>
            <strong>Resume failed baseline_qc</strong><span>Reuse the workdir and resume incomplete outputs.</span>
          </button>
          <button disabled={disabled} type="button" onClick={() => onRerunStage("mapping")}>
            <strong>Rerun mapping stage</strong><span>Continue through metadata and baseline QC.</span>
          </button>
          <button disabled={disabled} type="button" onClick={() => onRerunStage("metadata")}>
            <strong>Rerun metadata stage</strong><span>Continue through baseline QC.</span>
          </button>
          <button disabled={disabled} type="button" onClick={() => onRerunStage("baseline_qc")}>
            <strong>Rerun baseline QC stage</strong><span>Use existing mapping and metadata outputs.</span>
          </button>
        </div>
      </section>
    </div>
  );
}
