export type RunSummary = {
  analysis_id: string;
  project_name?: string | null;
  pipeline: string;
  status: string;
  created_at?: string | null;
  submitted_at?: string | null;
  submitted_by?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  pipeline_finished_at?: string | null;
  sample_count?: number | null;
  qc_status?: string | null;
  qc_highlights?: QcHighlight[];
  workflow_summary?: WorkflowStageSummary[];
};

export type WorkflowStageSummary = {
  key: string;
  label: string;
  status: string;
  completed_jobs: number;
  total_jobs: number;
  dry_run?: boolean;
};

export type RunListResponse = {
  items: RunSummary[];
  total: number;
};

export type RunListOptions = {
  pipeline?: string;
  status?: string;
  keyword?: string;
  sort?: "created_desc" | "duration_desc" | "status";
  limit?: number;
  offset?: number;
};

export type OperatorSample = {
  analysis_id: string;
  project_name: string;
  pipeline: string;
  sample_id: string;
  family_id?: string | null;
  status: string;
  qc_status: string;
  source_folder?: string | null;
  r1_name?: string | null;
  r2_name?: string | null;
  report_status: string;
};

export type OperatorSampleResponse = {
  items: OperatorSample[];
  total: number;
  limit: number;
  offset: number;
};

export type FailureItem = {
  analysis_id: string;
  project_name: string;
  pipeline: string;
  workflow_status: string;
  qc_status: string;
  failure_kind: "workflow" | "qc";
  failure_layer: "airflow" | "runner" | "pipeline_rule" | "qc" | "unknown";
  failed_step: string;
  failed_step_label: string;
  sample_id?: string | null;
  return_code?: number | null;
  stderr_excerpt: string;
  possible_reason: string;
  suggested_action_code: string;
  can_resume: boolean;
  can_rerun_stage: boolean;
  created_at?: string | null;
};

export type FailureListResponse = {
  items: FailureItem[];
  total: number;
  limit: number;
  offset: number;
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
  submitted_at?: string | null;
  pipeline_finished_at?: string | null;
  submitted_by?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  pipeline_release_id?: string | null;
  wgs_version?: string | null;
  wgs_source_commit?: string | null;
  resolved_runtime?: {
    cce_pipeline_version?: string | null;
    cce_pipeline_source_commit?: string | null;
    profile_id?: string | null;
    profile_revision?: string | null;
    profile_sha256?: string | null;
    master_image_digest?: string | null;
    pipeline_build_sha256?: string | null;
    resource_manifest_sha256?: string | null;
  } | null;
  rule_event_schema_version?: string | null;
  observer?: {
    status: string;
    last_success_at?: string | null;
    last_error?: string | null;
    updated_at?: string | null;
  } | null;
};

export type UserRole = "viewer" | "operator" | "admin";

export type SessionUser = {
  username: string;
  role: UserRole;
  csrf_token?: string;
  display_name?: string | null;
};

export type LoginRequest = {username: string; password: string};

export type WgsRelease = {
  release_id: string;
  version: string;
  source_commit: string;
  execution_enabled: boolean;
  runtime_adapter_enabled: boolean;
};

export type WgsFamily = {
  family_id: string;
  status?: string | null;
  sample_count?: number | null;
  message?: string | null;
};

export type WgsPod = {
  attempt: number;
  pod_hash: string;
  job_name?: string | null;
  phase?: string | null;
  reason?: string | null;
  exit_code?: number | null;
  image_id?: string | null;
  node_name?: string | null;
  message?: string | null;
  resources?: Record<string, unknown> | null;
  observed_at?: string | null;
  updated_at?: string | null;
};

export type WgsTransfer = {
  transfer_id?: string | null;
  source?: string | null;
  destination?: string | null;
  status?: string | null;
  progress_detail_available?: boolean;
  bytes_total?: number | null;
  bytes_transferred?: number | null;
  progress_percent?: number | null;
  speed_bps?: number | null;
  eta_seconds?: number | null;
  estimated_finish_at?: string | null;
  files_total?: number | null;
  files_completed?: number | null;
  current_file?: string | null;
  checkpoint_ref?: string | null;
  heartbeat_at?: string | null;
  verification_status?: string | null;
  message?: string | null;
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

export type PgtaTarget = "predict" | "metadata" | "dryrun_cnv" | "invalid_target" | "baseline_qc";

export type RuntimeProfileSummary = {
  id: string;
  label: string;
  pipeline_version: string;
  config_version: string;
};

export type PipelineConfigTemplate = {
  pipeline: "pgta" | "nipt_docker";
  profile: RuntimeProfileSummary;
  profiles: RuntimeProfileSummary[];
  config_template_hash: string;
  editable_yaml: string;
  changed_paths: string[];
};

export type PipelineConfigValidation = {
  valid: boolean;
  profile: RuntimeProfileSummary;
  config_template_hash: string;
  normalized_yaml: string;
  changed_paths: string[];
  warnings: string[];
  errors: string[];
};

export type RunConfig = {
  analysis_id: string;
  pipeline: string;
  state: "waiting_for_prepare" | "resolved" | "legacy" | string;
  profile?: RuntimeProfileSummary | null;
  config_template_hash?: string | null;
  config_requested_hash?: string | null;
  resolved_config_hash?: string | null;
  changed_paths: string[];
  requested_yaml?: string | null;
  resolved_yaml?: string | null;
};

type PipelineConfigSelection = {
  runtime_profile_id: string;
  config_template_hash: string;
  snakemake_config_yaml: string;
};

export type CreatePgtaRunRequest = PipelineConfigSelection & {
  pipeline: "pgta";
  project_name: string;
  target: PgtaTarget;
  rawdata_root: string;
  selected_samples: ScanCandidate[];
  submitted_by?: string | null;
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

export type CreateNiptDockerRunRequest = PipelineConfigSelection & {
  pipeline: "nipt_docker";
  project_name: string;
  rawdata_root: string;
  selected_samples: ScanCandidate[];
  submitted_by?: string | null;
  run_mode: NiptRunMode;
  cores?: number | null;
  email_to?: string | null;
  note?: string | null;
};

export type CreateWgsRunRequest = {
  pipeline: "wgs";
  project_name: string;
  batch_no: string;
  fq_path: string;
  execution_mode?: "cce";
  submitted_by?: string | null;
  note?: string | null;
};

export type CreateRunRequest = CreatePgtaRunRequest | CreateWesRunRequest | CreateNiptDockerRunRequest | CreateWgsRunRequest;

export type ReanalysisRequest = {
  mode: "resume" | "rerun_rule" | "rerun_stage";
  rule?: string | null;
  sample_id?: string | null;
  stage?: "mapping" | "metadata" | "baseline_qc" | null;
  reason?: string | null;
};

export type ReanalysisResponse = {
  analysis_id: string;
  new_dag_run_id: string;
  mode: string;
  stage?: string | null;
  status: string;
};

export type RuleEvent = {
  rule: string;
  phase?: string;
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
  layer?: number | null;
  elapsed_seconds?: number | null;
  historical_median_seconds?: number | null;
  estimated_remaining_seconds?: number | null;
  eta_history_count?: number;
  eta_model?: string | null;
};

export type WgsValidationIssue = {
  id: number; code: string; severity: string; scope_type?: string | null;
  sample_id?: string | null; family_id?: string | null; file_path?: string | null;
  message: string; status: string; created_at: string; resolved_at?: string | null;
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
  current_phase?: string | null;
  current_rule?: string | null;
  current_sample?: string | null;
  rule_counts?: {total: number; running: number; success: number; failed: number; terminal: number};
  updated_at?: string | null;
  current_airflow_stage?: string | null;
  overall_progress_percent?: number | null;
  analysis_eta_seconds?: number | null;
  analysis_eta_model?: string | null;
  analysis_eta_history_count?: number;
};

export type QcMetric = {
  sample_id?: string | null;
  metric_name: string;
  metric_value?: string | null;
  metric_numeric?: number | null;
  threshold?: string | null;
  status: string;
  decision_metric?: boolean;
  source_file?: string | null;
};

export type RunQc = {
  summary: {
    pass: number;
    warn: number;
    fail: number;
    unknown: number;
  };
  sample_summary?: {
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

export type RunLogIndexItem = {
  key: string;
  label: string;
  stream: string;
  relative_path: string;
  rule?: string | null;
  sample_id?: string | null;
  status?: string | null;
};

export type QcHighlight = {
  key: string;
  value: number | string | null;
  unit: string;
  status: string;
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
  stable_observation_count?: number;
  last_seen_at?: string | null;
  state_changed_at?: string | null;
  archived_at?: string | null;
  archive_reason?: string | null;
  archive_path?: string | null;
  last_error?: string | null;
  project_name?: string | null;
  submitted_by?: string | null;
  run_source?: "intake" | null;
  source_batch_id?: string | null;
  analysis_status?: string | null;
  display_status?: string | null;
  sample_count?: number;
  progress_percent?: number;
  current_stage?: string | null;
  submitted_at?: string | null;
  pipeline_finished_at?: string | null;
  elapsed_seconds?: number | null;
  average_duration_seconds?: number | null;
  eta_history_count?: number;
  eta_model?: string | null;
  estimated_remaining_seconds?: number | null;
  estimated_finish_at?: string | null;
};

export type IntakeStatusResponse = {
  items: IntakeDiscovery[];
  total?: number;
  limit?: number;
  offset?: number;
};

export type IntakeDiscoveryState = "bootstrap" | "observed" | "ready" | "submitted" | "error" | "disabled";
export type IntakeLifecycle = "active" | "archived" | "all";

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
  intake?: {
    mode?: string | null;
    inbox_root?: string | null;
    data_root?: string | null;
    manifest_glob?: string | null;
    ready_suffix?: string | null;
    stable_scans?: number | null;
    request_inbox?: string | null;
    request_glob?: string | null;
    request_submit_enabled?: boolean | null;
  };
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
  schedule?: string;
  next_run?: string | null;
  trigger_contracts?: Record<string, string>;
  retention?: {enabled: boolean; days: number; scope: string};
  message?: string | null;
};

export type IntakeView = "pending" | "history" | "all";

export type DashboardPipeline = "all" | "deployed" | "pgta" | "nipt_docker" | "wgs";

export type DeployedPipeline = "pgta" | "nipt_docker" | "wgs";

export type PlatformCapabilities = {
  environment: string;
  deployed_pipelines: DeployedPipeline[];
  airflow_url: string | null;
};

export type DashboardOverview = {
  pipeline: DashboardPipeline;
  period: string;
  totals: Record<string, number>;
  status_distribution: Record<string, number>;
  pipeline_breakdown: Record<string, Record<string, number>>;
  trend: Array<{date: string; runs: number; failed: number; success: number}>;
  qc_summary: Record<string, number>;
  sample_summary?: {
    total: number;
    running: number;
    workflow_failed: number;
    qc_failed: number;
    completed: number;
  };
  sample_trend?: Array<{
    date: string;
    total: number;
    running: number;
    workflow_failed: number;
    qc_failed: number;
    completed: number;
  }>;
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
  display_status?: string;
  qc_status: string;
  qc_display_status?: "pass" | "warn" | "fail" | "pending" | "unavailable" | "unknown" | string;
  qc_display_note?: string | null;
  run_source?: "manual" | "intake";
  source_batch_id?: string | null;
  sample_count: number;
  created_at?: string | null;
  submitted_at?: string | null;
  submitted_by?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  pipeline_finished_at?: string | null;
  dag_id?: string | null;
  dag_run_id?: string | null;
  percent: number;
  current_airflow_task?: string | null;
  current_pipeline_rule?: string | null;
  current_stage_label?: string | null;
  current_stage_source?: string | null;
  elapsed_seconds?: number | null;
  average_duration_seconds?: number | null;
  eta_history_count?: number;
  eta_model?: string | null;
  estimated_remaining_seconds?: number | null;
  estimated_finish_at?: string | null;
  progress_source: string;
  not_in_airflow: boolean;
  note?: string | null;
  qc_highlights?: QcHighlight[];
};

export type WorkflowCatalogItem = {
  pipeline: "pgta" | "nipt_docker" | "wgs";
  name: string;
  dag_id: string;
  runtime_profile_id: string;
  runtime: string;
  stages: WorkflowStageSummary[];
  latest_run?: {
    analysis_id: string;
    project_name: string;
    status: string;
    current_stage?: string | null;
    submitted_at?: string | null;
    finished_at?: string | null;
  } | null;
  run_count: number;
  success_rate?: number | null;
};

export type WorkflowCatalogResponse = {items: WorkflowCatalogItem[]};

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

export type RunResourceSummary = {
  analysis_id: string;
  pipeline: string;
  wall_seconds: number;
  peak_pss_bytes?: number | null;
  peak_rss_bytes: number;
  read_bytes: number;
  write_bytes: number;
  cpu_seconds: number;
  sample_count: number;
  complete: boolean;
  source?: string;
  summary_artifact?: string;
  raw_samples_paths?: string[];
  stages?: Array<{
    wall_seconds: number;
    peak_pss_bytes?: number | null;
    peak_rss_bytes: number;
    read_bytes: number;
    write_bytes: number;
    cpu_seconds: number;
    sample_count: number;
    complete: boolean;
    source?: string;
    samples_path?: string;
  }>;
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
  const fallback = import.meta.env.MODE === "test" ? "http://localhost:8000/api" : "/api";
  return String(configured || fallback).replace(/\/+$/, "");
}

let csrfToken = "";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const method = String(init?.method || "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (!{"GET": true, "HEAD": true, "OPTIONS": true}[method] && csrfToken && path !== "/auth/login") {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(`${getApiBaseUrl()}${path}`, {...init, headers, credentials: "same-origin"});
  const body = await response.text();
  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  const looksHtml = contentType.includes("text/html") || /^\s*<!doctype html|^\s*<html/i.test(body);
  const looksJson = contentType.includes("json") || /^\s*[\[{]/.test(body);
  const statusLabel = `${response.status}${response.statusText ? ` ${response.statusText}` : ""}`;

  if (!response.ok) {
    if (looksHtml) {
      throw new ApiError(
        `Request failed: ${statusLabel}. The API gateway returned HTML for ${method} ${path}; check the nginx /api proxy and client allowlist.`,
        response.status,
        "NON_JSON_API_ERROR",
      );
    }
    if (looksJson && body.trim()) {
      try {
        const payload = JSON.parse(body) as {detail?: string | {code?: string; message?: string}; code?: string; message?: string};
        const detail = payload.detail;
        const code = typeof detail === "object" && detail ? detail.code : payload.code;
        const message = typeof detail === "string"
          ? detail
          : (typeof detail === "object" && detail ? detail.message : payload.message);
        throw new ApiError(message || `Request failed: ${statusLabel}.`, response.status, code);
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(
          `Request failed: ${statusLabel}. The API returned malformed JSON for ${method} ${path}.`,
          response.status,
          "MALFORMED_API_ERROR",
        );
      }
    }
    const summary = summarizeResponseText(body);
    throw new ApiError(
      `Request failed: ${statusLabel}${summary ? ` - ${summary}` : ""}.`,
      response.status,
      "NON_JSON_API_ERROR",
    );
  }

  if (!body.trim()) {
    throw new ApiError(
      `The API returned an empty response for ${method} ${path} (${statusLabel}).`,
      response.status,
      "EMPTY_API_RESPONSE",
    );
  }
  if (looksHtml || !looksJson) {
    throw new ApiError(
      `The API returned HTML instead of JSON for ${method} ${path}; check the nginx /api proxy configuration.`,
      response.status,
      "INVALID_API_RESPONSE",
    );
  }
  try {
    return JSON.parse(body) as T;
  } catch {
    throw new ApiError(
      `The API returned malformed JSON for ${method} ${path} (${statusLabel}).`,
      response.status,
      "INVALID_API_RESPONSE",
    );
  }
}

function summarizeResponseText(body: string): string {
  return body.replace(/\s+/g, " ").trim().slice(0, 240);
}

export function listRuns(options: RunListOptions = {}): Promise<RunListResponse> {
  const params = new URLSearchParams();
  if (options.pipeline) params.set("pipeline", options.pipeline);
  if (options.status) params.set("status", options.status);
  if (options.keyword) params.set("keyword", options.keyword);
  params.set("sort", options.sort || "created_desc");
  params.set("limit", String(options.limit ?? 50));
  params.set("offset", String(options.offset ?? 0));
  return requestJson<RunListResponse>(`/runs?${params.toString()}`);
}

export function listSamplesResource(options: {
  pipeline?: string;
  status?: string;
  qcStatus?: string;
  keyword?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<OperatorSampleResponse> {
  const params = new URLSearchParams();
  if (options.pipeline) params.set("pipeline", options.pipeline);
  if (options.status) params.set("status", options.status);
  if (options.qcStatus) params.set("qc_status", options.qcStatus);
  if (options.keyword) params.set("keyword", options.keyword);
  params.set("limit", String(options.limit ?? 25));
  params.set("offset", String(options.offset ?? 0));
  return requestJson<OperatorSampleResponse>(`/samples?${params.toString()}`);
}

export function listFailures(options: {
  pipeline?: string;
  kind?: "all" | "workflow" | "qc";
  layer?: string;
  period?: "24h" | "7d" | "30d";
  keyword?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<FailureListResponse> {
  const params = new URLSearchParams();
  params.set("pipeline", options.pipeline || "all");
  params.set("kind", options.kind || "all");
  params.set("period", options.period || "7d");
  if (options.layer) params.set("layer", options.layer);
  if (options.keyword) params.set("keyword", options.keyword);
  params.set("limit", String(options.limit ?? 20));
  params.set("offset", String(options.offset ?? 0));
  return requestJson<FailureListResponse>(`/failures?${params.toString()}`);
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

export function getRunResources(analysisId: string): Promise<RunResourceSummary> {
  return requestJson<RunResourceSummary>(`/runs/${encodeURIComponent(analysisId)}/resources`);
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health");
}

export function getPlatformCapabilities(): Promise<PlatformCapabilities> {
  return requestJson<PlatformCapabilities>("/platform/capabilities");
}

export function getWgsRelease(): Promise<WgsRelease> {
  return requestJson<WgsRelease>("/wgs/release");
}

export function getSession(): Promise<SessionUser> {
  return requestJson<SessionUser>("/auth/me").then((user) => {
    csrfToken = user.csrf_token || "";
    return user;
  });
}

export function login(payload: LoginRequest): Promise<SessionUser> {
  return requestJson<SessionUser>("/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  }).then((user) => {
    csrfToken = user.csrf_token || "";
    return user;
  });
}

export function logout(): Promise<void> {
  return requestJson<void>("/auth/logout", {method: "POST"}).finally(() => {
    csrfToken = "";
  });
}

export function listUsers(): Promise<{items: SessionUser[]}> {
  return requestJson<{items: SessionUser[]}>("/users");
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

export function getPipelineConfigTemplate(options: {
  pipeline: "pgta" | "nipt_docker";
  target?: PgtaTarget;
  runMode?: NiptRunMode;
  profileId?: string;
}): Promise<PipelineConfigTemplate> {
  const params = new URLSearchParams({
    pipeline: options.pipeline,
    target: options.target || "metadata",
    run_mode: options.runMode || "mount_smoke",
  });
  if (options.profileId) params.set("profile_id", options.profileId);
  return requestJson<PipelineConfigTemplate>(`/pipeline-config/template?${params.toString()}`);
}

export function validatePipelineConfig(payload: {
  pipeline: "pgta" | "nipt_docker";
  target?: PgtaTarget;
  run_mode?: NiptRunMode;
  cores?: number | null;
  runtime_profile_id: string;
  config_template_hash: string;
  snakemake_config_yaml: string;
}): Promise<PipelineConfigValidation> {
  return requestJson<PipelineConfigValidation>("/pipeline-config/validate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function scanAndSubmitIntake(payload: {pipelines: DeployedPipeline[]; bootstrap?: boolean; max_samples?: number}): Promise<IntakeStatusResponse> {
  return requestJson<IntakeStatusResponse>("/intake/scan-and-submit", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function previewIntakeScan(payload: {pipelines: DeployedPipeline[]; bootstrap?: boolean; max_samples?: number}): Promise<IntakeScanPreviewResponse> {
  return requestJson<IntakeScanPreviewResponse>("/intake/scan-preview", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
}

export function getIntakeStatus(options: {
  pipeline?: DeployedPipeline | "deployed";
  state?: IntakeDiscoveryState;
  lifecycle?: IntakeLifecycle;
  view?: IntakeView;
  keyword?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<IntakeStatusResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 50));
  params.set("offset", String(options.offset ?? 0));
  if (options.pipeline) params.set("pipeline", options.pipeline);
  if (options.state) params.set("state", options.state);
  if (options.lifecycle) params.set("lifecycle", options.lifecycle);
  if (options.view) params.set("view", options.view);
  if (options.keyword) params.set("keyword", options.keyword);
  return requestJson<IntakeStatusResponse>(`/intake/status?${params.toString()}`);
}

export function getWorkflowCatalog(): Promise<WorkflowCatalogResponse> {
  return requestJson<WorkflowCatalogResponse>("/workflows");
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

export function getRunFamilies(analysisId: string): Promise<{items: WgsFamily[]}> {
  return requestJson<{items: WgsFamily[]}>(`/runs/${encodeURIComponent(analysisId)}/families`);
}

export function getRunRules(analysisId: string): Promise<{items: RuleEvent[]}> {
  return requestJson<{items: RuleEvent[]}>(`/runs/${encodeURIComponent(analysisId)}/rules`);
}

export function getRunPods(analysisId: string): Promise<{items: WgsPod[]}> {
  return requestJson<{items: WgsPod[]}>(`/runs/${encodeURIComponent(analysisId)}/pods`);
}

export function getRunTransfers(analysisId: string): Promise<{items: WgsTransfer[]}> {
  return requestJson<{items: WgsTransfer[]}>(`/runs/${encodeURIComponent(analysisId)}/transfers`);
}

export function getRunValidationIssues(analysisId: string): Promise<{items: WgsValidationIssue[]}> {
  return requestJson<{items: WgsValidationIssue[]}>(`/runs/${encodeURIComponent(analysisId)}/validation-issues`);
}

export function revalidateRun(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}/actions/revalidate`, {method: "POST"});
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

export function getRunConfig(analysisId: string): Promise<RunConfig> {
  return requestJson<RunConfig>(`/runs/${encodeURIComponent(analysisId)}/config`);
}

export function getRunLog(analysisId: string, stream: LogStream, key?: string): Promise<RunLog> {
  const params = new URLSearchParams({stream, tail: "200"});
  if (key) params.set("key", key);
  return requestJson<RunLog>(`/runs/${encodeURIComponent(analysisId)}/logs?${params.toString()}`);
}

export function getRunLogIndex(analysisId: string): Promise<{items: RunLogIndexItem[]}> {
  return requestJson<{items: RunLogIndexItem[]}>(`/runs/${encodeURIComponent(analysisId)}/logs/index`);
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

export function resumeRun(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}/actions/resume`, {method: "POST"});
}

export function rerunFailedRun(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}/actions/rerun_failed`, {method: "POST"});
}

export function cancelRun(analysisId: string): Promise<RunDetail> {
  return requestJson<RunDetail>(`/runs/${encodeURIComponent(analysisId)}/actions/cancel`, {method: "POST"});
}
