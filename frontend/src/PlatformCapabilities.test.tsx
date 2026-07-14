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
