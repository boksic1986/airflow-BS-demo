import {useEffect, useState} from "react";
import {Link} from "react-router-dom";

import type {
  DashboardOverview,
  DashboardPipeline,
  DashboardRunsResponse,
  IntakeDiscovery,
  IntakeScannerStateResponse,
  PlatformResourcesResponse,
} from "../api";
import type {RunTrackerFilter} from "../components/RunTracker";

import {
  getDashboardOverview,
  getDashboardRuns,
  getIntakeScannerState,
  getIntakeStatus,
  getPlatformResources,
  submitRun,
} from "../api";
import {RunTracker} from "../components/RunTracker";
import {
  OperationsOverview,
  PipelineRail,
} from "../features/dashboard/DashboardOverview";
import {DashboardResourcePanels} from "../features/dashboard/DashboardResourcePanels";
import {IntakeScannerPanel} from "../features/dashboard/IntakeScannerPanel";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {hasRegisteredSubmissionUi} from "../features/platform/submissionUiRegistry";
import {errorMessage} from "../lib/errors";
import {useSilentRefresh} from "../lib/useSilentRefresh";

const trackerLimit = 10;
const intakeLimit = 10;

export function DashboardPage() {
  const capabilities = usePlatformCapabilities();
  const [pipeline, setPipeline] = useState<DashboardPipeline>("all");
  const [period, setPeriod] = useState<"24h" | "7d" | "30d">("7d");
  const [trackerFilter, setTrackerFilter] = useState<RunTrackerFilter>("all");
  const [trackerKeyword, setTrackerKeyword] = useState("");
  const [trackerOffset, setTrackerOffset] = useState(0);
  const [intakeOffset, setIntakeOffset] = useState(0);
  const [intakeTotal, setIntakeTotal] = useState(0);
  const [resourceTab, setResourceTab] = useState<DashboardPipeline>("all");

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [trackerPayload, setTrackerPayload] = useState<DashboardRunsResponse | null>(null);
  const [resources, setResources] = useState<PlatformResourcesResponse | null>(null);
  const [intakeItems, setIntakeItems] = useState<IntakeDiscovery[]>([]);
  const [intakeScanner, setIntakeScanner] = useState<IntakeScannerStateResponse | null>(null);
  const [submitError, setTrackerError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const deployedDefinitions = capabilities.pipelines.filter((item) => capabilities.isDeployed(item.id));
  const selectedPipeline = deployedDefinitions.find((item) => item.id === pipeline) || deployedDefinitions[0];
  const showIntake = pipeline === "all"
    ? deployedDefinitions.some((item) => item.capabilities.includes("intake"))
    : Boolean(selectedPipeline?.capabilities.includes("intake"));
  const deployedPipeline = pipeline === "all" ? "deployed" : pipeline;
  const onlyDeployedPipeline = capabilities.deployed_pipelines.length === 1
    ? capabilities.deployed_pipelines[0]
    : null;
  const dashboardReady = !capabilities.loading
    && (!onlyDeployedPipeline || pipeline === onlyDeployedPipeline);

  const {refresh: loadOverview, loading: overviewLoading, error: overviewError} = useSilentRefresh(async ({isCurrent}) => {
    const result = await getDashboardOverview({pipeline: deployedPipeline, period});
    if (isCurrent()) setOverview(result);
  }, JSON.stringify([deployedPipeline, period]), dashboardReady);

  const {refresh: loadTracker, loading: trackerLoading, error: trackerRefreshError} = useSilentRefresh(async ({isCurrent}) => {
      const result = await getDashboardRuns({
        pipeline: deployedPipeline,
        status: trackerStatusParam(trackerFilter),
        keyword: trackerKeyword.trim() || undefined,
        limit: trackerLimit,
        offset: trackerOffset,
      });
      if (isCurrent()) setTrackerPayload(result);
  }, JSON.stringify([deployedPipeline, trackerFilter, trackerKeyword, trackerOffset]), dashboardReady);
  const trackerError = submitError || trackerRefreshError;

  const {refresh: loadIntake, loading: intakeLoading, error: intakeError} = useSilentRefresh(async ({isCurrent}) => {
    if (!showIntake) {
      setIntakeItems([]);
      setIntakeTotal(0);
      setIntakeScanner(null);
      return;
    }
      const [payloadResult, scannerResult] = await Promise.allSettled([
        getIntakeStatus({
          pipeline: deployedPipeline,
          keyword: trackerKeyword.trim() || undefined,
          lifecycle: "all",
          view: "attention",
          limit: intakeLimit,
          offset: intakeOffset,
        }),
        getIntakeScannerState(),
      ]);
      if (!isCurrent()) return;
      if (payloadResult.status === "fulfilled") {
        setIntakeItems(payloadResult.value.items);
        setIntakeTotal(payloadResult.value.total ?? payloadResult.value.items.length);
      }
      if (scannerResult.status === "fulfilled") setIntakeScanner(scannerResult.value);
      const failure = payloadResult.status === "rejected"
        ? payloadResult.reason
        : scannerResult.status === "rejected"
          ? scannerResult.reason
          : null;
      if (failure) throw failure;
  }, JSON.stringify([deployedPipeline, intakeOffset, showIntake, trackerKeyword]), dashboardReady);

  const {loading: resourcesLoading, error: resourcesError} = useSilentRefresh(async ({isCurrent}) => {
    const result = await getPlatformResources();
    if (isCurrent()) setResources(result);
  }, 'resources', dashboardReady);
  useEffect(() => {
    if (capabilities.deployed_pipelines.length === 1) {
      const onlyPipeline = capabilities.deployed_pipelines[0]!;
      setPipeline(onlyPipeline);
      setResourceTab(onlyPipeline);
    }
  }, [capabilities.deployed_pipelines]);


  function handlePipelineChange(nextPipeline: DashboardPipeline) {
    setPipeline(nextPipeline);
    setResourceTab(nextPipeline);
    setTrackerFilter("all");
    setTrackerOffset(0);
    setIntakeOffset(0);
  }

  function handleFilterChange(nextFilter: RunTrackerFilter) {
    setTrackerFilter(nextFilter);
    setTrackerOffset(0);
  }

  function handleKeywordChange(nextKeyword: string) {
    setTrackerKeyword(nextKeyword);
    setTrackerOffset(0);
    setIntakeOffset(0);
  }

  async function handleTrackerSubmit(analysisId: string) {
    setActionMessage(null);
    setTrackerError(null);
    try {
      const submitted = await submitRun(analysisId);
      setActionMessage(`Submitted ${analysisId} to Airflow${submitted.dag_run_id ? ` as ${submitted.dag_run_id}` : ""}.`);
      await Promise.all([loadOverview(), loadTracker(), loadIntake()]);
    } catch (submitError) {
      setTrackerError(errorMessage(submitError));
    }
  }


  const showQc = pipeline === "all"
    ? deployedDefinitions.some((item) => item.capabilities.includes("qc"))
    : Boolean(selectedPipeline?.capabilities.includes("qc"));
  const pipelineOptions: DashboardPipeline[] = capabilities.deployed_pipelines.length === 1
    ? [...capabilities.deployed_pipelines]
    : ["all", ...capabilities.deployed_pipelines];
  const trackerRows = trackerPayload?.items || [];
  const canSubmit = deployedDefinitions.some((item) => (
    hasRegisteredSubmissionUi(item, capabilities.isDeployed)
  ));

  return (
    <div className="page-stack dashboard-page">
      <section className="page-header control-tower-header">
        <div>
          <p className="eyebrow">Bioinformatics production control tower</p>
          <h1>Command Center</h1>
          <p>Deployed workflow operations, sample throughput, intake readiness, and node health.</p>
        </div>
        {canSubmit ? <Link className="button primary" to="/submit">Submit run</Link> : null}
      </section>

      {actionMessage ? <div className="success-note" role="status">{actionMessage}</div> : null}

      <section className="dashboard-command-grid">
        <PipelineRail pipeline={pipeline} pipelines={deployedDefinitions} onChange={handlePipelineChange} />
        <div className="dashboard-main-column">
          {overviewError ? <div className="inline-error" role="alert">Overview unavailable: {overviewError}</div> : null}
          {overviewLoading && !overview ? <p className="muted panel-loading">Loading overview...</p> : null}
          <OperationsOverview overview={overview} period={period} loading={overviewLoading} onPeriodChange={setPeriod} showQc={showQc} />
          <div className="dashboard-tracker-region" aria-busy={trackerLoading}>
            {trackerError ? <div className="inline-error" role="alert">Run tracker unavailable: {trackerError}</div> : null}
            {trackerLoading && !trackerPayload ? <p className="muted panel-loading">Loading run tracker...</p> : null}
            <RunTracker
              filter={trackerFilter}
              keyword={trackerKeyword}
              limit={trackerPayload?.limit || trackerLimit}
              offset={trackerPayload?.offset || trackerOffset}
              rows={trackerRows}
              total={trackerPayload?.total || 0}
              onFilterChange={handleFilterChange}
              onKeywordChange={handleKeywordChange}
              onPageChange={setTrackerOffset}
              onSubmit={(analysisId) => void handleTrackerSubmit(analysisId)}
            />
          </div>
          {showIntake ? <IntakeScannerPanel
              scanner={intakeScanner}
              items={intakeItems}
              total={intakeTotal}
              limit={intakeLimit}
              offset={intakeOffset}
              loading={intakeLoading}
              error={intakeError}
              onPageChange={setIntakeOffset}
            /> : null}
          <DashboardResourcePanels
            resources={resources}
            resourceTab={resourceTab}
            overview={overview}
            rows={trackerRows}
            loading={resourcesLoading}
            error={resourcesError}
            pipelines={pipelineOptions}
            onResourceTabChange={setResourceTab}
          />
        </div>
      </section>
      <span className="sr-only">Selected pipeline: {selectedPipeline?.display_name || "All pipelines"}</span>
    </div>
  );
}

function trackerStatusParam(filter: RunTrackerFilter): string | undefined {
  if (filter === "all") return undefined;
  if (filter === "active") return "active";
  return filter;
}
