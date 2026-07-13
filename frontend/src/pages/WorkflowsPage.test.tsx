import "@testing-library/jest-dom/vitest";

import {render, screen, waitFor} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {afterEach, expect, it, vi} from "vitest";

import {WorkflowsPage} from "./WorkflowsPage";

afterEach(() => vi.restoreAllMocks());

it("loads only the two deployed workflows from the live catalog endpoint", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({items: [
      {pipeline: "pgta", name: "PGT-A Predict", dag_id: "bio_pgta", runtime_profile_id: "pgta-s9-predict-v1", runtime: "Snakemake 9.23.1", stages: [{key: "mapping", label: "Mapping", status: "success", completed_jobs: 2, total_jobs: 2}], latest_run: {analysis_id: "PGTA_LIVE", project_name: "PGT-A live", status: "success", current_stage: "Completed"}, run_count: 2, success_rate: 1},
      {pipeline: "nipt_docker", name: "NIPT Docker Full", dag_id: "bio_nipt_docker", runtime_profile_id: "niptpro-s9-full-v1", runtime: "Snakemake 9.23.1 in NIPTPro", stages: [{key: "mapping", label: "Mapping", status: "failed", completed_jobs: 2, total_jobs: 4}], latest_run: {analysis_id: "NIPT_FAILED", project_name: "NIPT failed", status: "failed", current_stage: "Mapping"}, run_count: 1, success_rate: 0},
    ]}),
  }));

  render(<MemoryRouter><WorkflowsPage /></MemoryRouter>);

  await waitFor(() => expect(screen.getByText("PGT-A Predict")).toBeInTheDocument());
  expect(screen.getByText("NIPT Docker Full")).toBeInTheDocument();
  expect(screen.getByText("NIPT_FAILED")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/workflows"), undefined);
});
