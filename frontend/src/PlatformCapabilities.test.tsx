import "@testing-library/jest-dom/vitest";

import {cleanup, render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";


afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  delete window.__AIRFLOW_DEMO_CONFIG__;
  window.history.pushState({}, "", "/");
});

function sharedCapabilitiesResponse() {
  return new Response(JSON.stringify({
    environment: "BS10610",
    deployed_pipelines: ["nipt_docker", "wgs"],
    airflow_url: "http://172.17.106.10:12958",
  }), {status: 200, headers: {"Content-Type": "application/json"}});
}


it("renders the NIPT-only product from backend capabilities", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) {
      return Promise.resolve(new Response(JSON.stringify({
        environment: "BS10610",
        deployed_pipelines: ["nipt_docker"],
        airflow_url: "http://172.17.106.10:12958",
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({
      pipeline: "nipt_docker",
      period: "7d",
      totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0},
      items: [], total: 0, limit: 10, offset: 0,
      source: "host_proc", services: [], host: {cpu: {}, memory: {}, disks: []}, containers: [],
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  expect(await screen.findByText("NIPT Control Tower")).toBeInTheDocument();
  expect(screen.getByText("NIPT Docker only")).toBeInTheDocument();
  await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith("/api/platform/capabilities", undefined));
});


it("renders the WGS-only product from backend capabilities", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) {
      return Promise.resolve(new Response(JSON.stringify({
        environment: "BS10610-WGS",
        deployed_pipelines: ["wgs"],
        airflow_url: "http://172.17.106.10:13958",
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({
      pipeline: "wgs",
      period: "7d",
      totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0},
      items: [], total: 0, limit: 10, offset: 0,
      source: "host_proc", services: [], host: {cpu: {}, memory: {}, disks: []}, containers: [],
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  expect(await screen.findByText("WGS Control Tower")).toBeInTheDocument();
  expect(screen.getByText("WGS only")).toBeInTheDocument();
});


it("renders one shared NIPT and WGS control plane without PGT-A", async () => {
  window.__AIRFLOW_DEMO_CONFIG__ = {apiBaseUrl: "/api"};
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) {
      return Promise.resolve(new Response(JSON.stringify({
        environment: "BS10610",
        deployed_pipelines: ["nipt_docker", "wgs"],
        airflow_url: "http://172.17.106.10:12958",
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({
      pipeline: "all",
      period: "7d",
      totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0},
      items: [], total: 0, limit: 10, offset: 0,
      source: "host_proc", services: [], host: {cpu: {}, memory: {}, disks: []}, containers: [],
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  expect(await screen.findByText("NIPT Docker + WGS")).toBeInTheDocument();
  expect(screen.getByRole("button", {name: "NIPT Docker"})).toBeInTheDocument();
  expect(screen.getByRole("button", {name: "WGS"})).toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "PGT-A"})).not.toBeInTheDocument();
});

it("opens Submit Run on NIPT without issuing a transient PGT-A config request", async () => {
  window.history.pushState({}, "", "/submit");
  const requestedUrls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.endsWith("/api/platform/capabilities")) return Promise.resolve(sharedCapabilitiesResponse());
    if (url.includes("/api/input/roots")) {
      return Promise.resolve(new Response(JSON.stringify({pipeline: "nipt_docker", roots: ["/data/nipt-fastq"]}), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    if (url.includes("/api/pipeline-config/template")) {
      return Promise.resolve(new Response(JSON.stringify({
        pipeline: "nipt_docker",
        profile: {id: "niptpro-s9-full-v1", label: "NIPT S9", pipeline_version: "1.1.11", config_version: "v1"},
        profiles: [{id: "niptpro-s9-full-v1", label: "NIPT S9", pipeline_version: "1.1.11", config_version: "v1"}],
        config_template_hash: "hash",
        editable_yaml: "params:\n  seed: 9696\n",
        changed_paths: [],
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({items: []}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  expect(await screen.findByRole("radio", {name: /NIPT Docker/i})).toBeInTheDocument();
  expect(screen.getByRole("radio", {name: /^WGS/i})).toBeInTheDocument();
  await waitFor(() => expect(requestedUrls.some((url) => url.includes("pipeline=nipt_docker"))).toBe(true));
  expect(requestedUrls.some((url) => url.includes("pipeline=pgta"))).toBe(false);
  expect(screen.queryByText(/PGT-A/i)).not.toBeInTheDocument();
});

it.each([
  ["/runs?pipeline=pgta", "/api/runs?"],
  ["/samples?pipeline=pgta", "/api/samples?"],
  ["/failures?pipeline=pgta", "/api/failures?"],
])("drops an undeployed PGT-A filter from %s", async (route, endpoint) => {
  window.history.pushState({}, "", route);
  const requestedUrls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.endsWith("/api/platform/capabilities")) return Promise.resolve(sharedCapabilitiesResponse());
    return Promise.resolve(new Response(JSON.stringify({items: [], total: 0, limit: 25, offset: 0}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  await waitFor(() => expect(requestedUrls.some((url) => url.includes(endpoint))).toBe(true));
  const resourceCalls = requestedUrls.filter((url) => url.includes(endpoint));
  expect(resourceCalls.every((url) => !url.includes("pipeline=pgta"))).toBe(true);
  expect(resourceCalls).toHaveLength(1);
  expect(resourceCalls[0]).toContain("pipeline=deployed");
  expect(screen.queryByRole("option", {name: "PGT-A"})).not.toBeInTheDocument();
});

it("loads the shared Dashboard through one deployed-scope overview and run query", async () => {
  window.history.pushState({}, "", "/dashboard");
  const requestedUrls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.endsWith("/api/platform/capabilities")) return Promise.resolve(sharedCapabilitiesResponse());
    return Promise.resolve(new Response(JSON.stringify({
      pipeline: "deployed",
      period: "7d",
      totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0},
      status_distribution: {},
      pipeline_breakdown: {},
      trend: [],
      qc_summary: {},
      sample_summary: {total: 0, running: 0, workflow_failed: 0, qc_failed: 0, completed: 0},
      sample_trend: [],
      failure_summary: [],
      intake_summary: {},
      items: [],
      total: 0,
      limit: 10,
      offset: 0,
      source: "host_proc",
      services: [],
      host: {cpu: {}, memory: {}, disks: []},
      containers: [],
    }), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  await waitFor(() => expect(requestedUrls.some((url) => url.includes("/api/dashboard/runs?"))).toBe(true));
  const overviewCalls = requestedUrls.filter((url) => url.includes("/api/dashboard/overview?"));
  const runCalls = requestedUrls.filter((url) => url.includes("/api/dashboard/runs?"));
  const intakeCalls = requestedUrls.filter((url) => url.includes("/api/intake/status?"));
  expect(overviewCalls).toHaveLength(1);
  expect(runCalls).toHaveLength(1);
  expect(intakeCalls).toHaveLength(1);
  expect(overviewCalls[0]).toContain("pipeline=deployed");
  expect(runCalls[0]).toContain("pipeline=deployed");
  expect(intakeCalls[0]).toContain("pipeline=deployed");
  expect(screen.queryByRole("button", {name: "PGT-A"})).not.toBeInTheDocument();
});

it("hides stale PGT-A intake config and discovery records in Platform Settings", async () => {
  window.history.pushState({}, "", "/settings");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) return Promise.resolve(sharedCapabilitiesResponse());
    if (url.includes("/api/intake/config")) {
      const pipelineConfig = (id: string) => ({
        enabled: true,
        roots: [{id, container_path: `/data/${id}`}],
        ignore_patterns: [],
        auto_submit: {enabled: false},
      });
      return Promise.resolve(new Response(JSON.stringify({
        source: "config/intake.yaml",
        defaults: {ready_rule: "stable_fingerprint", stable_scans: 2, auto_submit: false},
        pipelines: {
          pgta: pipelineConfig("legacy-pgta-root"),
          nipt_docker: pipelineConfig("nipt-root"),
          wgs: pipelineConfig("wgs-root"),
        },
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    if (url.includes("/api/intake/scanner-state")) {
      return Promise.resolve(new Response(JSON.stringify({
        dag_id: "bio_intake_scan",
        airflow_reachable: true,
        is_paused: true,
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    if (url.includes("/api/intake/status")) {
      return Promise.resolve(new Response(JSON.stringify({items: [
        {pipeline: "pgta", root_path: "/data/pgta", batch_id: "legacy-pgta-batch", fingerprint: "old", file_count: 2, total_bytes: 10, ready_state: "observed", submit_state: "not_submitted"},
        {pipeline: "nipt_docker", root_path: "/data/nipt", batch_id: "nipt-batch", fingerprint: "new", file_count: 2, total_bytes: 10, ready_state: "observed", submit_state: "not_submitted"},
      ], total: 2, limit: 10, offset: 0}), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({items: []}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<App />);

  expect(await screen.findByText("nipt-root")).toBeInTheDocument();
  expect(screen.getByText("wgs-root")).toBeInTheDocument();
  expect(await screen.findByText("nipt-batch")).toBeInTheDocument();
  expect(screen.queryByText("legacy-pgta-root")).not.toBeInTheDocument();
  expect(screen.queryByText("legacy-pgta-batch")).not.toBeInTheDocument();
  expect(screen.queryByText("PGT-A")).not.toBeInTheDocument();
});
