import "@testing-library/jest-dom/vitest";

import {render, screen, waitFor} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {afterEach, expect, it, vi} from "vitest";

import {PlatformCapabilitiesProvider} from "../features/platform/PlatformCapabilitiesContext";
import {WorkflowsPage} from "./WorkflowsPage";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("filters stale PGT-A catalog data and shows only deployed NIPT and WGS workflows", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) {
      return Promise.resolve(new Response(JSON.stringify({
        environment: "BS10610",
        deployed_pipelines: ["nipt_docker", "wgs"],
        airflow_url: "http://172.17.106.10:12958",
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({items: [
      {pipeline: "pgta", name: "PGT-A Predict", dag_id: "bio_pgta", runtime_profile_id: "pgta-s9-predict-v1", runtime: "Snakemake 9.23.1", stages: [], latest_run: null, run_count: 2, success_rate: 1},
      {pipeline: "nipt_docker", name: "NIPT Docker Full", dag_id: "bio_nipt_docker", runtime_profile_id: "niptpro-s9-full-v1", runtime: "Snakemake 9.23.1 in NIPTPro", stages: [{key: "mapping", label: "Mapping", status: "failed", completed_jobs: 2, total_jobs: 4}], latest_run: {analysis_id: "NIPT_FAILED", project_name: "NIPT failed", status: "failed", current_stage: "Mapping"}, run_count: 1, success_rate: 0},
      {pipeline: "wgs", name: "WGS Host Full", dag_id: "bio_wgs", runtime_profile_id: "wgs-s9-host-v1", runtime: "Snakemake 9.23.1 on BS host", stages: [{key: "pre_calling", label: "Pre-calling", status: "running", completed_jobs: 12, total_jobs: 18}], latest_run: {analysis_id: "WGS_RUNNING", project_name: "WGS family", status: "running", current_stage: "Pre-calling"}, run_count: 1, success_rate: 0},
    ]}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<PlatformCapabilitiesProvider><MemoryRouter><WorkflowsPage /></MemoryRouter></PlatformCapabilitiesProvider>);

  await waitFor(() => expect(screen.getByText("NIPT Docker Full")).toBeInTheDocument());
  expect(screen.getByText("WGS Host Full")).toBeInTheDocument();
  expect(screen.getByText("NIPT_FAILED")).toBeInTheDocument();
  expect(screen.getByText("WGS_RUNNING")).toBeInTheDocument();
  expect(screen.queryByText("PGT-A Predict")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/workflows"), undefined);
});
