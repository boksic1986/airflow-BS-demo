import {Play, RefreshCw, RotateCcw, Square} from "lucide-react";
import {useEffect, useState} from "react";
import {useParams} from "react-router-dom";

import type {Artifact, DeployedPipeline, LogStream, RuleEvent, RunConfig, RunDetail, RunLog, RunLogIndexItem, RunProgressResponse, RunQc, RunResourceSummary, Sample, WgsFamily, WgsPod, WgsTransfer} from "../api";

import {
  getRunArtifacts,
  getRunFamilies,
  getRunPods,
  getRunTransfers,
  getRunConfig,
  getRunDetail,
  getRunLog,
  getRunLogIndex,
  getRunProgress,
  getRunQc,
  getRunResources,
  getRunRules,
  getRunSamples,
  submitRun,
  syncAirflow, cancelRun, rerunFailedRun, resumeRun,
} from "../api";
import {ErrorPanel} from "../components/ErrorPanel";
import {LogViewer, preferredLogSource} from "../components/LogViewer";
import {MetricCard} from "../components/MetricCard";
import {StatusBadge} from "../components/StatusBadge";
import {CurrentProgressPanel} from "../features/run-detail/CurrentProgressPanel";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {RunQcTab} from "../features/run-detail/RunQcTab";
import {RunFilesTab, RunOverviewTab} from "../features/run-detail/RunResourceTabs";
import {RunWorkflowTab} from "../features/run-detail/RunWorkflowTab";
import {errorMessage, parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatBytes, formatDate, formatDuration, formatSecondsDuration} from "../lib/format";
import {computeRunProgress, progressFromResponse} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus} from "../lib/status";

const tabs = ["Overview", "Families", "Rules", "Pods", "Transfers", "QC", "Logs", "Files"] as const;
type DetailTab = (typeof tabs)[number];

type Bundle = {
  detail: RunDetail | null;
  samples: Sample[];
  rules: RuleEvent[];
  artifacts: Artifact[];
  qc: RunQc | null;
  progress: RunProgressResponse | null;
  config: RunConfig | null;
  resources: RunResourceSummary | null;
  families: WgsFamily[];
  pods: WgsPod[];
  transfers: WgsTransfer[];
};

const emptyBundle: Bundle = {detail: null, samples: [], rules: [], artifacts: [], qc: null, progress: null, config: null, resources: null, families: [], pods: [], transfers: []};

export function RunDetailPage() {
  const {analysisId = ""} = useParams();
  const capabilities = usePlatformCapabilities();
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
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [lastAutoSyncedAt, setLastAutoSyncedAt] = useState<string | null>(null);

  async function loadDetail() {
    if (!analysisId) return;
    setLoading(true);
    setError(null);
    setResourceError(null);
    setLogIndexError(null);
    setProgressError(null);
    setConfigError(null);
    try {
      const detail = await getRunDetail(analysisId);
      if (!capabilities.isDeployed(detail.pipeline as DeployedPipeline)) {
        throw new Error("This run belongs to a pipeline that is not deployed in this environment.");
      }
      const [samples, rules, progress, artifacts, qc, config, indexedLogs, resources, families, pods, transfers] = await Promise.all([
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunProgress(analysisId).catch((progressLoadError) => {
          setProgressError(errorMessage(progressLoadError));
          return null;
        }),
        getRunArtifacts(analysisId),
        getRunQc(analysisId),
        getRunConfig(analysisId).catch((configLoadError) => {
          setConfigError(errorMessage(configLoadError));
          return null;
        }),
        getRunLogIndex(analysisId).catch((indexLoadError) => {
          setLogIndexError(errorMessage(indexLoadError));
          return {items: []};
        }),
        getRunResources(analysisId).catch((resourceLoadError) => {
          setResourceError(errorMessage(resourceLoadError));
          return null;
        }),
        getRunFamilies(analysisId).catch(() => ({items: []})),
        getRunPods(analysisId).catch(() => ({items: []})),
        getRunTransfers(analysisId).catch(() => ({items: []})),
      ]);
      setBundle({detail, samples: samples.items, rules: progress?.rule_events || rules.items, progress, artifacts: artifacts.items, qc, config, resources, families: families.items, pods: pods.items, transfers: transfers.items});
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
    if (pipeline && capabilities.isDeployed(pipeline as DeployedPipeline)) void loadLog(logStream, logKey);
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
    if (!analysisId || !detail?.dag_run_id || !isActiveStatus(detail.status)) return;
    let stopped = false;
    const refreshFromAirflow = async () => {
      try {
        await syncAirflow(analysisId);
        if (stopped) return;
        setLastAutoSyncedAt(new Date().toISOString());
        await loadDetail();
      } catch (syncError) {
        if (!stopped) setActionError(errorMessage(syncError));
      }
    };
    void refreshFromAirflow();
    const interval = window.setInterval(() => void refreshFromAirflow(), 5000);
    return () => { stopped = true; window.clearInterval(interval); };
  }, [analysisId, detail?.dag_run_id, detail?.status]);

  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(detail?.error_summary, failedRule?.rule);
  const progress = detail && bundle.progress
    ? progressFromResponse(bundle.progress)
    : detail
      ? computeRunProgress({analysis_id: detail.analysis_id, pipeline: detail.pipeline, status: detail.status, created_at: detail.created_at, started_at: detail.started_at, ended_at: detail.ended_at, sample_count: bundle.samples.length}, detail, bundle.rules)
      : null;
  const canSubmit = detail?.status === "created" && capabilities.isDeployed(detail.pipeline as DeployedPipeline);
  async function runAction(action: "sync" | "submit" | "resume" | "rerun_failed" | "cancel") {
    if (!analysisId) return;
    setActing(true);
    setActionError(null);
    try {
      if (action === "sync") await syncAirflow(analysisId);
      if (action === "submit") await submitRun(analysisId);
      if (action === "resume") await resumeRun(analysisId);
      if (action === "rerun_failed") await rerunFailedRun(analysisId);
      if (action === "cancel") await cancelRun(analysisId);
      await loadDetail();
      await loadLog(action === "sync" ? logStream : "stdout");
      if (action !== "sync") setLogStream("stdout");
    } catch (actionFailure) {
      setActionError(errorMessage(actionFailure));
    } finally {
      setActing(false);
    }
  }

  if (loading && !detail) return <p className="muted">Loading run detail...</p>;

  const sampleQcSummary = bundle.qc?.sample_summary || bundle.qc?.summary;

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
            {detail.status === "failed" ? <><button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("resume")}><RotateCcw size={15} />Resume</button><button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("rerun_failed")}><RotateCcw size={15} />Rerun failed</button></> : null}
            {isActiveStatus(detail.status) ? <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("cancel")}><Square size={15} />Cancel</button> : null}
            <button className="button ghost" type="button" disabled={acting || !detail.dag_run_id} onClick={() => void runAction("sync")}><RefreshCw size={15} />Sync Airflow</button>
          </div>
        </section>
        {actionError ? <div className="inline-error" role="alert">{actionError}</div> : null}
        <section className="metric-grid" aria-label="Run summary metrics">
          <MetricCard title="Samples" value={bundle.samples.length} />
          <MetricCard title="Duration" value={formatDuration(detail.submitted_at || detail.started_at, detail.pipeline_finished_at || detail.ended_at)} status={detail.status} />
          <MetricCard title="QC fail" value={sampleQcSummary?.fail ?? 0} status={(sampleQcSummary?.fail ?? 0) > 0 ? "failed" : "success"} />
          <MetricCard title="Rule events" value={bundle.rules.length} status={failedRule ? "failed" : undefined} />
        </section>
        <ErrorPanel diagnosis={diagnosis} />
        {progressError ? <div className="inline-error" role="alert">Current progress unavailable: {progressError}</div> : null}
        <div className="split-grid">
          <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} />
          <section className="panel"><div className="section-heading"><h2>QC summary</h2><p>Sample-level decisions; informational metrics do not lower sample status.</p></div><div className="metric-grid compact">{(["pass", "warn", "fail", "unknown"] as const).map((status) => <MetricCard key={status} title={status} value={sampleQcSummary?.[status] ?? 0} status={status} />)}</div></section>
        </div>
        {detail.pipeline === "wgs" ? <section className="panel">
          <div className="section-heading"><h2>Resource usage</h2><p>{bundle.resources ? (bundle.resources.complete ? "Complete runner telemetry" : "Partial runner telemetry") : "Telemetry is written after the runner starts."}</p></div>
          {resourceError && !bundle.resources ? <p className="empty-state">Resource telemetry is not available yet.</p> : null}
          {bundle.resources ? <>
            <div className="metric-grid compact">
              <MetricCard title="Peak PSS" value={formatBytes(bundle.resources.peak_pss_bytes)} />
              <MetricCard
                title={bundle.resources.source === "docker_container_host_procfs" && bundle.resources.peak_pss_bytes == null ? "RSS process sum" : "Peak RSS"}
                value={formatBytes(bundle.resources.peak_rss_bytes)}
                description={bundle.resources.source === "docker_container_host_procfs" && bundle.resources.peak_pss_bytes == null ? "Upper bound; shared pages may be counted once per process." : undefined}
              />
              <MetricCard title="CPU time" value={formatSecondsDuration(bundle.resources.cpu_seconds)} />
              <MetricCard title="Wall time" value={formatSecondsDuration(bundle.resources.wall_seconds)} />
              <MetricCard title="Read I/O" value={formatBytes(bundle.resources.read_bytes)} />
              <MetricCard title="Write I/O" value={formatBytes(bundle.resources.write_bytes)} />
            </div>
            {bundle.resources.stages?.length ? <div className="table-wrap"><table className="dense-table"><thead><tr><th>Stage</th><th>Wall</th><th>CPU</th><th>Peak PSS</th><th>Read / Write</th></tr></thead><tbody>{bundle.resources.stages.map((stage, index) => <tr key={`${stage.samples_path || "stage"}-${index}`}><td>{stage.samples_path?.split("/").pop()?.replace(".jsonl", "") || `Stage ${index + 1}`}</td><td>{formatSecondsDuration(stage.wall_seconds)}</td><td>{formatSecondsDuration(stage.cpu_seconds)}</td><td>{formatBytes(stage.peak_pss_bytes)}</td><td>{formatBytes(stage.read_bytes)} / {formatBytes(stage.write_bytes)}</td></tr>)}</tbody></table></div> : null}
          </> : null}
        </section> : null}
        <section className="panel">
          <div className="tabs" role="tablist" aria-label="Run detail tabs">{tabs.map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} role="tab" type="button" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
          {activeTab === "Overview" ? <RunOverviewTab detail={detail} samples={bundle.samples} /> : null}
          {activeTab === "Families" ? <WgsFamiliesTab families={bundle.families} /> : null}
          {activeTab === "Rules" ? <RunWorkflowTab progress={bundle.progress} rules={bundle.rules} /> : null}
          {activeTab === "Pods" ? <WgsPodsTab pods={bundle.pods} /> : null}
          {activeTab === "Transfers" ? <WgsTransfersTab transfers={bundle.transfers} /> : null}
          {activeTab === "QC" ? <RunQcTab qc={bundle.qc} runStatus={detail.status} /> : null}
          {activeTab === "Logs" ? <>{logIndexError ? <div className="inline-error" role="alert">Log index unavailable: {logIndexError}</div> : null}<LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} sources={logSources} activeKey={logKey} onKeyChange={handleLogKeyChange} /></> : null}
          {activeTab === "Files" ? <RunFilesTab artifacts={bundle.artifacts} /> : null}
        </section>
      </> : null}
    </div>
  );
}

function WgsFamiliesTab({families}: {families: WgsFamily[]}) {
  return <WgsTable headers={["Family", "Samples", "Status", "Message"]} rows={families.map((family) => [family.family_id, family.sample_count ?? "-", family.status ?? "-", family.message ?? "-"])} empty="No families returned." />;
}

function WgsPodsTab({pods}: {pods: WgsPod[]}) {
  return <WgsTable headers={["Pod", "Phase", "Status", "Node", "Message"]} rows={pods.map((pod) => [pod.name, pod.phase ?? "-", pod.status ?? "-", pod.node_name ?? "-", pod.message ?? "-"])} empty="No pods returned." />;
}

function WgsTransfersTab({transfers}: {transfers: WgsTransfer[]}) {
  return <WgsTable headers={["Transfer", "Source", "Destination", "Status", "Progress"]} rows={transfers.map((transfer) => [transfer.transfer_id ?? "-", transfer.source ?? "-", transfer.destination ?? "-", transfer.status ?? "-", `${transfer.bytes_transferred ?? 0} / ${transfer.bytes_total ?? 0}`])} empty="No transfers returned." />;
}

function WgsTable({headers, rows, empty}: {headers: string[]; rows: Array<Array<string | number>>; empty: string}) {
  return <div className="table-wrap"><table className="data-table"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((value, cell) => <td key={cell}>{value}</td>)}</tr>)}{rows.length === 0 ? <tr><td className="empty-cell" colSpan={headers.length}>{empty}</td></tr> : null}</tbody></table></div>;
}
