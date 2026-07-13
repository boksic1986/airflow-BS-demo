import "@testing-library/jest-dom/vitest";

import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router-dom";
import {describe, expect, it, vi} from "vitest";

import type {DashboardRunTrackerRow, IntakeDiscovery} from "../api";
import {IntakeScannerPanel} from "../features/dashboard/IntakeScannerPanel";
import {LogViewer, preferredLogSource} from "./LogViewer";
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
  expect(screen.getByText("batch-20")).toBeInTheDocument();
  expect(screen.getByText("QC unavailable")).toBeInTheDocument();
});

it("switches Intake scanner between pending records and history", async () => {
  const onViewChange = vi.fn();
  const item: IntakeDiscovery = {pipeline: "pgta", root_path: "/data/inbox", batch_id: "project-1", fingerprint: "x", file_count: 10, total_bytes: 100, ready_state: "observed", submit_state: "not_submitted"};
  render(<MemoryRouter><IntakeScannerPanel items={[item]} total={1} limit={10} offset={0} loading={false} error={null} view="pending" onViewChange={onViewChange} onPageChange={vi.fn()} /></MemoryRouter>);

  await userEvent.click(screen.getByRole("button", {name: "History"}));
  expect(onViewChange).toHaveBeenCalledWith("history");
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
