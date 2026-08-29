import {useCallback, useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {
  DashboardOverview,
  DashboardPipeline,
  DashboardRunsResponse,
  IntakeDiscovery,
  IntakeScannerStateResponse,
  SystemResourcesResponse,
} from "../api";
import type {RunTrackerFilter} from "../components/RunTracker";

import {
  getDashboardOverview,
  getDashboardRuns,
  getIntakeScannerState,
  getIntakeStatus,
  getSystemResources,
  submitRun,
  syncAirflow,
} from "../api";
import {RunTracker} from "../components/RunTracker";
import {
  CommandSummary,
  dashboardPipelines,
  OperationsOverview,
  PipelineRail,
} from "../features/dashboard/DashboardOverview";
import {DashboardResourcePanels} from "../features/dashboard/DashboardResourcePanels";
import {IntakeScannerPanel} from "../features/dashboard/IntakeScannerPanel";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";
import {isActiveStatus} from "../lib/status";

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
  const [intakeView, setIntakeView] = useState<"pending" | "history">("pending");
  const [intakeTotal, setIntakeTotal] = useState(0);
  const [resourceTab, setResourceTab] = useState<DashboardPipeline>("all");

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [trackerPayload, setTrackerPayload] = useState<DashboardRunsResponse | null>(null);
  const [resources, setResources] = useState<SystemResourcesResponse | null>(null);
  const [intakeItems, setIntakeItems] = useState<IntakeDiscovery[]>([]);
  const [intakeScanner, setIntakeScanner] = useState<IntakeScannerStateResponse | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [trackerLoading, setTrackerLoading] = useState(true);
  const [intakeLoading, setIntakeLoading] = useState(true);
  const [resourcesLoading, setResourcesLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [trackerError, setTrackerError] = useState<string | null>(null);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [resourcesError, setResourcesError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const deployedPipeline = pipeline === "all" ? "deployed" : pipeline;

  const loadOverview = useCallback(async (showSpinner = true) => {
    if (showSpinner) setOverviewLoading(true);
    setOverviewError(null);
    try {
      setOverview(await getDashboardOverview({pipeline: deployedPipeline, period}));
    } catch (loadError) {
      setOverviewError(errorMessage(loadError));
    } finally {
      if (showSpinner) setOverviewLoading(false);
    }
  }, [deployedPipeline, period]);

  const loadTracker = useCallback(async (showSpinner = true) => {
    if (showSpinner) setTrackerLoading(true);
    setTrackerError(null);
    try {
      setTrackerPayload(await getDashboardRuns({
        pipeline: deployedPipeline,
        status: trackerStatusParam(trackerFilter),
        keyword: trackerKeyword.trim() || undefined,
        limit: trackerLimit,
        offset: trackerOffset,
      }));
    } catch (loadError) {
      setTrackerError(errorMessage(loadError));
    } finally {
      if (showSpinner) setTrackerLoading(false);
    }
  }, [deployedPipeline, trackerFilter, trackerKeyword, trackerOffset]);

  const loadIntake = useCallback(async (showSpinner = true) => {
    if (showSpinner) setIntakeLoading(true);
    setIntakeError(null);
    try {
      const [payload, scanner] = await Promise.all([
        getIntakeStatus({
          pipeline: deployedPipeline,
          keyword: trackerKeyword.trim() || undefined,
          lifecycle: "all",
          view: intakeView,
          limit: intakeLimit,
          offset: intakeOffset,
        }),
        getIntakeScannerState(),
      ]);
      setIntakeItems(payload.items);
      setIntakeTotal(payload.total ?? payload.items.length);
      setIntakeScanner(scanner);
    } catch (loadError) {
      setIntakeError(errorMessage(loadError));
    } finally {
      if (showSpinner) setIntakeLoading(false);
    }
  }, [intakeOffset, intakeView, pipeline, trackerKeyword]);

  const loadResources = useCallback(async () => {
    setResourcesLoading(true);
    setResourcesError(null);
    try {
      setResources(await getSystemResources());
    } catch (loadError) {
      setResourcesError(errorMessage(loadError));
    } finally {
      setResourcesLoading(false);
    }
  }, []);

  useEffect(() => { void loadOverview(); }, [loadOverview]);
  useEffect(() => { void loadTracker(); }, [loadTracker]);
  useEffect(() => { void loadIntake(); }, [loadIntake]);
  useEffect(() => { void loadResources(); }, [loadResources]);
  useEffect(() => {
    if (capabilities.deployed_pipelines.length === 1) {
      const onlyPipeline = capabilities.deployed_pipelines[0]!;
      setPipeline(onlyPipeline);
      setResourceTab(onlyPipeline);
    }
  }, [capabilities.deployed_pipelines]);

  const activeRunIds = useMemo(
    () => [...new Set((trackerPayload?.items || []).filter((row) => isActiveStatus(row.status)).map((row) => row.analysis_id))],
    [trackerPayload],
  );
  const activeRunKey = activeRunIds.join("|");

  useEffect(() => {
    if (!activeRunKey) return undefined;
    const ids = activeRunKey.split("|");
    let disposed = false;
    async function syncActiveRuns() {
      await Promise.all(ids.map((analysisId) => syncAirflow(analysisId).catch(() => null)));
      if (!disposed) await Promise.all([loadOverview(false), loadTracker(false), loadIntake(false)]);
    }
    void syncActiveRuns();
    const timer = window.setInterval(() => { void syncActiveRuns(); }, 15000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [activeRunKey, loadIntake, loadOverview, loadTracker]);

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
      await Promise.all([loadOverview(false), loadTracker(false), loadIntake(false)]);
    } catch (submitError) {
      setTrackerError(errorMessage(submitError));
    }
  }

  async function handleTrackerSync(analysisId: string) {
    setActionMessage(null);
    setTrackerError(null);
    try {
      await syncAirflow(analysisId);
      setActionMessage(`Synced ${analysisId} from Airflow.`);
      await Promise.all([loadOverview(false), loadTracker(false), loadIntake(false)]);
    } catch (syncError) {
      setTrackerError(errorMessage(syncError));
    }
  }

  const selectedPipeline = dashboardPipelines.find((item) => item.value === pipeline) || dashboardPipelines[0];
  const pipelineOptions: DashboardPipeline[] = capabilities.deployed_pipelines.length === 1
    ? [...capabilities.deployed_pipelines]
    : ["all", ...capabilities.deployed_pipelines];
  const trackerRows = trackerPayload?.items || [];

  return (
    <div className="page-stack dashboard-page">
      <section className="page-header control-tower-header">
        <div>
          <p className="eyebrow">Bioinformatics production control tower</p>
          <h1>Command Center</h1>
          <p>Deployed workflow operations, sample throughput, intake readiness, and node health.</p>
        </div>
        <Link className="button primary" to="/submit">Submit run</Link>
      </section>

      {actionMessage ? <div className="success-note" role="status">{actionMessage}</div> : null}

      <section className="dashboard-command-grid">
        <PipelineRail pipeline={pipeline} pipelines={pipelineOptions} onChange={handlePipelineChange} />
        <div className="dashboard-main-column">
          <CommandSummary overview={overview} pipeline={pipeline} loading={overviewLoading} error={overviewError} />
          <OperationsOverview overview={overview} period={period} loading={overviewLoading} onPeriodChange={setPeriod} />
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
              onSync={(analysisId) => void handleTrackerSync(analysisId)}
            />
          </div>
          <IntakeScannerPanel
            scanner={intakeScanner}
            items={intakeItems}
            total={intakeTotal}
            limit={intakeLimit}
            offset={intakeOffset}
            loading={intakeLoading}
            error={intakeError}
            view={intakeView}
            onViewChange={(nextView) => { setIntakeView(nextView); setIntakeOffset(0); }}
            onPageChange={setIntakeOffset}
          />
        </div>
      </section>
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
      <span className="sr-only">Selected pipeline: {selectedPipeline.label}</span>
    </div>
  );
}

function trackerStatusParam(filter: RunTrackerFilter): string | undefined {
  if (filter === "all") return undefined;
  if (filter === "active") return "active";
  return filter;
}
