import "@testing-library/jest-dom/vitest";

import {cleanup, render, screen, waitFor, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import App from "./App";

const pgtaRunId = "PGTA_20260706_162150_00C4FD";
const failedRunId = "PGTA_20260703_170957_3DDEC3";
const wesRunId = "WES_20260705_164813_C5561C";
const createdPgtaRunId = "PGTA_20260708_100000_UI001";
const rawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";

function mockJson(payload: object, init?: ResponseInit) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: init?.status ?? 200,
      headers: {"Content-Type": "application/json"},
    }),
  );
}

function setRoute(path: string) {
  window.history.pushState({}, "", path);
}

describe("bioinformatics platform frontend", () => {
  let createdPgtaStatus = "created";
  let createdPgtaDagRunId: string | null = null;
  let wesStatus = "success";
  let wesDagRunId = `manual__${wesRunId}`;

  const runs = () => [
    {
      analysis_id: failedRunId,
      pipeline: "pgta",
      status: "failed",
      created_at: "2026-07-03T17:09:57+08:00",
      started_at: "2026-07-03T17:10:00+08:00",
      ended_at: "2026-07-03T17:11:00+08:00",
      sample_count: 1,
      qc_status: "unknown",
    },
    {
      analysis_id: pgtaRunId,
      pipeline: "pgta",
      status: "success",
      created_at: "2026-07-06T16:21:50+08:00",
      started_at: "2026-07-07T14:41:47+08:00",
      ended_at: "2026-07-07T22:53:00+08:00",
      sample_count: 2,
      qc_status: "fail",
    },
    {
      analysis_id: wesRunId,
      pipeline: "wes_qsub",
      status: wesStatus,
      created_at: "2026-07-05T16:48:13+08:00",
      started_at: "2026-07-05T16:49:00+08:00",
      ended_at: "2026-07-05T16:50:00+08:00",
      sample_count: 2,
      qc_status: "pass",
    },
    {
      analysis_id: createdPgtaRunId,
      pipeline: "pgta",
      status: createdPgtaStatus,
      created_at: "2026-07-08T10:00:00+08:00",
      started_at: null,
      ended_at: null,
      sample_count: 2,
      qc_status: "unknown",
    },
  ];

  beforeEach(() => {
    setRoute("/");
    createdPgtaStatus = "created";
    createdPgtaDagRunId = null;
    wesStatus = "success";
    wesDagRunId = `manual__${wesRunId}`;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/runs?limit=50&offset=0")) {
          return mockJson({items: runs(), total: runs().length});
        }
        if (url.endsWith("/api/health")) return mockJson({status: "ok"});
        if (url.endsWith("/api/health/db")) return mockJson({status: "ok"});
        if (url.endsWith("/api/health/airflow")) {
          return mockJson({
            status: "ok",
            airflow: {metadatabase: {status: "healthy"}, scheduler: {status: "healthy"}},
          });
        }
        if (url.endsWith("/api/input/scan") && init?.method === "POST") {
          return mockJson({
            pipeline: "pgta",
            rawdata_root: rawdataRoot,
            truncated: false,
            items: [
              {
                sample_id: "G10",
                r1: `${rawdataRoot}/Sample_G10/G10_R1.fastq.gz`,
                r2: `${rawdataRoot}/Sample_G10/G10_R2.fastq.gz`,
                source_dir: `${rawdataRoot}/Sample_G10`,
                r1_size: 100,
                r2_size: 101,
                discovery_method: "server_path_scan",
              },
              {
                sample_id: "G11",
                r1: `${rawdataRoot}/Sample_G11/G11_R1.fastq.gz`,
                r2: `${rawdataRoot}/Sample_G11/G11_R2.fastq.gz`,
                source_dir: `${rawdataRoot}/Sample_G11`,
                r1_size: 200,
                r2_size: 201,
                discovery_method: "server_path_scan",
              },
            ],
          });
        }
        if (url.endsWith("/api/runs") && init?.method === "POST") {
          const body = JSON.parse(String(init.body || "{}")) as {pipeline?: string};
          if (body.pipeline === "wes_qsub") {
            wesStatus = "created";
            return mockJson({
              analysis_id: wesRunId,
              pipeline: "wes_qsub",
              dag_id: "bio_wes_qsub",
              dag_run_id: null,
              status: "created",
              workdir: `/data/airflow-demo/runs/${wesRunId}`,
              sample_count: 2,
            });
          }
          createdPgtaStatus = "created";
          return mockJson({
            analysis_id: createdPgtaRunId,
            pipeline: "pgta",
            dag_id: "bio_pgta",
            dag_run_id: null,
            status: "created",
            workdir: `/data/airflow-demo/runs/${createdPgtaRunId}`,
            sample_count: 2,
          });
        }
        if (url.endsWith(`/api/runs/${failedRunId}`)) {
          return mockJson({
            analysis_id: failedRunId,
            pipeline: "pgta",
            status: "failed",
            mode: "new",
            dag_id: "bio_pgta",
            dag_run_id: `manual__${failedRunId}`,
            workdir: `/data/airflow-demo/runs/${failedRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${failedRunId}/config/samples.selected.tsv`,
            params: {target: "invalid_target", selected_count: 1},
            error_summary:
              '{"status":"failed","stderr_path":"/data/airflow-demo/runs/PGTA/logs/snakemake.stderr.log","last_100_lines":["MissingRuleException: No rule to produce __airflow_demo_invalid_target__"]}',
            email_to: "demo@example.com",
            created_at: "2026-07-03T17:09:57+08:00",
            started_at: "2026-07-03T17:10:00+08:00",
            ended_at: "2026-07-03T17:11:00+08:00",
          });
        }
        if (url.endsWith(`/api/runs/${pgtaRunId}`)) {
          return mockJson({
            analysis_id: pgtaRunId,
            pipeline: "pgta",
            status: "success",
            mode: "resume",
            dag_id: "bio_pgta",
            dag_run_id: `manual__${pgtaRunId}__resume__20260707T144147Z`,
            workdir: `/data/airflow-demo/runs/${pgtaRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${pgtaRunId}/config/samples.selected.tsv`,
            params: {target: "baseline_qc", selected_count: 2},
            error_summary: null,
            email_to: null,
            created_at: "2026-07-06T16:21:50+08:00",
            started_at: "2026-07-07T14:41:47+08:00",
            ended_at: "2026-07-07T22:53:00+08:00",
          });
        }
        if (url.endsWith(`/api/runs/${wesRunId}`)) {
          return mockJson({
            analysis_id: wesRunId,
            pipeline: "wes_qsub",
            status: wesStatus,
            mode: "new",
            dag_id: "bio_wes_qsub",
            dag_run_id: wesDagRunId,
            workdir: `/data/airflow-demo/runs/${wesRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${wesRunId}/config/samples.selected.tsv`,
            params: {target: "final_summary", selected_count: 2, input_mode: "mock_wes"},
            error_summary: null,
            email_to: null,
          });
        }
        if (url.endsWith(`/api/runs/${createdPgtaRunId}`)) {
          return mockJson({
            analysis_id: createdPgtaRunId,
            pipeline: "pgta",
            status: createdPgtaStatus,
            mode: "new",
            dag_id: "bio_pgta",
            dag_run_id: createdPgtaDagRunId,
            workdir: `/data/airflow-demo/runs/${createdPgtaRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${createdPgtaRunId}/config/samples.selected.tsv`,
            params: {target: "baseline_qc", selected_count: 2},
            error_summary: null,
            email_to: null,
          });
        }
        if (url.match(/\/api\/runs\/[^/]+\/samples$/)) {
          const id = url.split("/api/runs/")[1].split("/samples")[0];
          if (id === wesRunId) {
            return mockJson({
              items: [
                {sample_id: "S001", family_id: "FAM001", fq1: "pipelines/wes/mock_data/S001.input.txt", status: "success", qc_status: "pass"},
                {sample_id: "S002", family_id: "FAM001", fq1: "pipelines/wes/mock_data/S002.input.txt", status: "success", qc_status: "pass"},
              ],
            });
          }
          return mockJson({
            items: [
              {sample_id: "G10", fq1: `${rawdataRoot}/Sample_G10/G10_R1.fastq.gz`, fq2: `${rawdataRoot}/Sample_G10/G10_R2.fastq.gz`, status: id === failedRunId ? "failed" : "success", qc_status: id === pgtaRunId ? "fail" : "unknown"},
              {sample_id: "G11", fq1: `${rawdataRoot}/Sample_G11/G11_R1.fastq.gz`, fq2: `${rawdataRoot}/Sample_G11/G11_R2.fastq.gz`, status: id === failedRunId ? "failed" : "success", qc_status: id === pgtaRunId ? "fail" : "unknown"},
            ],
          });
        }
        if (url.match(/\/api\/runs\/[^/]+\/rules$/)) {
          const id = url.split("/api/runs/")[1].split("/rules")[0];
          if (id === failedRunId) {
            return mockJson({
              items: [{rule: "__airflow_demo_invalid_target__", sample_id: null, status: "failed", snakemake_jobid: "1", return_code: 1, message: "MissingRuleException"}],
            });
          }
          return mockJson({
            items: [
              {rule: "fastp", sample_id: id === wesRunId ? "S001" : null, status: "success", snakemake_jobid: "1", qsub_jobid: id === wesRunId ? "MOCK-WES-fastp-S001" : null, return_code: 0},
              {rule: id === wesRunId ? "final_summary" : "baseline_bam_uniformity_qc", sample_id: null, status: "success", snakemake_jobid: "2", return_code: 0},
            ],
          });
        }
        if (url.match(/\/api\/runs\/[^/]+\/qc$/)) {
          const id = url.split("/api/runs/")[1].split("/qc")[0];
          if (id === pgtaRunId) {
            return mockJson({
              summary: {pass: 0, warn: 0, fail: 14, unknown: 0},
              items: [{sample_id: "G10", metric_name: "baseline_qc_decision", metric_value: "FAIL", metric_numeric: null, threshold: "PASS", status: "fail"}],
            });
          }
          if (id === wesRunId) {
            return mockJson({
              summary: {pass: 6, warn: 0, fail: 0, unknown: 0},
              items: [{sample_id: "S001", metric_name: "mock_mean_depth", metric_value: "100", metric_numeric: 100, threshold: ">=80", status: "pass"}],
            });
          }
          return mockJson({summary: {pass: 0, warn: 0, fail: 0, unknown: 0}, items: []});
        }
        if (url.match(/\/api\/runs\/[^/]+\/artifacts$/)) {
          const id = url.split("/api/runs/")[1].split("/artifacts")[0];
          return mockJson({
            items: [
              {key: "snakemake_command", type: "snakemake_log", label: "Snakemake command", path: `/data/airflow-demo/runs/${id}/logs/snakemake.command.txt`, size_bytes: 256, url: `/api/runs/${id}/logs?stream=metadata`},
              {key: "qc_summary", type: "qc_tsv", label: "QC summary", path: `/data/airflow-demo/runs/${id}/reports/qc_summary.tsv`, size_bytes: 128, url: `/api/runs/${id}/artifacts/qc_summary`},
            ],
          });
        }
        if (url.includes("/logs?")) {
          const stream = new URL(url).searchParams.get("stream");
          if (url.includes(failedRunId) && stream === "stderr") {
            return mockJson({
              path: `/data/airflow-demo/runs/${failedRunId}/logs/snakemake.stderr.log`,
              stream: "stderr",
              truncated: false,
              lines: ["MissingRuleException: No rule to produce __airflow_demo_invalid_target__"],
            });
          }
          return mockJson({
            path: "/data/airflow-demo/runs/demo/logs/snakemake.stdout.log",
            stream: stream || "stdout",
            truncated: false,
            lines: ["workflow complete"],
          });
        }
        if (url.endsWith(`/api/runs/${createdPgtaRunId}/actions/submit`) && init?.method === "POST") {
          createdPgtaStatus = "submitted";
          createdPgtaDagRunId = `manual__${createdPgtaRunId}`;
          return mockJson({analysis_id: createdPgtaRunId, pipeline: "pgta", status: "submitted", dag_id: "bio_pgta", dag_run_id: createdPgtaDagRunId, sample_count: 2});
        }
        if (url.endsWith(`/api/runs/${wesRunId}/actions/submit`) && init?.method === "POST") {
          wesStatus = "submitted";
          wesDagRunId = `manual__${wesRunId}__new`;
          return mockJson({analysis_id: wesRunId, pipeline: "wes_qsub", status: "submitted", dag_id: "bio_wes_qsub", dag_run_id: wesDagRunId, sample_count: 2});
        }
        if (url.endsWith(`/api/runs/${wesRunId}/actions/reanalyze`) && init?.method === "POST") {
          wesStatus = "submitted";
          wesDagRunId = `manual__${wesRunId}__rerun_rule`;
          return mockJson({analysis_id: wesRunId, new_dag_run_id: wesDagRunId, mode: "rerun_rule", status: "submitted"});
        }
        if (url.match(/\/api\/runs\/[^/]+\/actions\/sync-airflow$/) && init?.method === "POST") {
          return mockJson({status: "success"});
        }
        return mockJson({detail: {code: "NOT_MOCKED", message: url}}, {status: 404});
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders a PGT-A-only routed app shell dashboard with platform status", async () => {
    render(<App />);

    expect(await screen.findByRole("navigation", {name: /primary navigation/i})).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /dashboard/i})).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByRole("link", {name: /workflows/i})).not.toBeInTheDocument();
    expect(screen.getByText(/Demo environment/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/Failed runs/i)).length).toBeGreaterThan(0);
    expect(screen.getByText(failedRunId)).toBeInTheDocument();
    expect(screen.getByText(/Airflow scheduler/i)).toBeInTheDocument();
    expect(screen.getByText(/PGT-A resource overview/i)).toBeInTheDocument();
    expect(screen.queryByText(wesRunId)).not.toBeInTheDocument();
    expect(screen.queryByText(/WES qsub/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/NIPT/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/WGS/i)).not.toBeInTheDocument();
  });

  it("shows only PGT-A runs in the run table without hiding status text", async () => {
    const user = userEvent.setup();
    setRoute("/runs");
    render(<App />);

    expect(await screen.findByRole("heading", {name: /runs/i})).toBeInTheDocument();
    const pipelineSelect = screen.getByLabelText(/pipeline/i);
    expect(pipelineSelect).toHaveValue("pgta");
    expect(within(pipelineSelect).queryByRole("option", {name: /^WES/i})).not.toBeInTheDocument();
    expect(within(pipelineSelect).queryByRole("option", {name: /^NIPT/i})).not.toBeInTheDocument();
    expect(within(pipelineSelect).queryByRole("option", {name: /^WGS/i})).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/status/i), "failed");
    expect(screen.getByText(failedRunId)).toBeInTheDocument();
    expect(screen.getAllByText(/failed/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(wesRunId)).not.toBeInTheDocument();
  });

  it("opens failed run detail with stderr diagnostics and searchable logs", async () => {
    const user = userEvent.setup();
    setRoute(`/runs/${failedRunId}`);
    render(<App />);

    expect(await screen.findByText(failedRunId)).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: /failure diagnosis/i})).toBeInTheDocument();
    expect(screen.getAllByText(/MissingRuleException/i).length).toBeGreaterThan(0);

    const logsTab = screen.getByRole("tab", {name: /logs/i});
    await user.click(logsTab);
    expect(await screen.findByRole("tab", {name: /stderr/i})).toHaveAttribute("aria-selected", "true");
    await user.type(screen.getByLabelText(/search logs/i), "MissingRule");
    expect(screen.getByText(/1 matching line/i)).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /copy visible log excerpt/i})).toBeInTheDocument();
  });

  it("keeps the existing PGT-A scan, create, and submit flow as the only submit path", async () => {
    const user = userEvent.setup();
    setRoute("/submit");
    render(<App />);

    expect(await screen.findByRole("heading", {name: /submit task/i})).toBeInTheDocument();
    expect(screen.queryByRole("radio", {name: /wes/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", {name: /wgs/i})).not.toBeInTheDocument();
    expect(screen.queryByText(/sample sheet text/i)).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText(/rawdata root/i));
    await user.type(screen.getByLabelText(/rawdata root/i), rawdataRoot);
    await user.selectOptions(screen.getByRole("combobox", {name: /^target$/i}), "baseline_qc");
    await user.click(screen.getByRole("button", {name: /^scan$/i}));
    await user.click(await screen.findByRole("checkbox", {name: /select sample G10/i}));
    await user.click(screen.getByRole("checkbox", {name: /select sample G11/i}));
    await user.click(screen.getByRole("button", {name: /create run/i}));

    expect(await screen.findByText(createdPgtaRunId)).toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: /submit to airflow/i}));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${createdPgtaRunId}/actions/submit`),
        expect.objectContaining({method: "POST"}),
      );
    });
  });

  it("shows only PGT-A workflow, samples, and failure resources", async () => {
    const user = userEvent.setup();
    render(<App />);

    setRoute("/workflows");
    cleanup();
    render(<App />);
    expect((await screen.findAllByText(/PGT-A/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/WES qsub/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/NIPT docker/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/WGS/i)).not.toBeInTheDocument();

    cleanup();
    setRoute("/samples");
    render(<App />);
    expect((await screen.findAllByText(/^G10$/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/S001/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/NIPT-DEMO/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", {name: /failures/i}));
    expect(await screen.findByText(/Recent failed runs/i)).toBeInTheDocument();
    expect(screen.getAllByText(/retry suggestion/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(wesRunId)).not.toBeInTheDocument();
  });
});
