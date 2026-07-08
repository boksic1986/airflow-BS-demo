import "@testing-library/jest-dom/vitest";

import {cleanup, render, screen, waitFor, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import App from "./App";

const pgtaRunId = "PGTA_20260706_162150_00C4FD";
const failedRunId = "PGTA_20260703_170957_3DDEC3";
const wesRunId = "WES_20260705_164813_C5561C";
const niptRunId = "NIPT_20260708_120000_UI001";
const createdPgtaRunId = "PGTA_20260708_100000_UI001";
const activePgtaRunId = "PGTA_20260708_103000_ACTIVE";
const rawdataRoot = "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28";
const niptRoot = "/opt/pipelines/NIPT/fastq";
const niptBatchRoot = `${niptRoot}/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2`;

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
  let niptStatus = "created";
  let niptDagRunId: string | null = null;

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
      analysis_id: niptRunId,
      pipeline: "nipt_docker",
      status: niptStatus,
      created_at: "2026-07-08T12:00:00+08:00",
      started_at: null,
      ended_at: null,
      sample_count: 96,
      qc_status: "unknown",
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
    {
      analysis_id: activePgtaRunId,
      pipeline: "pgta",
      status: "running",
      created_at: "2026-07-08T10:30:00+08:00",
      started_at: "2026-07-08T10:31:00+08:00",
      ended_at: null,
      sample_count: 2,
      qc_status: "unknown",
    },
  ];

  const dashboardRows = () => [
    {
      analysis_id: activePgtaRunId,
      project_name: "Fresh transfer 2-sample QC",
      pipeline: "pgta",
      status: "running",
      qc_status: "unknown",
      sample_count: 2,
      created_at: "2026-07-08T10:30:00+08:00",
      started_at: "2026-07-08T10:31:00+08:00",
      ended_at: null,
      dag_id: "bio_pgta",
      dag_run_id: `manual__${activePgtaRunId}`,
      percent: 52,
      current_airflow_task: "run_pgta_target",
      current_pipeline_rule: "baseline_bam_uniformity_qc",
      progress_source: "snakemake_events",
      not_in_airflow: false,
      note: "Airflow task run_pgta_target; pipeline rule events captured",
    },
    {
      analysis_id: failedRunId,
      project_name: "PGT-A failed smoke",
      pipeline: "pgta",
      status: "failed",
      qc_status: "unknown",
      sample_count: 1,
      created_at: "2026-07-03T17:09:57+08:00",
      started_at: "2026-07-03T17:10:00+08:00",
      ended_at: "2026-07-03T17:11:00+08:00",
      dag_id: "bio_pgta",
      dag_run_id: `manual__${failedRunId}`,
      percent: 50,
      current_airflow_task: "run_pgta_target",
      current_pipeline_rule: "__airflow_demo_invalid_target__",
      progress_source: "snakemake_events",
      not_in_airflow: false,
      note: "Pipeline rule failed",
    },
    {
      analysis_id: createdPgtaRunId,
      project_name: "Created only PGT-A",
      pipeline: "pgta",
      status: "created",
      qc_status: "unknown",
      sample_count: 2,
      created_at: "2026-07-08T10:00:00+08:00",
      started_at: null,
      ended_at: null,
      dag_id: "bio_pgta",
      dag_run_id: null,
      percent: 0,
      current_airflow_task: null,
      current_pipeline_rule: null,
      progress_source: "estimate",
      not_in_airflow: true,
      note: "Created in backend only",
    },
    {
      analysis_id: niptRunId,
      project_name: "NIPT scanned batch mount smoke",
      pipeline: "nipt_docker",
      status: niptStatus,
      qc_status: "unknown",
      sample_count: 96,
      created_at: "2026-07-08T12:00:00+08:00",
      started_at: null,
      ended_at: null,
      dag_id: "bio_nipt_docker",
      dag_run_id: niptDagRunId,
      percent: niptStatus === "created" ? 0 : 100,
      current_airflow_task: niptStatus === "created" ? null : "run_nipt_docker",
      current_pipeline_rule: niptStatus === "created" ? null : "nipt_mount_smoke",
      progress_source: niptStatus === "created" ? "estimate" : "snakemake_events",
      not_in_airflow: niptStatus === "created",
      note: niptStatus === "created" ? "Created in backend only" : "Airflow task run_nipt_docker; pipeline event captured",
    },
    ...Array.from({length: 8}, (_, index) => ({
      analysis_id: `PGTA_PAGE_${index + 1}`,
      project_name: `Paged PGT-A ${index + 1}`,
      pipeline: "pgta",
      status: "success",
      qc_status: "pass",
      sample_count: 1,
      created_at: `2026-07-08T09:${String(index).padStart(2, "0")}:00+08:00`,
      started_at: `2026-07-08T09:${String(index).padStart(2, "0")}:01+08:00`,
      ended_at: `2026-07-08T09:${String(index).padStart(2, "0")}:10+08:00`,
      dag_id: "bio_pgta",
      dag_run_id: `manual__PGTA_PAGE_${index + 1}`,
      percent: 100,
      current_airflow_task: "collect_pgta_artifact",
      current_pipeline_rule: "metadata",
      progress_source: "snakemake_events",
      not_in_airflow: false,
      note: "Airflow success",
    })),
  ];

  const dashboardOverview = (pipeline = "all") => ({
    pipeline,
    period: "7d",
    totals: {runs: pipeline === "nipt_docker" ? 1 : 12, running: pipeline === "nipt_docker" ? 0 : 1, failed: pipeline === "nipt_docker" ? 0 : 1, success: pipeline === "nipt_docker" ? 0 : 8, created: pipeline === "nipt_docker" ? 1 : 2},
    status_distribution: {created: pipeline === "nipt_docker" ? 1 : 2, submitted: 0, queued: 0, running: pipeline === "nipt_docker" ? 0 : 1, success: pipeline === "nipt_docker" ? 0 : 8, failed: pipeline === "nipt_docker" ? 0 : 1, other: 0},
    pipeline_breakdown: {
      pgta: {runs: pipeline === "nipt_docker" ? 0 : 11, running: 1, failed: 1, success: 8},
      nipt_docker: {runs: 1, running: 0, failed: 0, success: 0},
    },
    trend: [
      {date: "2026-07-06", runs: 2, success: 1, failed: 0},
      {date: "2026-07-07", runs: 3, success: 2, failed: 1},
      {date: "2026-07-08", runs: 7, success: 5, failed: 0},
    ],
    qc_summary: {pass: 8, warn: 0, fail: 1, unknown: 3},
    failure_summary: [{analysis_id: failedRunId, pipeline: "pgta", project_name: "PGT-A failed smoke", status: "failed", error_summary: "MissingRuleException", created_at: "2026-07-03T17:09:57+08:00"}],
    intake_summary: {observed: 1, ready: 0, submitted: 1, bootstrap: 1, error: 0, disabled: 0},
  });

  const systemResources = () => ({
    source: "host_proc_docker_stats",
    host: {
      cpu: {cores: 128, load_average: [3.4, 3.1, 2.8]},
      memory: {total_bytes: 1024 * 1024 * 1024 * 1024, available_bytes: 900 * 1024 * 1024 * 1024, used_bytes: 124 * 1024 * 1024 * 1024, used_percent: 12.1},
      disks: [{path: "/data", total_bytes: 1000, used_bytes: 570, free_bytes: 430, used_percent: 57}],
    },
    containers: [{name: "airflow-demo-backend-1", cpu_percent: "0.13%", memory_usage: "131MiB / 1.3TiB", block_io: "1.5MB / 0B"}],
  });

  beforeEach(() => {
    setRoute("/");
    createdPgtaStatus = "created";
    createdPgtaDagRunId = null;
    wesStatus = "success";
    wesDagRunId = `manual__${wesRunId}`;
    niptStatus = "created";
    niptDagRunId = null;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/dashboard/overview")) {
          const pipeline = new URL(url).searchParams.get("pipeline") || "all";
          return mockJson(dashboardOverview(pipeline));
        }
        if (url.includes("/api/dashboard/runs")) {
          const parsed = new URL(url);
          const pipeline = parsed.searchParams.get("pipeline") || "all";
          const status = parsed.searchParams.get("status") || "";
          const keyword = (parsed.searchParams.get("keyword") || "").toLowerCase();
          const limit = Number(parsed.searchParams.get("limit") || "10");
          const offset = Number(parsed.searchParams.get("offset") || "0");
          let items = dashboardRows();
          if (pipeline !== "all") items = items.filter((item) => item.pipeline === pipeline);
          if (status) {
            if (status === "active") items = items.filter((item) => ["running", "submitted", "queued", "scheduled"].includes(item.status));
            else if (status === "failed") items = items.filter((item) => item.status === "failed");
            else items = items.filter((item) => item.status === status);
          }
          if (keyword) items = items.filter((item) => `${item.analysis_id} ${item.project_name}`.toLowerCase().includes(keyword));
          return mockJson({items: items.slice(offset, offset + limit), total: items.length, limit, offset, pipeline});
        }
        if (url.endsWith("/api/system/resources")) return mockJson(systemResources());
        if (url.endsWith("/api/runs?limit=50&offset=0") || url.endsWith("/api/runs?pipeline=pgta&limit=50&offset=0")) {
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
        if (url.includes("/api/intake/status")) {
          return mockJson({
            items: [
              {
                pipeline: "pgta",
                root_path: rawdataRoot,
                batch_id: "Sample_G10",
                fingerprint: "pgta-fingerprint",
                file_count: 2,
                total_bytes: 201,
                ready_state: "observed",
                analysis_id: null,
                submit_state: "bootstrap",
                last_seen_at: "2026-07-08T10:00:00+08:00",
              },
              {
                pipeline: "nipt_docker",
                root_path: niptRoot,
                batch_id: "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
                fingerprint: "nipt-fingerprint",
                file_count: 4,
                total_bytes: 402,
                ready_state: "ready",
                analysis_id: niptRunId,
                submit_state: "submitted",
                last_seen_at: "2026-07-08T10:05:00+08:00",
              },
            ],
          });
        }
        if (url.endsWith("/api/intake/scan-preview") && init?.method === "POST") {
          return mockJson({
            summary: {
              total_batches: 2,
              new_observed: 0,
              stable_ready: 1,
              bootstrap_protected: 1,
              would_create: 0,
              would_submit: 0,
              blocked_auto_submit: 1,
              errors: 0,
            },
            items: [
              {
                pipeline: "pgta",
                root_path: rawdataRoot,
                batch_id: "Sample_G10",
                source_dir: `${rawdataRoot}/Sample_G10`,
                fingerprint: "pgta-fingerprint",
                file_count: 2,
                total_bytes: 201,
                max_mtime: "2026-07-08T10:00:00+08:00",
                existing_ready_state: "observed",
                existing_submit_state: "bootstrap",
                existing_analysis_id: null,
                would_transition_to: "observed",
                would_create_run: false,
                would_submit: false,
                auto_submit_enabled: false,
                reason: "bootstrap_protected",
              },
              {
                pipeline: "nipt_docker",
                root_path: niptRoot,
                batch_id: "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
                source_dir: niptBatchRoot,
                fingerprint: "nipt-fingerprint",
                file_count: 4,
                total_bytes: 402,
                max_mtime: "2026-07-08T10:05:00+08:00",
                existing_ready_state: "observed",
                existing_submit_state: "not_submitted",
                existing_analysis_id: null,
                would_transition_to: "ready",
                would_create_run: false,
                would_submit: false,
                auto_submit_enabled: false,
                reason: "auto_submit_disabled",
              },
            ],
          });
        }
        if (url.endsWith("/api/intake/config")) {
          return mockJson({
            source: "/app/config/intake.yaml",
            defaults: {ready_rule: "stable_fingerprint", stable_scans: 2, auto_submit: false},
            pipelines: {
              pgta: {
                enabled: true,
                roots: [{id: "pgta_rawdata", container_path: rawdataRoot}],
                auto_submit: {enabled: false, pipeline_enabled: false, target: "metadata"},
              },
              nipt_docker: {
                enabled: true,
                roots: [{id: "nipt_fastq", container_path: niptRoot}],
                file_flavor: "clean_fastq",
                r1_pattern: "*.R1.clean.fastq.gz",
                r2_pattern: "*.R2.clean.fastq.gz",
                ignore_patterns: ["002/*.adapter.fastq.gz"],
                auto_submit: {enabled: false, pipeline_enabled: false, run_mode: "mount_smoke"},
              },
            },
          });
        }
        if (url.endsWith("/api/intake/scanner-state")) {
          return mockJson({
            dag_id: "bio_intake_scan",
            airflow_reachable: true,
            is_paused: true,
            latest_dag_run_id: "scheduled__2026-07-08T17:00:00+08:00",
            latest_dag_run_state: "success",
            latest_start_date: "2026-07-08T17:00:01+08:00",
            latest_end_date: "2026-07-08T17:00:05+08:00",
            message: null,
          });
        }
        if (url.includes("/api/input/roots")) {
          const pipeline = new URL(url).searchParams.get("pipeline");
          return mockJson({pipeline, roots: pipeline === "nipt_docker" ? [niptRoot] : [rawdataRoot]});
        }
        if (url.endsWith("/api/input/scan") && init?.method === "POST") {
          const body = JSON.parse(String(init.body || "{}")) as {pipeline?: string};
          if (body.pipeline === "nipt_docker") {
            return mockJson({
              pipeline: "nipt_docker",
              rawdata_root: niptRoot,
              truncated: false,
              items: [
                {
                  sample_id: "NIPT26040207.A06",
                  r1: `${niptBatchRoot}/NIPT26040207.A06.R1.clean.fastq.gz`,
                  r2: `${niptBatchRoot}/NIPT26040207.A06.R2.clean.fastq.gz`,
                  source_dir: niptBatchRoot,
                  r1_size: 100,
                  r2_size: 101,
                  discovery_method: "nipt_docker_clean_scan",
                },
                {
                  sample_id: "NIPT26040208.A07",
                  r1: `${niptBatchRoot}/NIPT26040208.A07.R1.clean.fastq.gz`,
                  r2: `${niptBatchRoot}/NIPT26040208.A07.R2.clean.fastq.gz`,
                  source_dir: niptBatchRoot,
                  r1_size: 100,
                  r2_size: 101,
                  discovery_method: "nipt_docker_clean_scan",
                },
              ],
            });
          }
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
          if (body.pipeline === "nipt_docker") {
            niptStatus = "created";
            return mockJson({
              analysis_id: niptRunId,
              pipeline: "nipt_docker",
              dag_id: "bio_nipt_docker",
              dag_run_id: null,
              status: "created",
              workdir: `/data/airflow-demo/runs/${niptRunId}`,
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
        if (url.endsWith(`/api/runs/${activePgtaRunId}`)) {
          return mockJson({
            analysis_id: activePgtaRunId,
            pipeline: "pgta",
            status: "running",
            mode: "new",
            dag_id: "bio_pgta",
            dag_run_id: `manual__${activePgtaRunId}`,
            workdir: `/data/airflow-demo/runs/${activePgtaRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${activePgtaRunId}/config/samples.selected.tsv`,
            params: {project_name: "Fresh transfer 2-sample QC", target: "metadata", selected_count: 2},
            error_summary: null,
            email_to: null,
            created_at: "2026-07-08T10:30:00+08:00",
            started_at: "2026-07-08T10:31:00+08:00",
            ended_at: null,
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
        if (url.endsWith(`/api/runs/${niptRunId}`)) {
          return mockJson({
            analysis_id: niptRunId,
            pipeline: "nipt_docker",
            status: niptStatus,
            mode: "new",
            dag_id: "bio_nipt_docker",
            dag_run_id: niptDagRunId,
            workdir: `/data/airflow-demo/runs/${niptRunId}`,
            sample_sheet_path: `/data/airflow-demo/runs/${niptRunId}/config/samples.selected.tsv`,
            params: {
              project_name: "NIPT scanned batch mount smoke",
              input_mode: "nipt_docker_scan",
              source_batch_dir: niptBatchRoot,
              run_mode: "mount_smoke",
              selected_count: 2,
              chip_name: "260414_TPNB500380AR_1065_AH32CCBGY2",
            },
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
        if (url.match(/\/api\/runs\/[^/]+\/progress$/)) {
          const id = url.split("/api/runs/")[1].split("/progress")[0];
          const baseTasks = [
            {task_id: "validate_request", state: "success", start_date: "2026-07-08T10:30:00+08:00", end_date: "2026-07-08T10:30:01+08:00", duration: 1, try_number: 1, operator: "PythonOperator"},
            {task_id: id === niptRunId ? "prepare_nipt_docker_run" : "prepare_pgta_config", state: "success", start_date: "2026-07-08T10:30:01+08:00", end_date: "2026-07-08T10:30:02+08:00", duration: 1, try_number: 1, operator: "PythonOperator"},
          ];
          if (id === activePgtaRunId) {
            return mockJson({
              analysis_id: id,
              pipeline: "pgta",
              status: "running",
              dag_id: "bio_pgta",
              dag_run_id: `manual__${id}`,
              percent: 52,
              current_step: "baseline_bam_uniformity_qc",
              current_source: "snakemake_events",
              note: "Airflow task run_pgta_target; pipeline rule running",
              not_in_airflow: false,
              progress_source: "snakemake_events",
              airflow_tasks: [...baseTasks, {task_id: "run_pgta_target", state: "running", start_date: "2026-07-08T10:30:02+08:00", end_date: null, duration: null, try_number: 1, operator: "PythonOperator"}],
              rule_events: [
                {rule: "fastp", sample_id: "G10", status: "success", snakemake_jobid: "1", return_code: 0},
                {rule: "baseline_bam_uniformity_qc", sample_id: "G11", status: "running", snakemake_jobid: "2", return_code: null},
              ],
            });
          }
          if (id === niptRunId) {
            const visibleStatus = niptStatus;
            return mockJson({
              analysis_id: id,
              pipeline: "nipt_docker",
              status: visibleStatus,
              dag_id: "bio_nipt_docker",
              dag_run_id: niptDagRunId,
              percent: visibleStatus === "success" ? 100 : visibleStatus === "created" ? 0 : 15,
              current_step: visibleStatus === "created" ? "Created only" : "nipt_mount_smoke",
              current_source: visibleStatus === "created" ? "backend" : "snakemake_events",
              note: visibleStatus === "created" ? "Created in backend only" : "Airflow task run_nipt_docker; pipeline smoke step",
              not_in_airflow: visibleStatus === "created",
              progress_source: visibleStatus === "created" ? "estimate" : "snakemake_events",
              airflow_tasks: visibleStatus === "created" ? [] : [...baseTasks, {task_id: "run_nipt_docker", state: "success", start_date: "2026-07-08T12:00:02+08:00", end_date: "2026-07-08T12:00:12+08:00", duration: 10, try_number: 1, operator: "PythonOperator"}],
              rule_events: visibleStatus === "created" ? [] : [{rule: "nipt_mount_smoke", sample_id: null, status: "success", snakemake_jobid: null, return_code: 0}],
            });
          }
          if (id === createdPgtaRunId && createdPgtaStatus === "created") {
            return mockJson({
              analysis_id: id,
              pipeline: "pgta",
              status: "created",
              dag_id: "bio_pgta",
              dag_run_id: null,
              percent: 0,
              current_step: "Created only",
              current_source: "backend",
              note: "Created in backend only",
              not_in_airflow: true,
              progress_source: "estimate",
              airflow_tasks: [],
              rule_events: [],
            });
          }
          return mockJson({
            analysis_id: id,
            pipeline: id === wesRunId ? "wes_qsub" : "pgta",
            status: id === failedRunId ? "failed" : "success",
            dag_id: id === failedRunId ? "bio_pgta" : "bio_pgta",
            dag_run_id: `manual__${id}`,
            percent: id === failedRunId ? 50 : 100,
            current_step: id === failedRunId ? "__airflow_demo_invalid_target__" : "Workflow complete",
            current_source: id === failedRunId ? "snakemake_events" : "airflow_task_instances",
            note: id === failedRunId ? "Pipeline rule failed" : "Airflow success",
            not_in_airflow: false,
            progress_source: id === failedRunId ? "snakemake_events" : "airflow_task_instances",
            airflow_tasks: baseTasks,
            rule_events: [],
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
          if (id === niptRunId) {
            return mockJson({
              items: [
                {
                  sample_id: "NIPT26040207.A06",
                  family_id: null,
                  fq1: `${niptBatchRoot}/NIPT26040207.A06.R1.clean.fastq.gz`,
                  fq2: `${niptBatchRoot}/NIPT26040207.A06.R2.clean.fastq.gz`,
                  status: niptStatus === "success" ? "success" : "pending",
                  qc_status: "unknown",
                  metadata: {input_mode: "nipt_docker_scan", source_dir: niptBatchRoot},
                },
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
          if (id === activePgtaRunId) {
            return mockJson({
              items: [
                {rule: "validate_request", sample_id: null, status: "success", snakemake_jobid: "1", return_code: 0},
                {rule: "prepare_pgta_config", sample_id: null, status: "success", snakemake_jobid: "2", return_code: 0},
                {rule: "run_pgta_target", sample_id: null, status: "running", snakemake_jobid: "3", return_code: null},
              ],
            });
          }
          if (id === niptRunId) {
            return mockJson({
              items: [
                {rule: "validate_request", sample_id: null, status: niptStatus === "created" ? "planned" : "success", snakemake_jobid: "1", return_code: 0},
                {rule: "run_nipt_docker", sample_id: null, status: niptStatus === "running" ? "running" : "planned", snakemake_jobid: "2", return_code: null},
              ],
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
          if (id === niptRunId) {
            return mockJson({
              summary: {pass: niptStatus === "success" ? 1 : 0, warn: 0, fail: 0, unknown: 0},
              items: niptStatus === "success" ? [{sample_id: "NC-20260414.A01", metric_name: "nipt_mount_smoke", metric_value: "pass", metric_numeric: null, threshold: "image/mount/config readable", status: "pass"}] : [],
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
        if (url.endsWith(`/api/runs/${niptRunId}/actions/submit`) && init?.method === "POST") {
          niptStatus = "submitted";
          niptDagRunId = `manual__${niptRunId}`;
          return mockJson({analysis_id: niptRunId, pipeline: "nipt_docker", status: "submitted", dag_id: "bio_nipt_docker", dag_run_id: niptDagRunId, sample_count: 96});
        }
        if (url.endsWith(`/api/runs/${wesRunId}/actions/reanalyze`) && init?.method === "POST") {
          wesStatus = "submitted";
          wesDagRunId = `manual__${wesRunId}__rerun_rule`;
          return mockJson({analysis_id: wesRunId, new_dag_run_id: wesDagRunId, mode: "rerun_rule", status: "submitted"});
        }
        if (url.match(/\/api\/runs\/[^/]+\/actions\/sync-airflow$/) && init?.method === "POST") {
          const id = url.split("/api/runs/")[1].split("/actions/sync-airflow")[0];
          if (id === createdPgtaRunId) {
            createdPgtaStatus = "success";
            return mockJson({
              analysis_id: createdPgtaRunId,
              pipeline: "pgta",
              status: "success",
              dag_id: "bio_pgta",
              dag_run_id: createdPgtaDagRunId,
              sample_count: 2,
              started_at: "2026-07-08T10:00:02+08:00",
              ended_at: "2026-07-08T10:00:12+08:00",
            });
          }
          if (id === niptRunId) {
            niptStatus = "success";
            return mockJson({
              analysis_id: niptRunId,
              pipeline: "nipt_docker",
              status: "success",
              dag_id: "bio_nipt_docker",
              dag_run_id: niptDagRunId,
              sample_count: 96,
              started_at: "2026-07-08T12:00:02+08:00",
              ended_at: "2026-07-08T12:00:12+08:00",
            });
          }
          return mockJson({status: "success"});
        }
        return mockJson({detail: {code: "NOT_MOCKED", message: url}}, {status: 404});
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the routed app shell dashboard with deployed platform status", async () => {
    render(<App />);

    expect(await screen.findByRole("navigation", {name: /primary navigation/i})).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /dashboard/i})).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", {name: /workflows/i})).toHaveAttribute("href", "/workflows");
    expect(screen.getByText(/Demo environment/i)).toBeInTheDocument();
    expect(await screen.findByRole("heading", {name: /^Run Tracker$/i})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /All pipelines/i})).toHaveClass("active");
    expect(screen.getByRole("button", {name: /^PGT-A$/i})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /NIPT Docker/i})).toBeInTheDocument();
    expect(screen.queryByRole("heading", {name: /Recent failed runs/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", {name: /Recent completed runs/i})).not.toBeInTheDocument();
    expect(screen.getByText(/Status distribution/i)).toBeInTheDocument();
    expect(screen.getByText(/7-day activity/i)).toBeInTheDocument();
    expect(screen.getByText(/Fresh transfer 2-sample QC/i)).toBeInTheDocument();
    expect(screen.getByText(activePgtaRunId)).toBeInTheDocument();
    expect(screen.getByText(/52%/i)).toBeInTheDocument();
    expect(screen.getAllByText(/baseline_bam_uniformity_qc/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("progressbar", {name: new RegExp(activePgtaRunId)})).toHaveAttribute("aria-valuenow", "52");
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/dashboard/overview?pipeline=all&period=7d"), undefined);
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/dashboard/runs?pipeline=all&limit=10&offset=0"), undefined);
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/system/resources"), undefined);
    expect(vi.mocked(globalThis.fetch).mock.calls.some(([input]) => String(input).includes("/progress"))).toBe(false);
    expect(vi.mocked(globalThis.fetch).mock.calls.some(([input]) => String(input).includes("/rules"))).toBe(false);
    expect(screen.getAllByText(/Not in Airflow/i).length).toBeGreaterThan(0);
    expect(screen.getByText(failedRunId)).toBeInTheDocument();
    expect(screen.getAllByText(niptRunId).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/NIPT docker/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Bootstrap observed/i)).toBeInTheDocument();
    expect(screen.queryByText(/^queued$/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", {name: /Intake scanner/i})).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: /Service & Node Health/i})).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: /Pipeline Resources/i})).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: /Workflow Activity/i})).toBeInTheDocument();
    expect(screen.queryByRole("heading", {name: /^Deployed workflows$/i})).not.toBeInTheDocument();
    expect(screen.getByText(/CPU cores/i)).toBeInTheDocument();
    expect(screen.getByText(/\/data/i)).toBeInTheDocument();
    expect(screen.getByText(/1-10 of 12/i)).toBeInTheDocument();
    expect(screen.queryByText(wesRunId)).not.toBeInTheDocument();
    expect(screen.queryByText(/WES qsub/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/NIPT qsub/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/WGS/i)).not.toBeInTheDocument();
  });

  it("filters, pages, and switches the dashboard tracker without per-run progress calls", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByRole("heading", {name: /^Run Tracker$/i})).toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: /^Running$/i}));
    expect(screen.getByText(activePgtaRunId)).toBeInTheDocument();
    expect(screen.queryByText(createdPgtaRunId)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", {name: /Created only/i}));
    expect(screen.getByText(createdPgtaRunId)).toBeInTheDocument();
    expect(screen.getAllByText(/Not in Airflow/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(activePgtaRunId)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", {name: /^All$/i}));
    await user.click(screen.getByRole("button", {name: /Next page/i}));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/dashboard/runs?pipeline=all&limit=10&offset=10"), undefined);
    });

    await user.click(screen.getByRole("button", {name: /NIPT Docker/i}));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/dashboard/overview?pipeline=nipt_docker&period=7d"), undefined);
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/dashboard/runs?pipeline=nipt_docker&limit=10&offset=0"), undefined);
    });
    expect(screen.getAllByText(/NIPT docker/i).length).toBeGreaterThan(0);
    expect(vi.mocked(globalThis.fetch).mock.calls.some(([input]) => String(input).includes("/progress"))).toBe(false);
  });

  it("shows only PGT-A runs in the run table without hiding status text", async () => {
    const user = userEvent.setup();
    setRoute("/runs");
    render(<App />);

    expect(await screen.findByRole("heading", {name: /runs/i})).toBeInTheDocument();
    const pipelineSelect = screen.getByLabelText(/pipeline/i);
    expect(pipelineSelect).toHaveValue("all");
    expect(within(pipelineSelect).queryByRole("option", {name: /^WES/i})).not.toBeInTheDocument();
    expect(within(pipelineSelect).getByRole("option", {name: /^NIPT Docker/i})).toBeInTheDocument();
    expect(within(pipelineSelect).queryByRole("option", {name: /^NIPT qsub/i})).not.toBeInTheDocument();
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

  it("auto-syncs an active PGT-A run detail through the backend Airflow bridge", async () => {
    createdPgtaStatus = "submitted";
    createdPgtaDagRunId = `manual__${createdPgtaRunId}`;
    setRoute(`/runs/${createdPgtaRunId}`);
    render(<App />);

    expect(await screen.findByText(createdPgtaRunId)).toBeInTheDocument();
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${createdPgtaRunId}/actions/sync-airflow`),
        expect.objectContaining({method: "POST"}),
      );
    });
  });

  it("creates and submits a PGT-A run to Airflow from the primary submit action", async () => {
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

    expect(await screen.findByText(/Sample_G10/i)).toBeInTheDocument();
    expect(screen.getByText(/Sample_G11/i)).toBeInTheDocument();
    expect(screen.queryByText(`${rawdataRoot}/Sample_G10/G10_R1.fastq.gz`)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: /show FASTQ files for Sample_G10/i}));
    expect(screen.getByText("G10_R1.fastq.gz")).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", {name: /select folder Sample_G10/i}));
    await user.click(screen.getByRole("checkbox", {name: /select folder Sample_G11/i}));
    await user.click(screen.getByRole("button", {name: /create and submit to airflow/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/runs"),
        expect.objectContaining({method: "POST"}),
      );
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${createdPgtaRunId}/actions/submit`),
        expect.objectContaining({method: "POST"}),
      );
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${createdPgtaRunId}/actions/sync-airflow`),
        expect.objectContaining({method: "POST"}),
      );
    });
    expect(await screen.findByText(createdPgtaRunId)).toBeInTheDocument();
    expect(screen.getByText(`manual__${createdPgtaRunId}`)).toBeInTheDocument();
    const handoffSummary = screen.getByText(/Airflow handoff confirmed/i).closest("div");
    expect(handoffSummary).not.toBeNull();
    expect(within(handoffSummary as HTMLElement).getByText("success")).toBeInTheDocument();
    expect(screen.getByText(/Create only/i)).toBeInTheDocument();
  });

  it("exposes NIPT Docker server batch submission without re-enabling WES or qsub flows", async () => {
    setRoute("/submit");
    render(<App />);

    expect(await screen.findByRole("heading", {name: /submit task/i})).toBeInTheDocument();
    expect(screen.getByRole("radio", {name: /PGT-A/i})).toBeInTheDocument();
    expect(screen.getByRole("radio", {name: /NIPT Docker/i})).toBeInTheDocument();
    expect(screen.queryByRole("combobox", {name: /NIPT template/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", {name: /WES/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", {name: /NIPT qsub/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", {name: /WGS/i})).not.toBeInTheDocument();
  });

  it("creates and submits a NIPT Docker scanned batch run to Airflow", async () => {
    const user = userEvent.setup();
    setRoute("/submit");
    render(<App />);

    expect(await screen.findByRole("heading", {name: /submit task/i})).toBeInTheDocument();
    await user.click(screen.getByRole("radio", {name: /NIPT Docker/i}));
    expect(screen.queryByRole("combobox", {name: /NIPT template/i})).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText(/rawdata root/i));
    await user.type(screen.getByLabelText(/rawdata root/i), niptRoot);
    expect(screen.getByRole("combobox", {name: /NIPT run mode/i})).toHaveValue("mount_smoke");
    expect(screen.getByLabelText(/NIPT cores/i)).toHaveValue(40);
    await user.click(screen.getByRole("button", {name: /^scan$/i}));

    expect(await screen.findByText(/260414_TPNB500380AR_1065_AH32CCBGY2/i)).toBeInTheDocument();
    expect(screen.queryByText(`${niptBatchRoot}/NIPT26040207.A06.R1.clean.fastq.gz`)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: /show FASTQ files for 260414_TPNB500380AR_1065_AH32CCBGY2/i}));
    expect(screen.getByText("NIPT26040207.A06.R1.clean.fastq.gz")).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", {name: /select folder 260414_TPNB500380AR_1065_AH32CCBGY2/i}));
    await user.click(screen.getByRole("button", {name: /create and submit to airflow/i}));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/runs"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"pipeline":"nipt_docker"'),
        }),
      );
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${niptRunId}/actions/submit`),
        expect.objectContaining({method: "POST"}),
      );
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/runs/${niptRunId}/actions/sync-airflow`),
        expect.objectContaining({method: "POST"}),
      );
    });
    const createCall = vi.mocked(globalThis.fetch).mock.calls.find(
      ([input, init]) => String(input).endsWith("/api/runs") && init?.method === "POST" && String(init.body).includes('"pipeline":"nipt_docker"'),
    );
    expect(createCall).toBeTruthy();
    expect(String(createCall?.[1]?.body)).not.toContain("template_id");
    expect(String(createCall?.[1]?.body)).toContain(`"rawdata_root":"${niptRoot}"`);
    expect(String(createCall?.[1]?.body)).toContain("NIPT26040207.A06");
    expect(await screen.findByText(niptRunId)).toBeInTheDocument();
    expect(screen.getByText(`manual__${niptRunId}`)).toBeInTheDocument();
    expect(screen.getByText(/Airflow handoff confirmed/i)).toBeInTheDocument();
  });

  it("shows NIPT Docker run detail with Airflow tasks and pipeline steps", async () => {
    niptStatus = "success";
    niptDagRunId = `manual__${niptRunId}`;
    setRoute(`/runs/${niptRunId}`);
    render(<App />);

    expect(await screen.findByText(niptRunId)).toBeInTheDocument();
    expect(screen.queryByRole("heading", {name: /Current deployment scope/i})).not.toBeInTheDocument();
    expect(screen.getByText(/100%/i)).toBeInTheDocument();
    expect(screen.getByText(/nipt_mount_smoke/i)).toBeInTheDocument();

    const workflowTab = screen.getByRole("tab", {name: /workflow/i});
    await userEvent.click(workflowTab);
    expect(await screen.findByRole("heading", {name: /Airflow tasks/i})).toBeInTheDocument();
    expect(screen.getAllByText(/run_nipt_docker/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", {name: /Pipeline steps/i})).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining(`/api/runs/${niptRunId}/progress`), undefined);
  });

  it("shows a read-only intake scanner settings console without scanner action buttons", async () => {
    const user = userEvent.setup();
    setRoute("/settings");
    render(<App />);

    expect(await screen.findByRole("heading", {name: /Intake Scanner/i})).toBeInTheDocument();
    expect(screen.getByText("/app/config/intake.yaml")).toBeInTheDocument();
    expect(screen.getByText(/stable_fingerprint/i)).toBeInTheDocument();
    expect(screen.getByText(/2 stable scans/i)).toBeInTheDocument();
    expect(screen.getByText("bio_intake_scan")).toBeInTheDocument();
    expect(screen.getByText(/Paused/i)).toBeInTheDocument();
    expect(screen.getByText(/Airflow reachable/i)).toBeInTheDocument();
    expect(screen.getByText(/scheduled__2026-07-08T17:00:00\+08:00/i)).toBeInTheDocument();
    expect(screen.getByText("pgta_rawdata")).toBeInTheDocument();
    expect(screen.getAllByText(rawdataRoot).length).toBeGreaterThan(0);
    expect(screen.getByText("nipt_fastq")).toBeInTheDocument();
    expect(screen.getAllByText(niptRoot).length).toBeGreaterThan(0);
    expect(screen.getByText(/clean_fastq/i)).toBeInTheDocument();
    expect(screen.getByText(/\*\.R1\.clean\.fastq\.gz/i)).toBeInTheDocument();
    expect(screen.getByText(/mount_smoke/i)).toBeInTheDocument();
    expect(screen.getByText(/Bootstrap observed/i)).toBeInTheDocument();
    expect(screen.queryByText(/^queued$/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Use Preview configured roots/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", {name: /Preview configured intake roots/i}));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/intake/scan-preview"),
        expect.objectContaining({method: "POST"}),
      );
    });
    expect(screen.getByText(/Read-only preview: no DB writes/i)).toBeInTheDocument();
    expect(screen.getByText(/would submit/i)).toBeInTheDocument();
    expect(screen.getByText(/blocked by config/i)).toBeInTheDocument();
    expect(screen.getByText(/auto-submit disabled by config/i)).toBeInTheDocument();
    expect(screen.getAllByText(/bootstrap protected/i).length).toBeGreaterThan(0);
    expect(vi.mocked(globalThis.fetch).mock.calls.some(([input]) => String(input).includes("/api/intake/scan-and-submit"))).toBe(false);

    await user.click(screen.getByRole("button", {name: /Refresh intake scanner/i}));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/intake/config"), undefined);
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/intake/status?limit=100"), undefined);
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/intake/scanner-state"), undefined);
    });
    expect(screen.queryByRole("button", {name: /unpause/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: /scan now/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: /full run/i})).not.toBeInTheDocument();
  });

  it("shows only deployed PGT-A and NIPT Docker workflow, samples, and failure resources", async () => {
    const user = userEvent.setup();
    render(<App />);

    setRoute("/workflows");
    cleanup();
    render(<App />);
    expect((await screen.findAllByText(/PGT-A/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/WES qsub/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/NIPT docker/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/WGS/i)).not.toBeInTheDocument();

    cleanup();
    setRoute("/samples");
    render(<App />);
    expect((await screen.findAllByText(/^G10$/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/S001/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/NIPT26040207\.A06/i).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("link", {name: /failures/i}));
    expect(await screen.findByText(/Recent failed runs/i)).toBeInTheDocument();
    expect(screen.getAllByText(/retry suggestion/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(wesRunId)).not.toBeInTheDocument();
  });
});
