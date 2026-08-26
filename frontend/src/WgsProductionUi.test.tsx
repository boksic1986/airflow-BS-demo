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

it("uses batch number and a controlled FASTQ link directory on the WGS submission form", async () => {
  window.history.pushState({}, "", "/submit");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Submit WGS run"})).toBeInTheDocument();
  expect(screen.getByLabelText("Batch number")).toBeInTheDocument();
  expect(screen.getByLabelText("Controlled FASTQ link directory")).toBeInTheDocument();
  expect(screen.queryByText(/READY/)).not.toBeInTheDocument();
  expect(screen.getByText(/will not start CCE/i)).toBeInTheDocument();
});

it("loads WGS resource tabs for an active run", async () => {
  window.history.pushState({}, "", "/runs/WGS_001");
  const urls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    urls.push(url);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.includes("/api/runs/WGS_001?") || url.endsWith("/api/runs/WGS_001")) return json({analysis_id: "WGS_001", pipeline: "wgs", status: "running", pipeline_snapshot_id: "wgs-v4.1.1-candidate-3489b39-64d50022", rule_event_schema_version: "rule-event.v1", observer: {status: "healthy", last_success_at: "2026-08-26T01:01:05Z", last_error: null, updated_at: "2026-08-26T01:01:05Z"}});
    if (url.includes("/api/runs/WGS_001/families")) return json({items: []});
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
  expect(await screen.findByRole("tab", {name: "Families"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "Master"})).toBeInTheDocument();
  expect(screen.getByText("wgs-v4.1.1-candidate-3489b39-64d50022")).toBeInTheDocument();
  expect(screen.getByText(/healthy/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "Master"}));
  expect(await screen.findByText("wgs-master-a1")).toBeInTheDocument();
  expect(screen.getByText("OOMKilled")).toBeInTheDocument();
  expect(screen.getByText("137")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "Transfers"}));
  expect(await screen.findByText("WGS_001-a1-input")).toBeInTheDocument();
  expect(screen.getByText(/阶段状态可用/)).toBeInTheDocument();
  expect(screen.queryByLabelText("WGS_001-a1-input progress")).not.toBeInTheDocument();
  expect(screen.queryByText(/0 B\/s/)).not.toBeInTheDocument();
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/families"))).toBe(true);
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/pods"))).toBe(true);
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

function json(value: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(value), {status: 200, headers: {"Content-Type": "application/json"}}));
}
