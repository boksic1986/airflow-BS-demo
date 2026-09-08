import "@testing-library/jest-dom/vitest";

import {render, screen, waitFor, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router-dom";
import {afterEach, expect, it, vi} from "vitest";

import {PlatformCapabilitiesProvider} from "../features/platform/PlatformCapabilitiesContext";
import {WorkflowsPage} from "./WorkflowsPage";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("renders a full-page filterable run lifecycle with QC", async () => {
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
      return Promise.resolve(new Response(JSON.stringify({items: [
        {
          analysis_id: "WGS_20260907_152648_54EFF2", project_name: "WGS_Clinical", batch_no: "20260906B", pipeline: "wgs",
          status: "success", workflow_status: "success", workflow_label: "Workflow completed", qc_status: "pass", created_at: "2026-09-07T15:26:48Z",
          lifecycle: {cloud_release: {status: "failed", updated_at: "2026-09-08T03:00:00Z"}, downstream_release: {status: "not_started"}},
        },
        {
          analysis_id: "WGS_20260906_120052_F17DAF", project_name: "WGS_Clinical", batch_no: "20260905C", pipeline: "wgs",
          status: "success", workflow_status: "success", workflow_label: "Workflow completed", qc_status: "warn", created_at: "2026-09-06T12:00:52Z",
          lifecycle: {cloud_release: {status: "success", updated_at: "2026-09-07T01:00:00Z"}, downstream_release: {status: "not_started"}},
        },
        {
          analysis_id: "WGS_20260906_104054_118DB3", project_name: "WGS_Clinical", batch_no: "20260905B", pipeline: "wgs",
          status: "success", workflow_status: "success", workflow_label: "Workflow completed", qc_status: "fail", created_at: "2026-09-06T10:40:54Z",
          lifecycle: {cloud_release: {status: "not_started"}, downstream_release: {status: "not_started"}},
        },
        {
          analysis_id: "WGS_20260905_141052_4C1BC0", project_name: "WGS_Clinical", batch_no: "20260904A", pipeline: "wgs",
          status: "success", workflow_status: "success", workflow_label: "Workflow completed", qc_status: "pass", created_at: "2026-09-05T14:10:52Z",
          lifecycle: {cloud_release: {status: "success"}, downstream_release: {status: "success"}},
        },
      ], total: 4}), {status: 200, headers: {"Content-Type": "application/json"}}));
    }
    return Promise.resolve(new Response(JSON.stringify({items: [
      {id: "wgs", display_name: "WGS", dag_id: "bio_wgs", version: "4.1.1", enabled: true, submit_enabled: true, capabilities: ["submit", "qc"], execution_targets: ["cce", "local"]},
      {id: "wes", display_name: "Whole exome sequencing", dag_id: "bio_wes", version: null, enabled: false, submit_enabled: false, capabilities: ["submit"], execution_targets: ["local"]},
    ]}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<PlatformCapabilitiesProvider><MemoryRouter><WorkflowsPage /></MemoryRouter></PlatformCapabilitiesProvider>);

  await waitFor(() => expect(screen.getByRole("heading", {name: "Run lifecycle"})).toBeInTheDocument());
  expect(screen.queryByRole("heading", {name: "Workflow Catalog"})).not.toBeInTheDocument();
  expect(screen.queryByText("Deployed pipeline capabilities and recent workflow, cloud release, and delivery state.")).not.toBeInTheDocument();
  expect(screen.queryByText("Recent runs")).not.toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "Cloud release"})).toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "Result delivery"})).toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "QC"})).toBeInTheDocument();
  const lifecycleTable = screen.getByRole("table", {name: "Run lifecycle"});
  await waitFor(() => expect(within(lifecycleTable).getAllByRole("row")).toHaveLength(5));

  await userEvent.selectOptions(screen.getByLabelText("QC status"), "fail");
  expect(within(lifecycleTable).getAllByRole("row")).toHaveLength(2);
  expect(within(lifecycleTable).getByText("20260905B")).toBeInTheDocument();

  await userEvent.selectOptions(screen.getByLabelText("QC status"), "all");

  await userEvent.selectOptions(screen.getByLabelText("Cloud release status"), "failed");
  expect(within(lifecycleTable).getAllByRole("row")).toHaveLength(2);
  expect(within(lifecycleTable).getByText("20260906B")).toBeInTheDocument();
  expect(within(lifecycleTable).queryByText("20260905C")).not.toBeInTheDocument();
  expect(screen.queryByText("Whole exome sequencing")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/runs?pipeline=deployed"), expect.objectContaining({credentials: "same-origin"}));
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("limit=200"), expect.objectContaining({credentials: "same-origin"}));
  expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/workflows"), expect.anything());
});
