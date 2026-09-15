import "@testing-library/jest-dom/vitest";
import {cleanup, render, screen} from "@testing-library/react";
import {afterEach, expect, it} from "vitest";
import {EstimatedStageProgress} from "./EstimatedStageProgress";
import {CurrentProgressPanel} from "../features/run-detail/CurrentProgressPanel";
import type {RunDetail, StageEstimate} from "../api";

afterEach(cleanup);
const estimate = {estimated_progress_percent: 50, estimate_model: "stage_median_linear_v1",
  estimate_remaining_seconds: 60, estimate_generation: 2} as StageEstimate;

it("uses the shared accessible bar for WGS estimates and caps overrun display", () => {
  const view = render(<EstimatedStageProgress stage={estimate} status="running" />);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  expect(screen.getByText(/预估进度/)).toBeInTheDocument();
  expect(screen.getByText(/续跑中/)).toBeInTheDocument();
  view.rerender(<EstimatedStageProgress stage={{...estimate, estimated_progress_percent: 99, estimate_overrun: true, estimate_remaining_seconds: 0}} status="running" />);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "99");
  expect(screen.getByText(/已超过预计时间/)).toBeInTheDocument();
});

it("keeps failed estimates failed and unknown history unmeasured", () => {
  const view = render(<EstimatedStageProgress stage={{...estimate, estimate_frozen: true}} status="failed" />);
  expect(screen.getByRole("progressbar")).toHaveClass("progress-failed");
  view.rerender(<EstimatedStageProgress stage={{...estimate, estimate_frozen: true}} status="running" />);
  expect(screen.getByRole("progressbar")).toHaveClass("progress-queued");
  view.rerender(<EstimatedStageProgress stage={{estimate_model: "stage_median_linear_v1"}} status="running" />);
  expect(screen.getByText(/暂无预估/)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
});

it("current progress presents estimate rather than unavailable or measured complete", () => {
  render(<CurrentProgressPanel detail={{analysis_id: "SYNTH", pipeline: "wgs", status: "running"} as RunDetail}
    progress={{available: false, percent: 0, label: "Detailed progress unavailable", currentStep: "Publishing", note: "", notInAirflow: false, status: "running"}}
    stage={estimate} />);
  expect(screen.queryByText("Detailed progress unavailable")).not.toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
});
