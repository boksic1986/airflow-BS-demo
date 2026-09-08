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

it("renders only registry pipelines deployed by capabilities", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/platform/capabilities")) {
      return Promise.resolve(new Response(JSON.stringify({
        environment: "BS10610",
        deployed_pipelines: ["wgs"],
        pipelines: [
          {id: "wgs", display_name: "Whole genome sequencing", dag_id: "bio_wgs", enabled: true, submit_enabled: true, capabilities: ["submit", "qc"], execution_targets: ["cce", "local"]},
          {id: "wes", display_name: "Whole exome sequencing", dag_id: "bio_wes", enabled: false, submit_enabled: false, capabilities: ["submit"], execution_targets: ["local"]},
        ],
        airflow_url: null,
      }), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    if (url.includes("/api/runs?")) {
      return Promise.resolve(new Response(JSON.stringify({items: [{
        analysis_id: "WGS_20260907_152648_54EFF2",
        project_name: "WGS_Clinical",
        batch_no: "20260906B",
        pipeline: "wgs",
        status: "downloading",
        workflow_status: "running",
        workflow_label: "Workflow running",
        created_at: "2026-09-07T15:26:48Z",
      }], total: 1}), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({items: [
      {id: "wgs", display_name: "WGS", dag_id: "bio_wgs", version: "4.1.1", enabled: true, submit_enabled: true, capabilities: ["submit", "qc"], execution_targets: ["cce", "local"]},
      {id: "wes", display_name: "Whole exome sequencing", dag_id: "bio_wes", version: null, enabled: false, submit_enabled: false, capabilities: ["submit"], execution_targets: ["local"]},
    ]}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<PlatformCapabilitiesProvider><MemoryRouter><WorkflowsPage /></MemoryRouter></PlatformCapabilitiesProvider>);

  await waitFor(() => expect(screen.getByRole("heading", {name: "WGS"})).toBeInTheDocument());
  expect(screen.getByText("cce, local")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("20260906B")).toBeInTheDocument());
  expect(screen.getByText("Workflow running")).toBeInTheDocument();
  expect(screen.queryByText("Whole exome sequencing")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/workflows"), expect.objectContaining({credentials: "same-origin"}));
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/runs?pipeline=wgs"), expect.objectContaining({credentials: "same-origin"}));
});
