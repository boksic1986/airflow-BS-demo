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

declare global {
  interface Window {
    __AIRFLOW_DEMO_CONFIG__?: {
      apiBaseUrl?: string;
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

export function listRuns(): Promise<RunListResponse> {
  return requestJson<RunListResponse>("/runs?pipeline=pgta&limit=50&offset=0");
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
