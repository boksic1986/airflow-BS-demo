import {
  Activity,
  AlertTriangle,
  Archive,
  Database,
  FileText,
  ListChecks,
  Play,
  Plus,
  RefreshCw,
  RotateCw,
  Search,
} from "lucide-react";
import {useEffect, useMemo, useRef, useState} from "react";

import {
  ApiError,
  Artifact,
  ScanCandidate,
  LogStream,
  PgtaTarget,
  RuleEvent,
  RunQc,
  RunDetail,
  RunLog,
  RunSummary,
  Sample,
  createRun,
  getRunArtifacts,
  getRunDetail,
  getRunLog,
  getRunQc,
  getRunRules,
  getRunSamples,
  listRuns,
  reanalyzeRun,
  scanInput,
  submitRun,
  syncAirflow,
} from "./api";

type RunBundle = {
  detail: RunDetail | null;
  samples: Sample[];
  rules: RuleEvent[];
  artifacts: Artifact[];
  qc: RunQc | null;
};

const emptyBundle: RunBundle = {
  detail: null,
  samples: [],
  rules: [],
  artifacts: [],
  qc: null,
};

const defaultRawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";
const targetOptions: Array<{value: PgtaTarget; label: string}> = [
  {value: "metadata", label: "metadata smoke"},
  {value: "dryrun_cnv", label: "CNV dry-run"},
  {value: "invalid_target", label: "failure smoke"},
  {value: "baseline_qc", label: "baseline QC smoke"},
];
const submitTargets = targetOptions.map((option) => option.value);
const wesRerunRules = ["fastp", "bwa_mem", "markdup", "final_summary"];
const wesSamples = ["S001", "S002"];
const displayTimeZone =
  window.__AIRFLOW_DEMO_CONFIG__?.timeZone || import.meta.env.VITE_DISPLAY_TIME_ZONE || "Asia/Shanghai";

function statusClass(status?: string | null): string {
  const normalized = (status || "unknown").toLowerCase();
  if (["success", "pass"].includes(normalized)) return "status-success";
  if (["failed", "fail", "error"].includes(normalized)) return "status-failed";
  if (["running", "submitted", "queued"].includes(normalized)) return "status-running";
  if (["warn", "warning", "qc_warning"].includes(normalized)) return "status-warn";
  return "status-neutral";
}

function formatDate(value?: string | null): string {
  if (!value) return "not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: displayTimeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value || "00";
  return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")} ${displayTimeZone}`;
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code ? `${error.code}: ${error.message}` : error.message;
  }
  if (error instanceof Error) return error.message;
  return "Request failed";
}

function runTarget(detail?: RunDetail | null): string | null {
  const target = detail?.params?.target;
  return typeof target === "string" ? target : null;
}

function runSelectedCount(detail?: RunDetail | null): number {
  const selectedCount = detail?.params?.selected_count;
  if (typeof selectedCount === "number") return selectedCount;
  if (typeof selectedCount === "string") {
    const parsed = Number(selectedCount);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [bundle, setBundle] = useState<RunBundle>(emptyBundle);
  const [logStream, setLogStream] = useState<LogStream>("metadata");
  const [runLog, setRunLog] = useState<RunLog | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [logError, setLogError] = useState<string | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastAutoSyncedAt, setLastAutoSyncedAt] = useState<string | null>(null);
  const [autoSyncError, setAutoSyncError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [projectName, setProjectName] = useState("PGT-A metadata smoke");
  const [target, setTarget] = useState<PgtaTarget>("metadata");
  const [rawdataRoot, setRawdataRoot] = useState(defaultRawdataRoot);
  const [maxSamples, setMaxSamples] = useState(20);
  const [emailTo, setEmailTo] = useState("");
  const [note, setNote] = useState("");
  const [scanItems, setScanItems] = useState<ScanCandidate[]>([]);
  const [selectedSamples, setSelectedSamples] = useState<Set<string>>(new Set());
  const [scanTruncated, setScanTruncated] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [formNotice, setFormNotice] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [wesProjectName, setWesProjectName] = useState("WES mock smoke");
  const [wesNote, setWesNote] = useState("");
  const [creatingWes, setCreatingWes] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [rerunRule, setRerunRule] = useState("fastp");
  const [rerunSample, setRerunSample] = useState("S001");
  const autoSyncInFlightRef = useRef(false);

  const selectedRun = useMemo(
    () => runs.find((run) => run.analysis_id === selectedId) || null,
    [runs, selectedId],
  );

  const canSubmitRun =
    bundle.detail?.status === "created" &&
    ((bundle.detail.pipeline === "pgta" &&
      submitTargets.includes((runTarget(bundle.detail) || "metadata") as PgtaTarget) &&
      (runTarget(bundle.detail) !== "baseline_qc" || runSelectedCount(bundle.detail) >= 2)) ||
      bundle.detail.pipeline === "wes_qsub");
  const canReanalyzeWes =
    bundle.detail?.pipeline === "wes_qsub" &&
    Boolean(bundle.detail?.dag_run_id) &&
    !["submitted", "running", "queued"].includes((bundle.detail?.status || "").toLowerCase());
  const currentRunStatus = (bundle.detail?.status || selectedRun?.status || "").toLowerCase();
  const autoSyncEnabled = Boolean(
    selectedId && bundle.detail?.dag_run_id && ["submitted", "running", "queued"].includes(currentRunStatus),
  );

  async function refreshRuns(preferredId?: string | null) {
    setLoadingRuns(true);
    setListError(null);
    try {
      const payload = await listRuns();
      setRuns(payload.items);
      const nextId =
        preferredId && payload.items.some((run) => run.analysis_id === preferredId)
          ? preferredId
          : payload.items[0]?.analysis_id || null;
      setSelectedId(nextId);
    } catch (error) {
      setListError(errorMessage(error));
    } finally {
      setLoadingRuns(false);
    }
  }

  async function refreshDetail(analysisId: string) {
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const [detail, samples, rules, artifacts, qc] = await Promise.all([
        getRunDetail(analysisId),
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunArtifacts(analysisId),
        getRunQc(analysisId),
      ]);
      setBundle({
        detail,
        samples: samples.items,
        rules: rules.items,
        artifacts: artifacts.items,
        qc,
      });
    } catch (error) {
      setBundle(emptyBundle);
      setDetailError(errorMessage(error));
    } finally {
      setLoadingDetail(false);
    }
  }

  async function refreshLog(analysisId: string, stream: LogStream) {
    setLogError(null);
    setRunLog(null);
    try {
      setRunLog(await getRunLog(analysisId, stream));
    } catch (error) {
      setLogError(errorMessage(error));
    }
  }

  async function refreshSelectedRun(analysisId: string, stream: LogStream) {
    await Promise.all([refreshRuns(analysisId), refreshDetail(analysisId), refreshLog(analysisId, stream)]);
  }

  async function handleSync() {
    if (!selectedId) return;
    setSyncing(true);
    setDetailError(null);
    try {
      await syncAirflow(selectedId);
      await refreshSelectedRun(selectedId, logStream);
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setSyncing(false);
    }
  }

  async function handleScan() {
    setScanning(true);
    setScanError(null);
    setCreateError(null);
    setFormNotice(null);
    setSelectedSamples(new Set());
    try {
      const payload = await scanInput({
        pipeline: "pgta",
        rawdata_root: rawdataRoot,
        max_samples: maxSamples,
      });
      setScanItems(payload.items);
      setScanTruncated(payload.truncated);
      setFormNotice(`${payload.items.length} candidate samples found`);
    } catch (error) {
      setScanItems([]);
      setScanTruncated(false);
      setScanError(errorMessage(error));
    } finally {
      setScanning(false);
    }
  }

  function toggleSample(sampleId: string) {
    setSelectedSamples((current) => {
      const next = new Set(current);
      if (next.has(sampleId)) {
        next.delete(sampleId);
      } else {
        next.add(sampleId);
      }
      return next;
    });
  }

  async function handleCreateRun() {
    const selected = scanItems.filter((item) => selectedSamples.has(item.sample_id));
    if (selected.length === 0) return;
    setCreating(true);
    setCreateError(null);
    setFormNotice(null);
    try {
      const created = await createRun({
        pipeline: "pgta",
        project_name: projectName,
        target,
        rawdata_root: rawdataRoot,
        selected_samples: selected,
        email_to: emailTo.trim() || null,
        note: note.trim() || null,
      });
      setSelectedId(created.analysis_id);
      setFormNotice(`Created ${created.analysis_id}`);
      await refreshSelectedRun(created.analysis_id, logStream);
    } catch (error) {
      setCreateError(errorMessage(error));
    } finally {
      setCreating(false);
    }
  }

  async function handleSubmitRun() {
    if (!selectedId) return;
    setSubmitting(true);
    setDetailError(null);
    try {
      await submitRun(selectedId);
      await refreshSelectedRun(selectedId, logStream);
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateAndSubmitWes() {
    setCreatingWes(true);
    setDetailError(null);
    setCreateError(null);
    try {
      const created = await createRun({
        pipeline: "wes_qsub",
        project_name: wesProjectName,
        target: "final_summary",
        note: wesNote.trim() || null,
      });
      setSelectedId(created.analysis_id);
      await submitRun(created.analysis_id);
      await refreshSelectedRun(created.analysis_id, "stdout");
      setLogStream("stdout");
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setCreatingWes(false);
    }
  }

  async function handleReanalyze(mode: "resume" | "rerun_rule") {
    if (!selectedId) return;
    setReanalyzing(true);
    setDetailError(null);
    try {
      await reanalyzeRun(selectedId, {
        mode,
        rule: mode === "rerun_rule" ? rerunRule : null,
        sample_id: mode === "rerun_rule" && rerunRule !== "final_summary" ? rerunSample : null,
        reason: mode === "resume" ? "frontend resume" : "frontend rerun selected rule",
      });
      await refreshSelectedRun(selectedId, "stdout");
      setLogStream("stdout");
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setReanalyzing(false);
    }
  }

  useEffect(() => {
    void refreshRuns(null);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setBundle(emptyBundle);
      setRunLog(null);
      return;
    }
    void refreshDetail(selectedId);
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    void refreshLog(selectedId, logStream);
  }, [selectedId, logStream]);

  useEffect(() => {
    setLastAutoSyncedAt(null);
    setAutoSyncError(null);
  }, [selectedId]);

  useEffect(() => {
    if (!autoSyncEnabled || !selectedId) return undefined;
    let disposed = false;

    async function syncSelectedActiveRun() {
      if (autoSyncInFlightRef.current || !selectedId) return;
      autoSyncInFlightRef.current = true;
      setAutoSyncError(null);
      try {
        await syncAirflow(selectedId);
        if (disposed) return;
        await refreshSelectedRun(selectedId, logStream);
        if (!disposed) {
          setLastAutoSyncedAt(new Date().toISOString());
        }
      } catch (error) {
        if (!disposed) {
          setAutoSyncError(errorMessage(error));
        }
      } finally {
        autoSyncInFlightRef.current = false;
      }
    }

    const timer = window.setInterval(() => {
      void syncSelectedActiveRun();
    }, 15000);

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [autoSyncEnabled, selectedId, logStream]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">airflow-demo</p>
          <h1>Analysis Runs</h1>
        </div>
        <div className="topbar-actions">
          <a className="secondary-link" href={`${window.location.protocol}//${window.location.hostname}:12958`}>
            Airflow 12958
          </a>
          <button className="icon-button" type="button" onClick={() => void refreshRuns(selectedId)} disabled={loadingRuns}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="run-list" aria-label="Analysis run list">
          <div className="pane-title">
            <Activity size={17} />
            <span>Runs</span>
            <span className="count">{runs.length}</span>
          </div>
          {listError ? <ErrorBanner message={listError} /> : null}
          {runs.length === 0 && !loadingRuns ? <p className="empty">No runs returned.</p> : null}
          <div className="run-items">
            {runs.map((run) => (
              <button
                key={run.analysis_id}
                className={`run-row ${run.analysis_id === selectedId ? "selected" : ""}`}
                type="button"
                onClick={() => setSelectedId(run.analysis_id)}
              >
                <span className="run-id">{run.analysis_id}</span>
                <span className={`status-pill ${statusClass(run.status)}`}>{run.status}</span>
                <span className="run-meta">
                  {run.sample_count ?? 0} samples · {formatDate(run.created_at)}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="detail-pane" aria-label="Run detail">
          <section className="submit-workspace" aria-label="Submit new analysis">
            <NewRunPanel
              projectName={projectName}
              target={target}
              rawdataRoot={rawdataRoot}
              maxSamples={maxSamples}
              emailTo={emailTo}
              note={note}
              scanItems={scanItems}
              selectedSamples={selectedSamples}
              scanTruncated={scanTruncated}
              scanError={scanError}
              createError={createError}
              formNotice={formNotice}
              scanning={scanning}
              creating={creating}
              onProjectNameChange={setProjectName}
              onTargetChange={setTarget}
              onRawdataRootChange={setRawdataRoot}
              onMaxSamplesChange={setMaxSamples}
              onEmailToChange={setEmailTo}
              onNoteChange={setNote}
              onScan={() => void handleScan()}
              onToggleSample={toggleSample}
              onCreate={() => void handleCreateRun()}
            />
            <NewWesPanel
              projectName={wesProjectName}
              note={wesNote}
              creating={creatingWes}
              onProjectNameChange={setWesProjectName}
              onNoteChange={setWesNote}
              onCreateAndSubmit={() => void handleCreateAndSubmitWes()}
            />
          </section>
          {selectedRun ? (
            <>
              <div className="detail-header">
                <div>
                  <p className="eyebrow">Selected Run</p>
                  <h2>{selectedRun.pipeline.toUpperCase()}</h2>
                  <p className="subtle">Analysis ID: {selectedRun.analysis_id}</p>
                </div>
                <div className="detail-status">
                  <span className={`status-pill large ${statusClass(bundle.detail?.status || selectedRun.status)}`}>
                    {bundle.detail?.status || selectedRun.status}
                  </span>
                </div>
              </div>

              <div className="toolbar" role="toolbar" aria-label="Run actions">
                {canSubmitRun ? (
                  <button className="icon-button primary-action" type="button" onClick={handleSubmitRun} disabled={submitting}>
                    <Play size={16} />
                    Submit to Airflow
                  </button>
                ) : null}
                <button className="icon-button" type="button" onClick={handleSync} disabled={syncing || !bundle.detail?.dag_run_id}>
                  <RotateCw size={16} />
                  Sync Airflow
                </button>
                {bundle.detail?.dag_run_id ? (
                  <span className={`auto-sync-status ${autoSyncEnabled ? "active" : ""}`} aria-live="polite">
                    {autoSyncEnabled ? "Auto sync active" : "Auto sync idle"}
                    {lastAutoSyncedAt ? ` / Last synced ${formatDate(lastAutoSyncedAt)}` : ""}
                  </span>
                ) : null}
                {canReanalyzeWes ? (
                  <>
                    <button className="icon-button" type="button" onClick={() => void handleReanalyze("resume")} disabled={reanalyzing}>
                      <RotateCw size={16} />
                      Resume
                    </button>
                    <label className="toolbar-select">
                      <span>Rerun rule</span>
                      <select value={rerunRule} onChange={(event) => setRerunRule(event.target.value)}>
                        {wesRerunRules.map((rule) => (
                          <option key={rule} value={rule}>
                            {rule}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="toolbar-select">
                      <span>Rerun sample</span>
                      <select value={rerunSample} onChange={(event) => setRerunSample(event.target.value)} disabled={rerunRule === "final_summary"}>
                        {wesSamples.map((sample) => (
                          <option key={sample} value={sample}>
                            {sample}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button className="icon-button" type="button" onClick={() => void handleReanalyze("rerun_rule")} disabled={reanalyzing}>
                      <Play size={16} />
                      Rerun rule
                    </button>
                  </>
                ) : null}
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => selectedId && void refreshDetail(selectedId)}
                  disabled={loadingDetail}
                >
                  <RefreshCw size={16} />
                  Refresh Detail
                </button>
              </div>

              {detailError ? <ErrorBanner message={detailError} /> : null}
              {autoSyncError ? <ErrorBanner message={`Auto sync failed: ${autoSyncError}`} /> : null}
              {bundle.detail ? <Overview detail={bundle.detail} sampleCount={bundle.samples.length} /> : null}
              <QcPanel qc={bundle.qc} />

              <div className="detail-grid">
                <SamplesTable samples={bundle.samples} />
                <RulesTable rules={bundle.rules} />
              </div>

              <div className="lower-grid">
                <LogPanel
                  stream={logStream}
                  onStreamChange={setLogStream}
                  log={runLog}
                  error={logError}
                />
                <ArtifactsList artifacts={bundle.artifacts} />
              </div>
            </>
          ) : (
            <div className="blank-state">
              <Database size={30} />
              <p>Select a run to inspect its samples, logs, artifacts, and rule status.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function NewRunPanel({
  projectName,
  target,
  rawdataRoot,
  maxSamples,
  emailTo,
  note,
  scanItems,
  selectedSamples,
  scanTruncated,
  scanError,
  createError,
  formNotice,
  scanning,
  creating,
  onProjectNameChange,
  onTargetChange,
  onRawdataRootChange,
  onMaxSamplesChange,
  onEmailToChange,
  onNoteChange,
  onScan,
  onToggleSample,
  onCreate,
}: {
  projectName: string;
  target: PgtaTarget;
  rawdataRoot: string;
  maxSamples: number;
  emailTo: string;
  note: string;
  scanItems: ScanCandidate[];
  selectedSamples: Set<string>;
  scanTruncated: boolean;
  scanError: string | null;
  createError: string | null;
  formNotice: string | null;
  scanning: boolean;
  creating: boolean;
  onProjectNameChange: (value: string) => void;
  onTargetChange: (value: PgtaTarget) => void;
  onRawdataRootChange: (value: string) => void;
  onMaxSamplesChange: (value: number) => void;
  onEmailToChange: (value: string) => void;
  onNoteChange: (value: string) => void;
  onScan: () => void;
  onToggleSample: (sampleId: string) => void;
  onCreate: () => void;
}) {
  const minimumSelectedSamples = target === "baseline_qc" ? 2 : 1;
  const canCreateRun = selectedSamples.size >= minimumSelectedSamples;
  const selectionHint =
    selectedSamples.size > 0
      ? `${selectedSamples.size} scanned sample${selectedSamples.size === 1 ? "" : "s"} selected.`
      : "Select at least one scanned sample to enable Create Run.";
  const targetHint =
    target === "baseline_qc" && selectedSamples.size < 2
      ? "Baseline QC smoke requires at least 2 selected samples."
      : selectionHint;

  return (
    <section className="new-run-panel" aria-label="New PGT-A Run">
      <div className="pane-title">
        <Plus size={17} />
        <span>New PGT-A Run</span>
      </div>
      <div className="form-grid pgta-form-grid">
        <label>
          <span>Project name</span>
          <input value={projectName} onChange={(event) => onProjectNameChange(event.target.value)} />
        </label>
        <label>
          <span>Rawdata root</span>
          <input value={rawdataRoot} onChange={(event) => onRawdataRootChange(event.target.value)} />
        </label>
        <label>
          <span>Max samples</span>
          <input
            min={1}
            max={1000}
            type="number"
            value={maxSamples}
            onChange={(event) => onMaxSamplesChange(Number(event.target.value) || 1)}
          />
        </label>
        <label>
          <span>Target</span>
          <select value={target} onChange={(event) => onTargetChange(event.target.value as PgtaTarget)}>
            {targetOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Email</span>
          <input value={emailTo} onChange={(event) => onEmailToChange(event.target.value)} />
        </label>
        <label>
          <span>Note</span>
          <textarea value={note} rows={2} onChange={(event) => onNoteChange(event.target.value)} />
        </label>
      </div>
      <div className="submit-toolbar">
        <button className="icon-button" type="button" onClick={onScan} disabled={scanning || !rawdataRoot.trim()}>
          <Search size={16} />
          Scan
        </button>
        <button className="icon-button primary-action" type="button" onClick={onCreate} disabled={creating || !canCreateRun}>
          <Plus size={16} />
          Create Run
        </button>
      </div>
      <p className="form-hint">{targetHint}</p>
      {scanError ? <ErrorBanner message={scanError} /> : null}
      {createError ? <ErrorBanner message={createError} /> : null}
      {formNotice ? <p className="form-notice">{formNotice}</p> : null}
      {scanTruncated ? <p className="form-warning">Scan result was truncated; narrow the rawdata root or lower the range.</p> : null}
      <CandidateTable items={scanItems} selectedSamples={selectedSamples} onToggleSample={onToggleSample} />
    </section>
  );
}

function NewWesPanel({
  projectName,
  note,
  creating,
  onProjectNameChange,
  onNoteChange,
  onCreateAndSubmit,
}: {
  projectName: string;
  note: string;
  creating: boolean;
  onProjectNameChange: (value: string) => void;
  onNoteChange: (value: string) => void;
  onCreateAndSubmit: () => void;
}) {
  return (
    <section className="new-run-panel compact-panel" aria-label="New WES Mock Run">
      <div className="pane-title">
        <Plus size={17} />
        <span>New WES Mock Run</span>
      </div>
      <div className="form-grid">
        <label>
          <span>WES name</span>
          <input value={projectName} onChange={(event) => onProjectNameChange(event.target.value)} />
        </label>
        <label>
          <span>Output</span>
          <input value="final_summary" readOnly />
        </label>
        <label>
          <span>WES note</span>
          <textarea value={note} rows={2} onChange={(event) => onNoteChange(event.target.value)} />
        </label>
      </div>
      <div className="submit-toolbar">
        <button className="icon-button primary-action" type="button" onClick={onCreateAndSubmit} disabled={creating || !projectName.trim()}>
          <Play size={16} />
          Create and Submit WES
        </button>
      </div>
    </section>
  );
}

function CandidateTable({
  items,
  selectedSamples,
  onToggleSample,
}: {
  items: ScanCandidate[];
  selectedSamples: Set<string>;
  onToggleSample: (sampleId: string) => void;
}) {
  if (items.length === 0) {
    return <p className="empty">No candidate samples scanned.</p>;
  }

  return (
    <div className="candidate-table table-wrap">
      <table>
        <thead>
          <tr>
            <th>select</th>
            <th>sample</th>
            <th>R1</th>
            <th>R2</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.sample_id}-${item.r1}`}>
              <td>
                <input
                  aria-label={`Select sample ${item.sample_id}`}
                  checked={selectedSamples.has(item.sample_id)}
                  type="checkbox"
                  onChange={() => onToggleSample(item.sample_id)}
                />
              </td>
              <td>{item.sample_id}</td>
              <td className="path-cell">{item.r1}</td>
              <td className="path-cell">{item.r2}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ErrorBanner({message}: {message: string}) {
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={16} />
      <span>{message}</span>
    </div>
  );
}

function Overview({detail, sampleCount}: {detail: RunDetail; sampleCount: number}) {
  const rows = [
    ["DAG", detail.dag_id || "not set"],
    ["DAG run", detail.dag_run_id || "not set"],
    ["Mode", detail.mode || "not set"],
    ["Samples", String(sampleCount)],
    ["Workdir", detail.workdir || "not set"],
    ["Manifest", detail.sample_sheet_path || "not set"],
    ["Started", formatDate(detail.started_at)],
    ["Ended", formatDate(detail.ended_at)],
  ];
  return (
    <section className="section-band">
      <div className="section-title">
        <FileText size={17} />
        <h3>Overview</h3>
      </div>
      <div className="kv-grid">
        {rows.map(([label, value]) => (
          <div className="kv-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      {detail.params ? (
        <pre className="params-block">{JSON.stringify(detail.params, null, 2)}</pre>
      ) : null}
      {detail.error_summary ? <ErrorBanner message={detail.error_summary} /> : null}
    </section>
  );
}

function SamplesTable({samples}: {samples: Sample[]}) {
  return (
    <section className="section-band">
      <div className="section-title">
        <Database size={17} />
        <h3>Samples</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>sample</th>
              <th>status</th>
              <th>R1</th>
              <th>R2</th>
            </tr>
          </thead>
          <tbody>
            {samples.map((sample) => (
              <tr key={sample.sample_id}>
                <td>{sample.sample_id}</td>
                <td>
                  <span className={`status-pill ${statusClass(sample.status)}`}>{sample.status || "unknown"}</span>
                </td>
                <td className="path-cell">{sample.fq1 || "not set"}</td>
                <td className="path-cell">{sample.fq2 || "not set"}</td>
              </tr>
            ))}
            {samples.length === 0 ? (
              <tr>
                <td colSpan={4} className="empty-cell">
                  No samples returned.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function RulesTable({rules}: {rules: RuleEvent[]}) {
  return (
    <section className="section-band">
      <div className="section-title">
        <ListChecks size={17} />
        <h3>Snakemake Rules</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>rule</th>
              <th>sample</th>
              <th>status</th>
              <th>jobid</th>
              <th>return</th>
              <th>message</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={`${rule.rule}-${rule.sample_id || "project"}-${rule.snakemake_jobid || "none"}`}>
                <td>{rule.rule}</td>
                <td>{rule.sample_id || "project"}</td>
                <td>
                  <span className={`status-pill ${statusClass(rule.status)}`}>{rule.status}</span>
                </td>
                <td>{rule.snakemake_jobid || "not set"}</td>
                <td>{rule.return_code ?? "not set"}</td>
                <td>{rule.message || "not set"}</td>
              </tr>
            ))}
            {rules.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-cell">
                  No rule events returned.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function QcPanel({qc}: {qc: RunQc | null}) {
  const summary = qc?.summary || {pass: 0, warn: 0, fail: 0, unknown: 0};
  const metrics = qc?.items || [];
  return (
    <section className="section-band">
      <div className="section-title">
        <ListChecks size={17} />
        <h3>QC</h3>
      </div>
      <div className="qc-summary" aria-label="QC summary">
        {(["pass", "warn", "fail", "unknown"] as const).map((status) => (
          <span className={`status-pill ${statusClass(status)}`} key={status}>
            {status}: {summary[status]}
          </span>
        ))}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>sample</th>
              <th>metric</th>
              <th>value</th>
              <th>threshold</th>
              <th>status</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={`${metric.sample_id || "project"}-${metric.metric_name}`}>
                <td>{metric.sample_id || "project"}</td>
                <td>{metric.metric_name}</td>
                <td>{metric.metric_value ?? metric.metric_numeric ?? "not set"}</td>
                <td>{metric.threshold || "not set"}</td>
                <td>
                  <span className={`status-pill ${statusClass(metric.status)}`}>{metric.status}</span>
                </td>
              </tr>
            ))}
            {metrics.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-cell">
                  No QC metrics returned.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LogPanel({
  stream,
  onStreamChange,
  log,
  error,
}: {
  stream: LogStream;
  onStreamChange: (stream: LogStream) => void;
  log: RunLog | null;
  error: string | null;
}) {
  const streams: LogStream[] = ["metadata", "stdout", "stderr"];
  return (
    <section className="section-band">
      <div className="section-title">
        <FileText size={17} />
        <h3>Logs</h3>
      </div>
      <div className="segmented" role="tablist" aria-label="Log stream">
        {streams.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={stream === item}
            className={stream === item ? "active" : ""}
            onClick={() => onStreamChange(item)}
          >
            {item}
          </button>
        ))}
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      <div className="log-box" aria-label={`${stream} log`}>
        {log?.lines.length ? (
          log.lines.map((line, index) => (
            <div key={`${line}-${index}`} className="log-line">
              {line}
            </div>
          ))
        ) : (
          <span className="empty">No log lines returned.</span>
        )}
      </div>
      {log ? <p className="subtle">Path: {log.path}</p> : null}
    </section>
  );
}

function ArtifactsList({artifacts}: {artifacts: Artifact[]}) {
  return (
    <section className="section-band">
      <div className="section-title">
        <Archive size={17} />
        <h3>Artifacts</h3>
      </div>
      <div className="artifact-list">
        {artifacts.map((artifact) => (
          <div className="artifact-row" key={artifact.key}>
            <div>
              <strong>{artifact.label}</strong>
              <span>{artifact.type}</span>
            </div>
            <span>{formatBytes(artifact.size_bytes)}</span>
          </div>
        ))}
        {artifacts.length === 0 ? <p className="empty">No artifacts returned.</p> : null}
      </div>
    </section>
  );
}
