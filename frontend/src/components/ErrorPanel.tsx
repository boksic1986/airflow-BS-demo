import {AlertTriangle, Copy} from "lucide-react";

import type {ParsedErrorSummary} from "../lib/errors";

export function ErrorPanel({diagnosis}: {diagnosis: ParsedErrorSummary | null}) {
  if (!diagnosis) return null;

  async function copyExcerpt() {
    await navigator.clipboard?.writeText(diagnosis?.stderrExcerpt || "");
  }

  return (
    <section className="error-panel" aria-label="Failure diagnosis">
      <div className="section-heading inline">
        <AlertTriangle size={18} />
        <h2>Failure diagnosis</h2>
      </div>
      <dl className="definition-grid">
        <div>
          <dt>Failed step</dt>
          <dd>{diagnosis.failedStep}</dd>
        </div>
        <div>
          <dt>Exit code</dt>
          <dd>{diagnosis.exitCode}</dd>
        </div>
        <div>
          <dt>Error log path</dt>
          <dd className="path-text">{diagnosis.errorLogPath}</dd>
        </div>
        <div>
          <dt>Possible reason</dt>
          <dd>{diagnosis.possibleReason}</dd>
        </div>
      </dl>
      <pre className="diagnostic-excerpt">{diagnosis.stderrExcerpt}</pre>
      <div className="panel-actions">
        <button className="button ghost" type="button" onClick={() => void copyExcerpt()}>
          <Copy size={15} />
          Copy error summary
        </button>
        <span>{diagnosis.suggestedAction}</span>
      </div>
    </section>
  );
}
