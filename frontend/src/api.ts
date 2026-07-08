export type RunSummary = {
  analysis_id: string;
  pipeline: string;
  status: string;
  created_at?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  sample_count?: number | null;
  qc_status?: string | null;
};

export type RunListResponse = {
  items: RunSummary[];
  total: number;
};

export type RunListOptions = {
  pipeline?: string;
  status?: string;
  limit?: number;
  offset?: number;
};

export type RunDetail = {
  analysis_id: string;
  pipeline: string;
  status: string;
  mode?: string | null;
  dag_id?: string | null;
  dag_run_id?: string | null;
  airflow_url?: string | null;
  workdir?: string | null;
  sample_sheet_path?: string | null;
  params?: Record<string, unknown> | null;
  error_summary?: string | null;
  email_to?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
};

export type Sample = {
  sample_id: string;
  family_id?: string | null;
  sample_type?: string | null;
  sex?: string | null;
  fq1?: string | null;
  fq2?: string | null;
  status?: string | null;
  qc_status?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type ScanCandidate = {
  sample_id: string;
  r1: string;
  r2: string;
  source_dir?: string | null;
  r1_size?: number | null;
  r2_size?: number | null;
  r1_mtime?: number | null;
  r2_mtime?: number | null;
  discovery_method?: string | null;
};

export type ScanInputRequest = {
  pipeline: "pgta" | "nipt_docker";
  rawdata_root: string;
  max_samples?: number;
};

export type ScanInputResponse = {
  pipeline: string;
  rawdata_root: string;
  truncated: boolean;
  items: ScanCandidate[];
};

export type InputRootsResponse = {
  pipeline: string;
  roots: string[];
};

export type PgtaTarget = "metadata" | "dryrun_cnv" | "invalid_target" | "baseline_qc";

export type CreatePgtaRunRequest = {
  pipeline: "pgta";
  project_name: string;
  target: PgtaTarget;
  rawdata_root: string;
  selected_samples: ScanCandidate[];
  email_to?: string | null;
  note?: string | null;
};

export type CreateWesRunRequest = {
  pipeline: "wes_qsub";
  project_name: string;
  target: "final_summary";
  email_to?: string | null;
  note?: string | null;
};

export type NiptRunMode = "mount_smoke" | "full_run";

export type CreateNiptDockerRunRequest = {
  pipeline: "nipt_docker";
  project_name: string;
  rawdata_root: string;
  selected_samples: ScanCandidate[];
  run_mode: NiptRunMode;
  cores?: number | null;
  email_to?: string | null;
  note?: string | null;
};

export type CreateRunRequest = CreatePgtaRunRequest | CreateWesRunRequest | CreateNiptDockerRunRequest;

export type ReanalysisRequest = {
  mode: "resume" | "rerun_rule";
  rule?: string | null;
  sample_id?: string | null;
  reason?: string | null;
};

export type ReanalysisResponse = {
  analysis_id: string;
  new_dag_run_id: string;
  mode: string;
  status: string;
};

export type RuleEvent = {
  rule: string;
  sample_id?: string | null;
  status: string;
  snakemake_jobid?: string | null;
  qsub_jobid?: string | null;
  stdout_path?: string | null;
  stderr_path?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  message?: string | null;
  return_code?: number | null;
  wildcards?: Record<string, unknown> | null;
};

export type AirflowTaskProgress = {
  task_id: string;
  state: string;
  start_date?: string | null;
  end_date?: string | null;
  duration?: number | null;
  try_number?: number | null;
  operator?: string | null;
};

export type RunProgressResponse = {
  analysis_id: string;
  pipeline: string;
  status: string;
  dag_id?: string | null;
  dag_run_id?: string | null;
  percent: number;
  current_step: string;
  current_source: string;
  note: string;
  not_in_airflow: boolean;
  progress_source: "airflow_task_instances" | "snakemake_events" | "estimate" | string;
  airflow_tasks: AirflowTaskProgress[];
  rule_events: RuleEvent[];
  updated_at?: string | null;
};

export type QcMetric = {
  sample_id?: string | null;
  metric_name: string;
  metric_value?: string | null;
  metric_numeric?: number | null;
  threshold?: string | null;
  status: string;
  source_file?: string | null;
};

export type RunQc = {
  summary: {
    pass: number;
    warn: number;
    fail: number;
    unknown: number;
  };
  items: QcMetric[];
};

export type LogStream = "metadata" | "stdout" | "stderr";

export type RunLog = {
  path: string;
  stream: LogStream;
  truncated: boolean;
  lines: string[];
};

export type Artifact = {
  key: string;
  type: string;
  label: string;
  path: string;
  size_bytes: number;
  url: string;
};

export type HealthResponse = {
  status: string;
  airflow?: {
    metadatabase?: {status?: string};
    scheduler?: {status?: string};
  };
};

export type IntakeDiscovery = {
  pipeline: string;
  root_path: string;
  batch_id: string;
  fingerprint: string;
  file_count: number;
  total_bytes: number;
  ready_state: string;
  analysis_id?: string | null;
  submit_state: string;
  last_seen_at?: string | null;
};

export type IntakeStatusResponse = {
  items: IntakeDiscovery[];
};

export type IntakeScanPreviewItem = {
  pipeline: string;
  root_path: string;
  batch_id: string;
  source_dir: string;
  fingerprint: string;
  file_count: number;
  total_bytes: number;
  max_mtime?: string | null;
  existing_ready_state?: string | null;
  existing_submit_state?: string | null;
  existing_analysis_id?: string | null;
  would_transition_to: string;
  would_create_run: boolean;
  would_submit: boolean;
  auto_submit_enabled: boolean;
  reason: string;
};

export type IntakeScanPreviewResponse = {
  items: IntakeScanPreviewItem[];
  summary: {
    total_batches: number;
    new_observed: number;
    stable_ready: number;
    bootstrap_protected: number;
    would_create: number;
    would_submit: number;
    blocked_auto_submit: number;
    errors: number;
  };
};

export type IntakeConfigRoot = {
  id: string;
  container_path: string;
};

export type IntakePipelineConfig = {
  enabled: boolean;
  roots: IntakeConfigRoot[];
  file_flavor?: string | null;
  r1_pattern?: string | null;
  r2_pattern?: string | null;
  ignore_patterns?: string[];
  auto_submit?: Record<string, string | number | boolean | null>;
};

export type IntakeConfigResponse = {
  source: string;
  defaults?: {
    ready_rule?: string;
    stable_scans?: number;
    auto_submit?: boolean;
  };
  pipelines: Record<string, IntakePipelineConfig>;
};

export type IntakeScannerStateResponse = {
  dag_id: string;
  airflow_reachable: boolean;
  is_paused: boolean | null;
  latest_dag_run_id?: string | null;
  latest_dag_run_state?: string | null;
  latest_start_date?: string | null;
  latest_end_date?: string | null;
  message?: string | null;
};

export type DashboardPipeline = "all" | "pgta" | "nipt_docker";

export type DashboardOverview = {
  pipeline: DashboardPipeline;
  period: string;
  totals: Record<string, number>;
  status_distribution: Record<string, number>;
  pipeline_breakdown: Record<string, Record<string, number>>;
  trend: Array<{date: string; runs: number; failed: number; success: number}>;
  qc_summary: Record<string, number>;
  failure_summary: Array<{
    analysis_id: string;
    pipeline: string;
    project_name: string;
    status: string;
    error_summary?: string | null;
    created_at?: string | null;
  }>;
  intake_summary: Record<string, number>;
};

export type DashboardRunTrackerRow = {
  analysis_id: string;
  project_name: string;
  pipeline: string;
  status: string;
  qc_status: string;
  sample_count: number;
  created_at?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  dag_id?: string | null;
  dag_run_id?: string | null;
  percent: number;
  current_airflow_task?: string | null;
  current_pipeline_rule?: string | null;
  progress_source: string;
  not_in_airflow: boolean;
  note?: string | null;
};

export type DashboardRunsResponse = {
  items: DashboardRunTrackerRow[];
  total: number;
  limit: number;
  offset: number;
  pipeline: DashboardPipeline;
};

export type SystemResourcesResponse = {
  source: string;
  host: {
    cpu: {cores: number; load_average?: number[]};
    memory: {total_bytes: number; available_bytes: number; used_bytes: number; used_percent: number};
    disks: Array<{path: string; total_bytes: number; used_bytes: number; free_bytes: number; used_percent: number}>;
  };
  containers: Array<{name: string; cpu_percent: string; memory_usage: string; block_io: string}>;
};

declare global {
  interface Window {
    __AIRFLOW_DEMO_CONFIG__?: {
      apiBaseUrl?: string;
      timeZone?: string;
    };
  }
}

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function getApiBaseUrl(): string {
  const configured = window.__AIRFLOW_DEMO_CONFIG__?.apiBaseUrl || import.meta.env.VITE_API_BASE_URL;
  const fallback = `${window.location.protocol}//${window.location.hostname}:8000/api`;
  return String(configured || fallback).replace(/\/+$/, "");
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, init);
  if (!response.ok) {
    let message = response.statusText || "Request failed";
    let code: string | undefined;
    try {
      const payload = await response.json();
      code = payload?.detail?.code;
      message = payload?.detail?.message || message;
    } catch {
      // Keep the HTTP status text when the backend did not return JSON.
    }
    throw new ApiError(message, response.status, code);
  }
  return (await response.json()) as T;
}

export function listRuns(options: RunListOptions = {}): Promise<RunListResponse> {
  const params = new URLSearchParams();
  if (options.pipeline) params.set("pipeline", options.pipeline);
  if (options.status) params.set("status", options.status);
  params.set("limit", String(options.limit ?? 50));
  params.set("offset", String(options.offset ?? 0));
  return requestJson<RunListResponse>(`/runs?${params.toString()}`);
}

export function getDashboardOverview(options: {pipeline?: DashboardPipeline; period?: "24h" | "7d" | "30d"} = {}): Promise<DashboardOverview> {
  const params = new URLSearchParams();
  params.set("pipeline", options.pipeline || "all");
  params.set("period", options.period || "7d");
  return requestJson<DashboardOverview>(`/dashboard/overview?${params.toString()}`);
}

export function getDashboardRuns(options: {
  pipeline?: DashboardPipeline;
  status?: string;
  keyword?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<DashboardRunsResponse> {
  const params = new URLSearchParams();
  params.set("pipeline", options.pipeline || "all");
  if (options.status) params.set("status", options.status);
  if (options.keyword) params.set("keyword", options.keyword);
  params.set("limit", String(options.limit ?? 10));
  params.set("offset", String(options.offset ?? 0));
  return requestJson<DashboardRunsResponse>(`/dashboard/runs?${params.toString()}`);
}

export function getSystemResources(): Promise<SystemResourcesResponse> {
  return requestJson<SystemResourcesResponse>("/system/resources");
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health");
}

export function getDbHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health/db");
}

export function getAirflowHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health/airflow");
}

export function scanInput(payload: ScanInputRequest): Promise<ScanInputResponse> {
  return requestJson<ScanInputResponse>("/input/scan", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function getInputRoots(pipeline: "pgta" | "nipt_docker"): Promise<InputRootsResponse> {
  return requestJson<InputRootsResponse>(`/input/roots?pipeline=${encodeURIComponent(pipeline)}`);
}

export function scanAndSubmitIntake(payload: {pipelines: Array<"pgta" | "nipt_docker">; bootstrap?: boolean; max_samples?: number}): Promise<IntakeStatusResponse> {
  return requestJson<IntakeStatusResponse>("/intake/scan-and-submit", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function previewIntakeScan(payload: {pipelines: Array<"pgta" | "nipt_docker">; bootstrap?: boolean; max_samples?: number}): Promise<IntakeScanPreviewResponse> {
  return requestJson<IntakeScanPreviewResponse>("/intake/scan-preview", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function getIntakeStatus(options: {pipeline?: "pgta" | "nipt_docker"; limit?: number} = {}): Promise<IntakeStatusResponse> {
  const params = new URLSearchParams();
  if (options.pipeline) params.set("pipeline", options.pipeline);
  params.set("limit", String(options.limit ?? 50));
  return requestJson<IntakeStatusResponse>(`/intake/status?${params.toString()}`);
}

export function getIntakeConfig(): Promise<IntakeConfigResponse> {
  return requestJson<IntakeConfigResponse>("/intake/config");
}

export function getIntakeScannerState(): Promise<IntakeScannerStateResponse> {
  return requestJson<IntakeScannerStateResponse>("/intake/scanner-state");
}

export function createRun(payload: CreateRunRequest): Promise<RunDetail> {
  return requestJson<RunDetail>("/runs", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function getRunDetail(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}`);
}

export function getRunSamples(analysisId: string): Promise<{items: Sample[]}> {
  return requestJson<{items: Sample[]}>(`/runs/${encodeURIComponent(analysisId)}/samples`);
}

export function getRunRules(analysisId: string): Promise<{items: RuleEvent[]}> {
  return requestJson<{items: RuleEvent[]}>(`/runs/${encodeURIComponent(analysisId)}/rules`);
}

export function getRunProgress(analysisId: string): Promise<RunProgressResponse> {
  return requestJson<RunProgressResponse>(`/runs/${encodeURIComponent(analysisId)}/progress`);
}

export function getRunQc(analysisId: string): Promise<RunQc> {
  return requestJson<RunQc>(`/runs/${encodeURIComponent(analysisId)}/qc`);
}

export function getRunArtifacts(analysisId: string): Promise<{items: Artifact[]}> {
  return requestJson<{items: Artifact[]}>(`/runs/${encodeURIComponent(analysisId)}/artifacts`);
}

export function getRunLog(analysisId: string, stream: LogStream): Promise<RunLog> {
  return requestJson<RunLog>(`/runs/${encodeURIComponent(analysisId)}/logs?stream=${stream}&tail=200`);
}

export function syncAirflow(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}/actions/sync-airflow`, {
    method: "POST",
  });
}

export function submitRun(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}/actions/submit`, {
    method: "POST",
  });
}

export function reanalyzeRun(analysisId: string, payload: ReanalysisRequest): Promise<ReanalysisResponse> {
  return requestJson<ReanalysisResponse>(`/runs/${encodeURIComponent(analysisId)}/actions/reanalyze`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}
