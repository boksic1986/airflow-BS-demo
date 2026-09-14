import "@testing-library/jest-dom/vitest";

import {cleanup, fireEvent, render, screen, waitFor, within} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";

const analysisId = "GATK_SYNTHETIC_STEP7";
const batch = "MOCK_BATCH";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

function json(value: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(value), {
    status: 200, headers: {"Content-Type": "application/json"},
  }));
}

function setup(role: "admin" | "viewer") {
  window.history.pushState({}, "", `/runs/${analysisId}`);
  const mutations: Array<{url: string; body: unknown}> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") {
      mutations.push({url: new URL(url, window.location.origin).pathname, body: JSON.parse(String(init.body))});
      return json({action_id: "gatk-step7-abcdef123456", status: "queued"});
    }
    if (url.endsWith("/api/auth/me")) return json({username: role, role});
    if (url.endsWith("/api/platform/capabilities")) return json({
      environment: "Synthetic test", deployed_pipelines: ["gatk"], airflow_url: null,
      pipelines: [{id: "gatk", display_name: "GATK Cloud", dag_id: "bio_gatk",
        version: "7.6.0", enabled: true, submit_enabled: true,
        capabilities: ["submit", "rules", "artifacts"], execution_targets: ["cce"]}],
    });
    if (url.endsWith(`/api/runs/${analysisId}/workspace`)) return json({
      run: {analysis_id: analysisId, pipeline: "gatk", status: "success", attempt: 1,
        params: {batch},
        lifecycle: {
          workflow: {status: "success", updated_at: null, updated_by: null},
          cloud_release: {status: "not_started", updated_at: null, updated_by: null},
          raw_fastq_backup: {status: "not_started", updated_at: null, updated_by: null},
          downstream_release: {status: "success", updated_at: null, updated_by: null},
        },
        step7_cleanup: {available: true, reason: null, required_batch: batch, latest_action: null},
      },
      summary: {sample_count: 1, rule_count: 1, failed_rule_count: 0},
      progress: {analysis_id: analysisId, pipeline: "gatk", status: "success", percent: 100,
        current_step: "step6_materialize", current_source: "gatk-runtime", note: "",
        not_in_airflow: false, progress_source: "run-stage-state", airflow_tasks: [], rule_events: []},
      validation_issues: [], slot_usage: null,
    });
    return json({items: [], total: 0});
  }));
  return mutations;
}

it("shows GATK Step7 and submits only after the admin acknowledges the exact batch", async () => {
  const mutations = setup("admin");
  render(<App />);
  const panel = await screen.findByRole("region", {name: "Step7 SFS cleanup"});
  expect(screen.getByRole("heading", {name: "Data lifecycle"})).toBeInTheDocument();
  expect(screen.getByText("Workflow success")).toBeInTheDocument();
  fireEvent.click(within(panel).getByText("Release SFS data"));
  const submit = within(panel).getByRole("button", {name: "Run Step7 SFS cleanup"});
  expect(submit).toBeDisabled();
  fireEvent.click(within(panel).getByRole("checkbox", {name: "Acknowledge SFS cleanup"}));
  fireEvent.change(within(panel).getByLabelText("Step7 Batch confirmation"), {target: {value: "OTHER_BATCH"}});
  expect(submit).toBeDisabled();
  expect(mutations).toHaveLength(0);
  fireEvent.change(within(panel).getByLabelText("Step7 Batch confirmation"), {target: {value: batch}});
  fireEvent.click(submit);
  await waitFor(() => expect(mutations).toEqual([{
    url: `/api/runs/${analysisId}/actions/cleanup-step7`,
    body: {batch_confirmation: batch, retry_failed: false, expected_action_id: null},
  }]));
});

it("keeps GATK lifecycle visible but does not offer destructive controls to viewers", async () => {
  const mutations = setup("viewer");
  render(<App />);
  const panel = await screen.findByRole("region", {name: "Step7 SFS cleanup"});
  expect(screen.getByText("Workflow success")).toBeInTheDocument();
  expect(within(panel).queryByText("Release SFS data")).not.toBeInTheDocument();
  expect(within(panel).queryByRole("checkbox")).not.toBeInTheDocument();
  expect(mutations).toHaveLength(0);
});
