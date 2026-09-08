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

it("marks Run Tracker headings and cells for compact centered responsive layout", () => {
  const {container} = render(
    <MemoryRouter>
      <RunTracker
        rows={[row]}
        total={1}
        limit={10}
        offset={0}
        filter="all"
        keyword=""
        onFilterChange={() => undefined}
        onKeywordChange={() => undefined}
        onPageChange={() => undefined}
        onSubmit={() => undefined}
        onSync={() => undefined}
      />
    </MemoryRouter>,
  );

  expect(screen.getByRole("columnheader", {name: "Started"})).toHaveClass("tracker-time-heading");
  expect(screen.getByRole("columnheader", {name: "Finished"})).toHaveClass("tracker-time-heading");
  expect(screen.getByTitle(/Airflow handoff time/)).toHaveClass("tracker-time-cell");
  expect(screen.getByTitle(/Pipeline completion time/)).toHaveClass("tracker-time-cell");

  const compactHeadings = ["Project", "Batch", "Pipeline", "Status", "Data lifecycle", "Current stage"];
  compactHeadings.forEach((name) => {
    expect(screen.getByRole("columnheader", {name})).toHaveClass("tracker-centered-heading", "tracker-compact-heading");
  });

  const headings = screen.getAllByRole("columnheader");
  headings.forEach((heading) => expect(heading).toHaveClass("tracker-centered-heading"));

  const cells = Array.from(container.querySelectorAll("tbody td"));
  expect(cells).toHaveLength(10);
  cells.forEach((cell) => expect(cell).toHaveClass("tracker-centered-cell"));
  cells.slice(0, 6).forEach((cell) => expect(cell).toHaveClass("tracker-compact-cell"));
});

it("centers the project source tag without relying on the compact breakpoint", () => {
  const {container} = render(
    <MemoryRouter>
      <RunTracker
        rows={[row]}
        total={1}
        limit={10}
        offset={0}
        filter="all"
        keyword=""
        onFilterChange={() => undefined}
        onKeywordChange={() => undefined}
        onPageChange={() => undefined}
        onSubmit={() => undefined}
        onSync={() => undefined}
      />
    </MemoryRouter>,
  );

  const sourceLine = container.querySelector<HTMLElement>(".tracker-source-line");
  expect(sourceLine).not.toBeNull();
  expect(sourceLine).toHaveClass("tracker-source-line-centered");
});
