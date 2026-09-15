import "@testing-library/jest-dom/vitest";
import {cleanup, render, screen} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {afterEach, expect, it} from "vitest";
import type {DashboardRunTrackerRow, RunDetail, RunProgressResponse} from "../api";
import {RunTracker} from "./RunTracker";
import {CurrentProgressPanel} from "../features/run-detail/CurrentProgressPanel";
import {progressFromResponse} from "../lib/runProgress";

afterEach(cleanup);

it("uses the same overall completion label in Tracker and detail for both pipelines", () => {
  for (const pipeline of ["wgs", "gatk"]) {
    const row = {analysis_id: "SYNTH", pipeline, status: "success", current_stage_label: "WGS workflow completed", not_in_airflow: false} as DashboardRunTrackerRow;
    const progress = progressFromResponse({status: "success", stage_status: "success", stage_label: row.current_stage_label, progress_percent: 100} as RunProgressResponse);
    render(<MemoryRouter><RunTracker rows={[row]} total={1} limit={10} offset={0} filter="all" keyword="" onFilterChange={() => {}} onKeywordChange={() => {}} onPageChange={() => {}} onSubmit={() => {}} />
      <CurrentProgressPanel detail={{...row} as RunDetail} progress={progress} /></MemoryRouter>);
    expect(screen.getAllByText("Completed", {selector: "strong"})).toHaveLength(2);
    expect(screen.queryByText("WGS workflow completed")).not.toBeInTheDocument();
    cleanup();
  }
});

it("does not mistake a successful individual stage for overall completion", () => {
  for (const status of ["running", "publishing", "failed", "cancelled"]) {
    const progress = progressFromResponse({status, stage_status: "success", stage_label: "Publishing WGS results", progress_percent: 100} as RunProgressResponse);
    render(<CurrentProgressPanel detail={{analysis_id: "SYNTH", pipeline: "wgs", status} as RunDetail} progress={progress} />);
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
    expect(screen.getByText("Publishing WGS results", {selector: "strong"})).toBeInTheDocument();
    cleanup();
  }
});
