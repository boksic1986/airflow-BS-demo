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
    return Promise.resolve(new Response(JSON.stringify({items: [
      {id: "wgs", display_name: "Whole genome sequencing", dag_id: "bio_wgs", version: "4.1.1", enabled: true, submit_enabled: true, capabilities: ["submit", "qc"], execution_targets: ["cce", "local"]},
      {id: "wes", display_name: "Whole exome sequencing", dag_id: "bio_wes", version: null, enabled: false, submit_enabled: false, capabilities: ["submit"], execution_targets: ["local"]},
    ]}), {status: 200, headers: {"Content-Type": "application/json"}}));
  }));

  render(<PlatformCapabilitiesProvider><MemoryRouter><WorkflowsPage /></MemoryRouter></PlatformCapabilitiesProvider>);

  await waitFor(() => expect(screen.getByText("Whole genome sequencing")).toBeInTheDocument());
  expect(screen.getByText("cce, local")).toBeInTheDocument();
  expect(screen.queryByText("Whole exome sequencing")).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/workflows"), expect.objectContaining({credentials: "same-origin"}));
});
