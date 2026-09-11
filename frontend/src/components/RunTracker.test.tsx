import "@testing-library/jest-dom";

import {render, screen} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";

import type {DashboardRunTrackerRow} from "../api";
import {RunTracker} from "./RunTracker";

const row: DashboardRunTrackerRow = {
  analysis_id: "WGS_20260908_120000_T230",
  project_name: "WGS_Clinical",
  batch_no: "20260908A",
  pipeline: "wgs",
  status: "success",
  qc_status: "pass",
  sample_count: 3,
  submitted_at: "2026-09-08T01:02:03Z",
  pipeline_finished_at: "2026-09-08T04:05:06Z",
  progress_source: "test",
  not_in_airflow: false,
};

it("offers cancelled history and does not show pending progress for a cancelled run", () => {
  render(<MemoryRouter><RunTracker rows={[{...row,status:'cancelled',sample_scope_status:'preparing'}]} total={1} limit={10} offset={0} filter="all" keyword="" onFilterChange={()=>undefined} onKeywordChange={()=>undefined} onPageChange={()=>undefined} onSubmit={()=>undefined}/></MemoryRouter>);
  expect(screen.getByRole('button',{name:'已取消记录'})).toBeInTheDocument();
  expect(screen.queryByText('Waiting to start')).not.toBeInTheDocument();
  expect(screen.queryByText(/待确定分析范围/)).not.toBeInTheDocument();
  expect(screen.getAllByText('提交已取消').length).toBeGreaterThan(0);
});

it("keeps project content left aligned and omits the compact lifecycle column", () => {
  const {container} = render(
    <MemoryRouter>
      <RunTracker rows={[row]} total={1} limit={10} offset={0} filter="all" keyword="" onFilterChange={() => undefined} onKeywordChange={() => undefined} onPageChange={() => undefined} onSubmit={() => undefined} />
    </MemoryRouter>,
  );

  expect(screen.queryByRole("columnheader", {name: "Data lifecycle"})).not.toBeInTheDocument();
  expect(screen.getByRole("columnheader", {name: "Project"})).toHaveClass("tracker-project-heading");
  expect(screen.getByRole("columnheader", {name: "Project"})).not.toHaveClass("tracker-centered-heading", "tracker-compact-heading");
  expect(screen.getByRole("columnheader", {name: "Started"})).toHaveClass("tracker-time-heading");
  expect(screen.getByRole("columnheader", {name: "Finished"})).toHaveClass("tracker-time-heading");
  expect(screen.getByTitle(/Airflow handoff time/)).toHaveClass("tracker-time-cell");
  expect(screen.getByTitle(/Pipeline completion time/)).toHaveClass("tracker-time-cell");

  const headings = screen.getAllByRole("columnheader");
  expect(headings).toHaveLength(9);
  headings.slice(1).forEach((heading) => expect(heading).toHaveClass("tracker-centered-heading"));
  headings.forEach((heading) => expect(heading).not.toHaveClass("tracker-compact-heading"));

  const cells = Array.from(container.querySelectorAll("tbody td"));
  expect(cells).toHaveLength(9);
  expect(cells[0]).toHaveClass("tracker-project-cell");
  expect(cells[0]).not.toHaveClass("tracker-centered-cell", "tracker-compact-cell");
  cells.slice(1).forEach((cell) => expect(cell).toHaveClass("tracker-centered-cell"));
  cells.forEach((cell) => expect(cell).not.toHaveClass("tracker-compact-cell"));
});

it("left aligns the project source tag", () => {
  const {container} = render(
    <MemoryRouter>
      <RunTracker rows={[row]} total={1} limit={10} offset={0} filter="all" keyword="" onFilterChange={() => undefined} onKeywordChange={() => undefined} onPageChange={() => undefined} onSubmit={() => undefined} />
    </MemoryRouter>,
  );

  const sourceLine = container.querySelector<HTMLElement>(".tracker-source-line");
  expect(sourceLine).not.toBeNull();
  expect(sourceLine).not.toHaveClass("tracker-source-line-centered");
});

it("right aligns the stage percentage above its progress bar", () => {
  render(
    <MemoryRouter>
      <RunTracker rows={[{...row, stage_progress: {available: true, percent: 100, completed_units: 1, total_units: 1, unit: "workflow"}}]} total={1} limit={10} offset={0} filter="all" keyword="" onFilterChange={() => undefined} onKeywordChange={() => undefined} onPageChange={() => undefined} onSubmit={() => undefined} />
    </MemoryRouter>,
  );

  expect(screen.getByText("100.0%").closest(".run-progress-meta")).toHaveClass("align-end");
});
