import {useEffect, useState} from "react";
import {Link} from "react-router-dom";

import type {RunSummary, Sample} from "../api";

import {getRunSamples, listRuns} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {errorMessage} from "../lib/errors";
import {compactPipelineName} from "../lib/format";
import {deployedWorkflowTemplates} from "../mocks/platform";

type SampleRow = {
  sample_id: string;
  family_id?: string | null;
  pipeline: string;
  run_id?: string;
  status?: string | null;
  fastq_path?: string | null;
  qc_status?: string | null;
  report_status?: string | null;
  error_summary?: string | null;
};
const visiblePipelines = new Set<string>(deployedWorkflowTemplates.map((pipeline) => pipeline.id));

export function SamplesPage() {
  const [rows, setRows] = useState<SampleRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    async function loadSamples() {
      setLoading(true);
      setError(null);
      try {
        const runs = await listRuns();
        const visibleRuns = runs.items.filter((run) => visiblePipelines.has(run.pipeline)).slice(0, 8);
        const samplePayloads = await Promise.all(
          visibleRuns.map(async (run: RunSummary) => ({
            run,
            samples: await getRunSamples(run.analysis_id).catch(() => ({items: [] as Sample[]})),
          })),
        );
        if (disposed) return;
        setRows(
          samplePayloads.flatMap(({run, samples}) =>
            samples.items.map((sample) => ({
              sample_id: sample.sample_id,
              family_id: sample.family_id,
              pipeline: run.pipeline,
              run_id: run.analysis_id,
              status: sample.status,
              fastq_path: sample.fq1 || sample.fq2,
              qc_status: sample.qc_status,
              report_status: run.status === "success" ? "available if artifact exists" : "not generated",
              error_summary: run.status === "failed" ? "see run detail" : null,
            })),
          ),
        );
      } catch (loadError) {
        if (!disposed) setError(errorMessage(loadError));
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void loadSamples();
    return () => {
      disposed = true;
    };
  }, []);

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Sample resource</p>
          <h1>Samples</h1>
          <p>Sample view across deployed PGT-A and NIPT Docker runs, workflow status, QC status, and run detail links.</p>
        </div>
      </section>
      <section className="panel">
        {loading ? <p className="muted">Loading samples...</p> : null}
        {error ? <div className="inline-error" role="alert">{error}</div> : null}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>sample_id</th>
                <th>family_id</th>
                <th>pipeline</th>
                <th>status</th>
                <th>fastq_path</th>
                <th>qc_status</th>
                <th>report_status</th>
                <th>error_summary</th>
                <th>action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.run_id || "mock"}-${row.sample_id}`}>
                  <td>{row.sample_id}</td>
                  <td>{row.family_id || "not set"}</td>
                  <td>{compactPipelineName(row.pipeline)}</td>
                  <td><StatusBadge status={row.status || "unknown"} /></td>
                  <td className="path-text">{row.fastq_path || "not set"}</td>
                  <td><StatusBadge status={row.qc_status || "unknown"} size="sm" /></td>
                  <td>{row.report_status || "not set"}</td>
                  <td>{row.error_summary || "none"}</td>
                  <td>{row.run_id ? <Link className="button ghost" to={`/runs/${encodeURIComponent(row.run_id)}`}>Run</Link> : "mock"}</td>
                </tr>
              ))}
              {rows.length === 0 ? <tr><td className="empty-cell" colSpan={9}>No samples available.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
