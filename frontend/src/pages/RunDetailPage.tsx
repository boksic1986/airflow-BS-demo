import {Play, RefreshCw, RotateCcw, Square} from "lucide-react";
import {useCallback, useEffect, useRef, useState, type ReactNode} from "react";
import {useParams} from "react-router-dom";

import type {Artifact, DeployedPipeline, LogStream, RuleEvent, RunDetail, RunLog, RunLogIndexItem, RunProgressResponse, Sample, WgsExecutionChoiceRequest, WgsManifestSummary, WgsPod, WgsSampleManifestRow, WgsTransfer, WgsValidationIssue} from "../api";

import {
  ApiError,
  getRunArtifacts,
  getRunDetail,
  getRunPods,
  getRunProgress,
  getRunValidationIssues,
  getRunTransfers,
  getRunWorkspace,
  getRunLog,
  getRunLogIndex,
  getRunRules,
  getRunSamples,
  submitRun,
  syncAirflow, cancelRun, cleanupStep7, rerunFailedRun, resumeRun, revalidateRun, repairStep4, updateWgsExecutionChoice,
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
import {Step7CleanupPanel} from "../features/run-detail/Step7CleanupPanel";
import {DataLifecyclePanel} from "../features/run-detail/DataLifecyclePanel";
import {WgsTransfersTab} from "../features/run-detail/WgsTransfersTab";
import {ExecutionTargetSelector} from "../features/wgs/ExecutionTargetSelector";
import {errorMessage, parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatDate, formatDuration, formatPercent, formatSecondsDuration} from "../lib/format";
import {progressFromResponse} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus} from "../lib/status";

const allTabs = ["Overview", "Samples", "Rules", "Master", "Transfers", "QC", "Logs", "Files"] as const;
type DetailTab = (typeof allTabs)[number];

type Bundle = {
  detail: RunDetail | null;
  samples: Sample[];
  manifest: WgsSampleManifestRow[];
  manifestSummary: WgsManifestSummary | null;
  rules: RuleEvent[];
  artifacts: Artifact[];
  progress: RunProgressResponse | null;
  pods: WgsPod[];
  transfers: WgsTransfer[];
  validationIssues: WgsValidationIssue[];
  slotUsage: {pool: string; used: number; limit: number; waiting: number; mode: string} | null;
  snapshotAt: string | null;
};

const emptyBundle: Bundle = {detail: null, samples: [], manifest: [], manifestSummary: null, rules: [], artifacts: [], progress: null, pods: [], transfers: [], validationIssues: [], slotUsage: null, snapshotAt: null};

export function RunDetailPage() {
  const {analysisId = ""} = useParams();
  const capabilities = usePlatformCapabilities();
  const session = useSession();
  const capabilityKey = capabilities.deployed_pipelines.join(",");
  const [bundle, setBundle] = useState<Bundle>(emptyBundle);
  const [summary, setSummary] = useState({sample_count: 0, rule_count: 0, failed_rule_count: 0});
  const [loadedTabs, setLoadedTabs] = useState<Set<DetailTab>>(new Set());
  const [tabError, setTabError] = useState<string | null>(null);
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
  const [actionError, setActionError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [lastAutoSyncedAt, setLastAutoSyncedAt] = useState<string | null>(null);
  const workspaceRequestInFlight = useRef(false);

  const loadDetail = useCallback(async (showSpinner = true) => {
    if (!analysisId) return;
    if (workspaceRequestInFlight.current) return;
    workspaceRequestInFlight.current = true;
    if (showSpinner) setLoading(true);
    setError(null);
    setProgressError(null);
    try {
      let detail: RunDetail;
      let progress: RunProgressResponse | null;
      let validationIssues: WgsValidationIssue[];
      let slotUsage: Bundle["slotUsage"];
      try {
        const workspace = await getRunWorkspace(analysisId);
        detail = workspace.run;
        progress = workspace.progress;
        validationIssues = workspace.validation_issues || [];
        slotUsage = workspace.slot_usage;
        setSummary(workspace.summary);
        setBundle((current) => {
          const active = workspace.active_transfer;
          const transfers = !active
            ? current.transfers
            : current.transfers.some((item) => item.transfer_id === active.transfer_id)
              ? current.transfers.map((item) => item.transfer_id === active.transfer_id ? active : item)
              : [active, ...current.transfers];
          return {...current, transfers, snapshotAt: workspace.snapshot_at || new Date().toISOString()};
        });
      } catch (workspaceError) {
        if (!(workspaceError instanceof ApiError) || workspaceError.status !== 404) throw workspaceError;
        const [legacyDetail, legacyProgress, samples, rules, failedRules, issues] = await Promise.all([
          getRunDetail(analysisId),
          getRunProgress(analysisId),
          getRunSamples(analysisId),
          getRunRules(analysisId, {limit: 1}),
          getRunRules(analysisId, {limit: 1, status: "failed"}),
          getRunValidationIssues(analysisId).catch(() => ({items: []})),
        ]);
        detail = legacyDetail;
        progress = legacyProgress;
        validationIssues = issues.items;
        slotUsage = null;
        setSummary({sample_count: samples.items.length, rule_count: rules.total, failed_rule_count: failedRules.total});
        setBundle((current) => ({...current, samples: samples.items, manifest: samples.manifest || [], manifestSummary: samples.manifest_summary || null}));
      }
      if (!capabilities.isDeployed(detail.pipeline as DeployedPipeline)) {
        throw new Error("This run belongs to a pipeline that is not deployed in this environment.");
      }
      setBundle((current) => ({...current, detail, progress, validationIssues, slotUsage}));
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      if (showSpinner) setLoading(false);
      workspaceRequestInFlight.current = false;
    }
  }, [analysisId, capabilities]);

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
    setBundle(emptyBundle);
    setSummary({sample_count: 0, rule_count: 0, failed_rule_count: 0});
    setLoadedTabs(new Set());
    if (!capabilities.loading) void loadDetail();
  }, [analysisId, capabilities.loading, capabilityKey]);
  useEffect(() => {
    const pipeline = bundle.detail?.pipeline;
    if (
      pipeline
      && capabilities.isDeployed(pipeline as DeployedPipeline)
      && (!["wgs", "gatk"].includes(pipeline) || Boolean(logKey))
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
  const tabs = detail?.pipeline === "gatk"
    ? allTabs.filter((tab) => tab !== "QC")
    : [...allTabs];

  useEffect(() => {
    if (!analysisId || !detail || loadedTabs.has(activeTab)) return;
    let canceled = false;
    const loadTab = async () => {
      setTabError(null);
      try {
        if (activeTab === "Overview" || activeTab === "Samples" || activeTab === "QC") {
          const result = await getRunSamples(analysisId);
          if (!canceled) setBundle((current) => ({...current, samples: result.items, manifest: result.manifest || [], manifestSummary: result.manifest_summary || null}));
        } else if (activeTab === "Rules") {
          const result = await getRunRules(analysisId, {limit: 50, sort: "active_first"});
          if (!canceled) setBundle((current) => ({...current, rules: result.items}));
        } else if (activeTab === "Master") {
          const result = await getRunPods(analysisId);
          if (!canceled) setBundle((current) => ({...current, pods: result.items}));
        } else if (activeTab === "Transfers") {
          const result = await getRunTransfers(analysisId);
          if (!canceled) setBundle((current) => ({...current, transfers: result.items}));
        } else if (activeTab === "Logs") {
          const result = await getRunLogIndex(analysisId);
          if (!canceled) {
            setLogSources(result.items);
            const preferred = preferredLogSource(result.items, detail.status, bundle.progress?.current_step) || result.items[0];
            if (preferred) {
              setLogKey(preferred.key);
              setLogStream(preferred.stream === "stderr" ? "stderr" : preferred.stream === "metadata" ? "metadata" : "stdout");
            }
          }
        } else if (activeTab === "Files") {
          const result = await getRunArtifacts(analysisId);
          if (!canceled) setBundle((current) => ({...current, artifacts: result.items}));
        }
        if (!canceled) setLoadedTabs((current) => {
          const next = new Set(current).add(activeTab);
          if (activeTab === "Overview" || activeTab === "Samples" || activeTab === "QC") {
            next.add("Overview");
            next.add("Samples");
            next.add("QC");
          }
          return next;
        });
      } catch (loadError) {
        if (!canceled) setTabError(errorMessage(loadError));
      }
    };
    void loadTab();
    return () => { canceled = true; };
  }, [activeTab, analysisId, detail?.status, loadedTabs]);

  useEffect(() => {
    const step7Status = detail?.step7_cleanup?.latest_action?.status?.toLowerCase();
    const step7Active = step7Status === "requested" || step7Status === "queued" || step7Status === "running";
    if (!analysisId || !detail || (!isActiveStatus(detail.status) && !step7Active)) return;
    const refreshActiveRun = async () => {
      if (document.visibilityState === "hidden") return;
      await loadDetail(false);
      if (activeTab === "Rules") {
        const result = await getRunRules(analysisId, {limit: 50, sort: "active_first"});
        setBundle((current) => ({...current, rules: result.items}));
      } else if (activeTab === "Overview" || activeTab === "Samples" || activeTab === "QC") {
        const result = await getRunSamples(analysisId);
        setBundle((current) => ({...current, samples: result.items, manifest: result.manifest || [], manifestSummary: result.manifest_summary || null}));
      } else if (activeTab === "Transfers") {
        const result = await getRunTransfers(analysisId);
        setBundle((current) => ({...current, transfers: result.items}));
      }
      setLastAutoSyncedAt(new Date().toISOString());
    };
    const interval = window.setInterval(() => void refreshActiveRun(), 5000);
    const onVisibility = () => { if (document.visibilityState === "visible") void refreshActiveRun(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => { window.clearInterval(interval); document.removeEventListener("visibilitychange", onVisibility); };
  }, [activeTab, analysisId, detail?.status, detail?.step7_cleanup?.latest_action?.status, loadDetail]);

  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(
    detail?.error_summary,
    failedRule?.rule || (detail?.pipeline === "wgs" ? bundle.progress?.stage_label : null),
  );
  const progress = detail && bundle.progress ? progressFromResponse(bundle.progress) : null;
  const canSubmit = detail?.status === "created" && capabilities.isDeployed(detail.pipeline as DeployedPipeline);
  const pipelineCapabilities = capabilities.pipelines.find((item) => item.id === detail?.pipeline)?.capabilities || [];
  const canResume = pipelineCapabilities.includes("resume");
  const canRerun = pipelineCapabilities.includes("rerun");
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

  async function runStep7Cleanup(batchConfirmation: string, retryFailed = false) {
    const latestAction = detail?.step7_cleanup?.latest_action;
    if (!analysisId || !detail?.step7_cleanup || (!detail.step7_cleanup.available && !(retryFailed && latestAction?.status === "failed"))) return;
    setActing(true); setActionError(null);
    try {
      await cleanupStep7(analysisId, batchConfirmation, retryFailed && latestAction ? {retryFailed: true, expectedActionId: latestAction.action_id} : undefined);
      await loadDetail();
    } catch (actionFailure) { setActionError(errorMessage(actionFailure)); }
    finally { setActing(false); }
  }

  async function switchExecutionTarget(payload: WgsExecutionChoiceRequest) {
    if (!analysisId) return;
    await updateWgsExecutionChoice(analysisId, payload);
    await loadDetail();
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
            {detail.dag_run_id && isActiveStatus(detail.status) ? <span className="muted">{lastAutoSyncedAt ? `Live snapshot / ${formatDate(lastAutoSyncedAt)}` : "Live snapshot active"}</span> : null}
            {canSubmit ? <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("submit")}><Play size={15} />Submit to Airflow</button> : null}
            {detail.status === "needs_review" && session.hasRole("operator") ? <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("revalidate")}><RefreshCw size={15} />Revalidate source</button> : null}
            {detail.status === "failed" && canResume ? <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("resume")}><RotateCcw size={15} />Resume</button> : null}
            {detail.status === "failed" && canRerun ? <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("rerun_failed")}><RotateCcw size={15} />Rerun failed</button> : null}
            {detail.pipeline !== "gatk" && isActiveStatus(detail.status) && !(detail.execution_dispatch?.desired_mode === "cce" && ["committed", "running"].includes(detail.execution_dispatch.dispatch_state)) ? <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("cancel")}><Square size={15} />Cancel</button> : null}
            <button className="button ghost" type="button" disabled={acting || !detail.dag_run_id} onClick={() => void runAction("sync")}><RefreshCw size={15} />Sync Airflow</button>
          </div>
        </section>
        {actionError ? <div className="inline-error" role="alert">{actionError}</div> : null}
        {detail.pipeline === "wgs" && detail.execution_dispatch ? <ExecutionTargetSelector attempt={detail.attempt || 1} batch={String(detail.params?.batch || detail.params?.sequencing_batch || detail.params?.batch_no || "-")} sampleCount={summary.sample_count} dispatch={detail.execution_dispatch} onSwitch={switchExecutionTarget} onRefresh={loadDetail} /> : null}
        {detail.step4_repair?.available || detail.step4_repair?.latest_action ? <Step4RepairPanel capability={detail.step4_repair} canOperate={session.hasRole("operator")} acting={acting} onRepair={() => void runAction("repair_step4")} /> : null}
        {session.hasRole("admin") && (detail.step7_cleanup?.available || detail.step7_cleanup?.latest_action) ? <Step7CleanupPanel capability={detail.step7_cleanup} acting={acting} onCleanup={(batchConfirmation, retryFailed) => void runStep7Cleanup(batchConfirmation, retryFailed)} /> : null}
        {detail.status === "needs_review" ? <section className="panel validation-review"><div className="section-heading"><h2>Input needs review</h2><p>Correct the source links or metadata upstream, then revalidate. This page cannot edit sampleinfo.</p></div><WgsTable headers={["Severity", "Code", "Scope", "Message", "Status"]} rows={bundle.validationIssues.map((issue) => [issue.severity, issue.code, issue.sample_id || issue.family_id || issue.file_path || issue.scope_type || "batch", issue.message, issue.status])} empty="No structured issue was returned." /></section> : null}
        <section className="metric-grid" aria-label="Run summary metrics">
          <MetricCard title="Samples" value={summary.sample_count} />
          <MetricCard title="Duration" value={formatDuration(detail.submitted_at || detail.started_at, detail.pipeline_finished_at || detail.ended_at)} status={detail.status} />
          <MetricCard title="Batch" value={String(detail.params?.batch_no || detail.params?.batch || "-")} />
          <MetricCard title="Rule events" value={summary.rule_count} status={summary.failed_rule_count ? "failed" : undefined} />
        </section>
        {detail.pipeline === "wgs" && detail.lifecycle ? <DataLifecyclePanel lifecycle={detail.lifecycle} /> : null}
        {isFailedStatus(detail.status) ? <ErrorPanel diagnosis={diagnosis} showErrorLogPath={detail.pipeline !== "wgs"} /> : null}
        {progressError ? <div className="inline-error" role="alert">Current progress unavailable: {progressError}</div> : null}
        {detail.pipeline === "wgs" ? <div className="run-detail-snapshot-grid">
          <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} stage={bundle.progress} />
          <section className="panel pipeline-evidence-panel snapshot-panel-stretch">
            <div className="section-heading"><h2>Pipeline evidence</h2></div>
            <div className="definition-grid pipeline-evidence-grid">
              <div><dt>Release</dt><dd className="path-text">{detail.pipeline_release_id || "not pinned"}</dd></div>
              <div><dt>WGS version</dt><dd>{detail.wgs_version || "unknown"}</dd></div>
              <div><dt>WGS commit</dt><dd className="path-text">{detail.wgs_source_commit || "unknown"}</dd></div>
              <div><dt>cce-pipeline</dt><dd>{detail.resolved_runtime?.cce_pipeline_version || "not resolved"}</dd></div>
              <div><dt>CCE profile</dt><dd>{detail.resolved_runtime?.profile_id ? `${detail.resolved_runtime.profile_id}/${detail.resolved_runtime.profile_revision || "-"}` : "not resolved"}</dd></div>
              <div><dt>Execution target</dt><dd>{detail.execution_dispatch?.desired_target || detail.execution_mode || "not resolved"}</dd></div>
              <div><dt>Project path</dt><dd className="path-text">{bundle.manifestSummary?.project_path || "not recorded"}</dd></div>
            </div>
            {detail.observer?.last_error ? <div className="inline-error" role="alert">Rule monitoring degraded: {detail.observer.last_error}</div> : null}
          </section>
        </div> : detail.pipeline === "gatk" ? <div className="run-detail-snapshot-grid">
          <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} stage={bundle.progress} />
          <section className="panel pipeline-evidence-panel">
            <div className="section-heading"><h2>GATK execution contract</h2><p>Frozen manual submission and CCE runtime identity.</p></div>
            <div className="definition-grid pipeline-evidence-grid">
              <div><dt>Release</dt><dd className="path-text">{detail.pipeline_release_id || "not pinned"}</dd></div>
              <div><dt>GATK workflow</dt><dd>{detail.gatk_version || "V7.6.0"}</dd></div>
              <div><dt>Runtime profile</dt><dd>{detail.runtime_profile_id || "not pinned"}</dd></div>
              <div><dt>Input snapshot</dt><dd className="path-text">{detail.submission_preview_hash ? detail.submission_preview_hash.slice(0, 12) : "not captured"}</dd></div>
            </div>
          </section>
        </div> : <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} stage={bundle.progress} />}
        <section className="panel">
          <div className="tabs" role="tablist" aria-label="Run detail tabs">{tabs.map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} role="tab" type="button" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
          {tabError ? <div className="inline-error" role="alert">This tab could not be loaded: {tabError}</div> : null}
          {activeTab === "Overview" ? <RunOverviewTab detail={detail} samples={bundle.manifest} sampleCount={summary.sample_count} manifestSummary={bundle.manifestSummary} /> : null}
          {activeTab === "Samples" ? <WgsSamplesTab samples={bundle.samples} manifest={bundle.manifest} showQc={detail.pipeline !== "gatk"} /> : null}
          {activeTab === "Rules" ? <RunWorkflowTab progress={bundle.progress} rules={bundle.rules} onOpenLog={(key) => { setLogKey(key); setLogStream("stdout"); setActiveTab("Logs"); }} /> : null}
          {activeTab === "Master" ? <WgsMasterTab pods={bundle.pods} /> : null}
          {activeTab === "Transfers" ? <WgsTransfersTab detail={detail} transfers={bundle.transfers} refreshKey={bundle.snapshotAt} /> : null}
          {activeTab === "QC" ? <WgsQcTab samples={bundle.samples} /> : null}
          {activeTab === "Logs" ? <>{logIndexError ? <div className="inline-error" role="alert">Log index unavailable: {logIndexError}</div> : null}<LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} sources={logSources} activeKey={logKey} onKeyChange={handleLogKeyChange} /></> : null}
          {activeTab === "Files" ? <RunFilesTab artifacts={bundle.artifacts} /> : null}
        </section>
      </> : null}
    </div>
  );
}

function WgsSamplesTab({samples, manifest, showQc = true}: {samples: Sample[]; manifest: WgsSampleManifestRow[]; showQc?: boolean}) {
  const manifestBySample = new Map(manifest.map((item) => [item.sample_id, item]));
  const headers = ["Sample", "Family / relation", "Received", "Estimated report", "Current stage", "Current Rule", "Rules", "Progress", "Status", "Elapsed"];
  if (showQc) headers.push("QC");
  return <WgsTable headers={headers} rows={samples.map((sample) => {
    const frozen = manifestBySample.get(sample.sample_id);
    const row: ReactNode[] = [sample.sample_id, [sample.family_id || frozen?.family_id, sample.family_relation || frozen?.family_relation].filter(Boolean).join(" / ") || "-", frozen?.received_date || "-", frozen?.estimated_report_date || "-", sample.current_stage || "-", sample.current_rule || "-", `${sample.completed_rules ?? 0}/${sample.total_rules ?? 0}`, formatPercent(sample.progress_percent), <StatusBadge status={sample.status || "unknown"} size="sm" />, sample.elapsed_seconds == null ? "-" : formatSecondsDuration(sample.elapsed_seconds)];
    if (showQc) row.push(<StatusBadge status={qcDisplayStatus(sample)} size="sm" />);
    return row;
  })} empty="No analysis sample state returned." />;
}

function WgsQcTab({samples}: {samples: Sample[]}) {
  return <WgsTable headers={["Sample", "QC status", "Q30", "Mapped", "Average depth", "≥20X", "Contamination"]} rows={samples.map((sample) => [
    sample.sample_id,
    <StatusBadge status={qcDisplayStatus(sample)} size="sm" />,
    qcMetric(sample, "clean_q30_percent"),
    qcMetric(sample, "mapped_reads_percent"),
    qcMetric(sample, "average_depth"),
    qcMetric(sample, "coverage_20x_percent"),
    qcMetric(sample, "contamination"),
  ])} empty="QC is pending or unavailable because the batch QCstat has not been projected yet." />;
}

function WgsMasterTab({pods}: {pods: WgsPod[]}) {
  return <WgsTable headers={["Master Job", "Pod hash", "Phase", "Reason", "Exit", "Node", "Resources", "Message"]} rows={pods.map((pod) => [pod.job_name ?? "-", pod.pod_hash, pod.phase ?? "-", pod.reason ?? "-", pod.exit_code ?? "-", pod.node_name ?? "-", compactResources(pod.resources), pod.message ?? "-"])} empty="Master Pod evidence is not available yet." />;
}

function WgsTable({headers, rows, empty}: {headers: string[]; rows: Array<Array<ReactNode>>; empty: string}) {
  return <div className="table-wrap"><table className="data-table"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((value, cell) => <td key={cell}>{value}</td>)}</tr>)}{rows.length === 0 ? <tr><td className="empty-cell" colSpan={headers.length}>{empty}</td></tr> : null}</tbody></table></div>;
}

function compactResources(resources?: Record<string, unknown> | null): string {
  if (!resources || Object.keys(resources).length === 0) return "-";
  return JSON.stringify(resources);
}

function qcDisplayStatus(sample: Sample): string {
  if (sample.qc_status && sample.qc_status !== "unknown") return sample.qc_status;
  return isActiveStatus(sample.status || "") ? "pending" : "unavailable";
}

function qcMetric(sample: Sample, key: string): string | number {
  const value = sample.qc_metrics?.[key];
  return value == null || value === "" ? "-" : value;
}
