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

it("filters stale retired catalog data and shows only the deployed WGS workflow", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) {
      return Promise.resolve(new Response(JSON.stringify({
        environment: "BS10610",
        deployed_pipelines: ["wgs"],
        airflow_url: null,
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({items: [
      {pipeline: "pgta", name: "PGT-A Predict", dag_id: "bio_pgta", runtime_profile_id: "pgta-s9-predict-v1", runtime: "Snakemake 9.23.1", stages: [], latest_run: null, run_count: 2, success_rate: 1},
      {pipeline: "nipt_docker", name: "NIPT Docker Full", dag_id: "bio_nipt_docker", runtime_profile_id: "niptpro-s9-full-v1", runtime: "Snakemake 9.23.1 in NIPTPro", stages: [{key: "mapping", label: "Mapping", status: "failed", completed_jobs: 2, total_jobs: 4}], latest_run: {analysis_id: "NIPT_FAILED", project_name: "NIPT failed", status: "failed", current_stage: "Mapping"}, run_count: 1, success_rate: 0},
      {pipeline: "wgs", name: "WGS 4.2.0 CCE", dag_id: "bio_wgs", runtime_profile_id: "wgs-4.1.1-r1", runtime: "Snakemake 9.24.0+biosan4 on CCE", stages: [{key: "step3", label: "CCE analysis", status: "running", completed_jobs: 0, total_jobs: 0}], latest_run: {analysis_id: "WGS_RUNNING", project_name: "WGS family", status: "running", current_stage: "Step3 analysis"}, run_count: 1, success_rate: 0},
    ]}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<PlatformCapabilitiesProvider><MemoryRouter><WorkflowsPage /></MemoryRouter></PlatformCapabilitiesProvider>);

  await waitFor(() => expect(screen.getByText("WGS 4.2.0 CCE")).toBeInTheDocument());
  expect(screen.getByText("WGS_RUNNING")).toBeInTheDocument();
  expect(screen.queryByText("NIPT Docker Full")).not.toBeInTheDocument();
  expect(screen.queryByText("NIPT_FAILED")).not.toBeInTheDocument();
  expect(screen.queryByText("PGT-A Predict")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/workflows"), expect.objectContaining({credentials: "same-origin"}));
});
