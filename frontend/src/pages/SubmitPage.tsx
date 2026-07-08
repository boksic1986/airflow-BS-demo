import {ChevronDown, ChevronRight, Play, Plus, Search} from "lucide-react";
import type {ReactNode} from "react";
import {useEffect, useState} from "react";
import {Link} from "react-router-dom";

import type {NiptRunMode, PgtaTarget, RunDetail, ScanCandidate} from "../api";

import {createRun, getInputRoots, getRunDetail, scanInput, submitRun, syncAirflow} from "../api";
import {PipelineSelector} from "../components/PipelineSelector";
import {StatusBadge} from "../components/StatusBadge";
import {errorMessage} from "../lib/errors";
import {compactPipelineName} from "../lib/format";
import {deployedWorkflowTemplates} from "../mocks/platform";

const defaultPgtaRawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";
const defaultNiptRawdataRoot = "/opt/pipelines/NIPT/fastq";
const pgtaTargets: Array<{value: PgtaTarget; label: string}> = [
  {value: "metadata", label: "metadata smoke"},
  {value: "dryrun_cnv", label: "CNV dry-run"},
  {value: "invalid_target", label: "failure smoke"},
  {value: "baseline_qc", label: "baseline QC smoke"},
];
const handoffSyncAttempts = 6;
const handoffSyncDelayMs = 2500;
const fallbackTemplate = deployedWorkflowTemplates.find((pipeline) => pipeline.id === "pgta") || deployedWorkflowTemplates[0]!;

export function SubmitPage() {
  const [selectedPipeline, setSelectedPipeline] = useState<"pgta" | "nipt_docker">("pgta");
  const [projectName, setProjectName] = useState("Bioinformatics demo run");
  const [emailTo, setEmailTo] = useState("");
  const [reference, setReference] = useState("hg19");
  const [priority, setPriority] = useState("normal");
  const [runMode, setRunMode] = useState("dry-run");
  const [niptRunMode, setNiptRunMode] = useState<NiptRunMode>("mount_smoke");
  const [niptCores, setNiptCores] = useState(40);
  const [target, setTarget] = useState<PgtaTarget>("metadata");
  const [rawdataRoot, setRawdataRoot] = useState(defaultPgtaRawdataRoot);
  const [rootOptions, setRootOptions] = useState<string[]>([defaultPgtaRawdataRoot]);
  const [maxSamples, setMaxSamples] = useState(20);
  const [scanItems, setScanItems] = useState<ScanCandidate[]>([]);
  const [selectedSamples, setSelectedSamples] = useState<Set<string>>(new Set());
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [handoffWarning, setHandoffWarning] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdRunIds, setCreatedRunIds] = useState<string[]>([]);
  const [handoffRuns, setHandoffRuns] = useState<RunDetail[]>([]);

  const selectedTemplate = deployedWorkflowTemplates.find((pipeline) => pipeline.id === selectedPipeline) || fallbackTemplate;
  const selectedScanRows = scanItems.filter((item) => selectedSamples.has(item.sample_id));
  const pgtaNeedsMoreSamples = selectedPipeline === "pgta" && target === "baseline_qc" && selectedSamples.size < 2;
  const canCreatePgta = selectedScanRows.length > 0 && !pgtaNeedsMoreSamples;
  const canCreateNipt = selectedScanRows.length > 0 && Boolean(projectName.trim());
  const canCreateSelected = selectedPipeline === "nipt_docker" ? canCreateNipt : canCreatePgta;

  useEffect(() => {
    let disposed = false;
    const fallbackRoot = selectedPipeline === "nipt_docker" ? defaultNiptRawdataRoot : defaultPgtaRawdataRoot;
    getInputRoots(selectedPipeline)
      .then((payload) => {
        if (disposed) return;
        const roots = payload.roots.length ? payload.roots : [fallbackRoot];
        setRootOptions(roots);
        setRawdataRoot((current) => {
          if (roots.includes(current)) return current;
          if (selectedPipeline === "pgta" && current === defaultNiptRawdataRoot) return roots[0]!;
          if (selectedPipeline === "nipt_docker" && current === defaultPgtaRawdataRoot) return roots[0]!;
          return current.trim() ? current : roots[0]!;
        });
      })
      .catch(() => {
        if (!disposed) {
          setRootOptions([fallbackRoot]);
          setRawdataRoot((current) => current.trim() || fallbackRoot);
        }
      });
    return () => {
      disposed = true;
    };
  }, [selectedPipeline]);

  async function handleScan() {
    setScanning(true);
    setError(null);
    setNotice(null);
    setSelectedSamples(new Set());
    setExpandedFolders(new Set());
    setCreatedRunIds([]);
    setHandoffRuns([]);
    setHandoffWarning(null);
    try {
      const result = await scanInput({pipeline: selectedPipeline, rawdata_root: rawdataRoot, max_samples: maxSamples});
      setScanItems(result.items);
      setNotice(`${result.items.length} ${compactPipelineName(selectedPipeline)} candidate samples found${result.truncated ? " (truncated)" : ""}.`);
    } catch (scanError) {
      setScanItems([]);
      setError(errorMessage(scanError));
    } finally {
      setScanning(false);
    }
  }

  function handlePipelineChange(value: string) {
    if (value !== "pgta" && value !== "nipt_docker") return;
    setSelectedPipeline(value);
    setRawdataRoot(value === "nipt_docker" ? defaultNiptRawdataRoot : defaultPgtaRawdataRoot);
    setRootOptions([value === "nipt_docker" ? defaultNiptRawdataRoot : defaultPgtaRawdataRoot]);
    setScanItems([]);
    setSelectedSamples(new Set());
    setExpandedFolders(new Set());
    setCreatedRunIds([]);
    setHandoffRuns([]);
    setHandoffWarning(null);
    setNotice(null);
    setError(null);
  }

  function toggleSample(sampleId: string) {
    setSelectedSamples((current) => {
      const next = new Set(current);
      if (next.has(sampleId)) next.delete(sampleId);
      else next.add(sampleId);
      return next;
    });
  }

  function toggleFolder(sourceDir: string, items: ScanCandidate[]) {
    setSelectedSamples((current) => {
      const next = new Set(current);
      const allSelected = items.every((item) => next.has(item.sample_id));
      for (const item of items) {
        if (allSelected) next.delete(item.sample_id);
        else next.add(item.sample_id);
      }
      return next;
    });
  }

  function toggleExpandedFolder(sourceDir: string) {
    setExpandedFolders((current) => {
      const next = new Set(current);
      if (next.has(sourceDir)) next.delete(sourceDir);
      else next.add(sourceDir);
      return next;
    });
  }

  async function createSelectedRuns(): Promise<RunDetail[]> {
    if (selectedPipeline === "nipt_docker") {
      const batches = groupCandidates(selectedScanRows, rawdataRoot);
      return Promise.all(
        batches.map((batch) =>
          createRun({
            pipeline: "nipt_docker",
            project_name: batches.length > 1 ? `${projectName} ${batch.folderName}` : projectName,
            rawdata_root: rawdataRoot,
            selected_samples: batch.items,
            run_mode: niptRunMode,
            cores: niptCores,
            email_to: emailTo.trim() || null,
            note: `reference=${reference}; priority=${priority}; mode=${runMode}; batch=${batch.relativePath}/${batch.folderName}`,
          }),
        ),
      );
    }
    return [
      await createRun({
        pipeline: "pgta",
        project_name: projectName,
        target,
        rawdata_root: rawdataRoot,
        selected_samples: selectedScanRows,
        email_to: emailTo.trim() || null,
        note: `reference=${reference}; priority=${priority}; mode=${runMode}`,
      }),
    ];
  }

  async function handleCreateOnly() {
    setCreating(true);
    setError(null);
    setNotice(null);
    setHandoffWarning(null);
    setCreatedRunIds([]);
    setHandoffRuns([]);
    try {
      const created = await createSelectedRuns();
      setCreatedRunIds(created.map((run) => run.analysis_id));
      setNotice(`Created ${created.length} run${created.length === 1 ? "" : "s"}. Not visible in Airflow until submitted.`);
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setCreating(false);
    }
  }

  async function handleCreateAndSubmit() {
    setCreating(true);
    setError(null);
    setNotice(null);
    setHandoffWarning(null);
    setCreatedRunIds([]);
    setHandoffRuns([]);
    try {
      const createdRuns = await createSelectedRuns();
      setCreatedRunIds(createdRuns.map((run) => run.analysis_id));
      const submittedRuns: RunDetail[] = [];
      const missingDagRuns: string[] = [];
      for (const created of createdRuns) {
        const submitted = await submitRun(created.analysis_id);
        const synced = submitted.dag_run_id ? await syncSubmittedRun(created.analysis_id, submitted) : null;
        const detail = synced || (await getRunDetail(created.analysis_id).catch(() => submitted));
        submittedRuns.push(detail);
        if (!submitted.dag_run_id && !detail.dag_run_id) {
          missingDagRuns.push(created.analysis_id);
        }
      }
      setHandoffRuns(submittedRuns);
      if (missingDagRuns.length) {
        setHandoffWarning(`Submit returned without dag_run_id for ${missingDagRuns.join(", ")}; check backend/Airflow handoff.`);
      }
      setNotice(`Submitted ${createdRuns.length} run${createdRuns.length === 1 ? "" : "s"} to Airflow.`);
    } catch (submitError) {
      setError(errorMessage(submitError));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Controlled intake</p>
          <h1>Submit Task</h1>
          <p>Prepare deployed PGT-A or NIPT Docker requests from scanned server batches, then submit them to Airflow.</p>
        </div>
      </section>

      <section className="panel">
        <PipelineSelector pipelines={deployedWorkflowTemplates} value={selectedPipeline} onChange={handlePipelineChange} />
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
              <input value={selectedPipeline === "nipt_docker" ? "NIPT Docker scanned chip batch" : "PGT-A baseline/demo defaults"} readOnly />
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
            <h2>{selectedPipeline === "nipt_docker" ? "NIPT Docker server-path scan" : "PGT-A server-path scan"}</h2>
            <p>
              {selectedPipeline === "nipt_docker"
                ? "Scan an allowlisted NIPT FASTQ root, select one chip folder or individual clean FASTQ pairs, then create one run for that batch."
                : "Scan an allowlisted PGT-A FASTQ directory, select samples, create a run, then submit it to Airflow."}
            </p>
          </div>
          <StatusBadge status={selectedTemplate.implementationStatus} />
        </div>
        <div className="form-grid pgta-grid">
          <label className="field full">
            <span>Scan root</span>
            <input
              aria-label="Rawdata root"
              list="input-root-options"
              value={rawdataRoot}
              onChange={(event) => setRawdataRoot(event.target.value)}
            />
            <datalist id="input-root-options">
              {rootOptions.map((root) => (
                <option key={root} value={root} />
              ))}
            </datalist>
          </label>
          <label className="field">
            <span>Max samples</span>
            <input type="number" min={1} max={1000} value={maxSamples} onChange={(event) => setMaxSamples(Number(event.target.value) || 1)} />
          </label>
          {selectedPipeline === "pgta" ? (
            <label className="field">
              <span>Target</span>
              <select aria-label="Target" value={target} onChange={(event) => setTarget(event.target.value as PgtaTarget)}>
                {pgtaTargets.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="field">
                <span>NIPT run mode</span>
                <select aria-label="NIPT run mode" value={niptRunMode} onChange={(event) => setNiptRunMode(event.target.value as NiptRunMode)}>
                  <option value="mount_smoke">mount_smoke</option>
                  <option value="full_run">full_run (requires backend env)</option>
                </select>
              </label>
              <label className="field">
                <span>NIPT cores</span>
                <input aria-label="NIPT cores" type="number" min={1} max={40} value={niptCores} onChange={(event) => setNiptCores(Number(event.target.value) || 1)} />
              </label>
            </>
          )}
        </div>
        <div className="panel-actions">
          <button className="button ghost" type="button" disabled={scanning || !rawdataRoot.trim()} onClick={() => void handleScan()}>
            <Search size={15} />
            Scan
          </button>
          <button className="button primary" type="button" disabled={creating || !canCreateSelected} onClick={() => void handleCreateAndSubmit()}>
            <Play size={15} />
            Create and submit to Airflow
          </button>
          <button className="button ghost" type="button" disabled={creating || !canCreateSelected} onClick={() => void handleCreateOnly()}>
            <Plus size={15} />
            Create only
          </button>
        </div>
        {pgtaNeedsMoreSamples ? <p className="inline-error">baseline_qc requires at least two selected PGT-A samples.</p> : null}
        {selectedPipeline === "nipt_docker" && niptRunMode === "full_run" ? (
          <p className="inline-error">full_run is disabled unless backend NIPT_ALLOW_HEAVY_RUN=true; use mount_smoke for normal demo acceptance.</p>
        ) : null}
        <CandidateFolderTable
          expanded={expandedFolders}
          items={scanItems}
          rawdataRoot={rawdataRoot}
          selected={selectedSamples}
          onToggleFolder={toggleFolder}
          onToggleSample={toggleSample}
          onToggleExpanded={toggleExpandedFolder}
        />
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Submit preview</h2>
          <p>Execution is blocked until the selected pipeline scan returns validated FASTQ pairs and the run guard passes.</p>
        </div>
        <div className="submit-preview-list">
          <PreviewField label="Pipeline" value={<strong className="preview-pill">{compactPipelineName(selectedPipeline)}</strong>} />
          <PreviewField label="Project" value={projectName || "not set"} />
          <PreviewField label="Reference" value={reference} />
          <PreviewField label="Mode" value={runMode} />
          <PreviewField label="Selected samples" value={String(selectedScanRows.length)} />
          {selectedPipeline === "pgta" ? <PreviewField label="PGT-A target" value={target} /> : null}
          {selectedPipeline === "nipt_docker" ? <PreviewField label="NIPT run mode" value={niptRunMode} /> : null}
          <PreviewField label="Scan root" value={rawdataRoot || "not set"} wide mono />
          <PreviewField label="Estimated workflow" value={selectedTemplate.steps.map((step) => step.name).join(" -> ")} wide />
        </div>
        {createdRunIds.length > 0 && handoffRuns.length === 0 ? (
          <p className="success-note">
            Created run{createdRunIds.length === 1 ? "" : "s"}{" "}
            {createdRunIds.map((analysisId, index) => (
              <span key={analysisId}>
                {index > 0 ? ", " : null}
                <Link to={`/runs/${encodeURIComponent(analysisId)}`}>{analysisId}</Link>
              </span>
            ))}
          </p>
        ) : null}
        {handoffRuns.map((run) => <HandoffSummary key={run.analysis_id} run={run} />)}
        {handoffWarning ? <div className="inline-error" role="alert">{handoffWarning}</div> : null}
      </section>

      {notice ? <div className="success-note" role="status">{notice}</div> : null}
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
    </div>
  );
}

function PreviewField({label, value, wide = false, mono = false}: {label: string; value: ReactNode; wide?: boolean; mono?: boolean}) {
  return (
    <div className={wide ? "submit-preview-field wide" : "submit-preview-field"}>
      <span>{label}</span>
      <strong className={mono ? "mono" : undefined}>{value}</strong>
    </div>
  );
}

async function syncSubmittedRun(analysisId: string, fallback: RunDetail): Promise<RunDetail | null> {
  let latest = fallback;
  for (let attempt = 0; attempt < handoffSyncAttempts; attempt += 1) {
    const synced = await syncAirflow(analysisId).catch(() => null);
    if (synced) {
      latest = mergeRunDetail(latest, synced);
      if ((latest.status || "").toLowerCase() !== "submitted") return latest;
    }
    if (attempt < handoffSyncAttempts - 1) await wait(handoffSyncDelayMs);
  }
  return latest;
}

function mergeRunDetail(previous: RunDetail, next: RunDetail): RunDetail {
  return {
    ...previous,
    ...next,
    analysis_id: next.analysis_id || previous.analysis_id,
    pipeline: next.pipeline || previous.pipeline,
    dag_id: next.dag_id || previous.dag_id,
    dag_run_id: next.dag_run_id || previous.dag_run_id,
    workdir: next.workdir || previous.workdir,
    sample_sheet_path: next.sample_sheet_path || previous.sample_sheet_path,
    params: next.params || previous.params,
  };
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function CandidateFolderTable({
  items,
  selected,
  rawdataRoot,
  expanded,
  onToggleFolder,
  onToggleSample,
  onToggleExpanded,
}: {
  items: ScanCandidate[];
  selected: Set<string>;
  rawdataRoot: string;
  expanded: Set<string>;
  onToggleFolder: (sourceDir: string, items: ScanCandidate[]) => void;
  onToggleSample: (sampleId: string) => void;
  onToggleExpanded: (sourceDir: string) => void;
}) {
  const groups = groupCandidates(items, rawdataRoot);

  return (
    <div className="folder-list">
      {groups.map((group) => {
        const folderExpanded = expanded.has(group.sourceDir);
        const allSelected = group.items.every((item) => selected.has(item.sample_id));
        return (
          <div className="folder-row" key={group.sourceDir}>
            <div className="folder-summary">
              <input
                aria-label={`Select folder ${group.folderName}`}
                checked={allSelected}
                type="checkbox"
                onChange={() => onToggleFolder(group.sourceDir, group.items)}
              />
              <button
                aria-label={`${folderExpanded ? "Hide" : "Show"} FASTQ files for ${group.folderName}`}
                className="icon-button"
                type="button"
                onClick={() => onToggleExpanded(group.sourceDir)}
              >
                {folderExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>
              <div>
                <strong>{group.folderName}</strong>
                <span>{group.relativePath}</span>
              </div>
              <span>{group.items.length} sample{group.items.length === 1 ? "" : "s"}</span>
            </div>
            {folderExpanded ? (
              <div className="folder-files">
                {group.items.map((item) => (
                  <div className="folder-sample" key={`${item.sample_id}-${item.r1}`}>
                    <label>
                      <input
                        aria-label={`Select sample ${item.sample_id}`}
                        checked={selected.has(item.sample_id)}
                        type="checkbox"
                        onChange={() => onToggleSample(item.sample_id)}
                      />
                      <strong>{item.sample_id}</strong>
                    </label>
                    <span>{fileName(item.r1)}</span>
                    <span>{fileName(item.r2)}</span>
                    <details>
                      <summary>full path</summary>
                      <code>{item.r1}</code>
                      <code>{item.r2}</code>
                    </details>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
      {groups.length === 0 ? <p className="empty-state">No candidate samples scanned.</p> : null}
    </div>
  );
}

function HandoffSummary({run}: {run: RunDetail}) {
  const confirmed = Boolean(run.dag_run_id);
  return (
    <div className={confirmed ? "success-note handoff-summary" : "inline-error handoff-summary"}>
      <strong>{confirmed ? "Airflow handoff confirmed" : "Airflow handoff needs review"}</strong>
      <dl className="definition-grid compact">
        <div><dt>run_id</dt><dd><Link to={`/runs/${encodeURIComponent(run.analysis_id)}`}>{run.analysis_id}</Link></dd></div>
        <div><dt>dag_run_id</dt><dd className="mono">{run.dag_run_id || "missing"}</dd></div>
        <div><dt>backend status</dt><dd>{run.status}</dd></div>
        <div><dt>pipeline</dt><dd>{compactPipelineName(run.pipeline)}</dd></div>
      </dl>
    </div>
  );
}

function groupCandidates(items: ScanCandidate[], rawdataRoot: string) {
  const groups = new Map<string, ScanCandidate[]>();
  for (const item of items) {
    const sourceDir = item.source_dir || parentDir(item.r1);
    groups.set(sourceDir, [...(groups.get(sourceDir) || []), item]);
  }
  return [...groups.entries()].map(([sourceDir, groupItems]) => ({
    sourceDir,
    folderName: fileName(sourceDir),
    relativePath: relativeParentFolder(sourceDir, rawdataRoot),
    items: groupItems,
  }));
}

function parentDir(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  return normalized.slice(0, normalized.lastIndexOf("/")) || normalized;
}

function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/").replace(/\/+$/, "");
  return normalized.slice(normalized.lastIndexOf("/") + 1) || normalized;
}

function relativeParentFolder(sourceDir: string, rawdataRoot: string): string {
  const root = rawdataRoot.replace(/\\/g, "/").replace(/\/+$/, "");
  const source = sourceDir.replace(/\\/g, "/").replace(/\/+$/, "");
  if (!source.startsWith(root)) return parentDir(source);
  const relative = source.slice(root.length).replace(/^\/+/, "");
  const parent = parentDir(relative);
  return parent === relative ? "." : parent;
}
