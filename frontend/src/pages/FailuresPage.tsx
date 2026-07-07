import {useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {RunSummary} from "../api";

import {getRunDetail, getRunRules, listRuns} from "../api";
import {ErrorPanel} from "../components/ErrorPanel";
import {StatusBadge} from "../components/StatusBadge";
import {errorMessage, parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatDate} from "../lib/format";
import {isFailedStatus} from "../lib/status";

type FailureRow = {
  run: RunSummary;
  failedStep: string | null;
  errorSummary: string | null;
};

export function FailuresPage() {
  const [rows, setRows] = useState<FailureRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    async function loadFailures() {
      setLoading(true);
      setError(null);
      try {
        const payload = await listRuns();
        const failed = payload.items.filter((run) => isFailedStatus(run.status)).slice(0, 10);
        const details = await Promise.all(
          failed.map(async (run) => {
            const [detail, rules] = await Promise.all([
              getRunDetail(run.analysis_id).catch(() => null),
              getRunRules(run.analysis_id).catch(() => ({items: []})),
            ]);
            const failedRule = rules.items.find((rule) => isFailedStatus(rule.status));
            return {run, failedStep: failedRule?.rule || null, errorSummary: detail?.error_summary || null};
          }),
        );
        if (!disposed) setRows(details);
      } catch (loadError) {
        if (!disposed) setError(errorMessage(loadError));
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void loadFailures();
    return () => {
      disposed = true;
    };
  }, []);

  const firstDiagnosis = useMemo(() => {
    const first = rows[0];
    return first ? parseErrorSummary(first.errorSummary, first.failedStep) : null;
  }, [rows]);

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Failure triage</p>
          <h1>Recent failed runs</h1>
          <p>Failed step, error type, stderr excerpt, retry suggestion, and link to detail without SSH first.</p>
        </div>
      </section>
      {loading ? <p className="muted">Loading failures...</p> : null}
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      <ErrorPanel diagnosis={firstDiagnosis} />
      <section className="panel">
        <div className="section-heading">
          <h2>Failure queue</h2>
          <p>Retry suggestion: inspect stderr, confirm failed rule/sample, then resume or rerun selected rule only.</p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>run_id</th><th>pipeline</th><th>status</th><th>failed step</th><th>created_at</th><th>stderr excerpt</th><th>action</th></tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const diagnosis = parseErrorSummary(row.errorSummary, row.failedStep);
                return (
                  <tr key={row.run.analysis_id}>
                    <td className="mono path-text">{row.run.analysis_id}</td>
                    <td>{compactPipelineName(row.run.pipeline)}</td>
                    <td><StatusBadge status={row.run.status} /></td>
                    <td>{diagnosis?.failedStep || "workflow"}</td>
                    <td>{formatDate(row.run.created_at)}</td>
                    <td>{diagnosis?.stderrExcerpt.slice(0, 160) || "No stderr excerpt available."}</td>
                    <td><Link className="button ghost" to={`/runs/${encodeURIComponent(row.run.analysis_id)}`}>Detail</Link></td>
                  </tr>
                );
              })}
              {rows.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No failed runs returned.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
