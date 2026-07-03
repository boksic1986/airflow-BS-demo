import "@testing-library/jest-dom/vitest";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const runId = "PGTA_20260703_054712_501D8B";

function mockJson(payload: object, init?: ResponseInit) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: init?.status ?? 200,
      headers: {"Content-Type": "application/json"},
    }),
  );
}

describe("PGT-A run dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/runs?pipeline=pgta&limit=50&offset=0")) {
          return mockJson({
            items: [
              {
                analysis_id: runId,
                pipeline: "pgta",
                status: "success",
                created_at: "2026-07-03T05:47:12+08:00",
                started_at: "2026-07-03T05:48:00+08:00",
                ended_at: "2026-07-03T05:49:00+08:00",
                sample_count: 2,
                qc_status: "unknown",
              },
            ],
            total: 1,
          });
        }
        if (url.endsWith(`/api/runs/${runId}`)) {
          return mockJson({
            analysis_id: runId,
            pipeline: "pgta",
            status: "success",
            mode: "new",
            dag_id: "bio_pgta_airflow",
            dag_run_id: `manual__${runId}_events`,
            airflow_url: null,
            workdir: `/data/airflow-demo/runs/${runId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${runId}/config/samples.selected.tsv`,
            params: {target: "metadata", selected_count: 2},
            error_summary: null,
            email_to: null,
          });
        }
        if (url.endsWith(`/api/runs/${runId}/samples`)) {
          return mockJson({
            items: [
              {
                sample_id: "G1",
                fq1: "/data/project/CNV/PGT-A/rawdata/G1_R1.fastq.gz",
                fq2: "/data/project/CNV/PGT-A/rawdata/G1_R2.fastq.gz",
                status: "pending",
                qc_status: "unknown",
                metadata: {source_dir: "/data/project/CNV/PGT-A/rawdata/G1"},
              },
            ],
          });
        }
        if (url.endsWith(`/api/runs/${runId}/rules`)) {
          return mockJson({
            items: [
              {
                rule: "all",
                sample_id: null,
                status: "success",
                snakemake_jobid: "0",
                qsub_jobid: null,
                stdout_path: null,
                stderr_path: null,
                start_time: "2026-07-03T05:48:00",
                end_time: "2026-07-03T05:49:00",
                message: "finished",
                return_code: 0,
                wildcards: {},
              },
              {
                rule: "collect_run_metadata",
                sample_id: null,
                status: "success",
                snakemake_jobid: "1",
                qsub_jobid: null,
                stdout_path: null,
                stderr_path: null,
                start_time: "2026-07-03T05:48:10",
                end_time: "2026-07-03T05:48:20",
                message: "finished",
                return_code: 0,
                wildcards: {},
              },
            ],
          });
        }
        if (url.endsWith(`/api/runs/${runId}/artifacts`)) {
          return mockJson({
            items: [
              {
                key: "run_metadata",
                type: "pgta_metadata",
                label: "PGT-A run metadata",
                path: `/data/airflow-demo/runs/${runId}/logs/run_metadata.tsv`,
                size_bytes: 128,
                url: `/api/runs/${runId}/logs?stream=metadata`,
              },
            ],
          });
        }
        if (url.endsWith(`/api/runs/${runId}/logs?stream=metadata&tail=200`)) {
          return mockJson({
            path: `/data/airflow-demo/runs/${runId}/logs/run_metadata.tsv`,
            stream: "metadata",
            truncated: false,
            lines: ["key\tvalue", "target\tmetadata"],
          });
        }
        if (url.endsWith(`/api/runs/${runId}/actions/sync-airflow`) && init?.method === "POST") {
          return mockJson({
            analysis_id: runId,
            pipeline: "pgta",
            status: "success",
            dag_id: "bio_pgta_airflow",
            dag_run_id: `manual__${runId}_events`,
            workdir: `/data/airflow-demo/runs/${runId}`,
            error_summary: null,
          });
        }
        return mockJson({detail: {code: "NOT_MOCKED", message: url}}, {status: 404});
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the selected PGT-A run with samples, rules, logs, and artifacts", async () => {
    render(<App />);

    expect(await screen.findByText(runId)).toBeInTheDocument();
    expect(await screen.findByText("bio_pgta_airflow")).toBeInTheDocument();
    expect(screen.getByText("G1")).toBeInTheDocument();
    expect(screen.getByText("collect_run_metadata")).toBeInTheDocument();
    expect(screen.getByText("PGT-A run metadata")).toBeInTheDocument();
    expect(await screen.findByText((_, element) => element?.textContent === "key\tvalue")).toBeInTheDocument();
  });

  it("syncs Airflow status from the run detail toolbar", async () => {
    render(<App />);

    const toolbar = await screen.findByRole("toolbar", {name: /run actions/i});
    await userEvent.click(within(toolbar).getByRole("button", {name: /sync airflow/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${runId}/actions/sync-airflow`),
        expect.objectContaining({method: "POST"}),
      );
    });
  });
});
