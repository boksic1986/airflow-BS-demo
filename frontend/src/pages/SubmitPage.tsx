import {ChevronDown, ChevronRight, Play, Plus, Search} from "lucide-react";
import type {ReactNode} from "react";
import {useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {DeployedPipeline, NiptRunMode, PgtaTarget, RunDetail, ScanCandidate} from "../api";

import {ApiError, createRun, getInputRoots, getRunDetail, scanInput, submitRun, syncAirflow} from "../api";
import {PipelineSelector} from "../components/PipelineSelector";
import {StatusBadge} from "../components/StatusBadge";
import {SnakemakeConfigEditor} from "../features/submit/SnakemakeConfigEditor";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import type {SnakemakeConfigSelection} from "../features/submit/SnakemakeConfigEditor";
import {errorMessage} from "../lib/errors";
import {compactPipelineName} from "../lib/format";
import {deployedWorkflowTemplates} from "../mocks/platform";

const defaultPgtaRawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";
const defaultNiptRawdataRoot = "/data/nipt-fastq";
const handoffSyncAttempts = 6;
const handoffSyncDelayMs = 2500;
const submittedByStorageKey = "airflow-demo.submitted-by";
const fallbackTemplate = deployedWorkflowTemplates.find((pipeline) => pipeline.id === "nipt_docker") || deployedWorkflowTemplates[0]!;

function loadSubmittedBy() {
  try {
    return window.localStorage.getItem(submittedByStorageKey)?.trim() || "jiucheng";
  } catch {
    return "jiucheng";
  }
}

function rememberSubmittedBy(value: string) {
  try {
    if (value.trim()) window.localStorage.setItem(submittedByStorageKey, value);
    else window.localStorage.removeItem(submittedByStorageKey);
  } catch {
    // Browser storage can be unavailable in restricted sessions; submission still works.
  }
}

export function SubmitPage() {
  const capabilities = usePlatformCapabilities();
  const [selectedPipeline, setSelectedPipeline] = useState<DeployedPipeline>("nipt_docker");
  const [projectName, setProjectName] = useState("Bioinformatics demo run");
  const [submittedBy, setSubmittedBy] = useState(loadSubmittedBy);
  const [reference] = useState("hg19");
  const [priority, setPriority] = useState("normal");
  const [runMode, setRunMode] = useState("production-run");
  const [niptRunMode, setNiptRunMode] = useState<NiptRunMode>("full_run");
  const [niptCores, setNiptCores] = useState(32);
  const [target] = useState<PgtaTarget>("predict");
  const [rawdataRoot, setRawdataRoot] = useState(defaultNiptRawdataRoot);
  const [rootOptions, setRootOptions] = useState<string[]>([defaultNiptRawdataRoot]);
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
  const [configSelection, setConfigSelection] = useState<SnakemakeConfigSelection | null>(null);
  const [configEditorRevision, setConfigEditorRevision] = useState(0);
  const [showNiptFullConfirm, setShowNiptFullConfirm] = useState(false);
  const [showWgsFullConfirm, setShowWgsFullConfirm] = useState(false);
  const [wgsPrecallingConfigPath, setWgsPrecallingConfigPath] = useState("");
  const [wgsDownstreamConfigPath, setWgsDownstreamConfigPath] = useState("");
  const [wgsTargetsPath, setWgsTargetsPath] = useState("");
  const [wgsStage, setWgsStage] = useState<"precalling" | "full">("precalling");

  const availableTemplates = useMemo(
    () => deployedWorkflowTemplates.filter((pipeline) => capabilities.deployed_pipelines.includes(pipeline.id as DeployedPipeline)),
    [capabilities.deployed_pipelines],
  );
  const selectedTemplate = availableTemplates.find((pipeline) => pipeline.id === selectedPipeline) || availableTemplates[0] || fallbackTemplate;
  const selectedScanRows = scanItems.filter((item) => selectedSamples.has(item.sample_id));
  const canCreatePgta = selectedScanRows.length > 0 && Boolean(projectName.trim());
  const canCreateNipt = selectedScanRows.length > 0 && Boolean(projectName.trim());
  const canCreateWgs = Boolean(
    projectName.trim()
    && wgsPrecallingConfigPath.trim()
    && wgsTargetsPath.trim()
    && (wgsStage === "precalling" || wgsDownstreamConfigPath.trim()),
  );
  const canCreateSelected = selectedPipeline === "wgs"
    ? canCreateWgs
    : (selectedPipeline === "nipt_docker" ? canCreateNipt : canCreatePgta) && Boolean(configSelection?.valid);

  useEffect(() => {
    if (selectedPipeline === "wgs") {
      setRootOptions([]);
      setRawdataRoot("");
      setScanItems([]);
      return;
    }
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

  useEffect(() => {
    if (capabilities.deployed_pipelines.includes(selectedPipeline)) return;
    const nextPipeline = capabilities.deployed_pipelines[0];
    if (nextPipeline) handlePipelineChange(nextPipeline);
  }, [capabilities.deployed_pipelines, selectedPipeline]);

  async function handleScan() {
    if (selectedPipeline === "wgs") return;
    setScanning(true);
    setError(null);
    setShowNiptFullConfirm(false);
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
    if (value !== "pgta" && value !== "nipt_docker" && value !== "wgs") return;
    if (!confirmConfigReset()) return;
    setSelectedPipeline(value);
    setConfigSelection(null);
    setRawdataRoot(value === "wgs" ? "" : value === "nipt_docker" ? defaultNiptRawdataRoot : defaultPgtaRawdataRoot);
    setRootOptions(value === "wgs" ? [] : [value === "nipt_docker" ? defaultNiptRawdataRoot : defaultPgtaRawdataRoot]);
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
    if (selectedPipeline === "wgs") {
      return [
        await createRun({
          pipeline: "wgs",
          project_name: projectName,
          wgs_precalling_config_path: wgsPrecallingConfigPath,
          wgs_downstream_config_path: wgsDownstreamConfigPath || undefined,
          wgs_targets_path: wgsTargetsPath,
          wgs_stage: wgsStage,
          wgs_dry_run: true,
          submitted_by: submittedBy.trim() || null,
          note: "BS10610 host-native Snakemake 9 controlled run",
        }),
      ];
    }
    if (!configSelection?.valid) throw new Error("Validate the Snakemake config before creating the run.");
    const configPayload = {
      runtime_profile_id: configSelection.runtimeProfileId,
      config_template_hash: configSelection.configTemplateHash,
      snakemake_config_yaml: configSelection.configYaml,
    };
    if (selectedPipeline === "nipt_docker") {
      const batches = groupCandidates(selectedScanRows, rawdataRoot);
      return Promise.all(
        batches.map((batch) =>
          createRun({
            pipeline: "nipt_docker",
            project_name: batches.length > 1 ? `${projectName} ${batch.folderName}` : projectName,
            rawdata_root: rawdataRoot,
            selected_samples: batch.items,
            submitted_by: submittedBy.trim() || null,
            run_mode: niptRunMode,
            cores: niptCores,
            ...configPayload,
            email_to: null,
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
        submitted_by: submittedBy.trim() || null,
        ...configPayload,
        email_to: null,
        note: `reference=${reference}; priority=${priority}; mode=${runMode}`,
      }),
    ];
  }

  function confirmConfigReset(): boolean {
    return !configSelection?.dirty || window.confirm("Discard the edited Snakemake config and load new defaults?");
  }

  function handleNiptRunModeChange(value: NiptRunMode) {
    if (!confirmConfigReset()) return;
    setConfigSelection(null);
    setNiptRunMode(value);
  }

  function handleNiptCoresChange(value: number) {
    if (!confirmConfigReset()) return;
    setConfigSelection(null);
    setNiptCores(value);
  }

  function handleCreateError(createError: unknown) {
    if (createError instanceof ApiError && createError.code === "PROFILE_CHANGED") {
      setConfigSelection(null);
      setConfigEditorRevision((current) => current + 1);
      setError("Runtime profile changed. Defaults were reloaded; review and validate the config again.");
      return;
    }
    setError(errorMessage(createError));
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
      handleCreateError(createError);
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
      handleCreateError(submitError);
    } finally {
      setCreating(false);
    }
  }

  function requestCreateAndSubmit() {
    if (selectedPipeline === "nipt_docker" && niptRunMode === "full_run") {
      setShowNiptFullConfirm(true);
      return;
    }
    if (selectedPipeline === "wgs" && wgsStage === "full") {
      setShowWgsFullConfirm(true);
      return;
    }
    void handleCreateAndSubmit();
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Controlled intake</p>
          <h1>Submit Run</h1>
          <p>Prepare deployed pipeline requests from scanned server batches, validate the preview, then submit them to Airflow.</p>
        </div>
      </section>

      <section className="submit-stepper" aria-label="Submit run steps">
        <StepMarker index={1} title="Pipeline" detail={compactPipelineName(selectedPipeline)} active />
        <StepMarker index={2} title={selectedPipeline === "wgs" ? "Host config" : "Server batch"} detail={selectedPipeline === "wgs" ? (canCreateWgs ? "ready" : "paths required") : scanItems.length ? `${scanItems.length} candidates` : "scan required"} active={selectedPipeline === "wgs" ? canCreateWgs : scanItems.length > 0} />
        <StepMarker index={3} title="Preview" detail={selectedPipeline === "wgs" ? wgsStage : `${selectedScanRows.length} selected`} active={selectedPipeline === "wgs" ? canCreateWgs : selectedScanRows.length > 0} />
        <StepMarker index={4} title="Airflow handoff" detail={handoffRuns.length ? "confirmed" : "pending"} active={handoffRuns.length > 0} />
      </section>

      <section className="panel submit-wizard-panel">
        <div className="section-heading">
          <p className="eyebrow">Step 1</p>
          <h2>Select deployed workflow</h2>
          <p>{availableTemplates.length === 1 ? `${compactPipelineName(availableTemplates[0]!.id)} is the only deployed workflow in this environment.` : "Only deployed workflows are selectable."}</p>
        </div>
        <PipelineSelector pipelines={availableTemplates} value={selectedPipeline} onChange={handlePipelineChange} />
      </section>

      <div className="submit-grid">
        <section className="panel">
          <div className="section-heading">
            <p className="eyebrow">Step 2</p>
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
              <input value={selectedPipeline === "wgs" ? "GRCh38" : reference} readOnly aria-describedby="pgta-reference-note" />
              {selectedPipeline === "pgta" ? <small id="pgta-reference-note">Locked by the approved PGT-A S9 runtime profile.</small> : null}
            </label>
            <label className="field">
              <span>Sequencing strategy</span>
              <input value={selectedPipeline === "wgs" ? "Whole-genome sequencing" : selectedPipeline === "nipt_docker" ? "Low-pass WGS / NIPT aneuploidy screening" : "Low-pass WGS / PGT-A copy-number screening"} readOnly />
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
              <input value={selectedPipeline === "wgs" ? wgsStage : selectedPipeline === "pgta" ? "predict" : runMode} readOnly={selectedPipeline !== "nipt_docker"} onChange={(event) => setRunMode(event.target.value)} />
            </label>
            <label className="field">
              <span>Submitted by</span>
              <input
                aria-label="Submitted by"
                autoComplete="off"
                list="submitted-by-options"
                maxLength={128}
                placeholder="jiucheng"
                value={submittedBy}
                onChange={(event) => {
                  setSubmittedBy(event.target.value);
                  rememberSubmittedBy(event.target.value);
                }}
              />
              <datalist id="submitted-by-options">
                <option value="jiucheng" />
                <option value="airflow" />
              </datalist>
            </label>
          </div>
          {selectedPipeline !== "wgs" ? <SnakemakeConfigEditor
            key={`${selectedPipeline}-${target}-${niptRunMode}-${niptCores}-${configEditorRevision}`}
            pipeline={selectedPipeline}
            target={target}
            runMode={niptRunMode}
            cores={niptCores}
            onChange={setConfigSelection}
          /> : null}
        </section>
      </div>

      <section className="panel">
        <div className="section-heading split">
          <div>
            <p className="eyebrow">Step 3</p>
            <h2>{selectedPipeline === "wgs" ? "WGS host configuration" : selectedPipeline === "nipt_docker" ? "NIPT Docker server-path scan" : "PGT-A server-path scan"}</h2>
            <p>
              {selectedPipeline === "wgs"
                ? "Select approved BS10610 pre-calling and downstream configs. Airflow orchestrates the host workflow through a restricted SSH gate."
                : selectedPipeline === "nipt_docker"
                ? "Scan an allowlisted NIPT FASTQ root, select one chip folder or individual clean FASTQ pairs, then create one run for that batch."
                : "Scan an allowlisted PGT-A FASTQ directory, select samples, create a run, then submit it to Airflow."}
            </p>
          </div>
          <StatusBadge status={selectedTemplate.implementationStatus} />
        </div>
        <div className="form-grid pgta-grid">
          {selectedPipeline === "wgs" ? <>
            <label className="field full">
              <span>Pre-calling config</span>
              <input aria-label="WGS pre-calling config" value={wgsPrecallingConfigPath} onChange={(event) => setWgsPrecallingConfigPath(event.target.value)} placeholder="/sg2/.../config_precalling.yaml" />
            </label>
            <label className="field full">
              <span>Downstream config</span>
              <input aria-label="WGS downstream config" value={wgsDownstreamConfigPath} onChange={(event) => setWgsDownstreamConfigPath(event.target.value)} placeholder="/sg2/.../config_downstream.yaml" />
            </label>
            <label className="field full">
              <span>Controlled targets</span>
              <input aria-label="WGS targets" value={wgsTargetsPath} onChange={(event) => setWgsTargetsPath(event.target.value)} placeholder="/sg2/.../final_targets.txt" />
            </label>
            <label className="field">
              <span>WGS validation stage</span>
              <select aria-label="WGS stage" value={wgsStage} onChange={(event) => setWgsStage(event.target.value as "precalling" | "full")}>
                <option value="precalling">Pre-calling dry-run</option>
                <option value="full">Full downstream dry-run</option>
              </select>
            </label>
            <div className="nipt-full-run-notice full" role="note">
              <strong>Dry-run validation only</strong>
              <span>Snakemake 9 resolves the selected BS10610 workflow graph without executing WGS rules. Real WGS execution is disabled.</span>
            </div>
          </> : <>
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
              <input aria-label="Target" value="predict" readOnly />
              <small>Reference building and baseline QC are maintenance-only and hidden from normal submission.</small>
            </label>
          ) : (
            <>
              <label className="field">
                <span>NIPT run mode</span>
                <select aria-label="NIPT run mode" value={niptRunMode} onChange={(event) => handleNiptRunModeChange(event.target.value as NiptRunMode)}>
                  <option value="full_run">Full analysis</option>
                </select>
              </label>
              <label className="field">
                <span>NIPT cores</span>
                <input aria-label="NIPT cores" type="number" min={1} max={40} value={niptCores} onChange={(event) => handleNiptCoresChange(Number(event.target.value) || 1)} />
              </label>
            </>
          )}
          </>}
        </div>
        <div className="panel-actions">
          {selectedPipeline !== "wgs" ? <button className="button ghost" type="button" disabled={scanning || !rawdataRoot.trim()} onClick={() => void handleScan()}>
            <Search size={15} />
            Scan
          </button> : null}
          <button className="button primary" type="button" disabled={creating || !canCreateSelected} onClick={requestCreateAndSubmit}>
            <Play size={15} />
            Create and submit to Airflow
          </button>
          <button className="button ghost" type="button" disabled={creating || !canCreateSelected} onClick={() => void handleCreateOnly()}>
            <Plus size={15} />
            Create only
          </button>
        </div>
        {selectedPipeline === "nipt_docker" && niptRunMode === "full_run" ? (
          <div className="nipt-full-run-notice" role="note">
            <strong>Full NIPT analysis</strong>
            <span>32 cores / up to 60 GiB memory / estimated 25-35 minutes. Runs are serialized by the NIPT Airflow pool.</span>
          </div>
        ) : null}
        {selectedPipeline !== "wgs" ? <CandidateFolderTable
          expanded={expandedFolders}
          items={scanItems}
          rawdataRoot={rawdataRoot}
          selected={selectedSamples}
          onToggleFolder={toggleFolder}
          onToggleSample={toggleSample}
          onToggleExpanded={toggleExpandedFolder}
        /> : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Step 4</p>
          <h2>Submit preview</h2>
          <p>{selectedPipeline === "wgs" ? "Execution is blocked until all host configuration paths pass the WGS runner guard." : "Execution is blocked until the selected pipeline scan returns validated FASTQ pairs and the run guard passes."}</p>
        </div>
        <div className="submit-preview-list">
          <PreviewField label="Pipeline" value={<strong className="preview-pill">{compactPipelineName(selectedPipeline)}</strong>} />
          <PreviewField label="Project" value={projectName || "not set"} />
          <PreviewField label="Submitted by" value={submittedBy || "not set"} />
          <PreviewField label="Reference" value={selectedPipeline === "wgs" ? "GRCh38" : reference} />
          <PreviewField label="Mode" value={selectedPipeline === "wgs" ? (wgsStage === "full" ? "Full downstream dry-run" : "Pre-calling dry-run") : selectedPipeline === "pgta" ? "predict" : runMode} />
          <PreviewField label="Selected samples" value={selectedPipeline === "wgs" ? "resolved during prepare" : String(selectedScanRows.length)} />
          {selectedPipeline === "pgta" ? <PreviewField label="PGT-A target" value={target} /> : null}
          {selectedPipeline === "nipt_docker" ? <PreviewField label="NIPT run mode" value={niptRunMode} /> : null}
          <PreviewField label="Runtime profile" value={selectedPipeline === "wgs" ? "WGS Snakemake 9 host" : configSelection?.profile.label || "loading"} />
          <PreviewField label="Config revision" value={selectedPipeline === "wgs" ? "wgs-s9-host-v1" : configSelection?.profile.config_version || "loading"} />
          <PreviewField label="Config changes" value={selectedPipeline === "wgs" ? "controlled config files" : configSelection ? String(configSelection.changedPaths.length) : "not validated"} />
          <PreviewField label={selectedPipeline === "wgs" ? "Pre-calling config" : "Scan root"} value={selectedPipeline === "wgs" ? wgsPrecallingConfigPath || "not set" : rawdataRoot || "not set"} wide mono />
          {selectedPipeline === "wgs" ? <PreviewField label="Downstream config" value={wgsDownstreamConfigPath || "not set"} wide mono /> : null}
          {selectedPipeline === "wgs" ? <PreviewField label="Targets" value={wgsTargetsPath || "not set"} wide mono /> : null}
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
      {showNiptFullConfirm ? (
        <div className="modal-backdrop">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-label="Confirm NIPT full analysis">
            <div className="section-heading">
              <p className="eyebrow">Resource confirmation</p>
              <h2>Start full NIPT analysis?</h2>
              <p>{selectedScanRows.length} selected samples will use the approved Snakemake 9 runtime with 32 cores and up to 60 GiB memory.</p>
            </div>
            <div className="panel-actions">
              <button className="button ghost" type="button" onClick={() => setShowNiptFullConfirm(false)}>Cancel</button>
              <button className="button primary" type="button" onClick={() => { setShowNiptFullConfirm(false); void handleCreateAndSubmit(); }}>Confirm full analysis</button>
            </div>
          </section>
        </div>
      ) : null}
      {showWgsFullConfirm ? (
        <div className="modal-backdrop">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-label="Confirm WGS full dry-run">
            <div className="section-heading">
              <p className="eyebrow">Dry-run validation gate</p>
              <h2>Resolve the full WGS workflow graph?</h2>
              <p>Host-native Snakemake 9 validates the downstream graph and inputs without executing WGS rules. Real WGS execution remains disabled.</p>
            </div>
            <div className="panel-actions">
              <button className="button ghost" type="button" onClick={() => setShowWgsFullConfirm(false)}>Cancel</button>
              <button className="button primary" type="button" onClick={() => { setShowWgsFullConfirm(false); void handleCreateAndSubmit(); }}>Confirm full dry-run</button>
            </div>
          </section>
        </div>
      ) : null}
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

function StepMarker({index, title, detail, active = false}: {index: number; title: string; detail: string; active?: boolean}) {
  return (
    <div className={active ? "submit-step active" : "submit-step"}>
      <span>{index}</span>
      <div>
        <strong>{title}</strong>
        <small>{detail}</small>
      </div>
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
