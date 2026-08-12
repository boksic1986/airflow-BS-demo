import "@testing-library/jest-dom/vitest";

import {cleanup, render, screen} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

it("shows execution modes on the WGS submission form", async () => {
  window.history.pushState({}, "", "/submit");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Submit WGS run"})).toBeInTheDocument();
  expect(screen.getByRole("option", {name: "CCE (configured, disabled)"})).toBeInTheDocument();
  expect(screen.getByRole("option", {name: "SGE (configured, disabled)"})).toBeInTheDocument();
  expect(screen.getByRole("option", {name: "Local (configured, disabled)"})).toBeInTheDocument();
  expect(screen.getByText("Controlled batch directory")).toBeInTheDocument();
  expect(screen.getByText(/will not start CCE, SGE, or local WGS work/i)).toBeInTheDocument();
});

it("loads WGS resource tabs for an active run", async () => {
  window.history.pushState({}, "", "/runs/WGS_001");
  const urls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    urls.push(url);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({environment: "WGS", deployed_pipelines: ["wgs"], airflow_url: null});
    if (url.includes("/api/runs/WGS_001?") || url.endsWith("/api/runs/WGS_001")) return json({analysis_id: "WGS_001", pipeline: "wgs", status: "running"});
    if (url.includes("/api/runs/WGS_001/families")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/rules")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/pods")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/transfers")) return json({items: []});
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
  expect(screen.getByRole("tab", {name: "Pods"})).toBeInTheDocument();
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
