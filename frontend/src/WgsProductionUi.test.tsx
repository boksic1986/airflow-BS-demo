import "@testing-library/jest-dom/vitest";

import {cleanup, fireEvent, render, screen} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

it("uses a pipeline-selectable staged WGS submission form", async () => {
  window.history.pushState({}, "", "/submit");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.endsWith("/api/wgs/release")) return json({release_id: "wgs-4.1.1-6c98281", version: "V4.1.1", source_commit: "6c982817614db6a1157b6f287427ddf01ac91827", execution_enabled: false, runtime_adapter_enabled: false, submission_preview_enabled: false});
    if (url.endsWith("/api/wgs/projects")) return json({items: [{project_id: "WGS_Clinical", display_name: "WGS Clinical", platforms: [{platform_id: "T7", display_name: "T7 / hg38 / V4.1.1"}], fastq_roots: [{root_id: "T7_Fastq", display_name: "T7 FASTQ"}], editable_config: {use_reference: {type: "enum", values: ["all", "ref", "no"], default: "all"}}}]});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Submit run"})).toBeInTheDocument();
  expect(screen.getByLabelText("Pipeline")).toHaveValue("wgs");
  expect(screen.getByRole("option", {name: "WES (not available)"})).toBeDisabled();
  expect(screen.getByLabelText("FASTQ root")).toBeInTheDocument();
  expect(screen.getByLabelText("Batch")).toBeInTheDocument();
  expect(screen.queryByLabelText("Sequencing batch")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Analysis batch")).not.toBeInTheDocument();
  expect(await screen.findByText("WGS V4.1.1 / 6c98281")).toBeInTheDocument();
  expect(screen.queryByLabelText("Variant caller")).not.toBeInTheDocument();
  expect(screen.queryByRole("combobox", {name: /WGS version/i})).not.toBeInTheDocument();
  expect(screen.queryByText(/READY/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Use reference")).not.toBeInTheDocument();
  expect(screen.getByRole("button", {name: "Prepare sample information"})).toBeDisabled();
  expect(screen.getByText(/WGS first generates sampleinfo/)).toBeInTheDocument();
  expect(screen.queryByText(/preview is not enabled/)).not.toBeInTheDocument();
});

it("starts stage one without accepting runtime configuration", async () => {
  window.history.pushState({}, "", "/submit");
  const requests: Array<{url: string; init?: RequestInit}> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    requests.push({url, init});
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.endsWith("/api/wgs/release")) return json({release_id: "wgs-4.1.1-6c98281", version: "V4.1.1", source_commit: "6c982817614db6a1157b6f287427ddf01ac91827", execution_enabled: true, runtime_adapter_enabled: true, submission_preview_enabled: false});
    if (url.endsWith("/api/wgs/projects")) return json({items: [{project_id: "WGS_Clinical", display_name: "WGS Clinical", platforms: [{platform_id: "T7", display_name: "T7 / hg38 / V4.1.1"}], fastq_roots: [{root_id: "T7_Fastq", display_name: "T7 FASTQ"}], editable_config: {use_reference: {type: "enum", values: ["all", "ref", "no"], default: "all"}}}]});
    if (url.endsWith("/api/wgs/runs")) return json({analysis_id: "WGS_TEST", pipeline: "wgs", status: "submitted", params: {submission_phase: "config_review"}});
    if (url.endsWith("/api/runs/WGS_TEST")) return json({analysis_id: "WGS_TEST", pipeline: "wgs", status: "submitted", params: {submission_phase: "config_review"}});
    if (url.endsWith("/api/runs/WGS_TEST/samples")) return json({items: [{sample_id: "S1", family_id: "F1", status: "pending", metadata: {}}]});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("button", {name: "Prepare sample information"})).toBeInTheDocument();
  expect(await screen.findByText("Enabled")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Batch"), {target: {value: "20260901B"}});
  fireEvent.click(screen.getByRole("button", {name: "Prepare sample information"}));
  expect(await screen.findByRole("heading", {name: "Review samples and configuration"})).toBeInTheDocument();
  expect(await screen.findByText("S1")).toBeInTheDocument();
  expect(screen.getByLabelText("Use reference")).toBeInTheDocument();
  expect(screen.getByLabelText("Resource set")).toHaveValue("default");
  const submitted = requests.find((item) => item.url.endsWith("/api/wgs/runs") && item.init?.method === "POST");
  expect(JSON.parse(String(submitted?.init?.body))).toMatchObject({batch: "20260901B"});
  expect(String(submitted?.init?.body)).not.toContain("use_reference");
  expect(String(submitted?.init?.body)).not.toContain("sequencing_batch");
  expect(String(submitted?.init?.body)).not.toContain("analysis_batch");
});

it("loads WGS resource tabs for an active run", async () => {
  window.history.pushState({}, "", "/runs/WGS_001");
  const urls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    urls.push(url);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.includes("/api/runs/WGS_001?") || url.endsWith("/api/runs/WGS_001")) return json({analysis_id: "WGS_001", pipeline: "wgs", status: "running", pipeline_release_id: "wgs-4.1.1-1656b5d", wgs_version: "V4.1.1", wgs_source_commit: "1656b5d7a6e2f24242c38149f6d1c92ac266cd37", resolved_runtime: {cce_pipeline_version: "0.7.1", profile_id: "wgs-4.1.1-r1", master_image_digest: "sha256:abc"}, rule_event_schema_version: "rule-event.v1", observer: {lifecycle_status: "active", monitoring_health: "healthy", activated_at: "2026-08-26T01:00:00Z", last_success_at: "2026-08-26T01:01:05Z", last_error: null, updated_at: "2026-08-26T01:01:05Z"}});
    if (url.includes("/api/runs/WGS_001/samples")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/rules")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/pods")) return json({items: [{attempt: 1, pod_hash: "abc123", job_name: "wgs-master-a1", phase: "Failed", reason: "OOMKilled", exit_code: 137, node_name: "cce-node-1", message: "Master failed", resources: {memory: "4Gi"}, observed_at: "2026-08-24T01:01:00Z", updated_at: "2026-08-24T01:01:05Z"}]});
    if (url.includes("/api/runs/WGS_001/transfers")) return json({items: [{transfer_id: "WGS_001-a1-input", source: "/controlled/fq", destination: "OBS input prefix", status: "running", progress_detail_available: false, heartbeat_at: "2026-08-26T01:01:05Z", message: "Step1 upload is running"}]});
    if (url.includes("/api/runs/WGS_001/progress")) return json({analysis_id: "WGS_001", pipeline: "wgs", status: "running", percent: 0, current_step: "prepare", current_source: "runner", note: "", not_in_airflow: false, progress_source: "estimate", airflow_tasks: [], rule_events: []});
    if (url.includes("/api/runs/WGS_001/qc")) return json({summary: {pass: 0, warn: 0, fail: 0, unknown: 0}, items: []});
    if (url.includes("/api/runs/WGS_001/logs/index")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/logs")) return json({path: "", stream: "stdout", truncated: false, lines: []});
    if (url.includes("/api/runs/WGS_001/artifacts")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/resources")) return json({analysis_id: "WGS_001", pipeline: "wgs", wall_seconds: 0, peak_rss_bytes: 0, read_bytes: 0, write_bytes: 0, cpu_seconds: 0, sample_count: 0, complete: false});
    return json({items: []});
  }));

  render(<App />);
  expect(await screen.findByRole("tab", {name: "Samples"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "Master"})).toBeInTheDocument();
  expect(screen.getAllByText("wgs-4.1.1-1656b5d").length).toBeGreaterThan(0);
  expect(screen.getByText("V4.1.1")).toBeInTheDocument();
  expect(screen.getByText("0.7.1")).toBeInTheDocument();
  expect(screen.queryByText(/sha256:abc/)).not.toBeInTheDocument();
  expect(screen.getByText(/healthy/i)).toBeInTheDocument();
  expect(screen.getByText(/active/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "Master"}));
  expect(await screen.findByText("wgs-master-a1")).toBeInTheDocument();
  expect(screen.getByText("OOMKilled")).toBeInTheDocument();
  expect(screen.getByText("137")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "Transfers"}));
  expect(await screen.findByText("WGS_001-a1-input")).toBeInTheDocument();
  expect(screen.getByText(/阶段状态可用/)).toBeInTheDocument();
  expect(screen.queryByLabelText("WGS_001-a1-input progress")).not.toBeInTheDocument();
  expect(screen.queryByText(/0 B\/s/)).not.toBeInTheDocument();
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/samples"))).toBe(true);
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/pods"))).toBe(true);
});

it("shows and searches the public WGS batch in the sample inventory", async () => {
  window.history.pushState({}, "", "/samples");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.includes("/api/samples")) return json({
      items: [{
        analysis_id: "WGS_001",
        project_name: "WGS_Clinical",
        pipeline: "wgs",
        sample_id: "S1",
        family_id: "F1",
        batch_no: "20260901B",
        sequencing_batch: "20260901B",
        status: "success",
        report_status: "not_available",
      }],
      total: 1,
      limit: 25,
      offset: 0,
    });
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByText("20260901B")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("sample, family, batch, project or run ID")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "batch"})).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", {name: "sequencing batch"})).not.toBeInTheDocument();
});

it("keeps account administration hidden for viewers", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    return json({items: [], total: 0});
  }));
  render(<App />);
  expect(await screen.findByText("WGS Control Tower")).toBeInTheDocument();
  expect(screen.queryByRole("link", {name: "Accounts"})).not.toBeInTheDocument();
});

it("removes QC summary actions from the WGS-only dashboard", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.includes("/api/dashboard/overview")) return json({totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0}, sample_summary: {total: 0, running: 0, workflow_failed: 0, qc_failed: 7, completed: 0}, status_distribution: {}, trend: [], sample_trend: []});
    if (url.includes("/api/dashboard/runs")) return json({items: [], total: 0, limit: 10, offset: 0});
    if (url.includes("/api/intake/scanner-state")) return json({last_scanned_directory_count: 0, schedule_seconds: 600, auto_dispatch_enabled: false});
    if (url.includes("/api/intake/status")) return json({items: [], total: 0, limit: 10, offset: 0});
    if (url.includes("/api/platform/resources")) return json({status: "stale", items: [], updated_at: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Command Center"})).toBeInTheDocument();
  expect(screen.queryByText("QC alerts")).not.toBeInTheDocument();
  expect(screen.queryByText("QC failed samples")).not.toBeInTheDocument();
  expect(screen.getByText("Workflow fails")).toBeInTheDocument();
});

it("keeps scanner metadata when the discovery list has a transiently unavailable API", async () => {
  let intakeAttempts = 0;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS production", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.includes("/api/dashboard/overview")) return json({totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0}, sample_summary: {total: 0, running: 0, workflow_failed: 0, completed: 0}, status_distribution: {}, trend: [], sample_trend: []});
    if (url.includes("/api/dashboard/runs")) return json({items: [], total: 0, limit: 10, offset: 0});
    if (url.includes("/api/intake/scanner-state")) return json({last_scanned_directory_count: 1843, schedule_seconds: 600, auto_dispatch_enabled: false});
    if (url.includes("/api/intake/status")) {
      intakeAttempts += 1;
      return Promise.reject(new TypeError("Failed to fetch"));
    }
    if (url.includes("/api/platform/resources")) return json({status: "stale", items: [], updated_at: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByText("本轮检查 1843 个批次目录")).toBeInTheDocument();
  expect(await screen.findByText(/Intake unavailable: Failed to fetch/)).toBeInTheDocument();
  expect(intakeAttempts).toBe(2);
});

function json(value: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(value), {status: 200, headers: {"Content-Type": "application/json"}}));
}
