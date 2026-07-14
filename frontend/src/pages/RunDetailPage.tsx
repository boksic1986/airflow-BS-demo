import {Play, RefreshCw} from "lucide-react";
import {useEffect, useState} from "react";
import {useParams} from "react-router-dom";

import type {Artifact, LogStream, RuleEvent, RunConfig, RunDetail, RunLog, RunLogIndexItem, RunProgressResponse, RunQc, RunResourceSummary, Sample} from "../api";

import {
  getRunArtifacts,
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
  syncAirflow,
} from "../api";
import {ErrorPanel} from "../components/ErrorPanel";
import {LogViewer, preferredLogSource} from "../components/LogViewer";
import {MetricCard} from "../components/MetricCard";
import {StatusBadge} from "../components/StatusBadge";
import {CurrentProgressPanel} from "../features/run-detail/CurrentProgressPanel";
import {RunQcTab} from "../features/run-detail/RunQcTab";
import {RunConfigTab, RunFilesTab, RunOverviewTab, RunSamplesTab} from "../features/run-detail/RunResourceTabs";
import {RunWorkflowTab} from "../features/run-detail/RunWorkflowTab";
import {errorMessage, parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatBytes, formatDate, formatDuration, formatSecondsDuration} from "../lib/format";
import {computeRunProgress, progressFromResponse} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus} from "../lib/status";

const tabs = ["Overview", "Samples", "Workflow", "QC", "Logs", "Files", "Config"] as const;
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
};

const emptyBundle: Bundle = {detail: null, samples: [], rules: [], artifacts: [], qc: null, progress: null, config: null, resources: null};

export function RunDetailPage() {
  const {analysisId = ""} = useParams();
  const [bundle, setBundle] = useState<Bundle>(emptyBundle);
  const [log, setLog] = useState<RunLog | null>(null);
  const [logStream, setLogStream] = useState<LogStream>("metadata");
  const [logSources, setLogSources] = useState<RunLogIndexItem[]>([]);
  const [logKey, setLogKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logError, setLogError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [lastAutoSyncedAt, setLastAutoSyncedAt] = useState<string | null>(null);

  async function loadDetail() {
    if (!analysisId) return;
    setLoading(true);
    setError(null);
    setResourceError(null);
    try {
      const [detail, samples, rules, progress, artifacts, qc, config, indexedLogs, resources] = await Promise.all([
        getRunDetail(analysisId),
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunProgress(analysisId).catch(() => null),
        getRunArtifacts(analysisId),
        getRunQc(analysisId),
        getRunConfig(analysisId).catch(() => null),
        getRunLogIndex(analysisId).catch(() => ({items: []})),
        getRunResources(analysisId).catch((resourceLoadError) => {
          setResourceError(errorMessage(resourceLoadError));
          return null;
        }),
      ]);
      setBundle({detail, samples: samples.items, rules: progress?.rule_events || rules.items, progress, artifacts: artifacts.items, qc, config, resources});
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

  useEffect(() => { void loadDetail(); }, [analysisId]);
  useEffect(() => { void loadLog(logStream, logKey); }, [analysisId, logKey, logStream]);

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
    const interval = window.setInterval(() => void refreshFromAirflow(), 15000);
    return () => { stopped = true; window.clearInterval(interval); };
  }, [analysisId, detail?.dag_run_id, detail?.status]);

  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(detail?.error_summary, failedRule?.rule);
  const progress = detail && bundle.progress
    ? progressFromResponse(bundle.progress)
    : detail
      ? computeRunProgress({analysis_id: detail.analysis_id, pipeline: detail.pipeline, status: detail.status, created_at: detail.created_at, started_at: detail.started_at, ended_at: detail.ended_at, sample_count: bundle.samples.length}, detail, bundle.rules)
      : null;
  const canSubmit = detail?.status === "created" && ["pgta", "nipt_docker", "wgs"].includes(detail.pipeline);
  async function runAction(action: "sync" | "submit") {
    if (!analysisId) return;
    setActing(true);
    setActionError(null);
    try {
      if (action === "sync") await syncAirflow(analysisId);
      if (action === "submit") await submitRun(analysisId);
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
        <div className="split-grid">
          <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} />
          <section className="panel"><div className="section-heading"><h2>QC summary</h2><p>Sample-level decisions; informational metrics do not lower sample status.</p></div><div className="metric-grid compact">{(["pass", "warn", "fail", "unknown"] as const).map((status) => <MetricCard key={status} title={status} value={sampleQcSummary?.[status] ?? 0} status={status} />)}</div></section>
        </div>
        {detail.pipeline === "wgs" || detail.pipeline === "nipt_docker" ? <section className="panel">
          <div className="section-heading"><h2>Resource usage</h2><p>{bundle.resources ? (bundle.resources.complete ? "Complete runner telemetry" : "Partial runner telemetry") : "Telemetry is written after the runner starts."}</p></div>
          {resourceError && !bundle.resources ? <p className="empty-state">Resource telemetry is not available yet.</p> : null}
          {bundle.resources ? <>
            <div className="metric-grid compact">
              <MetricCard title="Peak PSS" value={formatBytes(bundle.resources.peak_pss_bytes)} />
              <MetricCard title="Peak RSS" value={formatBytes(bundle.resources.peak_rss_bytes)} />
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
          {activeTab === "Samples" ? <RunSamplesTab samples={bundle.samples} /> : null}
          {activeTab === "Workflow" ? <RunWorkflowTab progress={bundle.progress} rules={bundle.rules} /> : null}
          {activeTab === "QC" ? <RunQcTab qc={bundle.qc} runStatus={detail.status} /> : null}
          {activeTab === "Logs" ? <LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} sources={logSources} activeKey={logKey} onKeyChange={handleLogKeyChange} /> : null}
          {activeTab === "Files" ? <RunFilesTab artifacts={bundle.artifacts} /> : null}
          {activeTab === "Config" ? <RunConfigTab artifacts={bundle.artifacts} config={bundle.config} detail={detail} /> : null}
        </section>
      </> : null}
    </div>
  );
}
