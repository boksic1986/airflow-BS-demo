import "@testing-library/jest-dom/vitest";

import {render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";


afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  delete window.__AIRFLOW_DEMO_CONFIG__;
  window.history.pushState({}, "", "/");
});


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
