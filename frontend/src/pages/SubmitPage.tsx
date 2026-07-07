import {Play, Plus, Search} from "lucide-react";
import {useState} from "react";
import {Link} from "react-router-dom";

import type {PgtaTarget, ScanCandidate} from "../api";

import {createRun, scanInput, submitRun} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {errorMessage} from "../lib/errors";
import {compactPipelineName} from "../lib/format";
import {deployedWorkflowTemplates} from "../mocks/platform";

const defaultRawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";
const pgtaTargets: Array<{value: PgtaTarget; label: string}> = [
  {value: "metadata", label: "metadata smoke"},
  {value: "dryrun_cnv", label: "CNV dry-run"},
  {value: "invalid_target", label: "failure smoke"},
  {value: "baseline_qc", label: "baseline QC smoke"},
];

export function SubmitPage() {
  const [projectName, setProjectName] = useState("Bioinformatics demo run");
  const [emailTo, setEmailTo] = useState("");
  const [reference, setReference] = useState("hg19");
  const [priority, setPriority] = useState("normal");
  const [runMode, setRunMode] = useState("dry-run");
  const [target, setTarget] = useState<PgtaTarget>("metadata");
  const [rawdataRoot, setRawdataRoot] = useState(defaultRawdataRoot);
  const [maxSamples, setMaxSamples] = useState(20);
  const [scanItems, setScanItems] = useState<ScanCandidate[]>([]);
  const [selectedSamples, setSelectedSamples] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);

  const selectedTemplate = deployedWorkflowTemplates[0];
  const selectedScanRows = scanItems.filter((item) => selectedSamples.has(item.sample_id));
  const pgtaNeedsMoreSamples = target === "baseline_qc" && selectedSamples.size < 2;

  async function handleScan() {
    setScanning(true);
    setError(null);
    setNotice(null);
    setSelectedSamples(new Set());
    try {
      const result = await scanInput({pipeline: "pgta", rawdata_root: rawdataRoot, max_samples: maxSamples});
      setScanItems(result.items);
      setNotice(`${result.items.length} candidate samples found${result.truncated ? " (truncated)" : ""}.`);
    } catch (scanError) {
      setScanItems([]);
      setError(errorMessage(scanError));
    } finally {
      setScanning(false);
    }
  }

  function toggleSample(sampleId: string) {
    setSelectedSamples((current) => {
      const next = new Set(current);
      if (next.has(sampleId)) next.delete(sampleId);
      else next.add(sampleId);
      return next;
    });
  }

  async function handleCreatePgta() {
    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createRun({
        pipeline: "pgta",
        project_name: projectName,
        target,
        rawdata_root: rawdataRoot,
        selected_samples: selectedScanRows,
        email_to: emailTo.trim() || null,
        note: `reference=${reference}; priority=${priority}; mode=${runMode}`,
      });
      setCreatedRunId(created.analysis_id);
      setNotice(`Created ${created.analysis_id}. Review then submit to Airflow.`);
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setCreating(false);
    }
  }

  async function handleSubmitCreated() {
    if (!createdRunId) return;
    setCreating(true);
    setError(null);
    try {
      await submitRun(createdRunId);
      setNotice(`Submitted ${createdRunId} to Airflow.`);
    } catch (submitError) {
      setError(errorMessage(submitError));
    } finally {
      setCreating(false);
    }
  }

  const canCreatePgta = selectedScanRows.length > 0 && !pgtaNeedsMoreSamples;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Controlled intake</p>
          <h1>Submit Task</h1>
          <p>Prepare the current PGT-A demo request with server-path scan, validation, and Airflow submission.</p>
        </div>
      </section>

      <div className="submit-grid">
        <section className="panel">
          <div className="section-heading">
            <h2>Run parameters</h2>
            <p>{selectedTemplate.description}</p>
          </div>
          <div className="form-grid">
            <label className="field">
              <span>Project name</span>
              <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
            </label>
            <label className="field">
              <span>Reference genome</span>
              <select value={reference} onChange={(event) => setReference(event.target.value)}>
                <option value="hg19">hg19</option>
                <option value="hg38">hg38</option>
                <option value="GRCh37">GRCh37</option>
                <option value="GRCh38">GRCh38</option>
              </select>
            </label>
            <label className="field">
              <span>Panel / capture kit</span>
              <input value="PGT-A baseline/demo defaults" readOnly />
            </label>
            <label className="field">
              <span>Priority</span>
              <select value={priority} onChange={(event) => setPriority(event.target.value)}>
                <option value="normal">normal</option>
                <option value="urgent">urgent</option>
                <option value="low">low</option>
              </select>
            </label>
            <label className="field">
              <span>Run mode</span>
              <select value={runMode} onChange={(event) => setRunMode(event.target.value)}>
                <option value="dry-run">dry-run</option>
                <option value="production-run">production-run</option>
              </select>
            </label>
            <label className="field">
              <span>Notification email</span>
              <input value={emailTo} placeholder="demo@example.com" onChange={(event) => setEmailTo(event.target.value)} />
            </label>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="section-heading split">
          <div>
            <h2>PGT-A server-path scan</h2>
            <p>Real backend path: scan allowlisted FASTQ directory, create run, then submit to Airflow.</p>
          </div>
          <StatusBadge status={selectedTemplate.implementationStatus} />
        </div>
        <div className="form-grid pgta-grid">
          <label className="field full">
            <span>Rawdata root</span>
            <input aria-label="Rawdata root" value={rawdataRoot} onChange={(event) => setRawdataRoot(event.target.value)} />
          </label>
          <label className="field">
            <span>Max samples</span>
            <input type="number" min={1} max={1000} value={maxSamples} onChange={(event) => setMaxSamples(Number(event.target.value) || 1)} />
          </label>
          <label className="field">
            <span>Target</span>
            <select aria-label="Target" value={target} onChange={(event) => setTarget(event.target.value as PgtaTarget)}>
              {pgtaTargets.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="panel-actions">
          <button className="button ghost" type="button" disabled={scanning || !rawdataRoot.trim()} onClick={() => void handleScan()}>
            <Search size={15} />
            Scan
          </button>
          <button className="button primary" type="button" disabled={creating || !canCreatePgta} onClick={() => void handleCreatePgta()}>
            <Plus size={15} />
            Create Run
          </button>
          {createdRunId ? (
            <button className="button primary" type="button" disabled={creating} onClick={() => void handleSubmitCreated()}>
              <Play size={15} />
              Submit to Airflow
            </button>
          ) : null}
        </div>
        {pgtaNeedsMoreSamples ? <p className="inline-error">baseline_qc requires at least two selected PGT-A samples.</p> : null}
        <CandidateTable items={scanItems} selected={selectedSamples} onToggle={toggleSample} />
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Submit preview</h2>
          <p>Execution is blocked until PGT-A server-path scan returns selected samples and the target guard passes.</p>
        </div>
        <div className="preview-grid">
          <div><span>Pipeline</span><strong>{compactPipelineName("pgta")}</strong></div>
          <div><span>Project</span><strong>{projectName || "not set"}</strong></div>
          <div><span>Reference</span><strong>{reference}</strong></div>
          <div><span>Mode</span><strong>{runMode}</strong></div>
          <div><span>Estimated workflow</span><strong>{selectedTemplate.steps.map((step) => step.name).join(" -> ")}</strong></div>
        </div>
        {createdRunId ? (
          <p className="success-note">
            Created run <Link to={`/runs/${encodeURIComponent(createdRunId)}`}>{createdRunId}</Link>
          </p>
        ) : null}
      </section>

      {notice ? <div className="success-note" role="status">{notice}</div> : null}
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
    </div>
  );
}

function CandidateTable({
  items,
  selected,
  onToggle,
}: {
  items: ScanCandidate[];
  selected: Set<string>;
  onToggle: (sampleId: string) => void;
}) {
  return (
    <div className="table-wrap">
      <table className="data-table compact">
        <thead>
          <tr><th>select</th><th>sample_id</th><th>R1</th><th>R2</th></tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.sample_id}-${item.r1}`}>
              <td>
                <input
                  aria-label={`Select sample ${item.sample_id}`}
                  checked={selected.has(item.sample_id)}
                  type="checkbox"
                  onChange={() => onToggle(item.sample_id)}
                />
              </td>
              <td>{item.sample_id}</td>
              <td className="path-text">{item.r1}</td>
              <td className="path-text">{item.r2}</td>
            </tr>
          ))}
          {items.length === 0 ? <tr><td className="empty-cell" colSpan={4}>No candidate samples scanned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}
