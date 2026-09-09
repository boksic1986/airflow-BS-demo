import "@testing-library/jest-dom/vitest";

import {act, cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";

import App from "./App";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

it("uses a pipeline-selectable staged WGS submission form", async () => {
  window.history.pushState({}, "", "/submit");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/wgs/release")) return json({release_id: "wgs-4.2.0-b067c72", version: "V4.2.0", source_commit: "b067c72eed795e59b724b13324b0d380ae8b7e94", profile_id: "wgs-4.2.0", profile_revision: "r1", cce_pipeline_version: "0.8.3", execution_enabled: false, runtime_adapter_enabled: false, submission_preview_enabled: false});
    if (url.endsWith("/api/wgs/projects")) return json({items: [{project_id: "WGS_Clinical", display_name: "WGS Clinical", platforms: [{platform_id: "T7", display_name: "T7 / hg38 / WGS V4.2.0"}], fastq_roots: [{root_id: "T7_Fastq", display_name: "T7 FASTQ"}], editable_config: {use_reference: {type: "enum", values: ["all", "ref", "no"], default: "all"}}}]});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Submit run"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "WGS"})).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByRole("option", {name: /WES/i})).not.toBeInTheDocument();
  expect(screen.getByLabelText("FASTQ root")).toBeInTheDocument();
  expect(screen.getByLabelText("Batch")).toBeInTheDocument();
  expect(screen.queryByLabelText("Sequencing batch")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Analysis batch")).not.toBeInTheDocument();
  expect(await screen.findByText("WGS V4.2.0 / b067c72")).toBeInTheDocument();
  expect(screen.getByText("wgs-4.2.0/r1")).toBeInTheDocument();
  expect(screen.getByText("0.8.3")).toBeInTheDocument();
  expect(screen.queryByLabelText("Variant caller")).not.toBeInTheDocument();
  expect(screen.queryByRole("combobox", {name: /WGS version/i})).not.toBeInTheDocument();
  expect(screen.queryByText(/READY/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Use reference")).not.toBeInTheDocument();
  expect(screen.getByRole("button", {name: "Prepare sample information"})).toBeDisabled();
  expect(screen.getByText(/WGS first generates sampleinfo/)).toBeInTheDocument();
  expect(screen.queryByText(/preview is not enabled/)).not.toBeInTheDocument();
});

it("keeps WGS and GATK Cloud visible in the submission pipeline switcher", async () => {
  window.history.pushState({}, "", "/submit");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({
      ...wgsCapabilities(),
      deployed_pipelines: ["wgs", "gatk"],
      pipelines: [
        ...wgsCapabilities().pipelines,
        {id: "gatk", display_name: "GATK Cloud", dag_id: "bio_gatk", version: "7.6.0", enabled: true, submit_enabled: true, capabilities: ["submit", "rules", "artifacts"], execution_targets: ["cce"]},
      ],
    });
    if (url.endsWith("/api/pipelines/gatk/release")) return json({pipeline: "gatk", profile_id: "gatk-scmc-v7.6.0", profile_revision: "bd04f6d", execution_target: "cce", execution_enabled: false});
    if (url.endsWith("/api/wgs/release")) return json({release_id: "wgs-4.1.1-6c98281", version: "V4.1.1", source_commit: "6c982817614db6a1157b6f287427ddf01ac91827", execution_enabled: true, runtime_adapter_enabled: true, submission_preview_enabled: false});
    if (url.endsWith("/api/wgs/projects")) return json({items: [{project_id: "WGS_Clinical", display_name: "WGS Clinical", platforms: [{platform_id: "T7", display_name: "T7 / hg38 / V4.1.1"}], fastq_roots: [{root_id: "T7_Fastq", display_name: "T7 FASTQ"}], editable_config: {use_reference: {type: "enum", values: ["all", "ref", "no"], default: "all"}}}]});
    return json({items: [], total: 0});
  }));

  render(<App />);

  const wgsTab = await screen.findByRole("tab", {name: "WGS"});
  const gatkTab = screen.getByRole("tab", {name: "GATK Cloud"});
  expect(wgsTab).toHaveAttribute("aria-selected", "true");
  expect(gatkTab).toHaveAttribute("aria-selected", "false");
  fireEvent.click(gatkTab);
  expect(await screen.findByRole("heading", {name: "Submit GATK Cloud"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "GATK Cloud"})).toHaveAttribute("aria-selected", "true");
  expect(await screen.findByText("gatk-scmc-v7.6.0")).toBeInTheDocument();
  expect(screen.getByText(/GATK execution is disabled/)).toBeInTheDocument();
  expect(window.location.search).toBe("?pipeline=gatk");
  expect(screen.queryByLabelText("FASTQ root")).not.toBeInTheDocument();
});

it("previews and confirms a locked GATK Cloud project", async () => {
  window.history.pushState({}, "", "/submit?pipeline=gatk");
  const requests: Array<{url: string; init?: RequestInit}> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    requests.push({url, init});
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json({
      ...wgsCapabilities(),
      deployed_pipelines: ["wgs", "gatk"],
      pipelines: [
        ...wgsCapabilities().pipelines,
        {id: "gatk", display_name: "GATK Cloud", dag_id: "bio_gatk", version: "7.6.0", enabled: true, submit_enabled: true, capabilities: ["submit", "rules", "artifacts"], execution_targets: ["cce"]},
      ],
    });
    if (url.endsWith("/api/pipelines/gatk/release")) return json({pipeline: "gatk", profile_id: "gatk-scmc-v7.6.0", profile_revision: "bd04f6d", execution_target: "cce", execution_enabled: true});
    if (url.endsWith("/api/pipelines/gatk/submission-preview")) return json({
      draft_id: "gatk-draft-1",
      preview_hash: "a".repeat(64),
      pipeline: "gatk",
      profile_id: "gatk-scmc-v7.6.0",
      profile_revision: "bd04f6d",
      batch: "20260908A",
      sampleinfo_name: "WES_20260908A_T7.sampleinfo.txt",
      sample_count: 2,
      fastq_file_count: 4,
      fastq_total_bytes: 4294967296,
      samples: ["SCMC001", "SCMC002"],
      validation: {sample_sets_match: true, fastq_pairs_complete: true, paths_approved: true},
      expires_at: "2026-09-08T12:30:00Z",
    });
    if (url.endsWith("/api/runs")) return json({analysis_id: "GATK_20260908_120000_A1B2C3", pipeline: "gatk", status: "submitted"});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Submit GATK Cloud"})).toBeInTheDocument();
  expect(screen.getByText(/SCMC samples are selected from sampleinfo/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("WES project directory"), {target: {value: "/sg2/21.lijing/WES_Clinical/WES_20260908A_T7_V7.6.0_hg38"}});
  fireEvent.click(screen.getByRole("button", {name: "Preview project"}));
  expect(await screen.findByText("WES_20260908A_T7.sampleinfo.txt")).toBeInTheDocument();
  expect(screen.getByText("SCMC001")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Confirm and submit"}));
  expect(await screen.findByRole("link", {name: "GATK_20260908_120000_A1B2C3"})).toHaveAttribute("href", "/runs/GATK_20260908_120000_A1B2C3");
  const submitted = requests.find((item) => item.url.endsWith("/api/runs") && item.init?.method === "POST");
  expect(JSON.parse(String(submitted?.init?.body))).toMatchObject({
    pipeline: "gatk",
    execution_mode: "cce",
    submission_draft_id: "gatk-draft-1",
    submission_preview_hash: "a".repeat(64),
  });
  const previewRequest = requests.find((item) => item.url.endsWith("/api/pipelines/gatk/submission-preview"));
  expect(new Headers(previewRequest?.init?.headers).get("Content-Type")).toBe("application/json");
});

it("starts stage one without accepting runtime configuration", async () => {
  window.history.pushState({}, "", "/submit");
  const requests: Array<{url: string; init?: RequestInit}> = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    requests.push({url, init});
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/wgs/release")) return json({release_id: "wgs-4.1.1-6c98281", version: "V4.1.1", source_commit: "6c982817614db6a1157b6f287427ddf01ac91827", execution_enabled: true, runtime_adapter_enabled: true, submission_preview_enabled: false});
    if (url.endsWith("/api/wgs/projects")) return json({items: [{project_id: "WGS_Clinical", display_name: "WGS Clinical", platforms: [{platform_id: "T7", display_name: "T7 / hg38 / V4.1.1"}], fastq_roots: [{root_id: "T7_Fastq", display_name: "T7 FASTQ"}], editable_config: {use_reference: {type: "enum", values: ["all", "ref", "no"], default: "all"}}}]});
    if (url.endsWith("/api/wgs/runs")) return json({analysis_id: "WGS_TEST", pipeline: "wgs", status: "submitted", params: {submission_phase: "config_review"}});
    if (url.endsWith("/api/runs/WGS_TEST")) return json({analysis_id: "WGS_TEST", pipeline: "wgs", status: "submitted", params: {submission_phase: "config_review"}});
    if (url.endsWith("/api/runs/WGS_TEST/samples")) return json({items: [{sample_id: "S1", family_id: "F1", status: "pending", metadata: {}}]});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("button", {name: "Prepare sample information"})).toBeInTheDocument();
  expect(await screen.findByText("Enabled")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Batch"), {target: {value: "20260901B"}});
  fireEvent.click(screen.getByRole("button", {name: "Prepare sample information"}));
  expect(await screen.findByRole("heading", {name: "Review samples and configuration"})).toBeInTheDocument();
  expect(await screen.findByText("S1")).toBeInTheDocument();
  expect(screen.getByLabelText("Use reference")).toBeInTheDocument();
  expect(screen.getByLabelText("Resource set")).toHaveValue("default");
  const submitted = requests.find((item) => item.url.endsWith("/api/wgs/runs") && item.init?.method === "POST");
  expect(JSON.parse(String(submitted?.init?.body))).toMatchObject({batch: "20260901B"});
  expect(String(submitted?.init?.body)).not.toContain("use_reference");
  expect(String(submitted?.init?.body)).not.toContain("sequencing_batch");
  expect(String(submitted?.init?.body)).not.toContain("analysis_batch");
});

it("leaves the preparation screen when the polled run has failed", async () => {
  window.history.pushState({}, "", "/submit");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/wgs/release")) return json({release_id: "wgs-4.1.1-6c98281", version: "V4.1.1", source_commit: "6c982817614db6a1157b6f287427ddf01ac91827", execution_enabled: true, runtime_adapter_enabled: true, submission_preview_enabled: false});
    if (url.endsWith("/api/wgs/projects")) return json({items: [{project_id: "WGS_Clinical", display_name: "WGS Clinical", platforms: [{platform_id: "T7", display_name: "T7 / hg38 / V4.1.1"}], fastq_roots: [{root_id: "T7_Fastq", display_name: "T7 FASTQ"}], editable_config: {use_reference: {type: "enum", values: ["all", "ref", "no"], default: "all"}}}]});
    if (url.endsWith("/api/wgs/runs")) return json({analysis_id: "WGS_FAILED", pipeline: "wgs", status: "submitted", params: {submission_phase: "preparing_sampleinfo"}});
    if (url.endsWith("/api/runs/WGS_FAILED")) return json({analysis_id: "WGS_FAILED", pipeline: "wgs", status: "failed", error_summary: "sampleinfo failed", params: {submission_phase: "preparing_sampleinfo"}});
    if (url.endsWith("/api/runs/WGS_FAILED/samples")) return json({items: []});
    return json({items: [], total: 0});
  }));

  render(<App />);
  expect(await screen.findByText("Enabled")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Batch"), {target: {value: "20260902A"}});
  fireEvent.click(screen.getByRole("button", {name: "Prepare sample information"}));

  expect(await screen.findByRole("heading", {name: "Sample information preparation failed"})).toBeInTheDocument();
  expect(screen.getByRole("link", {name: "View failure details"})).toHaveAttribute("href", "/runs/WGS_FAILED");
  expect(screen.queryByText("This page refreshes automatically.")).not.toBeInTheDocument();
});

it("loads WGS resource tabs for an active run", async () => {
  window.history.pushState({}, "", "/runs/WGS_001");
  const urls: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    urls.push(url);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/runs/WGS_001/workspace")) return json({
      run: {analysis_id: "WGS_001", pipeline: "wgs", status: "running", pipeline_release_id: "wgs-4.1.1-1656b5d", wgs_version: "V4.1.1", wgs_source_commit: "1656b5d7a6e2f24242c38149f6d1c92ac266cd37", resolved_runtime: {cce_pipeline_version: "0.7.1", profile_id: "wgs-4.1.1-r1", master_image_digest: "sha256:abc"}, rule_event_schema_version: "rule-event.v1", observer: {lifecycle_status: "active", monitoring_health: "healthy", activated_at: "2026-08-26T01:00:00Z", last_success_at: "2026-08-26T01:01:05Z", last_error: null, updated_at: "2026-08-26T01:01:05Z"}},
      summary: {sample_count: 1, rule_count: 10, failed_rule_count: 0},
      progress: {analysis_id: "WGS_001", pipeline: "wgs", status: "running", percent: 20, current_step: "mapping", current_rule: "mapping", current_source: "runner", note: "", not_in_airflow: false, progress_source: "kubernetes-api", airflow_tasks: [], rule_events: []},
      active_transfer: null,
      slot_usage: {pool: "wgs-heavy-io", limit: 25, used: 0, waiting: 0, mode: "monitor-only"},
    });
    if (url.includes("/api/runs/WGS_001/samples")) return json({
      manifest: [{sample_id: "S1", data_id: "S1-WGS", sample_type: "blood", family_id: "F1", family_relation: "proband", received_date: "2026-08-20", estimated_report_date: "2026-09-10"}],
      items: [{sample_id: "S1", data_id: "S1-WGS", family_id: "F1", family_relation: "proband", current_stage: "Mapping", current_rule: "mapping", completed_rules: 2, total_rules: 10, progress_percent: 20, status: "running", elapsed_seconds: 90, qc_status: "pass", qc_metrics: {clean_q30_percent: "98.5%", mapped_reads_percent: "99.8%", average_depth: "58.83", coverage_20x_percent: "96.78%", contamination: "PASS"}}],
    });
    if (url.includes("/api/runs/WGS_001/rules")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/pods")) return json({items: [{attempt: 1, pod_hash: "abc123", job_name: "wgs-master-a1", phase: "Failed", reason: "OOMKilled", exit_code: 137, node_name: "cce-node-1", message: "Master failed", resources: {memory: "4Gi"}, observed_at: "2026-08-24T01:01:00Z", updated_at: "2026-08-24T01:01:05Z"}]});
    if (url.includes("/api/runs/WGS_001/transfers")) return json({items: [{transfer_id: "WGS_001-a1-input", attempt: 1, direction: "upload", status: "running", progress_detail_available: false, heartbeat_at: "2026-08-26T01:01:05Z", message: "Step1 upload is running"}]});
    if (url.includes("/api/runs/WGS_001/progress")) return json({analysis_id: "WGS_001", pipeline: "wgs", status: "running", percent: 0, current_step: "prepare", current_source: "runner", note: "", not_in_airflow: false, progress_source: "estimate", airflow_tasks: [], rule_events: []});
    if (url.includes("/api/runs/WGS_001/qc")) return json({summary: {pass: 0, warn: 0, fail: 0, unknown: 0}, items: []});
    if (url.includes("/api/runs/WGS_001/logs/index")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/logs")) return json({path: "", stream: "stdout", truncated: false, lines: []});
    if (url.includes("/api/runs/WGS_001/artifacts")) return json({items: []});
    if (url.includes("/api/runs/WGS_001/resources")) return json({analysis_id: "WGS_001", pipeline: "wgs", wall_seconds: 0, peak_rss_bytes: 0, read_bytes: 0, write_bytes: 0, cpu_seconds: 0, sample_count: 0, complete: false});
    return json({items: []});
  }));

  const {container} = render(<App />);
  expect(await screen.findByRole("tab", {name: "Samples"})).toBeInTheDocument();
  expect(screen.getByRole("tab", {name: "Master"})).toBeInTheDocument();
  expect(screen.getAllByText("wgs-4.1.1-1656b5d").length).toBeGreaterThan(0);
  expect(screen.getByText("V4.1.1")).toBeInTheDocument();
  expect(screen.getByText("0.7.1")).toBeInTheDocument();
  expect(screen.queryByText(/sha256:abc/)).not.toBeInTheDocument();
  expect(urls.filter((url) => url.endsWith("/api/runs/WGS_001/workspace"))).toHaveLength(1);
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/samples"))).toBe(true);
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/pods"))).toBe(false);
  expect(screen.queryByText(/Monitoring health/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/CCE monitor/i)).not.toBeInTheDocument();
  const snapshotGrid = container.querySelector(".run-detail-snapshot-grid");
  expect(snapshotGrid).toBeInTheDocument();
  expect(snapshotGrid?.children[0]).toContainElement(screen.getByRole("heading", {name: "Current progress"}));
  expect(snapshotGrid?.children[1]).toContainElement(screen.getByRole("heading", {name: "Pipeline evidence"}));
  expect(snapshotGrid?.children[0]).toHaveClass("snapshot-panel-stretch");
  expect(snapshotGrid?.children[1]).toHaveClass("snapshot-panel-stretch");
  fireEvent.click(screen.getByRole("tab", {name: "Samples"}));
  expect(await screen.findByText("S1")).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", {name: "Data"})).not.toBeInTheDocument();
  expect(screen.getByText("2026-08-20")).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", {name: "Safe QC metrics"})).not.toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "QC"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "QC"}));
  expect(await screen.findByRole("columnheader", {name: "Average depth"})).toBeInTheDocument();
  expect(screen.getByText("98.5%")).toBeInTheDocument();
  expect(screen.getByText("99.8%")).toBeInTheDocument();
  expect(screen.getByText("58.83")).toBeInTheDocument();
  expect(screen.getByText("96.78%")).toBeInTheDocument();
  expect(screen.getByText("PASS")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "Master"}));
  expect(await screen.findByText("wgs-master-a1")).toBeInTheDocument();
  expect(screen.getByText("OOMKilled")).toBeInTheDocument();
  expect(screen.getByText("137")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", {name: "Transfers"}));
  expect(await screen.findByText("FASTQ upload")).toBeInTheDocument();
  expect(screen.getByText(/Stage status is available/)).toBeInTheDocument();
  expect(screen.queryByLabelText("FASTQ upload progress")).not.toBeInTheDocument();
  expect(screen.queryByText(/0 B\/s/)).not.toBeInTheDocument();
  expect(urls.filter((url) => url.includes("/api/runs/WGS_001/samples"))).toHaveLength(1);
  expect(urls.some((url) => url.includes("/api/runs/WGS_001/pods"))).toBe(true);
});

it("renders independent WGS data lifecycle states without replacing workflow success", async () => {
  window.history.pushState({}, "", "/runs/WGS_LIFECYCLE");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/runs/WGS_LIFECYCLE/workspace")) return json({
      run: {
        analysis_id: "WGS_LIFECYCLE",
        pipeline: "wgs",
        status: "success",
        params: {batch_no: "20260907A"},
        lifecycle: {
          workflow: {status: "success", updated_at: "2026-09-07T01:00:00Z", updated_by: "wgs-scanner"},
          cloud_release: {status: "failed", updated_at: "2026-09-07T02:00:00Z", updated_by: "admin", message: "SFS cleanup failed"},
          raw_fastq_backup: {status: "running", revision: 2, updated_at: "2026-09-07T03:00:00Z", updated_by: "admin", message: "Archive in progress"},
          downstream_release: {status: "not_started", revision: 1, updated_at: null, updated_by: null, message: null},
        },
      },
      summary: {sample_count: 3, rule_count: 209, failed_rule_count: 0, batch_qc_status: "pass"},
      progress: {analysis_id: "WGS_LIFECYCLE", pipeline: "wgs", status: "success", percent: 100, current_step: "finalize_run", current_source: "biodemo", note: "", not_in_airflow: false, progress_source: "run-stage-state", airflow_tasks: [], rule_events: []},
      validation_issues: [],
      slot_usage: null,
    });
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Data lifecycle"})).toBeInTheDocument();
  expect(screen.getByText("Workflow success")).toBeInTheDocument();
  expect(screen.getByText("FASTQ backup running")).toBeInTheDocument();
  expect(screen.getAllByText("Not started").length).toBeGreaterThan(0);
  expect(screen.getByText("SFS cleanup failed")).toBeInTheDocument();
  expect(screen.getByText("Post-run action failed; workflow results remain successful.")).toBeInTheDocument();
  expect(screen.getAllByText("Result delivery").length).toBeGreaterThan(0);
  expect(screen.getAllByText("success").length).toBeGreaterThan(0);
  expect(screen.getByText("Batch QC")).toBeInTheDocument();
  expect(screen.getAllByText("pass").length).toBeGreaterThan(0);
  expect(screen.getByText("wgs-scanner")).toBeInTheDocument();
});

it("falls back to legacy run resources when the workspace endpoint is unavailable", async () => {
  window.history.pushState({}, "", "/runs/WGS_LEGACY");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/runs/WGS_LEGACY/workspace")) return jsonStatus({detail: "Not Found"}, 404);
    if (url.endsWith("/api/runs/WGS_LEGACY")) return json({analysis_id: "WGS_LEGACY", pipeline: "wgs", status: "success", params: {batch_no: "20260905B"}});
    if (url.endsWith("/api/runs/WGS_LEGACY/progress")) return json({
      analysis_id: "WGS_LEGACY",
      pipeline: "wgs",
      status: "success",
      percent: 100,
      current_step: "finalize_run",
      current_source: "biodemo",
      note: "",
      not_in_airflow: false,
      progress_source: "run-stage-state",
      airflow_tasks: [],
      rule_events: [],
      orchestration_stages: [
        {stage_code: "step5_download", step_number: 5, label: "Downloading WGS results", status: "success"},
        {stage_code: "step6_materialize", step_number: 6, label: "Materializing local results", status: "success"},
      ],
    });
    if (url.endsWith("/api/runs/WGS_LEGACY/samples")) return json({items: [{sample_id: "S1", data_id: "S1-WGS"}], manifest: []});
    if (url.includes("/api/runs/WGS_LEGACY/rules")) return json({items: [], total: 0, limit: 1, offset: 0});
    if (url.endsWith("/api/runs/WGS_LEGACY/validation-issues")) return json({items: []});
    return json({items: []});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "WGS_LEGACY"})).toBeInTheDocument();
  expect(screen.queryByText("Not Found")).not.toBeInTheDocument();
  expect(screen.getAllByText("20260905B").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("tab", {name: "Rules"}));
  const stages = await screen.findByLabelText("Pipeline stage dependency graph");
  const labels = Array.from(stages.querySelectorAll("strong"), (node) => node.textContent);
  expect(labels).toEqual(["Downloading WGS results", "Materializing local results"]);
});

it("enables Step7 after an admin confirms the displayed public batch", async () => {
  window.history.pushState({}, "", "/runs/WGS_STEP7");
  const copyBatch = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {configurable: true, value: {writeText: copyBatch}});
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "admin", role: "admin"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/runs/WGS_STEP7/workspace")) return json({
      run: {
        analysis_id: "WGS_STEP7",
        pipeline: "wgs",
        status: "success",
        params: {batch_no: "WGS_20260825A_T7Hg38V4.1.1", analysis_batch: "20260825A"},
        lifecycle: {
          workflow: {status: "success", updated_at: "2026-09-07T01:00:00Z", updated_by: "wgs-scanner"},
          cloud_release: {status: "not_started", updated_at: null, updated_by: null, message: null},
          raw_fastq_backup: {status: "not_started", updated_at: null, updated_by: null, message: null},
          downstream_release: {status: "not_started", updated_at: null, updated_by: null, message: null},
        },
        step7_cleanup: {available: true, reason: null, required_batch: "20260825A", latest_action: null},
      },
      summary: {sample_count: 3, rule_count: 209, failed_rule_count: 0},
      progress: {analysis_id: "WGS_STEP7", pipeline: "wgs", status: "success", percent: 100, current_step: "finalize_run", current_source: "biodemo", note: "", not_in_airflow: false, progress_source: "run-stage-state", airflow_tasks: [], rule_events: []},
      validation_issues: [],
      slot_usage: null,
    });
    return json({items: [], total: 0});
  }));

  render(<App />);

  const panel = await screen.findByRole("region", {name: "Step7 SFS cleanup"});
  expect(panel.closest(".data-lifecycle-item")).toHaveClass("data-lifecycle-item");
  expect(document.querySelector(".destructive-panel")).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("Release SFS data"));
  expect(panel).toHaveTextContent("Type 20260825A to confirm");
  const checkbox = screen.getByRole("checkbox", {name: "Acknowledge SFS cleanup"});
  expect(checkbox.closest("label")).toHaveClass("checkbox-field");
  fireEvent.click(screen.getByRole("button", {name: "Copy batch 20260825A"}));
  expect(copyBatch).toHaveBeenCalledWith("20260825A");
  const button = screen.getByRole("button", {name: "Run Step7 SFS cleanup"});
  fireEvent.click(checkbox);
  fireEvent.change(screen.getByLabelText("Step7 Batch confirmation"), {target: {value: " 20260825A "}});
  expect(button).toBeEnabled();
});

it("keeps refreshing a completed run while its Step7 maintenance action is active", async () => {
  vi.useFakeTimers({shouldAdvanceTime: true});
  window.history.pushState({}, "", "/runs/WGS_STEP7_ACTIVE");
  let workspaceCalls = 0;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "admin", role: "admin"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.endsWith("/api/runs/WGS_STEP7_ACTIVE/workspace")) {
      workspaceCalls += 1;
      return json({
        run: {
          analysis_id: "WGS_STEP7_ACTIVE",
          pipeline: "wgs",
          status: "success",
          params: {analysis_batch: "20260825A"},
          lifecycle: {
            workflow: {status: "success", updated_at: "2026-09-07T01:00:00Z", updated_by: "wgs-scanner"},
            cloud_release: {status: "pending", updated_at: "2026-09-07T03:48:21Z", updated_by: "admin", message: null},
            raw_fastq_backup: {status: "not_started", updated_at: null, updated_by: null, message: null},
            downstream_release: {status: "not_started", updated_at: null, updated_by: null, message: null},
          },
          step7_cleanup: {
            available: false,
            reason: "cleanup_in_progress",
            required_batch: "20260825A",
            latest_action: {
              action_id: "step7-sfs-abcdef123456",
              analysis_id: "WGS_STEP7_ACTIVE",
              attempt: 7,
              action_type: "cleanup_step7_sfs",
              linkage_group: "sfs",
              status: "queued",
              requested_by: "admin",
              created_at: "2026-09-07T03:48:21Z",
            },
          },
        },
        summary: {sample_count: 3, rule_count: 209, failed_rule_count: 0, batch_qc_status: "pass"},
        progress: {analysis_id: "WGS_STEP7_ACTIVE", pipeline: "wgs", status: "success", percent: 100, current_step: "finalize_run", current_source: "biodemo", note: "", not_in_airflow: false, progress_source: "run-stage-state", airflow_tasks: [], rule_events: []},
        validation_issues: [],
        slot_usage: null,
      });
    }
    return json({items: [], total: 0});
  }));

  render(<App />);
  expect(await screen.findByText("Waiting for Step7 worker")).toBeInTheDocument();
  expect(workspaceCalls).toBe(1);

  await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });

  expect(workspaceCalls).toBeGreaterThan(1);
});

it("shows the privacy-safe Sample Information columns in the requested order", async () => {
  window.history.pushState({}, "", "/samples");
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "operator", role: "operator"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.includes("/api/samples")) return json({
      items: [{
        analysis_id: "WGS_001",
        project_name: "WGS_Clinical",
        pipeline: "wgs",
        sample_id: "S1",
        family_id: "F1",
        batch_no: "20260901B",
        order_number_masked: "****5678",
        test_project: "Whole genome sequencing",
        sequencing_batch: "20260901B",
        status: "success",
        report_status: "not_available",
      }],
      total: 1,
      limit: 25,
      offset: 0,
    });
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Sample Information"})).toBeInTheDocument();
  expect(await screen.findByText("20260901B")).toBeInTheDocument();
  expect(screen.getByText("****5678")).toBeInTheDocument();
  expect(screen.getByText("Whole genome sequencing")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("sample, family, batch, project or run ID")).toBeInTheDocument();
  expect(screen.getAllByRole("columnheader").map((cell) => cell.textContent)).toEqual([
    "Sample / family",
    "Batch",
    "Order",
    "Relation / type",
    "Project / run",
    "Status",
  ]);
  expect(screen.queryByText("Paginated sample inventory across deployed workflows.")).not.toBeInTheDocument();
});

it("keeps account administration hidden for viewers", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    return json({items: [], total: 0});
  }));
  render(<App />);
  expect(await screen.findByText("NGS Huawei Cloud")).toBeInTheDocument();
  expect(screen.queryByRole("link", {name: "Accounts"})).not.toBeInTheDocument();
});

it("replaces duplicate dashboard metrics with actionable attention and total throughput", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities());
    if (url.includes("/api/dashboard/overview")) return json({totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0}, sample_summary: {total: 63, running: 0, workflow_failed: 0, qc_failed: 7, completed: 56}, status_distribution: {}, trend: [], sample_trend: [], attention_items: [{id: "qc-WGS_001", category: "qc_failed", severity: "danger", title: "QC failed", detail: "WGS_001 has 7 failed samples.", analysis_id: "WGS_001", batch_id: "20260901B"}]});
    if (url.includes("/api/dashboard/runs")) return json({items: [], total: 0, limit: 10, offset: 0});
    if (url.includes("/api/intake/scanner-state")) return json({last_scanned_directory_count: 0, schedule_seconds: 600, auto_dispatch_enabled: false});
    if (url.includes("/api/intake/status")) return json({items: [{pipeline: "wgs", chip_id: "2243th_20260906B", batch_id: "20260906B", sequencing_batch: "20260906B", ready_state: "ready", submit_state: "ready", eligible_pair_count: 9, excluded_addon_pair_count: 0, pair_issue_count: 0, last_seen_at: "2026-09-08T12:33:22Z"}], total: 1, limit: 10, offset: 0});
    if (url.includes("/api/platform/resources")) return json({status: "stale", items: [], updated_at: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "Command Center"})).toBeInTheDocument();
  expect(screen.getByRole("heading", {name: "Attention required"})).toBeInTheDocument();
  expect(await screen.findByText("QC failed")).toBeInTheDocument();
  expect(screen.getByText("Total")).toBeInTheDocument();
  expect(screen.getByText("63")).toBeInTheDocument();
  expect(screen.getByText("QC failed samples")).toBeInTheDocument();
  expect(screen.queryByLabelText("Command center summary")).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", {name: "Status distribution"})).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", {name: "7d run activity"})).not.toBeInTheDocument();
  const mainColumn = screen.getByRole("heading", {name: "Run Tracker"}).closest(".dashboard-main-column");
  expect(mainColumn).toContainElement(screen.getByRole("heading", {name: "Analysis Node Health"}));
  expect(mainColumn).toContainElement(screen.getByRole("heading", {name: "Cloud Resources"}));
  expect(mainColumn).toContainElement(screen.getByRole("heading", {name: "SFS I/O"}));
});

it("does not request or render intake for a selected pipeline without intake", async () => {
  const intakeRequests: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json({
      ...wgsCapabilities(),
      deployed_pipelines: ["wgs", "gatk"],
      pipelines: [
        ...wgsCapabilities().pipelines,
        {id: "gatk", display_name: "GATK Cloud", dag_id: "bio_gatk", version: "7.6.0", enabled: true, submit_enabled: true, capabilities: ["submit", "rules", "artifacts"], execution_targets: ["cce"]},
      ],
    });
    if (url.includes("/api/dashboard/overview")) return json({totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0}, sample_summary: {total: 0, running: 0, workflow_failed: 0, completed: 0}, status_distribution: {}, trend: [], sample_trend: []});
    if (url.includes("/api/dashboard/runs")) return json({items: [], total: 0, limit: 10, offset: 0});
    if (url.includes("/api/intake/scanner-state")) {
      intakeRequests.push(url);
      return json({last_scanned_directory_count: 0, schedule_seconds: 600, auto_dispatch_enabled: false});
    }
    if (url.includes("/api/intake/status")) {
      intakeRequests.push(url);
      return url.includes("pipeline=gatk")
        ? jsonStatus({detail: {code: "PIPELINE_CAPABILITY_UNAVAILABLE"}}, 409)
        : json({items: [], total: 0, limit: 10, offset: 0});
    }
    if (url.includes("/api/platform/resources")) return json({status: "stale", items: [], updated_at: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByRole("heading", {name: "WGS Intake Queue"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "GATK Cloud"}));
  await waitFor(() => expect(screen.getByText("Selected pipeline: GATK Cloud")).toBeInTheDocument());
  expect(screen.queryByRole("heading", {name: "WGS Intake Queue"})).not.toBeInTheDocument();
  expect(intakeRequests.some((url) => url.includes("pipeline=gatk"))).toBe(false);
});

it("keeps scanner metadata when the discovery list has a transiently unavailable API", async () => {
  let intakeAttempts = 0;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/auth/me")) return json({username: "viewer", role: "viewer"});
    if (url.endsWith("/api/platform/capabilities")) return json(wgsCapabilities("WGS production"));
    if (url.includes("/api/dashboard/overview")) return json({totals: {runs: 0, running: 0, failed: 0, success: 0, created: 0}, sample_summary: {total: 0, running: 0, workflow_failed: 0, completed: 0}, status_distribution: {}, trend: [], sample_trend: []});
    if (url.includes("/api/dashboard/runs")) return json({items: [], total: 0, limit: 10, offset: 0});
    if (url.includes("/api/intake/scanner-state")) return json({last_scanned_directory_count: 1843, schedule_seconds: 600, auto_dispatch_enabled: false});
    if (url.includes("/api/intake/status")) {
      intakeAttempts += 1;
      return Promise.reject(new TypeError("Failed to fetch"));
    }
    if (url.includes("/api/platform/resources")) return json({status: "stale", items: [], updated_at: null});
    return json({items: [], total: 0});
  }));

  render(<App />);

  expect(await screen.findByText("本轮检查 1843 个批次目录")).toBeInTheDocument();
  expect(await screen.findByText(/Intake unavailable: Failed to fetch/)).toBeInTheDocument();
  expect(intakeAttempts).toBe(2);
});

function json(value: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(value), {status: 200, headers: {"Content-Type": "application/json"}}));
}
function jsonStatus(value: unknown, status: number): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(value), {status, headers: {"Content-Type": "application/json"}}));
}

function wgsCapabilities(environment = "WGS") {
  return {
    environment,
    deployed_pipelines: ["wgs"],
    pipelines: [{
      id: "wgs",
      display_name: "WGS",
      dag_id: "bio_wgs",
      version: "4.1.1",
      enabled: true,
      submit_enabled: true,
      capabilities: ["intake", "submit", "rules", "qc", "artifacts", "resume", "rerun"],
      execution_targets: ["cce", "local", "sge"],
    }],
    airflow_url: null,
  };
}
