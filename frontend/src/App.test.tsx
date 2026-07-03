import "@testing-library/jest-dom/vitest";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const runId = "PGTA_20260703_054712_501D8B";
const createdRunId = "PGTA_20260703_180000_NEW001";
const rawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";

function mockJson(payload: object, init?: ResponseInit) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: init?.status ?? 200,
      headers: {"Content-Type": "application/json"},
    }),
  );
}

describe("PGT-A run dashboard", () => {
  let createdRunStatus = "created";
  let createdDagRunId: string | null = null;

  function runListItems() {
    const items: Array<{
      analysis_id: string;
      pipeline: string;
      status: string;
      created_at: string;
      started_at: string | null;
      ended_at: string | null;
      sample_count: number;
      qc_status: string;
    }> = [
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
    ];
    if (createdRunStatus) {
      items.unshift({
        analysis_id: createdRunId,
        pipeline: "pgta",
        status: createdRunStatus,
        created_at: "2026-07-03T18:00:00+08:00",
        started_at: null,
        ended_at: null,
        sample_count: 1,
        qc_status: "unknown",
      });
    }
    return items;
  }

  beforeEach(() => {
    createdRunStatus = "";
    createdDagRunId = null;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/runs?pipeline=pgta&limit=50&offset=0")) {
          return mockJson({
            items: runListItems(),
            total: runListItems().length,
          });
        }
        if (url.endsWith("/api/input/scan") && init?.method === "POST") {
          return mockJson({
            pipeline: "pgta",
            rawdata_root: rawdataRoot,
            truncated: true,
            items: [
              {
                sample_id: "G1",
                r1: `${rawdataRoot}/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R1.fastq.gz`,
                r2: `${rawdataRoot}/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R2.fastq.gz`,
                source_dir: `${rawdataRoot}/Sample_DEMO-G1-G1`,
                r1_size: 123,
                r2_size: 124,
                r1_mtime: 1782810000.0,
                r2_mtime: 1782810001.0,
                discovery_method: "server_path_scan",
              },
              {
                sample_id: "G2",
                r1: `${rawdataRoot}/Sample_DEMO-G2-G2/DEMO-G2-G2_combined_R1.fastq.gz`,
                r2: `${rawdataRoot}/Sample_DEMO-G2-G2/DEMO-G2-G2_combined_R2.fastq.gz`,
                source_dir: `${rawdataRoot}/Sample_DEMO-G2-G2`,
                r1_size: 223,
                r2_size: 224,
                r1_mtime: 1782810100.0,
                r2_mtime: 1782810101.0,
                discovery_method: "server_path_scan",
              },
            ],
          });
        }
        if (url.endsWith("/api/runs") && init?.method === "POST") {
          createdRunStatus = "created";
          return mockJson(
            {
              analysis_id: createdRunId,
              pipeline: "pgta",
              dag_id: "bio_pgta",
              dag_run_id: null,
              status: "created",
              workdir: `/data/airflow-demo/runs/${createdRunId}`,
              sample_count: 1,
            },
            {status: 201},
          );
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
        if (url.endsWith(`/api/runs/${createdRunId}`)) {
          return mockJson({
            analysis_id: createdRunId,
            pipeline: "pgta",
            status: createdRunStatus || "created",
            mode: "new",
            dag_id: "bio_pgta",
            dag_run_id: createdDagRunId,
            airflow_url: null,
            workdir: `/data/airflow-demo/runs/${createdRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${createdRunId}/config/samples.selected.tsv`,
            params: {target: "metadata", selected_count: 1},
            error_summary: null,
            email_to: "demo@example.com",
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
        if (url.endsWith(`/api/runs/${createdRunId}/samples`)) {
          return mockJson({
            items: [
              {
                sample_id: "G1",
                fq1: `${rawdataRoot}/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R1.fastq.gz`,
                fq2: `${rawdataRoot}/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R2.fastq.gz`,
                status: "pending",
                qc_status: "unknown",
                metadata: {source_dir: `${rawdataRoot}/Sample_DEMO-G1-G1`},
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
        if (url.endsWith(`/api/runs/${createdRunId}/rules`)) {
          return mockJson({items: []});
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
        if (url.endsWith(`/api/runs/${createdRunId}/artifacts`)) {
          return mockJson({items: []});
        }
        if (url.endsWith(`/api/runs/${runId}/logs?stream=metadata&tail=200`)) {
          return mockJson({
            path: `/data/airflow-demo/runs/${runId}/logs/run_metadata.tsv`,
            stream: "metadata",
            truncated: false,
            lines: ["key\tvalue", "target\tmetadata"],
          });
        }
        if (url.endsWith(`/api/runs/${createdRunId}/logs?stream=metadata&tail=200`)) {
          return mockJson({detail: {code: "LOG_NOT_FOUND", message: "metadata log is not ready"}}, {status: 404});
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
        if (url.endsWith(`/api/runs/${createdRunId}/actions/submit`) && init?.method === "POST") {
          createdRunStatus = "submitted";
          createdDagRunId = `manual__${createdRunId}`;
          return mockJson({
            analysis_id: createdRunId,
            pipeline: "pgta",
            status: "submitted",
            dag_id: "bio_pgta",
            dag_run_id: createdDagRunId,
            workdir: `/data/airflow-demo/runs/${createdRunId}`,
            sample_count: 1,
            sample_sheet_path: `/data/airflow-demo/runs/${createdRunId}/config/samples.selected.tsv`,
            params: {target: "metadata", selected_count: 1},
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

  it("scans a server FASTQ path and renders selectable sample candidates", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.clear(await screen.findByLabelText(/rawdata root/i));
    await user.type(screen.getByLabelText(/rawdata root/i), rawdataRoot);
    await user.click(screen.getByRole("button", {name: /^scan$/i}));

    const newRunPanel = screen.getByRole("region", {name: /new pgt-a run/i});
    expect(await within(newRunPanel).findByText("G1")).toBeInTheDocument();
    expect(within(newRunPanel).getByText("G2")).toBeInTheDocument();
    expect(screen.getByText(/scan result was truncated/i)).toBeInTheDocument();

    const createButton = screen.getByRole("button", {name: /create run/i});
    expect(createButton).toBeDisabled();
    await user.click(screen.getByRole("checkbox", {name: /select sample G1/i}));
    expect(createButton).toBeEnabled();
  });

  it("creates a PGT-A run from selected server-path samples and selects the new run", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.clear(await screen.findByLabelText(/project name/i));
    await user.type(screen.getByLabelText(/project name/i), "metadata smoke");
    await user.clear(screen.getByLabelText(/rawdata root/i));
    await user.type(screen.getByLabelText(/rawdata root/i), rawdataRoot);
    await user.click(screen.getByRole("button", {name: /^scan$/i}));
    await user.click(await screen.findByRole("checkbox", {name: /select sample G1/i}));
    await user.click(screen.getByRole("button", {name: /create run/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/runs"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"project_name":"metadata smoke"'),
        }),
      );
    });
    expect(await screen.findByText(`Analysis ID: ${createdRunId}`)).toBeInTheDocument();
    expect(screen.getByText("bio_pgta")).toBeInTheDocument();
  });

  it("submits a created metadata run to Airflow and refreshes the submitted state", async () => {
    const user = userEvent.setup();
    createdRunStatus = "created";
    render(<App />);

    expect(await screen.findByText(`Analysis ID: ${createdRunId}`)).toBeInTheDocument();
    const toolbar = await screen.findByRole("toolbar", {name: /run actions/i});
    await user.click(within(toolbar).getByRole("button", {name: /submit to airflow/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${createdRunId}/actions/submit`),
        expect.objectContaining({method: "POST"}),
      );
    });
    expect(await screen.findByText(`manual__${createdRunId}`)).toBeInTheDocument();
    expect(screen.getAllByText("submitted").length).toBeGreaterThan(0);
  });
});
