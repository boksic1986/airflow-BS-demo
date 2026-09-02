import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router-dom";
import {describe, expect, it, vi} from "vitest";

import type {DashboardRunTrackerRow, IntakeDiscovery, IntakeScannerStateResponse} from "../api";
import {IntakeScannerPanel} from "../features/dashboard/IntakeScannerPanel";
import {IntakeDiscoveryTable} from "./IntakeDiscoveryTable";
import {LogViewer, preferredLogSource} from "./LogViewer";
import {OperationProjectCell} from "./OperationCells";
import {RunTracker} from "./RunTracker";

const manualRun: DashboardRunTrackerRow = {
  analysis_id: "NIPT_MANUAL",
  project_name: "Manual NIPT",
  pipeline: "nipt_docker",
  status: "failed",
  display_status: "failed",
  qc_status: "unknown",
  qc_display_status: "unavailable",
  qc_display_note: "Workflow stopped before QC.",
  run_source: "manual",
  source_batch_id: "batch-20",
  sample_count: 20,
  percent: 40,
  progress_source: "snakemake_events",
  not_in_airflow: false,
};

it("labels manual runs and exposes QC unavailable without sample metric rows", () => {
  render(<MemoryRouter><RunTracker rows={[manualRun]} total={1} limit={10} offset={0} filter="all" keyword="" onFilterChange={vi.fn()} onKeywordChange={vi.fn()} onPageChange={vi.fn()} onSubmit={vi.fn()} onSync={vi.fn()} /></MemoryRouter>);

  expect(screen.getByText("Manual")).toBeInTheDocument();
  expect(screen.getAllByText("batch-20").length).toBeGreaterThan(0);
  expect(screen.queryByText("QC unavailable")).not.toBeInTheDocument();
});

it("hides a dot-only source batch placeholder", () => {
  render(<MemoryRouter><OperationProjectCell analysisId="NIPT_DOT" fallbackId="NIPT_DOT" projectName="NIPT batch" sampleCount={27} source="manual" sourceBatchId="." submittedBy="jiucheng" /></MemoryRouter>);

  expect(screen.queryByTitle("Source batch")).not.toBeInTheDocument();
});

it("switches Intake scanner between pending records and history", async () => {
  const onViewChange = vi.fn();
  const item: IntakeDiscovery = {pipeline: "pgta", root_path: "/data/inbox", batch_id: "project-1", fingerprint: "x", file_count: 10, total_bytes: 100, ready_state: "observed", submit_state: "not_submitted"};
  render(<MemoryRouter><IntakeScannerPanel items={[item]} total={1} limit={10} offset={0} loading={false} error={null} view="pending" onViewChange={onViewChange} onPageChange={vi.fn()} /></MemoryRouter>);

  await userEvent.click(screen.getByRole("button", {name: "History"}));
  expect(onViewChange).toHaveBeenCalledWith("history");
});

it("shows T7 scan-only discovery counts without sample identifiers", () => {
  const item: IntakeDiscovery = {
    pipeline: "wgs",
    chip_id: "2201th_20260821B_E250208844",
    batch_id: "2201th_20260821B_E250208844",
    sequencing_batch: "20260821B",
    ready_state: "ready",
    submit_state: "disabled",
    analysis_id: null,
    eligible_pair_count: 17,
    excluded_addon_pair_count: 5,
    pair_issue_count: 0,
  };

  const scanner: IntakeScannerStateResponse = {
    scanner: "wgs-intake-scanner",
    enabled: true,
    schedule_seconds: 600,
    auto_dispatch_enabled: false,
    first_scan_at: "2026-08-30T01:00:00Z",
    last_scan_at: "2026-08-30T01:30:00Z",
    last_scanned_directory_count: 1830,
    last_error: null,
  };

  render(<MemoryRouter><IntakeScannerPanel scanner={scanner} items={[item]} total={1} limit={10} offset={0} loading={false} error={null} view="pending" onViewChange={vi.fn()} onPageChange={vi.fn()} /></MemoryRouter>);

  expect(screen.getByRole("heading", {name: "T7自动扫描"})).toBeInTheDocument();
  expect(screen.getByText("自动发现新的测序批次；分析任务需人工确认")).toBeInTheDocument();
  expect(screen.getByText("扫描周期 10分钟")).toBeInTheDocument();
  expect(screen.getByText("本轮检查 1830 个批次目录")).toBeInTheDocument();
  expect(screen.queryByText(/BarcodeStat\.txt/)).not.toBeInTheDocument();
  expect(screen.getByText("20260821B")).toBeInTheDocument();
  expect(screen.getByText("17")).toBeInTheDocument();
  expect(screen.getByText("5")).toBeInTheDocument();
  expect(screen.queryByText(/sample/i)).not.toBeInTheDocument();
});

it("aligns linked intake operations with Run Tracker project and runtime details", () => {
  const item: IntakeDiscovery = {
    pipeline: "nipt_docker",
    root_path: "/data/project/CNV/PGT-A/rawdata/lib_test/pgta_crontab",
    batch_id: "nipt-batch-20",
    fingerprint: "x",
    file_count: 40,
    total_bytes: 100,
    ready_state: "ready",
    submit_state: "submitted",
    analysis_id: "NIPT_20",
    project_name: "NIPT Project 20",
    submitted_by: "jiucheng",
    run_source: "intake",
    sample_count: 20,
    analysis_status: "success",
    display_status: "success",
    progress_percent: 100,
    current_stage: "Completed",
    elapsed_seconds: 1800,
    estimated_remaining_seconds: null,
    submitted_at: "2026-07-14T03:30:00Z",
    pipeline_finished_at: "2026-07-14T04:00:00Z",
  };

  render(<MemoryRouter><IntakeDiscoveryTable ariaLabel="Intake operations" items={[item]} /></MemoryRouter>);

  expect(screen.getByText("NIPT Project 20")).toBeInTheDocument();
  expect(screen.getByText("NIPT_20")).toBeInTheDocument();
  expect(screen.getByText("Operator jiucheng / 20 samples")).toBeInTheDocument();
  expect(screen.getByText("20 samples", {selector: "td"})).toBeInTheDocument();
  expect(screen.getByText("Intake")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "Runtime / ETA"})).toBeInTheDocument();
  expect(screen.getByText(/Elapsed 30m/)).toBeInTheDocument();
  expect(screen.queryByText(item.root_path!)).not.toBeInTheDocument();
});

describe("LogViewer grouping", () => {
  it("groups failed sample logs separately from workflow and other rule logs", () => {
    render(<LogViewer stream="stderr" onStreamChange={vi.fn()} log={null} error={null} activeKey="failed-s1" onKeyChange={vi.fn()} sources={[
      {key: "failed-s1", label: "S1 mapping stderr", stream: "stderr", relative_path: "logs/S1.err", rule: "map", sample_id: "S1", status: "failed"},
      {key: "workflow", label: "Workflow stderr", stream: "stderr", relative_path: "logs/workflow.err"},
      {key: "success-s2", label: "S2 mapping", stream: "stdout", relative_path: "logs/S2.out", rule: "map", sample_id: "S2", status: "success"},
    ]} />);

    expect(screen.getByRole("group", {name: "Failed sample logs"})).toBeInTheDocument();
    expect(screen.getByRole("group", {name: "Workflow stdout/stderr"})).toBeInTheDocument();
    expect(screen.getByRole("group", {name: "Other rule logs"})).toBeInTheDocument();
  });

  it("opens a failed sample log before the current successful rule log", () => {
    const preferred = preferredLogSource([
      {key: "current-map", label: "map current", stream: "stdout", relative_path: "log/sample-ok.map.log", rule: "map", sample_id: "sample-ok", status: "success"},
      {key: "failed-map", label: "map failed", stream: "stdout", relative_path: "log/sample-failed.map.log", rule: "map", sample_id: "sample-failed", status: "failed"},
      {key: "workflow-stderr", label: "stderr", stream: "stderr", relative_path: "logs/snakemake.stderr.log"},
    ], "failed", "map");

    expect(preferred?.key).toBe("failed-map");
  });
});
