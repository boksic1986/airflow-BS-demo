import "@testing-library/jest-dom/vitest";

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const runId = "PGTA_20260703_054712_501D8B";
const createdRunId = "PGTA_20260703_180000_NEW001";
const wesRunId = "WES_20260705_010000_NEW001";
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
  let createdRunTarget: "metadata" | "dryrun_cnv" | "invalid_target" = "metadata";
  let wesRunStatus = "";
  let wesDagRunId: string | null = null;

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
    if (wesRunStatus) {
      items.unshift({
        analysis_id: wesRunId,
        pipeline: "wes_qsub",
        status: wesRunStatus,
        created_at: "2026-07-05T01:00:00+08:00",
        started_at: null,
        ended_at: null,
        sample_count: 2,
        qc_status: "unknown",
      });
    }
    return items;
  }

  beforeEach(() => {
    createdRunStatus = "";
    createdDagRunId = null;
    createdRunTarget = "metadata";
    wesRunStatus = "";
    wesDagRunId = null;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/runs?pipeline=pgta&limit=50&offset=0") || url.endsWith("/api/runs?limit=50&offset=0")) {
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
          const requestBody = JSON.parse(String(init.body || "{}")) as {
            pipeline?: string;
            target?: "metadata" | "dryrun_cnv" | "invalid_target" | "final_summary";
          };
          if (requestBody.pipeline === "wes_qsub") {
            wesRunStatus = "created";
            return mockJson(
              {
                analysis_id: wesRunId,
                pipeline: "wes_qsub",
                dag_id: "bio_wes_qsub",
                dag_run_id: null,
                status: "created",
                workdir: `/data/airflow-demo/runs/${wesRunId}`,
                sample_count: 2,
              },
              {status: 201},
            );
          }
          createdRunTarget =
            requestBody.target === "dryrun_cnv" || requestBody.target === "invalid_target" ? requestBody.target : "metadata";
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
            params: {target: createdRunTarget, selected_count: 1},
            error_summary: null,
            email_to: "demo@example.com",
          });
        }
        if (url.endsWith(`/api/runs/${wesRunId}`)) {
          return mockJson({
            analysis_id: wesRunId,
            pipeline: "wes_qsub",
            status: wesRunStatus || "success",
            mode: "new",
            dag_id: "bio_wes_qsub",
            dag_run_id: wesDagRunId || `manual__${wesRunId}`,
            airflow_url: null,
            workdir: `/data/airflow-demo/runs/${wesRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${wesRunId}/config/samples.selected.tsv`,
            params: {target: "final_summary", selected_count: 2, input_mode: "mock_wes"},
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
        if (url.endsWith(`/api/runs/${wesRunId}/samples`)) {
          return mockJson({
            items: [
              {
                sample_id: "S001",
                fq1: "pipelines/wes/mock_data/S001.input.txt",
                fq2: null,
                status: "pending",
                qc_status: "unknown",
                metadata: {input_mode: "mock_wes"},
              },
              {
                sample_id: "S002",
                fq1: "pipelines/wes/mock_data/S002.input.txt",
                fq2: null,
                status: "pending",
                qc_status: "unknown",
                metadata: {input_mode: "mock_wes"},
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
        if (url.endsWith(`/api/runs/${wesRunId}/rules`)) {
          return mockJson({
            items: [
              {
                rule: "fastp",
                sample_id: "S001",
                status: "success",
                snakemake_jobid: "1",
                qsub_jobid: "MOCK-WES-fastp-S001",
                stdout_path: `/data/airflow-demo/runs/${wesRunId}/logs/qsub/fastp.S001.o`,
                stderr_path: `/data/airflow-demo/runs/${wesRunId}/logs/qsub/fastp.S001.e`,
                return_code: 0,
                wildcards: {sample: "S001"},
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
        if (url.endsWith(`/api/runs/${runId}/qc`)) {
          return mockJson({summary: {pass: 0, warn: 0, fail: 0, unknown: 0}, items: []});
        }
        if (url.endsWith(`/api/runs/${createdRunId}/artifacts`)) {
          return mockJson({items: []});
        }
        if (url.endsWith(`/api/runs/${createdRunId}/qc`)) {
          return mockJson({summary: {pass: 0, warn: 0, fail: 0, unknown: 0}, items: []});
        }
        if (url.endsWith(`/api/runs/${wesRunId}/artifacts`)) {
          return mockJson({
            items: [
              {
                key: "wes_final_summary",
                type: "wes_mock_summary",
                label: "WES mock final summary",
                path: `/data/airflow-demo/runs/${wesRunId}/reports/final_summary.tsv`,
                size_bytes: 42,
                url: `/api/runs/${wesRunId}/artifacts/wes_final_summary`,
              },
            ],
          });
        }
        if (url.endsWith(`/api/runs/${wesRunId}/qc`)) {
          return mockJson({
            summary: {pass: 6, warn: 0, fail: 0, unknown: 0},
            items: [
              {
                sample_id: "S001",
                metric_name: "workflow_status",
                metric_value: "mock_success",
                metric_numeric: null,
                threshold: "mock_success",
                status: "pass",
                source_file: `/data/airflow-demo/runs/${wesRunId}/reports/qc_summary.tsv`,
              },
              {
                sample_id: "S001",
                metric_name: "mock_mean_depth",
                metric_value: "100",
                metric_numeric: 100,
                threshold: ">=80",
                status: "pass",
                source_file: `/data/airflow-demo/runs/${wesRunId}/reports/qc_summary.tsv`,
              },
              {
                sample_id: "S002",
                metric_name: "mock_pct_20x",
                metric_value: "0.95",
                metric_numeric: 0.95,
                threshold: ">=0.90",
                status: "pass",
                source_file: `/data/airflow-demo/runs/${wesRunId}/reports/qc_summary.tsv`,
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
        if (url.endsWith(`/api/runs/${createdRunId}/logs?stream=metadata&tail=200`)) {
          return mockJson({detail: {code: "LOG_NOT_FOUND", message: "metadata log is not ready"}}, {status: 404});
        }
        if (url.endsWith(`/api/runs/${wesRunId}/logs?stream=metadata&tail=200`)) {
          return mockJson({detail: {code: "LOG_NOT_FOUND", message: "metadata log is not used for WES"}}, {status: 404});
        }
        if (url.endsWith(`/api/runs/${wesRunId}/logs?stream=stdout&tail=200`)) {
          return mockJson({
            path: `/data/airflow-demo/runs/${wesRunId}/logs/snakemake.stdout.log`,
            stream: "stdout",
            truncated: false,
            lines: ["WES mock snakemake stdout"],
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
            params: {target: createdRunTarget, selected_count: 1},
            error_summary: null,
          });
        }
        if (url.endsWith(`/api/runs/${wesRunId}/actions/submit`) && init?.method === "POST") {
          wesRunStatus = "submitted";
          wesDagRunId = `manual__${wesRunId}`;
          return mockJson({
            analysis_id: wesRunId,
            pipeline: "wes_qsub",
            status: "submitted",
            dag_id: "bio_wes_qsub",
            dag_run_id: wesDagRunId,
            workdir: `/data/airflow-demo/runs/${wesRunId}`,
            sample_count: 2,
            sample_sheet_path: `/data/airflow-demo/runs/${wesRunId}/config/samples.selected.tsv`,
            params: {target: "final_summary", selected_count: 2, input_mode: "mock_wes"},
            error_summary: null,
          });
        }
        if (url.endsWith(`/api/runs/${wesRunId}/actions/reanalyze`) && init?.method === "POST") {
          const requestBody = JSON.parse(String(init.body || "{}")) as {mode: string};
          wesRunStatus = "submitted";
          wesDagRunId = `manual__${wesRunId}__${requestBody.mode}__20260705T010500`;
          return mockJson({
            analysis_id: wesRunId,
            new_dag_run_id: wesDagRunId,
            mode: requestBody.mode,
            status: "submitted",
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

  it("creates a dryrun_cnv run when the target selector is changed", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.selectOptions(await screen.findByLabelText(/target/i), "dryrun_cnv");
    await user.click(screen.getByRole("button", {name: /^scan$/i}));
    await user.click(await screen.findByRole("checkbox", {name: /select sample G1/i}));
    await user.click(screen.getByRole("button", {name: /create run/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/runs"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"target":"dryrun_cnv"'),
        }),
      );
    });
    expect(
      await screen.findByText(
        (_, element) =>
          element?.tagName.toLowerCase() === "pre" &&
          (element.textContent?.includes('"target": "dryrun_cnv"') ?? false),
      ),
    ).toBeInTheDocument();
  });

  it("submits a created metadata run to Airflow and refreshes the submitted state", async () => {
    const user = userEvent.setup();
    createdRunStatus = "created";
    render(<App />);

    expect(await screen.findByText(`Analysis ID: ${createdRunId}`)).toBeInTheDocument();
    const toolbar = await screen.findByRole("toolbar", {name: /run actions/i});
    await user.click(await within(toolbar).findByRole("button", {name: /submit to airflow/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${createdRunId}/actions/submit`),
        expect.objectContaining({method: "POST"}),
      );
    });
    expect(await screen.findByText(`manual__${createdRunId}`)).toBeInTheDocument();
    expect(screen.getAllByText("submitted").length).toBeGreaterThan(0);
  });

  it("submits a created dryrun_cnv run to Airflow", async () => {
    const user = userEvent.setup();
    createdRunStatus = "created";
    createdRunTarget = "dryrun_cnv";
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
  });

  it("creates and submits a WES mock run from the WES panel", async () => {
    const user = userEvent.setup();
    render(<App />);

    const wesPanel = await screen.findByRole("region", {name: /new wes mock run/i});
    await user.click(within(wesPanel).getByRole("button", {name: /create and submit wes/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/runs"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"pipeline":"wes_qsub"'),
        }),
      );
    });
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${wesRunId}/actions/submit`),
        expect.objectContaining({method: "POST"}),
      );
    });
    expect(await screen.findByText(`manual__${wesRunId}`)).toBeInTheDocument();
  });

  it("renders WES QC summary and metric rows in run detail", async () => {
    wesRunStatus = "success";
    render(<App />);

    expect(await screen.findByText(`Analysis ID: ${wesRunId}`)).toBeInTheDocument();
    expect(await screen.findByRole("heading", {name: "QC"})).toBeInTheDocument();
    expect(screen.getByText("pass: 6")).toBeInTheDocument();
    expect(screen.getByText("mock_mean_depth")).toBeInTheDocument();
    expect(screen.getByText("mock_pct_20x")).toBeInTheDocument();
    expect(screen.getAllByText("pass").length).toBeGreaterThan(0);
  });

  it("triggers WES resume from run detail", async () => {
    const user = userEvent.setup();
    wesRunStatus = "success";
    render(<App />);

    expect(await screen.findByText(`Analysis ID: ${wesRunId}`)).toBeInTheDocument();
    const toolbar = await screen.findByRole("toolbar", {name: /run actions/i});
    await user.click(within(toolbar).getByRole("button", {name: /^resume$/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${wesRunId}/actions/reanalyze`),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"mode":"resume"'),
        }),
      );
    });
  });

  it("triggers WES selected rule rerun from run detail", async () => {
    const user = userEvent.setup();
    wesRunStatus = "success";
    render(<App />);

    expect(await screen.findByText(`Analysis ID: ${wesRunId}`)).toBeInTheDocument();
    const toolbar = await screen.findByRole("toolbar", {name: /run actions/i});

    await user.selectOptions(screen.getByLabelText(/rerun rule/i), "fastp");
    await user.selectOptions(screen.getByLabelText(/rerun sample/i), "S001");
    await user.click(within(toolbar).getByRole("button", {name: /rerun rule/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${wesRunId}/actions/reanalyze`),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"rule":"fastp"'),
        }),
      );
    });
  });
});
