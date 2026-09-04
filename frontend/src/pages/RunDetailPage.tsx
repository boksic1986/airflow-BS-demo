import {Play, RefreshCw, RotateCcw, Square} from "lucide-react";
import {useEffect, useState} from "react";
import {useParams} from "react-router-dom";

import type {Artifact, DeployedPipeline, LogStream, RuleEvent, RunConfig, RunDetail, RunLog, RunLogIndexItem, RunProgressResponse, Sample, WgsPod, WgsSampleManifestRow, WgsTransfer, WgsValidationIssue} from "../api";

import {
  getRunArtifacts,
  getRunPods,
  getRunTransfers,
  getRunConfig,
  getRunDetail,
  getRunLog,
  getRunLogIndex,
  getRunProgress,
  getRunRules,
  getRunValidationIssues,
  getRunSamples,
  submitRun,
  syncAirflow, cancelRun, cleanupStep7, rerunFailedRun, resumeRun, revalidateRun, repairStep4,
} from "../api";
import {useSession} from "../features/auth/SessionContext";
import {ErrorPanel} from "../components/ErrorPanel";
import {LogViewer, preferredLogSource} from "../components/LogViewer";
import {MetricCard} from "../components/MetricCard";
import {StatusBadge} from "../components/StatusBadge";
import {CurrentProgressPanel} from "../features/run-detail/CurrentProgressPanel";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {RunFilesTab, RunOverviewTab} from "../features/run-detail/RunResourceTabs";
import {RunWorkflowTab} from "../features/run-detail/RunWorkflowTab";
import {Step4RepairPanel} from "../features/run-detail/Step4RepairPanel";
import {errorMessage, parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatBytes, formatDate, formatDuration, formatSecondsDuration} from "../lib/format";
import {progressFromResponse} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus} from "../lib/status";

const tabs = ["Overview", "Samples", "Rules", "Master", "Transfers", "Logs", "Files"] as const;
type DetailTab = (typeof tabs)[number];

type Bundle = {
  detail: RunDetail | null;
  samples: Sample[];
  manifest: WgsSampleManifestRow[];
  rules: RuleEvent[];
  artifacts: Artifact[];
  progress: RunProgressResponse | null;
  config: RunConfig | null;
  pods: WgsPod[];
  transfers: WgsTransfer[];
  validationIssues: WgsValidationIssue[];
};

const emptyBundle: Bundle = {detail: null, samples: [], manifest: [], rules: [], artifacts: [], progress: null, config: null, pods: [], transfers: [], validationIssues: []};

export function RunDetailPage() {
  const {analysisId = ""} = useParams();
  const capabilities = usePlatformCapabilities();
  const session = useSession();
  const capabilityKey = capabilities.deployed_pipelines.join(",");
  const [bundle, setBundle] = useState<Bundle>(emptyBundle);
  const [log, setLog] = useState<RunLog | null>(null);
  const [logStream, setLogStream] = useState<LogStream>("metadata");
  const [logSources, setLogSources] = useState<RunLogIndexItem[]>([]);
  const [logKey, setLogKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logError, setLogError] = useState<string | null>(null);
  const [logIndexError, setLogIndexError] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [step7Confirm, setStep7Confirm] = useState(false);
  const [step7Batch, setStep7Batch] = useState("");
  const [acting, setActing] = useState(false);
  const [lastAutoSyncedAt, setLastAutoSyncedAt] = useState<string | null>(null);

  async function loadDetail() {
    if (!analysisId) return;
    setLoading(true);
    setError(null);
    setLogIndexError(null);
    setProgressError(null);
    setConfigError(null);
    try {
      const detail = await getRunDetail(analysisId);
      if (!capabilities.isDeployed(detail.pipeline as DeployedPipeline)) {
        throw new Error("This run belongs to a pipeline that is not deployed in this environment.");
      }
      const [samples, rules, progress, artifacts, config, indexedLogs, pods, transfers, validationIssues] = await Promise.all([
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunProgress(analysisId).catch((progressLoadError) => {
          setProgressError(errorMessage(progressLoadError));
          return null;
        }),
        getRunArtifacts(analysisId),
        getRunConfig(analysisId).catch((configLoadError) => {
          setConfigError(errorMessage(configLoadError));
          return null;
        }),
        getRunLogIndex(analysisId).catch((indexLoadError) => {
          setLogIndexError(errorMessage(indexLoadError));
          return {items: []};
        }),
        getRunPods(analysisId).catch(() => ({items: []})),
        getRunTransfers(analysisId).catch(() => ({items: []})),
        getRunValidationIssues(analysisId).catch(() => ({items: []})),
      ]);
      setBundle({detail, samples: samples.items, manifest: samples.manifest || [], rules: rules.items, progress, artifacts: artifacts.items, config, pods: pods.items, transfers: transfers.items, validationIssues: validationIssues.items});
      setLogSources(indexedLogs.items);
      if (indexedLogs.items.length) {
        const preferred = preferredLogSource(indexedLogs.items, detail.status, progress?.current_step) || indexedLogs.items[0];
        setLogKey((current) => indexedLogs.items.some((item) => item.key === current) ? current : preferred.key);
        setLogStream(preferred.stream === "stderr" ? "stderr" : preferred.stream === "metadata" ? "metadata" : "stdout");
      } else if (isFailedStatus(detail.status)) {
        setLogStream("stderr");
      }
    } catch (loadError) {
      setBundle(emptyBundle);
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }

  async function loadLog(stream: LogStream, key?: string | null) {
    if (!analysisId) return;
    setLog(null);
    setLogError(null);
    try {
      setLog(await getRunLog(analysisId, stream, key || undefined));
    } catch (loadError) {
      setLogError(errorMessage(loadError));
    }
  }

  useEffect(() => {
    if (!capabilities.loading) void loadDetail();
  }, [analysisId, capabilities.loading, capabilityKey]);
  useEffect(() => {
    const pipeline = bundle.detail?.pipeline;
    if (
      pipeline
      && capabilities.isDeployed(pipeline as DeployedPipeline)
      && (pipeline !== "wgs" || Boolean(logKey))
    ) void loadLog(logStream, logKey);
  }, [analysisId, bundle.detail?.pipeline, capabilityKey, logKey, logStream]);

  function handleLogKeyChange(nextKey: string) {
    const source = logSources.find((item) => item.key === nextKey);
    setLogKey(nextKey);
    if (source?.stream === "stderr" || source?.stream === "metadata" || source?.stream === "stdout") {
      setLogStream(source.stream);
    }
  }

  const detail = bundle.detail;

  useEffect(() => {
    if (!analysisId || !detail || !isActiveStatus(detail.status)) return;
    let stopped = false;
    const refreshActiveRun = async () => {
      try {
        if (detail.dag_run_id) await syncAirflow(analysisId);
        if (stopped) return;
        setLastAutoSyncedAt(new Date().toISOString());
        await loadDetail();
      } catch (syncError) {
        if (!stopped) setActionError(errorMessage(syncError));
      }
    };
    void refreshActiveRun();
    const interval = window.setInterval(() => void refreshActiveRun(), 5000);
    return () => { stopped = true; window.clearInterval(interval); };
  }, [analysisId, detail?.dag_run_id, detail?.status]);

  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(
    detail?.error_summary,
    failedRule?.rule || (detail?.pipeline === "wgs" ? bundle.progress?.stage_label : null),
  );
  const progress = detail && bundle.progress ? progressFromResponse(bundle.progress) : null;
  const canSubmit = detail?.status === "created" && capabilities.isDeployed(detail.pipeline as DeployedPipeline);
  async function runAction(action: "sync" | "submit" | "resume" | "rerun_failed" | "cancel" | "revalidate" | "repair_step4") {
    if (!analysisId) return;
    setActing(true);
    setActionError(null);
    try {
      if (action === "sync") await syncAirflow(analysisId);
      if (action === "submit") await submitRun(analysisId);
      if (action === "resume") await resumeRun(analysisId);
      if (action === "rerun_failed") await rerunFailedRun(analysisId);
      if (action === "cancel") await cancelRun(analysisId);
      if (action === "revalidate") await revalidateRun(analysisId);
      if (action === "repair_step4") await repairStep4(analysisId);
      await loadDetail();
      await loadLog(action === "sync" ? logStream : "stdout");
      if (action !== "sync") setLogStream("stdout");
    } catch (actionFailure) {
      setActionError(errorMessage(actionFailure));
    } finally {
      setActing(false);
    }
  }

  async function runStep7Cleanup() {
    if (!analysisId || !detail?.step7_cleanup?.available) return;
    setActing(true); setActionError(null);
    try {
      await cleanupStep7(analysisId, step7Batch);
      setStep7Confirm(false); setStep7Batch("");
      await loadDetail();
    } catch (actionFailure) { setActionError(errorMessage(actionFailure)); }
    finally { setActing(false); }
  }

  if (loading && !detail) return <p className="muted">Loading run detail...</p>;

  return (
    <div className="page-stack run-detail-page">
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {detail ? <>
        <section className="run-summary-header">
          <div><p className="eyebrow">Run detail</p><h1>{detail.analysis_id}</h1><p>{compactPipelineName(detail.pipeline)} / {detail.dag_id || "no DAG"} / {detail.mode || "mode not set"}</p></div>
          <div className="summary-actions">
            <StatusBadge status={detail.status} size="lg" />
            {detail.dag_run_id && isActiveStatus(detail.status) ? <span className="muted">{lastAutoSyncedAt ? `Auto sync / ${formatDate(lastAutoSyncedAt)}` : "Auto sync active"}</span> : null}
            {canSubmit ? <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("submit")}><Play size={15} />Submit to Airflow</button> : null}
            {detail.status === "needs_review" && session.hasRole("operator") ? <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("revalidate")}><RefreshCw size={15} />Revalidate source</button> : null}
            {detail.status === "failed" ? <><button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("resume")}><RotateCcw size={15} />Resume</button><button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("rerun_failed")}><RotateCcw size={15} />Rerun failed</button></> : null}
            {isActiveStatus(detail.status) ? <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("cancel")}><Square size={15} />Cancel</button> : null}
            <button className="button ghost" type="button" disabled={acting || !detail.dag_run_id} onClick={() => void runAction("sync")}><RefreshCw size={15} />Sync Airflow</button>
          </div>
        </section>
        {actionError ? <div className="inline-error" role="alert">{actionError}</div> : null}
        {detail.step4_repair?.available || detail.step4_repair?.latest_action ? <Step4RepairPanel capability={detail.step4_repair} canOperate={session.hasRole("operator")} acting={acting} onRepair={() => void runAction("repair_step4")} /> : null}
        {session.hasRole("admin") && (detail.step7_cleanup?.available || detail.step7_cleanup?.latest_action) ? <section className="panel destructive-panel"><div className="section-heading"><h2>SFS cleanup</h2><p>Step7 deletes only the frozen run SFS analysis and linkage directories. OBS data is not deleted.</p></div>{detail.step7_cleanup.latest_action ? <StatusBadge status={detail.step7_cleanup.latest_action.status} /> : null}{detail.step7_cleanup.available ? <><label className="field checkbox-field"><input type="checkbox" aria-label="Acknowledge SFS cleanup" checked={step7Confirm} onChange={(event) => setStep7Confirm(event.target.checked)} /><span>I verified Step5 and Step6 results and understand SFS cleanup is destructive.</span></label><label className="field"><span>Type Batch to confirm</span><input aria-label="Step7 Batch confirmation" value={step7Batch} onChange={(event) => setStep7Batch(event.target.value)} /></label><button className="button danger" type="button" disabled={acting || !step7Confirm || step7Batch !== detail.step7_cleanup.required_batch} onClick={() => void runStep7Cleanup()}>Run Step7 SFS cleanup</button></> : null}</section> : null}
        {detail.status === "needs_review" ? <section className="panel validation-review"><div className="section-heading"><h2>Input needs review</h2><p>Correct the source links or metadata upstream, then revalidate. This page cannot edit sampleinfo.</p></div><WgsTable headers={["Severity", "Code", "Scope", "Message", "Status"]} rows={bundle.validationIssues.map((issue) => [issue.severity, issue.code, issue.sample_id || issue.family_id || issue.file_path || issue.scope_type || "batch", issue.message, issue.status])} empty="No structured issue was returned." /></section> : null}
        <section className="metric-grid" aria-label="Run summary metrics">
          <MetricCard title="Samples" value={bundle.samples.length} />
          <MetricCard title="Duration" value={formatDuration(detail.submitted_at || detail.started_at, detail.pipeline_finished_at || detail.ended_at)} status={detail.status} />
          <MetricCard title="Batch" value={String(detail.params?.batch_no || "-")} />
          <MetricCard title="Rule events" value={bundle.rules.length} status={failedRule ? "failed" : undefined} />
        </section>
        {detail.pipeline === "wgs" ? <section className="panel">
          <div className="section-heading"><h2>Pipeline evidence</h2><p>Fixed WGS release, resolved CCE runtime and local observer freshness.</p></div>
          <div className="definition-grid">
            <div><dt>Release</dt><dd className="path-text">{detail.pipeline_release_id || "not pinned"}</dd></div>
            <div><dt>WGS version</dt><dd>{detail.wgs_version || "unknown"}</dd></div>
            <div><dt>WGS commit</dt><dd className="path-text">{detail.wgs_source_commit || "unknown"}</dd></div>
            <div><dt>cce-pipeline</dt><dd>{detail.resolved_runtime?.cce_pipeline_version || "not resolved"}</dd></div>
            <div><dt>CCE profile</dt><dd>{detail.resolved_runtime?.profile_id ? `${detail.resolved_runtime.profile_id}/${detail.resolved_runtime.profile_revision || "-"}` : "not resolved"}</dd></div>
            <div><dt>Rule schema</dt><dd>{detail.rule_event_schema_version || "unknown"}</dd></div>
            <div><dt>CCE monitor</dt><dd>{detail.observer ? <StatusBadge status={detail.observer.lifecycle_status} /> : "CCE监控尚未启动"}</dd></div>
            <div><dt>Monitoring health</dt><dd>{detail.observer ? <StatusBadge status={detail.observer.monitoring_health} /> : "not applicable"}</dd></div>
            <div><dt>Last evidence</dt><dd>{formatDate(detail.observer?.last_success_at || detail.observer?.updated_at)}</dd></div>
          </div>
          {detail.observer?.last_error ? <div className="inline-error" role="alert">Rule monitoring degraded: {detail.observer.last_error}</div> : null}
        </section> : null}
        {isFailedStatus(detail.status) ? <ErrorPanel diagnosis={diagnosis} showErrorLogPath={detail.pipeline !== "wgs"} /> : null}
        {progressError ? <div className="inline-error" role="alert">Current progress unavailable: {progressError}</div> : null}
        <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} stage={bundle.progress} />
        <section className="panel">
          <div className="tabs" role="tablist" aria-label="Run detail tabs">{tabs.map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} role="tab" type="button" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
          {activeTab === "Overview" ? <RunOverviewTab detail={detail} samples={bundle.manifest} /> : null}
          {activeTab === "Samples" ? <WgsSamplesTab samples={bundle.samples} /> : null}
          {activeTab === "Rules" ? <RunWorkflowTab progress={bundle.progress} rules={bundle.rules} onOpenLog={(key) => { setLogKey(key); setLogStream("stdout"); setActiveTab("Logs"); }} /> : null}
          {activeTab === "Master" ? <WgsMasterTab pods={bundle.pods} /> : null}
          {activeTab === "Transfers" ? <WgsTransfersTab detail={detail} transfers={bundle.transfers} /> : null}
          {activeTab === "Logs" ? <>{logIndexError ? <div className="inline-error" role="alert">Log index unavailable: {logIndexError}</div> : null}<LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} sources={logSources} activeKey={logKey} onKeyChange={handleLogKeyChange} /></> : null}
          {activeTab === "Files" ? <RunFilesTab artifacts={bundle.artifacts} /> : null}
        </section>
      </> : null}
    </div>
  );
}

function WgsSamplesTab({samples}: {samples: Sample[]}) {
  return <WgsTable headers={["Sample", "Data", "Family / relation", "Current stage", "Current Rule", "Rules", "Progress", "Status", "Elapsed", "QC", "Safe QC metrics"]} rows={samples.map((sample) => [sample.sample_id, sample.data_id || "-", [sample.family_id, sample.family_relation].filter(Boolean).join(" / ") || "-", sample.current_stage || "-", sample.current_rule || "-", `${sample.completed_rules ?? 0}/${sample.total_rules ?? 0}`, sample.progress_percent == null ? "-" : `${sample.progress_percent}%`, sample.status || "-", sample.elapsed_seconds == null ? "-" : formatSecondsDuration(sample.elapsed_seconds), sample.qc_status || "unknown", compactQc(sample.qc_metrics)])} empty="No analysis sample state returned." />;
}

function WgsMasterTab({pods}: {pods: WgsPod[]}) {
  return <WgsTable headers={["Master Job", "Pod hash", "Phase", "Reason", "Exit", "Node", "Resources", "Message"]} rows={pods.map((pod) => [pod.job_name ?? "-", pod.pod_hash, pod.phase ?? "-", pod.reason ?? "-", pod.exit_code ?? "-", pod.node_name ?? "-", compactResources(pod.resources), pod.message ?? "-"])} empty="Master Pod evidence is not available yet." />;
}

function WgsTransfersTab({detail, transfers}: {detail: RunDetail; transfers: WgsTransfer[]}) {
  return <div className="transfer-list">{transfers.map((transfer) => {
    const hasDetail = transfer.progress_detail_available === true;
    const title = transfer.direction === "download" ? "Results download" : "FASTQ upload";
    return <section className="transfer-card" key={transfer.transfer_id || `${transfer.source}-${transfer.destination}`}>
      <div className="section-heading"><div><h3>{title}</h3><p>Batch {String(detail.params?.sequencing_batch || detail.params?.analysis_batch || "-")} · Attempt {transfer.attempt ?? 1}{transfer.progress_basis === "legacy_estimate" ? " · Legacy estimate" : ""}</p></div><StatusBadge status={transfer.status || "unknown"} size="lg" /></div>
      {hasDetail ? <>
        <progress className="transfer-progress" max={100} value={transfer.progress_percent ?? 0} aria-label={`${title} progress`} />
        <div className="definition-grid"><div><dt>Progress</dt><dd>{transfer.progress_percent ?? 0}% / {formatBytes(transfer.bytes_transferred)} of {formatBytes(transfer.bytes_total)}</dd></div><div><dt>Speed</dt><dd>{formatBytes(transfer.speed_bps)}/s</dd></div><div><dt>ETA</dt><dd>{transfer.eta_seconds == null ? "-" : formatSecondsDuration(transfer.eta_seconds)}</dd></div><div><dt>Files</dt><dd>{transfer.files_completed ?? "-"} / {transfer.files_total ?? "-"}</dd></div><div><dt>Current file</dt><dd className="path-text">{transfer.current_file || "-"}</dd></div><div><dt>Heartbeat</dt><dd>{formatDate(transfer.heartbeat_at)}</dd></div></div>
      </> : <div className="transfer-phase-status">
        <p>阶段状态可用；当前 cce-pipeline 合同未提供可靠的字节、速度或 ETA 明细。</p>
        <div className="definition-grid"><div><dt>Stage message</dt><dd>{transfer.message || "Waiting for the next stage status."}</dd></div><div><dt>Heartbeat</dt><dd>{formatDate(transfer.heartbeat_at)}</dd></div></div>
      </div>}
    </section>;
  })}{transfers.length === 0 ? <p className="empty-state">No transfers returned.</p> : null}</div>;
}

function WgsTable({headers, rows, empty}: {headers: string[]; rows: Array<Array<string | number>>; empty: string}) {
  return <div className="table-wrap"><table className="data-table"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((value, cell) => <td key={cell}>{value}</td>)}</tr>)}{rows.length === 0 ? <tr><td className="empty-cell" colSpan={headers.length}>{empty}</td></tr> : null}</tbody></table></div>;
}

function compactResources(resources?: Record<string, unknown> | null): string {
  if (!resources || Object.keys(resources).length === 0) return "-";
  return JSON.stringify(resources);
}

function compactQc(metrics?: Record<string, string | number | null>): string {
  if (!metrics || Object.keys(metrics).length === 0) return "-";
  const labels: Record<string, string> = {clean_q30_percent: "Q30", mapped_reads_percent: "Mapped", average_depth: "Depth", coverage_20x_percent: "20X", contamination: "Contam"};
  return Object.entries(metrics).map(([key, value]) => `${labels[key] || key}: ${value}`).join(" · ");
}
